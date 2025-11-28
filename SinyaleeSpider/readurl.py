import requests
import re
import os
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BlogCrawler:
    def __init__(self, delay=1, timeout=10):
        """
        初始化爬虫
        
        Args:
            delay: 请求间隔时间（秒）
            timeout: 请求超时时间（秒）
        """
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def extract_urls_from_text(self, file_path):
        """
        从文本文件中提取URL
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            list: 包含标题和URL的字典列表
        """
        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # 使用正则表达式匹配序号、标题和URL
            pattern = r'(\d+)\.\s+(.*?)\s+-\s+(https?://[^\s]+)'
            matches = re.findall(pattern, content)
            
            for match in matches:
                number, title, url = match
                urls.append({
                    'number': number,
                    'title': self.sanitize_filename(title),
                    'url': url
                })
                
            logger.info(f"从文件中提取到 {len(urls)} 个URL")
            
        except Exception as e:
            logger.error(f"读取文件时出错: {e}")
            
        return urls
    
    def sanitize_filename(self, filename):
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理后的文件名
        """
        # 移除Windows文件名中不允许的字符
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '_', filename)
        # 限制文件名长度
        if len(filename) > 100:
            filename = filename[:100]
        return filename.strip()
    
    def create_save_directory(self, base_dir="blog_pages"):
        """
        创建保存目录
        
        Args:
            base_dir: 基础目录名
            
        Returns:
            str: 创建的目录路径
        """
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            logger.info(f"创建目录: {base_dir}")
        return base_dir
    
    def fetch_page(self, url):
        """
        获取网页内容
        
        Args:
            url: 网页URL
            
        Returns:
            tuple: (成功状态, 响应内容或错误信息)
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()  # 如果状态码不是200，抛出异常
            
            # 检测编码
            if response.encoding.lower() == 'iso-8859-1':
                response.encoding = response.apparent_encoding
                
            return True, response.text
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求失败: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"未知错误: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def extract_content(self, html_content):
        """
        从HTML中提取主要内容
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 提取的文本内容
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 尝试找到文章主要内容区域
            # 常见的文章内容选择器
            content_selectors = [
                'article',
                '.entry-content',
                '.post-content',
                '.content',
                'main',
                '.main-content',
                '#content'
            ]
            
            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break
            
            # 如果没有找到特定的内容区域，使用body
            if not content_element:
                content_element = soup.find('body')
            
            # 获取文本
            text = content_element.get_text(separator='\n', strip=True)
            
            # 清理多余的空白行
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            return cleaned_text
            
        except Exception as e:
            logger.warning(f"内容提取失败，返回原始HTML: {e}")
            return html_content
    
    def save_content(self, content, file_path):
        """
        保存内容到文件
        
        Args:
            content: 要保存的内容
            file_path: 文件路径
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            return False
    
    def crawl(self, file_path, save_dir="blog_pages", save_html=False):
        """
        主爬取函数
        
        Args:
            file_path: 包含URL列表的文本文件路径
            save_dir: 保存目录
            save_html: 是否保存原始HTML
        """
        # 提取URL
        urls = self.extract_urls_from_text(file_path)
        if not urls:
            logger.error("没有提取到URL，程序退出")
            return
        
        # 创建保存目录
        save_dir = self.create_save_directory(save_dir)
        
        success_count = 0
        fail_count = 0
        
        # 统计文件
        stats_file = os.path.join(save_dir, "crawl_stats.txt")
        
        for url_info in urls:
            number = url_info['number']
            title = url_info['title']
            url = url_info['url']
            
            logger.info(f"正在处理 [{number}] {title}")
            
            # 获取网页内容
            success, content = self.fetch_page(url)
            
            if success:
                # 提取文本内容
                text_content = self.extract_content(content)
                
                # 保存文本内容
                text_filename = f"{number}_{title}.txt"
                text_filepath = os.path.join(save_dir, text_filename)
                
                if self.save_content(text_content, text_filepath):
                    logger.info(f"✓ 成功保存: {text_filename}")
                    success_count += 1
                else:
                    logger.error(f"✗ 保存失败: {text_filename}")
                    fail_count += 1
                
                # 如果需要保存原始HTML
                if save_html:
                    html_filename = f"{number}_{title}.html"
                    html_filepath = os.path.join(save_dir, html_filename)
                    self.save_content(content, html_filepath)
                    logger.info(f"✓ 保存HTML: {html_filename}")
            else:
                logger.error(f"✗ 获取失败: {title}")
                fail_count += 1
            
            # 延迟，避免请求过快
            time.sleep(self.delay)
        
        # 保存统计信息
        stats_content = f"""爬取统计报告
生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
总URL数量: {len(urls)}
成功爬取: {success_count}
失败数量: {fail_count}
成功率: {success_count/len(urls)*100:.2f}%
        """
        self.save_content(stats_content, stats_file)
        logger.info(f"爬取完成！统计信息已保存到: {stats_file}")

def main():
    # 配置参数
    TEXT_FILE = "爬取报告.txt"  # 包含URL列表的文本文件
    SAVE_DIR = "blog_pages"      # 保存目录
    DELAY = 35                    # 请求间隔（秒）
    SAVE_HTML = False            # 是否保存原始HTML
    
    # 创建爬虫实例
    crawler = BlogCrawler(delay=DELAY)
    
    # 开始爬取
    crawler.crawl(TEXT_FILE, SAVE_DIR, SAVE_HTML)

if __name__ == "__main__":
    main()