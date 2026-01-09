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
