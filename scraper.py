# ======================================================================================
#
#            应急用节点备用
#
#   - 作者: 无
#   - 日期: 2025-09-19 23:21:33
#   - 描述: 此脚本自动获取每日更新的节点，
#     智能重命名它们，添加日期后缀，并生成
#     结构化的 JSON 文件和通用的 Base64 订阅文件。
#
# ======================================================================================

# ----------------------------------------
# 1. 导入所需的核心库
# ----------------------------------------
import requests  # 用于发起网络请求，获取网页和订阅内容
import re        # 用于正则表达式，从网页源码中精确提取订阅链接
import os        # 用于操作系统相关功能，主要是创建文件夹(public)
import datetime  # 用于处理日期和时间，计算今天的URL ID
import yaml      # 用于解析从订阅链接下载的YAML格式的节点配置文件
import json      # 用于将处理后的节点数据生成为格式化的JSON文件
import base64    # 用于将最终的节点链接列表编码成客户端通用的Base64格式
from urllib.parse import quote # 用于URL编码，确保节点名称中的特殊字符不会导致链接格式错误

# ----------------------------------------
# 2. 核心配置区
# ----------------------------------------
# 这是整个脚本的计算基准。如果未来某天脚本失效（比如网站更改了ID规则），
# 您只需要找到当天网站上可用的页面，并用当天的日期和ID更新下面这两行即可。
BASE_ID = 196                     # 基准ID
BASE_DATE_STR = "2025-09-19"      # 基准日期 (格式: YYYY-MM-DD)


def calculate_current_url_and_date():
    """
    根据当前日期计算出当天的目标URL，并返回格式化后的日期字符串。
    这是实现自动访问每日更新页面的核心函数。

    Returns:
        tuple: (计算出的今日URL, 格式为"MM-DD"的日期后缀)
               如果计算失败，则返回 (None, None)
    """
    print("步骤 1: 正在根据当前日期计算目标URL...")
    try:
        # 将字符串格式的基准日期转换为Python的date对象，以便进行计算
        base_date = datetime.datetime.strptime(BASE_DATE_STR, "%Y-%m-%d").date()
        
        # 获取当前的UTC日期。使用UTC可以避免时区问题，确保在任何服务器上运行结果都一致
        today = datetime.datetime.utcnow().date()
        
        # 计算今天与基准日期相差的天数
        delta_days = (today - base_date).days
        
        # 假设ID每天递增1，计算出今天的ID
        current_id = BASE_ID + delta_days
        
        # 拼接成最终的目标URL
        target_url = f"https://nodesdz.com/?id={current_id}"
        
        # 使用 strftime 方法将今天的日期格式化为 "MM-DD" 的形式，例如 "09-20"
        date_suffix = today.strftime("%m-%d")
        
        print(f"生成的今日URL: {target_url}")
        print(f"生成的日期后缀: {date_suffix}")
        
        return target_url, date_suffix

    except Exception as e:
        # 捕获任何可能发生的异常，例如日期格式错误
        print(f"错误：计算URL时发生错误 - {e}")
        return None, None

def create_vless_link_from_clash(proxy):
    """
    将从Clash配置文件中解析出的单个proxy字典，转换为通用的VLESS分享链接(URI)。

    Args:
        proxy (dict): 包含单个节点配置的字典。

    Returns:
        str: 拼接好的VLESS链接，如果节点类型不是vless则返回None。
    """
    if proxy.get("type") != "vless":
        return None
    
    # 使用 quote 函数对节点名称进行URL编码，防止名称中的空格、中文或特殊符号破坏链接结构
    name = quote(proxy.get("name", "Unnamed")) 
    
    # 将Clash配置中的字段映射到VLESS链接的参数
    params = {
        "security": "reality",
        "sni": proxy.get("servername", ""),
        "fp": proxy.get("client-fingerprint", "chrome"),
        "publicKey": proxy.get("reality-opts", {}).get("public-key", ""),
        "shortId": proxy.get("reality-opts", {}).get("short-id", ""),
        "flow": proxy.get("flow", "")
    }
    
    # 使用列表推导式和 & 连接符，高效地拼接URL参数，同时过滤掉值为空的参数
    param_str = '&'.join([f"{k}={v}" for k, v in params.items() if v])
    
    # 按照VLESS URI标准格式拼接最终链接
    return f"vless://{proxy.get('uuid')}@{proxy.get('server')}:{proxy.get('port')}?{param_str}#{name}"

