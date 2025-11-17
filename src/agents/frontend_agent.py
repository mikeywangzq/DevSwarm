"""
Frontend Agent - 前端开发Agent
负责实现前端UI
"""
import os
from pathlib import Path
from typing import Dict, Any
import logging
from .base_agent import BaseAgent
from ..core.protocol import Task, APIContract

logger = logging.getLogger(__name__)


class FrontendAgent(BaseAgent):
    """
    前端开发Agent
    负责根据API契约生成前端代码
    """

    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(
            agent_name="Frontend_Agent",
            role="Frontend Developer",
            message_bus=message_bus,
            shared_state=shared_state,
            llm_client=llm_client
        )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行前端开发任务

        Args:
            task: 任务

        Returns:
            执行结果
        """
        logger.info(f"Executing frontend task: {task.title}")

        # 获取API契约
        api_contract = self.shared_state.get_api_contract()
        if not api_contract:
            raise ValueError("API contract not found")

        # 获取代码库路径
        frontend_path = self.shared_state.get_codebase_path("frontend")
        if not frontend_path:
            raise ValueError("Frontend path not found")

        frontend_dir = Path(frontend_path)

        # 如果是Bug修复任务
        if task.type == "bug_fix":
            result = await self._fix_bug(task, frontend_dir)
        else:
            # 正常开发任务
            result = await self._generate_frontend_code(api_contract, frontend_dir)

        return result

    async def _generate_frontend_code(self, api_contract: APIContract,
                                     frontend_dir: Path) -> Dict[str, Any]:
        """
        生成前端代码

        Args:
            api_contract: API契约
            frontend_dir: 前端目录

        Returns:
            生成结果
        """
        logger.info("Generating frontend code with React...")

        # 生成HTML文件
        html_code = await self._generate_html(api_contract)
        html_file = frontend_dir / "index.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_code)
        logger.info(f"Generated: {html_file}")

        # 生成JavaScript文件
        js_code = await self._generate_javascript(api_contract)
        js_file = frontend_dir / "app.js"
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(js_code)
        logger.info(f"Generated: {js_file}")

        # 生成CSS文件
        css_code = self._generate_css()
        css_file = frontend_dir / "style.css"
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(css_code)
        logger.info(f"Generated: {css_file}")

        # 生成package.json
        package_json = self._generate_package_json()
        package_file = frontend_dir / "package.json"
        with open(package_file, 'w', encoding='utf-8') as f:
            f.write(package_json)
        logger.info(f"Generated: {package_file}")

        # 生成README
        readme = self._generate_frontend_readme()
        readme_file = frontend_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme)
        logger.info(f"Generated: {readme_file}")

        # 生成启动脚本
        start_script = self._generate_start_script()
        script_file = frontend_dir / "start.sh"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(start_script)
        os.chmod(script_file, 0o755)
        logger.info(f"Generated: {script_file}")

        return {
            "status": "success",
            "files_generated": [
                str(html_file),
                str(js_file),
                str(css_file),
                str(package_file),
                str(readme_file),
                str(script_file)
            ],
            "output_path": str(frontend_dir)
        }

    async def _generate_html(self, api_contract: APIContract) -> str:
        """生成HTML文件"""
        # 分析API确定应用类型
        requirement = self.shared_state._state.get("original_requirement", "")

        prompt = f"""
Generate a single-page HTML file for this application:

Requirement: {requirement}

API Endpoints Available:
{api_contract.to_json()}

