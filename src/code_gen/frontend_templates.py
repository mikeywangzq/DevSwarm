"""
多框架前端代码生成模板
Multi-Framework Frontend Code Generation Templates

本模块提供多种前端框架的代码生成模板。
支持根据API契约自动生成不同框架的前端代码。

支持的前端框架:
    - Vanilla JS + HTML + CSS (默认)
    - React
    - Vue 3

主要功能:
    - 根据API契约生成UI组件
    - 生成API调用逻辑
    - 生成状态管理代码
    - 生成配置文件

使用方式:
    >>> from src.code_gen.frontend_templates import generate_react_frontend
    >>> files = generate_react_frontend(api_contract)
    >>> # 或使用统一接口
    >>> files = generate_frontend(api_contract, framework='react')
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def _validate_api_contract(api_contract: Dict[str, Any]) -> None:
    """
    验证API契约格式

    Args:
        api_contract: API契约字典

    Raises:
        ValueError: 如果契约格式不正确
    """
    if not isinstance(api_contract, dict):
        raise ValueError("api_contract must be a dictionary")

    endpoints = api_contract.get('endpoints', [])
    if not isinstance(endpoints, list):
        raise ValueError("api_contract.endpoints must be a list")

    # 验证每个endpoint的基本结构
    for i, ep in enumerate(endpoints):
        if not isinstance(ep, dict):
            logger.warning(f"Endpoint {i} is not a dictionary, skipping validation")
            continue

        if 'method' not in ep:
            logger.warning(f"Endpoint {i} missing 'method' field")
        if 'path' not in ep:
            logger.warning(f"Endpoint {i} missing 'path' field")


def generate_vanilla_frontend(api_contract: Dict[str, Any]) -> Dict[str, str]:
    """
    生成Vanilla JS前端代码（默认实现，已存在）

    Args:
        api_contract (Dict[str, Any]): API契约字典

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射
    """
    # 验证API契约格式
    _validate_api_contract(api_contract)

    # 这个是现有的实现，保持不变
    endpoints = api_contract.get('endpoints', [])
    base_url = api_contract.get('base_url', 'http://localhost:5000')

    # 简化的Vanilla JS实现
    html_content = _generate_vanilla_html(endpoints, base_url)
    js_content = _generate_vanilla_js(endpoints, base_url)
    css_content = _generate_vanilla_css()

    return {
        'index.html': html_content,
        'app.js': js_content,
        'style.css': css_content,
        'README.md': _generate_vanilla_readme(base_url)
    }


def generate_react_frontend(api_contract: Dict[str, Any]) -> Dict[str, str]:
    """
    生成React前端代码

    Args:
        api_contract (Dict[str, Any]): API契约字典

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射
    """
    # 验证API契约格式
    _validate_api_contract(api_contract)

    endpoints = api_contract.get('endpoints', [])
    base_url = api_contract.get('base_url', 'http://localhost:5000')

    # 生成React组件
    app_component = _generate_react_app(endpoints, base_url)
    api_service = _generate_react_api_service(endpoints, base_url)
    package_json = _generate_react_package_json()

    return {
        'src/App.jsx': app_component,
        'src/services/api.js': api_service,
        'src/index.js': _generate_react_index(),
        'src/App.css': _generate_react_css(),
        'public/index.html': _generate_react_html(),
        'package.json': package_json,
        'README.md': _generate_react_readme(base_url),
        '.gitignore': 'node_modules/\nbuild/\n.env\n',
        '.env.example': f'REACT_APP_API_URL={base_url}\n'
    }


def generate_vue_frontend(api_contract: Dict[str, Any]) -> Dict[str, str]:
    """
    生成Vue 3前端代码

    Args:
        api_contract (Dict[str, Any]): API契约字典

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射
    """
    # 验证API契约格式
    _validate_api_contract(api_contract)

    endpoints = api_contract.get('endpoints', [])
    base_url = api_contract.get('base_url', 'http://localhost:5000')

    # 生成Vue组件
    app_component = _generate_vue_app(endpoints, base_url)
    api_service = _generate_vue_api_service(endpoints, base_url)
    package_json = _generate_vue_package_json()

    return {
        'src/App.vue': app_component,
        'src/services/api.js': api_service,
        'src/main.js': _generate_vue_main(),
        'public/index.html': _generate_vue_html(),
        'package.json': package_json,
        'README.md': _generate_vue_readme(base_url),
        '.gitignore': 'node_modules/\ndist/\n.env\n',
        '.env.example': f'VUE_APP_API_URL={base_url}\n'
    }


# ========== React Generator Functions ==========

def _generate_react_app(endpoints: List[Dict], base_url: str) -> str:
    """生成React主组件"""
    return f'''import React, {{ useState, useEffect }} from 'react';
import {{ getItems, createItem, deleteItem }} from './services/api';
import './App.css';

function App() {{
  const [items, setItems] = useState([]);
  const [newItem, setNewItem] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {{
    loadItems();
  }}, []);

  const loadItems = async () => {{
    try {{
      setLoading(true);
      setError(null);
      const data = await getItems();
      setItems(data.items || []);
    }} catch (err) {{
      setError('Failed to load items: ' + err.message);
      console.error(err);
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleAddItem = async (e) => {{
    e.preventDefault();
    if (!newItem.trim()) return;

    try {{
      setLoading(true);
      setError(null);
      await createItem({{ title: newItem }});
      setNewItem('');
      await loadItems();
    }} catch (err) {{
      setError('Failed to add item: ' + err.message);
      console.error(err);
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleDeleteItem = async (id) => {{
    try {{
      setLoading(true);
      setError(null);
      await deleteItem(id);
      await loadItems();
    }} catch (err) {{
      setError('Failed to delete item: ' + err.message);
      console.error(err);
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <div className="App">
      <div className="container">
        <h1>My Application</h1>

        {{error && (
          <div className="error-message">
            {{error}}
          </div>
        )}}

        <form onSubmit={{handleAddItem}} className="add-form">
          <input
            type="text"
            value={{newItem}}
            onChange={{(e) => setNewItem(e.target.value)}}
            placeholder="Enter new item..."
            disabled={{loading}}
          />
          <button type="submit" disabled={{loading}}>
            {{loading ? 'Loading...' : 'Add Item'}}
          </button>
        </form>

        <div className="items-list">
          {{items.length === 0 ? (
            <p className="empty-message">No items yet. Add one above!</p>
          ) : (
            items.map((item) => (
              <div key={{item.id}} className="item">
                <span className="item-title">{{item.title}}</span>
                <button
                  className="delete-btn"
                  onClick={{() => handleDeleteItem(item.id)}}
                  disabled={{loading}}
                >
                  Delete
                </button>
              </div>
            ))
          )}}
        </div>
      </div>
    </div>
  );
}}

export default App;
'''


def _generate_react_api_service(endpoints: List[Dict], base_url: str) -> str:
    """生成React API服务"""
    return f'''const API_URL = process.env.REACT_APP_API_URL || '{base_url}';

async function handleResponse(response) {{
  if (!response.ok) {{
    const error = await response.json().catch(() => ({{}}));
    throw new Error(error.message || `HTTP error! status: ${{response.status}}`);
  }}
  return response.json();
}}

export async function getItems() {{
  const response = await fetch(`${{API_URL}}/api/items`);
  return handleResponse(response);
}}

export async function createItem(data) {{
  const response = await fetch(`${{API_URL}}/api/items`, {{
    method: 'POST',
    headers: {{
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify(data),
  }});
  return handleResponse(response);
}}

export async function updateItem(id, data) {{
  const response = await fetch(`${{API_URL}}/api/items/${{id}}`, {{
    method: 'PUT',
    headers: {{
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify(data),
  }});
  return handleResponse(response);
}}

export async function deleteItem(id) {{
  const response = await fetch(`${{API_URL}}/api/items/${{id}}`, {{
    method: 'DELETE',
  }});
  return handleResponse(response);
}}
'''


def _generate_react_index() -> str:
    """生成React入口文件"""
    return '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
'''


def _generate_react_css() -> str:
    """生成React样式"""
    return '''* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

.App {
  max-width: 800px;
  margin: 0 auto;
}

.container {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

h1 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.error-message {
  background: #fee;
  border: 1px solid #fcc;
  color: #c33;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.add-form {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.add-form input {
  flex: 1;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
}

.add-form input:focus {
  outline: none;
  border-color: #667eea;
}

.add-form button {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}

.add-form button:hover:not(:disabled) {
  background: #5568d3;
}

.add-form button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-message {
  text-align: center;
  color: #999;
  padding: 40px 0;
}

.item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.item-title {
  flex: 1;
  font-size: 16px;
  color: #333;
}

.delete-btn {
  padding: 8px 16px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.3s;
}

.delete-btn:hover:not(:disabled) {
  background: #c82333;
}

.delete-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}
'''


def _generate_react_html() -> str:
    """生成React HTML模板"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>React App</title>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
