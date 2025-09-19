# scraper.py
import requests
import re
import os
import datetime
import yaml
import json
import base64
from urllib.parse import quote

# --- 核心配置区 ---
BASE_ID = 196
BASE_DATE_STR = "2025-09-19"

def calculate_current_url():
    """根据当前日期计算出当天的目标URL。"""
    print("步骤 1: 正在根据当前日期计算目标URL...")
    try:
        base_date = datetime.datetime.strptime(BASE_DATE_STR, "%Y-%m-%d").date()
        today = datetime.datetime.utcnow().date()
        delta_days = (today - base_date).days
        current_id = BASE_ID + delta_days
        target_url = f"https://nodesdz.com/?id={current_id}"
        print(f"生成的今日URL: {target_url}")
        return target_url
    except Exception as e:
        print(f"错误：计算URL时发生错误 - {e}")
        return None

def create_vless_link_from_clash(proxy):
    """从Clash的proxy字典直接创建VLESS链接"""
    if proxy.get("type") != "vless": return None
    name = quote(proxy.get("name", "Unnamed"))
    params = {
        "security": "reality", "sni": proxy.get("servername", ""),
        "fp": proxy.get("client-fingerprint", "chrome"),
        "publicKey": proxy.get("reality-opts", {}).get("public-key", ""),
        "shortId": proxy.get("reality-opts", {}).get("short-id", ""),
        "flow": proxy.get("flow", "")
    }
    param_str = '&'.join([f"{k}={v}" for k, v in params.items() if v])
    return f"vless://{proxy.get('uuid')}@{proxy.get('server')}:{proxy.get('port')}?{param_str}#{name}"

def main():
    target_url = calculate_current_url()
    if not target_url: return

    try:
        print(f"步骤 2 & 3: 正在抓取和提取Clash订阅链接...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        page_res = requests.get(target_url, headers=headers, timeout=15)
        page_res.raise_for_status()
        match = re.search(r'clash\s*:\s*"(https?://[^\s"]+)"', page_res.text)
        if not match: raise ValueError("在页面中未找到Clash订阅链接")
        sub_link = match.group(1)
        print(f"提取成功 -> {sub_link}")

        print("步骤 4: 正在下载YAML订阅内容...")
        sub_headers = {'User-Agent': 'ClashforWindows/0.20.19'}
        sub_res = requests.get(sub_link, headers=sub_headers, timeout=15)
        sub_res.raise_for_status()
        
        print("步骤 5: 正在解析YAML...")
        data = yaml.safe_load(sub_res.text)
        proxies = data.get('proxies', [])
        if not proxies: raise ValueError("YAML文件中没有找到proxies")
        
        print(f"解析到 {len(proxies)} 个节点。")
        
        # =================================================================== #
        # =================== 在这里进行自定义名称修改 ====================== #
        # =================================================================== #
        
        print("正在进行智能重命名和地区识别...")
        for proxy in proxies:
            name = proxy.get("name", "")
            
            if "香港" in name:
                proxy["name"] = f"🇭🇰 香港"
            elif "日本" in name:
                proxy["name"] = f"🇯🇵 日本"
            elif "新加坡" in name:
                proxy["name"] = f"🇸🇬 新加坡"
            elif "美国" in name:
                proxy["name"] = f"🇺🇸 美国"
            # 如果上面关键词都不存在，则执行您的要求
            else:
                proxy["name"] = f"🇨🇳 中国"

        print("正在为重名节点添加序号...")
        name_counts = {}
        processed_proxies = []
        for proxy in proxies:
            name = proxy.get("name")
            current_count = name_counts.get(name, 0) + 1
            name_counts[name] = current_count
            # 只为第二个及以后的同名节点添加序号
            if current_count > 1:
                proxy["name"] = f"{name}-{current_count}"
            processed_proxies.append(proxy)
        proxies = processed_proxies # 使用处理后的新列表

        # =================================================================== #
        # ========================= 修改结束 ================================ #
        # =================================================================== #

        output_dir = 'public'
        if not os.path.exists(output_dir): os.makedirs(output_dir)

        print("正在生成 nodes.json ...")
        json_path = os.path.join(output_dir, 'nodes.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(proxies, f, indent=2, ensure_ascii=False)
        print(f"已将处理后的节点信息保存到 -> {json_path}")

        print("正在生成通用 Base64 订阅文件 sub.txt ...")
        vless_links = [link for proxy in proxies if (link := create_vless_link_from_clash(proxy))]
        
        subscription_text = "\n".join(vless_links)
        encoded_subscription = base64.b64encode(subscription_text.encode('utf-8')).decode('utf-8')
        
        sub_path = os.path.join(output_dir, 'sub.txt')
        with open(sub_path, 'w', encoding='utf-8') as f:
            f.write(encoded_subscription)
        print(f"已将通用订阅文件保存到 -> {sub_path}")

    except Exception as e:
        print(f"脚本执行失败: {e}")

if __name__ == "__main__":
    main()