#!/usr/bin/env python3
"""
DevSwarm Demo Script
快速演示多Agent系统的功能
"""
import asyncio
import sys
import logging
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.message_bus import MessageBus
from src.core.shared_state import SharedState
from src.llm.llm_client import get_llm_client, LLMProvider
from src.agents.pm_agent import PMAgent
from src.agents.backend_agent import BackendAgent
from src.agents.frontend_agent import FrontendAgent
from src.agents.qa_agent import QAAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  DevSwarm Multi-Agent System Demo")
    print("=" * 60)
    print()

    # 1. 初始化系统
    print("📦 Initializing system...")
    message_bus = MessageBus()
    shared_state = SharedState(workspace_root="./workspace")
    llm_client = get_llm_client(provider=LLMProvider.OPENAI)

    # 2. 创建Agents
    print("🤖 Creating agents...")
    pm_agent = PMAgent(message_bus, shared_state, llm_client)
    backend_agent = BackendAgent(message_bus, shared_state, llm_client)
    frontend_agent = FrontendAgent(message_bus, shared_state, llm_client)
    qa_agent = QAAgent(message_bus, shared_state, llm_client)

    # 3. 启动消息总线
    print("🚀 Starting message bus...")
    await message_bus.start()

    # 4. 启动所有Agents
    print("✅ Starting agents...")
    pm_agent.start()
    backend_agent.start()
    frontend_agent.start()
    qa_agent.start()

    print()
    print("=" * 60)
    print("  System Ready!")
    print("=" * 60)
    print()

    # 5. 示例需求
    requirement = input("Enter your requirement (or press Enter for default): ").strip()

    if not requirement:
        requirement = "我想要一个简单的待办事项清单应用，支持添加、删除和查看所有待办事项"
        print(f"\nUsing default requirement: {requirement}")

    print()
    print("=" * 60)
    print("  Starting Project Development")
    print("=" * 60)
    print()

    # 6. 启动项目
    try:
        project_id = await pm_agent.start_project(requirement)

        print()
        print(f"✅ Project started: {project_id}")
        print()

        # 7. 等待项目完成（轮询状态）
        print("⏳ Waiting for completion (this may take a few minutes)...")
        print()

        completed = False
        iteration = 0
        max_iterations = 60  # 最多等待5分钟

        while not completed and iteration < max_iterations:
            await asyncio.sleep(5)  # 每5秒检查一次

            status = pm_agent.get_project_status()
            project_status = status['project_status']

            # 显示进度
            print(f"📊 Status: {project_status} | "
                  f"Tasks: {status['completed_tasks']}/{status['total_tasks']} completed")

            if project_status == "completed":
                completed = True
                break
            elif project_status == "failed":
                print("❌ Project failed!")
                break

            iteration += 1

        # 8. 显示结果
        print()
        print("=" * 60)
        if completed:
            print("  🎉 Project Completed Successfully!")
        else:
            print("  ⚠️  Project Status:", project_status)
        print("=" * 60)
        print()

        # 显示项目摘要
        summary = shared_state.export_summary()
        print(summary)
        print()

        # 显示生成的文件路径
        backend_path = shared_state.get_codebase_path("backend")
        frontend_path = shared_state.get_codebase_path("frontend")

        print("📁 Generated Files:")
        print(f"   Backend:  {backend_path}")
        print(f"   Frontend: {frontend_path}")
        print()

        if completed:
            print("💡 Next Steps:")
            print(f"   1. cd {Path(backend_path).parent}")
            print("   2. Follow the README.md instructions to run the app")
            print()

    except Exception as e:
        logger.error(f"Error during demo: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")

    finally:
        # 9. 清理
        print("🧹 Cleaning up...")
        await message_bus.stop()
        print("✅ Demo completed!")


def main():
    """主函数"""
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
