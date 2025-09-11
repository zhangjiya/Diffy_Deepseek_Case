#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import config_manager

def test_config():
    """测试配置获取"""
    print("🔍 测试配置获取...")
    
    try:
        # 测试获取豆包密钥配置
        key1_config = config_manager.get_doubao_key_config("key1")
        print(f"✅ key1配置: {type(key1_config)} - {key1_config}")
        
        key2_config = config_manager.get_doubao_key_config("key2")
        print(f"✅ key2配置: {type(key2_config)} - {key2_config}")
        
        # 测试默认密钥
        default_config = config_manager.get_doubao_key_config()
        print(f"✅ 默认配置: {type(default_config)} - {default_config}")
        
        # 测试不存在的密钥
        try:
            invalid_config = config_manager.get_doubao_key_config("invalid_key")
            print(f"❌ 无效密钥应该抛出异常: {invalid_config}")
        except ValueError as e:
            print(f"✅ 无效密钥正确抛出异常: {e}")
            
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_config()
