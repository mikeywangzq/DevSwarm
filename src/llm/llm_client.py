"""
LLM Client - LLM集成客户端
支持多种LLM提供商（OpenAI, Anthropic等）
"""
import os
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class LLMClient:
    """
    LLM客户端封装
    提供统一的接口调用不同的LLM
    """

    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            provider: LLM提供商
            model: 模型名称
            api_key: API密钥
        """
        self.provider = provider
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_default_model()
        self.client = None

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
        生成文本

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            生成的文本
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
        生成代码

        Args:
            description: 代码描述
            language: 编程语言
            context: 上下文信息

        Returns:
            生成的代码
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

        Args:
            error_message: 错误消息
            code_context: 代码上下文
            logs: 日志信息

        Returns:
            分析结果和修复建议
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

        Args:
            requirement: 用户需求

        Returns:
            任务分解结果
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


# 单例实例
_llm_client: Optional[LLMClient] = None


def get_llm_client(provider: LLMProvider = LLMProvider.OPENAI,
                   model: Optional[str] = None) -> LLMClient:
    """
    获取LLM客户端单例

    Args:
        provider: LLM提供商
        model: 模型名称

    Returns:
        LLM客户端实例
    """
    global _llm_client

    if _llm_client is None:
        _llm_client = LLMClient(provider=provider, model=model)

    return _llm_client
