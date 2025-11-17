"""
Web用户界面应用
Web UI Application Module

本模块实现了DevSwarm系统的Web用户界面，基于Flask框架。
用户通过Web界面提交需求、监控项目进度、查看生成的代码。

主要功能:
    1. **需求提交**: 用户通过Web表单提交需求
    2. **进度监控**: 实时显示项目和任务状态
    3. **日志查看**: 展示系统运行日志和Agent活动
    4. **结果下载**: 提供生成代码的下载链接

路由说明:
    - /: 主页，显示提交表单
    - /api/generate: 接收需求并启动项目生成
    - /api/status: 查询项目状态
    - /api/logs: 获取系统日志

系统初始化:
    应用启动时会初始化所有核心组件（消息总线、共享状态、LLM客户端）
    和所有Agent（PM、Backend、Frontend、QA），并启动消息总线。

使用方式:
    python src/web/app.py
    然后访问: http://localhost:3000
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.message_bus import MessageBus
from src.core.shared_state import SharedState
from src.llm.llm_client import get_llm_client, LLMProvider
from src.agents.pm_agent import PMAgent
from src.agents.backend_agent import BackendAgent
from src.agents.frontend_agent import FrontendAgent
from src.agents.qa_agent import QAAgent
from src.utils.websocket_logger import setup_websocket_logging
from src.utils.performance import PerformanceMetrics, BenchmarkSuite
from src.utils.security_scanner import SecurityScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global system components
message_bus = None
shared_state = None
pm_agent = None
backend_agent = None
frontend_agent = None
qa_agent = None
event_loop = None


def initialize_system():
    """初始化多Agent系统"""
    global message_bus, shared_state, pm_agent, backend_agent, frontend_agent, qa_agent, event_loop

    logger.info("Initializing DevSwarm Multi-Agent System...")

    # 创建事件循环
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)

    # 初始化核心组件
    message_bus = MessageBus()
    shared_state = SharedState(workspace_root="./workspace")

    # 初始化LLM客户端
    llm_client = get_llm_client(provider=LLMProvider.OPENAI)

    # 初始化Agents
    pm_agent = PMAgent(message_bus, shared_state, llm_client)
    backend_agent = BackendAgent(message_bus, shared_state, llm_client)
    frontend_agent = FrontendAgent(message_bus, shared_state, llm_client)
    qa_agent = QAAgent(message_bus, shared_state, llm_client)

    # 启动消息总线
    event_loop.run_until_complete(message_bus.start())

    # 启动所有Agents
    pm_agent.start()
    backend_agent.start()
    frontend_agent.start()
    qa_agent.start()

    # 设置WebSocket日志处理器
    setup_websocket_logging(socketio, min_level=logging.INFO)

    logger.info("System initialized successfully!")


# ============= WebSocket Event Handlers =============

@socketio.on('connect', namespace='/logs')
def handle_connect():
    """
    处理客户端连接
    当用户打开Web页面时建立WebSocket连接
    """
    logger.info("Client connected to log stream")
    emit('connection_response', {'data': 'Connected to DevSwarm log stream'})


@socketio.on('disconnect', namespace='/logs')
def handle_disconnect():
    """
    处理客户端断开连接
    当用户关闭页面时断开WebSocket连接
    """
    logger.info("Client disconnected from log stream")


@socketio.on('request_history', namespace='/logs')
def handle_history_request(data):
    """
    客户端请求历史日志
    客户端可以请求最近的N条日志记录
    """
    limit = data.get('limit', 100)
    logger.info(f"Client requested last {limit} log entries")
    # 注意：历史日志需要单独存储，当前实现仅支持实时流
    emit('history_response', {
        'message': 'Historical logs not yet implemented',
        'logs': []
    })


# ============= HTTP Routes =============

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/submit', methods=['POST'])
def submit_requirement():
    """
    提交需求并启动项目
    """
    try:
        data = request.get_json()
        requirement = data.get('requirement', '').strip()

        if not requirement:
            return jsonify({
                'success': False,
                'error': 'Requirement cannot be empty'
            }), 400

        logger.info(f"Received requirement: {requirement}")

        # 启动项目（异步）
        project_id = event_loop.run_until_complete(
            pm_agent.start_project(requirement)
        )

        return jsonify({
            'success': True,
            'project_id': project_id,
            'message': 'Project started successfully!'
        })

    except Exception as e:
        logger.error(f"Error submitting requirement: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """
    获取项目状态
    """
    try:
        if not pm_agent or not pm_agent.current_project_id:
            return jsonify({
                'success': False,
                'error': 'No active project'
            }), 404

        # 获取项目状态
        project_status = pm_agent.get_project_status()

        # 获取所有任务
        all_tasks = shared_state.get_all_tasks()
        tasks_info = [
            {
                'task_id': task.task_id,
                'title': task.title,
                'assigned_to': task.assigned_to,
                'status': task.status.value,
                'type': task.type
            }
            for task in all_tasks
        ]

        # 获取消息历史统计
        message_stats = message_bus.get_stats()

        return jsonify({
            'success': True,
            'project': project_status,
            'tasks': tasks_info,
            'message_stats': message_stats,
            'summary': shared_state.export_summary()
        })

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/messages', methods=['GET'])
def get_messages():
    """
    获取消息历史
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        messages = message_bus.get_message_history(limit=limit)

        messages_data = [
            {
                'message_id': msg.message_id,
                'timestamp': msg.timestamp,
                'from_agent': msg.from_agent,
                'to_agent': msg.to_agent,
                'type': msg.type.value,
                'task_id': msg.task.task_id if msg.task else None
            }
            for msg in messages
        ]

        return jsonify({
            'success': True,
            'messages': messages_data
        })

    except Exception as e:
        logger.error(f"Error getting messages: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/agents', methods=['GET'])
def get_agents_status():
    """
    获取所有Agent的状态
    """
    try:
        agents = []

        if pm_agent:
            agents.append(pm_agent.get_status())
        if backend_agent:
            agents.append(backend_agent.get_status())
        if frontend_agent:
            agents.append(frontend_agent.get_status())
        if qa_agent:
            agents.append(qa_agent.get_status())

        return jsonify({
            'success': True,
            'agents': agents
        })

    except Exception as e:
        logger.error(f"Error getting agents status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'system': 'DevSwarm Multi-Agent System',
        'message_bus_running': message_bus.is_running if message_bus else False
    })


