import os
from pathlib import Path
from src.config import config_manager

class PromptManager:
    def __init__(self):
        self._templates_cache = {}
        self._last_modified = {}
    
    def load_template_from_file(self, file_path, template_name=None):
        """从文件加载提示词模板，支持缓存和自动重载"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"提示词模板文件不存在: {file_path}")
        
        # 检查文件是否被修改
        current_mtime = os.path.getmtime(file_path)
        if (file_path in self._templates_cache and 
            file_path in self._last_modified and 
            current_mtime <= self._last_modified[file_path]):
            # 使用缓存
            return self._templates_cache[file_path]
        
        # 重新加载文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._templates_cache[file_path] = content
                self._last_modified[file_path] = current_mtime
                return content
        except Exception as e:
            raise Exception(f"加载提示词模板失败 {file_path}: {e}")
    
    def get_template_by_id(self, template_id):
        """根据模板ID获取提示词模板"""
        print(f"🔍 正在查找模板ID: {template_id}")
        templates = config_manager.get_prompt_templates()
        print(f"📋 可用模板列表: {[t.get('id') for t in templates]}")
        
        for template in templates:
            print(f"  - 检查模板: {template.get('id')} vs {template_id}")
            if template.get("id") == template_id:
                file_path = template.get("file")
                print(f"✅ 找到匹配模板，文件路径: {file_path}")
                if file_path and os.path.exists(file_path):
                    print(f"✅ 文件存在，开始加载...")
                    return self.load_template_from_file(file_path)
                else:
                    print(f"❌ 文件不存在或路径无效: {file_path}")
                break
        
        print(f"❌ 未找到匹配的模板ID: {template_id}")
        raise ValueError(f"提示词模板不存在或文件丢失: {template_id}")
    
    def get_default_template(self):
        """获取默认提示词模板"""
        default_id = config_manager.get_default_prompt_template()
        return self.get_template_by_id(default_id)
    
    def format_prompt(self, template, content, title, user_requirements=None):
        """格式化提示词，支持用户自定义要求"""
        formatted = template.replace("{content}", content).replace("{title}", title)
        
        if user_requirements:
            formatted = formatted.replace("{user_requirements}", user_requirements)
        
        return formatted
    
    def create_custom_template(self, template_id, name, description, content):
        """创建自定义提示词模板"""
        # 创建prompts目录（如果不存在）
        prompts_dir = Path("prompts")
        prompts_dir.mkdir(exist_ok=True)
        
        # 生成文件路径
        file_path = prompts_dir / f"{template_id}.txt"
        
        # 写入模板内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 添加到配置
        config_manager.add_custom_prompt_template(
            template_id, name, description, str(file_path)
        )
        
        # 清除缓存
        if str(file_path) in self._templates_cache:
            del self._templates_cache[str(file_path)]
        
        return str(file_path)
    
    def get_available_templates(self):
        """获取所有可用的提示词模板信息"""
        return config_manager.get_prompt_templates()
    
    def reload_all_templates(self):
        """重新加载所有提示词模板"""
        self._templates_cache.clear()
        self._last_modified.clear()
        return True

prompt_manager = PromptManager() 