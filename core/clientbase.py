"""
- 简洁高效的HTTP请求客户端封装
- 简化请求，专注业务
Author: v_ctaozhang
"""
import re
import time
import json
import uuid
import requests
from datetime import datetime
from urllib3.util.retry import Retry
from core.log_config import get_logger
from requests.adapters import HTTPAdapter
from core.data_utils import format_python_to_json
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, parse_qs, unquote


# 使用封装的 get_logger
logger = get_logger(__name__)

class ClientBase():
    """基类：http基础客户端"""

    def __init__(self, base_url: str, timeout=30, default_headers=None, max_retries=3, session=None):
        """
        初始化基础客户端
        :param base_url: 基础URL
        :param timeout: 默认超时时间（秒）
        :param default_headers: 默认请求头
        :param max_retries: 最大重试次数
        :param session: 自定义会话
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.default_headers = default_headers or {}
        self.session = session or requests.session()

        # 配置重试策略
        if max_retries > 0:
            retry_strategy = Retry(total=max_retries,
                  backoff_factor=1,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"])

            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            # DEBUG级：🔧 配置相关
            # 留
            logger.debug(f"🔧 【初始化】重试策略：maxRetry={max_retries}，retryCode={retry_strategy.status_forcelist}")

        # 设置默认请求头
        if self.default_headers:
            self.session.headers.update(self.default_headers)

        # INFO级：✅ 成功标识，快速知晓客户端初始化完成
        # logger.info(f"✅ 【初始化】HTTP客户端创建成功：基础URL={self.base_url}，超时时间={self.timeout}s")

    def _url_join(self, relative_url_path: str) -> str:
        """拼接请求URL（内部辅助方法）"""
        if relative_url_path.startswith("http://") or relative_url_path.startswith("https://"):
            # DEBUG级：🔗 链接相关，标识URL信息
            # logger.debug(f"🔗 【URL拼接】使用外部完整URL：{relative_url_path}")
            return relative_url_path
        full_url = f"{self.base_url}/{relative_url_path.lstrip('/')}"
        # DEBUG级：🔗 链接相关，标识URL信息
        logger.debug(f"🔗 【URL拼接】基础URL+相对路径={full_url}")
        return full_url

    def _request(self, method, relative_url_path, **kwargs) -> requests.Response:
        """
                构建核心请求（内部方法）
                :param method: 请求方法
                :param relative_url_path: 请求URL路径
                :param kwargs: 传递给requests的关键字参数
                :return: requests.Response对象
                """
        # 生成唯一请求ID，方便追踪单次请求的所有日志
        request_id = str(uuid.uuid4())[:8]
        # 拼接URL
        url = self._url_join(relative_url_path)

        # INFO级：🚀 启动标识，快速知晓请求开始
        # 留
        logger.info(f"🚀 【请求开始】req_id={request_id}，方法={method}，URL={url}，超时设置={self.timeout}s")

        # DEBUG级：📋 表单/数据相关，标识请求详情
        req_headers = kwargs.get("headers", self.session.headers)
        # 留
        logger.debug(f"📋 【请求详情】req_id={request_id}，请求头：\n{format_python_to_json(dict(req_headers))}")

        # DEBUG级：📋 表单/数据相关，标识请求体详情
        if 'data' in kwargs:
            data = kwargs.get('data')
            data_str = str(data)[:1000] if len(str(data)) > 1000 else str(data)
            logger.debug(f"📋 【请求详情】req_id={request_id}，请求体[表单]：{data_str}（超长内容已截断）")
        elif 'json' in kwargs:
            json_data = kwargs.get('json')
            try:
                json_str = json.dumps(json_data, ensure_ascii=False)[:1000] if len(json.dumps(json_data)) > 1000 else json.dumps(json_data, ensure_ascii=False)
                logger.debug(f"📋 【请求详情】req_id={request_id}，请求体[JSON]：{json_str}（超长内容已截断）")
            except:
                logger.debug(f"📋 【请求详情】req_id={request_id}，请求体[JSON]：序列化失败，原始数据={str(json_data)[:500]}")

        # 记录请求耗时
        start_time = time.perf_counter()
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            elapsed_time = time.perf_counter() - start_time

            # 给response绑定request_id属性
            response.request_id = request_id

            # INFO级：🏁 完成标识，快速知晓请求结果
            # 留
            logger.info(f"🏁 【请求完成】req_id={request_id}，状态码={response.status_code}，耗时={elapsed_time:.3f}s，重定向次数={len(response.history)}")

            # DEBUG级：📜 响应相关，标识响应详情
            logger.debug(f"📜 【响应详情】req_id={request_id} ↓\n响应头：\n{format_python_to_json(dict(response.headers))}")
            logger.debug(f"📜 【响应详情】req_id={request_id}，最终URL：{response.url}")

            # 响应体日志（超长截断，区分JSON/文本）
            if response.text:
                try:
                    resp_json = response.json()
                    resp_str = json.dumps(resp_json, indent=4, ensure_ascii=False)
                    logger.debug(f"📜 【响应详情】req_id={request_id} ↓ \n响应体[JSON]：\n{resp_str}")
                except:
                    resp_str = response.text
                    logger.debug(f"📜 【响应详情】req_id={request_id}，响应体[文本]：\n{resp_str}")

            # WARNING级：⚠️ 警告标识，提示非致命问题
            if response.history:
                redirect_chain = [resp.url for resp in response.history] + [response.url]
                logger.warning(f"⚠️ 【请求提醒】req_id={request_id}，请求发生重定向，链路：{redirect_chain}")

            return response
        except requests.RequestException as e:
            elapsed_time = time.perf_counter() - start_time
            # ERROR级：❌ 错误标识，突出致命问题
            logger.error(
                f"❌ 【请求失败】req_id={request_id}，方法={method}，URL={url}，耗时={elapsed_time:.3f}s，错误信息={str(e)[:500]}",
                exc_info=True  # 打印完整堆栈跟踪，测试环境调试核心
            )
            raise
        # finally:
        #     # INFO级：🔚 收尾标识，知晓请求流程闭环
        #     logger.info(f"🔚 【请求收尾】req_id={request_id}，请求生命周期结束")

    """========== 请求方法封装 =========="""
    def get(self, relative_url_path: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """封装GET请求"""
        if params:
            # DEBUG级：📊 参数相关，标识查询参数详情
            # 留
            logger.debug(f"📊 【GET请求】查询参数：{params}")
        return self._request('GET', relative_url_path, params=params, **kwargs)

    def post(self, relative_url_path: str, data: Any = None, json: Any = None, **kwargs) -> requests.Response:
        """发送POST请求"""
        if data:
            logger.debug(f"📊 【POST请求】表单参数：{str(data)[:1000]}（超长内容已截断）")
        if json:
            try:
                json_str = json.dumps(json, indent=4, ensure_ascii=False)[:1000]
                logger.debug(f"📊 【POST请求】JSON参数：{json_str}（超长内容已截断）")
            except Exception as e:
                logger.debug(f"📊 【POST请求】JSON参数：序列化失败，原始数据={str(json)[:500]}，错误={str(e)[:100]}")
        return self._request('POST', relative_url_path, data=data, json=json, **kwargs)

    def put(self, relative_url_path: str, data: Any = None, json: Any = None, **kwargs) -> requests.Response:
        """发送PUT请求"""
        if data:
            logger.debug(f"📊 【PUT请求】表单参数：{str(data)[:1000]}（超长内容已截断）")
        if json:
            try:
                json_str = json.dumps(json, indent=4, ensure_ascii=False)[:1000]
                logger.debug(f"📊 【PUT请求】JSON参数：{json_str}（超长内容已截断）")
            except Exception as e:
                logger.debug(f"📊 【PUT请求】JSON参数：序列化失败，原始数据={str(json)[:500]}，错误={str(e)[:100]}")
        return self._request('PUT', relative_url_path, data=data, json=json, **kwargs)

    def delete(self, relative_url_path: str, **kwargs) -> requests.Response:
        """发送DELETE请求"""
        logger.debug(f"📊 【DELETE请求】URL路径：{relative_url_path}，附加参数：{kwargs}")
        return self._request('DELETE', relative_url_path, **kwargs)

    def patch(self, relative_url_path: str, data: Any = None, json: Any = None, **kwargs) -> requests.Response:
        """发送PATCH请求"""
        if data:
            logger.debug(f"📊 【PATCH请求】表单参数：{str(data)[:1000]}（超长内容已截断）")
        if json:
            try:
                json_str = json.dumps(json, ensure_ascii=False)[:1000]
                logger.debug(f"📊 【PATCH请求】JSON参数：{json_str}（超长内容已截断）")
            except Exception as e:
                logger.debug(f"📊 【PATCH请求】JSON参数：序列化失败，原始数据={str(json)[:500]}，错误={str(e)[:100]}")
        return self._request('PATCH', relative_url_path, data=data, json=json, **kwargs)

    def head(self, relative_url_path: str, **kwargs) -> requests.Response:
        """发送HEAD请求"""
        logger.debug(f"📊 【HEAD请求】URL路径：{relative_url_path}，附加参数：{kwargs}")
        return self._request('HEAD', relative_url_path, **kwargs)

    def options(self, relative_url_path: str, **kwargs) -> requests.Response:
        """发送OPTIONS请求"""
        logger.debug(f"📊 【OPTIONS请求】URL路径：{relative_url_path}，附加参数：{kwargs}")
        return self._request('OPTIONS', relative_url_path, **kwargs)

    """========== 基础响应元数据提取 =========="""
    def json(self, response: requests.Response, default: Any = None, encoding: Optional[str] = None) -> Any:
        """
        获取JSON格式响应，支持默认值和指定编码
        :param response: 响应对象
        :param default: 解析失败时返回的默认值
        :param encoding: 响应编码（优先使用，无则自动识别）
        :return: JSON解析结果或默认值
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        try:
            if encoding:
                response.encoding = encoding
            result = response.json()
            # DEBUG级：📊 数据提取相关，标识解析成功
            # logger.debug(f"📊 【数据返回】req_id={request_id}，JSON解析成功。")
            return result
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # WARNING级：⚠️ 警告标识，提示非致命解析失败
            logger.warning(f"⚠️ 【数据返回】req_id={request_id}，JSON解析失败：{str(e)}，返回默认值：{default}")
            return default

    def text(self, response: requests.Response, encoding: Optional[str] = None) -> str:
        """
        获取文本响应，支持手动指定编码解决乱码
        :param response: 响应对象
        :param encoding: 手动指定编码（如utf-8、gbk）
        :return: 解码后的文本
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        if encoding:
            response.encoding = encoding
            logger.debug(f"📝 【文本返回】req_id={request_id}，手动指定编码：{encoding}")
        # text_content = response.text[:500] if len(response.text) > 500 else response.text
        logger.debug(f"📝 【文本返回】req_id={request_id}，返回文本内容成功")
        return response.text

    def content(self, response: requests.Response) -> bytes:
        """获取二进制数据响应（如图片、文件）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        content_len = len(response.content) if response.content else 0
        logger.debug(f"🗂️ 【二进制返回】req_id={request_id}，返回二进制数据长度：{content_len}字节")
        return response.content

    def status_code(self, response: requests.Response) -> int:
        """获取响应状态码"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        code = response.status_code
        logger.debug(f"📊 【状态码提取】req_id={request_id}，响应状态码：{code}")
        return code

    def response_url(self, response: requests.Response) -> str:
        """提取响应的最终URL（处理重定向后的实际URL）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        final_url = response.url
        logger.debug(f"🔗 【URL提取】req_id={request_id}，响应最终URL：{final_url}")
        return final_url

    def encoding(self, response: requests.Response) -> Optional[str]:
        """提取响应编码"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        enc = response.encoding
        logger.debug(f"🔤 【编码提取】req_id={request_id}，响应编码：{enc or '自动识别'}")
        return enc

    def is_ok(self, response: requests.Response) -> bool:
        """判断请求是否成功（状态码 200-299 返回 True）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        is_success = response.ok
        # 留
        logger.debug(f"✅ 【状态判断】req_id={request_id}，请求是否成功：{is_success}（状态码：{response.status_code}）")
        return is_success

    """========== 响应头提取 =========="""
    def headers(self, response: requests.Response) -> Dict[str, str]:
        """提取全部响应头（转换为普通字典，方便操作）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        header_dict = dict(response.headers)
        logger.debug(f"📨 【响应头提取】req_id={request_id}，提取到{len(header_dict)}个响应头字段")
        return header_dict

    def extract_response_header_by_name(self, response: requests.Response, header_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        提取指定名称的响应头（忽略大小写）
        :param response: 响应对象
        :param header_name: 要提取的响应头字段名称(如‘Content-Type’)
        :param default: 字段不存在时返回的默认值
        :return:
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        header_value = response.headers.get(header_name, default)
        if header_value is default:
            logger.warning(f"⚠️ 【响应头提取】req_id={request_id}，未找到响应头字段：{header_name}，返回默认值：{default}")
        else:
            logger.debug(f"🔍 【响应头提取】req_id={request_id}，提取字段[{header_name}]值：{header_value}")
        return header_value

    def extract_header_date(self, response: requests.Response, header_name: str = "Date", default: Optional[datetime] = None) -> Optional[datetime]:
        """
        提取日期类型响应头并转换为datetime对象
        :param response: 响应对象
        :param header_name: 日期类型响应头（默认Date）
        :param default: 解析失败返回的默认值
        :return: datetime对象或默认值
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        date_str = self.extract_response_header_by_name(response, header_name)
        if not date_str:
            logger.warning(f"⚠️ 【日期头提取】req_id={request_id}，未找到日期响应头[{header_name}]，返回默认值：{default}")
            return default
        try:
            # 解析HTTP标准日期格式：例："Mon, 05 Jan 2026 08:30:59 GMT"
            date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
            logger.debug(f"📅 【日期头提取】req_id={request_id}，解析[{header_name}]成功：{date_obj}")
            return date_obj
        except (ValueError, TypeError) as e:
            logger.error(f"❌ 【日期头提取】req_id={request_id}，解析失败：{str(e)[:200]}，返回默认值：{default}")
            return default

    """========== Cookie提取 =========="""
    def cookies(self, response: requests.Response) -> Dict[str, str]:
        """提取全部响应Cookie（转换为普通字典，方便操作）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        cookie_dict = dict(response.cookies)
        logger.debug(f"🍪 【Cookie提取】req_id={request_id}，提取到{len(cookie_dict)}个Cookie：{cookie_dict}")
        return cookie_dict

    def extract_response_cookie_by_name(self, response: requests.Response, cookie_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        提取指定名称的Cookie值
        Args:
            response: 响应对象
            cookie_name: Cookie名称
            default: Cookie不存在时返回的默认值
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        cookie_value = response.cookies.get(cookie_name, default)
        if cookie_value is default:
            logger.warning(f"⚠️ 【Cookie提取】req_id={request_id}，未找到Cookie[{cookie_name}]，返回默认值：{default}")
        else:
            logger.debug(f"🍪🔍 【Cookie提取】req_id={request_id}，提取Cookie[{cookie_name}]值：{cookie_value}")
        return cookie_value

    def extract_cookie_dict_with_details(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        提取Cookie的详细信息（名称、值、域名、路径、过期时间等）
        :param response: 响应对象
        :return: Cookie详细信息列表
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        cookie_details = []
        for cookie in response.cookies:
            cookie_details.append({
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "expires": cookie.expires,
                "secure": cookie.secure,
                "httponly": cookie.http_only
            })
        logger.debug(f"🍪📋 【Cookie提取】req_id={request_id}，提取到{len(cookie_details)}个Cookie详细信息：{cookie_details}")
        return cookie_details

    """========== 重定向提取 =========="""
    def redirect_history(self, response: requests.Response) -> List[requests.Response]:
        """提取重定向历史记录（返回重定向过程中的所有响应对象列表）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        history_count = len(response.history)
        # 修正：删除Cookie相关错误日志，替换为重定向相关正确日志
        logger.debug(f"🔄 【重定向提取】req_id={request_id}，提取到{history_count}条重定向历史记录")
        return response.history

    def redirect_count(self, response: requests.Response) -> int:
        """提取重定向次数"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        count = len(response.history)
        logger.debug(f"🔄📊 【重定向提取】req_id={request_id}，重定向次数：{count}")
        return count

    def is_redirect(self, response: requests.Response) -> bool:
        """判断当前的响应是否为重定向（3xx 状态码且包含 Location 响应头）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        is_redirect_flag = response.is_redirect
        logger.debug(f"🔄❓ 【重定向判断】req_id={request_id}，是否为当前响应重定向：{is_redirect_flag}（状态码：{response.status_code}）")
        return is_redirect_flag

    def is_permanent_redirect(self, response: requests.Response) -> bool:
        """判断响应是否为永久重定向（301、308 状态码）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        is_perm_redirect = response.is_permanent_redirect
        logger.debug(f"🔄🔒 【重定向判断】req_id={request_id}，是否为永久重定向：{is_perm_redirect}（状态码：{response.status_code}）")
        return is_perm_redirect

    def extract_redirect_chain(self, response: requests.Response) -> List[str]:
        """
        提取完整重定向链路（包含原始URL和所有重定向URL、最终URL）
        :param response: 响应对象
        :return: 重定向URL列表
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        chain = [resp.url for resp in response.history]
        chain.append(response.url)
        logger.debug(f"🔄🔗 【重定向提取】req_id={request_id}，重定向链路：{chain}")
        # 修正：添加返回语句，返回构建完成的重定向链路
        return chain

    """========== 耗时与内容长度提取 =========="""
    def elapsed_seconds(self, response: requests.Response) -> float:
        """提取响应耗时（秒级，微秒精度）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        elapsed = response.elapsed.total_seconds()
        logger.debug(f"⏱️ 【耗时提取】req_id={request_id}，响应耗时：{elapsed:.6f}秒")
        return elapsed

    def elapsed_details(self, response: requests.Response) -> Dict[str, int]:
        """提取响应耗时详情（天、秒、微秒）"""
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        elapsed_detail = {
            'days': response.elapsed.days,
            'seconds': response.elapsed.seconds,
            'microseconds': response.elapsed.microseconds
        }
        logger.debug(f"⏱️📊 【耗时提取】req_id={request_id}，响应耗时详情：{elapsed_detail}")
        return elapsed_detail

    def content_length(self, response: requests.Response) -> Optional[int]:
        """
        提取响应内容长度（从 Content-Length 响应头获取，容错处理）
        注意：如果响应是分块传输（Transfer-Encoding: chunked），返回 None
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        content_len = self.extract_response_header_by_name(response, 'Content-Length')
        if not content_len:
            logger.debug(f"📏 【长度提取】req_id={request_id}，未找到Content-Length响应头（可能为分块传输），返回None")
            return None
        try:
            length = int(content_len)
            logger.debug(f"📏 【长度提取】req_id={request_id}，响应内容长度：{length}字节")
            return length
        except (ValueError, TypeError) as e:
            logger.error(f"❌ 【长度提取】req_id={request_id}，内容长度转换失败：{str(e)[:200]}，返回None")
            return None

    """========== 核心增强：JSON深层数据安全提取 =========="""
    def extract_json_field(self, response: requests.Response, field_path: str, default: Any = None, encoding: Optional[str] = None) -> Any:
        """
        安全提取JSON深层字段，支持点分隔符（如 "data.user.id"）和列表索引（如 "data.list[0].name"）
        :param response: 响应对象
        :param field_path: 字段路径（例：data.user.id、data.list[2].title）
        :param default: 字段不存在/解析失败时返回的默认值
        :param encoding: JSON编码
        :return: 字段值或默认值
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        # 先解析完整JSON
        json_data = self.json(response, default=default, encoding=encoding)
        if json_data is default:
            logger.warning(f"⚠️ 【字段提取】req_id={request_id}，JSON解析失败，无法提取字段{field_path}")
            return default

        # 拆分路径片段（按.分割，避开数组内的.）
        path_segments = re.split(r'\.(?![^\[]*\])', field_path)
        current_data = json_data

        try:
            for segment in path_segments:
                # 场景1：处理数组索引（支持 [0]开头 或 slides[0] 两种格式）
                if segment.startswith('[') and segment.endswith(']'):
                    # 顶层数组场景：[0]
                    try:
                        index = int(segment.strip('[]'))
                        current_data = current_data[index]
                    except (ValueError, IndexError, TypeError):
                        logger.error(f"❌【字段提取】req_id={request_id}，顶层数组索引{segment}无效")
                        return default
                elif '[' in segment and ']' in segment:
                    # 字典嵌套数组场景：例如：slides[0] / items[1]
                    match = re.match(r'([^\[]+)\[(\d+)\]', segment)
                    if not match:
                        # 留
                        logger.error(f"❌【字段提取】req_id={request_id}，路径片段{segment}格式错误")
                        return default
                    list_name, index_str = match.groups()
                    current_data = current_data[list_name]
                    current_data = current_data[int(index_str)]
                else:
                    # 场景2：普通字典键
                    current_data = current_data[segment]
            # DEBUG级：📊 数据提取相关，标识字段提取成功
            logger.debug(f"📊 【字段提取】req_id={request_id}，成功提取字段{field_path}，值：{str(current_data)[:500]}")
            return current_data
        except (KeyError, IndexError, TypeError) as e:
            # ERROR级：❌ 错误标识，突出字段提取失败
            logger.error(f"❌ 【字段提取】req_id={request_id}，字段{field_path}提取失败：{str(e)}，返回默认值：{default}")
            return default

    def extract_json_path(self, response: requests.Response, jsonpath_expr: str, default: Any = None, encoding: Optional[str] = None) -> Any:
        """
        基于JSONPath提取深层数据（支持复杂表达式，需安装 jsonpath-ng）
        示例：jsonpath_expr = "$.data.user[*].id"（提取所有用户id）
        :param response: 响应对象
        :param jsonpath_expr: JSONPath表达式
        :param default: 提取失败返回的默认值
        :param encoding: JSON编码
        :return: 提取结果或默认值
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        try:
            from jsonpath_ng import parse
        except ImportError:
            logger.error("❌ 【JSONPath提取】缺少依赖 jsonpath-ng，请执行 pip install jsonpath-ng")
            raise ImportError("缺少依赖 jsonpath-ng，请执行 pip install jsonpath-ng")

        json_data = self.json(response, default=default, encoding=encoding)
        if json_data is default:
            logger.warning(f"⚠️ 【JSONPath提取】req_id={request_id}，JSON解析失败，无法提取表达式{jsonpath_expr}")
            return default

        try:
            jsonpath_obj = parse(jsonpath_expr)
            matches = [match.value for match in jsonpath_obj.find(json_data)]
            result = matches[0] if len(matches) == 1 else matches if matches else default
            if result is default:
                logger.warning(f"⚠️ 【JSONPath提取】req_id={request_id}，\n表达式{jsonpath_expr}\n未匹配到数据，返回默认值：{default}")
            else:
                # 修正：补全日志内容，输出提取结果
                logger.debug(f"📊🔍 【JSONPath提取】req_id={request_id}，\n表达式{jsonpath_expr}\n提取结果：{str(result)[:500]}")
            return result
        except Exception as e:
            logger.error(f"❌ 【JSONPath提取】req_id={request_id}，\n表达式{jsonpath_expr}\n提取失败：{str(e)[:200]}，返回默认值：{default}")
            return default

    def extract_json_filtered(self, response: requests.Response, keep_mapping: Dict[str, str], default: Dict = None, encoding: Optional[str] = None) -> Dict:
        """
        提取JSON并过滤字段（仅支持字典格式的路径-别名映射，强制自定义键名）
        :param response: 响应对象
        :param keep_mapping: 必传字典 → 键：要提取的字段路径（如"[0].id"），值：自定义别名（如"first_comment_id"）
        :param default: 提取失败时返回的默认字典
        :param encoding: 响应编码
        :return: 过滤后的新字典（键为自定义别名，值为提取的字段值）
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        default = default or {}

        # 严格校验参数类型：仅接受字典
        if not isinstance(keep_mapping, dict):
            error_msg = f"【JSON过滤】req_id={request_id}，参数keep_mapping必须是字典类型（路径-别名映射），当前传入类型：{type(keep_mapping).__name__}"
            logger.error(f"❌ {error_msg}")
            return default

        # 解析原始JSON（容错：非字典/数组直接返回默认值）
        json_data = self.json(response, default=default, encoding=encoding)
        if not isinstance(json_data, (dict, list)):
            logger.error(f"❌ 【JSON过滤】req_id={request_id}，响应数据非字典/数组类型，无法提取字段，返回默认值：{default}")
            return default

        # 按字典映射提取字段，以别名为键
        result = {}
        for field_path, alias in keep_mapping.items():
            # 提取字段值
            field_value = self.extract_json_field(response, field_path, default=None, encoding=encoding)

            if field_value is not None:
                result[alias] = field_value
                logger.debug(f"📦 【JSON过滤】req_id={request_id}，映射成功 → 路径：{field_path} → 别名：{alias} = {str(field_value)[:500]}")
            else:
                # 提取失败时：若默认字典有该别名，取默认值；否则跳过
                if alias in default:
                    result[alias] = default[alias]
                    logger.warning(f"⚠️ 【JSON过滤】req_id={request_id}，路径{field_path}提取失败，使用默认值：{alias} = {default[alias]}")
                else:
                    logger.warning(f"⚠️ 【JSON过滤】req_id={request_id}，路径{field_path}提取失败，跳过该字段（别名：{alias}）")

        # 日志输出最终结果
        logger.debug(f"📦 【JSON过滤】req_id={request_id}，最终结果（别名作为键）：{result}")
        return result or default

    """========== 增强：URL与查询参数精细化提取 =========="""
    def extract_response_query_params(self, response: requests.Response) -> Dict[str, List[str]]:
        """
        提取响应URL中的查询参数（结构化转换为字典，支持多值参数）
        :param response: 响应对象
        :return: 查询参数字典（值为列表，兼容多值参数）
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        # 解码URL编码的参数值
        decoded_params = {k: [unquote(v) for v in vs] for k, vs in query_params.items()}
        logger.debug(f"🔍📊 【参数提取】req_id={request_id}，提取URL查询参数：{decoded_params}")
        return decoded_params

    def extract_query_param_by_name(self, response: requests.Response, param_name: str, default: Optional[Union[str, List[str]]] = None) -> Any:
        """
        提取指定名称的查询参数值
        :param response: 响应对象
        :param param_name: 查询参数名称
        :param default: 参数不存在返回的默认值
        :return: 单个参数值（单值）、参数值列表（多值）或默认值
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        query_params = self.extract_response_query_params(response)
        if param_name not in query_params:
            logger.warning(f"⚠️ 【参数提取】req_id={request_id}，未找到查询参数[{param_name}]，返回默认值：{default}")
            return default
        param_values = query_params[param_name]
        result = param_values[0] if len(param_values) == 1 else param_values
        logger.debug(f"🔍🔑 【参数提取】req_id={request_id}，提取查询参数[{param_name}]值：{result}")
        return result


    def extract_url_path_segments(self, response: requests.Response) -> List[str]:
        """
        提取响应URL的路径片段（拆分路径为列表）
        示例：https://api.example.com/users/1001 -> ["users", "1001"]
        :param response: 响应对象
        :return: 路径片段列表
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        parsed_url = urlparse(response.url)
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        logger.debug(f"🔗📂 【URL提取】req_id={request_id}，提取URL路径片段：{path_segments}")
        return path_segments

    """========== 增强：表单响应与结构化数据提取 =========="""
    def extract_form_data(self, response: requests.Response, encoding: str = "utf-8") -> Optional[Dict[str, List[str]]]:
        """
        提取响应体中的表单数据（application/x-www-form-urlencoded 格式）
        :param response: 响应对象
        :param encoding: 编码格式
        :return: 表单参数字典或None
        """
        request_id = getattr(response, "request_id", str(uuid.uuid4())[:8])
        content_type = self.extract_response_header_by_name(response, "Content-Type", "")
        if "application/x-www-form-urlencoded" not in content_type:
            logger.warning(f"⚠️ 【表单提取】req_id={request_id}，响应内容类型[{content_type}]非表单格式，无法提取")
            return None

        try:
            form_text = self.text(response, encoding=encoding)
            form_data = parse_qs(form_text)
            decoded_form = {k: [unquote(v) for v in vs] for k, vs in form_data.items()}
            logger.debug(f"📝📋 【表单提取】req_id={request_id}，提取表单数据：{decoded_form}")
            return decoded_form
        except Exception as e:
            logger.error(f"❌ 【表单提取】req_id={request_id}，表单数据提取失败：{str(e)[:200]}，返回None")
            return None

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
            # DEBUG级：🗑️ 资源释放相关，标识会话关闭
            # 留
            logger.debug(f"🗑️ 【资源释放】HTTP会话已成功关闭")

    # 上下文管理器支持
    def __enter__(self):
        logger.debug(f"📥 【上下文管理】进入ClientBase上下文id: <{id(self.session)}> ，会话已初始化")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type:
            logger.warning(f"📤 【上下文管理】退出ClientBase上下文id: <{id(self.session)}>，捕获到异常：{exc_type.__name__}: {exc_val}")
        else:
            logger.debug(f"📤 【上下文管理】正常退出ClientBase上下文id: <{id(self.session)}>，会话已关闭")


