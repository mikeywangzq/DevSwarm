"""
LLM客户端集成模块
LLM Client Integration Module

本模块封装了对大语言模型(LLM)的访问，提供统一的接口支持多个LLM提供商。
Agent通过此模块调用LLM生成代码、分析需求、调试错误等。

支持的LLM提供商:
    - OpenAI (GPT-4, GPT-3.5等)
    - Anthropic (Claude系列)
    - Local (本地模型)

主要功能:
    1. **文本生成**: 通用的文本生成接口
    2. **代码生成**: 专门的代码生成接口
    3. **错误分析**: 分析代码错误并提供修复建议
    4. **任务分解**: 将用户需求分解为具体任务
    5. **降级处理**: LLM不可用时的fallback机制

使用方式:
    1. 直接实例化LLMClient
    2. 使用get_llm_client()获取单例

Example:
    >>> # 方式1：直接实例化
    >>> client = LLMClient(provider=LLMProvider.OPENAI, model="gpt-4")
    >>> response = await client.generate("Write a hello world function")
    >>>
    >>> # 方式2：使用单例
    >>> client = get_llm_client()
    >>> code = await client.generate_code("Sort function", "python")
"""
import os
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """
    LLM提供商枚举

    定义系统支持的所有LLM提供商类型。

    Attributes:
        OPENAI: OpenAI (GPT-4, GPT-3.5等)
        ANTHROPIC: Anthropic (Claude系列)
        LOCAL: 本地模型（预留，未完全实现）
    """
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class LLMClient:
    """
    LLM客户端类

    提供统一的接口访问不同LLM提供商，屏蔽底层API差异。
    支持文本生成、代码生成、错误分析等功能。

    核心功能:
        - generate(): 通用文本生成
        - generate_code(): 代码生成
        - analyze_error(): 错误分析和修复建议
        - generate_task_breakdown(): 需求分解

    错误处理:
        - API密钥缺失: 使用fallback模式
        - 网络错误: 自动降级到fallback
        - 导入错误: 提示缺少依赖但不中断

    Attributes:
        provider (LLMProvider): 当前使用的提供商
        api_key (Optional[str]): API密钥
        model (str): 模型名称
        client: 底层LLM客户端实例
    """

    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None):
        """
        初始化LLM客户端

        尝试初始化指定提供商的客户端。如果初始化失败（如缺少API密钥或依赖），
        不会抛出异常，而是在后续使用时降级到fallback模式。

        Args:
            provider (LLMProvider): LLM提供商，默认OpenAI
            model (Optional[str]): 模型名称，如果不指定则使用默认模型
            api_key (Optional[str]): API密钥，如果不指定则从环境变量读取

        Example:
            >>> # 使用默认配置（OpenAI + GPT-4）
            >>> client = LLMClient()
            >>>
            >>> # 指定Anthropic
            >>> client = LLMClient(
            ...     provider=LLMProvider.ANTHROPIC,
            ...     model="claude-3-sonnet-20240229"
            ... )
            >>>
            >>> # 显式提供API密钥
            >>> client = LLMClient(api_key="sk-...")
        """
        self.provider = provider
        # 从参数或环境变量获取API密钥
        self.api_key = api_key or self._get_api_key()
        # 从参数或使用默认模型
        self.model = model or self._get_default_model()
        # 底层客户端实例，初始化时设置
        self.client = None

        # 初始化底层LLM客户端
        self._initialize_client()

    def _get_api_key(self) -> Optional[str]:
        """从环境变量获取API密钥"""
        if self.provider == LLMProvider.OPENAI:
            return os.getenv("OPENAI_API_KEY")
        elif self.provider == LLMProvider.ANTHROPIC:
            return os.getenv("ANTHROPIC_API_KEY")
        return None

    def _get_default_model(self) -> str:
        """获取默认模型"""
        if self.provider == LLMProvider.OPENAI:
            return "gpt-4"
        elif self.provider == LLMProvider.ANTHROPIC:
            return "claude-3-sonnet-20240229"
        return "default"

    def _initialize_client(self):
        """初始化LLM客户端"""
        try:
            if self.provider == LLMProvider.OPENAI:
                import openai
                openai.api_key = self.api_key
                self.client = openai
                logger.info(f"OpenAI client initialized with model {self.model}")

            elif self.provider == LLMProvider.ANTHROPIC:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                logger.info(f"Anthropic client initialized with model {self.model}")

            else:
                logger.warning(f"Provider {self.provider} not fully implemented")

        except ImportError as e:
            logger.error(f"Failed to import LLM library: {e}")
            logger.warning("LLM functionality will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")

    async def generate(self, prompt: str,
                      system_prompt: Optional[str] = None,
                      temperature: float = 0.7,
                      max_tokens: int = 2000,
                      **kwargs) -> str:
        """
        生成文本（通用接口）

        调用LLM生成文本响应。支持自定义system prompt和生成参数。
        如果LLM不可用，自动降级到fallback模式。

        Args:
            prompt (str): 用户提示词，描述要生成的内容
            system_prompt (Optional[str]): 系统提示词，定义AI角色和行为
            temperature (float): 温度参数(0-1)，控制随机性
                - 0: 确定性输出，适合代码生成
                - 1: 创造性输出，适合文本生成
            max_tokens (int): 最大生成token数
            **kwargs: 其他提供商特定参数

        Returns:
            str: 生成的文本内容

        Example:
            >>> response = await client.generate(
            ...     prompt="解释Python装饰器",
            ...     system_prompt="你是Python专家",
            ...     temperature=0.7
            ... )
        """
        if not self.client:
            logger.warning("LLM client not initialized, using fallback")
            return self._fallback_generate(prompt)

        try:
            if self.provider == LLMProvider.OPENAI:
                return await self._generate_openai(
                    prompt, system_prompt, temperature, max_tokens, **kwargs
                )
            elif self.provider == LLMProvider.ANTHROPIC:
                return await self._generate_anthropic(
                    prompt, system_prompt, temperature, max_tokens, **kwargs
                )
            else:
                return self._fallback_generate(prompt)

        except Exception as e:
            logger.error(f"Error generating text: {e}", exc_info=True)
            return self._fallback_generate(prompt)

    async def _generate_openai(self, prompt: str,
                               system_prompt: Optional[str],
                               temperature: float,
                               max_tokens: int,
                               **kwargs) -> str:
        """使用OpenAI生成文本"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.choices[0].message.content

    async def _generate_anthropic(self, prompt: str,
                                  system_prompt: Optional[str],
                                  temperature: float,
                                  max_tokens: int,
                                  **kwargs) -> str:
        """使用Anthropic生成文本"""
        system_params = {}
        if system_prompt:
            system_params["system"] = system_prompt

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
            **system_params,
            **kwargs
        )

        return response.content[0].text

    def _fallback_generate(self, prompt: str) -> str:
        """
        降级生成方法（当LLM不可用时）
        返回预定义的响应
        """
        logger.warning("Using fallback generation - responses will be limited")

        # 简单的关键词匹配
        prompt_lower = prompt.lower()

        if "api" in prompt_lower and "contract" in prompt_lower:
            return self._generate_api_contract_fallback()
        elif "frontend" in prompt_lower or "react" in prompt_lower:
            return self._generate_frontend_fallback()
        elif "backend" in prompt_lower or "flask" in prompt_lower:
            return self._generate_backend_fallback()
        elif "test" in prompt_lower:
            return self._generate_test_fallback()
        else:
            return "Task acknowledged. Processing..."

    def _generate_api_contract_fallback(self) -> str:
        """生成API契约的降级响应"""
        return """
{
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/items",
      "description": "Get all items",
      "response": {"items": []}
    },
    {
      "method": "POST",
      "path": "/api/items",
      "description": "Create new item",
      "request_body": {"title": "string"},
      "response": {"id": "string", "title": "string"}
    },
    {
      "method": "DELETE",
      "path": "/api/items/:id",
      "description": "Delete an item",
      "response": {"success": true}
    }
  ]
}
"""

    def _generate_frontend_fallback(self) -> str:
        """生成前端代码的降级响应"""
        return "Frontend code structure created with React components"

    def _generate_backend_fallback(self) -> str:
        """生成后端代码的降级响应"""
        return "Backend API endpoints created with Flask"

    def _generate_test_fallback(self) -> str:
        """生成测试代码的降级响应"""
        return "Test cases created for API endpoints"

    async def generate_code(self, description: str,
                           language: str,
                           context: Optional[str] = None) -> str:
        """
        生成代码（专用接口）

        针对代码生成优化的接口，使用较低temperature确保代码质量。

        Args:
            description (str): 代码功能描述
            language (str): 编程语言（如"python", "javascript"）
            context (Optional[str]): 额外上下文，如API规范、依赖说明等

        Returns:
            str: 生成的代码字符串

        Example:
            >>> code = await client.generate_code(
            ...     description="实现快速排序算法",
            ...     language="python",
            ...     context="使用递归实现"
            ... )
        """
        system_prompt = f"You are an expert {language} developer. Generate clean, well-commented code."

        prompt = f"Generate {language} code for: {description}"
        if context:
            prompt += f"\n\nContext:\n{context}"

        return await self.generate(prompt, system_prompt=system_prompt, temperature=0.3)

    async def analyze_error(self, error_message: str,
                           code_context: str,
                           logs: List[str]) -> str:
        """
        分析错误并提供修复建议

        QA Agent用于分析测试失败的错误，LLM会分析错误原因并提供具体修复方案。

        Args:
            error_message (str): 错误消息或异常信息
            code_context (str): 相关代码上下文
            logs (List[str]): 日志列表，用于辅助诊断

        Returns:
            str: 包含根因分析、修复方案和说明的文本

        Example:
            >>> fix = await client.analyze_error(
            ...     error_message="TypeError: 'NoneType' object is not subscriptable",
            ...     code_context="result = data['items'][0]",
            ...     logs=["Request failed", "Response: None"]
            ... )
        """
        system_prompt = "You are an expert debugging assistant. Analyze errors and provide specific fixes."

        prompt = f"""
