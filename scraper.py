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
    # ... (此函数无需改动，和之前一样)
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
    
    # URL编码节点名称，防止特殊字符导致解析失败
    name = quote(proxy.get("name", "Unnamed")) 
    
    # 拼接参数
    params = {
        "security": "reality",
        "sni": proxy.get("servername", ""),
        "fp": proxy.get("client-fingerprint", "chrome"), # 从clash配置中获取指纹
        "publicKey": proxy.get("reality-opts", {}).get("public-key", ""),
        "shortId": proxy.get("reality-opts", {}).get("short-id", ""),
        "flow": proxy.get("flow", "")
    }
    
    # 过滤掉值为空的参数
    param_str = '&'.join([f"{k}={v}" for k, v in params.items() if v])
    
    return f"vless://{proxy.get('uuid')}@{proxy.get('server')}:{proxy.get('port')}?{param_str}#{name}"

def main():
    target_url = calculate_current_url()
    if not target_url: return

    try:
        # 步骤 2 & 3: 抓取页面并提取订阅链接
        print(f"步骤 2 & 3: 正在抓取和提取Clash订阅链接...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        page_res = requests.get(target_url, headers=headers, timeout=15)
        page_res.raise_for_status()
        match = re.search(r'clash\s*:\s*"(https?://[^\s"]+)"', page_res.text)
        if not match: raise ValueError("在页面中未找到Clash订阅链接")
        sub_link = match.group(1)
        print(f"提取成功 -> {sub_link}")

        # 步骤 4: 下载订阅内容
        print("步骤 4: 正在下载YAML订阅内容...")
        sub_headers = {'User-Agent': 'ClashforWindows/0.20.19'}
        sub_res = requests.get(sub_link, headers=sub_headers, timeout=15)
        sub_res.raise_for_status()
        
        # 步骤 5: 解析YAML
        print("步骤 5: 正在解析YAML...")
        data = yaml.safe_load(sub_res.text)
        proxies = data.get('proxies', [])
        if not proxies: raise ValueError("YAML文件中没有找到proxies")
        
        print(f"解析到 {len(proxies)} 个节点。")
        
        # --- 新增处理流程 ---
        
        # 目标A: 生成 nodes.json
        print("正在生成 nodes.json ...")
        output_dir = 'public'
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        json_path = os.path.join(output_dir, 'nodes.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(proxies, f, indent=2, ensure_ascii=False)
        print(f"已将原始节点信息保存到 -> {json_path}")

        # 目标B: 生成通用订阅 sub.txt
        print("正在生成通用 Base64 订阅文件 sub.txt ...")
        vless_links = []
        for proxy in proxies:
            link = create_vless_link_from_clash(proxy)
            if link:
                vless_links.append(link)
        
        # 将所有链接用换行符连接成一个大字符串
        subscription_text = "\n".join(vless_links)
        
        # Base64编码吧
        encoded_subscription = base64.b64encode(subscription_text.encode('utf-8')).decode('utf-8')
        
        sub_path = os.path.join(output_dir, 'sub.txt')
        with open(sub_path, 'w', encoding='utf-8') as f:
            f.write(encoded_subscription)
        print(f"已将通用订阅文件保存到 -> {sub_path}")

    except Exception as e:
        print(f"脚本执行失败: {e}")

if __name__ == "__main__":
    main()