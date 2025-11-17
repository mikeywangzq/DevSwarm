"""
系统配置模块
System Configuration Module

集中管理DevSwarm系统的所有配置选项。
支持从环境变量或配置文件加载配置。

配置项:
    - Backend语言/框架选择
    - Frontend框架选择
    - LLM提供商和模型
    - 工作区路径
    - 性能监控开关
    - 日志级别

使用方式:
    >>> from src.config.settings import get_config
    >>> config = get_config()
    >>> print(config.backend_language)  # 'flask', 'nodejs', 'go'
"""
import os
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DevSwarmConfig:
    """
    DevSwarm系统配置

    Attributes:
        backend_language (str): 后端语言/框架，可选值: 'flask', 'nodejs', 'go'
        frontend_framework (str): 前端框架，可选值: 'vanilla', 'react', 'vue'
        llm_provider (str): LLM提供商，可选值: 'openai', 'anthropic'
        llm_model (str): LLM模型名称
        workspace_root (str): 工作区根目录
        enable_performance_monitoring (bool): 是否启用性能监控
        enable_security_scanning (bool): 是否启用安全扫描
        log_level (str): 日志级别
    """
    # Backend配置
    backend_language: str = 'flask'  # flask, nodejs, go

    # Frontend配置
    frontend_framework: str = 'vanilla'  # vanilla, react, vue

    # LLM配置
    llm_provider: str = 'openai'  # openai, anthropic
    llm_model: Optional[str] = None  # 如果为None，使用默认模型

    # 工作区配置
    workspace_root: str = './workspace'

    # 功能开关
    enable_performance_monitoring: bool = True
    enable_security_scanning: bool = True

    # 日志配置
    log_level: str = 'INFO'

    @classmethod
    def from_env(cls) -> 'DevSwarmConfig':
        """
        从环境变量加载配置

        环境变量:
            DEVSWARM_BACKEND_LANGUAGE: 后端语言 (flask, nodejs, go)
            DEVSWARM_FRONTEND_FRAMEWORK: 前端框架 (vanilla, react, vue)
            DEVSWARM_LLM_PROVIDER: LLM提供商 (openai, anthropic)
            DEVSWARM_LLM_MODEL: LLM模型名称
            DEVSWARM_WORKSPACE_ROOT: 工作区根目录
            DEVSWARM_ENABLE_PERFORMANCE: 启用性能监控 (true/false)
            DEVSWARM_ENABLE_SECURITY: 启用安全扫描 (true/false)
            DEVSWARM_LOG_LEVEL: 日志级别 (DEBUG, INFO, WARNING, ERROR)

        Returns:
            DevSwarmConfig: 配置对象
        """
        return cls(
            backend_language=os.getenv('DEVSWARM_BACKEND_LANGUAGE', 'flask').lower(),
            frontend_framework=os.getenv('DEVSWARM_FRONTEND_FRAMEWORK', 'vanilla').lower(),
            llm_provider=os.getenv('DEVSWARM_LLM_PROVIDER', 'openai').lower(),
            llm_model=os.getenv('DEVSWARM_LLM_MODEL'),
            workspace_root=os.getenv('DEVSWARM_WORKSPACE_ROOT', './workspace'),
            enable_performance_monitoring=os.getenv('DEVSWARM_ENABLE_PERFORMANCE', 'true').lower() == 'true',
            enable_security_scanning=os.getenv('DEVSWARM_ENABLE_SECURITY', 'true').lower() == 'true',
            log_level=os.getenv('DEVSWARM_LOG_LEVEL', 'INFO').upper()
        )

    def validate(self) -> bool:
        """
        验证配置有效性

        Returns:
            bool: 配置是否有效
        """
        # 验证后端语言
        valid_backends = ['flask', 'python', 'nodejs', 'node', 'express', 'go', 'gin', 'golang']
        if self.backend_language not in valid_backends:
            logger.warning(f"Invalid backend_language: {self.backend_language}, falling back to 'flask'")
            self.backend_language = 'flask'

        # 验证前端框架
        valid_frontends = ['vanilla', 'react', 'vue']
        if self.frontend_framework not in valid_frontends:
            logger.warning(f"Invalid frontend_framework: {self.frontend_framework}, falling back to 'vanilla'")
            self.frontend_framework = 'vanilla'

        # 验证LLM提供商
        valid_providers = ['openai', 'anthropic']
        if self.llm_provider not in valid_providers:
            logger.warning(f"Invalid llm_provider: {self.llm_provider}, falling back to 'openai'")
            self.llm_provider = 'openai'

        return True


# 全局配置实例
_config: Optional[DevSwarmConfig] = None


def get_config() -> DevSwarmConfig:
    """
    获取全局配置实例（单例）

    第一次调用时从环境变量加载配置，后续调用返回相同实例。

    Returns:
        DevSwarmConfig: 配置对象

    Example:
        >>> config = get_config()
        >>> print(f"Using {config.backend_language} backend")
    """
    global _config

    if _config is None:
        _config = DevSwarmConfig.from_env()
        _config.validate()
        logger.info(f"Loaded configuration: backend={_config.backend_language}, "
                   f"frontend={_config.frontend_framework}")

    return _config


def set_config(config: DevSwarmConfig):
    """
    设置全局配置（用于测试）

    Args:
        config (DevSwarmConfig): 配置对象
    """
    global _config
    _config = config
    logger.info("Configuration updated programmatically")


def reset_config():
    """重置配置（用于测试）"""
    global _config
    _config = None
