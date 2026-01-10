import pytest
from core.log_config import get_logger
from core.data_utils import parse_yaml_to_params

# 使用封装的 get_logger
logger = get_logger(__name__)

# 1. 拆解YAML用例为参数名和参数值,用例名
param_names, param_values, case_ids = parse_yaml_to_params("chuan_can.yaml", "login_cases")
# 2. 参数化测试函数
@pytest.mark.parametrize(param_names, param_values, ids=case_ids)
def test_assert_status_code(client_base, response_assert, username, password, code, assert_config):
    """
    验证参数化用例yaml传参，断言
    client_base: 封装的请求客户端夹具
    response_assert：封装的断言夹具
    username：从yaml中data中传递的username
    password：从yaml中data中传递的password
    code：从yaml中data中传递的code
    assert_config：从yaml中读取到的断言列表，每个元素是一个断言
    """
    params = {
        "username": username,
        "password": password,
        "code": code
    }

    # 发送请求（httpbin的/get接口会原样返回请求参数，可直接验证）
    response = client_base.get("https://httpbin.org/get", params=params)

    # 断言
    assertor = response_assert(response)
    # 方式1：执行链式断言(动态断言,参数化格式推荐)
    assertor.assert_from_config(assert_config)

    # 方式2：硬编码断言(不需要参数化时,直接断言推荐)
    assertor.assert_json_field("args.username", username)
    assertor.assert_json_field("args.password", str(password))