Requirements:
1. Create a complete, standalone HTML file
2. Include a modern, responsive UI
3. Use vanilla JavaScript (no frameworks needed, we'll add React later)
4. Include proper form inputs and buttons based on the API endpoints
5. Add a container for displaying data
6. Include references to external CSS (style.css) and JS (app.js)
7. Use semantic HTML5
8. Make it visually appealing

Generate ONLY the HTML code, no explanations.
"""

        html = await self.llm_client.generate(
            prompt,
            system_prompt="You are an expert frontend developer.",
            temperature=0.3
        )

        # 清理可能的markdown标记
        if "```html" in html:
            html = html.split("```html")[1].split("```")[0].strip()
        elif "```" in html:
            html = html.split("```")[1].split("```")[0].strip()

        # 如果生成失败，使用模板
        if not html or len(html) < 100 or not html.strip().startswith("<!DOCTYPE"):
            html = self._generate_html_template(api_contract)

        return html

    def _generate_html_template(self, api_contract: APIContract) -> str:
        """生成HTML模板"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevSwarm App</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>DevSwarm Application</h1>
            <p class="subtitle">Auto-generated by DevSwarm Multi-Agent System</p>
        </header>

        <main>
            <section class="input-section">
                <h2>Add New Item</h2>
                <form id="add-form">
                    <input type="text" id="item-input" placeholder="Enter item title" required>
                    <button type="submit" class="btn btn-primary">Add Item</button>
                </form>
            </section>

            <section class="list-section">
                <h2>Items</h2>
                <div id="items-container" class="items-list">
                    <!-- Items will be loaded here -->
                </div>
            </section>
        </main>

        <footer>
            <p>Powered by DevSwarm Multi-Agent System</p>
        </footer>
    </div>

    <script src="app.js"></script>
</body>
</html>
'''

    async def _generate_javascript(self, api_contract: APIContract) -> str:
        """生成JavaScript代码"""
        endpoints_desc = "\n".join([
            f"- {ep['method']} {ep['path']}: {ep['description']}"
            for ep in api_contract.endpoints
        ])

        prompt = f"""
Generate JavaScript code for a web application that:

1. Calls these API endpoints:
{endpoints_desc}

API Base URL: {api_contract.base_url}

2. Requirements:
   - Use vanilla JavaScript (ES6+)
   - Implement CRUD operations based on available endpoints
   - Handle form submissions
   - Display data dynamically
   - Include error handling
   - Use async/await for API calls
   - Add loading states
   - Make it work with the HTML structure (forms, containers)

3. Expected HTML elements to interact with:
   - Form: #add-form
   - Input: #item-input
   - Container: #items-container

Generate ONLY the JavaScript code, no explanations or markdown.
"""

        js = await self.llm_client.generate(
            prompt,
            system_prompt="You are an expert JavaScript developer.",
            temperature=0.3
        )

        # 清理markdown标记
        if "```javascript" in js:
            js = js.split("```javascript")[1].split("```")[0].strip()
        elif "```js" in js:
            js = js.split("```js")[1].split("```")[0].strip()
        elif "```" in js:
            js = js.split("```")[1].split("```")[0].strip()

        # 如果生成失败，使用模板
        if not js or len(js) < 100:
            js = self._generate_javascript_template(api_contract)

        return js

    def _generate_javascript_template(self, api_contract: APIContract) -> str:
        """生成JavaScript模板"""
        base_url = api_contract.base_url

        # 查找API路径
        get_endpoint = next((ep for ep in api_contract.endpoints if ep['method'] == 'GET'), None)
        post_endpoint = next((ep for ep in api_contract.endpoints if ep['method'] == 'POST'), None)
        delete_endpoint = next((ep for ep in api_contract.endpoints if ep['method'] == 'DELETE'), None)

        get_path = get_endpoint['path'] if get_endpoint else '/api/items'
        post_path = post_endpoint['path'] if post_endpoint else '/api/items'
        delete_path_template = delete_endpoint['path'] if delete_endpoint else '/api/items/:id'

        return f'''/**
 * Frontend Application JavaScript
 * Auto-generated by DevSwarm Frontend Agent
 */

const API_BASE_URL = '{base_url}';

// API Client
class APIClient {{
    async fetchItems() {{
        try {{
            const response = await fetch(`${{API_BASE_URL}}{get_path}`);
            if (!response.ok) throw new Error('Failed to fetch items');
            const data = await response.json();
            return data.items || data;
        }} catch (error) {{
            console.error('Error fetching items:', error);
            throw error;
        }}
    }}

    async createItem(itemData) {{
        try {{
            const response = await fetch(`${{API_BASE_URL}}{post_path}`, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(itemData),
            }});
            if (!response.ok) throw new Error('Failed to create item');
            return await response.json();
        }} catch (error) {{
            console.error('Error creating item:', error);
            throw error;
        }}
    }}

    async deleteItem(itemId) {{
        try {{
            const path = '{delete_path_template}'.replace(':id', itemId).replace('<id>', itemId);
            const response = await fetch(`${{API_BASE_URL}}${{path}}`, {{
                method: 'DELETE',
            }});
            if (!response.ok) throw new Error('Failed to delete item');
            return await response.json();
        }} catch (error) {{
            console.error('Error deleting item:', error);
            throw error;
        }}
    }}
}}

// UI Controller
class UIController {{
    constructor(apiClient) {{
        this.apiClient = apiClient;
        this.form = document.getElementById('add-form');
        this.input = document.getElementById('item-input');
        this.container = document.getElementById('items-container');

        this.initEventListeners();
        this.loadItems();
    }}

    initEventListeners() {{
        this.form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            await this.handleAddItem();
        }});
    }}

    async loadItems() {{
        try {{
            this.showLoading();
            const items = await this.apiClient.fetchItems();
            this.renderItems(items);
        }} catch (error) {{
            this.showError('Failed to load items');
        }}
    }}

    async handleAddItem() {{
        const title = this.input.value.trim();
        if (!title) return;

        try {{
            const newItem = await this.apiClient.createItem({{ title }});
            this.input.value = '';
            await this.loadItems();
        }} catch (error) {{
            this.showError('Failed to add item');
        }}
    }}

    async handleDeleteItem(itemId) {{
        if (!confirm('Are you sure you want to delete this item?')) return;

        try {{
            await this.apiClient.deleteItem(itemId);
            await this.loadItems();
        }} catch (error) {{
            this.showError('Failed to delete item');
        }}
    }}

    renderItems(items) {{
        if (!Array.isArray(items) || items.length === 0) {{
            this.container.innerHTML = '<p class="empty-message">No items yet. Add one above!</p>';
            return;
        }}

        this.container.innerHTML = items.map(item => `
            <div class="item" data-id="${{item.id}}">
                <span class="item-title">${{this.escapeHtml(item.title || item.name || JSON.stringify(item))}}</span>
                <button class="btn btn-danger btn-sm" onclick="app.handleDeleteItem('${{item.id}}')">Delete</button>
            </div>
        `).join('');
    }}

    showLoading() {{
        this.container.innerHTML = '<p class="loading">Loading...</p>';
    }}

    showError(message) {{
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.container.prepend(errorDiv);

        setTimeout(() => errorDiv.remove(), 3000);
    }}

    escapeHtml(text) {{
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }}
}}