'''


def _generate_react_package_json() -> str:
    """生成React package.json"""
    return '''{
  "name": "react-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
'''


def _generate_react_readme(base_url: str) -> str:
    """生成React README"""
    return f'''# React Frontend

Auto-generated React application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API URL
```

3. Run the application:

Development:
```bash
npm start
```

The app will start at: http://localhost:3000

Production build:
```bash
npm run build
```

## Features

- React 18 with Hooks
- Modern ES6+ JavaScript
- Responsive design
- Error handling
- Loading states
- Environment configuration

## API Integration

Backend API: {base_url}
'''


# ========== Vue Generator Functions ==========

def _generate_vue_app(endpoints: List[Dict], base_url: str) -> str:
    """生成Vue主组件"""
    return f'''<template>
  <div id="app">
    <div class="container">
      <h1>My Application</h1>

      <div v-if="error" class="error-message">
        {{{{ error }}}}
      </div>

      <form @submit.prevent="handleAddItem" class="add-form">
        <input
          v-model="newItem"
          type="text"
          placeholder="Enter new item..."
          :disabled="loading"
        />
        <button type="submit" :disabled="loading">
          {{{{ loading ? 'Loading...' : 'Add Item' }}}}
        </button>
      </form>

      <div class="items-list">
        <p v-if="items.length === 0" class="empty-message">
          No items yet. Add one above!
        </p>
        <div
          v-for="item in items"
          :key="item.id"
          class="item"
        >
          <span class="item-title">{{{{ item.title }}}}</span>
          <button
            class="delete-btn"
            @click="handleDeleteItem(item.id)"
            :disabled="loading"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {{ ref, onMounted }} from 'vue';
import {{ getItems, createItem, deleteItem }} from './services/api';

export default {{
  name: 'App',
  setup() {{
    const items = ref([]);
    const newItem = ref('');
    const loading = ref(false);
    const error = ref(null);

    const loadItems = async () => {{
      try {{
        loading.value = true;
        error.value = null;
        const data = await getItems();
        items.value = data.items || [];
      }} catch (err) {{
        error.value = 'Failed to load items: ' + err.message;
        console.error(err);
      }} finally {{
        loading.value = false;
      }}
    }};

    const handleAddItem = async () => {{
      if (!newItem.value.trim()) return;

      try {{
        loading.value = true;
        error.value = null;
        await createItem({{ title: newItem.value }});
        newItem.value = '';
        await loadItems();
      }} catch (err) {{
        error.value = 'Failed to add item: ' + err.message;
        console.error(err);
      }} finally {{
        loading.value = false;
      }}
    }};

    const handleDeleteItem = async (id) => {{
      try {{
        loading.value = true;
        error.value = null;
        await deleteItem(id);
        await loadItems();
      }} catch (err) {{
        error.value = 'Failed to delete item: ' + err.message;
        console.error(err);
      }} finally {{
        loading.value = false;
      }}
    }};

    onMounted(() => {{
      loadItems();
    }});

    return {{
      items,
      newItem,
      loading,
      error,
      handleAddItem,
      handleDeleteItem
    }};
  }}
}};
</script>

<style>
* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}}

#app {{
  max-width: 800px;
  margin: 0 auto;
}}

.container {{
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}}

h1 {{
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}}

.error-message {{
  background: #fee;
  border: 1px solid #fcc;
  color: #c33;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}}

.add-form {{
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}}

.add-form input {{
  flex: 1;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
}}

.add-form input:focus {{
  outline: none;
  border-color: #667eea;
}}

.add-form button {{
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}}

.add-form button:hover:not(:disabled) {{
  background: #5568d3;
}}

.add-form button:disabled {{
  background: #ccc;
  cursor: not-allowed;
}}

.items-list {{
  display: flex;
  flex-direction: column;
  gap: 10px;
}}

.empty-message {{
  text-align: center;
  color: #999;
  padding: 40px 0;
}}

.item {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}}

.item-title {{
  flex: 1;
  font-size: 16px;
  color: #333;
}}

.delete-btn {{
  padding: 8px 16px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.3s;
}}

.delete-btn:hover:not(:disabled) {{
  background: #c82333;
}}

.delete-btn:disabled {{
  background: #ccc;
  cursor: not-allowed;
}}
</style>
'''


def _generate_vue_api_service(endpoints: List[Dict], base_url: str) -> str:
    """生成Vue API服务"""
    return f'''const API_URL = import.meta.env.VUE_APP_API_URL || '{base_url}';

async function handleResponse(response) {{
  if (!response.ok) {{
    const error = await response.json().catch(() => ({{}}));
    throw new Error(error.message || `HTTP error! status: ${{response.status}}`);
  }}
  return response.json();
}}

export async function getItems() {{
  const response = await fetch(`${{API_URL}}/api/items`);
  return handleResponse(response);
}}

export async function createItem(data) {{
  const response = await fetch(`${{API_URL}}/api/items`, {{
    method: 'POST',
    headers: {{
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify(data),
  }});
  return handleResponse(response);
}}

export async function updateItem(id, data) {{
  const response = await fetch(`${{API_URL}}/api/items/${{id}}`, {{
    method: 'PUT',
    headers: {{
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify(data),
  }});
  return handleResponse(response);
}}

export async function deleteItem(id) {{
  const response = await fetch(`${{API_URL}}/api/items/${{id}}`, {{
    method: 'DELETE',
  }});
  return handleResponse(response);
}}
'''


def _generate_vue_main() -> str:
    """生成Vue入口文件"""
    return '''import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');
'''


def _generate_vue_html() -> str:
    """生成Vue HTML模板"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vue App</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
'''


def _generate_vue_package_json() -> str:
    """生成Vue package.json"""
    return'''{
  "name": "vue-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.3.4"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.3.4",
    "vite": "^4.4.9"
  }
}
'''


def _generate_vue_readme(base_url: str) -> str:
    """生成Vue README"""
    return f'''# Vue Frontend

Auto-generated Vue 3 application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API URL
```

3. Run the application:

Development:
```bash
npm run dev
```

The app will start at: http://localhost:5173

Production build:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Features

- Vue 3 with Composition API
- Vite for fast development
- Reactive state management
- Modern ES6+ JavaScript
- Responsive design
- Error handling
- Loading states

## API Integration

Backend API: {base_url}
'''


# ========== Vanilla JS Helper Functions ==========

def _generate_vanilla_html(endpoints: List[Dict], base_url: str) -> str:
    """生成Vanilla HTML"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Application</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>My Application</h1>
        <div id="error-message" class="error-message hidden"></div>
        <form id="add-form" class="add-form">
            <input type="text" id="item-input" placeholder="Enter new item..." />
            <button type="submit">Add Item</button>
        </form>
        <div id="items-list" class="items-list"></div>
    </div>
    <script src="app.js"></script>
</body>
</html>
'''


def _generate_vanilla_js(endpoints: List[Dict], base_url: str) -> str:
    """生成Vanilla JS"""
    return f'''const API_URL = '{base_url}';

async function getItems() {{
    const response = await fetch(`${{API_URL}}/api/items`);
    return response.json();
}}

async function createItem(data) {{
    const response = await fetch(`${{API_URL}}/api/items`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(data)
    }});
    return response.json();
}}

async function deleteItem(id) {{
    await fetch(`${{API_URL}}/api/items/${{id}}`, {{ method: 'DELETE' }});
}}

async function loadItems() {{
    try {{
        const data = await getItems();
        const list = document.getElementById('items-list');
        list.innerHTML = data.items.map(item => `
            <div class="item">
                <span>${{item.title}}</span>
                <button onclick="handleDelete('${{item.id}}')">Delete</button>
            </div>
        `).join('');
    }} catch (error) {{
        console.error(error);
    }}
}}

document.getElementById('add-form').addEventListener('submit', async (e) => {{
    e.preventDefault();
    const input = document.getElementById('item-input');
    await createItem({{ title: input.value }});
    input.value = '';
    await loadItems();
}});

async function handleDelete(id) {{
    await deleteItem(id);
    await loadItems();
}}

loadItems();
'''


def _generate_vanilla_css() -> str:
    """生成Vanilla CSS"""
    return '''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

h1 {
    text-align: center;
    margin-bottom: 20px;
}

.add-form {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

.add-form input {
    flex: 1;
    padding: 12px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 16px;
}

.add-form button {
    padding: 12px 24px;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}

.items-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.item {
    display: flex;
    justify-content: space-between;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
}

.hidden {
    display: none;
}
'''


def _generate_vanilla_readme(base_url: str) -> str:
    """生成Vanilla README"""
    return f'''# Vanilla JS Frontend

Simple HTML/CSS/JavaScript frontend.

## Running

Open `index.html` in your browser or use a local server:

```bash
python -m http.server 8000
```

Then visit: http://localhost:8000

API Backend: {base_url}
'''


# ========== Unified Interface ==========

def generate_frontend(api_contract: Dict[str, Any], framework: str = 'vanilla') -> Dict[str, str]:
    """
    统一的前端代码生成接口

    Args:
        api_contract (Dict[str, Any]): API契约字典
        framework (str): 前端框架，可选值:
            - 'vanilla' (默认) - Vanilla JS
            - 'react' - React
            - 'vue' - Vue 3

    Returns:
        Dict[str, str]: 文件路径到文件内容的映射

    Example:
        >>> api_contract = {...}
        >>> files = generate_frontend(api_contract, framework='react')
        >>> for path, content in files.items():
        ...     write_file(path, content)
    """
    framework = framework.lower()

    if framework in ['vanilla', 'vanillajs', 'html']:
        return generate_vanilla_frontend(api_contract)
    elif framework == 'react':
        return generate_react_frontend(api_contract)
    elif framework in ['vue', 'vue3']:
        return generate_vue_frontend(api_contract)
    else:
        logger.warning(f"Unsupported framework: {framework}, falling back to Vanilla JS")
        return generate_vanilla_frontend(api_contract)
