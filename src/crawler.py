# src/crawler.py

import os
import time
import hashlib
import requests
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
from PIL import Image
from io import BytesIO

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrawlerEngine")

class GenericImageCrawler:
    def __init__(self, output_dir: str = "downloads"):
        """
        初始化爬虫引擎
        
        Args:
            output_dir: 图片保存的根目录
        """
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        
        # 伪装成浏览器，防止简单的反爬虫
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        
        # 创建目录
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir, exist_ok=True)
            
        self.visited_urls: Set[str] = set()

    def is_valid_image_url(self, url: str) -> bool:
        """检查URL后缀是否为图片格式"""
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
        path = urlparse(url).path
        ext = os.path.splitext(path)[1].lower()
        # 有些图片的URL没有后缀，先暂时允许，下载时再校验
        if not ext: 
            return True 
        return ext in valid_exts

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """请求网页并返回解析后的 Soup 对象"""
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return BeautifulSoup(resp.content, 'html.parser') # 如果安装了lxml，改为 'lxml' 解析更快
            else:
                logger.warning(f"页面请求失败 [{resp.status_code}]: {url}")
        except Exception as e:
            logger.error(f"无法访问页面 {url}: {e}")
        return None

    def download_image(self, img_url: str, referer: str) -> Optional[Dict]:
        """
        下载并保存图片
        
        Returns:
            Dict: 包含图片路径、元数据的字典；失败则返回 None
        """
        try:
            # 1. 根据 URL 生成唯一哈希文件名 (防止重复下载)
            img_hash = hashlib.md5(img_url.encode()).hexdigest()[:12]
            
            # 尝试推断后缀，默认为 .jpg
            path_obj = urlparse(img_url)
            ext = os.path.splitext(path_obj.path)[1].lower()
            if not ext or len(ext) > 5: 
                ext = ".jpg"
                
            filename = f"img_{img_hash}{ext}"
            filepath = os.path.join(self.images_dir, filename)

            # 2. 如果文件已存在，跳过下载
            if os.path.exists(filepath):
                return {
                    "status": "exists", 
                    "path": filepath, 
                    "url": img_url,
                    "filename": filename
                }

            # 3. 发起请求下载
            # 添加 Referer 头，有些网站防盗链需要
            headers = {"Referer": referer}
            r = self.session.get(img_url, headers=headers, stream=True, timeout=10)
            
            if r.status_code == 200:
                # 4. 读取内存并校验是否为有效图片
                content = r.content
                if len(content) < 1024: # 忽略小于 1KB 的图
                    return None
                    
                image = Image.open(BytesIO(content))
                image.verify() # 校验文件完整性
                
                # 5. 写入磁盘
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                logger.info(f"下载成功: {filename}")
                return {
                    "status": "downloaded",
                    "path": filepath,
                    "url": img_url,
                    "referer": referer,
                    "resolution": f"{image.width}x{image.height}",
                    "filename": filename
                }
        except Exception as e:
            # 静默失败，不要打断整个爬虫
            logger.debug(f"图片下载/校验失败 {img_url}: {e}")
        return None

    def crawl(self, start_url: str, max_images: int = 5, keyword_filter: str = None) -> List[Dict]:
        """
        核心爬取逻辑
        
        Args:
            start_url: 目标网页 URL
            max_images: 本次任务最大下载数量
            keyword_filter: (可选) 关键词过滤，匹配 URL 或 alt 文本
            
        Returns:
            List[Dict]: 成功下载的图片列表
        """
        results = []
        logger.info(f"开始爬取页面: {start_url}")
        
        soup = self.fetch_page(start_url)
        if not soup:
            return []

        # 提取所有图片标签
        img_tags = soup.find_all('img')
        logger.info(f"页面发现 {len(img_tags)} 个图片标签")

        count = 0
        for img in img_tags:
            if count >= max_images:
                break

            # 兼容常见的懒加载属性
            raw_src = img.get('src') or img.get('data-src') or img.get('data-original')
            if not raw_src:
                continue

            # 处理相对路径
            full_url = urljoin(start_url, raw_src)
            alt_text = img.get('alt', '').strip()

            # --- 过滤逻辑 ---
            
            # 1. 关键词过滤
            if keyword_filter:
                kw = keyword_filter.lower()
                # 检查 URL 或 alt 文本是否包含关键词
                if (kw not in full_url.lower()) and (kw not in alt_text.lower()):
                    continue
            
            # 2. 格式过滤
            if not self.is_valid_image_url(full_url):
                continue
            
            # 3. 排除一些明显的图标/Logo干扰 (简单启发式)
            if 'logo' in full_url.lower() or 'icon' in full_url.lower():
                continue

            # --- 执行下载 ---
            meta = self.download_image(full_url, referer=start_url)
            
            if meta:
                meta['alt_text'] = alt_text
                results.append(meta)
                count += 1
                # 礼貌性延时，防止对目标服务器造成压力
                time.sleep(0.3)

        return results