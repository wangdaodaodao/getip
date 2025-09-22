# scraper.py
import requests
import re
import os
import datetime
import yaml  # For parsing YAML content
import json  # For outputting structured data

# --- 核心配置区 ---
BASE_ID = 196
BASE_DATE_STR = "2025-09-19"

def calculate_current_url():
    """根据当前日期计算出当天的目标URL。"""
    print("步骤 1: 正在根据当前日期计算目标URL...")
    try:
        print(f"基准日期: {BASE_DATE_STR}")
        print(f"基准ID: {BASE_ID}")

        base_date = datetime.datetime.strptime(BASE_DATE_STR, "%Y-%m-%d").date()
        today = datetime.datetime.utcnow().date()
        print(f"当前UTC日期: {today}")

        delta_days = (today - base_date).days
        print(f"距离基准日期的天数: {delta_days}")

        current_id = BASE_ID + delta_days
        print(f"计算得出的当前ID: {current_id}")

        target_url = f"https://nodesdz.com/?id={current_id}"
        print(f"生成的今日URL: {target_url}")
        return target_url
    except Exception as e:
        print(f"错误：计算URL时发生错误 - {e}")
        return None

def fetch_parse_and_save(target_url):
    """
    抓取、解析并保存订阅中的节点信息。
    """
    try:
        # 步骤 2: 访问页面并提取订阅链接
        print(f"步骤 2: 正在访问目标页面 -> {target_url}")
        print("正在设置请求头...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        print(f"请求头: {headers}")

        print("正在发送HTTP请求...")
        response = requests.get(target_url, headers=headers, timeout=15)
        print(f"HTTP响应状态码: {response.status_code}")
        response.raise_for_status()

        page_content = response.text
        print(f"页面内容长度: {len(page_content)} 字符")

        print("正在搜索Clash订阅链接...")
        match = re.search(r'clash\s*:\s*"(https?://[^\s"]+)"', page_content)

        if not match:
            print("错误：未能在页面中找到Clash订阅链接。")
            return

        subscription_link = match.group(1)
        print(f"步骤 3: 成功提取到Clash订阅链接 -> {subscription_link}")

        # 步骤 4: 下载订阅内容
        print("步骤 4: 正在从订阅链接获取YAML内容...")
        print(f"订阅链接: {subscription_link}")
        sub_headers = {'User-Agent': 'ClashforWindows/0.20.19'}
        print(f"订阅请求头: {sub_headers}")

        print("正在下载订阅内容...")
        sub_response = requests.get(subscription_link, headers=sub_headers, timeout=15)
        print(f"订阅HTTP响应状态码: {sub_response.status_code}")
        sub_response.raise_for_status()

        yaml_content = sub_response.text
        print(f"YAML内容长度: {len(yaml_content)} 字符")

        # 步骤 5: 解析YAML内容
        print("步骤 5: 正在解析YAML内容...")
        print("使用yaml.safe_load进行安全解析...")
        try:
            # 使用 safe_load 防止恶意YAML代码执行
            data = yaml.safe_load(yaml_content)
            print(f"YAML解析成功，数据类型: {type(data)}")

            # .get('proxies', []) 是一种安全的访问方式，如果'proxies'不存在，则返回一个空列表
            proxies = data.get('proxies', [])
            print(f"从YAML中提取的proxies数量: {len(proxies)}")

            if not proxies:
                print("警告: YAML文件中没有找到 'proxies' 列表。")
                return
            else:
                print(f"成功获取到 {len(proxies)} 个代理节点")
        except yaml.YAMLError as e:
            print(f"错误: 解析YAML失败 - {e}")
            return

        # 步骤 6: 提取并构建关键配置信息
        print(f"步骤 6: 正在从 {len(proxies)} 个节点中提取关键信息...")
        extracted_nodes = []
        processed_count = 0

        for i, proxy in enumerate(proxies, 1):
            print(f"正在处理节点 {i}/{len(proxies)}...")
            # 为了健壮性，使用 .get() 方法获取每个值，如果不存在则返回None或默认值
            node_info = {
                "name": proxy.get("name"),
                "type": proxy.get("type"),
                "server": proxy.get("server"),
                "port": proxy.get("port"),
                "uuid": proxy.get("uuid"),  # 适用于 VLESS/VMess
                "password": proxy.get("password"),  # 适用于 Shadowsocks/Trojan
                "tls": proxy.get("tls"),
                "network": proxy.get("network"),
                "servername": proxy.get("servername"),  # SNI
                # 处理嵌套的字典
                "reality-opts": proxy.get("reality-opts", {}),
                "ws-opts": proxy.get("ws-opts", {})
            }
            extracted_nodes.append(node_info)
            processed_count += 1

            if processed_count % 10 == 0 or processed_count == len(proxies):
                print(f"已处理 {processed_count}/{len(proxies)} 个节点")

        print(f"信息提取完成！共处理了 {len(extracted_nodes)} 个节点")

        # 步骤 7: 将提取的信息保存为JSON文件
        print("步骤 7: 正在保存节点信息到JSON文件...")
        output_dir = 'public'
        print(f"输出目录: {output_dir}")

        if not os.path.exists(output_dir):
            print(f"目录 {output_dir} 不存在，正在创建...")
            os.makedirs(output_dir)
            print(f"成功创建目录: {output_dir}")
        else:
            print(f"目录 {output_dir} 已存在")

        # 生成带时间戳的文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        json_filename = f"nodes2_{timestamp}.json"
        file_path = os.path.join(output_dir, json_filename)
        print(f"输出文件路径: {file_path}")

        print("正在写入JSON文件...")
        print(f"待保存的节点数量: {len(extracted_nodes)}")

        with open(file_path, 'w', encoding='utf-8') as f:
            # json.dumps 用于将Python字典/列表转换为JSON字符串
            # indent=2 使JSON文件格式化，更易读
            # ensure_ascii=False 确保中文字符能正确显示而不是被编码
            json.dump(extracted_nodes, f, indent=2, ensure_ascii=False)

        # 检查文件是否成功保存
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"步骤 7: 成功保存节点信息到 -> {file_path}")
            print(f"文件大小: {file_size} 字节")
            print(f"JSON格式化: indent=2, 包含中文字符支持")
        else:
            print(f"错误: 文件保存失败 - {file_path}")

    except requests.exceptions.RequestException as e:
        print(f"脚本执行失败: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("节点订阅抓取脚本启动...")
    print("=" * 50)

    url = calculate_current_url()
    if url:
        fetch_parse_and_save(url)
    else:
        print("错误：无法生成目标URL，脚本终止。")

    print("=" * 50)
    print("节点订阅抓取脚本执行完成！")
    print("=" * 50)
