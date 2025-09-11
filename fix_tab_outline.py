import re
import sys

def fix_to_tab_outline(input_path, output_path=None):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    fixed_lines = []
    last_step_indent = None
    for line in lines:
        # 去除前缀符号和多余空格
        line = re.sub(r'^[\-\*\d\.\s]+', '', line)
        # 只保留行首Tab，去掉所有空格
        line = re.sub(r'^(\t*) *', lambda m: m.group(1), line)
        # 判断是否为“用例步骤”或“预期结果”
        if '用例步骤：' in line:
            last_step_indent = len(line) - len(line.lstrip('\t'))
            fixed_lines.append(line.strip())
        elif '预期结果：' in line and last_step_indent is not None:
            indent = '\t' * (last_step_indent + 1)
            fixed_lines.append(f"{indent}{line.strip()}")
        else:
            fixed_lines.append(line.strip())
    with open(output_path or input_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    print(f'已严格修正Tab缩进和分层，输出文件: {output_path or input_path}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python fix_tab_outline.py <输入文件> [输出文件]')
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    fix_to_tab_outline(input_path, output_path) 