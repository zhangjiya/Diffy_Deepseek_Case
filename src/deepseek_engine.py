import requests
import base64
import os
from pathlib import Path
from src.config import config_manager

class DeepSeekEngine:
    def __init__(self, key_id=None, model=None, temperature=None, top_p=None):
        # 获取deepseek配置
        config = config_manager.get_config()
        deepseek_config = config.get("deepseek", {})
        
        self.api_key = deepseek_config["api_key"]
        self.base_url = deepseek_config["base_url"]
        self.model = model or deepseek_config["model"]
        self.max_tokens = deepseek_config.get("max_tokens", 4000)
        self.temperature = temperature if temperature is not None else deepseek_config.get("temperature", 0.7)
        self.top_p = top_p if top_p is not None else 0.9  # deepseek默认top_p
        self.key_name = "DeepSeek"

    def generate_test_cases(self, content, title="测试用例", prompt_template=None):
        """生成测试用例"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专业的AI测试工程师，专门负责生成高质量的测试用例。"},
            {"role": "user", "content": content}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p
        }
        
        try:
            print(f"【DeepSeek AI调用】模型: {self.model}, 温度: {self.temperature}, Top_p: {self.top_p}")
            print("【DeepSeek AI调用】Prompt内容前500：", content[:500])
            
            resp = requests.post(self.base_url, headers=headers, json=data, timeout=1800)
            print("【DeepSeek AI调用】响应状态码：", resp.status_code)
            print("【DeepSeek AI调用】响应内容：", resp.text)
            
            resp.raise_for_status()
            result = resp.json()
            ai_content = result["choices"][0]["message"]["content"]
            
            return {
                "success": True,
                "raw_response": ai_content,
                "file": "deepseek_ai.txt",
                "key_name": self.key_name
            }
        except Exception as e:
            print("【DeepSeek AI调用】异常：", e)
            return {
                "success": False,
                "error": str(e),
                "raw_response": "",
                "key_name": self.key_name
            }
