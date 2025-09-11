#!/usr/bin/env python3
"""
飞书插件获取 User Access Token 的脚本 (增强调试版)
"""

import requests
import json
from flask import Flask, request
import webbrowser
import threading
import time
from urllib.parse import quote

# 飞书插件配置信息 - 请替换为你的实际信息
PLUGIN_ID = "MII_689D7F37950A801C"  # 替换为你的插件ID
PLUGIN_SECRET = "your_plugin_secret_here"  # 替换为你的插件密钥
REDIRECT_URI = "http://localhost:5000/oauth/callback"  # 本地回调地址

app = Flask(__name__)
access_token_result = None


class FeishuPluginAuth:
    """飞书插件认证类"""

    @staticmethod
    def get_plugin_access_token():
        """获取插件访问凭证 (plugin_access_token)"""
        url = "https://open.feishu.cn/open_api/auth/plugin_token"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            "plugin_id": PLUGIN_ID,
            "plugin_secret": PLUGIN_SECRET
        }

        try:
            print(f"请求 plugin_access_token: {url}")
            print(f"请求数据: {json.dumps(data)}")

            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")

            response.raise_for_status()
            result = response.json()

            print(f"获取 plugin_access_token 响应: {json.dumps(result, indent=2)}")

            if result.get("code") == 0:
                plugin_token = result.get("data", {}).get("plugin_access_token")
                print(f"成功获取 plugin_access_token: {plugin_token}")
                return plugin_token
            else:
                error_msg = result.get("msg", "未知错误")
                error_code = result.get("code", "未知错误码")
                print(f"获取 plugin_access_token 失败: 错误码 {error_code}, 错误信息: {error_msg}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            print(f"处理响应异常: {str(e)}")
            return None

    @staticmethod
    def get_user_access_token(plugin_token, code):
        """使用授权码和插件令牌获取用户访问令牌 (user_access_token)"""
        url = "https://open.feishu.cn/open_api/authen/user_plugin_token"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Plugin-Token": plugin_token
        }
        data = {
            "grant_type": "authorization_code",
            "code": code
        }

        try:
            print(f"请求 user_access_token: {url}")
            print(f"请求头: {headers}")
            print(f"请求数据: {json.dumps(data)}")

            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")

            response.raise_for_status()
            result = response.json()

            print(f"获取用户访问令牌响应: {json.dumps(result, indent=2)}")

            if result.get("code") == 0:
                return result.get("data")
            else:
                error_msg = result.get("msg", "未知错误")
                error_code = result.get("code", "未知错误码")
                print(f"获取 user_access_token 失败: 错误码 {error_code}, 错误信息: {error_msg}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            print(f"处理响应异常: {str(e)}")
            return None


# Flask 路由
@app.route('/')
def index():
    """生成飞书授权链接"""
    # 对重定向 URI 进行 URL 编码
    encoded_redirect_uri = quote(REDIRECT_URI, safe='')
    auth_url = f"https://open.feishu.cn/open-apis/authen/v1/index?redirect_uri={encoded_redirect_uri}&app_id={PLUGIN_ID}"

    return f'''
    <h1>飞书插件获取 User Access Token</h1>
    <p>Plugin ID: {PLUGIN_ID}</p>
    <p>重定向 URI: {REDIRECT_URI}</p>
    <p>请确保已在飞书开放平台将回调地址设置为: {REDIRECT_URI}</p>
    <p><a href="{auth_url}" target="_blank">点击这里登录飞书获取授权</a></p>
    <p>授权链接: {auth_url}</p>
    '''


@app.route('/oauth/callback')
def oauth_callback():
    """处理飞书授权回调"""
    global access_token_result

    print("收到飞书回调请求")
    print(f"请求参数: {dict(request.args)}")

    # 获取授权码
    code = request.args.get('code')
    if not code:
        error_msg = request.args.get('error', '未知错误')
        error_description = request.args.get('error_description', '')
        print(f"授权失败: 未获取到授权码, 错误: {error_msg}, 描述: {error_description}")
        return f"授权失败: {error_msg} - {error_description}", 400

    print(f"获取到授权码: {code}")

    # 先获取 plugin_access_token
    auth = FeishuPluginAuth()
    plugin_token = auth.get_plugin_access_token()

    if not plugin_token:
        return "获取插件访问令牌失败", 500

    # 使用授权码和插件令牌获取用户访问令牌
    token_data = auth.get_user_access_token(plugin_token, code)

    if token_data:
        access_token_result = token_data
        print("成功获取用户访问令牌")
        return f'''
        <h1>授权成功!</h1>
        <p>User Access Token 已获取，脚本将在 5 秒后自动关闭。</p>
        <pre>{json.dumps(token_data, indent=2, ensure_ascii=False)}</pre>
        <script>
            setTimeout(function() {{
                window.close();
            }}, 5000);
        </script>
        '''
    else:
        return "授权失败: 无法获取访问令牌", 400


def run_server():
    """运行Flask服务器"""
    print("=" * 60)
    print("飞书插件获取 User Access Token")
    print("=" * 60)
    print(f"Plugin ID: {PLUGIN_ID}")
    print(f"重定向 URI: {REDIRECT_URI}")
    print("请确保已在飞书开放平台将回调地址设置为上述重定向 URI")
    print("访问 http://localhost:5000 开始授权流程")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    # 检查配置
    if PLUGIN_ID == "your_plugin_id_here" or PLUGIN_SECRET == "your_plugin_secret_here":
        print("错误: 请先配置你的 PLUGIN_ID 和 PLUGIN_SECRET")
        print("1. 打开飞书开放平台")
        print("2. 进入你的插件应用")
        print("3. 在'凭证与基础信息'页面找到 Plugin ID 和 Plugin Secret")
        print("4. 将它们替换到代码中的 PLUGIN_ID 和 PLUGIN_SECRET 变量")
        exit(1)


    # 在浏览器中打开授权页面
    def open_browser():
        time.sleep(1)  # 等待服务器启动
        webbrowser.open('http://localhost:5000')


    # 启动浏览器线程
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    # 运行服务器
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n用户中断执行")

    # 输出结果
    if access_token_result:
        print("\n" + "=" * 60)
        print("成功获取 User Access Token:")
        print(json.dumps(access_token_result, indent=2, ensure_ascii=False))
        print("=" * 60)
    else:
        print("未能获取到 User Access Token")