Analyze this error and provide a fix:

Error: {error_message}

Code Context:
{code_context}

Logs:
{chr(10).join(logs[-10:])}  # Last 10 log lines

Provide:
1. Root cause analysis
2. Specific code fix (as a diff/patch if possible)
3. Explanation
"""

        return await self.generate(prompt, system_prompt=system_prompt, temperature=0.2)

    async def generate_task_breakdown(self, requirement: str) -> Dict[str, Any]:
        """
        将需求分解为任务

        PM Agent使用此方法将用户需求分解为具体的开发任务。
        LLM会生成API契约和任务列表。

        Args:
            requirement (str): 用户的原始需求描述

        Returns:
            Dict[str, Any]: JSON格式的任务分解结果，包含api_contract和tasks

        Example:
            >>> breakdown = await client.generate_task_breakdown(
            ...     "创建一个待办事项管理应用"
            ... )
            >>> # 返回: {"api_contract": {...}, "tasks": [...]}
        """
        system_prompt = """You are a project manager. Break down requirements into specific, actionable tasks.
Return a JSON structure with tasks."""

        prompt = f"""
Break down this requirement into specific tasks:

Requirement: {requirement}

Return a JSON object with this structure:
{{
  "api_contract": {{...}},
  "tasks": [
    {{"id": "T1", "title": "...", "description": "...", "assigned_to": "backend|frontend|qa"}},
    ...
  ]
}}
"""

        return await self.generate(prompt, system_prompt=system_prompt, temperature=0.5)


# 全局单例实例
_llm_client: Optional[LLMClient] = None


def get_llm_client(provider: LLMProvider = LLMProvider.OPENAI,
                   model: Optional[str] = None) -> LLMClient:
    """
    获取LLM客户端单例

    推荐的获取LLM客户端的方式。确保整个应用共享同一个客户端实例，
    避免重复初始化和API配额浪费。

    Args:
        provider (LLMProvider): LLM提供商，默认OpenAI
        model (Optional[str]): 模型名称，默认为提供商的推荐模型

    Returns:
        LLMClient: 全局唯一的LLM客户端实例

    Note:
        首次调用时创建实例，后续调用返回已创建的实例（忽略参数）

    Example:
        >>> # 在应用启动时初始化
        >>> client = get_llm_client(provider=LLMProvider.OPENAI)
        >>>
        >>> # 在Agent中使用
        >>> client = get_llm_client()  # 返回已创建的实例
        >>> response = await client.generate("...")
    """
    global _llm_client

    # 延迟初始化：首次调用时创建
    if _llm_client is None:
        _llm_client = LLMClient(provider=provider, model=model)

    return _llm_client
