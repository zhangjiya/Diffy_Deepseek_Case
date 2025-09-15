import requests
import base64
import os
import time
from pathlib import Path
from src.config import config_manager

class DoubaoEngine:
    def __init__(self, key_id=None, model=None, temperature=None, top_p=None):
        # 获取指定密钥的配置
        key_config = config_manager.get_doubao_key_config(key_id)
        
        self.api_key = key_config["api_key"]
        self.base_url = key_config["base_url"]
        self.model = model or key_config["model"]
        self.max_tokens = key_config.get("max_tokens", 16384)
        self.temperature = temperature if temperature is not None else key_config.get("temperature", 0.3)
        self.top_p = top_p if top_p is not None else key_config.get("top_p", 0.6)
        self.key_id = key_id
        self.key_name = key_config.get("name", f"密钥{key_id}")

    def generate_test_cases(self, content, document_url="", document_title="测试用例", user_requirements=""):
        """生成测试用例"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 构建消息
                messages = [
                    {
                        "role": "system",
                        "content": "你是一名资深QA，基于需求文档生成测试用例。按以下结构输出：\n\n功能模块:<模块名>\n\n测试点:<边界值/异常流>\n\n用例步骤:<步骤>\n\n预期结果:<结果>\n\n"
                    }
                ]
                
                # 处理多模态内容（文本+图片）
                user_content = self._build_multimodal_content(content, document_url, user_requirements)
                
                # 根据内容类型构建消息
                if isinstance(user_content, list):
                    # 多模态内容（包含图片）
                    print(f"【豆包AI调用】构建多模态消息，包含 {len(user_content)} 个内容块")
                    messages.append({
                        "role": "user",
                        "content": user_content
                    })
                else:
                    # 纯文本内容
                    print("【豆包AI调用】构建纯文本消息")
                    messages.append({
                        "role": "user",
                        "content": user_content
                    })
                
                # 构建请求数据
                data = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p
                }
                
                # 添加调试信息
                print(f"【豆包AI调用】请求数据大小: {len(str(data))} 字符")
                if isinstance(user_content, list):
                    print(f"【豆包AI调用】多模态内容详情:")
                    for i, item in enumerate(user_content):
                        if item.get("type") == "text":
                            print(f"  文本块 {i+1}: {item['text'][:50]}...")
                        elif item.get("type") == "image_url":
                            url = item['image_url']['url']
                            print(f"  图片块 {i+1}: {url[:50]}...")
                
                # 计算内容长度
                content_length = len(str(content))
                
                # 发送请求
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # 根据内容长度设置HTTP请求头超时（推荐方式）
                # 根据官方文档，最大支持900秒（15分钟）
                if content_length > 50000:  # 超大文档
                    headers["Timeout"] = "900"  # 15分钟（官方最大支持）
                elif content_length > 20000:  # 大文档
                    headers["Timeout"] = "600"  # 10分钟
                elif content_length > 10000:  # 中等文档
                    headers["Timeout"] = "300"  # 5分钟
                else:  # 小文档
                    headers["Timeout"] = "180"  # 3分钟
                
                print(f"【豆包AI调用】密钥: {self.key_name}({self.key_id}), 模型: {self.model}, 尝试: {attempt + 1}/{max_retries}")
                print(f"【豆包AI调用】HTTP请求头超时: {headers['Timeout']}秒")
                
                # 根据官方文档优化超时设置
                # 连接超时和读取超时分别设置，最大支持900秒
                if content_length > 50000:  # 超大文档（包含大量图片）
                    connection_timeout = 30
                    read_timeout = 900  # 15分钟读取超时（官方最大支持）
                elif content_length > 20000:  # 大文档
                    connection_timeout = 30
                    read_timeout = 600  # 10分钟读取超时
                elif content_length > 10000:  # 中等文档
                    connection_timeout = 30
                    read_timeout = 300  # 5分钟读取超时
                else:  # 小文档
                    connection_timeout = 30
                    read_timeout = 180  # 3分钟读取超时
                
                timeout = (connection_timeout, read_timeout)
                print(f"【豆包AI调用】客户端超时设置: 连接{connection_timeout}秒, 读取{read_timeout}秒")
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    print(f"【豆包AI调用】响应内容：{content[:200]}...")
                    return {
                        "success": True,
                        "raw_response": content,
                        "file": None
                    }
                else:
                    print(f"【豆包AI调用】请求失败: {response.status_code}")
                    print(f"【豆包AI调用】错误响应: {response.text}")
                    print(f"【豆包AI调用】请求数据大小: {len(str(data))} 字符")
                    if attempt < max_retries - 1:
                        print(f"【豆包AI调用】将在{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        return {
                            "success": False,
                            "raw_response": f"AI调用失败: {response.status_code} - {response.text}",
                            "file": None
                        }
                    
            except requests.exceptions.Timeout as e:
                print(f"【豆包AI调用】超时异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"【豆包AI调用】将在{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return {
                        "success": False,
                        "raw_response": f"AI调用超时: {str(e)}",
                        "file": None
                    }
            except Exception as e:
                print(f"【豆包AI调用】异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"【豆包AI调用】将在{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return {
                        "success": False,
                        "raw_response": f"AI调用异常: {str(e)}",
                        "file": None
                    }
        
        return {
            "success": False,
            "raw_response": "AI调用失败: 超过最大重试次数",
            "file": None
        }
    
    def _build_multimodal_content(self, content, document_url, user_requirements):
        """构建多模态内容，支持文本和图片"""
        import re
        from pathlib import Path
        
        # 基础文本内容
        text_content = f"请基于以下需求文档生成完整的测试用例：\n\n文档URL: {document_url}\n\n文档内容: {content}\n\n"
        if user_requirements:
            text_content += f"用户要求: {user_requirements}\n\n"
        text_content += "请确保覆盖所有功能点，包括正常流程、边界条件和异常情况。\n\n"
        
        # 检查是否包含图片链接
        image_pattern = r'!\[图片\d+\]\((.*?)\)'
        image_matches = re.findall(image_pattern, content)
        
        if not image_matches:
            # 没有图片，直接返回文本内容
            return text_content
        
        # 去重并限制图片数量（豆包API限制最多5张图片，减少数量避免问题）
        unique_images = list(set(image_matches))[:5]  # 去重并限制最多5张图片
        
        if len(image_matches) > 5:
            print(f"【豆包AI调用】检测到{len(image_matches)}张图片，限制为前5张")
        
        # 豆包API的多模态格式：将图片作为content的一部分
        # 先构建包含图片引用的文本内容
        enhanced_text = text_content
        
        # 处理图片，将图片转换为base64并嵌入到文本中
        processed_images = []
        for i, image_path in enumerate(unique_images):
            if os.path.exists(image_path):
                # 预检查图片格式 - 根据豆包API文档，只支持JPEG和PNG
                file_extension = image_path.lower().split('.')[-1]
                supported_formats = {'jpg', 'jpeg', 'png'}
                if file_extension not in supported_formats:
                    print(f"【豆包AI调用】跳过不支持的图片格式: {image_path} (格式: {file_extension})")
                    continue
                try:
                    # 检查图片大小，如果太大则跳过
                    file_size = os.path.getsize(image_path)
                    if file_size > 2 * 1024 * 1024:  # 2MB限制，减少大小避免问题
                        print(f"【豆包AI调用】图片过大跳过: {image_path} ({file_size/1024/1024:.1f}MB)")
                        continue
                    
                    # 检查图片尺寸（豆包API要求：14-3600万像素）
                    try:
                        from PIL import Image
                        with Image.open(image_path) as img:
                            width, height = img.size
                            pixel_count = width * height
                            
                            # 更严格的尺寸检查
                            if pixel_count < 196 or pixel_count > 36000000:
                                print(f"【豆包AI调用】图片尺寸不符合要求跳过: {image_path} ({width}x{height}={pixel_count}像素)")
                                continue
                            if width < 14 or height < 14:
                                print(f"【豆包AI调用】图片尺寸过小跳过: {image_path} ({width}x{height})")
                                continue
                            
                            # 检查图片格式是否真的支持
                            if img.format not in ['JPEG', 'PNG']:
                                print(f"【豆包AI调用】图片格式不支持跳过: {image_path} (格式: {img.format})")
                                continue
                                
                            print(f"【豆包AI调用】图片尺寸检查通过: {image_path} ({width}x{height}={pixel_count}像素, 格式: {img.format})")
                            
                    except ImportError:
                        print("【豆包AI调用】警告: PIL未安装，跳过图片尺寸检查")
                    except Exception as e:
                        print(f"【豆包AI调用】图片尺寸检查失败: {image_path} - {e}")
                        continue
                    
                    # 读取图片并转换为base64
                    with open(image_path, "rb") as image_file:
                        image_bytes = image_file.read()
                        
                        # 验证图片数据完整性
                        if not image_bytes or len(image_bytes) == 0:
                            print(f"【豆包AI调用】图片数据为空跳过: {image_path}")
                            continue
                        
                        # 使用标准base64编码
                        image_data = base64.b64encode(image_bytes).decode('ascii')
                        
                        # 验证base64编码
                        if not image_data or len(image_data) == 0:
                            print(f"【豆包AI调用】base64编码失败跳过: {image_path}")
                            continue
                    
                    # 检查base64数据大小
                    if len(image_data) > 5 * 1024 * 1024:  # 5MB base64限制，减少大小避免问题
                        print(f"【豆包AI调用】图片base64过大跳过: {image_path} ({len(image_data)/1024/1024:.1f}MB)")
                        continue
                    
                    # 获取图片格式，只支持豆包API认可的格式（JPEG和PNG）
                    file_extension = image_path.lower().split('.')[-1]
                    supported_formats = {
                        'jpg': 'jpeg',
                        'jpeg': 'jpeg', 
                        'png': 'png'
                    }
                    
                    if file_extension not in supported_formats:
                        print(f"【豆包AI调用】不支持的图片格式跳过: {image_path} (格式: {file_extension})")
                        continue
                    
                    image_format = supported_formats[file_extension]
                    
                    # 验证base64数据格式
                    try:
                        # 尝试解码base64数据以验证格式正确性
                        base64.b64decode(image_data, validate=True)
                    except Exception as e:
                        print(f"【豆包AI调用】图片base64格式验证失败: {image_path} - {e}")
                        continue
                    
                    # 将图片添加到处理列表
                    # 确保MIME类型格式正确
                    mime_type = f"image/{image_format}"
                    if image_format == "jpeg":
                        mime_type = "image/jpeg"  # 确保使用标准的MIME类型
                    
                    # 尝试不同的图片格式，确保符合豆包API要求
                    # 方法1：标准格式
                    processed_images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    })
                    
                    # 在文本中添加图片引用
                    enhanced_text += f"\n\n[图片{i+1}]: 请分析此图片内容\n"
                    
                    print(f"【豆包AI调用】成功添加图片 {i+1}: {image_path} ({file_size/1024:.1f}KB, 格式: {image_format})")
                    
                except Exception as e:
                    print(f"【豆包AI调用】处理图片失败 {image_path}: {e}")
                    continue
            else:
                print(f"【豆包AI调用】图片文件不存在: {image_path}")
        
        # 如果有多模态内容，返回包含图片的消息格式
        if processed_images:
            print(f"【豆包AI调用】总共添加了 {len(processed_images)} 张图片")
            
            # 使用豆包API支持的多模态格式
            content = [
                {
                    "type": "text",
                    "text": enhanced_text
                }
            ] + processed_images
            
            print(f"【豆包AI调用】多模态内容格式: {len(content)} 个内容块")
            
            # 添加调试信息
            for i, item in enumerate(content):
                if item.get("type") == "image_url":
                    url = item['image_url']['url']
                    print(f"【豆包AI调用】图片 {i+1} URL: {url[:100]}...")
            
            return content
        else:
            # 没有图片，返回纯文本
            print("【豆包AI调用】纯文本内容")
            return enhanced_text