@app.route('/api/performance', methods=['GET'])
def get_performance_metrics():
    """
    获取性能指标摘要
    返回系统运行的性能统计信息
    """
    try:
        summary = PerformanceMetrics.get_summary()
        all_metrics = PerformanceMetrics.get_all_metrics()

        return jsonify({
            'success': True,
            'summary': summary,
            'total_metrics': len(all_metrics),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/performance/export', methods=['POST'])
def export_performance_metrics():
    """
    导出性能指标到文件
    """
    try:
        data = request.get_json() or {}
        filepath = data.get('filepath', './reports/performance_report.json')

        PerformanceMetrics.export_to_file(filepath)

        return jsonify({
            'success': True,
            'message': f'Performance metrics exported to {filepath}'
        })

    except Exception as e:
        logger.error(f"Error exporting performance metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/benchmark/run', methods=['POST'])
def run_benchmark():
    """
    运行基准测试
    """
    try:
        suite = BenchmarkSuite()

        # 在事件循环中运行基准测试
        report = event_loop.run_until_complete(suite.run_all_benchmarks())

        return jsonify({
            'success': True,
            'report': report
        })

    except Exception as e:
        logger.error(f"Error running benchmark: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/security/scan', methods=['POST'])
def run_security_scan():
    """
    运行安全扫描
    扫描当前项目的所有代码文件，检测安全漏洞
    """
    try:
        if not pm_agent or not pm_agent.current_project_id:
            return jsonify({
                'success': False,
                'error': 'No active project'
            }), 404

        project_id = pm_agent.current_project_id
        project_path = Path(shared_state.workspace_root) / project_id

        if not project_path.exists():
            return jsonify({
                'success': False,
                'error': 'Project directory not found'
            }), 404

        # 运行安全扫描
        scanner = SecurityScanner()
        report = scanner.scan_project(str(project_path))

        return jsonify({
            'success': True,
            'report': report.to_dict()
        })

    except Exception as e:
        logger.error(f"Error running security scan: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/security/scan/file', methods=['POST'])
def scan_file_security():
    """
    扫描单个文件的安全问题
    """
    try:
        data = request.get_json()
        file_path = data.get('file_path', '').strip()

        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path is required'
            }), 400

        if not pm_agent or not pm_agent.current_project_id:
            return jsonify({
                'success': False,
                'error': 'No active project'
            }), 404

        from pathlib import Path
        project_id = pm_agent.current_project_id
        full_path = Path(shared_state.workspace_root) / project_id / file_path

        # 安全检查
        try:
            full_path = full_path.resolve()
            project_root = (Path(shared_state.workspace_root) / project_id).resolve()
            if not str(full_path).startswith(str(project_root)):
                return jsonify({
                    'success': False,
                    'error': 'Invalid file path'
                }), 403
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 403

        # 扫描文件
        scanner = SecurityScanner()
        vulnerabilities = scanner.scan_file(str(full_path))

        return jsonify({
            'success': True,
            'file_path': file_path,
            'vulnerabilities': [v.to_dict() for v in vulnerabilities],
            'total': len(vulnerabilities)
        })

    except Exception as e:
        logger.error(f"Error scanning file: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files', methods=['GET'])
def get_project_files():
    """
    获取项目文件列表
    返回当前项目的所有生成文件的树形结构
    """
    try:
        if not pm_agent or not pm_agent.current_project_id:
            return jsonify({
                'success': False,
                'error': 'No active project'
            }), 404

        import os
        from pathlib import Path

        project_id = pm_agent.current_project_id
        project_path = Path(shared_state.workspace_root) / project_id

        if not project_path.exists():
            return jsonify({
                'success': False,
                'error': 'Project directory not found'
            }), 404

        def build_file_tree(path, base_path):
            """递归构建文件树"""
            items = []
            try:
                for item in sorted(path.iterdir()):
                    rel_path = str(item.relative_to(base_path))

                    if item.is_file():
                        # 获取文件大小和扩展名
                        size = item.stat().st_size
                        ext = item.suffix.lower()

                        items.append({
                            'type': 'file',
                            'name': item.name,
                            'path': rel_path,
                            'size': size,
                            'extension': ext
                        })
                    elif item.is_dir() and not item.name.startswith('.'):
                        # 递归处理子目录
                        children = build_file_tree(item, base_path)
                        items.append({
                            'type': 'directory',
                            'name': item.name,
                            'path': rel_path,
                            'children': children
                        })
            except PermissionError:
                pass

            return items

        file_tree = build_file_tree(project_path, project_path)

        return jsonify({
            'success': True,
            'project_id': project_id,
            'files': file_tree
        })

    except Exception as e:
        logger.error(f"Error getting project files: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/content', methods=['GET'])
def get_file_content():
    """
    获取文件内容
    Query参数: file_path - 相对于项目根目录的文件路径
    """
    try:
        if not pm_agent or not pm_agent.current_project_id:
            return jsonify({
                'success': False,
                'error': 'No active project'
            }), 404

        file_path = request.args.get('file_path', '').strip()
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path parameter is required'
            }), 400

        from pathlib import Path
        project_id = pm_agent.current_project_id
        full_path = Path(shared_state.workspace_root) / project_id / file_path

        # 安全检查：防止路径遍历攻击
        try:
            full_path = full_path.resolve()
            project_root = (Path(shared_state.workspace_root) / project_id).resolve()
            if not str(full_path).startswith(str(project_root)):
                return jsonify({
                    'success': False,
                    'error': 'Invalid file path'
                }), 403
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 403

        if not full_path.exists() or not full_path.is_file():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        # 读取文件内容
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 确定文件类型（用于语法高亮）
            ext = full_path.suffix.lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.jsx': 'javascript',
                '.ts': 'typescript',
                '.tsx': 'typescript',
                '.html': 'html',
                '.css': 'css',
                '.json': 'json',
                '.md': 'markdown',
                '.yaml': 'yaml',
                '.yml': 'yaml',
                '.sh': 'bash',
                '.sql': 'sql',
                '.go': 'go',
                '.rs': 'rust',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.txt': 'text'
            }
            language = language_map.get(ext, 'text')

            return jsonify({
                'success': True,
                'file_path': file_path,
                'content': content,
                'language': language,
                'size': len(content),
                'lines': content.count('\n') + 1
            })

        except UnicodeDecodeError:
            # 二进制文件
            return jsonify({
                'success': False,
                'error': 'Binary file cannot be previewed',
                'is_binary': True
            }), 400

    except Exception as e:
        logger.error(f"Error getting file content: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # 初始化系统
    initialize_system()

    # 启动Web服务器（使用SocketIO）
    logger.info("Starting web server with WebSocket support on http://localhost:3000")
    socketio.run(app, host='0.0.0.0', port=3000, debug=False, allow_unsafe_werkzeug=True)
