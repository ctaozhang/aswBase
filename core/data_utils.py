import os
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple

def load_yaml_cases(yaml_file_name: str, case_key: str) -> List[Dict[str, Any]]:
    """
    加载yaml文件，返回列表，列表内包含字典
    yaml_file_name：请把测试数据yaml文件放置于 tests目录/testdata目录下/  对应要加载的yaml文件名称, 例："chuan_can.yaml"
    case_key: 需要提取的测试键名，例如(基于chuan_can.yaml中的样例)："login_cases"
    """

    current_file = Path(__file__)
    # 根目录/tests/testdata/
    yaml_path = current_file.parent.parent / 'tests' / "testdata" / yaml_file_name
    # 加载yaml数据异常捕获
    try:
        with open(yaml_path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"未找到YAML文件：{yaml_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAML格式错误：{yaml_path}，错误：{str(e)}")

    if case_key not in yaml_data:
        raise KeyError(f"未找到用例键：{case_key}，可用键：{list(yaml_data.keys())}")
    # 加载出当前case_key下的所有用例
    cases = yaml_data[case_key]
    # 校验用例结构（desc, data）
    for idx, case in enumerate(cases):
        if "desc" not in case:
            raise ValueError(f"第{idx+1}条用例缺少必填字段：desc")
        if "data" not in case or "assert_config" not in case:
            raise ValueError(f"第{idx+1}条用例缺少data/assert_config字段")
        # 确保desc是字符串（处理YAML中desc可能的格式问题）
        if not isinstance(case["desc"], str):
            raise TypeError(f"第{idx+1}条用例的desc必须是字符串，当前类型：{type(case['desc'])}")
    return cases

def parse_yaml_to_params(yaml_file: str, case_key: str) -> Tuple[List[str], List[tuple], List[str]]:
    """解析yaml格式数据，组装返回"""

    cases = load_yaml_cases(yaml_file, case_key)
    if not cases:
        raise ValueError(f"{case_key} 下无测试用例")

    # 提取所有用例的data键，去重后排序
    all_data_keys = set()
    for case in cases:
        all_data_keys.update(case["data"].keys())
    param_names = sorted(list(all_data_keys)) + ["assert_config"]

    # 组装参数值（缺失的键值用None填充）
    param_values = []
    case_ids = []
    for case in cases:
        # 确保键和值对应
        data_values = [case["data"].get(key, None) for key in param_names[:-1]]
        # 组合data_value 和 assert_config值
        param_tuple = tuple(data_values) + (case["assert_config"],)
        # 往值列表里面装
        param_values.append(param_tuple)
        # 收集desc作为用例ID
        case_ids.append(case["desc"].strip())  # 去除首尾空格，避免格式问题

    # 进行返回tuple（参数名列表, 参数值列表，用例名列表）
    return param_names, param_values, case_ids

def format_python_to_json(data: any, indent: int = 4, ensure_ascii: bool = False, sort_keys: bool = False) -> str:
    """
    将Python数据转换为格式化的JSON字符串

    参数说明：
    - data: 待转换的Python数据（支持可序列化的类型，见下方说明）
    - indent: JSON缩进空格数，默认4（更易读）
    - ensure_ascii: 是否强制ASCII编码，默认False（保留中文/特殊符号）
    - sort_keys: 是否按字母序排序字典的key，默认False（保留原顺序）

    返回值：
    - 成功：格式化的JSON字符串
    - 失败：包含错误信息的提示字符串
    """
    try:
        # 核心转换逻辑
        json_str = json.dumps(
            data,
            indent=indent,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            # 额外处理：兼容datetime等特殊类型（可选）
            default=lambda obj: str(obj) if hasattr(obj, '__str__') else repr(obj)
        )
        return json_str
    except TypeError as e:
        return f"转换失败：数据类型不可序列化 → {str(e)}"
    except Exception as e:
        return f"转换异常：{str(e)}"

# 配置读取，根限制为字典类型
def read_json_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    通用的 JSON 文件读取函数，具备完善的异常处理

    Args:
        file_path: JSON 文件路径（相对/绝对路径）
        encoding: 文件编码，默认 utf-8

    Returns:
        解析后的 JSON 数据（字典格式）

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
        PermissionError: 文件无读取权限
        Exception: 其他未知错误
    """
    # 校验文件路径是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON 文件不存在,请确认是否保存在config目录：{file_path}")

    # 校验是否是文件（而非目录）
    if not os.path.isfile(file_path):
        raise IsADirectoryError(f"指定路径不是文件：{file_path}")

    try:
        with open(file_path, "r", encoding=encoding) as f:
            # 读取并解析 JSON
            data = json.load(f)

            # 确保返回的是字典（JSON 根节点通常为对象）
            if not isinstance(data, dict):
                raise TypeError(f"JSON 文件根节点必须是对象（字典），当前类型：{type(data)}")

            return data

    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"JSON 格式错误：{str(e)}", e.doc, e.pos)
    except PermissionError:
        raise PermissionError(f"无读取权限：{file_path}")
    except Exception as e:
        raise Exception(f"读取 JSON 文件失败：{str(e)}")

# 加载环境配置
def load_env_config(
        config_file: str = "client_config.json",
        env_var: str = "currentEnv",
        encoding: str = "utf-8"
) -> Dict[str, Any]:
    """
    适配多环境的配置加载函数（基于 JSON 配置文件）

    Args:
        config_file: 配置文件路径，默认 config.json
        env_var: 默认环境：development
        encoding: 文件编码

    Returns:
        指定环境的配置字典
    """
    current_file = Path(__file__)
    # 根目录/config
    config_path = current_file.parent.parent / 'config' / config_file
    # 1. 读取 JSON 配置文件
    all_config = read_json_file(config_path, encoding)

    # 2. 获取当前环境（环境变量 > 默认值）
    current_env = all_config.get(env_var)

    # 3. 验证环境是否存在
    if current_env not in all_config:
        raise ValueError(
            f"环境 {current_env} 不存在！配置文件中包含的环境：{list(all_config.keys())}"
        )

    # 4. 返回指定环境的配置
    env_config = all_config[current_env]

    return env_config