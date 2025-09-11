from src.doubao_engine import DoubaoEngine
from src.deepseek_engine import DeepSeekEngine

class DummyAIEngine:
    def generate_test_cases(self, content, title="测试用例", prompt_template=None):
        # 模拟AI生成测试用例内容
        example = (
            f"{title}\n"
            "\t测试点：示例测试点\n"
            "\t\t用例步骤：输入用户名；预期结果：显示欢迎页面\n"
            "\t\t用例步骤：输入错误密码；预期结果：提示密码错误"
        )
        return {
            "success": True,
            "raw_response": example,
            "file": "dummy.txt"
        }

class AIEngineFactory:
    @staticmethod
    def create_engine(provider=None, model=None, temperature=None, top_p=None, key_id=None):
        if provider == "doubao":
            return DoubaoEngine(
                key_id=key_id,
                model=model, 
                temperature=temperature, 
                top_p=top_p
            )
        elif provider == "deepseek":
            return DeepSeekEngine(
                key_id=key_id,
                model=model, 
                temperature=temperature, 
                top_p=top_p
            )
        # 可扩展其他引擎
        return DummyAIEngine() 