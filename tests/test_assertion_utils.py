import pytest
from datetime import datetime

# ========== 基础响应状态断言测试 ==========
@pytest.mark.skip()
def test_assert_status_code(client, response_assert):
    """测试：响应状态码断言（正例+反例）"""
    # 正例：断言200状态码
    resp = client.get("https://httpbin.org/get")
    assertor = response_assert(resp)
    # 链式调用
    assertor.assert_status_code(200).assert_is_ok().assert_elapsed_less_than(60)

    # 反例：断言404（实际200），预期抛出AssertionError
    with pytest.raises(AssertionError) as exc_info:
        assertor.assert_status_code(404, msg="状态码断言反例测试")
    assert "响应状态码" in str(exc_info.value)

@pytest.mark.skip()
def test_assert_is_ok(client, response_assert):
    """测试：请求成功断言（200-299）"""
    # 正例：201状态码（创建成功）
    resp = client.post("https://httpbin.org/post")
    resp.status_code = 201  # 手动修改状态码模拟场景
    assertor = response_assert(resp)
    assertor.assert_is_ok(msg="201属于成功状态码")

    # 反例：400状态码（失败）
    resp_err = client.get("https://httpbin.org/status/400")
    assertor_err = response_assert(resp_err)
    with pytest.raises(AssertionError):
        assertor_err.assert_is_ok(msg="400不属于成功状态码")

@pytest.mark.skip()
def test_assert_is_redirect(client, response_assert):
    """测试：重定向断言（3xx + Location头）"""
    # 正例：302重定向（带Location头）
    resp = client.get("https://httpbin.org/redirect/1", allow_redirects=False)
    assertor = response_assert(resp)
    assertor.assert_is_redirect(msg="302重定向断言")

    # 反例：200非重定向
    resp_ok = client.get("https://httpbin.org/get")
    assertor_ok = response_assert(resp_ok)
    with pytest.raises(AssertionError):
        assertor_ok.assert_is_redirect()

@pytest.mark.skip()
def test_assert_is_permanent_redirect(client, response_assert):
    """测试：永久重定向断言（301/308）"""
    # 正例：301永久重定向
    resp = client.get("https://httpbin.org/status/301", allow_redirects=False)
    resp.headers["Location"] = "https://httpbin.org"  # 补充Location头
    assertor = response_assert(resp)
    assertor.assert_is_permanent_redirect(msg="301永久重定向")

    # 反例：302临时重定向
    resp_temp = client.get("https://httpbin.org/status/302", allow_redirects=False)
    resp_temp.headers["Location"] = "https://httpbin.org"
    assertor_temp = response_assert(resp_temp)
    with pytest.raises(AssertionError):
        assertor_temp.assert_is_permanent_redirect()


# ========== JSON字段断言测试 ==========
@pytest.mark.skip()
def test_assert_json_field(client, response_assert):
    """测试：JSON深层字段断言（点分隔+数组索引）"""
    # 构造包含嵌套字段的响应
    resp_data = {
        "code": 0,
        "data": {
            "list": [{"id": 100, "name": "test"}],
            "total": 1
        }
    }
    resp = client.post(
        "https://httpbin.org/post",
        json=resp_data
    )
    # 实际响应中，请求体在json字段下，所以路径是 json.data.list[0].id
    assertor = response_assert(resp)
    # 正例：断言数组字段值
    assertor.assert_json_field("json.data.list[0].id", 100, msg="嵌套数组字段断言")
    # 反例：断言错误值
    with pytest.raises(AssertionError):
        assertor.assert_json_field("json.data.total", 2)

@pytest.mark.skip()
def test_assert_json_path(client, response_assert):
    """测试：JSONPath表达式断言"""
    resp = client.get("https://httpbin.org/json")
    assertor = response_assert(resp)
    # 正例：提取slideshow.title字段（httpbin/json接口固定返回该字段）
    assertor.assert_json_path(
        jsonpath_expr="$.slideshow.title",
        expected_value="Sample Slide Show",
        msg="JSONPath断言"
    )
    # 反例：错误预期值
    with pytest.raises(AssertionError):
        assertor.assert_json_path("$.slideshow.title", "Wrong Title")

