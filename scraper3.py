#!/usr/bin/env python3
import asyncio
import aiohttp
import yaml
import json
import os
import logging
import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

# --- 配置数据类 ---
@dataclass
class Config:
    base_id: int = 196
    base_date: str = "2025-09-19"
    base_url: str = "https://nodesdz.com"
    output_dir: Path = Path("public")
    cache_dir: Path = Path(".cache")
    cache_time: int = 3600  # 缓存有效期（秒）
    timeout: int = 15
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    clash_user_agent: str = "ClashforWindows/0.20.19"

@dataclass
class ProxyNode:
    name: str
    type: str
    server: str
    port: int
    uuid: Optional[str] = None
    password: Optional[str] = None
    tls: bool = True
    network: str = "tcp"
    servername: Optional[str] = None
    reality_opts: Optional[Dict] = None
    ws_opts: Optional[Dict] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

class ProxyManager:
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        self.logger = self._setup_logger()
        self._setup_directories()

    def _setup_logger(self) -> logging.Logger:
        """配置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
        return logging.getLogger("rich")

    def _setup_directories(self):
        """创建必要的目录"""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, url: str) -> Path:
        """获取缓存文件路径"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.config.cache_dir / f"{url_hash}.cache"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """检查缓存是否有效"""
        if not cache_path.exists():
            return False
        cache_time = datetime.datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = (datetime.datetime.now() - cache_time).total_seconds()
        return age < self.config.cache_time

    async def fetch_with_cache(self, url: str, headers: Dict = None) -> str:
        """获取URL内容，支持缓存"""
        cache_path = self._get_cache_path(url)
        
        if self._is_cache_valid(cache_path):
            self.logger.info(f"使用缓存内容: {url}")
            return cache_path.read_text(encoding='utf-8')

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=self.config.timeout) as response:
                response.raise_for_status()
                content = await response.text()
                
                # 保存到缓存
                cache_path.write_text(content, encoding='utf-8')
                return content

    def calculate_target_url(self) -> str:
        """计算目标URL"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("计算目标URL...", total=None)
            
            base_date = datetime.datetime.strptime(self.config.base_date, "%Y-%m-%d").date()
            today = datetime.datetime.utcnow().date()
            delta_days = (today - base_date).days
            current_id = self.config.base_id + delta_days
            target_url = f"{self.config.base_url}/?id={current_id}"
            
            progress.update(task, completed=True, description=f"目标URL: {target_url}")
            return target_url

    async def process_yaml_content(self, yaml_content: str) -> List[ProxyNode]:
        """处理YAML内容并提取节点信息"""
        try:
            data = yaml.safe_load(yaml_content)
            proxies = data.get('proxies', [])
            
            nodes = []
            for proxy in proxies:
                node = ProxyNode(
                    name=proxy.get('name', ''),
                    type=proxy.get('type', ''),
                    server=proxy.get('server', ''),
                    port=proxy.get('port', 443),
                    uuid=proxy.get('uuid'),
                    password=proxy.get('password'),
                    tls=proxy.get('tls', True),
                    network=proxy.get('network', 'tcp'),
                    servername=proxy.get('servername'),
                    reality_opts=proxy.get('reality-opts'),
                    ws_opts=proxy.get('ws-opts')
                )
                nodes.append(node)
            
            return nodes
        except yaml.YAMLError as e:
            self.logger.error(f"YAML解析错误: {e}")
            raise

    def save_nodes(self, nodes: List[ProxyNode]):
        """保存节点信息"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        json_filename = f"nodes3_{timestamp}.json"
        output_file = self.config.output_dir / json_filename
        nodes_data = [node.to_dict() for node in nodes]
        
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(nodes_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"保存了 {len(nodes)} 个节点到 {output_file}")

    async def run(self):
        """运行主流程"""
        try:
            # 1. 计算目标URL
            target_url = self.calculate_target_url()
            
            # 2. 获取页面内容
            self.logger.info("获取页面内容...")
            page_content = await self.fetch_with_cache(
                target_url,
                headers={"User-Agent": self.config.user_agent}
            )
            
            # 3. 提取Clash订阅链接
            import re
            match = re.search(r'clash\s*:\s*"(https?://[^\s"]+)"', page_content)
            if not match:
                raise ValueError("未找到Clash订阅链接")
            
            subscription_url = match.group(1)
            self.logger.info(f"找到订阅链接: {subscription_url}")
            
            # 4. 获取YAML内容
            yaml_content = await self.fetch_with_cache(
                subscription_url,
                headers={"User-Agent": self.config.clash_user_agent}
            )
            
            # 5. 处理节点信息
            nodes = await self.process_yaml_content(yaml_content)
            
            # 6. 保存结果
            self.save_nodes(nodes)
            
        except Exception as e:
            self.logger.error(f"处理过程中出错: {e}", exc_info=True)
            raise

def main():
    """主入口函数"""
    config = Config()
    manager = ProxyManager(config)
    
    try:
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        manager.logger.info("程序被用户中断")
    except Exception as e:
        manager.logger.error(f"程序执行失败: {e}")
        raise

if __name__ == "__main__":
    main()
