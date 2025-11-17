"""
Backend Agent模块 - 后端开发Agent
Backend Agent Module - Backend Developer

Backend Agent负责根据PM Agent生成的API契约实现后端服务代码。
使用LLM生成Flask API端点、数据模型和业务逻辑代码。

核心职责:
    1. **读取API契约**: 从共享状态获取API契约定义
    2. **生成代码**: 使用LLM生成Flask后端代码
        - API端点实现
        - 数据模型定义
        - 路由配置
        - requirements.txt依赖文件
    3. **代码写入**: 将生成的代码写入backend目录
    4. **Bug修复**: 根据QA反馈修复后端Bug

技术栈:
    - Flask: Web框架
    - Python标准库: 数据处理
    - 文件存储或简单内存存储: 数据持久化

Example:
    >>> backend = BackendAgent(message_bus, shared_state, llm_client)
    >>> # 收到PM分配的任务后自动执行
"""
import os
from pathlib import Path
from typing import Dict, Any
import logging
from .base_agent import BaseAgent
from ..core.protocol import Task, APIContract

logger = logging.getLogger(__name__)


class BackendAgent(BaseAgent):
    """
    后端开发Agent
    负责根据API契约生成后端代码
    """

    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(
            agent_name="Backend_Agent",
            role="Backend Developer",
            message_bus=message_bus,
            shared_state=shared_state,
            llm_client=llm_client
        )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行后端开发任务

        Args:
            task: 任务

        Returns:
            执行结果
        """
        logger.info(f"Executing backend task: {task.title}")

        # 获取API契约
        api_contract = self.shared_state.get_api_contract()
        if not api_contract:
            raise ValueError("API contract not found")

        # 获取代码库路径
        backend_path = self.shared_state.get_codebase_path("backend")
        if not backend_path:
            raise ValueError("Backend path not found")

        backend_dir = Path(backend_path)

        # 如果是Bug修复任务
        if task.type == "bug_fix":
            result = await self._fix_bug(task, backend_dir)
        else:
            # 正常开发任务
            result = await self._generate_backend_code(api_contract, backend_dir)

        return result

    async def _generate_backend_code(self, api_contract: APIContract,
                                    backend_dir: Path) -> Dict[str, Any]:
        """
        生成后端代码

        Args:
            api_contract: API契约
            backend_dir: 后端目录

        Returns:
            生成结果
        """
        logger.info("Generating backend code with Flask...")

        # 生成主应用文件
        app_code = await self._generate_flask_app(api_contract)
        app_file = backend_dir / "app.py"
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(app_code)
        logger.info(f"Generated: {app_file}")

        # 生成数据存储模块
        storage_code = self._generate_storage_module()
        storage_file = backend_dir / "storage.py"
        with open(storage_file, 'w', encoding='utf-8') as f:
            f.write(storage_code)
        logger.info(f"Generated: {storage_file}")

        # 生成requirements.txt
        requirements = self._generate_requirements()
        req_file = backend_dir / "requirements.txt"
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write(requirements)
        logger.info(f"Generated: {req_file}")

        # 生成README
        readme = self._generate_backend_readme(api_contract)
        readme_file = backend_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme)
        logger.info(f"Generated: {readme_file}")

        # 生成启动脚本
        start_script = self._generate_start_script()
        script_file = backend_dir / "start.sh"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(start_script)
        os.chmod(script_file, 0o755)
        logger.info(f"Generated: {script_file}")

        return {
            "status": "success",
            "files_generated": [
                str(app_file),
                str(storage_file),
                str(req_file),
                str(readme_file),
                str(script_file)
            ],
            "output_path": str(backend_dir)
        }

    async def _generate_flask_app(self, api_contract: APIContract) -> str:
        """
        生成Flask应用代码

        Args:
            api_contract: API契约

        Returns:
            Flask代码
        """
        # 构建提示
        endpoints_str = "\n".join([
            f"- {ep['method']} {ep['path']}: {ep['description']}"
            for ep in api_contract.endpoints
        ])

        prompt = f"""
