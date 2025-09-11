#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试DeepSeek API连接和功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.deepseek_engine import DeepSeekEngine

def test_deepseek_connection():
    """测试DeepSeek API连接"""
    try:
        print("🔍 正在测试DeepSeek API连接...")
        
        # 创建DeepSeek引擎
        engine = DeepSeekEngine()
        
        print(f"✅ DeepSeek引擎创建成功")
        print(f"   - API Key: {engine.api_key[:10]}...")
        print(f"   - Base URL: {engine.base_url}")
        print(f"   - Model: {engine.model}")
        print(f"   - Max Tokens: {engine.max_tokens}")
        print(f"   - Temperature: {engine.temperature}")
        print(f"   - Top P: {engine.top_p}")
        
        # 测试简单请求
        test_content = "请生成一个简单的登录功能测试用例"
        print(f"\n🧪 正在测试API调用...")
        print(f"   测试内容: {test_content}")
        
        result = engine.generate_test_cases(test_content, "登录功能测试")
        
        if result["success"]:
            print("✅ DeepSeek API调用成功！")
            print(f"   响应内容长度: {len(result['raw_response'])} 字符")
            print(f"   响应内容前200字符: {result['raw_response'][:200]}...")
            print(f"   文件名: {result['file']}")
            print(f"   密钥名称: {result['key_name']}")
        else:
            print("❌ DeepSeek API调用失败！")
            print(f"   错误信息: {result.get('error', '未知错误')}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deepseek_vs_doubao():
    """测试DeepSeek和豆包的区别"""
    try:
        print("\n🔄 正在测试DeepSeek和豆包的区别...")
        
        from src.doubao_engine import DoubaoEngine
        
        # 创建两个引擎
        deepseek_engine = DeepSeekEngine()
        doubao_engine = DoubaoEngine()
        
        print("✅ 两个引擎创建成功")
        print(f"   DeepSeek: {deepseek_engine.key_name}")
        print(f"   豆包: {doubao_engine.key_name}")
        
        # 测试相同的提示词
        test_content = "请生成一个用户注册功能的测试用例，包括正常流程和异常情况"
        
        print(f"\n🧪 使用相同提示词测试两个引擎...")
        print(f"   测试内容: {test_content}")
        
        # 测试DeepSeek
        print("\n📡 测试DeepSeek...")
        deepseek_result = deepseek_engine.generate_test_cases(test_content, "用户注册功能测试")
        
        # 测试豆包
        print("\n📡 测试豆包...")
        doubao_result = doubao_engine.generate_test_cases(test_content, "用户注册功能测试")
        
        # 比较结果
        print("\n📊 测试结果比较:")
        print(f"   DeepSeek: {'✅ 成功' if deepseek_result['success'] else '❌ 失败'}")
        print(f"   豆包: {'✅ 成功' if doubao_result['success'] else '❌ 失败'}")
        
        if deepseek_result['success'] and doubao_result['success']:
            print(f"   DeepSeek响应长度: {len(deepseek_result['raw_response'])} 字符")
            print(f"   豆包响应长度: {len(doubao_result['raw_response'])} 字符")
            
            # 检查文件名标注
            print(f"   DeepSeek文件名: {deepseek_result['file']}")
            print(f"   豆包文件名: {doubao_result['file']}")
            
        return True
        
    except Exception as e:
        print(f"❌ 比较测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试DeepSeek API功能...\n")
    
    # 测试连接
    if test_deepseek_connection():
        print("\n✅ DeepSeek API连接测试通过！")
    else:
        print("\n❌ DeepSeek API调用失败！")
        sys.exit(1)
    
    # 测试与豆包的区别
    if test_deepseek_vs_doubao():
        print("\n✅ DeepSeek与豆包对比测试通过！")
    else:
        print("\n❌ DeepSeek与豆包对比测试失败！")
        sys.exit(1)
    
    print("\n🎉 所有测试完成！DeepSeek API功能正常！")
