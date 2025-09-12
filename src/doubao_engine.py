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
                    },
                    {
                        "role": "user", 
                        "content": f"请基于以下需求文档生成完整的测试用例：\n\n文档URL: {document_url}\n\n文档内容: {content}\n\n请确保覆盖所有功能点，包括正常流程、边界条件和异常情况。\n\n"
                    }
                ]
                
                # 构建请求数据
                data = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p
                }
                
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
                    print(f"【豆包AI调用】请求失败: {response.status_code}, {response.text}")
                    if attempt < max_retries - 1:
                        print(f"【豆包AI调用】将在{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        return {
                            "success": False,
                            "raw_response": f"AI调用失败: {response.status_code}",
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