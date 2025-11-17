"""
代码生成模块
Code Generation Module

本模块提供各种语言和框架的代码生成功能
"""
from src.code_gen.backend_templates import (
    generate_backend,
    generate_flask_backend,
    generate_nodejs_backend,
    generate_go_backend
)

__all__ = [
    'generate_backend',
    'generate_flask_backend',
    'generate_nodejs_backend',
    'generate_go_backend'
]
