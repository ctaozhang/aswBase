import logging
import logging.config
import os

# 1. 定义目录路径（绝对路径，避免相对路径混乱）
FRAMEWORK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(FRAMEWORK_ROOT, "logs")
REPORT_DIR = os.path.join(FRAMEWORK_ROOT, "reports")

# 2. 自动创建日志/报告目录
for dir_path in [LOG_DIR, REPORT_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"目录不存在，已自动创建：{dir_path}")

# 3. 全局日志配置字典（适配自动化测试场景）
AUTOTEST_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # 关键：不禁用现有日志器，避免用例日志丢失
    "formatters": {
        # 控制台格式（简洁，便于本地调试）
        "console_fmt": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        # 文件格式（详细，包含用例所在文件/行号/函数，便于问题定位）
        "file_fmt": {
            "format": "%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(funcName)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        # 控制台处理器（输出INFO及以上，过滤调试日志）
        "console_handler": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "console_fmt"
        },
        # 测试日志文件处理器（按时间轮转，保留7天，适配长期执行）
        "test_file_handler": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "DEBUG",  # 记录所有级别日志，便于详细排查
            "formatter": "file_fmt",
            "filename": os.path.join(LOG_DIR, "test_main.log"),
            "when": "D",  # 每天轮转一次
            "interval": 1,
            "backupCount": 7,  # 保留7天测试日志
            "encoding": "utf-8"  # 解决中文乱码（如用例名称含中文）
        },
        # 错误日志处理器（单独输出，快速定位失败用例）
        "error_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",  # 仅记录ERROR/CRITICAL
            "formatter": "file_fmt",
            "filename": os.path.join(LOG_DIR, "test_error.log"),
            "maxBytes": 1024 * 1024 * 50,  # 单个文件50MB
            "backupCount": 3,  # 保留3个备份
            "encoding": "utf-8"
        }
    },
    "loggers": {
        # 根日志器（所有模块日志器的父级，全局生效）
        "": {
            "handlers": ["console_handler", "test_file_handler", "error_file_handler"],
            "level": "DEBUG",
            "propagate": True
        },
        # 屏蔽第三方工具冗余日志（自动化框架常用）
        "selenium": {
            "level": "WARNING",
            "propagate": True
        },
        "urllib3": {
            "level": "WARNING",
            "propagate": True
        },
        "requests": {
            "level": "WARNING",
            "propagate": True
        },
        "pytest": {
            "level": "WARNING",
            "propagate": True
        }
    }
}

def setup_global_logging():
    """
    加载自动化测试框架的全局日志配置
    调用时机：框架入口文件最开始执行
    """
    try:
        logging.config.dictConfig(AUTOTEST_LOGGING_CONFIG)
        # 验证配置生效（自动化框架启动日志）
        logger = logging.getLogger(__name__)
        logger.info("✅ 自动化测试框架 - 全局日志配置加载成功")
        logger.info(f"📂 日志存储目录：{LOG_DIR}")
        logger.info(f"📂 测试报告目录：{REPORT_DIR}")
    except Exception as e:
        print(f"❌ 全局日志配置加载失败：{e}")
        raise  # 日志加载失败，终止框架运行

def get_logger(name):
    """
    封装日志器获取方法（可选，简化各模块调用）
    :param name: 日志器名称（建议传入 __name__）
    :return: 配置好的 logger 实例
    """
    return logging.getLogger(name)