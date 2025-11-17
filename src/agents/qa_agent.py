"""
QA Agent模块 - 质量保证Agent
QA Agent Module - Quality Assurance Engineer

QA Agent负责对生成的代码进行自动化测试，检测Bug并报告给PM Agent。
实现DevSwarm系统的自愈能力（self-healing）。

核心职责:
    1. **启动服务**: 启动后端Flask服务器
    2. **执行测试**: 根据API契约自动生成和执行测试用例
        - API端点可用性测试
        - 数据正确性验证
        - HTTP状态码检查
    3. **Bug检测**: 捕获测试失败和异常
    4. **Bug报告**: 将Bug信息（错误消息、日志、代码上下文）报告给PM Agent
    5. **验证修复**: 重新测试验证Bug是否已修复

测试流程:
    1. 从共享状态获取API契约
    2. 启动后端服务（subprocess）
    3. 遍历所有API端点执行测试
    4. 收集测试结果
    5. 如有失败，生成BugReport发送给PM Agent

自愈机制:
    PM Agent收到Bug报告 → 分析原因 → 生成修复任务 → 重新分配给Worker Agent

Example:
    >>> qa = QAAgent(message_bus, shared_state, llm_client)
    >>> # 收到PM分配的测试任务后自动执行
"""
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List
import logging
import requests
from .base_agent import BaseAgent
from ..core.protocol import Task, BugReport, APIContract, MessageType

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    """
    质量保证Agent
    负责集成测试和Bug报告
    """

    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(
            agent_name="QA_Agent",
            role="Quality Assurance Engineer",
            message_bus=message_bus,
            shared_state=shared_state,
            llm_client=llm_client
        )

        self.backend_process = None
        self.test_results: List[Dict] = []

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行测试任务

        Args:
            task: 任务

        Returns:
            执行结果
        """
        logger.info(f"Executing QA task: {task.title}")

        # 获取API契约
        api_contract = self.shared_state.get_api_contract()
        if not api_contract:
            raise ValueError("API contract not found")

        # 获取代码路径
        backend_path = self.shared_state.get_codebase_path("backend")
        frontend_path = self.shared_state.get_codebase_path("frontend")

        if not backend_path or not frontend_path:
            raise ValueError("Code paths not found")

        # 执行集成测试
        result = await self._run_integration_tests(
            api_contract,
            Path(backend_path),
            Path(frontend_path)
        )

        return result

    async def _run_integration_tests(self,
                                    api_contract: APIContract,
                                    backend_dir: Path,
                                    frontend_dir: Path) -> Dict[str, Any]:
        """
        运行集成测试

        Args:
            api_contract: API契约
            backend_dir: 后端目录
            frontend_dir: 前端目录

        Returns:
            测试结果
        """
        logger.info("Running integration tests...")

        self.test_results.clear()

        try:
            # 1. 启动后端服务
            logger.info("Starting backend server...")
            if not await self._start_backend_server(backend_dir):
                raise Exception("Failed to start backend server")

            # 2. 等待服务启动
            await self._wait_for_server(api_contract.base_url)

            # 3. 执行API测试
            logger.info("Testing API endpoints...")
            api_test_results = await self._test_api_endpoints(api_contract)

            # 4. 检查测试结果
            failed_tests = [t for t in api_test_results if not t.get("passed", False)]

            if failed_tests:
                # 有失败的测试，报告Bug
                logger.warning(f"Found {len(failed_tests)} failing tests")
                await self._report_bugs(failed_tests)

                return {
                    "status": "failed",
                    "total_tests": len(api_test_results),
                    "passed": len(api_test_results) - len(failed_tests),
                    "failed": len(failed_tests),
                    "tests": api_test_results
                }
            else:
                logger.info("All tests passed!")
                return {
                    "status": "success",
                    "total_tests": len(api_test_results),
                    "passed": len(api_test_results),
                    "failed": 0,
                    "tests": api_test_results
                }

        except Exception as e:
            logger.error(f"Integration tests failed: {e}", exc_info=True)
            raise

        finally:
            # 停止后端服务
            self._stop_backend_server()

    async def _start_backend_server(self, backend_dir: Path) -> bool:
        """
        启动后端服务

        Args:
            backend_dir: 后端目录

        Returns:
            是否成功启动
        """
        try:
            app_file = backend_dir / "app.py"
            if not app_file.exists():
                logger.error(f"Backend app.py not found at {app_file}")
                return False

            # 启动Flask服务器（后台运行）
            self.backend_process = subprocess.Popen(
                ["python3", "app.py"],
                cwd=str(backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            logger.info(f"Backend server started with PID {self.backend_process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start backend server: {e}")
            return False

    def _stop_backend_server(self):
        """停止后端服务"""
        if self.backend_process:
            logger.info("Stopping backend server...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            self.backend_process = None

    async def _wait_for_server(self, base_url: str, max_attempts: int = 30):
        """
        等待服务器启动

        Args:
            base_url: 基础URL
            max_attempts: 最大尝试次数
        """
        logger.info(f"Waiting for server at {base_url}...")

        for i in range(max_attempts):
            try:
                response = requests.get(f"{base_url}/health", timeout=1)
                if response.status_code == 200:
                    logger.info("Server is ready!")
                    return
            except requests.exceptions.RequestException:
                pass

            time.sleep(1)

        raise Exception("Server failed to start within timeout")

    async def _test_api_endpoints(self, api_contract: APIContract) -> List[Dict]:
        """
        测试API端点

        Args:
            api_contract: API契约

        Returns:
            测试结果列表
        """
        results = []

        for endpoint in api_contract.endpoints:
            method = endpoint['method']
            path = endpoint['path']
            description = endpoint['description']

            test_name = f"test_{method.lower()}_{path.replace('/', '_').replace(':', '')}"

            logger.info(f"Testing: {method} {path}")

            try:
                if method == "GET":
                    result = await self._test_get_endpoint(
                        api_contract.base_url,
                        path,
                        test_name,
                        description
                    )
                elif method == "POST":
                    result = await self._test_post_endpoint(
                        api_contract.base_url,
                        path,
                        test_name,
                        description,
                        endpoint.get('request_body', {})
                    )
                elif method == "DELETE":
                    result = await self._test_delete_endpoint(
                        api_contract.base_url,
                        path,
                        test_name,
                        description
                    )
                elif method == "PUT":
                    result = await self._test_put_endpoint(
                        api_contract.base_url,
                        path,
                        test_name,
                        description,
                        endpoint.get('request_body', {})
                    )
                else:
                    result = {
                        "test_name": test_name,
                        "passed": False,
                        "error": f"Unsupported method: {method}"
                    }

                results.append(result)

            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                results.append({
                    "test_name": test_name,
                    "passed": False,
                    "error": str(e),
                    "method": method,
                    "path": path
                })

        return results

    async def _test_get_endpoint(self, base_url: str, path: str,
                                 test_name: str, description: str) -> Dict:
        """测试GET端点"""
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, timeout=5)

            passed = response.status_code == 200
            return {
                "test_name": test_name,
                "description": description,
                "passed": passed,
                "status_code": response.status_code,
                "method": "GET",
                "path": path,
                "error": None if passed else f"Expected 200, got {response.status_code}"
            }

        except Exception as e:
            return {
                "test_name": test_name,
                "description": description,
                "passed": False,
                "method": "GET",
                "path": path,
                "error": str(e)
            }

    async def _test_post_endpoint(self, base_url: str, path: str,
                                  test_name: str, description: str,
                                  request_body: Dict) -> Dict:
        """测试POST端点"""
        try:
            url = f"{base_url}{path}"

            # 创建测试数据
            test_data = {"title": "Test Item", "name": "Test Item"}
            # 如果有request_body规范，使用它
            if request_body:
                test_data = {
                    key: f"test_{key}" if isinstance(val, str) else val
                    for key, val in request_body.items()
                }

            response = requests.post(url, json=test_data, timeout=5)

            passed = response.status_code in [200, 201]
            return {
                "test_name": test_name,
                "description": description,
                "passed": passed,
                "status_code": response.status_code,
                "method": "POST",
                "path": path,
                "error": None if passed else f"Expected 200/201, got {response.status_code}"
            }

        except Exception as e:
            return {
                "test_name": test_name,
                "description": description,
                "passed": False,
                "method": "POST",
                "path": path,
                "error": str(e)
            }

    async def _test_delete_endpoint(self, base_url: str, path: str,
                                   test_name: str, description: str) -> Dict:
        """测试DELETE端点"""
        try:
            # 首先创建一个项目以便删除
            post_path = path.split(':')[0].rstrip('/<')
            create_response = requests.post(
                f"{base_url}{post_path}",
                json={"title": "Item to delete"},
                timeout=5
            )

            if create_response.status_code not in [200, 201]:
                return {
                    "test_name": test_name,
                    "description": description,
                    "passed": False,
                    "method": "DELETE",
                    "path": path,
                    "error": "Failed to create test item for deletion"
                }

            # 获取创建的项目ID
            created_item = create_response.json()
            item_id = created_item.get('id')

            if not item_id:
                return {
                    "test_name": test_name,
                    "description": description,
                    "passed": False,
                    "method": "DELETE",
                    "path": path,
                    "error": "Created item has no ID"
                }

            # 执行删除
            delete_path = path.replace(':id', item_id).replace('<id>', item_id)
            delete_url = f"{base_url}{delete_path}"
            response = requests.delete(delete_url, timeout=5)

            passed = response.status_code == 200
            return {
                "test_name": test_name,
                "description": description,
                "passed": passed,
                "status_code": response.status_code,
                "method": "DELETE",
                "path": path,
                "error": None if passed else f"Expected 200, got {response.status_code}"
            }

        except Exception as e:
            return {
                "test_name": test_name,
                "description": description,
                "passed": False,
                "method": "DELETE",
                "path": path,
                "error": str(e)
            }

    async def _test_put_endpoint(self, base_url: str, path: str,
                                test_name: str, description: str,
                                request_body: Dict) -> Dict:
        """测试PUT端点"""
        try:
            # 类似DELETE，先创建后更新
            post_path = path.split(':')[0].rstrip('/<')
            create_response = requests.post(
                f"{base_url}{post_path}",
                json={"title": "Item to update"},
                timeout=5
            )

            if create_response.status_code not in [200, 201]:
                return {
                    "test_name": test_name,
                    "description": description,
                    "passed": False,
                    "method": "PUT",
                    "path": path,
                    "error": "Failed to create test item for update"
                }

            created_item = create_response.json()
            item_id = created_item.get('id')

            if not item_id:
                return {
                    "test_name": test_name,
                    "description": description,
                    "passed": False,
                    "method": "PUT",
                    "path": path,
                    "error": "Created item has no ID"
                }

            # 执行更新
            update_path = path.replace(':id', item_id).replace('<id>', item_id)
            update_url = f"{base_url}{update_path}"
            update_data = {"title": "Updated Item"}

            response = requests.put(update_url, json=update_data, timeout=5)

            passed = response.status_code == 200
            return {
                "test_name": test_name,
                "description": description,
                "passed": passed,
                "status_code": response.status_code,
                "method": "PUT",
                "path": path,
                "error": None if passed else f"Expected 200, got {response.status_code}"
            }

        except Exception as e:
            return {
                "test_name": test_name,
                "description": description,
                "passed": False,
                "method": "PUT",
                "path": path,
                "error": str(e)
            }

    async def _report_bugs(self, failed_tests: List[Dict]):
        """
        报告Bug给PM Agent

        Args:
            failed_tests: 失败的测试列表
        """
        for test in failed_tests:
            bug_report = BugReport(
                test_name=test.get("test_name", "unknown"),
                error_message=test.get("error", "Unknown error"),
                logs=[
                    f"Method: {test.get('method', 'N/A')}",
                    f"Path: {test.get('path', 'N/A')}",
                    f"Status Code: {test.get('status_code', 'N/A')}"
                ],
                relevant_code_context=self._extract_code_context(test),
                severity="high" if test.get("status_code") == 404 else "medium"
            )

            # 发送Bug报告给PM
            await self.send_message(
                to_agent="PM_Agent",
                message_type=MessageType.BUG_REPORT,
                payload={
                    "task_id": self.current_task.task_id if self.current_task else None,
                    "bug_report": bug_report.to_dict()
                }
            )

            logger.info(f"Bug reported: {bug_report.test_name}")

    def _extract_code_context(self, test: Dict) -> str:
        """
        提取代码上下文（用于Bug报告）

        Args:
            test: 测试结果

        Returns:
            代码上下文字符串
        """
        method = test.get("method", "")
        path = test.get("path", "")

        # 尝试读取后端代码
        backend_path = self.shared_state.get_codebase_path("backend")
        if backend_path:
            app_file = Path(backend_path) / "app.py"
            if app_file.exists():
                try:
                    with open(app_file, 'r', encoding='utf-8') as f:
                        code = f.read()

                    # 简单查找相关代码
                    lines = code.split('\n')
                    relevant_lines = []

                    for i, line in enumerate(lines):
                        if path in line or f"'{method.lower()}'" in line.lower():
                            # 获取周围几行
                            start = max(0, i - 3)
                            end = min(len(lines), i + 4)
                            relevant_lines = lines[start:end]
                            break

                    if relevant_lines:
                        return '\n'.join(relevant_lines)

                except Exception as e:
                    logger.error(f"Failed to extract code context: {e}")

        return f"Unable to extract code context for {method} {path}"