@pytest.mark.skip()
def test_assert_json_contains(client, response_assert):
    """测试：JSON包含指定字典（递归检查）"""
    expected_dict = {
        "args": {},
        "headers": {
            "User-Agent": "pytest-test/1.0"  # 对应conftest中默认header
        }
    }
    resp = client.get("https://httpbin.org/get")
    assertor = response_assert(resp)
    # 正例：响应JSON包含指定字典
    assertor.assert_json_contains(expected_dict, msg="JSON包含字典断言")
    # 反例：修改User-Agent，断言失败
    wrong_dict = {"headers": {"User-Agent": "wrong-agent"}}
    with pytest.raises(AssertionError):
        assertor.assert_json_contains(wrong_dict)


# ========== 响应头断言测试 ==========
@pytest.mark.skip()
def test_assert_response_header(client, response_assert):
    """测试：响应头断言（忽略大小写）"""
    resp = client.get("https://httpbin.org/get")
    assertor = response_assert(resp)
    # 正例：断言Content-Type头
    assertor.assert_response_header(
        "Content-Type", "application/json", msg="响应头断言"
    )
    # 反例：错误的Content-Type
    with pytest.raises(AssertionError):
        assertor.assert_response_header("Content-Type", "text/html")

@pytest.mark.skip()
def test_assert_header_date(client, response_assert):
    """测试：日期类型响应头断言（datetime对比）"""
    resp = client.get("https://httpbin.org/get")
    assertor = response_assert(resp)
    # 提取响应头的Date并转为datetime（UTC时区）
    date_header = resp.headers["Date"]
    actual_date = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z")
    # 正例：断言日期（此处用实际提取的日期，模拟场景）
    assertor.assert_header_date(actual_date, msg="日期响应头断言")
    # 反例：错误的日期
    wrong_date = datetime(2020, 1, 1)
    with pytest.raises(AssertionError):
        assertor.assert_header_date(wrong_date)


# ========== Cookie断言测试 ==========
@pytest.mark.skip()
def test_assert_cookie(client, response_assert):
    """测试：从响应头Set-Cookie中断言Cookie值"""
    # 1. 发送请求：httpbin/cookies/set 会在响应头Set-Cookie中设置指定Cookie
    cookie_name = "test_cookie"
    cookie_value = "123456_headers"
    resp = client.get(
        f"https://httpbin.org/cookies/set?{cookie_name}={cookie_value}",
        allow_redirects=False  # 禁用重定向，避免Cookie被重定向吞掉
    )

    # 2. 验证响应头存在Set-Cookie（前置检查）
    assert "Set-Cookie" in resp.headers, "响应头未返回Set-Cookie"

    # 3. 正例：断言Cookie值（从响应头解析）
    assertor = response_assert(resp)
    assertor.assert_cookie(
        cookie_name=cookie_name,
        expected_value=cookie_value,
        msg="从响应头Set-Cookie断言Cookie值"
    )

    # 4. 反例：断言错误的Cookie值（预期抛出AssertionError）
    wrong_cookie_value = "wrong_789"
    with pytest.raises(AssertionError) as exc_info:
        assertor.assert_cookie(
            cookie_name=cookie_name,
            expected_value=wrong_cookie_value,
            msg="Cookie值错误断言反例"
        )

    # 验证断言失败信息的完整性
    assert f"Cookie[{cookie_name}]" in str(exc_info.value)
    assert str(cookie_value) in str(exc_info.value)  # 实际值
    assert str(wrong_cookie_value) in str(exc_info.value)  # 预期值


# ========== 重定向断言测试 ==========
@pytest.mark.skip()
def test_assert_redirect_count(client, response_assert):
    """测试：重定向次数断言"""
    # 重定向2次（/redirect/2）
    resp = client.get("https://httpbin.org/redirect/2", allow_redirects=True)
    assertor = response_assert(resp)
    # 正例：断言重定向次数为2
    assertor.assert_redirect_count(2, msg="重定向次数断言")
    # 反例：断言次数为1
    with pytest.raises(AssertionError):
        assertor.assert_redirect_count(1)

@pytest.mark.skip()
def test_assert_redirect_chain(client, response_assert):
    """测试：重定向链路断言"""
    # 构造重定向链路（httpbin/redirect/1的链路固定）
    resp = client.get("https://httpbin.org/redirect/1", allow_redirects=True)
    # 实际重定向链路：[原URL, 目标URL]
    expected_chain = [
        "https://httpbin.org/redirect/1",
        "https://httpbin.org/get"
    ]
    assertor = response_assert(resp)
    # 正例：断言链路
    assertor.assert_redirect_chain(expected_chain, msg="重定向链路断言")
    # 反例：错误链路
    wrong_chain = ["https://httpbin.org/wrong"]
    with pytest.raises(AssertionError):
        assertor.assert_redirect_chain(wrong_chain)


