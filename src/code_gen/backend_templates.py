"""
多语言后端代码生成模板
Multi-Language Backend Code Generation Templates

本模块提供多种后端语言和框架的代码生成模板。
支持根据API契约自动生成不同语言的后端代码骨架。

支持的后端技术栈:
    - Python + Flask (默认)
    - Node.js + Express
    - Go + Gin
    - (未来可扩展: Java Spring, Rust Actix等)

主要功能:
    - 根据API契约生成路由和处理函数
    - 生成数据模型
    - 生成配置文件和依赖文件
    - 生成README和运行说明

使用方式:
    >>> from src.code_gen.backend_templates import generate_nodejs_backend
    >>> code = generate_nodejs_backend(api_contract)
    >>> # 或者使用统一接口
    >>> code = generate_backend(api_contract, language='nodejs')
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def generate_flask_backend(api_contract: Dict[str, Any]) -> Dict[str, str]:
    """
    生成Flask后端代码

    Args:
        api_contract (Dict[str, Any]): API契约字典

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射
    """
    endpoints = api_contract.get('endpoints', [])
    base_url = api_contract.get('base_url', 'http://localhost:5000')

    # 生成主应用文件
    app_code = _generate_flask_app(endpoints)

    # 生成requirements.txt
    requirements = """Flask==2.3.0
