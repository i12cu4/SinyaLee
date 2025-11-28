import requests
from bs4 import BeautifulSoup
import os
import time
import re
from urllib.parse import urljoin, urlparse
import random

class BlogScraper:
    def __init__(self):
        self.base_url = "https://sinyalee.com/blog/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = 30
        self.visited_urls = set()  # 记录已访问的URL，避免重复爬取
        
    def clean_text(self, text):
        """清理文本，移除多余空白和特殊字符"""
        if not text:
            return ""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 替换多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 移除首尾空白
        return text.strip()
    
    def clean_filename(self, filename):
        """清理文件名，移除非法字符"""
        if not filename:
            return "未分类"
        # 移除HTML标签
        filename = re.sub(r'<[^>]+>', '', filename)
        # 替换多个空白字符为单个空格
        filename = re.sub(r'\s+', ' ', filename)
        # 移除文件名非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 限制文件名长度
        filename = filename.strip()[:100]
        return filename if filename else "未分类"
    
    def get_page_content_with_retry(self, url, max_retries=3):
        """获取指定页面的内容，带重试机制"""
        for attempt in range(max_retries):
            try:
                print(f"  尝试获取页面 (尝试 {attempt+1}/{max_retries})...")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                print(f"  成功获取页面: {url}")
                return response.text
            except requests.RequestException as e:
                print(f"  获取页面失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"  等待 {wait_time:.2f} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"  页面获取失败，已尝试{max_retries}次: {url}")
        return None
    
    def extract_article_links(self, html_content, base_url):
        """从页面HTML中提取文章链接"""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        article_links = []
        
        # 查找所有链接
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            if href:
                # 确保是绝对URL
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                
                # 只关注博客域名内的链接
                if 'sinyalee.com' in href and href not in self.visited_urls:
                    # 排除一些非内容页面
                    if any(x in href for x in ['/feed', '/wp-json', '/wp-admin', '/wp-content', '.xml', '.rss']):
                        continue
                    
                    # 如果是文章页面或分类页面，添加到待爬取列表
                    if any(x in href for x in ['/blog/', '/article/', '/post/']) or '?cat=' in href or '?paged=' in href:
                        article_links.append(href)
        
        return list(set(article_links))  # 去重
    
    def extract_article_content(self, html_content, url):
        """提取文章页面的详细内容"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取标题
        title_selectors = ['h1', '.post-title', '.entry-title', 'title']
        title = "未知标题"
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = self.clean_text(title_elem.get_text())
                break
        
        # 提取发布日期
        date_selectors = ['.post-date', '.entry-date', '.published', 'time']
        publish_date = "未知日期"
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                publish_date = self.clean_text(date_elem.get_text())
                break
        
        # 提取作者
        author_selectors = ['.author', '.post-author', '.entry-author']
        author = "未知作者"
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = self.clean_text(author_elem.get_text())
                break
        
        # 提取内容
        content_selectors = [
            '.post-content',
            '.entry-content',
            '.blog-content',
            'article .content',
            '.post-body',
            'article'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除脚本和样式
                for script in content_elem(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                content = self.clean_text(content_elem.get_text())
                break
        
        # 如果没有内容，尝试更通用的方法
        if not content:
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|post'))
            if main_content:
                for script in main_content(["script", "style", "nav", "header", "footer", "aside"]):
                    script.decompose()
                content = self.clean_text(main_content.get_text())
        
        # 提取分类/标签
        category_selectors = [
            '.category a',
            '.post-categories a',
            '.tags a',
            '.post-tags a',
            '.entry-categories a',
            '.cat-links a'
        ]
        categories = []
        for selector in category_selectors:
            cat_elems = soup.select(selector)
            for elem in cat_elems:
                cat_text = self.clean_text(elem.get_text())
                if cat_text and len(cat_text) < 50:
                    categories.append(cat_text)
        
        # 如果没有找到分类，使用默认分类
        if not categories:
            categories = ['未分类']
        
        return {
            'title': title,
            'content': content,
            'categories': categories,
            'url': url,
            'publish_date': publish_date,
            'author': author
        }
    
    def save_article(self, article_data, base_dir="blog_content"):
        """保存文章到txt文件"""
        if not article_data:
            return
        
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
        # 按分类保存
        for category in article_data['categories']:
            clean_category = self.clean_filename(category)
            if not clean_category:
                clean_category = "未分类"
                
            category_dir = os.path.join(base_dir, clean_category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
            
            clean_title = self.clean_filename(article_data['title'])
            if not clean_title:
                clean_title = "无标题"
                
            filename = f"{clean_title}.txt"
            filepath = os.path.join(category_dir, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"标题: {article_data['title']}\n")
                    f.write(f"链接: {article_data['url']}\n")
                    f.write(f"作者: {article_data['author']}\n")
                    f.write(f"发布日期: {article_data['publish_date']}\n")
                    f.write(f"分类: {', '.join(article_data['categories'])}\n")
                    f.write("="*80 + "\n")
                    f.write(article_data['content'])
                print(f"    已保存: {filename}")
            except Exception as e:
                print(f"    保存文件失败: {e}")
                # 尝试使用简单文件名
                simple_filename = f"article_{hash(article_data['url'])}.txt"
                simple_filepath = os.path.join(category_dir, simple_filename)
                with open(simple_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"标题: {article_data['title']}\n")
                    f.write(f"链接: {article_data['url']}\n")
                    f.write(f"作者: {article_data['author']}\n")
                    f.write(f"发布日期: {article_data['publish_date']}\n")
                    f.write(f"分类: {', '.join(article_data['categories'])}\n")
                    f.write("="*80 + "\n")
                    f.write(article_data['content'])
        
        # 同时保存到总目录
        all_articles_dir = os.path.join(base_dir, "所有文章")
        if not os.path.exists(all_articles_dir):
            os.makedirs(all_articles_dir)
        
        clean_title = self.clean_filename(article_data['title'])
        if not clean_title:
            clean_title = "无标题"
            
        filename = f"{clean_title}.txt"
        filepath = os.path.join(all_articles_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"标题: {article_data['title']}\n")
                f.write(f"链接: {article_data['url']}\n")
                f.write(f"作者: {article_data['author']}\n")
                f.write(f"发布日期: {article_data['publish_date']}\n")
                f.write(f"分类: {', '.join(article_data['categories'])}\n")
                f.write("="*80 + "\n")
                f.write(article_data['content'])
        except Exception as e:
            print(f"    保存到总目录失败: {e}")
    
    def crawl_site(self, start_urls, max_pages=100):
        """爬取整个网站的内容"""
        all_articles = []
        urls_to_visit = list(start_urls)
        
        page_count = 0
        while urls_to_visit and page_count < max_pages:
            url = urls_to_visit.pop(0)
            
            # 跳过已访问的URL
            if url in self.visited_urls:
                continue
                
            print(f"正在处理: {url}")
            self.visited_urls.add(url)
            
            html_content = self.get_page_content_with_retry(url)
            if not html_content:
                continue
            
            # 检查这是否是文章页面
            if any(x in url for x in ['/blog/', '/article/', '/post/']) and '?cat=' not in url and '?paged=' not in url:
                # 这是文章页面，提取内容
                article_data = self.extract_article_content(html_content, url)
                if article_data and article_data['content']:
                    self.save_article(article_data)
                    all_articles.append(article_data)
                    print(f"  成功提取文章: {article_data['title']}")
            
            # 从当前页面提取更多链接
            new_links = self.extract_article_links(html_content, url)
            for link in new_links:
                if link not in self.visited_urls and link not in urls_to_visit:
                    urls_to_visit.append(link)
            
            page_count += 1
            
            # 随机延迟，避免被屏蔽
            delay = random.uniform(1, 3)
            time.sleep(delay)
        
        return all_articles
    
    def scrape_blog_pages(self, start_page=1, end_page=24):
        """爬取博客的特定页面范围"""
        start_urls = [f"{self.base_url}?paged={i}" for i in range(start_page, end_page + 1)]
        return self.crawl_site(start_urls, max_pages=500)  # 增加最大页面数
    
    def generate_summary(self, all_articles):
        """生成汇总报告"""
        summary_file = "博客爬取汇总报告.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("博客爬取汇总报告\n")
            f.write("="*80 + "\n\n")
            f.write(f"总共爬取文章数量: {len(all_articles)}\n")
            f.write(f"总共访问页面数量: {len(self.visited_urls)}\n\n")
            
            # 分类统计
            category_count = {}
            for article in all_articles:
                for category in article['categories']:
                    category_count[category] = category_count.get(category, 0) + 1
            
            f.write("分类统计:\n")
            for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {category}: {count} 篇\n")
            
            # 作者统计
            author_count = {}
            for article in all_articles:
                author = article.get('author', '未知作者')
                author_count[author] = author_count.get(author, 0) + 1
            
            f.write("\n作者统计:\n")
            for author, count in sorted(author_count.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {author}: {count} 篇\n")
            
            f.write("\n文章列表:\n")
            for i, article in enumerate(all_articles, 1):
                f.write(f"{i}. {article['title']} - {article['url']}\n")
                f.write(f"   作者: {article['author']} | 日期: {article['publish_date']} | 分类: {', '.join(article['categories'])}\n\n")

def main():
    scraper = BlogScraper()
    
    print("开始深度爬取博客内容...")
    print("这将爬取博客的所有页面和文章内容，可能需要一些时间...")
    
    all_articles = scraper.scrape_blog_pages(1, 24)
    
    print("生成汇总报告...")
    scraper.generate_summary(all_articles)
    
    print(f"爬取完成！")
    print(f"共访问 {len(scraper.visited_urls)} 个页面")
    print(f"共提取 {len(all_articles)} 篇文章")
    print("文章已按分类保存到 'blog_content' 文件夹")
    print("详细汇总报告已保存到 '博客爬取汇总报告.txt'")

if __name__ == "__main__":
    main()