# ========== 响应内容断言测试 ==========
@pytest.mark.skip()
def test_assert_content_contains(client, response_assert):
    """测试：响应文本包含指定字符串"""
    resp = client.get("https://httpbin.org/html")  # 返回HTML页面
    assertor = response_assert(resp)
    # 正例：断言包含HTML标签
    assertor.assert_content_contains("<html>", msg="响应内容包含字符串")
    # 反例：不存在的字符串
    with pytest.raises(AssertionError):
        assertor.assert_content_contains("<body wrong>")

@pytest.mark.skip()
def test_assert_content_length(client, response_assert):
    """测试：响应内容长度断言（Content-Length头）"""
    resp = client.get("https://httpbin.org/get")
    assertor = response_assert(resp)
    # 提取实际Content-Length值
    actual_length = int(resp.headers["Content-Length"])
    # 正例：断言长度
    assertor.assert_content_length(actual_length, msg="内容长度断言")
    # 反例：错误长度
    with pytest.raises(AssertionError):
        assertor.assert_content_length(999999)


# ========== URL/查询参数断言测试 ==========
@pytest.mark.skip()
def test_assert_response_url(client, response_assert):
    """测试：响应最终URL断言"""
    # 重定向后的最终URL
    resp = client.get("https://httpbin.org/redirect/1", allow_redirects=True)
    assertor = response_assert(resp)
    # 正例：断言最终URL为/get
    assertor.assert_response_url("https://httpbin.org/get", msg="最终URL断言")
    # 反例：错误URL
    with pytest.raises(AssertionError):
        assertor.assert_response_url("https://httpbin.org/wrong")

@pytest.mark.skip()
def test_assert_query_param(client, response_assert):
    """测试：URL查询参数断言"""
    # 带查询参数的请求：?id=100&name=test
    resp = client.get("https://httpbin.org/get?id=100&name=test")
    assertor = response_assert(resp)
    # 正例：断言id参数值为100
    assertor.assert_query_param("id", "100", msg="查询参数断言")
    # 反例：错误的参数值
    with pytest.raises(AssertionError):
        assertor.assert_query_param("id", "200")


# ========== 耗时断言测试 ==========
@pytest.mark.skip()
def test_assert_elapsed_less_than(client, response_assert):
    """测试：响应耗时小于指定秒数"""
    resp = client.get("https://httpbin.org/get")
    assertor = response_assert(resp)
    # 正例：断言耗时小于1秒（httpbin响应通常<1秒）
    assertor.assert_elapsed_less_than(1.0, msg="耗时断言")
    # 反例：断言耗时小于0.0001秒（几乎不可能）
    with pytest.raises(AssertionError):
        assertor.assert_elapsed_less_than(0.0001)


# ========== 自定义业务规则断言测试 ==========
@pytest.mark.skip()
def test_assert_business_rule(client, response_assert):
    """测试：自定义业务规则断言"""
    # 1. 定义业务规则函数：响应JSON中code等于0则通过
    def business_rule_1(response) -> bool:
        try:
            return response.json().get("json")["code"] == 0
        except:
            return False

    # 2. 构造符合规则的响应
    resp_ok = client.post(
        "https://httpbin.org/post",
        json={"code": 0, "msg": "success"}
    )
    assertor_ok = response_assert(resp_ok)
    # 正例：规则满足
    assertor_ok.assert_business_rule(
        rule_func=business_rule_1,
        rule_desc="业务规则：code=0",
        msg="自定义规则断言正例"
    )

    # 3. 构造不符合规则的响应
    resp_err = client.post(
        "https://httpbin.org/post",
        json={"code": 500, "msg": "error"}
    )
    assertor_err = response_assert(resp_err)
    # 反例：规则不满足，预期抛出AssertionError
    with pytest.raises(AssertionError):
        assertor_err.assert_business_rule(
            rule_func=business_rule_1,
            rule_desc="业务规则：code=0",
            msg="自定义规则断言反例"
        )

    # 4. 测试规则函数执行异常的场景
    def error_rule(response) -> bool:
        raise ValueError("规则函数执行出错")

    with pytest.raises(AssertionError) as exc_info:
        assertor_ok.assert_business_rule(
            rule_func=error_rule,
            rule_desc="错误规则函数",
            msg="规则函数执行异常测试"
        )
    assert "规则函数执行报错" in str(exc_info.value)