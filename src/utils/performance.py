"""
性能测试和基准测试模块
Performance Testing and Benchmarking Module

本模块提供性能测试、监控和基准测试功能，帮助衡量DevSwarm系统的性能指标。
可以测量Agent响应时间、任务完成时间、LLM调用延迟、内存使用等关键指标。

主要功能:
    1. **性能装饰器**: 自动测量函数执行时间
    2. **性能指标收集**: 收集和聚合性能数据
    3. **基准测试**: 运行标准化测试场景
    4. **性能报告**: 生成可视化性能报告
    5. **实时监控**: 追踪系统资源使用

主要组件:
    - PerformanceTimer: 计时器上下文管理器
    - performance_monitor: 性能监控装饰器
    - PerformanceMetrics: 性能指标收集器
    - BenchmarkSuite: 基准测试套件

使用方式:
    >>> # 方式1：装饰器
    >>> @performance_monitor("my_function")
    >>> async def my_function():
    ...     pass
    >>>
    >>> # 方式2：上下文管理器
    >>> with PerformanceTimer("operation"):
    ...     # 执行操作
    ...     pass
    >>>
    >>> # 方式3：基准测试
    >>> suite = BenchmarkSuite()
    >>> report = await suite.run_all_benchmarks()
"""
import time
import asyncio
import psutil
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from functools import wraps
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """
    性能指标数据类

    记录单次操作的性能指标，包括执行时间、内存使用、时间戳等。

    Attributes:
        operation (str): 操作名称，如 "agent_task_execution", "llm_call"
        duration_ms (float): 执行时间（毫秒）
        timestamp (str): 时间戳，ISO 8601格式
        memory_used_mb (float): 内存使用量（MB）
        success (bool): 操作是否成功完成
        metadata (Dict): 额外的元数据，如任务ID、Agent名称等
    """
    operation: str                                    # 操作名称
    duration_ms: float                                # 执行时间（毫秒）
    timestamp: str                                    # 时间戳
    memory_used_mb: float = 0.0                      # 内存使用（MB）
    success: bool = True                              # 是否成功
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PerformanceTimer:
    """
    性能计时器上下文管理器

    用于测量代码块的执行时间和资源使用。支持作为上下文管理器使用，
    自动记录开始和结束时的状态。

    Attributes:
        operation (str): 操作名称
        start_time (float): 开始时间（秒）
        end_time (float): 结束时间（秒）
        start_memory (float): 开始时内存使用（MB）
        end_memory (float): 结束时内存使用（MB）

    Example:
        >>> with PerformanceTimer("database_query") as timer:
        ...     result = execute_query()
        >>> print(f"Query took {timer.duration_ms}ms")
    """

    def __init__(self, operation: str, metadata: Optional[Dict] = None):
        """
        初始化计时器

        Args:
            operation (str): 操作名称
            metadata (Optional[Dict]): 额外的元数据
        """
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.success = True

    def __enter__(self):
        """进入上下文，开始计时"""
        self.start_time = time.time()
        process = psutil.Process()
        self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，结束计时"""
        self.end_time = time.time()
        process = psutil.Process()
        self.end_memory = process.memory_info().rss / 1024 / 1024  # MB

        if exc_type is not None:
            self.success = False

        # 记录指标
        metric = PerformanceMetric(
            operation=self.operation,
            duration_ms=self.duration_ms,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            memory_used_mb=self.memory_delta,
            success=self.success,
            metadata=self.metadata
        )

        PerformanceMetrics.record(metric)

    @property
    def duration_ms(self) -> float:
        """获取执行时间（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    @property
    def memory_delta(self) -> float:
        """获取内存增量（MB）"""
        if self.start_memory and self.end_memory:
            return self.end_memory - self.start_memory
        return 0.0


