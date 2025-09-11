# 主程序入口
# 测试用例生成管道系统的主程序

import sys
import argparse
from pathlib import Path
from loguru import logger

# 添加src目录到Python路径
sys.path.append(str((Path(__file__).parent / "src").resolve()))

from src.config import config_manager
from src.test_case_generator import TestCaseGenerator
from src.api_server import api_server
from src.ai_engine import AIEngineFactory

# 重新加载提示词模版。清除缓存
from src.prompt_engineering import prompt_manager
prompt_manager.load_template_from_file("prompts/mtp_optimized_prompt.txt", "mtp_optimized")

# print("实际被格式化的模板内容：", template.content)
# logger.info("实际被格式化的模板内容：" + template.content)

# 极简合并用例步骤和预期结果为一行
import re
def merge_step_and_expect_final(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f if line.strip()]
    output_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if '用例步骤：' in line:
            if i + 1 < len(lines) and '预期结果：' in lines[i+1]:
                merged = f"{line.strip()}；{lines[i+1].strip()}"
                indent = re.match(r'^(\t*)', line).group(1)
                output_lines.append(f"{indent}{merged}")
                i += 2
                continue
            else:
                output_lines.append(line)
        elif '预期结果：' in line:
            i += 1
            continue
        else:
            output_lines.append(line)
        i += 1
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))