def main():
    """
    主执行函数，串联起整个自动化流程。
    """
    # 首先调用函数计算出今天的URL和日期后缀
    target_url, date_suffix = calculate_current_url_and_date()
    # 如果URL计算失败，则直接退出脚本
    if not target_url:
        return

    try:
        # 步骤 2 & 3: 访问目标网页，并用正则表达式提取出Clash订阅链接
        print(f"步骤 2 & 3: 正在抓取和提取Clash订阅链接...")
        headers = {'User-Agent': 'Mozilla/5.0'} # 模拟浏览器访问
        page_res = requests.get(target_url, headers=headers, timeout=15)
        page_res.raise_for_status() # 如果HTTP请求返回错误状态码，则抛出异常
        
        # 使用正则表达式查找 'clash: "..."' 格式的字符串，并捕获引号内的URL
        match = re.search(r'clash\s*:\s*"(https?://[^\s"]+)"', page_res.text)
        if not match:
            raise ValueError("在页面中未找到Clash订阅链接")
        sub_link = match.group(1) # .group(1) 获取第一个捕获组的内容，即URL本身
        print(f"提取成功 -> {sub_link}")

        # 步骤 4: 访问上一步提取到的订阅链接，下载YAML配置文件内容
        print("步骤 4: 正在下载YAML订阅内容...")
        # 模拟Clash客户端的User-Agent，某些服务器可能会校验这个
        sub_headers = {'User-Agent': 'ClashforWindows/0.20.19'}
        sub_res = requests.get(sub_link, headers=sub_headers, timeout=15)
        sub_res.raise_for_status()
        
        # 步骤 5: 使用PyYAML库解析YAML文本内容为Python字典/列表
        print("步骤 5: 正在解析YAML...")
        # yaml.safe_load 比 yaml.load 更安全，可以防止执行恶意的YAML代码
        data = yaml.safe_load(sub_res.text)
        # 安全地获取 'proxies' 键对应的值，如果不存在，则返回一个空列表，避免出错
        proxies = data.get('proxies', [])
        if not proxies:
            raise ValueError("YAML文件中没有找到proxies")
        
        print(f"解析到 {len(proxies)} 个节点。")
        
        # =================================================================== #
        # =================== 在这里进行自定义名称修改 ====================== #
        # =================================================================== #
        
        print("正在进行智能重命名和地区识别...")
        for proxy in proxies:
            name = proxy.get("name", "")
            
            # 根据节点原始名称中的关键词进行分类重命名
            if "香港" in name:
                proxy["name"] = f"🇭🇰 香港"
            elif "日本" in name:
                proxy["name"] = f"🇯🇵 日本"
            elif "新加坡" in name:
                proxy["name"] = f"🇸🇬 新加坡"
            elif "美国" in name:
                proxy["name"] = f"🇺🇸 美国"
            else:
                # 如果所有关键词都不匹配，则赋予默认名称
                proxy["name"] = f"🇨🇳 中国"

        print(f"正在为节点名称添加日期后缀: {date_suffix}")
        # 遍历所有节点，将日期后缀附加到新名称的末尾
        for proxy in proxies:
            proxy["name"] = f"{proxy['name']} {date_suffix}"

        print("正在为重名节点添加序号...")
        name_counts = {} # 用于计数的字典
        processed_proxies = [] # 存放处理后最终结果的列表
        for proxy in proxies:
            name = proxy.get("name")
            # .get(name, 0) 安全地获取当前名称的计数值，如果没有则从0开始
            current_count = name_counts.get(name, 0) + 1
            name_counts[name] = current_count
            # 只为第二个及以后的同名节点添加序号，保持第一个名称简洁
            if current_count > 1:
                proxy["name"] = f"{name}-{current_count}"
            processed_proxies.append(proxy)
        proxies = processed_proxies # 用处理好的列表覆盖原始列表

        # =================================================================== #
        # ========================= 修改结束 ================================ #
        # =================================================================== #

        # 确保输出目录 'public' 存在，如果不存在则创建
        output_dir = 'public'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # --- 生成最终产物 A: 结构化的JSON文件 ---
        print("正在生成 nodes.json ...")
        json_path = os.path.join(output_dir, 'nodes.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            # json.dump 将Python对象写入文件
            # indent=2 使JSON文件格式化，带缩进，易于阅读
            # ensure_ascii=False 确保中文字符和Emoji能正确显示，而不是被转义成\uXXXX
            json.dump(proxies, f, indent=2, ensure_ascii=False)
        print(f"已将处理后的节点信息保存到 -> {json_path}")

        # --- 生成最终产物 B: 客户端通用的Base64订阅文件 ---
        print("正在生成通用 Base64 订阅文件 sub.txt ...")
        # 使用列表推导式，高效地为处理后的每一个节点生成VLESS链接
        vless_links = [link for proxy in proxies if (link := create_vless_link_from_clash(proxy))]
        
        # 将所有链接用换行符(\n)连接成一个大的字符串
        subscription_text = "\n".join(vless_links)
        
        # 使用 base64 库将上述字符串编码成Base64格式
        encoded_subscription = base64.b64encode(subscription_text.encode('utf-8')).decode('utf-8')
        
        sub_path = os.path.join(output_dir, 'sub.txt')
        with open(sub_path, 'w', encoding='utf-8') as f:
            f.write(encoded_subscription)
        print(f"已将通用订阅文件保存到 -> {sub_path}")

    except Exception as e:
        # 捕获整个流程中可能发生的任何异常，并打印错误信息，方便调试
        print(f"脚本执行失败: {e}")

# ----------------------------------------
# 4. 脚本执行入口
# ----------------------------------------
# 这是Python脚本的标准入口。
# 当直接运行此文件时，__name__ 的值是 "__main__"，于是下面的代码块会被执行。
if __name__ == "__main__":
    main()
