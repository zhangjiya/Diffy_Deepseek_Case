#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_key2_generation():
    """测试使用账号2生成测试用例"""
    
    # 测试参数
    url = "http://localhost:5002/api/generate"
    
    data = {
        "ai_provider": "doubao",
        "model": "doubao-1-5-thinking-vision-pro-250428",
        "key_id": "key2",
        "prompt_template_id": "mtp_optimized_prompt",
        "user_requirements": "",
        "document_url": "https://aviagames.feishu.cn/docx/OVdydADCLoy6CCx54mpcqSrDnsI?from=from_copylink",
        "document_content": None
    }
    
    print("🚀 开始测试账号2生成测试用例...")
    print(f"📋 测试参数:")
    print(f"  - AI提供商: {data['ai_provider']}")
    print(f"  - 模型: {data['model']}")
    print(f"  - 密钥ID: {data['key_id']}")
    print(f"  - 提示词模板: {data['prompt_template_id']}")
    print(f"  - 文档URL: {data['document_url']}")
    print()
    
    try:
        print("📤 发送请求...")
        response = requests.post(url, json=data, timeout=300)
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功!")
            print(f"📄 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print("❌ 请求失败!")
            print(f"📄 错误内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_key2_generation()