flask-cors==4.0.0
python-dotenv==1.0.0
"""

    # 生成README
    readme = _generate_flask_readme(base_url)

    return {
        'app.py': app_code,
        'requirements.txt': requirements,
        'README.md': readme,
        '.env.example': 'FLASK_ENV=development\nPORT=5000\n'
    }


def _generate_flask_app(endpoints: List[Dict]) -> str:
    """生成Flask应用代码"""
    routes = []

    for endpoint in endpoints:
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        description = endpoint.get('description', '')

        # 转换路径参数格式 /api/items/:id -> /api/items/<id>
        flask_path = path.replace(':', '<').replace('/', '/<') if ':' in path else path
        if '<' in flask_path:
            flask_path = flask_path.replace('/<', '/<string:')
            flask_path += '>'

        # 生成路由处理函数
        func_name = _path_to_function_name(path, method)

        route_code = f'''
@app.route('{flask_path}', methods=['{method}'])
def {func_name}():
    """
    {description}
    """
    try:
        # TODO: Implement business logic
        return jsonify({{'message': 'Not implemented yet'}}), 501
    except Exception as e:
        return jsonify({{'error': str(e)}}), 500
'''
        routes.append(route_code)

    app_template = f'''from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'

# Routes
{''.join(routes)}

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({{'status': 'healthy'}}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
'''

    return app_template


def _generate_flask_readme(base_url: str) -> str:
    """生成Flask README"""
    return f'''# Flask Backend

Auto-generated Flask backend application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the application:
```bash
python app.py
```

The server will start at: {base_url}

## API Endpoints

See the API documentation for details on available endpoints.

## Development

- The application runs in debug mode when FLASK_ENV=development
- CORS is enabled for all origins
- Health check available at /health
'''


def generate_nodejs_backend(api_contract: Dict[str, Any]) -> Dict[str, str]:
    """
    生成Node.js + Express后端代码

    Args:
        api_contract (Dict[str, Any]): API契约字典

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射
    """
    endpoints = api_contract.get('endpoints', [])
    base_url = api_contract.get('base_url', 'http://localhost:3000')

    # 生成主应用文件
    app_code = _generate_express_app(endpoints)

    # 生成package.json
    package_json = _generate_package_json()

    # 生成README
    readme = _generate_nodejs_readme(base_url)

    return {
        'server.js': app_code,
        'package.json': package_json,
        'README.md': readme,
        '.env.example': 'NODE_ENV=development\nPORT=3000\n',
        '.gitignore': 'node_modules/\n.env\n'
    }


def _generate_express_app(endpoints: List[Dict]) -> str:
    """生成Express应用代码"""
    routes = []

    for endpoint in endpoints:
        method = endpoint.get('method', 'GET').lower()
        path = endpoint.get('path', '/')
        description = endpoint.get('description', '')

        # 转换路径参数格式 /api/items/:id (Express原生格式)
        express_path = path

        # 生成路由处理函数
        func_name = _path_to_function_name(path, method)

        route_code = f'''
// {description}
app.{method}('{express_path}', async (req, res) => {{
    try {{
        // TODO: Implement business logic
        res.status(501).json({{ message: 'Not implemented yet' }});
    }} catch (error) {{
        console.error(error);
        res.status(500).json({{ error: error.message }});
    }}
}});
'''
        routes.append(route_code)

    app_template = f'''const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({{ extended: true }}));

// Request logging
app.use((req, res, next) => {{
    console.log(`${{req.method}} ${{req.url}}`);
    next();
}});

// Routes
{''.join(routes)}

// Health check endpoint
app.get('/health', (req, res) => {{
    res.json({{ status: 'healthy' }});
}});

// Error handling middleware
app.use((err, req, res, next) => {{
    console.error(err.stack);
    res.status(500).json({{ error: 'Something went wrong!' }});
}});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {{
    console.log(`Server running on port ${{PORT}}`);
    console.log(`Environment: ${{process.env.NODE_ENV || 'development'}}`);
}});

module.exports = app;
'''

    return app_template


def _generate_package_json() -> str:
    """生成package.json"""
    return '''{
  "name": "express-backend",
  "version": "1.0.0",
  "description": "Auto-generated Express backend",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.0.3"
  },
  "devDependencies": {
    "nodemon": "^2.0.22"
  },
  "engines": {
    "node": ">=14.0.0"
  }
}
'''


def _generate_nodejs_readme(base_url: str) -> str:
    """生成Node.js README"""
    return f'''# Express Backend

Auto-generated Express.js backend application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the application:

Production:
```bash
npm start
```

Development (with auto-reload):
```bash
npm run dev
```

The server will start at: {base_url}

## API Endpoints

See the API documentation for details on available endpoints.

## Development

- The application includes CORS support
- JSON body parsing is enabled
- Request logging is included
- Health check available at /health

## Project Structure

- server.js - Main application file
- package.json - Dependencies and scripts
- .env - Environment configuration (not committed)
'''


def generate_go_backend(api_contract: Dict[str, Any]) -> Dict[str, str]:
    """
    生成Go + Gin后端代码

    Args:
        api_contract (Dict[str, Any]): API契约字典

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射
    """
    endpoints = api_contract.get('endpoints', [])
    base_url = api_contract.get('base_url', 'http://localhost:8080')

    # 生成主应用文件
    main_code = _generate_gin_main(endpoints)

    # 生成go.mod
    go_mod = _generate_go_mod()

    # 生成README
    readme = _generate_go_readme(base_url)

    return {
        'main.go': main_code,
        'go.mod': go_mod,
        'README.md': readme,
        '.env.example': 'GIN_MODE=release\nPORT=8080\n',
        '.gitignore': 'bin/\n*.exe\n.env\n'
    }


def _generate_gin_main(endpoints: List[Dict]) -> str:
    """生成Gin应用代码"""
    routes = []

    for endpoint in endpoints:
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        description = endpoint.get('description', '')

        # 转换路径参数格式 /api/items/:id (Gin原生格式)
        gin_path = path

        # 生成路由处理函数
        func_name = _path_to_function_name(path, method).title().replace('_', '')

        route_code = f'''
// {func_name} - {description}
func {func_name}(c *gin.Context) {{
    // TODO: Implement business logic
    c.JSON(http.StatusNotImplemented, gin.H{{
        "message": "Not implemented yet",
    }})
}}
'''
        routes.append(route_code)

    # 生成路由注册
    route_registrations = []
    for endpoint in endpoints:
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        func_name = _path_to_function_name(path, method).title().replace('_', '')

        if method == 'GET':
            route_registrations.append(f"    r.GET(\"{path}\", {func_name})")
        elif method == 'POST':
            route_registrations.append(f"    r.POST(\"{path}\", {func_name})")
        elif method == 'PUT':
            route_registrations.append(f"    r.PUT(\"{path}\", {func_name})")
        elif method == 'DELETE':
            route_registrations.append(f"    r.DELETE(\"{path}\", {func_name})")

    main_template = f'''package main

import (
    "log"
    "net/http"
    "os"

    "github.com/gin-gonic/gin"
    "github.com/joho/godotenv"
)

func main() {{
    // Load environment variables
    godotenv.Load()

    // Create Gin router
    r := gin.Default()

    // CORS middleware
    r.Use(corsMiddleware())

    // Routes
{chr(10).join(route_registrations)}

    // Health check
    r.GET("/health", func(c *gin.Context) {{
        c.JSON(http.StatusOK, gin.H{{
            "status": "healthy",
        }})
    }})

    // Start server
    port := os.Getenv("PORT")
    if port == "" {{
        port = "8080"
    }}

    log.Printf("Server starting on port %s", port)
    if err := r.Run(":" + port); err != nil {{
        log.Fatal(err)
    }}
}}

// corsMiddleware adds CORS headers
func corsMiddleware() gin.HandlerFunc {{
    return func(c *gin.Context) {{
        c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
        c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type")

        if c.Request.Method == "OPTIONS" {{
            c.AbortWithStatus(204)
            return
        }}

        c.Next()
    }}
}}

{''.join(routes)}
'''

    return main_template


def _generate_go_mod() -> str:
    """生成go.mod"""
    return '''module backend

go 1.20

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/joho/godotenv v1.5.1
)
'''


def _generate_go_readme(base_url: str) -> str:
    """生成Go README"""
    return f'''# Go Gin Backend

Auto-generated Go backend application using Gin framework.

## Setup

1. Initialize Go modules and download dependencies:
```bash
go mod download
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the application:

Development:
```bash
go run main.go
```

Build and run:
```bash
go build -o server
./server
```

The server will start at: {base_url}

## API Endpoints

See the API documentation for details on available endpoints.

## Features

- Gin web framework for high performance
- CORS middleware included
- Environment variable configuration
- Health check endpoint at /health
- Structured error handling

## Project Structure

- main.go - Main application file
- go.mod - Module dependencies
- .env - Environment configuration (not committed)
'''


def _path_to_function_name(path: str, method: str) -> str:
    """将路径和方法转换为函数名"""
    # 移除参数部分
    clean_path = path.replace(':', '').replace('/', '_')
    # 移除首尾下划线
    clean_path = clean_path.strip('_')
    # 添加方法前缀
    return f"{method.lower()}_{clean_path}".replace('__', '_')


def generate_backend(api_contract: Dict[str, Any], language: str = 'flask') -> Dict[str, str]:
    """
    统一的后端代码生成接口

    Args:
        api_contract (Dict[str, Any]): API契约字典
        language (str): 后端语言/框架，可选值:
            - 'flask' (默认)
            - 'nodejs' / 'express'
            - 'go' / 'gin'

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射

    Example:
        >>> api_contract = {...}
        >>> files = generate_backend(api_contract, language='nodejs')
        >>> for path, content in files.items():
        ...     write_file(path, content)
    """
    language = language.lower()

    if language in ['flask', 'python']:
        return generate_flask_backend(api_contract)
    elif language in ['nodejs', 'express', 'node', 'javascript']:
        return generate_nodejs_backend(api_contract)
    elif language in ['go', 'gin', 'golang']:
        return generate_go_backend(api_contract)
    else:
        logger.warning(f"Unsupported language: {language}, falling back to Flask")
        return generate_flask_backend(api_contract)
