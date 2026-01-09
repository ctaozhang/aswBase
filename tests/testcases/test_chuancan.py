# conftest.py

import os
import pytest,logging
from typing import List, Dict, Any, Tuple

# 复用 ClientBase 的日志配置
from core.data_utils import parse_yaml_to_params

logger = logging.getLogger(__name__)



# 1. 拆解YAML用例为参数名和参数值
param_names, param_values, case_ids = parse_yaml_to_params("chuan_can.yaml", "login_cases")
# 2. 参数化测试函数
@pytest.mark.parametrize(param_names, param_values, ids=case_ids)
def test_assert_status_code(client_base, response_assert,username, password, code, assert_config):
    """
    核心测试逻辑：
    1. 接收YAML拆解后的独立参数（username/password）
    2. 发送GET请求（用httpbin模拟登录接口）
    3. 执行assert_config中的批量断言
    """
    # ❶ 构建请求参数（使用YAML传递的username/password，而非硬编码）
    params = {
        "username": username,
        "password": password,
        "code": code
    }
    logger.info(f"执行用例：用户名={username}，密码={password}")

    # ❷ 发送请求（httpbin的/get接口会原样返回请求参数，可直接验证）
    response = client_base.get("https://httpbin.org/get", params=params)
    logger.info(f"响应数据：{response.json()}")


    # ❸ 执行批量断言（过滤undefine的断言项，避免无效失败）
    # from assertion_utils import ResponseAssertor

    assertor = response_assert(response)
    # 过滤掉值为undefine的断言项
    # filtered_assert_config = [
    #     item for item in assert_config if not any(v == "undefine" for v in item.values())
    # ]
    # 执行链式断言
    assertor.assert_from_config(assert_config)

    # ❹ 额外验证：请求参数是否正确传递（可选）
    resp_json = client_base.json(response)
    assert resp_json["args"]["username"] == username, f"用户名传递错误：预期{username}，实际{resp_json['args']['username']}"
    assert resp_json["args"]["password"] == str(password), f"密码传递错误：预期{password}，实际{resp_json['args']['password']}"


# 2. 动态传递参数给parametrize
# @pytest.mark.parametrize(param_names, param_values)
# def test_login(username, password, code, assert_config):
#     # 1. 构造请求数据（直接使用参数）
#     login_data = {
#         "username": username,
#         "password": password,
#         "code": code
#     }
#     print(login_data)
#     print(assert_config)
#     # 3. 执行断言（逻辑和之前一致）

if __name__ == "__main__":
    pytest.main(["-vs"])  # 直接运行，看多执行效果