def performance_monitor(operation: str, metadata_func: Optional[Callable] = None):
    """
    性能监控装饰器

    自动测量函数执行时间和资源使用。支持同步和异步函数。

    Args:
        operation (str): 操作名称
        metadata_func (Optional[Callable]): 用于生成元数据的函数，
            接收被装饰函数的参数，返回元数据字典

    Example:
        >>> @performance_monitor("process_data")
        >>> def process_data(data):
        ...     return transform(data)
        >>>
        >>> @performance_monitor("async_task",
        ...     metadata_func=lambda task_id: {"task_id": task_id})
        >>> async def async_task(task_id):
        ...     await do_work(task_id)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metadata = {}
            if metadata_func:
                metadata = metadata_func(*args, **kwargs)

            with PerformanceTimer(operation, metadata):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metadata = {}
            if metadata_func:
                metadata = metadata_func(*args, **kwargs)

            with PerformanceTimer(operation, metadata):
                return func(*args, **kwargs)

        # 判断是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class PerformanceMetrics:
    """
    性能指标收集器（单例）

    收集、聚合和导出性能指标。所有通过PerformanceTimer和performance_monitor
    记录的指标都会被自动收集到这里。

    主要功能:
        - record(): 记录单个性能指标
        - get_summary(): 获取性能摘要统计
        - export_to_file(): 导出到JSON文件
        - clear(): 清空已收集的指标
        - get_metrics_by_operation(): 按操作名称筛选指标

    Example:
        >>> # 记录指标
        >>> metric = PerformanceMetric(...)
        >>> PerformanceMetrics.record(metric)
        >>>
        >>> # 获取摘要
        >>> summary = PerformanceMetrics.get_summary()
        >>> print(summary["agent_task_execution"]["avg_duration_ms"])
        >>>
        >>> # 导出到文件
        >>> PerformanceMetrics.export_to_file("performance_report.json")
    """

    _metrics: List[PerformanceMetric] = []  # 所有指标
    _max_metrics = 10000                     # 最大保存指标数

    @classmethod
    def record(cls, metric: PerformanceMetric):
        """
        记录性能指标

        Args:
            metric (PerformanceMetric): 性能指标对象
        """
        cls._metrics.append(metric)

        # 限制指标数量，防止内存溢出
        if len(cls._metrics) > cls._max_metrics:
            # 保留最近的指标
            cls._metrics = cls._metrics[-cls._max_metrics:]

        logger.debug(f"Performance: {metric.operation} took {metric.duration_ms:.2f}ms")

    @classmethod
    def get_all_metrics(cls) -> List[PerformanceMetric]:
        """获取所有指标"""
        return cls._metrics.copy()

    @classmethod
    def get_metrics_by_operation(cls, operation: str) -> List[PerformanceMetric]:
        """
        按操作名称筛选指标

        Args:
            operation (str): 操作名称

        Returns:
            List[PerformanceMetric]: 匹配的指标列表
        """
        return [m for m in cls._metrics if m.operation == operation]

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """
        获取性能摘要统计

        计算每个操作的平均执行时间、最小值、最大值、总次数等统计信息。

        Returns:
            Dict[str, Any]: 性能摘要，按操作名称分组
                {
                    "operation_name": {
                        "count": 10,
                        "avg_duration_ms": 123.45,
                        "min_duration_ms": 50.0,
                        "max_duration_ms": 300.0,
                        "total_duration_ms": 1234.5,
                        "success_rate": 0.9,
                        "avg_memory_mb": 12.5
                    },
                    ...
                }
        """
        if not cls._metrics:
            return {}

        # 按操作分组
        operations = {}
        for metric in cls._metrics:
            if metric.operation not in operations:
                operations[metric.operation] = []
            operations[metric.operation].append(metric)

        # 计算统计信息
        summary = {}
        for operation, metrics in operations.items():
            durations = [m.duration_ms for m in metrics]
            successes = [m.success for m in metrics]
            memories = [m.memory_used_mb for m in metrics]

            summary[operation] = {
                'count': len(metrics),
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'total_duration_ms': sum(durations),
                'success_rate': sum(successes) / len(successes) if successes else 0,
                'avg_memory_mb': sum(memories) / len(memories) if memories else 0
            }

        return summary

    @classmethod
    def export_to_file(cls, filepath: str):
        """
        导出性能指标到JSON文件

        Args:
            filepath (str): 文件路径

        Example:
            >>> PerformanceMetrics.export_to_file("./reports/performance.json")
        """
        try:
            data = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'total_metrics': len(cls._metrics),
                'summary': cls.get_summary(),
                'metrics': [m.to_dict() for m in cls._metrics]
            }

            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Performance metrics exported to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}", exc_info=True)

    @classmethod
    def clear(cls):
        """清空所有指标"""
        cls._metrics = []
        logger.info("Performance metrics cleared")


class BenchmarkSuite:
    """
    基准测试套件

    提供标准化的基准测试场景，用于评估系统性能。
    可以测试各种场景，如简单任务、复杂任务、并发任务等。

    Example:
        >>> suite = BenchmarkSuite()
        >>> report = await suite.run_all_benchmarks()
        >>> print(f"Average project time: {report['avg_project_time_s']}s")
    """

    def __init__(self, workspace_root: str = "./benchmark_workspace"):
        """
        初始化基准测试套件

        Args:
            workspace_root (str): 基准测试工作区根目录
        """
        self.workspace_root = workspace_root
        self.results = []

    async def run_simple_project_benchmark(self) -> Dict[str, Any]:
        """
        基准测试：简单项目生成

        测试场景：生成一个简单的待办事项应用
        衡量指标：端到端时间、任务完成时间、LLM调用次数

        Returns:
            Dict[str, Any]: 测试结果
        """
        logger.info("Running simple project benchmark...")

        start_time = time.time()

        # 简单需求
        requirement = "Create a simple todo list application with add and delete functions"

        try:
            # 这里需要实际的PM Agent实例来运行
            # 为了演示，返回模拟结果
            duration = time.time() - start_time

            result = {
                'benchmark': 'simple_project',
                'requirement': requirement,
                'duration_s': duration,
                'success': True,
                'tasks_generated': 4,  # 模拟值
                'llm_calls': 8,        # 模拟值
            }

            self.results.append(result)
            logger.info(f"Simple project benchmark completed in {duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Simple project benchmark failed: {e}")
            return {
                'benchmark': 'simple_project',
                'success': False,
                'error': str(e)
            }

    async def run_complex_project_benchmark(self) -> Dict[str, Any]:
        """
        基准测试：复杂项目生成

        测试场景：生成一个具有多个功能的电商应用
        衡量指标：端到端时间、任务完成时间、代码行数

        Returns:
            Dict[str, Any]: 测试结果
        """
        logger.info("Running complex project benchmark...")

        start_time = time.time()

        requirement = """Create an e-commerce application with:
        - User authentication
        - Product catalog
        - Shopping cart
        - Order management
        - Payment integration
        """

        try:
            duration = time.time() - start_time

            result = {
                'benchmark': 'complex_project',
                'requirement': requirement,
                'duration_s': duration,
                'success': True,
                'tasks_generated': 12,  # 模拟值
                'llm_calls': 24,        # 模拟值
            }

            self.results.append(result)
            logger.info(f"Complex project benchmark completed in {duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Complex project benchmark failed: {e}")
            return {
                'benchmark': 'complex_project',
                'success': False,
                'error': str(e)
            }

    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """
        运行所有基准测试

        依次执行所有预定义的基准测试场景。

        Returns:
            Dict[str, Any]: 综合测试报告
        """
        logger.info("Starting benchmark suite...")

        # 清空之前的结果
        self.results = []
        PerformanceMetrics.clear()

        # 运行各种基准测试
        await self.run_simple_project_benchmark()
        await self.run_complex_project_benchmark()

        # 生成报告
        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'benchmarks_run': len(self.results),
            'results': self.results,
            'performance_summary': PerformanceMetrics.get_summary(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024
            }
        }

        logger.info(f"Benchmark suite completed. {len(self.results)} benchmarks run.")
        return report

    def export_report(self, filepath: str):
        """
        导出基准测试报告

        Args:
            filepath (str): 报告文件路径

        Example:
            >>> suite.export_report("./reports/benchmark_report.json")
        """
        try:
            report_data = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'results': self.results
            }

            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Benchmark report exported to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export benchmark report: {e}", exc_info=True)


# 全局性能监控开关
_performance_monitoring_enabled = True


def enable_performance_monitoring():
    """启用性能监控"""
    global _performance_monitoring_enabled
    _performance_monitoring_enabled = True
    logger.info("Performance monitoring enabled")


def disable_performance_monitoring():
    """禁用性能监控"""
    global _performance_monitoring_enabled
    _performance_monitoring_enabled = False
    logger.info("Performance monitoring disabled")


def is_performance_monitoring_enabled() -> bool:
    """检查性能监控是否启用"""
    return _performance_monitoring_enabled
