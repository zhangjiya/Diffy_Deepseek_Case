import time
from pathlib import Path
from document_converter import DocumentConverter
from src.prompt_engineering import prompt_manager
from src.config import config_manager

class TestCaseGenerator:
    def __init__(self, ai_engine=None, user_output_dir=None):
        self.ai_engine = ai_engine
        self.output_dir = config_manager.get_config()["output"]["output_dir"]
        self.user_output_dir = user_output_dir or self.output_dir

    def generate_from_url(self, document_url, output_filename=None, user_id=None, prompt_template_id=None, user_requirements=None):
        converter = DocumentConverter()
        md_path, _ = converter.convert_document_unified(document_url)
        with open(md_path, "r", encoding="utf-8") as f:
            document_content = f.read()
        title = Path(md_path).stem
        
        # 添加调试日志
        print(f"【URL方式】传递的参数:")
        print(f"  - document_url: {document_url}")
        print(f"  - title: {title}")
        print(f"  - user_id: {user_id}")
        print(f"  - prompt_template_id: {prompt_template_id}")
        print(f"  - user_requirements: {user_requirements}")
        
        # 修复参数传递顺序问题
        return self.generate_from_content(
            content=document_content, 
            title=title, 
            output_filename=output_filename, 
            user_id=user_id, 
            prompt_template_id=prompt_template_id,  # 确保这个参数正确传递
            user_requirements=user_requirements     # 确保这个参数正确传递
        )

    def fix_for_mindnote_format(self, raw_text: str, prompt_template_id: str = None) -> str:
        """
        优化：
        - 自动检测模板格式类型，支持分层格式和合并格式
        - 分层格式：预期结果作为用例步骤的子节点
        - 合并格式：自动将"用例步骤：..."和紧随其后的"预期结果：..."合并为一行
        - 一级节点无缩进，二级节点1个Tab，三级节点2个Tab
        - 移除多余空行和所有markdown符号
        """
        import re
        
        # 检测模板是否使用分层格式
        use_hierarchical_format = self._is_hierarchical_template(prompt_template_id)
        
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        fixed = []
        i = 0
        while i < len(lines):
            l = lines[i]
            # 一级节点（无缩进）
            if l.startswith('#'):
                l = l.lstrip('#').strip()
                fixed.append(l)
                i += 1
                continue
            # 二级节点
            if l.startswith('##'):
                l = l.lstrip('#').strip()
                fixed.append('\t' + l)
                i += 1
                continue
            # 三级节点
            if l.startswith('###'):
                l = l.lstrip('#').strip()
                fixed.append('\t\t' + l)
                i += 1
                continue
            # 测试点（通常为二级节点）
            if re.match(r'^(测试点|Test Point|验证点|检查点)', l):
                fixed.append('\t' + l)
                i += 1
                continue
            # 处理"用例步骤"与"预期结果"
            if re.match(r'^(用例步骤|步骤|Step)', l):
                if use_hierarchical_format:
                    # 分层格式：预期结果作为用例步骤的子节点
                    fixed.append('\t\t' + l)
                    i += 1
                    # 处理后续的预期结果作为子节点
                    while i < len(lines) and re.match(r'^(预期结果|期望|Expected)', lines[i]):
                        fixed.append('\t\t\t' + lines[i])
                        i += 1
                    continue
                else:
                    # 合并格式：合并"用例步骤"与"预期结果"为一行
                    merged = l
                    # 检查下一行是否为预期结果
                    if i+1 < len(lines) and re.match(r'^(预期结果|期望|Expected)', lines[i+1]):
                        merged += '；' + lines[i+1]
                        i += 1
                    fixed.append('\t\t' + merged)
                    i += 1
                    continue
            # 直接是"预期结果"但前面没有步骤，单独处理
            if re.match(r'^(预期结果|期望|Expected)', l):
                if use_hierarchical_format:
                    # 分层格式：预期结果作为独立节点
                    fixed.append('\t\t\t' + l)
                else:
                    # 合并格式：预期结果作为二级节点
                    fixed.append('\t\t' + l)
                i += 1
                continue
            # 数字编号的步骤
            if re.match(r'^[0-9]+[\.|、|．|\)]', l):
                # 检查下一行是否为预期结果
                merged = l
                if i+1 < len(lines) and re.match(r'^(预期结果|期望|Expected)', lines[i+1]):
                    merged += '；' + lines[i+1]
                    i += 1
                fixed.append('\t\t' + merged)
                i += 1
                continue
            # markdown无序/有序列表
            if l.startswith('- '):
                fixed.append('\t\t' + l[2:])
                i += 1
                continue
            if re.match(r'^[0-9]+\. ', l):
                fixed.append('\t\t' + l)
                i += 1
                continue
            # 一级节点（无缩进，如"活动入口"）
            if re.match(r'^[\u4e00-\u9fa5A-Za-z0-9]+$', l):
                fixed.append(l)
                i += 1
                continue
            # 其他行
            fixed.append(l)
            i += 1
        return '\n'.join(fixed) + '\n'

    def _is_hierarchical_template(self, prompt_template_id: str) -> bool:
        """
        检测模板是否使用分层格式
        通过检查模板内容中是否包含分层格式的关键词来判断
        """
        if not prompt_template_id:
            return False
        
        try:
            from src.prompt_engineering import prompt_manager
            template_content = prompt_manager.get_template_by_id(prompt_template_id)
            
            # 检查模板内容中是否包含分层格式的关键词
            hierarchical_keywords = [
                "预期结果作为用例步骤的子节点",
                "预期结果：<结果1>",
                "预期结果：<结果2>",
                "每个用例步骤和预期结果分别占一行",
                "预期结果作为用例步骤的子节点"
            ]
            
            # 如果模板内容包含任何一个分层格式关键词，则认为是分层格式
            for keyword in hierarchical_keywords:
                if keyword in template_content:
                    return True
            
            return False
        except Exception as e:
            print(f"检测模板格式时出错: {e}")
            return False

    def generate_from_content(self, content, title="测试用例", output_filename=None, user_id=None, generate_mindnote=None, prompt_template_id=None, user_requirements=None):
        # 如果未指定generate_mindnote参数，从配置文件读取
        if generate_mindnote is None:
            generate_mindnote = config_manager.get_config()["output"].get("generate_mindnote", True)
        if not self.ai_engine:
            raise ValueError("AI引擎未初始化")
        
        # 添加调试日志
        print(f"【Content方式】接收到的参数:")
        print(f"  - content长度: {len(content)}")
        print(f"  - title: {title}")
        print(f"  - user_id: {user_id}")
        print(f"  - prompt_template_id: {prompt_template_id}")
        print(f"  - user_requirements: {user_requirements}")
        
        # 统一处理提示词格式化
        print("当前使用的提示词是什么",prompt_template_id,user_requirements)
        formatted_prompt = self._format_prompt(content, title, prompt_template_id, user_requirements)
        result = self.ai_engine.generate_test_cases(formatted_prompt, title)
        raw_response = result.get("raw_response", "")
        
        # 生成包含文档标题的文件名
        if not output_filename:
            # 清理标题中的特殊字符，确保文件名安全
            safe_title = self._sanitize_filename(title)
            timestamp = int(time.time())
            
            # 添加用户ID到文件名中，确保唯一性
            user_suffix = f"_{user_id[:8]}" if user_id else ""
            
            # 根据AI引擎类型添加不同的标注
            if hasattr(self.ai_engine, 'key_name'):
                if self.ai_engine.key_name == "DeepSeek":
                    output_filename = f"{safe_title}_test_cases_{timestamp}{user_suffix}_deepseek.txt"
                else:
                    output_filename = f"{safe_title}_test_cases_{timestamp}{user_suffix}_ai.txt"
            else:
                output_filename = f"{safe_title}_test_cases_{timestamp}{user_suffix}_ai.txt"
        
        # 使用用户专属输出目录
        output_path = Path(self.user_output_dir) / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(raw_response)
        
        # 根据配置决定是否生成MindNote格式文件
        mindnote_file = None
        if generate_mindnote:
            mindnote_filename = output_filename.replace('.txt', '_mindnote.txt')
            mindnote_path = Path(self.user_output_dir) / mindnote_filename
            mindnote_content = self.fix_for_mindnote_format(raw_response, prompt_template_id)
            with open(mindnote_path, "w", encoding="utf-8") as f:
                f.write(mindnote_content)
            mindnote_file = str(mindnote_path)
        
        return {
            "success": True,
            "file": str(output_path),
            "mindnote_file": mindnote_file,
            "raw_response": raw_response,
            "key_name": result.get("key_name", "")
        }

    def _format_prompt(self, content, title, prompt_template_id=None, user_requirements=None):
        """统一处理提示词格式化，支持模板选择和自定义要求"""
        try:
            if prompt_template_id:
                # 使用指定的提示词模板
                print(f"正在加载指定的提示词模板: {prompt_template_id}")
                template = prompt_manager.get_template_by_id(prompt_template_id)
                print(f"✅ 成功加载模板: {prompt_template_id}, 长度: {len(template)} 字符")
                if "逻辑查缺补漏" in template:
                    print("✅ 确认模板包含'逻辑查缺补漏'功能")
                else:
                    print("⚠️ 模板不包含'逻辑查缺补漏'功能")
            else:
                # 使用默认提示词模板
                print("使用默认提示词模板")
                template = prompt_manager.get_default_template()
            
            formatted = prompt_manager.format_prompt(template, content, title, user_requirements)
            print(f"✅ 提示词格式化完成，长度: {len(formatted)} 字符")
            return formatted
            
        except Exception as e:
            print(f"❌ 提示词格式化失败: {e}")
            print(f"尝试加载的模板ID: {prompt_template_id}")
            # 回退到默认模板
            try:
                fallback_template = prompt_manager.get_default_template()
                formatted = prompt_manager.format_prompt(fallback_template, content, title, user_requirements)
                print(f"✅ 回退到默认模板成功，长度: {len(formatted)} 字符")
                return formatted
            except Exception as fallback_error:
                print(f"❌ 回退到默认模板也失败: {fallback_error}")
                # 最后的回退方案
                return f"请基于以下需求文档生成测试用例：\n\n文档标题: {title}\n\n文档内容: {content}\n\n用户要求: {user_requirements or '无特殊要求'}"

    def _sanitize_filename(self, filename):
        """清理文件名，移除或替换不安全的字符"""
        import re
        # 移除或替换文件名中的不安全字符
        # 保留中文字符、英文字母、数字、下划线、连字符
        safe_filename = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_-]', '_', filename)
        # 移除多余的下划线
        safe_filename = re.sub(r'_+', '_', safe_filename)
        # 移除开头和结尾的下划线
        safe_filename = safe_filename.strip('_')
        # 限制文件名长度
        if len(safe_filename) > 50:
            safe_filename = safe_filename[:50]
        return safe_filename