"""
Web UI Application
提供用户界面用于提交需求和监控项目进度
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.message_bus import MessageBus
from src.core.shared_state import SharedState
from src.llm.llm_client import get_llm_client, LLMProvider
from src.agents.pm_agent import PMAgent
from src.agents.backend_agent import BackendAgent
from src.agents.frontend_agent import FrontendAgent
from src.agents.qa_agent import QAAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

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

    logger.info("System initialized successfully!")


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


if __name__ == '__main__':
    # 初始化系统
    initialize_system()

    # 启动Web服务器
    logger.info("Starting web server on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000, debug=False)