def setup_logging():
    """设置日志配置"""
    config = config_manager.get_config()
    # 创建日志目录
    log_file = Path(config["logging"]["file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    # 配置日志
    logger.remove()  # 移除默认处理器
    logger.add(
        str(log_file),
        level=config["logging"]["level"],
        rotation=config["logging"]["max_size"],
        retention=config["logging"]["backup_count"],
        encoding='utf-8'
    )
    logger.add(
        sys.stdout,
        level=config["logging"]["level"],
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def run_cli():
    """命令行模式"""
    parser = argparse.ArgumentParser(description="测试用例生成管道系统")
    parser.add_argument("--url", help="飞书文档URL")
    parser.add_argument("--content", help="文档内容")
    parser.add_argument("--title", default="测试用例", help="文档标题")
    parser.add_argument("--output", help="输出文件名")
    parser.add_argument("--server", action="store_true", help="启动API服务器")
    parser.add_argument("--ai-provider", choices=["doubao", "deepseek"], 
                       help="选择AI提供商 (doubao/deepseek)")
    args = parser.parse_args()

    if args.server:
        # 启动API服务器
        logger.info("启动API服务器...")
        api_server.run()
    elif args.url:
        # 从URL生成测试用例
        generator = TestCaseGenerator()
        
        # 如果指定了AI提供商，重新创建AI引擎
        if args.ai_provider:
            from src.ai_engine import AIEngineFactory
            generator.ai_engine = AIEngineFactory.create_engine(args.ai_provider)
            logger.info(f"使用AI提供商: {args.ai_provider}")
        
        result = generator.generate_from_url(args.url, args.output)
        if result['success']:
            logger.info(f"测试用例生成成功！AI原始内容已保存: {result['file']}")
            try:
                # 只做合并用例步骤和预期结果为一行
                raw_file_path = result['file']
                final_txt_path = str(raw_file_path).replace('.txt', '_final.txt')
                merge_step_and_expect_final(str(raw_file_path), final_txt_path)
                logger.info(f"最终可导入飞书思维笔记的txt已生成: {final_txt_path}")
            except Exception as e:
                logger.warning(f"自动合并步骤-预期结果失败: {e}")
        else:
            logger.error(f"生成失败: {result.get('error')}")
            sys.exit(1)
    elif args.content:
        # 从内容生成测试用例
        generator = TestCaseGenerator()
        
        # 如果指定了AI提供商，重新创建AI引擎
        if args.ai_provider:
            from src.ai_engine import AIEngineFactory
            generator.ai_engine = AIEngineFactory.create_engine(args.ai_provider)
            logger.info(f"使用AI提供商: {args.ai_provider}")
        
        result = generator.generate_from_content(args.content, args.title, args.output)
        if result['success']:
            logger.info(f"测试用例生成成功！AI原始内容已保存: {result['file']}")
            try:
                # 只做合并用例步骤和预期结果为一行
                raw_file_path = result['file']
                final_txt_path = str(raw_file_path).replace('.txt', '_final.txt')
                merge_step_and_expect_final(str(raw_file_path), final_txt_path)
                logger.info(f"最终可导入飞书思维笔记的txt已生成: {final_txt_path}")
            except Exception as e:
                logger.warning(f"自动合并步骤-预期结果失败: {e}")
        else:
            logger.error(f"生成失败: {result.get('error')}")
            sys.exit(1)
    else:
        parser.print_help()


def run_interactive():
    """交互模式"""
    print("欢迎使用测试用例生成管道系统！")
    print("=" * 50)
    
    # 选择AI提供商
    print("\n请选择AI提供商:")
    print("1. 豆包 (Doubao) - 推荐用于测试用例生成")
    print("2. DeepSeek")
    print("3. 使用默认配置")
    
    choice = input("\n请输入选择 (1-3): ").strip()
    from src.ai_engine import AIEngineFactory
    if choice == "1":
        ai_engine = AIEngineFactory.create_engine("doubao")
        print("✅ 已选择豆包AI引擎")
    elif choice == "2":
        ai_engine = AIEngineFactory.create_engine("deepseek")
        print("✅ 已选择DeepSeek AI引擎")
    elif choice == "3":
        ai_engine = AIEngineFactory.create_engine()
        print("✅ 使用默认AI配置")
    else:
        ai_engine = AIEngineFactory.create_engine()
        print("❌ 无效选择，使用默认配置")
    generator = TestCaseGenerator(ai_engine=ai_engine)
    while True:
        print("\n请选择操作:")
        print("1. 从飞书文档URL生成测试用例")
        print("2. 从文本内容生成测试用例")
        print("3. 切换AI提供商")
        print("4. 退出")
        choice = input("\n请输入选择 (1-4): ").strip()
        if choice == "1":
            url = input("请输入飞书文档URL: ").strip()
            if url:
                print("正在生成测试用例...")
                result = generator.generate_from_url(url)
                if result['success']:
                    print(f"✅ 生成成功！AI原始内容已保存: {result['file']}")
                    try:
                        # 只做合并用例步骤和预期结果为一行
                        raw_file_path = result['file']
                        final_txt_path = str(raw_file_path).replace('.txt', '_final.txt')
                        merge_step_and_expect_final(str(raw_file_path), final_txt_path)
                        print(f"✅ 最终可导入飞书思维笔记的txt已生成: {final_txt_path}")
                    except Exception as e:
                        print(f"❌ 自动合并步骤-预期结果失败: {e}")
                else:
                    print(f"❌ 生成失败: {result.get('error')}")
        elif choice == "2":
            content = input("请输入文档内容: ").strip()
            title = input("请输入文档标题 (默认: 测试用例): ").strip() or "测试用例"
            if content:
                print("正在生成测试用例...")
                result = generator.generate_from_content(content, title)
                if result['success']:
                    print(f"✅ 生成成功！AI原始内容已保存: {result['file']}")
                    try:
                        # 只做合并用例步骤和预期结果为一行
                        raw_file_path = result['file']
                        final_txt_path = str(raw_file_path).replace('.txt', '_final.txt')
                        merge_step_and_expect_final(str(raw_file_path), final_txt_path)
                        print(f"✅ 最终可导入飞书思维笔记的txt已生成: {final_txt_path}")
                    except Exception as e:
                        print(f"❌ 自动合并步骤-预期结果失败: {e}")
                else:
                    print(f"❌ 生成失败: {result.get('error')}")
        elif choice == "3":
            print("\n请选择AI提供商:")
            print("1. 豆包 (Doubao) - 推荐用于测试用例生成")
            print("2. DeepSeek")
            ai_choice = input("请输入选择 (1-2): ").strip()
            if ai_choice == "1":
                ai_engine = AIEngineFactory.create_engine("doubao")
                print("✅ 已切换到豆包AI引擎")
            elif ai_choice == "2":
                ai_engine = AIEngineFactory.create_engine("deepseek")
                print("✅ 已切换到DeepSeek AI引擎")
            else:
                ai_engine = AIEngineFactory.create_engine()
                print("❌ 无效选择，使用默认配置")
            generator = TestCaseGenerator(ai_engine=ai_engine)
        elif choice == "4":
            print("感谢使用！再见！")
            break
        else:
            print("无效选择，请重新输入。")


def main():
    """主函数"""
    try:
        # 设置日志
        setup_logging()
        logger.info("启动测试用例生成管道系统...")
        
        # 显示当前配置的AI提供商
        config = config_manager.get_config()
        default_provider = getattr(config, 'default_ai_provider', 'doubao')
        logger.info(f"默认AI提供商: {default_provider}")
        
        # 检查命令行参数
        if len(sys.argv) > 1:
            run_cli()
        else:
            run_interactive()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 