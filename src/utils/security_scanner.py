"""
安全扫描模块
Security Scanner Module

本模块提供基础的安全扫描功能，检测生成代码中的常见安全漏洞。
在代码生成后自动扫描，识别潜在的安全问题并生成报告。

支持的漏洞类型:
    1. SQL注入 (SQL Injection)
    2. XSS跨站脚本 (Cross-Site Scripting)
    3. 硬编码密钥 (Hardcoded Secrets)
    4. 不安全的随机数 (Insecure Random)
    5. 危险函数使用 (eval, exec)
    6. 路径遍历 (Path Traversal)
    7. 弱加密 (Weak Cryptography)
    8. 命令注入 (Command Injection)

支持的语言:
    - Python
    - JavaScript / TypeScript
    - (其他语言的基础检查)

使用方式:
    >>> scanner = SecurityScanner()
    >>> report = scanner.scan_file("backend/app.py")
    >>> print(f"Found {len(report.vulnerabilities)} vulnerabilities")
    >>>
    >>> # 扫描整个项目
    >>> project_report = scanner.scan_project("./workspace/project_1")
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class Severity(Enum):
    """
    漏洞严重程度枚举

    Attributes:
        CRITICAL: 严重 - 需要立即修复
        HIGH: 高 - 需要优先修复
        MEDIUM: 中 - 应该修复
        LOW: 低 - 建议修复
        INFO: 信息 - 仅供参考
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(Enum):
    """
    漏洞类型枚举

    定义系统能够检测的所有漏洞类型
    """
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    HARDCODED_SECRET = "hardcoded_secret"
    INSECURE_RANDOM = "insecure_random"
    DANGEROUS_FUNCTION = "dangerous_function"
    PATH_TRAVERSAL = "path_traversal"
    WEAK_CRYPTO = "weak_crypto"
    COMMAND_INJECTION = "command_injection"
    INSECURE_DESERIALIZATION = "insecure_deserialization"


@dataclass
class Vulnerability:
    """
    漏洞数据类

    记录单个安全漏洞的详细信息

    Attributes:
        type (VulnerabilityType): 漏洞类型
        severity (Severity): 严重程度
        file_path (str): 文件路径
        line_number (int): 行号
        code_snippet (str): 相关代码片段
        description (str): 漏洞描述
        recommendation (str): 修复建议
    """
    type: VulnerabilityType
    severity: Severity
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        data['severity'] = self.severity.value
        return data


@dataclass
class SecurityScanReport:
    """
    安全扫描报告数据类

    汇总扫描结果和统计信息

    Attributes:
        scan_path (str): 扫描路径
        files_scanned (int): 扫描文件数
        vulnerabilities (List[Vulnerability]): 发现的漏洞列表
        timestamp (str): 扫描时间戳
    """
    scan_path: str
    files_scanned: int
    vulnerabilities: List[Vulnerability]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'scan_path': self.scan_path,
            'files_scanned': self.files_scanned,
            'total_vulnerabilities': len(self.vulnerabilities),
            'vulnerabilities_by_severity': self.get_counts_by_severity(),
            'vulnerabilities': [v.to_dict() for v in self.vulnerabilities],
            'timestamp': self.timestamp
        }

    def get_counts_by_severity(self) -> Dict[str, int]:
        """按严重程度统计漏洞数量"""
        counts = {sev.value: 0 for sev in Severity}
        for vuln in self.vulnerabilities:
            counts[vuln.severity.value] += 1
        return counts