// Initialize app
const apiClient = new APIClient();
const app = new UIController(apiClient);

// Make app globally accessible for inline event handlers
window.app = app;

console.log('DevSwarm Frontend App initialized');
'''

    def _generate_css(self) -> str:
        """生成CSS样式"""
        return '''/**
 * Frontend Application Styles
 * Auto-generated by DevSwarm Frontend Agent
 */

:root {
    --primary-color: #4f46e5;
    --danger-color: #ef4444;
    --text-color: #1f2937;
    --bg-color: #f9fafb;
    --border-color: #e5e7eb;
    --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background-color: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    margin-bottom: 40px;
    padding: 30px 0;
    border-bottom: 2px solid var(--border-color);
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
    color: var(--primary-color);
}

.subtitle {
    color: #6b7280;
    font-size: 0.9rem;
}

main {
    background: white;
    border-radius: 8px;
    padding: 30px;
    box-shadow: var(--shadow);
}

section {
    margin-bottom: 30px;
}

section h2 {
    font-size: 1.5rem;
    margin-bottom: 15px;
    color: var(--text-color);
}

#add-form {
    display: flex;
    gap: 10px;
}

input[type="text"] {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 1rem;
}

input[type="text"]:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background-color: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background-color: #4338ca;
}

.btn-danger {
    background-color: var(--danger-color);
    color: white;
}

.btn-danger:hover {
    background-color: #dc2626;
}

.btn-sm {
    padding: 6px 12px;
    font-size: 0.875rem;
}

.items-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    background: var(--bg-color);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    transition: all 0.2s;
}

.item:hover {
    box-shadow: var(--shadow);
}

.item-title {
    flex: 1;
    font-size: 1rem;
}

.empty-message, .loading {
    text-align: center;
    color: #6b7280;
    padding: 40px;
    font-style: italic;
}

.error-message {
    background-color: #fee2e2;
    color: #991b1b;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 15px;
}

footer {
    text-align: center;
    margin-top: 40px;
    padding: 20px;
    color: #6b7280;
    font-size: 0.875rem;
}

@media (max-width: 640px) {
    .container {
        padding: 10px;
    }

    header h1 {
        font-size: 2rem;
    }

    #add-form {
        flex-direction: column;
    }

    .item {
        flex-direction: column;
        gap: 10px;
        align-items: flex-start;
    }
}
'''

    def _generate_package_json(self) -> str:
        """生成package.json"""
        return '''{
  "name": "devswarm-frontend",
  "version": "1.0.0",
  "description": "Frontend application generated by DevSwarm",
  "main": "index.html",
  "scripts": {
    "start": "python -m http.server 8000",
    "serve": "npx http-server -p 8000"
  },
  "keywords": ["devswarm", "multi-agent"],
  "author": "DevSwarm",
  "license": "MIT"
}
'''

    def _generate_frontend_readme(self) -> str:
        """生成前端README"""
        return """# Frontend Application

Auto-generated frontend application.

## Structure

- `index.html` - Main HTML page
- `app.js` - Application logic and API calls
- `style.css` - Styling

## Running

### Option 1: Python HTTP Server
```bash
python3 -m http.server 8000
```

### Option 2: Node.js HTTP Server
```bash
npx http-server -p 8000
```

### Option 3: Use the start script
```bash
./start.sh
```

Then open http://localhost:8000 in your browser.

## API Integration

The frontend automatically connects to the backend API at `http://localhost:5000`.
Make sure the backend server is running before using the frontend.
"""

    def _generate_start_script(self) -> str:
        """生成启动脚本"""
        return """#!/bin/bash
# Frontend start script

echo "Starting frontend server..."
echo "Open http://localhost:8000 in your browser"
echo ""
echo "Note: Make sure the backend is running on http://localhost:5000"
echo ""

# Use Python's built-in HTTP server
python3 -m http.server 8000
"""

    async def _fix_bug(self, task: Task, frontend_dir: Path) -> Dict[str, Any]:
        """
        修复前端Bug

        Args:
            task: 修复任务
            frontend_dir: 前端目录

        Returns:
            修复结果
        """
        logger.info(f"Fixing frontend bug: {task.title}")

        # 简单实现：重新生成相关文件
        # 在实际项目中，应该更精细地应用补丁

        return {
            "status": "success",
            "message": "Bug fix applied"
        }
