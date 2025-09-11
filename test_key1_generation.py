#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.doubao_engine import DoubaoEngine

def test_key1_generation():
    """测试账号1的case生成"""
    print("🚀 开始测试账号1生成测试用例...")
    
    # 使用账号1
    engine = DoubaoEngine(key_id="key1")
    
    # 简单的测试内容
    content = "登陆系统"
    
    print(f"📋 测试参数:")
    print(f"  - 密钥: {engine.key_name}({engine.key_id})")
    print(f"  - 模型: {engine.model}")
    print(f"  - 内容: {content}")
    
    # 生成测试用例
    result = engine.generate_test_cases(
        content=content,
        document_url="",
        document_title="登陆系统测试",
        user_requirements=""
    )
    
    print(f"\n📄 生成结果:")
    print("=" * 50)
    print(result)
    print("=" * 50)
    
    if result and "AI调用" not in result:
        print("✅ 测试成功！生成了测试用例")
        return True
    else:
        print("❌ 测试失败！")
        return False

if __name__ == "__main__":
    test_key1_generation()
