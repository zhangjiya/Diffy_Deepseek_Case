# 配置管理模块
# 负责加载和管理系统配置

import yaml
from pathlib import Path
import os

class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self._config = None

    def get_config(self):
        if self._config is None:
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            with open(config_file, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        return self._config
    
    def reload_config(self):
        """重新加载配置文件"""
        self._config = None
        return self.get_config()
    
    def get_doubao_key_config(self, key_id=None):
        """获取豆包密钥配置"""
        config = self.get_config()
        doubao_config = config.get("doubao", {})
        
        if key_id is None:
            key_id = doubao_config.get("default_key", "key1")
        
        keys = doubao_config.get("keys", {})
        if key_id not in keys:
            raise ValueError(f"豆包密钥配置不存在: {key_id}")
        
        return keys[key_id]
    
    def get_deepseek_config(self):
        """获取DeepSeek配置"""
        config = self.get_config()
        deepseek_config = config.get("deepseek", {})
        if not deepseek_config:
            raise ValueError("DeepSeek配置不存在")
        return deepseek_config
    
    def get_available_doubao_keys(self):
        """获取所有可用的豆包密钥列表"""
        config = self.get_config()
        doubao_config = config.get("doubao", {})
        keys = doubao_config.get("keys", {})
        
        available_keys = []
        for key_id, key_config in keys.items():
            available_keys.append({
                "id": key_id,
                "name": key_config.get("name", f"密钥{key_id}"),
                "model": key_config.get("model", ""),
                "temperature": key_config.get("temperature", 0.3),
                "top_p": key_config.get("top_p", 0.6)
            })
        
        return available_keys
    
    def get_prompt_templates(self):
        """获取所有可用的提示词模板"""
        config = self.get_config()
        prompts_config = config.get("prompts", {})
        return prompts_config.get("available_templates", [])
    
    def get_default_prompt_template(self):
        """获取默认提示词模板"""
        config = self.get_config()
        prompts_config = config.get("prompts", {})
        return prompts_config.get("default_template", "mtp_optimized_prompt.txt")
    
    def add_custom_prompt_template(self, template_id, name, description, file_path):
        """添加自定义提示词模板"""
        config = self.get_config()
        prompts_config = config.get("prompts", {})
        
        # 检查模板是否已存在
        existing_templates = prompts_config.get("available_templates", [])
        for template in existing_templates:
            if template.get("id") == template_id:
                # 更新现有模板
                template.update({
                    "name": name,
                    "description": description,
                    "file": file_path
                })
                break
        else:
            # 添加新模板
            new_template = {
                "id": template_id,
                "name": name,
                "description": description,
                "file": file_path
            }
            existing_templates.append(new_template)
        
        # 保存到配置文件
        self._save_config(config)
        return True
    
    def _save_config(self, config):
        """保存配置到文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

config_manager = ConfigManager()

# 并发控制配置
concurrency_config = {
    "max_concurrent_requests": 3,  # 最大并发请求数
    "request_timeout": 1800,  # 请求超时时间（秒）
    "cleanup_interval": 1800,  # 清理过期请求的间隔（秒）
    "session_timeout": 3600,  # 会话超时时间（秒）
} 