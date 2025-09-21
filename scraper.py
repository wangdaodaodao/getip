import requests
import re
import os
import datetime
import json
import base64
import copy
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict

# --- 全局配置 ---
BASE_URL = "https://nodesdz.com"
OUTPUT_DIR = 'public'
USER_AGENT = 'Mozilla/5.0'

# 定义地区和对应的前缀
REGIONS = [
    {"name": "🇺🇸 美国(@未来专属线路)", "prefix": "awsall"},
    {"name": "🇭🇰 香港", "prefix": "awshk"},
    {"name": "🇯🇵 日本", "prefix": "awsjp"}
]

# 定义数据模板
ITEM_TEMPLATE = {
    "type": "vless",
    "port": 443,
    "network": "tcp",
    "tls": True,
    "udp": True,
    "flow": "xtls-rprx-vision",
    "servername": "www.microsoft.com",
    "reality-opts": {
      "public-key": "0XqnX5cXAa6isFhTW4eIM_CaAHTXJJ8tbMs9XabxJ1A",
      "short-id": ""
    },
    "client-fingerprint": "chrome"
}

def setup_session():
    session = requests.Session()
    retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_latest_post_info(session):
    print("步骤 1: 获取最新信息...")
    try:
        response = session.get(BASE_URL, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()
        match = re.search(r'<article class="log">.*?<h3>\s*<a href="https?://.*?/?\?id=(\d+)"', response.text, re.DOTALL)
        if not match:
            raise ValueError("未找到最新ID")
        latest_id = match.group(1)
        target_url = f"{BASE_URL}/?id={latest_id}"
        beijing_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8)
        date_suffix = beijing_time.strftime("%m-%d")
        print(f"获取成功: ID={latest_id}, URL={target_url}, 日期={date_suffix}")
        return target_url, date_suffix
    except Exception as e:
        print(f"错误: 获取最新信息失败 - {e}")
        return None, None

def generate_items_from_template(session, url, date_suffix):
    print("步骤 2: 提取关键信息...")
    try:
        response = session.get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()
        page_content = response.text

        uuid_match = re.search(r'clash:\s*".*?/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.yaml"', page_content)
        if not uuid_match:
            raise ValueError("未找到UUID")
        uuid = uuid_match.group(1)
        print(f"提取成功: UUID={uuid}")

        print("步骤 3: 生成配置列表...")
        items = []
        name_counts = defaultdict(int)
        for region in REGIONS:
            item = copy.deepcopy(ITEM_TEMPLATE)
            item["uuid"] = uuid
            # 直接在这里拼接固定的域名
            item["server"] = f"{region['prefix']}.freenodes01.cc"
            
            base_name = f"{region['name']}{date_suffix}"
            name_counts[base_name] += 1
            count = name_counts[base_name]
            item["name"] = f"{base_name}-{count}" if count > 1 else base_name
            
            items.append(item)
        
        print(f"成功生成 {len(items)} 个配置。")
        return items

    except Exception as e:
        print(f"错误: 生成配置失败 - {e}")
        return []

def create_custom_link(item):
    if item.get("type") != "vless" or 'uuid' not in item or 'server' not in item:
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
    return f"vless://{item['uuid']}@{item['server']}:{item.get('port')}?{param_str}#{name}"

def save_output_files(items):
    print("步骤 4: 生成输出文件...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_path = os.path.join(OUTPUT_DIR, 'data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"JSON 文件已保存: {json_path}")

    custom_links = [link for item in items if (link := create_custom_link(item))]
    if custom_links:
        combined_text = "\n".join(custom_links)
        encoded_content = base64.b64encode(combined_text.encode('utf-8')).decode('utf-8')
        sub_path = os.path.join(OUTPUT_DIR, 'good.txt')
        with open(sub_path, 'w', encoding='utf-8') as f:
            f.write(encoded_content)
        print(f"Base64 文件已保存: {sub_path}")

def main():
    session = setup_session()
    
    target_url, date_suffix = get_latest_post_info(session)
    if not target_url:
        return

    items = generate_items_from_template(session, target_url, date_suffix)
    if not items:
        return
        
    save_output_files(items)
    
    print("\n执行完毕!")

if __name__ == "__main__":
    main()