#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_web_api():
    """测试web API"""
    print("🚀 测试web API...")
    
    # 测试数据
    data = {
        "ai_provider": "doubao",
        "key_id": "key1",
        "model": "doubao-1-5-thinking-pro-250415",
        "document_content": "登陆系统",
        "document_title": "登陆系统测试",
        "prompt_template_id": "mtp_optimized_prompt",
        "user_requirements": ""
    }
    
    print(f"📤 发送请求到: http://localhost:5002/api/generate")
    print(f"📋 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            "http://localhost:5002/api/generate",
            json=data,
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ API调用成功！")
                return True
            else:
                print(f"❌ API调用失败: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

if __name__ == "__main__":
    test_web_api()
