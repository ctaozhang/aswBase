import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Union, Callable
from core.clientbase import ClientBase  # 导入实际的 ClientBase 类

# 复用 ClientBase 的日志配置
logger = logging.getLogger(__name__)


class ResponseAssertor:
    """响应断言工具类（适配pytest原生断言，保留原始断言信息格式化逻辑）"""
    # 断言方法映射字典
    _ASSERTION_MAP: Dict[str, Callable] = {}

    def __init__(self, response, request_id: str = None):
        self.response = response
        self.request_id = request_id or getattr(response, "request_id", "unknown")
        # 复用ClientBase的响应解析方法（base_url为空不影响解析类方法）
        self.client = ClientBase(base_url="")

        # 初始化断言方法映射（如果尚未初始化）
        self._initialize_assertion_map()

    def _initialize_assertion_map(self):
        """初始化断言方法映射表"""
        if not ResponseAssertor._ASSERTION_MAP:
            ResponseAssertor._ASSERTION_MAP = {
                # 状态断言
                "status_code": self.assert_status_code,
                "is_ok": self.assert_is_ok,
                "is_redirect": self.assert_is_redirect,
                "is_permanent_redirect": self.assert_is_permanent_redirect,

                # JSON断言
                "json_field": self.assert_json_field,
                "json_path": self.assert_json_path,
                "json_contains": self.assert_json_contains,

                # 响应头断言
                "response_header": self.assert_response_header,

                # Cookie断言
                "cookie": self.assert_cookie,

                # 重定向断言
                "redirect_count": self.assert_redirect_count,
                "redirect_chain": self.assert_redirect_chain,

                # 响应内容断言
                "content_contains": self.assert_content_contains,
                "content_length": self.assert_content_length,

                # URL/查询参数断言
                "response_url": self.assert_response_url,
                "query_param": self.assert_query_param,

                # 耗时断言
                "elapsed_less_than": self.assert_elapsed_less_than,
            }

    def _format_assert_msg(self, assert_type: str, expected: Any, actual: Any, msg: str = "") -> str:
        """格式化断言失败信息（清晰展示预期/实际值）"""
        base_msg = (
            f"\n===== 断言失败 [req_id={self.request_id}] =====\n"
            f"断言类型：{assert_type}\n"
            f"预期值：{json.dumps(expected, ensure_ascii=False, indent=2) if isinstance(expected, (dict, list)) else expected}\n"
            f"实际值：{json.dumps(actual, ensure_ascii=False, indent=2) if isinstance(actual, (dict, list)) else actual}\n"
        )
        if msg:
            base_msg += f"附加说明：{msg}\n"
        return base_msg

    # ========== 基础响应状态断言 ==========
    def assert_status_code(self, expected_code: int, msg: str = "") -> "ResponseAssertor":
        """断言响应状态码"""
        actual_code = self.client.status_code(self.response)
        assert actual_code == expected_code, self._format_assert_msg(
            assert_type="响应状态码",
            expected=expected_code,
            actual=actual_code,
            msg=msg
        )
        return self

    def assert_is_ok(self, msg: str = "") -> "ResponseAssertor":
        """断言请求成功（状态码200-299）"""
        is_success = self.client.is_ok(self.response)
        actual_code = self.client.status_code(self.response)
        assert is_success, self._format_assert_msg(
            assert_type="请求是否成功",
            expected=True,
            actual=False,
            msg=f"{msg}（实际状态码：{actual_code}）"
        )
        return self

    def assert_is_redirect(self, msg: str = "") -> "ResponseAssertor":
        """断言响应是重定向（3xx 状态码且包含 Location 响应头）"""
        is_redirect_flag = self.client.is_redirect(self.response)
        actual_code = self.client.status_code(self.response)
        assert is_redirect_flag, self._format_assert_msg(
            assert_type="是否为重定向响应",
            expected=True,
            actual=False,
            msg=f"{msg}（实际状态码：{actual_code}）"
        )
        return self

    def assert_is_permanent_redirect(self, msg: str = "") -> "ResponseAssertor":
        """断言响应是永久重定向（301/308 状态码）"""
        is_perm_redirect = self.client.is_permanent_redirect(self.response)
        actual_code = self.client.status_code(self.response)
        assert is_perm_redirect, self._format_assert_msg(
            assert_type="是否为永久重定向",
            expected=True,
            actual=False,
            msg=f"{msg}（实际状态码：{actual_code}）"
        )
        return self

    # ========== JSON 字段断言 ==========
    def assert_json_field(self, field_path: str, expected_value: Any, default: Any = None, encoding: str = None, msg: str = "") -> "ResponseAssertor":
        """断言JSON深层字段值（支持点分隔+数组索引，如data.list[0].id）"""
        actual_value = self.client.extract_json_field(
            self.response, field_path, default=default, encoding=encoding
        )
        assert actual_value == expected_value, self._format_assert_msg(
            assert_type=f"JSON字段[{field_path}]",
            expected=expected_value,
            actual=actual_value,
            msg=msg
        )
        return self

    def assert_json_path(self, jsonpath_expr: str, expected_value: Any, default: Any = None, encoding: str = None, msg: str = "") -> "ResponseAssertor":
        """断言JSONPath提取结果（需安装jsonpath-ng）"""
        actual_value = self.client.extract_json_path(
            self.response, jsonpath_expr, default=default, encoding=encoding
        )
        assert actual_value == expected_value, self._format_assert_msg(
            assert_type=f"JSONPath表达式[{jsonpath_expr}]",
            expected=expected_value,
            actual=actual_value,
            msg=msg
        )
        return self

    def assert_json_contains(self, expected_dict: Dict, encoding: str = None, msg: str = "") -> "ResponseAssertor":
        """断言JSON响应包含指定字典（递归检查键值对）"""

        def _dict_contains(actual: Dict, expected: Dict) -> bool:
            for k, v in expected.items():
                if k not in actual:
                    return False
                if isinstance(v, dict) and isinstance(actual[k], dict):
                    if not _dict_contains(actual[k], v):
                        return False
                elif actual[k] != v:
                    return False
            return True

        actual_json = self.client.json(self.response, default={}, encoding=encoding)
        # 先断言类型是字典
        assert isinstance(actual_json, dict), self._format_assert_msg(
            assert_type="JSON包含指定字典",
            expected=expected_dict,
            actual=f"响应非JSON字典类型（实际类型：{type(actual_json).__name__}）",
            msg=msg
        )
        # 再断言包含指定键值对
        assert _dict_contains(actual_json, expected_dict), self._format_assert_msg(
            assert_type="JSON包含指定字典",
            expected=expected_dict,
            actual=actual_json,
            msg=msg
        )
        return self

    # ========== 响应头断言 ==========
    def assert_response_header(self, header_name: str, expected_value: str, default: str = None, msg: str = "") -> "ResponseAssertor":
        """断言指定响应头的值（忽略大小写）"""
        actual_value = self.client.extract_response_header_by_name(
            self.response, header_name, default=default
        )
        assert actual_value == expected_value, self._format_assert_msg(
            assert_type=f"响应头[{header_name}]",
            expected=expected_value,
            actual=actual_value,
            msg=msg
        )
        return self

    def assert_header_date(self, expected_date: datetime, header_name: str = "Date", default: datetime = None, msg: str = "") -> "ResponseAssertor":
        """断言日期类型响应头的值（datetime对象对比）"""
        actual_date = self.client.extract_header_date(
            self.response, header_name=header_name, default=default
        )
        assert actual_date == expected_date, self._format_assert_msg(
            assert_type=f"日期响应头[{header_name}]",
            expected=expected_date,
            actual=actual_date,
            msg=msg
        )
        return self

    # ========== Cookie 断言 ==========
    def assert_cookie(self, cookie_name: str, expected_value: str, default: str = None, msg: str = "") -> "ResponseAssertor":
        """断言指定Cookie的值"""
        actual_value = self.client.extract_response_cookie_by_name(
            self.response, cookie_name, default=default
        )
        assert actual_value == expected_value, self._format_assert_msg(
            assert_type=f"Cookie[{cookie_name}]",
            expected=expected_value,
            actual=actual_value,
            msg=msg
        )
        return self

    # ========== 重定向断言 ==========
    def assert_redirect_count(self, expected_count: int, msg: str = "") -> "ResponseAssertor":
        """断言重定向次数"""
        actual_count = self.client.redirect_count(self.response)
        assert actual_count == expected_count, self._format_assert_msg(
            assert_type="重定向次数",
            expected=expected_count,
            actual=actual_count,
            msg=msg
        )
        return self

    def assert_redirect_chain(self, expected_chain: List[str], msg: str = "") -> "ResponseAssertor":
        """断言重定向链路（URL列表）"""
        actual_chain = self.client.extract_redirect_chain(self.response)
        assert actual_chain == expected_chain, self._format_assert_msg(
            assert_type="重定向链路",
            expected=expected_chain,
            actual=actual_chain,
            msg=msg
        )
        return self

    # ========== 响应内容断言 ==========
    def assert_content_contains(self, expected_str: str, encoding: str = None, msg: str = "") -> "ResponseAssertor":
        """断言响应文本包含指定字符串"""
        actual_text = self.client.text(self.response, encoding=encoding)
        assert expected_str in actual_text, self._format_assert_msg(
            assert_type="响应文本包含字符串",
            expected=expected_str,
            actual=f"响应文本未包含该字符串（前500字符：{actual_text[:500]}）",
            msg=msg
        )
        return self

    def assert_content_length(self, expected_length: int, msg: str = "") -> "ResponseAssertor":
        """断言响应内容长度（Content-Length头）"""
        actual_length = self.client.content_length(self.response)
        assert actual_length == expected_length, self._format_assert_msg(
            assert_type="响应内容长度",
            expected=expected_length,
            actual=actual_length,
            msg=msg
        )
        return self

    # ========== URL/查询参数断言 ==========
    def assert_response_url(self, expected_url: str, msg: str = "") -> "ResponseAssertor":
        """断言响应最终URL（含重定向）"""
        actual_url = self.client.response_url(self.response)
        assert actual_url == expected_url, self._format_assert_msg(
            assert_type="响应最终URL",
            expected=expected_url,
            actual=actual_url,
            msg=msg
        )
        return self

    def assert_query_param(self, param_name: str, expected_value: Union[str, List[str]], default: Any = None, msg: str = "") -> "ResponseAssertor":
        """断言响应URL中的查询参数值"""
        actual_value = self.client.extract_query_param_by_name(
            self.response, param_name, default=default
        )
        assert actual_value == expected_value, self._format_assert_msg(
            assert_type=f"URL查询参数[{param_name}]",
            expected=expected_value,
            actual=actual_value,
            msg=msg
        )
        return self

    # ========== 耗时断言 ==========
    def assert_elapsed_less_than(self, max_seconds: float, msg: str = "") -> "ResponseAssertor":
        """断言响应耗时小于指定秒数"""
        actual_seconds = self.client.elapsed_seconds(self.response)
        assert actual_seconds <= max_seconds, self._format_assert_msg(
            assert_type="响应耗时（小于指定值）",
            expected=f"≤ {max_seconds}秒",
            actual=f"{actual_seconds:.3f}秒",
            msg=msg
        )
        return self

    # ========== 新增：自定义业务规则断言 ==========
    def assert_business_rule(self, rule_func: callable, rule_desc: str, msg: str = "", **kwargs) -> "ResponseAssertor":
        """
        自定义业务规则断言（支持任意复杂的业务逻辑判断）
        :param rule_func: 业务规则函数，需接收 response 为第一个参数，可接收额外 kwargs，返回布尔值（True=断言通过，False=断言失败）
        :param rule_desc: 业务规则描述（用于断言失败时的类型说明）
        :param msg: 附加说明信息
        :param kwargs: 传递给 rule_func 的额外关键字参数
        :return: self（链式调用）
        """
        # 执行自定义业务规则函数
        try:
            rule_result = rule_func(self.response, **kwargs)
        except Exception as e:
            # 捕获规则函数执行异常，视为断言失败
            assert False, self._format_assert_msg(
                assert_type=f"自定义业务规则执行异常[{rule_desc}]",
                expected="规则函数执行无异常且返回True",
                actual=f"规则函数执行报错：{str(e)[:500]}",
                msg=msg
            )

        # 校验规则函数返回值（必须是布尔值）
        assert isinstance(rule_result, bool), self._format_assert_msg(
            assert_type=f"自定义业务规则返回值异常[{rule_desc}]",
            expected="布尔值（True/False）",
            actual=f"{type(rule_result).__name__}类型，值：{rule_result}",
            msg=msg
        )

        # 规则返回False则断言失败
        rule_context = f"规则函数入参：{kwargs}" if kwargs else "无额外入参"
        assert rule_result, self._format_assert_msg(
            assert_type=f"自定义业务规则[{rule_desc}]",
            expected="True（业务规则满足）",
            actual="False（业务规则不满足）",
            msg=f"{msg}\n{rule_context}"
        )

        # 日志记录：业务规则断言通过
        request_id = getattr(self.response, "request_id", "unknown")
        logger.debug(f"✅ 【业务规则断言】req_id={request_id}，规则[{rule_desc}]验证通过")
        return self

    # ========== 新增：从配置列表执行批量链式断言 ==========
    def assert_from_config(self, assert_config: List[Dict[str, Any]]) -> "ResponseAssertor":
        """
        从配置列表执行批量链式断言
        :param assert_config: 断言配置列表，每个元素为包含type字段的字典，其余为对应断言方法的关键字参数
        :return: self（支持链式调用）
        """
        # 校验配置列表类型
        if not isinstance(assert_config, list):
            raise TypeError(f"assert_config必须是列表类型，实际传入：{type(assert_config).__name__}")

        # 遍历执行每个断言配置
        for idx, assert_item in enumerate(assert_config):
            # 校验单个配置项类型
            if not isinstance(assert_item, dict):
                raise TypeError(f"assert_config第{idx}个元素必须是字典类型，实际传入：{type(assert_item).__name__}")

            # 校验是否包含type字段
            if "type" not in assert_item:
                raise ValueError(
                    f"assert_config第{idx}个元素缺少必填的'type'字段，当前配置项：{json.dumps(assert_item, ensure_ascii=False)}"
                )

            # 提取并校验断言类型
            assert_type = assert_item.pop("type")
            if assert_type not in self._ASSERTION_MAP:
                supported_types = list(self._ASSERTION_MAP.keys())
                raise ValueError(
                    f"assert_config第{idx}个元素的断言类型'{assert_type}'不支持！\n"
                    f"支持的断言类型：{supported_types}\n"
                    f"当前配置项（已弹出type）：{json.dumps(assert_item, ensure_ascii=False)}"
                )

            # 执行断言（链式调用）
            try:
                self._ASSERTION_MAP[assert_type](**assert_item)
            except Exception as e:
                # 包装异常信息，定位出错的配置项
                raise RuntimeError(
                    f"执行assert_config第{idx}个元素的[{assert_type}]断言时失败！\n"
                    f"配置项：{json.dumps({**assert_item, 'type': assert_type}, ensure_ascii=False)}"
                ) from e

        return self
