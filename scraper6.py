import requests, re, os, json, base64
from urllib.parse import quote, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
import datetime as dt



# --- 全局配置 ---
BASE_URL = "https://clashgithub.com"
CATEGORY_URL = "https://clashgithub.com/category/clashnode"
OUTPUT_DIR = 'public'
USER_AGENT = 'Mozilla/5.0'



def setup_session():
    session = requests.Session()
    retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session



def parse_vless_uri(vless_uri):
    """解析vless URI并返回配置字典"""
    import urllib.parse as urlparse
    try:
        parsed = urlparse.urlparse(vless_uri)
        if parsed.scheme != 'vless':
            return None

        # 提取用户信息 (uuid@server:port)
        user_info = parsed.netloc
        if '@' not in user_info:
            return None

        uuid, server_port = user_info.split('@', 1)
        if ':' not in server_port:
            return None

        server, port_str = server_port.split(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            return None

        # 解析查询参数
        query = urlparse.parse_qs(parsed.query)

        # 提取name并处理 - 直接使用原始名称
        raw_name = urlparse.unquote(parsed.fragment) if parsed.fragment else "Unnamed"

        # 过滤中国节点
        if ('🇨🇳' in raw_name or '_CN_' in raw_name or '中国' in raw_name or 'China' in raw_name):
            return None  # 中国节点过滤掉

        name = raw_name

        # 构建配置
        item = {
            "type": "vless",
            "uuid": uuid,
            "server": server,
            "port": port,
            "name": name,
            "network": "tcp",
            "tls": True,
            "udp": True
        }

        # 添加可选参数
        security = query.get('security', [''])[0]
        if security:
            if security == 'reality':
                item["flow"] = query.get('flow', ["xtls-rprx-vision"])[0]
                item["servername"] = query.get('sni', ["www.microsoft.com"])[0] or query.get('servername', ["www.microsoft.com"])[0]
                item["reality-opts"] = {
                    "public-key": query.get('pbk', [''])[0] or query.get('publicKey', ['0XqnX5cXAa6isFhTW4eIM_CaAHTXJJ8tbMs9XabxJ1A'])[0],
                    "short-id": query.get('sid', [''])[0] or query.get('shortId', [''])[0]
                }
                item["client-fingerprint"] = query.get('fp', ["chrome"])[0]

        return item

    except Exception as e:
        return None

def parse_generic_uri(uri):
    """解析各种协议的URI"""
    from urllib.parse import unquote as url_unquote
    try:
        parsed = urlparse(uri)
        scheme = parsed.scheme

        if scheme == 'vless':
            return parse_vless_uri(uri)
        elif scheme == 'ss':
            # SS协议: ss://base64@address:port#name
            if '@' in parsed.netloc:
                userhostpart = parsed.netloc
                auth_part, rest = userhostpart.split('@', 1)
                if ':' in rest:
                    address, port_str = rest.split(':', 1)
                    try:
                        port = int(port_str)
                    except ValueError:
                        return None

                    name = url_unquote(parsed.fragment) if parsed.fragment else f"SS-{address}:{port_str}"

                    # 过滤中国节点
                    if ('🇨🇳' in name or '_CN_' in name or '中国' in name or 'China' in name):
                        return None  # 中国节点过滤掉

                    item = {
                        "type": "ss",
                        "server": address,
                        "port": port,
                        "name": name,
                        "cipher": "unknown",  # SS协议需要更多的解析
                        "password": auth_part.decode() if isinstance(auth_part, bytes) else auth_part
                    }

                    return item

        elif scheme == 'trojan':
            # Trojan协议: trojan://password@address:port?params#name
            userhostpart = parsed.netloc
            if '@' in userhostpart:
                password, rest = userhostpart.split('@', 1)
                if ':' in rest:
                    address, port_str = rest.split(':', 1)
                    try:
                        port = int(port_str)
                    except ValueError:
                        return None

                    name = url_unquote(parsed.fragment) if parsed.fragment else f"Trojan-{address}:{port_str}"

                    # 过滤中国节点
                    if ('🇨🇳' in name or '_CN_' in name or '中国' in name or 'China' in name):
                        return None  # 中国节点过滤掉

                    item = {
                        "type": "trojan",
                        "server": address,
                        "port": port,
                        "name": name,
                        "password": password
                    }

                    return item

        elif scheme == 'vmess':
            # VMess协议: vmess://base64-encoded-json
            try:
                # 提取base64编码的JSON
                encoded_json = parsed.netloc
                if not encoded_json:
                    return None

                # 添加padding if needed
                missing_padding = len(encoded_json) % 4
                if missing_padding:
                    encoded_json += '=' * (4 - missing_padding)

                # 解码base64
                try:
                    decoded_json = base64.b64decode(encoded_json.encode('utf-8')).decode('utf-8')
                    vmess_data = json.loads(decoded_json)
                except Exception as decode_error:
                    print(f"VMess base64解码失败: {encoded_json}, 错误: {str(decode_error)}")
                    return None

                # 提取vmess数据
                server = vmess_data.get('add', vmess_data.get('host', ''))
                if not server:
                    return None

                try:
                    port = int(vmess_data.get('port', 443))
                except (ValueError, TypeError):
                    port = 443

                uuid = vmess_data.get('id', '')
                if not uuid:
                    return None

                name = vmess_data.get('ps', vmess_data.get('remarks', 'VMess Node'))

                # 过滤中国节点
                if ('🇨🇳' in name or '_CN_' in name or '中国' in name or 'China' in name):
                    return None  # 中国节点过滤掉

                item = {
                    "type": "vmess",
                    "uuid": uuid,
                    "server": server,
                    "port": port,
                    "name": name,
                    "alterId": vmess_data.get('aid', vmess_data.get('alterId', 0)),
                    "cipher": vmess_data.get('scy', 'auto'),
                    "network": vmess_data.get('net', 'tcp'),
                    "tls": vmess_data.get('tls', False) == 'tls'
                }

                return item

            except Exception as vmess_error:
                print(f"VMess解析失败, 错误: {str(vmess_error)}")
                return None

        # 对于不支持的协议，返回None以跳过
        return None

    except Exception as e:
        print(f"解析URI失败: {uri}, 错误: {str(e)}")
        return None

def get_nodes_from_txt(session, txt_url, date_suffix=None, quiet=False):
    """从txt URL获取并解析所有协议的节点"""
    if not quiet:
        print(f"正在下载订阅文件: {txt_url}")
    try:
        response = session.get(txt_url, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()

        # 解析txt内容
        total_lines = response.text.strip().split('\n')
        uris = []
        for line in total_lines:
            line = line.strip()
            # 只处理支持的协议: ss://, vless://, trojan://, vmess://
            if (line.startswith('ss://') or
                line.startswith('vless://') or
                line.startswith('trojan://') or
                line.startswith('vmess://')):
                uris.append(line)

        if not quiet:
            print(f"TXT文件共 {len(total_lines)} 行，找到 {len(uris)} 个支持的链接")

        # 解析每个URI
        items = []
        success_count = 0
        fail_count = 0

        for uri in uris:
            try:
                item = parse_generic_uri(uri)
                if item:
                    # 延迟添加日期后缀，先收集所有节点后统一处理编号
                    items.append(item)
                    success_count += 1
                else:
                    fail_count += 1
                    # 只有在非quiet模式下才打印详细错误
                    if not quiet:
                        uri_prefix = uri[:60] + "..." if len(uri) > 60 else uri
                        if uri.startswith('vmess://'):
                            print(f"VMess base64解码失败: {uri_prefix}")
                        else:
                            print(f"未能解析的URI: {uri_prefix}")
            except Exception as e:
                print(f"解析URL失败: {uri[:50]}..., 错误: {str(e)[:100]}")
                fail_count += 1

        # 为clashgithub.com节点添加日期后缀
        if date_suffix and 'clashgithub.com' in txt_url:
            final_suffix = f"-{date_suffix.replace('-', '-')}"
            for item in items:
                item['name'] = f"{item['name']}{final_suffix}"

        # 现在打印成功的前几个节点信息
        if not quiet and success_count > 0:
            print(f"成功解析了 {success_count} 个节点")
            for i, item in enumerate(items[:5], 1):
                print(f"・ {item['name']}")

        if not quiet:
            print(f"解析完成，成功: {success_count} 个，失败: {fail_count} 个")
        return items

    except Exception as e:
        print(f"获取或解析txt文件失败: {str(e)}")
        return []

def get_clashgithub_items(session, date_suffix):
    """从clashgithub.com获取节点"""
    try:
        # 获取主页，查找最新文章URL
        response = session.get(BASE_URL, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()

        # 直接取第一个链接（HTML页面按日期倒序排列）
        clashnode_links = re.findall(r'href="([^"]*clashnode[^"]*html[^"]*)"', response.text)
        if not clashnode_links:
            print("未找到文章链接")
            return []

        latest_url = clashnode_links[0]  # 第一个就是最新的
        print(f"使用最新文章: {latest_url.split('/')[-1]}")

        # 访问文章提取节点
        response = session.get(latest_url, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()

        # 从页面内容中提取节点链接（vless://, ss://, trojan://, vmess://）
        uris = []
        for line in response.text.split('\n'):
            line = line.strip()
            if line.startswith('vless://'):
                uris.append(line.split()[0])  # 只取第一部分，排除HTML
            elif line.startswith('ss://'):
                uris.append(line.split()[0])
            elif line.startswith('trojan://'):
                uris.append(line.split()[0])
            elif line.startswith('vmess://'):
                uris.append(line.split()[0])

        # 过滤重复
        uris = list(set(uris))

        # 解析每个URI
        items = []
        success_count = 0
        fail_count = 0

        for uri in uris:
            try:
                item = parse_generic_uri(uri)
                if item:
                    items.append(item)
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1

        # 为clashgithub.com节点添加日期后缀
        if date_suffix:
            final_suffix = f"-{date_suffix.replace('-', '-')}"
            for item in items:
                item['name'] = f"{item['name']}{final_suffix}"

        if success_count > 0:
            print(f"成功解析了 {success_count} 个节点")
            for i, item in enumerate(items[:5], 1):
                print(f"・ {item['name']}")
        else:
            print("页面中未找到有效的节点链接")

        return items

    except Exception as e:
        print(f"获取clashgithub.com节点时发生错误: {str(e)}")
        return []

def save_output_files(all_items, output_filename='good6.txt'):
    """保存节点配置到输出文件"""
    import datetime
    print(f"正在保存输出文件...")

    seen_keys = set()
    unique_items = [item for item in all_items if (key := (item.get('type', ''), item.get('server', ''), str(item.get('port', '')))) not in seen_keys and not seen_keys.add(key)]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = (datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))).strftime("%Y%m%d")

    json_filename = f'data6-{timestamp}.json'
    json_path = os.path.join(OUTPUT_DIR, json_filename)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(unique_items, f, indent=2, ensure_ascii=False)

    links = []
    for item in unique_items:
        try:
            if item.get("type") == "vless":
                name_encoded = quote(item.get("name", ""))
                params = [f"{k}={v}" for k, v in {
                    "security": "reality",
                    "sni": "www.microsoft.com",
                    "fp": "chrome",
                    "publicKey": "0XqnX5cXAa6isFhTW4eIM_CaAHTXJJ8tbMs9XabxJ1A",
                    "flow": "xtls-rprx-vision"
                }.items() if v]
                link = f"vless://{item['uuid']}@{item['server']}:{item.get('port')}?{'&'.join(params)}#{name_encoded}"
            elif item.get("type") == "ss":
                name_encoded = quote(item.get("name", ""))
                link = f"ss://{item.get('password', '')}@{item.get('server')}:{item.get('port', 443)}#{name_encoded}"
            elif item.get("type") == "trojan":
                name_encoded = quote(item.get("name", ""))
                link = f"trojan://{item.get('password', '')}@{item.get('server')}:{item.get('port', 443)}#{name_encoded}"
            elif item.get("type") == "vmess":
                vmess_data = {
                    "v": "2", "ps": item.get("name", ""), "add": item.get("server", ""),
                    "port": str(item.get("port", 443)), "id": item.get("uuid", ""),
                    "aid": str(item.get("alterId", 0)), "scy": item.get("cipher", "auto"),
                    "net": item.get("network", "tcp"),
                    "tls": "tls" if item.get("tls") else ""
                }
                json_str = json.dumps(vmess_data, separators=(',', ':'))
                link = f"vmess://{base64.b64encode(json_str.encode('utf-8')).decode('utf-8')}"
            if link:
                links.append(link)
        except:
            continue

    if links:
        combined_text = "\n".join(links)
        encoded_content = base64.b64encode(combined_text.encode('utf-8')).decode('utf-8')

        sub_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(sub_path, 'w', encoding='utf-8') as f:
            f.write(encoded_content)



def main():
    """主程序入口"""
    print("="*50)
    print("从clashgithub.com获取节点脚本开始执行")
    print("="*50)

    try:
        # 计算日期后缀
        beijing_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        date_suffix = beijing_time.strftime("%m-%d")

        session = setup_session()

        # 获取clashgithub.com节点
        print("获取clashgithub.com节点...")
        clashgithub_items = get_clashgithub_items(session, date_suffix)
        print(f"已添加 {len(clashgithub_items)} 个clashgithub.com节点")

        all_items = clashgithub_items

        if all_items:
            save_output_files(all_items)
            print("="*50)
            print(f"脚本执行成功，总共处理 {len(all_items)} 个节点")
            print("=" * 50)
        else:
            print("没有获取到任何节点数据，程序终止")

    except Exception as e:
        print(f"程序执行过程中发生错误: {str(e)}")
        print("="*50)
        print("节点更新脚本执行失败")
        print("="*50)

if __name__ == "__main__":
    main()
