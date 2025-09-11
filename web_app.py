#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例生成Web平台
提供Web界面来生成测试用例
"""

import sys
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, session
import time
import json
import uuid
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import queue

# 添加src目录到Python路径
sys.path.append(str((Path(__file__).parent / "src").resolve()))

from src.config import config_manager
from src.test_case_generator import TestCaseGenerator
from src.ai_engine import AIEngineFactory

app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 并发控制
request_semaphore = threading.Semaphore(3)  # 最多同时处理3个请求
processing_requests = {}  # 记录正在处理的请求
processing_lock = Lock()  # 保护processing_requests的锁
request_queue = queue.Queue()  # 请求队列

def get_user_session_id():
    """获取或创建用户会话ID"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

def get_content_hash(content):
    """计算内容哈希值，用于请求去重"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

def is_request_processing(user_id, content_hash):
    """检查请求是否正在处理中"""
    with processing_lock:
        key = f"{user_id}_{content_hash}"
        return key in processing_requests

def mark_request_processing(user_id, content_hash, status=True):
    """标记请求处理状态"""
    with processing_lock:
        key = f"{user_id}_{content_hash}"
        if status:
            processing_requests[key] = time.time()
        else:
            processing_requests.pop(key, None)

def cleanup_expired_requests():
    """清理过期的请求记录（超过30分钟）"""
    current_time = time.time()
    with processing_lock:
        expired_keys = [
            key for key, timestamp in processing_requests.items()
            if current_time - timestamp > 1800  # 30分钟
        ]
        for key in expired_keys:
            processing_requests.pop(key, None)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_test_cases():
    """生成测试用例的API接口"""
    # 获取用户会话ID
    user_id = get_user_session_id()
    
    try:
        data = request.get_json()
        
        # 获取参数
        ai_provider = data.get('ai_provider', 'doubao')
        model = data.get('model', None)
        temperature = data.get('temperature', None)
        top_p = data.get('top_p', None)
        key_id = data.get('key_id', None) or data.get('doubao_key', None)  # 新增：豆包密钥ID，兼容两种字段名
        prompt_template_id = data.get('prompt_template_id', None)  # 新增：提示词模板ID
        user_requirements = data.get('user_requirements', None)  # 新增：用户自定义要求
        document_url = data.get('document_url', '') or ''
        document_content = data.get('document_content', '') or ''
        document_title = data.get('document_title', '测试用例') or '测试用例'
        
        # 安全地调用strip()
        document_url = document_url.strip() if document_url else ''
        document_content = document_content.strip() if document_content else ''
        document_title = document_title.strip() if document_title else '测试用例'
        
        # 添加调试日志
        print(f"【调试】接收到的参数:")
        print(f"  - ai_provider: {ai_provider}")
        print(f"  - model: {model}")
        print(f"  - key_id: {key_id}")
        print(f"  - prompt_template_id: {prompt_template_id}")
        print(f"  - user_requirements: {user_requirements}")
        print(f"  - document_url: {document_url[:100] if document_url else 'None'}")
        print(f"  - document_content: {document_content[:100] if document_content else 'None'}")
        
        # 验证输入
        if not document_url and not document_content:
            return jsonify({
                'success': False,
                'error': '请提供文档URL或文档内容'
            }), 400
        
        # 计算内容哈希值
        content_for_hash = document_url if document_url else document_content
        content_hash = get_content_hash(content_for_hash)
        
        # 检查是否正在处理相同请求
        if is_request_processing(user_id, content_hash):
            return jsonify({
                'success': False,
                'error': '相同内容的请求正在处理中，请稍后再试'
            }), 429
        
        # 标记请求开始处理
        mark_request_processing(user_id, content_hash, True)
        
        try:
            # 使用信号量控制并发
            with request_semaphore:
                # 清理过期请求
                cleanup_expired_requests()
                
                # 创建AI引擎
                ai_engine = AIEngineFactory.create_engine(
                    provider=ai_provider,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    key_id=key_id  # 传递密钥ID
                )
                
                # 使用全局输出目录，不进行用户会话隔离
                output_dir = config_manager.get_config()["output"]["output_dir"]
                global_output_dir = Path(output_dir)
                global_output_dir.mkdir(parents=True, exist_ok=True)
                
                # 创建生成器，使用全局输出目录
                generator = TestCaseGenerator(ai_engine=ai_engine, user_output_dir=str(global_output_dir))
                
                # 生成测试用例
                if document_url:
                    result = generator.generate_from_url(
                        document_url, 
                        user_id=user_id,
                        prompt_template_id=prompt_template_id,
                        user_requirements=user_requirements
                    )
                else:
                    result = generator.generate_from_content(
                        document_content, 
                        document_title, 
                        user_id=user_id,
                        prompt_template_id=prompt_template_id,
                        user_requirements=user_requirements
                    )
                
                if result['success']:
                    # 读取生成的文件内容
                    with open(result['file'], 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    
                    # 检查是否生成了思维笔记文件
                    mindnote_content = None
                    if result.get('mindnote_file'):
                        with open(result['mindnote_file'], 'r', encoding='utf-8') as f:
                            mindnote_content = f.read()
                    
                    return jsonify({
                        'success': True,
                        'raw_content': raw_content,
                        'mindnote_content': mindnote_content,
                        'raw_file': result['file'],
                        'mindnote_file': result.get('mindnote_file'),
                        'user_id': user_id,
                        'key_name': result.get('key_name', '')  # 返回使用的密钥名称
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', '生成失败')
                    }), 500
                    
        finally:
            # 标记请求处理完成
            mark_request_processing(user_id, content_hash, False)
            
    except Exception as e:
        # 确保清理请求状态
        if 'content_hash' in locals():
            mark_request_processing(user_id, content_hash, False)
        
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/download/<file_type>/<filename>')
def download_file(file_type, filename):
    """下载生成的文件"""
    try:
        user_id = get_user_session_id()
        output_dir = config_manager.get_config()["output"]["output_dir"]
        
        # 检查文件是否属于当前用户
        user_output_dir = Path(output_dir) / f"user_{user_id[:8]}"
        file_path = user_output_dir / filename
        
        # 如果用户目录中不存在，检查全局目录（向后兼容）
        if not file_path.exists():
            file_path = Path(output_dir) / filename
        
        if not file_path.exists():
            return jsonify({'error': '文件不存在或无权限访问'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@app.route('/api/content/<file_type>/<filename>')
def get_file_content(file_type, filename):
    """获取文件内容用于复制"""
    try:
        user_id = get_user_session_id()
        output_dir = config_manager.get_config()["output"]["output_dir"]
        
        # 检查文件是否属于当前用户
        user_output_dir = Path(output_dir) / f"user_{user_id[:8]}"
        file_path = user_output_dir / filename
        
        # 如果用户目录中不存在，检查全局目录（向后兼容）
        if not file_path.exists():
            file_path = Path(output_dir) / filename
        
        if not file_path.exists():
            return jsonify({'error': '文件不存在或无权限访问'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'filename': filename
        })
    except Exception as e:
        return jsonify({'error': f'获取内容失败: {str(e)}'}), 500

@app.route('/api/ai-providers')
def get_ai_providers():
    """获取可用的AI提供商列表"""
    providers = [
        {
            'id': 'doubao',
            'name': '豆包 (Doubao)',
            'description': '推荐用于测试用例生成',
            'models': [
                {
                    'id': 'doubao-1-5-thinking-vision-pro-250428',
                    'name': 'Doubao 1.5 Thinking Vision Pro',
                    'description': '多模态思维模型，支持图像和文本理解',
                    'default_temperature': 0.3,
                    'default_top_p': 0.6
                },
                {
                    'id': 'doubao-1-5-thinking-pro-250415',
                    'name': 'Doubao 1.5 Thinking Pro',
                    'description': '思维链推理模型，适合复杂逻辑分析',
                    'default_temperature': 0.3,
                    'default_top_p': 0.6
                },
                {
                    'id': 'doubao-seed-1-6-thinking-250715',
                    'name': 'Doubao Seed 1.6 Thinking',
                    'description': '种子模型，强大的推理和思考能力',
                    'default_temperature': 0.3,
                    'default_top_p': 0.6
                }
            ]
        },
        {
            'id': 'deepseek',
            'name': 'DeepSeek',
            'description': '通用AI模型',
            'models': []
        }
    ]
    return jsonify(providers)

@app.route('/api/doubao-keys')
def get_doubao_keys():
    """获取可用的豆包密钥列表"""
    try:
        from src.config import config_manager
        keys = config_manager.get_available_doubao_keys()
        return jsonify({
            'success': True,
            'keys': keys
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取豆包密钥列表失败: {str(e)}'
        }), 500

@app.route('/api/prompt-templates')
def get_prompt_templates():
    """获取可用的提示词模板列表"""
    try:
        from src.config import config_manager
        templates = config_manager.get_prompt_templates()
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取提示词模板列表失败: {str(e)}'
        }), 500

@app.route('/api/prompt-templates', methods=['POST'])
def create_custom_prompt_template():
    """创建自定义提示词模板"""
    try:
        data = request.get_json()
        template_id = data.get('template_id')
        name = data.get('name')
        description = data.get('description')
        content = data.get('content')
        
        if not all([template_id, name, content]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        from src.prompt_engineering import prompt_manager
        file_path = prompt_manager.create_custom_template(template_id, name, description, content)
        
        return jsonify({
            'success': True,
            'message': '自定义提示词模板创建成功',
            'file_path': file_path
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'创建自定义提示词模板失败: {str(e)}'
        }), 500

@app.route('/api/prompt-templates/<template_id>/content')
def get_prompt_template_content(template_id):
    """获取提示词模板内容"""
    try:
        from src.config import config_manager
        from src.prompt_engineering import prompt_manager
        
        # 获取模板内容
        content = prompt_manager.get_template_by_id(template_id)
        
        # 获取模板信息
        templates = config_manager.get_prompt_templates()
        template_info = next((t for t in templates if t.get('id') == template_id), {})
        
        return jsonify({
            'success': True,
            'content': content,
            'name': template_info.get('name', template_id),
            'description': template_info.get('description', '')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取提示词模板内容失败: {str(e)}'
        }), 500

@app.route('/api/prompts')
def get_prompts():
    """获取提示词列表"""
    try:
        prompts_dir = Path(__file__).parent / 'prompts'
        
        if not prompts_dir.exists():
            return jsonify({
                'success': True,
                'prompts': []
            })
        
        prompts = []
        for file_path in prompts_dir.glob('*.txt'):
            if file_path.is_file():
                stat = file_path.stat()
                prompts.append({
                    'filename': file_path.name,
                    'name': file_path.stem,
                    'size': stat.st_size,
                    'modified_time': stat.st_mtime,
                    'modified_date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
                    'path': str(file_path)
                })
        
        # 按修改时间倒序排列
        prompts.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'prompts': prompts
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取提示词列表失败: {str(e)}'
        }), 500

@app.route('/api/prompts/<filename>')
def get_prompt_content(filename):
    """获取提示词内容"""
    try:
        prompts_dir = Path(__file__).parent / 'prompts'
        file_path = prompts_dir / filename
        
        if not file_path.exists():
            return jsonify({'error': '提示词文件不存在'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件信息
        stat = file_path.stat()
        
        return jsonify({
            'success': True,
            'content': content,
            'filename': filename,
            'name': file_path.stem,
            'size': stat.st_size,
            'modified_time': stat.st_mtime,
            'modified_date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        })
    except Exception as e:
        return jsonify({'error': f'获取提示词内容失败: {str(e)}'}), 500

@app.route('/api/prompts/<filename>/download')
def download_prompt(filename):
    """下载提示词文件"""
    try:
        prompts_dir = Path(__file__).parent / 'prompts'
        file_path = prompts_dir / filename
        
        if not file_path.exists():
            return jsonify({'error': '提示词文件不存在'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@app.route('/api/prompts/<filename>', methods=['DELETE'])
def delete_prompt(filename):
    """删除提示词文件"""
    try:
        prompts_dir = Path(__file__).parent / 'prompts'
        file_path = prompts_dir / filename
        
        if not file_path.exists():
            return jsonify({'error': '提示词文件不存在'}), 404
        
        # 检查是否为默认提示词文件，防止误删
        default_prompts = ['mtp_optimized_prompt.txt', 'custom_prompt.txt', 'logic_check_prompt.txt']
        if filename in default_prompts:
            return jsonify({
                'success': False,
                'error': '不能删除默认提示词文件'
            }), 400
        
        # 删除文件
        file_path.unlink()
        
        return jsonify({
            'success': True,
            'message': f'提示词文件 {filename} 已删除'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'删除提示词文件失败: {str(e)}'
        }), 500

@app.route('/api/history')
def get_history():
    """获取历史测试用例文件列表"""
    try:
        output_dir = config_manager.get_config()["output"]["output_dir"]
        
        # 获取全局输出目录和所有用户专属目录
        global_output_dir = Path(output_dir)
        
        files = []
        
        # 获取全局目录中的所有AI文件
        if global_output_dir.exists():
            for file_path in global_output_dir.glob('*_ai*.txt'):
                if file_path.is_file():
                    files.append(file_path)
        
        # 获取所有用户专属目录中的AI文件
        if global_output_dir.exists():
            for user_dir in global_output_dir.glob('user_*'):
                if user_dir.is_dir():
                    for file_path in user_dir.glob('*_ai*.txt'):
                        if file_path.is_file():
                            files.append(file_path)
        
        # 处理文件信息
        file_infos = []
        for file_path in files:
            filename = file_path.name
            stat = file_path.stat()
            
            # 判断文件类型
            file_type = 'raw'
            if '_mindnote' in filename:
                file_type = 'mindnote'
            elif '_final' in filename:
                file_type = 'final'
            
            # 提取时间戳和标题
            parts = filename.replace('.txt', '').split('_')
            timestamp = None
            title = "测试用例"
            
            for i, part in enumerate(parts):
                if part == 'ai' and i > 0:
                    try:
                        timestamp = int(parts[i-1])
                        if i > 1:
                            title = '_'.join(parts[:i-1])
                        break
                    except ValueError:
                        pass
            
            # 如果没有找到时间戳，尝试其他模式
            if timestamp is None:
                # 尝试从文件名末尾提取时间戳（用户ID后缀前的数字）
                if '_ai.txt' in filename or '_ai_mindnote.txt' in filename:
                    # 移除后缀
                    base_name = filename.replace('_ai.txt', '').replace('_ai_mindnote.txt', '')
                    # 尝试从末尾提取时间戳
                    parts = base_name.split('_')
                    if len(parts) > 1:
                        try:
                            timestamp = int(parts[-1])
                            title = '_'.join(parts[:-1])
                        except ValueError:
                            # 如果最后一部分不是数字，使用整个文件名作为标题
                            title = base_name
            
            # 清理标题，移除时间戳和用户ID
            if title and '_' in title:
                title_parts = title.split('_')
                # 如果最后一部分是数字（时间戳），移除它
                if len(title_parts) > 1 and title_parts[-1].isdigit():
                    title = '_'.join(title_parts[:-1])
                # 如果倒数第二部分也是数字（用户ID），也移除它
                if len(title_parts) > 2 and title_parts[-2].isdigit():
                    title = '_'.join(title_parts[:-2])
            
            # 如果时间戳还是None，尝试从文件名中提取
            if timestamp is None:
                # 尝试匹配模式：*_时间戳_用户ID_ai.txt
                import re
                pattern = r'_(\d+)_[a-f0-9]{8}_ai\.txt$'
                match = re.search(pattern, filename)
                if match:
                    timestamp = int(match.group(1))
            
            file_infos.append({
                'filename': filename,
                'file_type': file_type,
                'size': stat.st_size,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'timestamp': timestamp,
                'title': title,
                'path': str(file_path)
            })
        
        # 按创建时间倒序排列
        file_infos.sort(key=lambda x: x['created_time'], reverse=True)
        
        # 按文件类型分组
        grouped_files = {}
        for file_info in file_infos:
            # 使用标题和时间戳作为分组键，确保同一测试用例的不同格式文件被分到一组
            group_key = f"{file_info['title']}_{file_info['timestamp']}" if file_info['timestamp'] else file_info['title']
            
            if group_key not in grouped_files:
                grouped_files[group_key] = {
                    'title': file_info['title'],
                    'timestamp': file_info['timestamp'],
                    'created_time': file_info['created_time'],
                    'files': []
                }
            grouped_files[group_key]['files'].append(file_info)
        
        # 转换为列表格式
        history_list = []
        for base_name, group_info in grouped_files.items():
            history_list.append({
                'id': base_name,
                'title': group_info['title'],
                'timestamp': group_info['timestamp'],
                'created_time': group_info['created_time'],
                'created_date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(group_info['created_time'])),
                'files': group_info['files']
            })
        
        return jsonify({
            'success': True,
            'history': history_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取历史记录失败: {str(e)}'
        }), 500

@app.route('/api/history/<filename>')
def get_history_file(filename):
    """获取历史文件内容"""
    try:
        output_dir = config_manager.get_config()["output"]["output_dir"]
        
        # 直接使用全局目录，不进行用户会话隔离
        file_path = Path(output_dir) / filename
        
        if not file_path.exists():
            return jsonify({'error': '文件不存在或无权限访问'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件信息
        stat = file_path.stat()
        
        return jsonify({
            'success': True,
            'content': content,
            'filename': filename,
            'size': stat.st_size,
            'created_time': stat.st_ctime,
            'modified_time': stat.st_mtime
        })
    except Exception as e:
        return jsonify({'error': f'获取文件内容失败: {str(e)}'}), 500

@app.route('/api/status')
def get_system_status():
    """获取系统状态信息"""
    try:
        user_id = get_user_session_id()
        
        # 清理过期请求
        cleanup_expired_requests()
        
        # 获取当前处理的请求数量
        with processing_lock:
            current_processing = len(processing_requests)
            user_processing = sum(1 for key in processing_requests.keys() if user_id in key)
        
        # 获取全局目录信息
        output_dir = config_manager.get_config()["output"]["output_dir"]
        global_output_dir = Path(output_dir)
        
        global_file_count = 0
        if global_output_dir.exists():
            global_file_count = len(list(global_output_dir.glob('*_ai*.txt')))
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'system_status': {
                'total_processing_requests': current_processing,
                'user_processing_requests': user_processing,
                'max_concurrent_requests': 3,
                'global_file_count': global_file_count,
                'global_output_dir': str(global_output_dir)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取系统状态失败: {str(e)}'
        }), 500

@app.route('/api/clear-user-data', methods=['POST'])
def clear_user_data():
    """清除当前用户的所有数据"""
    try:
        user_id = get_user_session_id()
        output_dir = config_manager.get_config()["output"]["output_dir"]
        user_output_dir = Path(output_dir) / f"user_{user_id[:8]}"
        
        if user_output_dir.exists():
            # 删除用户目录中的所有文件
            for file_path in user_output_dir.glob('*'):
                if file_path.is_file():
                    file_path.unlink()
            
            # 删除空目录
            try:
                user_output_dir.rmdir()
            except OSError:
                pass  # 目录不为空，忽略错误
        
        return jsonify({
            'success': True,
            'message': '用户数据已清除'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'清除用户数据失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 创建templates目录
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # 创建static目录
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    
    print("启动测试用例生成Web平台...")
    print("本地访问地址: http://localhost:5002")
    # print("外部访问地址: http://10.240.8.108:5002")
    app.run(debug=True, host='0.0.0.0', port=5002)

    #ngrok http 5002