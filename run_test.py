# 第一步：优先加载全局日志配置（必须在导入其他模块前执行）
from core.log_config import setup_global_logging, get_logger
setup_global_logging()

# 第二步：导入框架依赖和执行用例所需模块
import os
import pytest
from datetime import datetime
from core.log_config import REPORT_DIR

# 获取入口日志器
logger = get_logger(__name__)

def run_auto_test():
    """执行自动化测试用例"""
    logger.info("🚀 开始执行自动化测试用例集")
    # 定义测试报告路径
    report_path = os.path.join(REPORT_DIR, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    # 构造 Pytest 执行参数
    pytest_args = [
        "tests/testcases",  # 测试用例目录
        f"--html={report_path}",  # 生成 HTML 测试报告
        "--self-contained-html",  # 报告独立文件（便于分享）
        "-v",  # 详细输出
        "-s"   # 允许打印日志（配合 logging 输出）
    ]
    # 执行用例
    pytest.main(pytest_args)
    logger.info(f"✅ 自动化测试用例执行完成，测试报告路径：{report_path}")

if __name__ == "__main__":
    run_auto_test()