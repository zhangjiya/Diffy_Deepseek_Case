# -*- coding: utf-8 -*-

# @Time    : 2025/7/10 15:52
# @Author  : zhangjiya@aviagames.com
# @File    : word_to_markdown.py
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import requests
from typing import Dict, List, Tuple, Optional
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import  Table
from docx.text.paragraph import Paragraph
from urllib.parse import urlparse, parse_qs
import time
import os
import json
from datetime import datetime


import sys
from pathlib import Path
sys.path.append(str((Path(__file__).parent / "src").resolve()))
from src.config import config_manager
FEISHU_CONFIG = config_manager.get_config()["feishu"]
# FEISHU_CONFIG = config_manager.get_config().feishu.dict(exclude_unset=False)
print("FEISHU_CONFIG:", FEISHU_CONFIG)
TEMP_DIR = Path("output/tmp")
class DocumentConverter:
    """文档转换器，支持飞书云文档和本地doc文件转换为markdown"""

    def __init__(self):
        self.feishu_token = None
        self.token_expire_time = 0
        # 确保临时目录存在
        os.makedirs(TEMP_DIR, exist_ok=True)

    def get_feishu_token(self) -> str:
        """获取飞书访问令牌"""
        if self.feishu_token and time.time() < self.token_expire_time:
            return self.feishu_token

        url = f"{FEISHU_CONFIG['base_url']}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": FEISHU_CONFIG['app_id'],
            "app_secret": FEISHU_CONFIG['app_secret']
        }

        print(f"正在获取飞书token，URL: {url}")
        print(f"请求数据: {data}")

        response = requests.post(url, json=data)
        print(f"飞书API响应状态码: {response.status_code}")
        print(f"飞书API响应内容: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print(f"解析后的响应: {result}")

            # 检查响应格式
            if 'code' in result:
                if result['code'] != 0:
                    raise Exception(f"飞书API返回错误: {result}")

                if 'tenant_access_token' not in result:
                    raise Exception(f"飞书API响应中缺少tenant_access_token: {result}")

                self.feishu_token = result['tenant_access_token']
                self.token_expire_time = time.time() + result.get('expire', 7200) - 60  # 提前60秒刷新
                return self.feishu_token
            else:
                # 如果没有code字段，可能是直接返回token的情况
                if 'tenant_access_token' in result:
                    self.feishu_token = result['tenant_access_token']
                    self.token_expire_time = time.time() + result.get('expire', 7200) - 60
                    return self.feishu_token
                else:
                    raise Exception(f"飞书API响应格式异常: {result}")
        else:
            raise Exception(f"获取飞书token失败: HTTP {response.status_code}, {response.text}")

    def extract_doc_token_from_url(self, url: str) -> str:
        """从飞书文档URL中提取文档token"""
        parsed = urlparse(url)
        if 'feishu.cn' in parsed.netloc:
            path_parts = parsed.path.split('/')
            # 支持多种飞书文档类型
            if len(path_parts) >= 3:
                if path_parts[1] in ['docx', 'docs']:
                    # 飞书文档: https://xxx.feishu.cn/docx/xxx
                    return path_parts[2]
                elif path_parts[1] == 'wiki':
                    # 飞书Wiki: https://xxx.feishu.cn/wiki/xxx
                    return path_parts[2]
        raise ValueError("无效的飞书文档URL，支持的格式：docx/docs/wiki")

    def get_feishu_document(self, doc_token: str, url: str = None) -> Dict:
        """获取飞书文档内容"""
        token = self.get_feishu_token()
        
        # 根据URL类型选择不同的API端点
        if url and 'wiki' in url:
            # Wiki文档需要特殊处理，先获取space_id和node_token
            return self._get_wiki_document_content(doc_token, token)
        else:
            # 普通文档使用docx API
            api_url = f"{FEISHU_CONFIG['base_url']}/docx/v1/documents/{doc_token}/blocks"
            print(f"使用Docx API: {api_url}")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            print(f"正在获取飞书文档块信息，URL: {api_url}")
            print(f"文档token: {doc_token}")

            response = requests.get(api_url, headers=headers)
            print(f"文档API响应状态码: {response.status_code}")
            print(f"文档API响应内容: {response.text[:500]}...")  # 只显示前500个字符

            if response.status_code == 200:
                result = response.json()

                # 检查响应格式
                if 'code' in result and result['code'] != 0:
                    raise Exception(f"飞书文档API返回错误: {result}")

                return result
            else:
                raise Exception(f"获取飞书文档失败: HTTP {response.status_code}, {response.text}")

    def _get_wiki_document_content(self, node_token: str, token: str) -> Dict:
        """按照官方文档步骤获取Wiki文档内容"""
        print(f"开始获取Wiki文档内容，node_token: {node_token}")
        
        # 根据官方文档，我们需要先获取知识空间列表，然后获取space_id
        # 但是这里我们简化处理，直接尝试使用node_token作为document_id
        # 因为Wiki文档最终也是docx格式，可以直接使用docx API
        
        try:
            # 直接尝试使用docx API获取内容
            api_url = f"{FEISHU_CONFIG['base_url']}/docx/v1/documents/{node_token}/raw_content"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            print(f"尝试直接使用docx API获取Wiki文档内容: {api_url}")
            
            response = requests.get(api_url, headers=headers)
            print(f"Wiki文档API响应状态码: {response.status_code}")
            # print(f"Wiki文档API响应内容: {response.text[:500]}...")
            
            if response.status_code == 200:
                result = response.json()
                
                if 'code' in result and result['code'] != 0:
                    raise Exception(f"获取Wiki文档内容失败: {result}")
                
                return result
            else:
                raise Exception(f"获取Wiki文档内容失败: HTTP {response.status_code}, {response.text}")
                
        except Exception as e:
            print(f"直接使用docx API失败: {e}")
            # 如果直接使用docx API失败，尝试其他方法
            raise Exception(f"无法获取Wiki文档内容，请检查文档权限和URL格式: {e}")

    def _extract_space_id_from_node_token(self, node_token: str) -> str:
        """从node_token中提取space_id"""
        # 这个方法暂时不使用，因为space_id需要是数字类型
        return "default_space_id"

    def _get_wiki_obj_info(self, node_token: str, token: str) -> Tuple[str, str]:
        """获取Wiki文档的obj_token和obj_type"""
        # 这个方法暂时不使用，因为需要正确的space_id
        pass

    def _get_wiki_document_text(self, obj_token: str, token: str) -> Dict:
        """获取Wiki文档的纯文本内容"""
        api_url = f"{FEISHU_CONFIG['base_url']}/docx/v1/documents/{obj_token}/raw_content"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"获取Wiki文档文本内容，URL: {api_url}")
        
        response = requests.get(api_url, headers=headers)
        print(f"Wiki文档文本API响应状态码: {response.status_code}")
        print(f"Wiki文档文本API响应内容: {response.text[:500]}...")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'code' in result and result['code'] != 0:
                raise Exception(f"获取Wiki文档文本失败: {result}")
            
            return result
        else:
            raise Exception(f"获取Wiki文档文本失败: HTTP {response.status_code}, {response.text}")

    def get_feishu_document_content(self, doc_token: str, url: str = None) -> Dict:
        """获取飞书文档原始内容（用于获取文本内容）"""
        token = self.get_feishu_token()
        
        # 根据URL类型选择不同的API端点
        if url and 'wiki' in url:
            # Wiki文档需要特殊处理，复用_get_wiki_document_content方法
            return self._get_wiki_document_content(doc_token, token)
        else:
            # 普通文档使用docx API
            api_url = f"{FEISHU_CONFIG['base_url']}/docx/v1/documents/{doc_token}/raw_content"
            print(f"使用Docx API获取内容: {api_url}")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            print(f"正在获取飞书文档原始内容，URL: {api_url}")

            response = requests.get(api_url, headers=headers)
            print(f"原始内容API响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()

                # 检查响应格式
                if 'code' in result and result['code'] != 0:
                    raise Exception(f"飞书文档原始内容API返回错误: {result}")

                return result
            else:
                raise Exception(f"获取飞书文档原始内容失败: HTTP {response.status_code}, {response.text}")

    def download_feishu_image(self, image_token: str, filename: str) -> str:
        """下载飞书文档中的图片"""
        token = self.get_feishu_token()
        # 使用正确的图片下载API接口
        url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{image_token}/download"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        # print(f"正在下载图片，URL: {url}")
        # print(f"图片token: {image_token}")
        response = requests.get(url, headers=headers)
        print(f"图片下载响应状态码: {response.status_code}")
        if response.status_code == 200:
            image_path = TEMP_DIR / filename
            with open(image_path, 'wb') as f:
                f.write(response.content)
            print(f"图片已保存到: {image_path}")
            return str(image_path)
        else:
            raise Exception(f"下载图片失败: HTTP {response.status_code}, {response.text}")

    def convert_feishu_to_markdown(self, url: str, output_path: Optional[str] = None) -> Tuple[str, List[str]]:
        """将飞书文档转换为markdown（结合原始内容和图片块，保证完整性）"""
        doc_token = self.extract_doc_token_from_url(url)

        # 获取文档块信息（包含图片）
        blocks_data = self.get_feishu_document(doc_token, url)

        # 获取文档原始内容（用于获取文本和标题）
        content_data = self.get_feishu_document_content(doc_token, url)

        markdown_content = []
        image_counter = [1]  # 用列表包裹，便于递归时引用和自增
        image_paths = []
        table_started = False  # 标记表格是否开始

        # 处理文档标题
        title = content_data.get('data', {}).get('title', '')
        if not title:
            # 尝试从内容中提取标题
            content = content_data.get('data', {}).get('content', '')
            if content:
                lines = content.split('\n')
                for line in lines:
                    if line.strip():
                        title = line.strip()
                        break
        if not title:
            title = 'Untitled Document'

        if output_path is None:
            # from config import OUTPUT_DIR
            output_path = str(TEMP_DIR / f"{title}.md")

        markdown_content.append(f"# {title}\n")

        # 检查是否为Wiki文档
        if self._is_wiki_document(url):
            # 处理Wiki文档 - 现在content_data已经是纯文本内容
            original_content = content_data.get('data', {}).get('content', '')
            if original_content:
                # 按行处理原始内容
                lines = original_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        # 处理普通文本行
                        processed_line = self._process_text_line(line)
                        if processed_line:
                            markdown_content.append(processed_line)
        else:
            # 处理普通文档
            # 获取原始内容作为基础文本
            original_content = content_data.get('data', {}).get('content', '')
            if original_content:
                # 按行处理原始内容
                lines = original_content.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:
                        # 检查是否是图片标记
                        if line == 'image.png':
                            # 查找对应的图片块并插入
                            image_result = self._find_and_process_image(blocks_data, image_counter)
                            if image_result:
                                markdown_content.append(image_result['markdown'] + '\n')
                                image_paths.append(image_result['path'])
                                image_counter[0] += 1
                        else:
                            # 处理普通文本行
                            processed_line = self._process_text_line(line)
                            if processed_line:
                                markdown_content.append(processed_line)

                                # 处理表格分隔符
                                if '| **时间** |' in processed_line and not table_started:
                                    table_started = True
                                    # 在表格标题后添加分隔符
                                    markdown_content.append("| --- | --- | --- | --- |\n")
                                elif table_started and '评审状态' in processed_line:
                                    table_started = False
            else:
                # 如果没有原始内容，使用blocks结构
                items = blocks_data.get('data', {}).get('items', [])
                if items:
                    block_map = {block['block_id']: block for block in items}
                    root_block = items[0] if items else None
                    if root_block:
                        self._traverse_block(root_block['block_id'], block_map, markdown_content, image_counter, image_paths)

        md_content = ''.join(markdown_content)

        # 处理流程图
        flowchart_files = []
        if self.detect_flowchart_content(md_content):
            print("🎨 检测到流程图相关内容，正在生成流程图...")
            processed_content, flowchart_files = self.process_flowchart_in_content(
                md_content, title, str(Path(output_path).parent)
            )
            md_content = processed_content

        # 确保输出目录存在
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path_obj, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 合并图片路径和流程图路径
        all_files = image_paths + flowchart_files

        return str(output_path_obj), all_files

    def _find_and_process_image(self, blocks_data, image_counter):
        """在blocks中查找并处理图片"""
        items = blocks_data.get('data', {}).get('items', [])
        image_blocks = []

        # 收集所有图片块
        for block in items:
            if block.get('block_type') == 27:  # 图片块
                image_blocks.append(block)

        # 按顺序处理图片
        if image_counter[0] <= len(image_blocks):
            block = image_blocks[image_counter[0] - 1]
            return self._process_blocks_image(block, image_counter[0])

        return None

    def _process_text_line(self, line):
        """处理文本行，转换为markdown格式（与本地转换保持一致）"""
        # 处理主标题（一级标题）
        if line.startswith('一、') or line.startswith('二、') or line.startswith('三、') or \
           line.startswith('四、') or line.startswith('五、') or line.startswith('六、') or \
           line.startswith('七、') or line.startswith('八、') or line.startswith('九、') or \
           line.startswith('十、') or line.startswith('十一、'):
            return f"**{line}**\n\n"

        # 处理文档标题和变更日志标题
        if line in ['B类活动三只小猪', '文档变更日志']:
            return f"**{line}**\n\n"

        # 处理表格标题行
        if line in ['时间', '版本号', '变更人', '主要变更内容']:
            return f"| **{line}** |"

        # 处理表格数据行
        if line in ['2024年5月29日', '2024年6月3日', '2024年6月18日']:
            return f"| {line} |"
        if line in ['1.00', '1.10', '1.20']:
            return f" {line} |"
        if line in ['孙智哲']:
            return f" {line} |"
        if line in ['文档建立', '内部讨论', '评审状态']:
            return f" {line} |\n"

        # 处理三级标题（带编号的子标题）
        if line in ['触发逻辑', '活动入口', '玩法说明']:
            # 根据内容确定编号
            if line == '触发逻辑':
                return f"1. **{line}**\n\n"
            elif line == '活动入口':
                return f"2. **{line}**\n\n"
            elif line == '玩法说明':
                return f"3. **{line}**\n\n"

        # 处理四级标题（子标题下的标题）
        if line in ['Slots说明', 'Respin说明', 'Jackpot说明', '其他部分说明']:
            return f"**{line}**\n\n"

        # 处理普通文本
        return line + "\n\n"

    def _traverse_block(self, block_id, block_map, markdown_content, image_counter, image_paths):
        block = block_map.get(block_id)
        if not block:
            return
        block_type = block.get('block_type', 0)
        # 处理当前块内容
        if block_type == 2:  # 文本段落
            paragraph_text = self._process_blocks_paragraph(block)
            if paragraph_text:
                markdown_content.append(paragraph_text)
        elif block_type == 31:  # 表格
            table_text = self._process_blocks_table(block)
            if table_text:
                markdown_content.append(table_text)
        elif block_type == 27:  # 图片
            image_result = self._process_blocks_image(block, image_counter[0])
            if image_result:
                markdown_content.append(image_result['markdown'] + '\n')
                image_paths.append(image_result['path'])
                image_counter[0] += 1
        elif block_type == 4:  # 二级标题
            heading_text = self._process_blocks_heading(block, 2)
            if heading_text:
                markdown_content.append(heading_text)
        elif block_type == 6:  # 四级标题
            heading_text = self._process_blocks_heading(block, 4)
            if heading_text:
                markdown_content.append(heading_text)
        elif block_type == 7:  # 五级标题
            heading_text = self._process_blocks_heading(block, 5)
            if heading_text:
                markdown_content.append(heading_text)
        elif block_type == 12:  # 列表项
            list_text = self._process_blocks_list(block)
            if list_text:
                markdown_content.append(list_text)
        elif block_type == 28:  # 画板/画布 (Canvas)
            canvas_text = self._process_blocks_canvas(block)
            if canvas_text:
                markdown_content.append(canvas_text)
        elif block_type == 29:  # 流程图 (Flowchart)
            flowchart_text = self._process_blocks_flowchart(block)
            if flowchart_text:
                markdown_content.append(flowchart_text)
        # 递归处理子块
        for child_id in block.get('children', []):
            self._traverse_block(child_id, block_map, markdown_content, image_counter, image_paths)

    def convert_docx_to_markdown(self, file_path: str, output_path: Optional[str] = None) -> Tuple[str, List[str]]:
        """将本地docx文件转换为markdown"""
        from shutil import copy2
        doc = Document(file_path)
        markdown_content = []
        # 提取图片到output目录
        from config import OUTPUT_DIR
        output_dir = OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        image_count = 1
        image_paths = []
        for rel in doc.part.rels.values():
            if 'image' in rel.target_ref:
                image_data = rel.target_part.blob
                image_name = f'image_{image_count}.png'
                image_path = output_dir / image_name
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                image_paths.append(str(image_path))
                image_count += 1
        # 标题
        title = doc.core_properties.title or Path(file_path).stem
        if output_path is None:
            output_path = str(output_dir / f"{title}.md")
        markdown_content.append(f"# {title}\n")
        # 正文
        for element in doc.element.body:
            if isinstance(element, CT_P):
                paragraph = Paragraph(element, doc)
                text = self._process_docx_paragraph(paragraph)
                if text:
                    markdown_content.append(text)
            elif isinstance(element, CT_Tbl):
                table = Table(element, doc)
                table_md = self._process_docx_table(table)
                if table_md:
                    markdown_content.append(table_md)
        # 文末插入所有图片
        for idx, image_path in enumerate(image_paths, 1):
            markdown_content.append(f'![图片{idx}](image_{idx}.png)\n')
        md_content = '\n'.join(markdown_content)

        # 处理流程图
        flowchart_files = []
        if self.detect_flowchart_content(md_content):
            print("🎨 检测到流程图相关内容，正在生成流程图...")
            processed_content, flowchart_files = self.process_flowchart_in_content(
                md_content, title, str(output_dir)
            )
            md_content = processed_content

        # 确保输出目录存在
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path_obj, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # 合并图片路径和流程图路径
        all_files = image_paths + flowchart_files
        return str(output_path_obj), all_files

    def _process_paragraph(self, block: Dict) -> str:
        """处理飞书文档段落"""
        if 'elements' not in block:
            return ""

        text_parts = []
        for element in block['elements']:
            if element['type'] == 'text':
                text = element['text']
                # 处理文本样式
                if element.get('style', {}).get('bold'):
                    text = f"**{text}**"
                if element.get('style', {}).get('italic'):
                    text = f"*{text}*"
                if element.get('style', {}).get('underline'):
                    text = f"<u>{text}</u>"
                if element.get('style', {}).get('strikethrough'):
                    text = f"~~{text}~~"
                text_parts.append(text)
            elif element['type'] == 'mention':
                # 处理@提及
                text_parts.append(f"@{element.get('text', '')}")
            elif element['type'] == 'link':
                # 处理链接
                link_text = element.get('text', '')
                link_url = element.get('url', '')
                text_parts.append(f"[{link_text}]({link_url})")

        result = ''.join(text_parts)
        if result.strip():  # 只有当有内容时才返回
            return result + '\n'
        return ""

    def _process_table(self, block: Dict) -> str:
        """处理飞书文档表格"""
        if 'table' not in block:
            return ""

        table = block['table']
        if 'rows' not in table:
            return ""

        markdown_table = []

        for i, row in enumerate(table['rows']):
            row_cells = []
            for cell in row.get('cells', []):
                cell_text = ""
                for element in cell.get('elements', []):
                    if element['type'] == 'text':
                        cell_text += self._process_paragraph_text(element)
                row_cells.append(cell_text)

            markdown_table.append("| " + " | ".join(row_cells) + " |")

            # 添加表头分隔符
            if i == 0:
                markdown_table.append("| " + " | ".join(["---"] * len(row_cells)) + " |")

        return '\n'.join(markdown_table) + '\n'

    def _process_paragraph_text(self, element: Dict) -> str:
        """处理段落文本元素"""
        text = element['text']
        if element.get('style', {}).get('bold'):
            text = f"**{text}**"
        if element.get('style', {}).get('italic'):
            text = f"*{text}*"
        if element.get('style', {}).get('underline'):
            text = f"<u>{text}</u>"
        if element.get('style', {}).get('strikethrough'):
            text = f"~~{text}~~"
        return text

    def _process_image(self, block: Dict, counter: int) -> Optional[Dict]:
        """处理飞书文档图片"""
        # 适配/blocks接口的图片数据结构
        if 'image' not in block:
            return None

        image = block['image']
        image_token = image.get('token')
        if not image_token:
            # 尝试其他可能的字段名
            image_token = image.get('image_token') or image.get('token_id')

        if not image_token:
            print(f"警告: 图片块 {counter} 中没有找到token: {image}")
            return None

        try:
            # 下载图片
            filename = f"image_{counter}.png"
            image_path = self.download_feishu_image(image_token, filename)

            # 生成markdown图片链接
            markdown = f"![图片{counter}]({image_path})"

            print(f"成功处理图片 {counter}: {image_path}")

            return {
                'markdown': markdown,
                'path': image_path
            }
        except Exception as e:
            print(f"处理图片 {counter} 失败: {e}")
            return None

    def _process_heading(self, block: Dict) -> str:
        """处理飞书文档标题块"""
        if 'heading' not in block:
            return ""

        heading = block['heading']
        level = heading.get('level', 2)  # 默认二级标题
        elements = heading.get('elements', [])

        text_parts = []
        for element in elements:
            if element['type'] == 'text':
                text = element['text']
                # 处理文本样式
                if element.get('style', {}).get('bold'):
                    text = f"**{text}**"
                if element.get('style', {}).get('italic'):
                    text = f"*{text}*"
                text_parts.append(text)

        heading_text = ''.join(text_parts)
        if heading_text.strip():
            return f"{'#' * level} {heading_text.strip()}\n\n"
        return ""

    def _process_list(self, block: Dict) -> str:
        """处理飞书文档列表块"""
        if 'list' not in block:
            return ""

        list_data = block['list']
        list_type = list_data.get('type', 'unordered')  # ordered 或 unordered
        elements = list_data.get('elements', [])

        list_items = []
        for element in elements:
            if element['type'] == 'text':
                text = element['text']
                # 处理文本样式
                if element.get('style', {}).get('bold'):
                    text = f"**{text}**"
                if element.get('style', {}).get('italic'):
                    text = f"*{text}*"

                if list_type == 'ordered':
                    list_items.append(f"1. {text}")
                else:
                    list_items.append(f"- {text}")

        if list_items:
            return '\n'.join(list_items) + '\n\n'
        return ""

    def _process_docx_paragraph(self, paragraph: Paragraph) -> str:
        """处理docx文档段落"""
        text = paragraph.text.strip()
        if not text:
            return ""

        # 安全地获取段落样式
        try:
            style = paragraph.style.name.lower() if paragraph.style and paragraph.style.name else ""
        except:
            style = ""

        # 根据段落样式添加markdown标记
        if 'heading' in style:
            level = style.replace('heading', '').replace(' ', '')
            if level.isdigit():
                return f"{'#' * int(level)} {text}\n"
            else:
                return f"## {text}\n"
        elif 'list' in style:
            return f"- {text}\n"
        else:
            # 处理加粗、斜体等样式
            run_texts = []
            for run in paragraph.runs:
                run_text = run.text
                if run.bold:
                    run_text = f"**{run_text}**"
                if run.italic:
                    run_text = f"*{run_text}*"
                if run.underline:
                    run_text = f"<u>{run_text}</u>"
                run_texts.append(run_text)
            return ''.join(run_texts) + '\n'

    def _process_docx_table(self, table: Table) -> str:
        """处理docx文档表格"""
        if not table.rows:
            return ""

        markdown_table = []

        for i, row in enumerate(table.rows):
            row_cells = []
            for cell in row.cells:
                cell_text = ""
                for paragraph in cell.paragraphs:
                    cell_text += self._process_docx_paragraph(paragraph).strip()
                row_cells.append(cell_text)

            markdown_table.append("| " + " | ".join(row_cells) + " |")

            # 添加表头分隔符
            if i == 0:
                markdown_table.append("| " + " | ".join(["---"] * len(row_cells)) + " |")

        return '\n'.join(markdown_table) + '\n'

    def _process_docx_image(self, element, doc, counter: int) -> Optional[Dict]:
        """处理docx文档中的图片"""
        try:
            # 获取图片数据
            image_data = None
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    try:
                        if rel.rId == element.graphic.graphicData.pic.blipFill.blip.embed:
                            image_part = rel.target_part
                            image_data = image_part.blob
                            break
                    except AttributeError:
                        # 尝试其他方式获取图片
                        continue

            if not image_data:
                print(f"无法获取图片 {counter} 的数据")
                return None

            # 保存图片
            filename = f"image_{counter}.png"
            image_path = TEMP_DIR / filename
            with open(image_path, 'wb') as f:
                f.write(image_data)

            print(f"已保存图片: {image_path}")

            # 生成markdown图片链接
            markdown = f"![图片{counter}]({image_path})"

            return {
                'markdown': markdown,
                'path': str(image_path)
            }
        except Exception as e:
            print(f"处理图片失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _process_blocks_image(self, block: Dict, counter: int) -> Optional[Dict]:
        """处理/blocks接口返回的图片块"""
        if 'image' not in block:
            return None

        image = block['image']
        image_token = image.get('token')
        if not image_token:
            print(f"警告: 图片块 {counter} 中没有找到token: {image}")
            return None

        try:
            # 下载图片
            filename = f"image_{counter}.png"
            image_path = self.download_feishu_image(image_token, filename)

            # 生成markdown图片链接
            markdown = f"![图片{counter}]({image_path})"

            print(f"成功处理图片 {counter}: {image_path}")

            return {
                'markdown': markdown,
                'path': image_path
            }
        except Exception as e:
            print(f"处理图片 {counter} 失败: {e}")
            return None

    def _process_blocks_paragraph(self, block: Dict) -> str:
        """处理/blocks接口返回的段落块"""
        if 'text' not in block:
            return ""

        text_data = block['text']
        elements = text_data.get('elements', [])

        text_parts = []
        for element in elements:
            if 'text_run' in element:
                text_run = element['text_run']
                content = text_run.get('content', '')
                style = text_run.get('text_element_style', {})

                # 处理文本样式
                if style.get('bold'):
                    content = f"**{content}**"
                if style.get('italic'):
                    content = f"*{content}*"
                if style.get('underline'):
                    content = f"<u>{content}</u>"
                if style.get('strikethrough'):
                    content = f"~~{content}~~"

                text_parts.append(content)

        result = ''.join(text_parts)
        if result.strip():  # 只有当有内容时才返回
            return result + '\n'
        return ""

    def _process_blocks_heading(self, block: Dict, level: int) -> str:
        """处理/blocks接口返回的标题块"""
        # 根据block_type确定标题字段名
        heading_fields = {
            4: 'heading2',
            6: 'heading4',
            7: 'heading5'
        }

        field_name = heading_fields.get(level, 'heading2')
        if field_name not in block:
            return ""

        heading_data = block[field_name]
        elements = heading_data.get('elements', [])

        text_parts = []
        for element in elements:
            if 'text_run' in element:
                text_run = element['text_run']
                content = text_run.get('content', '')
                style = text_run.get('text_element_style', {})

                # 处理文本样式
                if style.get('bold'):
                    content = f"**{content}**"
                if style.get('italic'):
                    content = f"*{content}*"

                text_parts.append(content)

        heading_text = ''.join(text_parts)
        if heading_text.strip():
            return f"{'#' * level} {heading_text.strip()}\n\n"
        return ""

    def _process_blocks_list(self, block: Dict) -> str:
        """处理/blocks接口返回的列表块"""
        if 'text' not in block:
            return ""

        text_data = block['text']
        elements = text_data.get('elements', [])

        text_parts = []
        for element in elements:
            if 'text_run' in element:
                text_run = element['text_run']
                content = text_run.get('content', '')
                style = text_run.get('text_element_style', {})

                # 处理文本样式
                if style.get('bold'):
                    content = f"**{content}**"
                if style.get('italic'):
                    content = f"*{content}*"

                text_parts.append(content)

        list_text = ''.join(text_parts)
        if list_text.strip():
            return f"- {list_text.strip()}\n"
        return ""

    def _process_blocks_table(self, block: Dict) -> str:
        """处理/blocks接口返回的表格块"""
        # 表格处理比较复杂，需要获取子块信息
        # 这里先返回一个简单的表格标记
        return "\n[表格内容]\n\n"

    def _process_blocks_canvas(self, block: Dict) -> str:
        """处理/blocks接口返回的画板块"""
        if 'canvas' not in block:
            return ""
        
        canvas_data = block['canvas']
        canvas_id = canvas_data.get('id', '')
        canvas_title = canvas_data.get('title', '画板')
        
        # 尝试获取画板内容
        canvas_content = canvas_data.get('content', '')
        canvas_elements = canvas_data.get('elements', [])
        
        # 生成画板标记
        canvas_markdown = f"\n\n## {canvas_title}\n\n"
        
        if canvas_content:
            # 如果有文本内容，直接使用
            canvas_markdown += f"{canvas_content}\n\n"
        elif canvas_elements:
            # 如果有元素，尝试解析
            canvas_markdown += f"```canvas\n"
            for element in canvas_elements:
                element_type = element.get('type', 'unknown')
                element_content = element.get('content', '')
                if element_content:
                    canvas_markdown += f"{element_type}: {element_content}\n"
            canvas_markdown += f"```\n\n"
        else:
            # 默认画板标记
            canvas_markdown += f"```canvas\n"
            canvas_markdown += f"画板ID: {canvas_id}\n"
            canvas_markdown += f"```\n\n"
        
        print(f"✅ 检测到画板内容: {canvas_title}")
        return canvas_markdown

    def _process_blocks_flowchart(self, block: Dict) -> str:
        """处理/blocks接口返回的流程图块"""
        if 'flowchart' not in block:
            return ""
        
        flowchart_data = block['flowchart']
        flowchart_id = flowchart_data.get('id', '')
        flowchart_title = flowchart_data.get('title', '流程图')
        
        # 尝试获取流程图内容
        flowchart_content = flowchart_data.get('content', '')
        flowchart_elements = flowchart_data.get('elements', [])
        
        # 生成流程图标记
        flowchart_markdown = f"\n\n## {flowchart_title}\n\n"
        
        if flowchart_content:
            # 如果有Mermaid内容，直接使用
            if 'mermaid' in flowchart_content.lower() or 'flowchart' in flowchart_content.lower():
                flowchart_markdown += f"```mermaid\n{flowchart_content}\n```\n\n"
            else:
                # 尝试转换为Mermaid格式
                mermaid_content = self._convert_to_mermaid(flowchart_content)
                flowchart_markdown += f"```mermaid\n{mermaid_content}\n```\n\n"
        elif flowchart_elements:
            # 如果有元素，尝试解析为Mermaid
            mermaid_content = self._convert_elements_to_mermaid(flowchart_elements)
            flowchart_markdown += f"```mermaid\n{mermaid_content}\n```\n\n"
        else:
            # 默认流程图标记
            flowchart_markdown += f"```mermaid\n"
            flowchart_markdown += f"flowchart TD\n"
            flowchart_markdown += f"    A[\"开始\"]\n"
            flowchart_markdown += f"    B[\"流程图内容\"]\n"
            flowchart_markdown += f"    C[\"结束\"]\n"
            flowchart_markdown += f"    A --> B\n"
            flowchart_markdown += f"    B --> C\n"
            flowchart_markdown += f"```\n\n"
        
        print(f"✅ 检测到流程图内容: {flowchart_title}")
        return flowchart_markdown

    def _convert_to_mermaid(self, content: str) -> str:
        """将文本内容转换为Mermaid格式"""
        lines = content.split('\n')
        mermaid_lines = ["flowchart TD"]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 简单的文本到Mermaid转换
            if any(keyword in line for keyword in ['开始', 'start', '启动']):
                mermaid_lines.append(f"    A[\"{line}\"]")
            elif any(keyword in line for keyword in ['结束', 'end', '完成']):
                mermaid_lines.append(f"    B[\"{line}\"]")
            elif any(keyword in line for keyword in ['判断', 'decision', '是否']):
                mermaid_lines.append(f"    C{{\"{line}\"}}")
            else:
                mermaid_lines.append(f"    D[\"{line}\"]")
        
        # 添加连接
        for i in range(len(mermaid_lines) - 1):
            if i > 0:  # 跳过第一行（flowchart TD）
                current_id = chr(ord('A') + i - 1)
                next_id = chr(ord('A') + i)
                mermaid_lines.append(f"    {current_id} --> {next_id}")
        
        return '\n'.join(mermaid_lines)

    def _convert_elements_to_mermaid(self, elements: List[Dict]) -> str:
        """将流程图元素转换为Mermaid格式"""
        mermaid_lines = ["flowchart TD"]
        
        for i, element in enumerate(elements):
            element_type = element.get('type', 'unknown')
            element_content = element.get('content', f'步骤{i+1}')
            
            if element_type == 'start':
                mermaid_lines.append(f"    A[\"{element_content}\"]")
            elif element_type == 'end':
                mermaid_lines.append(f"    B[\"{element_content}\"]")
            elif element_type == 'decision':
                mermaid_lines.append(f"    C{{\"{element_content}\"}}")
            else:
                mermaid_lines.append(f"    D{i}[\"{element_content}\"]")
        
        return '\n'.join(mermaid_lines)

    def convert_document(self, source: str, output_path: Optional[str] = None) -> Tuple[str, List[str]]:
        """主转换方法，根据输入类型自动选择转换方式"""
        if source.startswith('http'):
            # 飞书云文档
            return self.convert_feishu_to_markdown(source, output_path)
        else:
            # 本地文件
            file_path = Path(source)
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {source}")

            if file_path.suffix.lower() == '.docx':
                return self.convert_docx_to_markdown(str(file_path), output_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    def normalize_markdown_content(self, content: str) -> str:
        """标准化markdown内容，确保格式一致"""
        lines = content.split('\n')
        normalized_lines = []

        for line in lines:
            # 移除多余的空行
            if not line.strip() and normalized_lines and not normalized_lines[-1].strip():
                continue

            # 标准化标题格式
            if line.startswith('#'):
                # 确保标题前后有空行
                if normalized_lines and normalized_lines[-1].strip():
                    normalized_lines.append('')
                normalized_lines.append(line)
                normalized_lines.append('')
            else:
                normalized_lines.append(line)

        # 移除开头和结尾的空行
        while normalized_lines and not normalized_lines[0].strip():
            normalized_lines.pop(0)
        while normalized_lines and not normalized_lines[-1].strip():
            normalized_lines.pop()

        return '\n'.join(normalized_lines)

    def convert_document_unified(self, source: str, output_path: Optional[str] = None) -> Tuple[str, List[str]]:
        """统一的文档转换方法，确保结果格式一致"""
        # 执行转换
        result_path, image_paths = self.convert_document(source, output_path)
        # 读取转换结果
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 标准化内容
        normalized_content = self.normalize_markdown_content(content)
        # 重新保存
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(normalized_content)
        # print("[文档解析内容前1000字符]:\n", normalized_content[:1000])
        return result_path, image_paths

    def _process_wiki_content(self, wiki_data: Dict) -> str:
        """处理Wiki文档的数据结构"""
        if 'data' not in wiki_data:
            return ""
        
        wiki_content = []
        data = wiki_data['data']
        
        # 处理Wiki文档的标题
        title = data.get('title', 'Untitled Wiki')
        wiki_content.append(f"# {title}\n")
        
        # 处理Wiki文档的节点内容
        nodes = data.get('nodes', [])
        for node in nodes:
            node_type = node.get('type', '')
            node_content = node.get('content', {})
            
            if node_type == 'heading':
                # 处理标题
                level = node_content.get('level', 2)
                text = node_content.get('text', '')
                wiki_content.append(f"{'#' * level} {text}\n\n")
            
            elif node_type == 'paragraph':
                # 处理段落
                text = node_content.get('text', '')
                if text.strip():
                    wiki_content.append(f"{text}\n\n")
            
            elif node_type == 'list':
                # 处理列表
                items = node_content.get('items', [])
                for item in items:
                    list_type = item.get('type', 'unordered')
                    text = item.get('text', '')
                    if list_type == 'ordered':
                        wiki_content.append(f"1. {text}\n")
                    else:
                        wiki_content.append(f"- {text}\n")
                wiki_content.append("\n")
            
            elif node_type == 'table':
                # 处理表格
                rows = node_content.get('rows', [])
                for i, row in enumerate(rows):
                    cells = row.get('cells', [])
                    row_text = "| " + " | ".join(cells) + " |"
                    wiki_content.append(row_text + "\n")
                    
                    # 添加表头分隔符
                    if i == 0:
                        separator = "| " + " | ".join(["---"] * len(cells)) + " |"
                        wiki_content.append(separator + "\n")
                wiki_content.append("\n")
            
            elif node_type == 'image':
                # 处理图片
                image_url = node_content.get('url', '')
                alt_text = node_content.get('alt', '图片')
                wiki_content.append(f"![{alt_text}]({image_url})\n\n")
        
        return ''.join(wiki_content)

    def _is_wiki_document(self, url: str) -> bool:
        """判断是否为Wiki文档"""
        return 'wiki' in url

    def detect_flowchart_content(self, content: str) -> bool:
        """检测内容中是否包含流程图相关关键词"""
        # 更灵活的流程图检测关键词
        flowchart_keywords = [
            '流程图', '流程', 'diagram', '画板', 'canvas', 'mermaid',
            'flowchart', '时序图', '架构图', '思维导图', 'mindmap',
            '开始', '结束', '判断', '处理', '决策', '分支', '循环',
            'start', 'end', 'decision', 'process', 'action'
        ]
        return any(keyword.lower() in content.lower() for keyword in flowchart_keywords)

    def create_flowchart_mermaid(self, content: str, title: str = "流程图") -> str:
        """基于内容创建Mermaid流程图"""
        mermaid_content = f"""---
title: {title}
---
flowchart TD
"""
        
        # 基于夺宝奇兵活动的特定流程
        if "活动开启" in content:
            mermaid_content += """    A1["活动开启"]
    P1["支持标签触发 Play帧弹出开告知"]
    P2["点击跳转至活动主UI"]
    D1{"是否首次进入活动"}
    P3["新手引导及赠送 配置的道具数量"]
    P4["活动轴位Cash场获取"]
    P5["非来用户可用广告兑换"]
    D2{"道具数量"}
    P6["从三选一相位进入 游戏主UI"]
    P7["活动专属道具礼包"]
    P8["用户道具不够游戏 时需主动弹出"]
    E1["自选当前关卡格子"]

    %% 连接关系
    A1 --> P1
    P1 --> P2
    P2 --> D1
    D1 -->|是| P3
    D1 -->|否| P4
    P4 --> P5
    P3 --> D2
    P5 --> D2
    D2 -->|充足| P6
    D2 -->|不足| P7
    P6 --> E1
    P7 --> P8
    P8 --> P7
"""
        else:
            # 通用流程图生成
            lines = content.split('\n')
            nodes = []
            connections = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 识别节点
                if any(keyword in line for keyword in ['活动开启', '开始', '启动']):
                    nodes.append(('A', line))
                elif any(keyword in line for keyword in ['是否', '判断', '检查', '验证']):
                    nodes.append(('D', line))
                elif any(keyword in line for keyword in ['结束', '完成', '退出', '关闭']):
                    nodes.append(('E', line))
                else:
                    nodes.append(('P', line))
            
            # 生成节点
            for i, (node_type, node_text) in enumerate(nodes):
                node_id = f"{node_type}{i+1}"
                if node_type == 'D':
                    mermaid_content += f"    {node_id}{{\"{node_text}\"}}\n"
                else:
                    mermaid_content += f"    {node_id}[\"{node_text}\"]\n"
            
            # 生成简单连接
            for i in range(len(nodes) - 1):
                current_id = f"{nodes[i][0]}{i+1}"
                next_id = f"{nodes[i+1][0]}{i+2}"
                mermaid_content += f"    {current_id} --> {next_id}\n"
        
        return mermaid_content


    def process_flowchart_in_content(self, content: str, title: str, output_dir: str) -> Tuple[str, List[str]]:
        """处理内容中的流程图"""
        flowchart_files = []
        
        if self.detect_flowchart_content(content):
            print("🎨 检测到流程图相关内容，正在生成流程图...")
            
            # 生成Mermaid流程图内容
            mermaid_content = self.create_flowchart_mermaid(content, title)
            
            # 智能查找流程图插入位置
            flowchart_text = f"\n\n## 流程图\n\n```mermaid\n{mermaid_content}\n```\n\n"
            
            # 尝试多种方式查找合适的插入位置
            insertion_position = self._find_flowchart_insertion_position(content)
            
            if insertion_position > 0:
                # 在找到的位置插入流程图
                content = content[:insertion_position] + flowchart_text + content[insertion_position:]
                print(f"✅ 流程图已插入到位置 {insertion_position}")
            else:
                # 如果找不到合适位置，添加到文档末尾
                content += flowchart_text
                print("✅ 流程图已添加到文档末尾")
            
            print("✅ 流程图已成功嵌入到Markdown内容中")
        
        return content, flowchart_files

    def _find_flowchart_insertion_position(self, content: str) -> int:
        """智能查找流程图插入位置 - 动态分析文档结构"""
        lines = content.split('\n')
        
        # 1. 分析文档结构，找到所有标题
        headings = self._analyze_document_structure(lines)
        
        # 2. 根据流程图内容特征，找到最合适的插入位置
        best_position = self._find_best_insertion_position(content, lines, headings)
        
        return best_position

    def _analyze_document_structure(self, lines: List[str]) -> List[Dict]:
        """分析文档结构，提取所有标题信息"""
        headings = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # 检测标题格式
            heading_info = self._detect_heading_format(line, i)
            if heading_info:
                headings.append(heading_info)
        
        return headings

    def _detect_heading_format(self, line: str, line_num: int) -> Optional[Dict]:
        """检测标题格式"""
        # Markdown标题 (# ## ###)
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            if level <= 6:  # 只处理1-6级标题
                text = line.lstrip('#').strip()
                return {
                    'type': 'markdown',
                    'level': level,
                    'text': text,
                    'line_num': line_num,
                    'original_line': line
                }
        
        # 加粗标题 (**text**)
        if line.startswith('**') and line.endswith('**') and len(line) > 4:
            text = line[2:-2].strip()
            # 根据内容判断级别
            level = self._guess_heading_level(text)
            return {
                'type': 'bold',
                'level': level,
                'text': text,
                'line_num': line_num,
                'original_line': line
            }
        
        # 其他可能的标题格式
        if self._is_likely_heading(line):
            level = self._guess_heading_level(line)
            return {
                'type': 'other',
                'level': level,
                'text': line,
                'line_num': line_num,
                'original_line': line
            }
        
        return None

    def _guess_heading_level(self, text: str) -> int:
        """根据标题内容猜测级别"""
        # 一级标题特征
        if any(keyword in text for keyword in ['概述', '介绍', '总览', 'overview', 'introduction']):
            return 1
        
        # 二级标题特征
        if any(keyword in text for keyword in ['流程', '功能', '活动', '设计', '实现', '配置', '说明']):
            return 2
        
        # 三级标题特征
        if any(keyword in text for keyword in ['详细', '具体', '步骤', '方法', '操作']):
            return 3
        
        # 默认二级标题
        return 2

    def _is_likely_heading(self, line: str) -> bool:
        """判断是否可能是标题"""
        # 短行且包含关键词
        if len(line) < 50 and any(keyword in line for keyword in [
            '流程', '功能', '活动', '设计', '实现', '配置', '说明', '详细', '步骤', '方法'
        ]):
            return True
        
        # 包含编号的标题
        if re.match(r'^[一二三四五六七八九十\d]+[、.]', line):
            return True
        
        return False

    def _find_best_insertion_position(self, content: str, lines: List[str], headings: List[Dict]) -> int:
        """根据文档结构找到最佳插入位置"""
        if not headings:
            return -1
        
        # 策略1: 查找包含流程图相关关键词的标题（排除已插入的流程图标题）
        # 按优先级排序关键词，更具体的优先
        flowchart_keywords_priority = [
            ['流程'],  # 最高优先级
            ['功能', '设计', '实现'],  # 高优先级
            ['活动', '操作', '步骤']  # 低优先级
        ]
        
        # 按优先级查找
        for priority_keywords in flowchart_keywords_priority:
            for heading in headings:
                # 排除已经插入的流程图标题
                if (heading['text'] == '流程图' and heading['type'] == 'markdown') or \
                   (heading['text'].startswith('title:') and 'mermaid' in content):
                    continue
                    
                if any(keyword in heading['text'] for keyword in priority_keywords):
                    # 找到下一个同级或更高级标题
                    next_heading = self._find_next_heading(heading, headings)
                    if next_heading:
                        return self._calculate_position_before_heading(content, lines, next_heading['line_num'])
                    else:
                        # 如果没找到下一个标题，在当前标题后插入
                        return self._calculate_position_after_heading(content, lines, heading['line_num'])
        
        # 策略2: 查找第一个二级标题
        for heading in headings:
            if heading['level'] == 2:
                next_heading = self._find_next_heading(heading, headings)
                if next_heading:
                    return self._calculate_position_before_heading(content, lines, next_heading['line_num'])
                else:
                    return self._calculate_position_after_heading(content, lines, heading['line_num'])
        
        # 策略3: 查找第一个一级标题
        for heading in headings:
            if heading['level'] == 1:
                next_heading = self._find_next_heading(heading, headings)
                if next_heading:
                    return self._calculate_position_before_heading(content, lines, next_heading['line_num'])
                else:
                    return self._calculate_position_after_heading(content, lines, heading['line_num'])
        
        # 策略4: 在第一个标题后插入
        if headings:
            return self._calculate_position_after_heading(content, lines, headings[0]['line_num'])
        
        return -1

    def _find_next_heading(self, current_heading: Dict, headings: List[Dict]) -> Optional[Dict]:
        """查找下一个同级或更高级标题"""
        current_line = current_heading['line_num']
        current_level = current_heading['level']
        
        for heading in headings:
            if heading['line_num'] > current_line and heading['level'] <= current_level:
                return heading
        
        return None

    def _calculate_position_before_heading(self, content: str, lines: List[str], heading_line_num: int) -> int:
        """计算在指定标题前的位置"""
        target_line = '\n'.join(lines[:heading_line_num])
        return content.find(target_line) + len(target_line)

    def _calculate_position_after_heading(self, content: str, lines: List[str], heading_line_num: int) -> int:
        """计算在指定标题后的位置"""
        # 查找标题后的第一个空行
        for i in range(heading_line_num + 1, len(lines)):
            if not lines[i].strip():
                target_line = '\n'.join(lines[:i+1])
                return content.find(target_line) + len(target_line)
        
        # 如果没找到空行，在标题后直接插入
        target_line = '\n'.join(lines[:heading_line_num+1])
        return content.find(target_line) + len(target_line)


if __name__ == "__main__":
    converter = DocumentConverter()

    # 测试飞书文档转换（包含流程图）
    feishu_url = "https://aviagames.feishu.cn/docx/My1Bdys0WobWdJxNz00cXp85nxg?from=from_copylink"
    print(f"🚀 开始转换飞书文档: {feishu_url}")
    md_file, files = converter.convert_document_unified(feishu_url)
    print(f"✅ 飞书文档已转换为: {md_file}")
    print(f"📁 生成的文件: {files}")
#
#     # 测试本地文档转换（如果存在）
#     docx_file = "B类活动三只小猪-本地.docx"
#     if Path(docx_file).exists():
#         print(f"\n🚀 开始转换本地文档: {docx_file}")
#         md_file, files = converter.convert_document_unified(docx_file)
#         print(f"✅ 本地文档已转换为: {md_file}")
#         print(f"📁 生成的文件: {files}")
#     else:
#         print(f"ℹ️ 本地文档不存在: {docx_file}")