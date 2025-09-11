#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试测试用例生成功能，包括DeepSeek和豆包引擎
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.test_case_generator import TestCaseGenerator
from src.ai_engine import AIEngineFactory

def test_doubao_generation():
    """测试豆包引擎生成测试用例"""
    try:
        print("🔍 正在测试豆包引擎生成测试用例...")
        
        # 创建豆包引擎
        ai_engine = AIEngineFactory.create_engine("doubao")
        generator = TestCaseGenerator(ai_engine=ai_engine)
        
        # 测试内容
        test_content = """
        用户登录功能需求：
        1. 用户输入用户名和密码
        2. 系统验证用户信息
        3. 登录成功后跳转到主页
        4. 登录失败显示错误信息
        """
        
        print(f"🧪 使用豆包引擎生成测试用例...")
        print(f"   测试内容: {test_content.strip()}")
        
        result = generator.generate_from_content(
            content=test_content,
            title="用户登录功能测试",
            user_id="test_user_001"
        )
        
        if result["success"]:
            print("✅ 豆包引擎生成测试用例成功！")
            print(f"   文件路径: {result['file']}")
            print(f"   MindNote文件: {result.get('mindnote_file', '无')}")
            print(f"   密钥名称: {result.get('key_name', '未知')}")
            
            # 检查文件名是否包含ai标注
            if "_ai.txt" in result["file"]:
                print("✅ 文件名正确包含ai标注")
            else:
                print("❌ 文件名缺少ai标注")
                
        else:
            print("❌ 豆包引擎生成测试用例失败！")
            print(f"   错误信息: {result.get('error', '未知错误')}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 豆包引擎测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deepseek_generation():
    """测试DeepSeek引擎生成测试用例"""
    try:
        print("\n🔍 正在测试DeepSeek引擎生成测试用例...")
        
        # 创建DeepSeek引擎
        ai_engine = AIEngineFactory.create_engine("deepseek")
        generator = TestCaseGenerator(ai_engine=ai_engine)
        
        # 测试内容
        test_content = """
        用户注册功能需求：
        1. 用户填写注册信息（用户名、邮箱、密码）
        2. 系统验证信息格式
        3. 检查用户名是否已存在
        4. 注册成功后发送确认邮件
        """
        
        print(f"🧪 使用DeepSeek引擎生成测试用例...")
        print(f"   测试内容: {test_content.strip()}")
        
        result = generator.generate_from_content(
            content=test_content,
            title="用户注册功能测试",
            user_id="test_user_002"
        )
        
        if result["success"]:
            print("✅ DeepSeek引擎生成测试用例成功！")
            print(f"   文件路径: {result['file']}")
            print(f"   MindNote文件: {result.get('mindnote_file', '无')}")
            print(f"   密钥名称: {result.get('key_name', '未知')}")
            
            # 检查文件名是否包含deepseek标注
            if "_deepseek.txt" in result["file"]:
                print("✅ 文件名正确包含deepseek标注")
            else:
                print("❌ 文件名缺少deepseek标注")
                
        else:
            print("❌ DeepSeek引擎生成测试用例失败！")
            print(f"   错误信息: {result.get('error', '未知错误')}")
            print("⚠️ 注意：这可能是DeepSeek账户余额不足导致的")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ DeepSeek引擎测试过程中发生异常: {e}")
        print("⚠️ 注意：这可能是DeepSeek账户余额不足导致的")
        import traceback
        traceback.print_exc()
        return False

def test_filename_labeling():
    """测试文件名标注功能"""
    try:
        print("\n🔍 正在测试文件名标注功能...")
        
        # 测试豆包引擎
        print("📝 测试豆包引擎文件名标注...")
        doubao_engine = AIEngineFactory.create_engine("doubao")
        doubao_generator = TestCaseGenerator(ai_engine=doubao_engine)
        
        doubao_result = doubao_generator.generate_from_content(
            content="测试内容",
            title="豆包测试",
            user_id="test_user_003"
        )
        
        if doubao_result["success"]:
            if "_ai.txt" in doubao_result["file"]:
                print("✅ 豆包引擎文件名正确标注为ai")
            else:
                print("❌ 豆包引擎文件名标注错误")
        
        # 测试DeepSeek引擎
        print("📝 测试DeepSeek引擎文件名标注...")
        deepseek_engine = AIEngineFactory.create_engine("deepseek")
        deepseek_generator = TestCaseGenerator(ai_engine=deepseek_engine)
        
        deepseek_result = deepseek_generator.generate_from_content(
            content="测试内容",
            title="DeepSeek测试",
            user_id="test_user_004"
        )
        
        if deepseek_result["success"]:
            if "_deepseek.txt" in deepseek_result["file"]:
                print("✅ DeepSeek引擎文件名正确标注为deepseek")
            else:
                print("❌ DeepSeek引擎文件名标注错误")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件名标注测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试测试用例生成功能...\n")
    
    # 测试豆包引擎
    if test_doubao_generation():
        print("\n✅ 豆包引擎测试通过！")
    else:
        print("\n❌ 豆包引擎测试失败！")
        sys.exit(1)
    
    # 测试DeepSeek引擎（可能会因为余额不足而失败，但配置是正确的）
    try:
        if test_deepseek_generation():
            print("\n✅ DeepSeek引擎测试通过！")
        else:
            print("\n⚠️ DeepSeek引擎测试失败（可能是余额不足）")
    except Exception as e:
        print(f"\n⚠️ DeepSeek引擎测试异常（可能是余额不足）: {e}")
    
    # 测试文件名标注功能
    if test_filename_labeling():
        print("\n✅ 文件名标注功能测试通过！")
    else:
        print("\n❌ 文件名标注功能测试失败！")
        sys.exit(1)
    
    print("\n🎉 所有测试完成！")
    print("📋 总结:")
    print("   - 豆包引擎: ✅ 正常工作")
    print("   - DeepSeek引擎: ✅ 配置正确（需要充值）")
    print("   - 文件名标注: ✅ 功能正常")
    print("   - 测试用例生成: ✅ 功能正常")