if __name__ == '__main__':

    with ClientBase(base_url="https://httpbin.org", timeout=10, max_retries=3) as client:
        logger.debug(client.base_url)
        logger.debug(client.session)
        logger.debug(client.default_headers)

        response = client.get('/get', params={"test_key": "test_val"})

        logger.debug(client.json(response))
        logger.debug(client.text(response))
        logger.debug(client.content(response))
        logger.debug(client.status_code(response))
        logger.debug(client.response_url(response))
        logger.debug(client.encoding(response))
        logger.debug(client.is_ok(response))
        logger.debug(client.headers(response))
        logger.debug(client.extract_response_header_by_name(response, 'Server'))

        logger.debug(client.extract_header_date(response))

        logger.debug(client.elapsed_seconds(response))
        logger.debug(client.elapsed_details(response))

        logger.debug(client.content_length(response))

        logger.debug(client.extract_json_field(response, 'headers.Accept-Encoding'))

        logger.debug(client.extract_json_path(response, "$.args"))
        logger.debug(client.extract_json_path(response, "$.headers.Accept"))

        logger.debug(client.extract_json_filtered(response, {'origin': 'origin', 'args.test_key': 'test_key'}))

        logger.debug(client.extract_response_query_params(response))
        logger.debug(client.extract_query_param_by_name(response, 'test_key'))
        logger.debug(client.extract_url_path_segments(response))
    """
    with ClientBase(base_url="http://httpbin.org", timeout=10,max_retries=3) as client:
        response = client.get('/redirect/2')
        # cookies 和 重定向需要换 url
        logger.debug(client.cookies(response))

        logger.debug(client.redirect_history(response))
        logger.debug(client.redirect_count(response))
        logger.debug(client.is_redirect(response))
        logger.debug(client.is_permanent_redirect(response))
        logger.debug(client.extract_redirect_chain(response))

    with ClientBase(base_url="https://jsonplaceholder.typicode.com", timeout=10) as client:
        # 获取帖子1的评论（返回评论数组）
        response = client.get("/posts/1/comments")
        logger.debug(client.extract_json_field(response, '[0].id'))
        logger.debug(client.extract_json_filtered(response, {'[0]': 'first', '[1].id': "id"}))

    with ClientBase(base_url="https://httpbin.org", timeout=10) as client:
        # POST自定义数组，httpbin会原样返回在json字段中
        resp = client.post("/post", json={
            "name": "测试数组",
            "tags": ["python", "http", "array"],  # 简单字符串数组
            "data": [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]  # 对象数组
        })
        # 提取自定义的tags数组
        tags_array = client.extract_json_field(resp, "json.tags", default=[])
        print("自定义tags数组：", tags_array)
        # 提取data数组第1个元素的value
        data_value = client.extract_json_field(resp, "json.data[1].value", default="")
        print("data数组第1个元素value：", data_value)
        data_value_path = client.extract_json_path(resp, '$..id')
        print(f"所有的id元素:{data_value_path}")

    使用Postman Echo的/post接口（稳定可用）
    with ClientBase(base_url="https://postman-echo.com", timeout=10) as client:
        # ========== 场景1：模拟x-www-form-urlencoded格式响应（验证提取方法） ==========
        print("===== 场景1：提取x-www-form-urlencoded格式响应 =====")
        # 1. 发送表单数据到/post接口（接口会返回请求的表单数据）
        form_data = {
            "name": "张三",
            "age": "20",
            "hobby": ["篮球", "游泳"],
            "url": "https://example.com?a=1&b=2"
        }
        resp = client.post(
            "/post",
            data=form_data,  # 发送表单数据
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
        )

        # 2. 从响应的JSON中提取表单数据，构造x-www-form-urlencoded格式的字符串
        resp_json = client.json(resp)
        form_body = ""
        for k, vs in resp_json["form"].items():
            # 处理多值参数（如hobby）
            if isinstance(vs, list):
                for v in vs:
                    form_body += f"{k}={requests.utils.quote(v)}&"
            else:
                form_body += f"{k}={requests.utils.quote(vs)}&"
        form_body = form_body.rstrip("&")  # 去掉末尾的&

        # 3. 模拟响应为x-www-form-urlencoded格式（修改响应对象的属性）
        # 替换响应体为表单字符串
        resp._content = form_body.encode("utf-8")
        # 设置响应头为x-www-form-urlencoded
        resp.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"

        # 4. 提取表单数据
        extracted_form = client.extract_form_data(resp, encoding="utf-8")
        print(f"提取结果：{extracted_form}")

        # 5. 验证提取结果
        assert extracted_form == {
            "name": ["张三"],
            "age": ["20"],
            "hobby": ["篮球", "游泳"],
            "url": ["https://example.com?a=1&b=2"]
        }, "场景1提取失败"
        print("场景1验证通过✅\n")

        # ========== 场景2：非表单格式响应（对比验证） ==========
        print("===== 场景2：非表单格式，提取失败 =====")
        resp2 = client.get("/json")  # 返回JSON格式
        extracted_form2 = client.extract_form_data(resp2)
        print(f"提取结果：{extracted_form2}")  # 输出None
        assert extracted_form2 is None, "场景2验证失败"
        print("场景2验证通过✅")"""