Generate a complete Flask application that implements these API endpoints:

{endpoints_str}

API Contract Details:
{api_contract.to_json()}

Requirements:
1. Use Flask framework
2. Implement all endpoints according to the contract
3. Use CORS for cross-origin requests
4. Use the storage module (from storage import Storage) for data persistence
5. Include proper error handling
6. Add request validation
7. Return JSON responses
8. Include logging

Generate ONLY the Python code for app.py, no explanations.
Start with imports and end with if __name__ == '__main__'.
"""

        code = await self.llm_client.generate_code(
            description=prompt,
            language="python",
            context=None
        )

        # 如果LLM返回了markdown代码块，提取代码
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        # 如果生成失败，使用模板
        if not code or len(code) < 100:
            code = self._generate_flask_template(api_contract)

        return code

    def _generate_flask_template(self, api_contract: APIContract) -> str:
        """生成Flask模板代码"""
        endpoints_code = []

        for ep in api_contract.endpoints:
            method = ep['method']
            path = ep['path']
            desc = ep['description']

            # 转换路径参数格式 (:id -> <id>)
            flask_path = path.replace(':id', '<id>').replace(':',  '<').replace('/<', '/<')

            if method == "GET":
                code = f'''
@app.route('{flask_path}', methods=['GET'])
def {self._route_to_function_name(path, method)}():
    """{desc}"""
    try:
        items = storage.get_all()
        return jsonify({{"items": items}}), 200
    except Exception as e:
        logger.error(f"Error: {{e}}")
        return jsonify({{"error": str(e)}}), 500
'''
            elif method == "POST":
                code = f'''
@app.route('{flask_path}', methods=['POST'])
def {self._route_to_function_name(path, method)}():
    """{desc}"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({{"error": "No data provided"}}), 400

        item = storage.create(data)
        return jsonify(item), 201
    except Exception as e:
        logger.error(f"Error: {{e}}")
        return jsonify({{"error": str(e)}}), 500
'''
            elif method == "PUT":
                code = f'''
@app.route('{flask_path}', methods=['PUT'])
def {self._route_to_function_name(path, method)}(id):
    """{desc}"""
    try:
        data = request.get_json()
        item = storage.update(id, data)
        if item:
            return jsonify(item), 200
        return jsonify({{"error": "Item not found"}}), 404
    except Exception as e:
        logger.error(f"Error: {{e}}")
        return jsonify({{"error": str(e)}}), 500
'''
            elif method == "DELETE":
                code = f'''
@app.route('{flask_path}', methods=['DELETE'])
def {self._route_to_function_name(path, method)}(id):
    """{desc}"""
    try:
        success = storage.delete(id)
        if success:
            return jsonify({{"success": True}}), 200
        return jsonify({{"error": "Item not found"}}), 404
    except Exception as e:
        logger.error(f"Error: {{e}}")
        return jsonify({{"error": str(e)}}), 500
'''
            endpoints_code.append(code)

        full_code = f'''"""
Flask Backend Application
Auto-generated by DevSwarm Backend Agent
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from storage import Storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize storage
storage = Storage()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({{"status": "healthy"}}), 200

{''.join(endpoints_code)}

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({{"error": "Not found"}}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({{"error": "Internal server error"}}), 500

if __name__ == '__main__':
    logger.info("Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
'''
        return full_code

    def _route_to_function_name(self, path: str, method: str) -> str:
        """将路由转换为函数名"""
        # /api/items -> get_items
        # /api/items/:id -> get_item
        parts = [p for p in path.split('/') if p and not p.startswith(':')]
        name = '_'.join(parts)
        method_prefix = method.lower()
        return f"{method_prefix}_{name}"

    def _generate_storage_module(self) -> str:
        """生成存储模块"""
        return '''"""
