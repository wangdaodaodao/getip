
import requests
import re
import os
import datetime
import yaml
import json
import base64
from urllib.parse import quote

BASE_ID = 196
BASE_DATE_STR = "2025-09-19"

def calculate_current_url_and_date():
    print("步骤 1: 正在根据当前日期计算目标URL...")
    try:
        base_date = datetime.datetime.strptime(BASE_DATE_STR, "%Y-%m-%d").date()
        today = datetime.datetime.utcnow().date()
        delta_days = (today - base_date).days
        current_id = BASE_ID + delta_days
        target_url = f"https://nodesdz.com/?id={current_id}"
        date_suffix = today.strftime("%m-%d")
        print(f"生成的今日URL: {target_url}")
        print(f"生成的日期后缀: {date_suffix}")
        return target_url, date_suffix
    except Exception as e:
        print(f"错误：计算URL时发生错误 - {e}")
        return None, None

def create_custom_link_from_item(item):
    if item.get("type") != "vless":
        return None
    
    name = quote(item.get("name", "Unnamed"))
    
    params = {
        "security": "reality",
        "sni": item.get("servername", ""),
        "fp": item.get("client-fingerprint", "chrome"),
        "publicKey": item.get("reality-opts", {}).get("public-key", ""),
        "shortId": item.get("reality-opts", {}).get("short-id", ""),
        "flow": item.get("flow", "")
    }
    
    param_str = '&'.join([f"{k}={v}" for k, v in params.items() if v])
    
    return f"vless://{item.get('uuid')}@{item.get('server')}:{item.get('port')}?{param_str}#{name}"

def main():
    target_url, date_suffix = calculate_current_url_and_date()
    if not target_url:
        return

    try:
        print(f"步骤 2 & 3: 正在抓取和提取数据源链接...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        page_res = requests.get(target_url, headers=headers, timeout=15)
        page_res.raise_for_status()
        
        match = re.search(r'clash\s*:\s*"(https?://[^\s"]+)"', page_res.text)
        if not match:
            raise ValueError("在页面中未找到所需的数据链接")
        source_link = match.group(1)
        print(f"提取成功 -> {source_link}")

        print("步骤 4: 正在下载YAML格式内容...")
        source_headers = {'User-Agent': 'ClashforWindows/0.20.19'}
        source_res = requests.get(source_link, headers=source_headers, timeout=15)
        source_res.raise_for_status()
        
        print("步骤 5: 正在解析YAML...")
        data = yaml.safe_load(source_res.text)
        items = data.get('proxies', [])
        if not items:
            raise ValueError("YAML文件中没有找到'proxies'键")
        
        print(f"解析到 {len(items)} 个条目。")
        
        print("正在进行智能重命名和地区识别...")
        for item in items:
            name = item.get("name", "")
            
            if "香港" in name:
                item["name"] = f"🇭🇰 香港"
            elif "日本" in name:
                item["name"] = f"🇯🇵 日本"
            elif "新加坡" in name:
                item["name"] = f"🇸🇬 新加坡"
            elif "美国" in name:
                item["name"] = f"🇺🇸 美国"
            else:
                item["name"] = f"🇨🇳 中国"

        print(f"正在为条目名称添加日期后缀: {date_suffix}")
        for item in items:
            item["name"] = f"{item['name']} {date_suffix}"

        print("正在为重名条目添加序号...")
        name_counts = {}
        processed_items = []
        for item in items:
            name = item.get("name")
            current_count = name_counts.get(name, 0) + 1
            name_counts[name] = current_count
            if current_count > 1:
                item["name"] = f"{name}-{current_count}"
            processed_items.append(item)
        items = processed_items

        output_dir = 'public'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print("正在生成 data.json ...")
        json_path = os.path.join(output_dir, 'data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"已将处理后的条目信息保存到 -> {json_path}")

        print("正在生成通用 Base64 编码文件 encoded_data.txt ...")
        custom_links = [link for item in items if (link := create_custom_link_from_item(item))]
        
        combined_text = "\n".join(custom_links)
        
        encoded_content = base64.b64encode(combined_text.encode('utf-8')).decode('utf-8')
        
        sub_path = os.path.join(output_dir, 'good.txt')
        with open(sub_path, 'w', encoding='utf-8') as f:
            f.write(encoded_content)
        print(f"已将通用编码文件保存到 -> {sub_path}")

    except Exception as e:
        print(f"脚本执行失败: {e}")

if __name__ == "__main__":
    main()