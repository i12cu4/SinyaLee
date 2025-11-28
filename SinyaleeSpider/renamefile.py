import os
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# 配置参数 - 请根据实际情况修改这些路径
NAME_LIST_FILE = r"C:\Users\Administrator\Desktop\Lib\SinyaleeSpider\爬取报告.txt"    # 名单文件路径
TARGET_FOLDER = r"C:\Users\Administrator\Desktop\Lib\SinyaleeBlogs"   # 要处理的文件夹路径
# ===============


import os
import re
from pathlib import Path

def numbered_rename():
    """保留序号的精确匹配URL重命名版本"""
    
    # 读取名单
    name_url_map = {}
    with open(NAME_LIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                # 匹配格式：序号. 名称 - URL
                match = re.match(r'^(\d+)\.\s*(.+?)\s*-\s*(https?://[^\s]+)', line)
                if match:
                    serial = match.group(1)  # 序号
                    name = match.group(2)   # 名称
                    url = match.group(3)    # URL
                    name_url_map[url] = (serial, name)
    
    # 按照URL长度从长到短排序，优先匹配更具体的URL
    sorted_urls = sorted(name_url_map.keys(), key=lambda x: len(x), reverse=True)
    
    # 处理文件
    for filename in os.listdir(TARGET_FOLDER):
        if filename.endswith('.txt'):
            filepath = os.path.join(TARGET_FOLDER, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 从内容中提取所有URL
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                content_urls = re.findall(url_pattern, content)
                
                # 查找匹配的URL - 使用精确匹配
                matched_serial = None
                matched_name = None
                for url in sorted_urls:
                    if url in content_urls:
                        matched_serial, matched_name = name_url_map[url]
                        print(f"在文件 {filename} 中找到匹配URL: {url}")
                        break
                
                if matched_serial and matched_name:
                    # 清理文件名
                    clean_name = re.sub(r'[<>:"/\\|?*]', '_', matched_name)
                    # 使用序号和名称组合新文件名
                    new_filename = f"{matched_serial}.{clean_name}.txt"
                    new_filepath = os.path.join(TARGET_FOLDER, new_filename)
                    
                    # 处理文件名冲突
                    counter = 1
                    original_new_filepath = new_filepath
                    while os.path.exists(new_filepath) and new_filepath != filepath:
                        name_without_ext = f"{matched_serial}.{clean_name}"
                        new_filename = f"{name_without_ext}_{counter}.txt"
                        new_filepath = os.path.join(TARGET_FOLDER, new_filename)
                        counter += 1
                    
                    # 只有当文件名不同时才重命名
                    if new_filepath != filepath:
                        os.rename(filepath, new_filepath)
                        print(f"重命名: {filename} -> {new_filename}")
                    else:
                        print(f"跳过: {filename} (文件名已正确)")
                else:
                    print(f"跳过: {filename} (未找到匹配的URL)")
                    
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")

if __name__ == "__main__":
    numbered_rename()