class SecurityScanner:
    """
    安全扫描器

    提供代码安全扫描功能，检测常见的安全漏洞

    主要方法:
        - scan_file(): 扫描单个文件
        - scan_project(): 扫描整个项目目录
        - scan_code(): 扫描代码字符串

    Example:
        >>> scanner = SecurityScanner()
        >>> report = scanner.scan_project("./workspace/my_project")
        >>> if report.vulnerabilities:
        ...     print(f"Warning: Found {len(report.vulnerabilities)} vulnerabilities")
        ...     scanner.export_report(report, "security_report.json")
    """

    def __init__(self):
        """初始化安全扫描器"""
        # 定义各种漏洞的检测规则（正则表达式）
        self._init_python_rules()
        self._init_javascript_rules()
        self._init_common_rules()

    def _init_python_rules(self):
        """初始化Python安全规则"""
        self.python_rules = [
            {
                'type': VulnerabilityType.SQL_INJECTION,
                'severity': Severity.HIGH,
                'pattern': r'execute\s*\([^)]*[+%]\s*',
                'description': 'Potential SQL injection: string concatenation in SQL query',
                'recommendation': 'Use parameterized queries instead of string concatenation'
            },
            {
                'type': VulnerabilityType.DANGEROUS_FUNCTION,
                'severity': Severity.CRITICAL,
                'pattern': r'\beval\s*\(',
                'description': 'Use of dangerous function: eval()',
                'recommendation': 'Avoid using eval(). Consider safer alternatives like ast.literal_eval()'
            },
            {
                'type': VulnerabilityType.DANGEROUS_FUNCTION,
                'severity': Severity.HIGH,
                'pattern': r'\bexec\s*\(',
                'description': 'Use of dangerous function: exec()',
                'recommendation': 'Avoid using exec(). Refactor code to avoid dynamic code execution'
            },
            {
                'type': VulnerabilityType.INSECURE_RANDOM,
                'severity': Severity.MEDIUM,
                'pattern': r'import\s+random\b|from\s+random\s+import',
                'description': 'Use of insecure random number generator',
                'recommendation': 'Use secrets module for security-sensitive operations'
            },
            {
                'type': VulnerabilityType.COMMAND_INJECTION,
                'severity': Severity.HIGH,
                'pattern': r'os\.system\s*\(|subprocess\.call\s*\([^)]*shell\s*=\s*True',
                'description': 'Potential command injection vulnerability',
                'recommendation': 'Avoid shell=True. Use subprocess with argument lists'
            },
            {
                'type': VulnerabilityType.PATH_TRAVERSAL,
                'severity': Severity.MEDIUM,
                'pattern': r'open\s*\([^)]*[+]\s*|os\.path\.join\s*\([^)]*[+]',
                'description': 'Potential path traversal vulnerability',
                'recommendation': 'Validate and sanitize file paths before use'
            },
            {
                'type': VulnerabilityType.INSECURE_DESERIALIZATION,
                'severity': Severity.HIGH,
                'pattern': r'pickle\.loads\s*\(|pickle\.load\s*\(',
                'description': 'Insecure deserialization using pickle',
                'recommendation': 'Use JSON or other safe serialization formats for untrusted data'
            },
            {
                'type': VulnerabilityType.WEAK_CRYPTO,
                'severity': Severity.MEDIUM,
                'pattern': r'hashlib\.md5\s*\(|hashlib\.sha1\s*\(',
                'description': 'Use of weak cryptographic hash function',
                'recommendation': 'Use SHA-256 or stronger hash functions'
            }
        ]

    def _init_javascript_rules(self):
        """初始化JavaScript安全规则"""
        self.javascript_rules = [
            {
                'type': VulnerabilityType.XSS,
                'severity': Severity.HIGH,
                'pattern': r'innerHTML\s*=|document\.write\s*\(',
                'description': 'Potential XSS vulnerability: unsafe DOM manipulation',
                'recommendation': 'Use textContent or sanitize HTML before insertion'
            },
            {
                'type': VulnerabilityType.DANGEROUS_FUNCTION,
                'severity': Severity.CRITICAL,
                'pattern': r'\beval\s*\(',
                'description': 'Use of dangerous function: eval()',
                'recommendation': 'Avoid using eval(). Consider JSON.parse() or other alternatives'
            },
            {
                'type': VulnerabilityType.INSECURE_RANDOM,
                'severity': Severity.MEDIUM,
                'pattern': r'Math\.random\s*\(',
                'description': 'Use of insecure random number generator',
                'recommendation': 'Use crypto.getRandomValues() for security-sensitive operations'
            },
            {
                'type': VulnerabilityType.SQL_INJECTION,
                'severity': Severity.HIGH,
                'pattern': r'query\s*\([^)]*\+\s*|execute\s*\([^)]*\+',
                'description': 'Potential SQL injection: string concatenation in query',
                'recommendation': 'Use parameterized queries or prepared statements'
            }
        ]

    def _init_common_rules(self):
        """初始化通用安全规则（跨语言）"""
        self.common_rules = [
            {
                'type': VulnerabilityType.HARDCODED_SECRET,
                'severity': Severity.CRITICAL,
                'pattern': r'(?i)(api[_-]?key|password|secret|token)\s*[=:]\s*["\'][^"\']{8,}["\']',
                'description': 'Hardcoded secret detected',
                'recommendation': 'Use environment variables or secure credential management'
            },
            {
                'type': VulnerabilityType.HARDCODED_SECRET,
                'severity': Severity.HIGH,
                'pattern': r'(?i)(sk|pk|secret)[_-]?[a-z0-9]{32,}',
                'description': 'Potential hardcoded API key or secret',
                'recommendation': 'Store secrets in environment variables or secret managers'
            }
        ]

    def scan_file(self, file_path: str) -> List[Vulnerability]:
        """
        扫描单个文件

        Args:
            file_path (str): 文件路径

        Returns:
            List[Vulnerability]: 发现的漏洞列表
        """
        try:
            path = Path(file_path)

            if not path.exists() or not path.is_file():
                logger.warning(f"File not found: {file_path}")
                return []

            # 读取文件内容
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 跳过二进制文件
                logger.debug(f"Skipping binary file: {file_path}")
                return []

            # 根据文件类型选择规则
            ext = path.suffix.lower()
            rules = self._get_rules_for_extension(ext)

            # 扫描代码
            vulnerabilities = []
            lines = content.split('\n')

            for rule in rules:
                pattern = re.compile(rule['pattern'])

                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        vuln = Vulnerability(
                            type=rule['type'],
                            severity=rule['severity'],
                            file_path=str(path),
                            line_number=i,
                            code_snippet=line.strip(),
                            description=rule['description'],
                            recommendation=rule['recommendation']
                        )
                        vulnerabilities.append(vuln)

            return vulnerabilities

        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}", exc_info=True)
            return []

    def _get_rules_for_extension(self, ext: str) -> List[Dict]:
        """根据文件扩展名获取适用的规则"""
        rules = self.common_rules.copy()  # 通用规则总是适用

        if ext == '.py':
            rules.extend(self.python_rules)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            rules.extend(self.javascript_rules)

        return rules

    def scan_project(self, project_path: str) -> SecurityScanReport:
        """
        扫描整个项目目录

        递归扫描项目中的所有代码文件

        Args:
            project_path (str): 项目根目录路径

        Returns:
            SecurityScanReport: 扫描报告
        """
        from datetime import datetime

        logger.info(f"Starting security scan of project: {project_path}")

        project_root = Path(project_path)
        if not project_root.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return SecurityScanReport(
                scan_path=project_path,
                files_scanned=0,
                vulnerabilities=[],
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )

        # 扫描所有代码文件
        all_vulnerabilities = []
        files_scanned = 0

        # 支持的文件扩展名
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css'}

        for file_path in project_root.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in code_extensions:
                # 跳过某些目录
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if 'node_modules' in file_path.parts or '__pycache__' in file_path.parts:
                    continue

                files_scanned += 1
                vulnerabilities = self.scan_file(str(file_path))
                all_vulnerabilities.extend(vulnerabilities)

        logger.info(f"Security scan completed. Files scanned: {files_scanned}, "
                   f"Vulnerabilities found: {len(all_vulnerabilities)}")

        return SecurityScanReport(
            scan_path=project_path,
            files_scanned=files_scanned,
            vulnerabilities=all_vulnerabilities,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

    def scan_code(self, code: str, language: str = 'python') -> List[Vulnerability]:
        """
        扫描代码字符串

        Args:
            code (str): 代码内容
            language (str): 编程语言 ('python', 'javascript')

        Returns:
            List[Vulnerability]: 发现的漏洞列表
        """
        # 根据语言选择规则
        if language.lower() == 'python':
            rules = self.common_rules + self.python_rules
        elif language.lower() in ['javascript', 'js', 'typescript', 'ts']:
            rules = self.common_rules + self.javascript_rules
        else:
            rules = self.common_rules

        vulnerabilities = []
        lines = code.split('\n')

        for rule in rules:
            pattern = re.compile(rule['pattern'])

            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    vuln = Vulnerability(
                        type=rule['type'],
                        severity=rule['severity'],
                        file_path='<code_string>',
                        line_number=i,
                        code_snippet=line.strip(),
                        description=rule['description'],
                        recommendation=rule['recommendation']
                    )
                    vulnerabilities.append(vuln)

        return vulnerabilities

    def export_report(self, report: SecurityScanReport, filepath: str):
        """
        导出安全扫描报告到JSON文件

        Args:
            report (SecurityScanReport): 扫描报告
            filepath (str): 输出文件路径
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Security scan report exported to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export security report: {e}", exc_info=True)
