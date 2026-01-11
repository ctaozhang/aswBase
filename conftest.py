"""
Pytest全局配置：放所有测试用例共用的Fixture
无需手动导入，tests/下的所有用例可直接使用
"""
import pytest
from core.clientbase import ClientBase
from core.assertion_utils import ResponseAssertor
from core.data_utils import load_env_config

@pytest.fixture(scope="session")  # 会话级别复用，提升性能
def client():
    env_dict =load_env_config()
    """全局HTTP客户端Fixture（可配置不同环境的base_url）"""
    client = ClientBase(
        base_url= env_dict.get("base_url"),  # 可通过环境变量动态配置，后面进行优化
        timeout= env_dict.get("timeout"),
        max_retries= env_dict.get("max_retries"),
        default_headers= env_dict.get("default_headers")
    )
    yield client  # 用例执行完后释放
    client.close()  # 关闭会话


@pytest.fixture(scope="function")
def response_assert(client):
    """全局断言工具Fixture（入参为响应对象，返回断言实例）"""
    def _factory(response):
        return ResponseAssertor(response)
    return _factory