Storage Module - Simple JSON-based data storage
"""
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any

class Storage:
    """Simple JSON-based storage"""

    def __init__(self, db_file: str = "data.json"):
        self.db_file = Path(db_file)
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Ensure database file exists"""
        if not self.db_file.exists():
            with open(self.db_file, 'w') as f:
                json.dump([], f)

    def _read(self) -> List[Dict]:
        """Read all data"""
        with open(self.db_file, 'r') as f:
            return json.load(f)

    def _write(self, data: List[Dict]):
        """Write data"""
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_all(self) -> List[Dict]:
        """Get all items"""
        return self._read()

    def get_by_id(self, item_id: str) -> Optional[Dict]:
        """Get item by ID"""
        items = self._read()
        for item in items:
            if item.get('id') == item_id:
                return item
        return None

    def create(self, data: Dict) -> Dict:
        """Create new item"""
        items = self._read()

        # Generate ID if not provided
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())

        items.append(data)
        self._write(items)
        return data

    def update(self, item_id: str, data: Dict) -> Optional[Dict]:
        """Update item"""
        items = self._read()

        for i, item in enumerate(items):
            if item.get('id') == item_id:
                # Preserve ID
                data['id'] = item_id
                items[i] = data
                self._write(items)
                return data

        return None

    def delete(self, item_id: str) -> bool:
        """Delete item"""
        items = self._read()
        original_len = len(items)

        items = [item for item in items if item.get('id') != item_id]

        if len(items) < original_len:
            self._write(items)
            return True

        return False

    def clear(self):
        """Clear all data"""
        self._write([])
'''

    def _generate_requirements(self) -> str:
        """生成requirements.txt"""
        return """Flask==2.3.0
flask-cors==4.0.0
"""

    def _generate_backend_readme(self, api_contract: APIContract) -> str:
        """生成后端README"""
        endpoints = "\n".join([
            f"- `{ep['method']} {ep['path']}` - {ep['description']}"
            for ep in api_contract.endpoints
        ])

        return f"""# Backend API

Auto-generated Flask backend application.

## API Endpoints

{endpoints}

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
# Or use the start script
./start.sh
```

The server will start on http://localhost:5000

## Data Storage

Uses simple JSON file storage (data.json) for persistence.
"""

    def _generate_start_script(self) -> str:
        """生成启动脚本"""
        return """#!/bin/bash
# Backend start script

echo "Starting backend server..."

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# Run server
python app.py
"""

    async def _fix_bug(self, task: Task, backend_dir: Path) -> Dict[str, Any]:
        """
        修复Bug

        Args:
            task: 修复任务
            backend_dir: 后端目录

        Returns:
            修复结果
        """
        logger.info(f"Fixing bug: {task.title}")

        bug_report = task.metadata.get("bug_report", {})
        fix_suggestion = task.metadata.get("fix_suggestion", "")

        # 读取app.py
        app_file = backend_dir / "app.py"
        if not app_file.exists():
            raise FileNotFoundError(f"App file not found: {app_file}")

        with open(app_file, 'r', encoding='utf-8') as f:
            original_code = f.read()

        # 使用LLM应用修复
        prompt = f"""
Apply this bug fix to the code:

Original Code:
```python
{original_code}
```

Bug Report:
{bug_report.get('error_message', 'Unknown error')}

Fix Suggestion:
{fix_suggestion}

Return the COMPLETE fixed code (entire file), no explanations.
"""

        fixed_code = await self.llm_client.generate_code(
            description=prompt,
            language="python",
            context=None
        )

        # 清理代码块标记
        if "```python" in fixed_code:
            fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
        elif "```" in fixed_code:
            fixed_code = fixed_code.split("```")[1].split("```")[0].strip()

        # 写入修复后的代码
        if fixed_code and len(fixed_code) > 100:
            with open(app_file, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            logger.info(f"Bug fixed in {app_file}")

            return {
                "status": "success",
                "fixed_file": str(app_file),
                "bug": bug_report.get('test_name', 'unknown')
            }
        else:
            logger.warning("Fix generation failed, code too short")
            return {
                "status": "failed",
                "error": "Generated fix was invalid"
            }
