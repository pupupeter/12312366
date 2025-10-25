

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from pymongo import MongoClient
import hashlib
import os
from datetime import datetime
import subprocess
import atexit
import signal
import sys
import requests
import re
import urllib.parse

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用於 session 加密
app.config['JSON_AS_ASCII'] = False  # 確保 JSON 回應正確處理中文
app.config['TEMPLATES_AUTO_RELOAD'] = True  # 自動重載模板
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用靜態文件緩存

# MongoDB 連接
client = MongoClient('mongodb://localhost:27017/')
db = client['local']  # 資料庫名稱
collection = db['帳號密碼']  # 集合名稱

# 全局變量存儲子進程
web_app_process = None
web_app22_process = None
streamlit_process = None

# 啟動 web_app.py (韓文)
def start_web_app():
    global web_app_process
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        web_app_path = os.path.join(script_dir, 'web_app.py')

        web_app_process = subprocess.Popen(
            [sys.executable, web_app_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=script_dir
        )

        # 等待一下讓服務啟動
        import time
        time.sleep(2)

        # 檢查進程是否還在運行
        if web_app_process.poll() is None:
            print("✓ 韓文新聞系統 (web_app.py) 已在 port 5000 啟動")
        else:
            stdout, stderr = web_app_process.communicate()
            print(f"✗ web_app.py 啟動後立即終止")
            print(f"  錯誤: {stderr.decode('utf-8')}")
    except Exception as e:
        print(f"✗ 啟動 web_app.py 失敗: {e}")

# 啟動 web_app22.py (中文)
def start_web_app22():
    global web_app22_process
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        web_app22_path = os.path.join(script_dir, 'web_app22.py')

        web_app22_process = subprocess.Popen(
            [sys.executable, web_app22_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=script_dir
        )

        import time
        time.sleep(2)

        if web_app22_process.poll() is None:
            print("✓ 中文詞彙系統 (web_app22.py) 已在 port 5001 啟動")
        else:
            stdout, stderr = web_app22_process.communicate()
            print(f"✗ web_app22.py 啟動後立即終止")
            print(f"  錯誤: {stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"✗ 啟動 web_app22.py 失敗: {e}")

# 啟動 Streamlit TTS 服務
def start_streamlit():
    global streamlit_process
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        streamlit_path = os.path.join(script_dir, 'gemini_tts_auth_app.py')

        streamlit_process = subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', streamlit_path,
             '--server.port', '8501', '--server.headless', 'true'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=script_dir
        )

        import time
        time.sleep(3)

        if streamlit_process.poll() is None:
            print("✓ Gemini TTS 系統 (Streamlit) 已在 port 8501 啟動")
        else:
            stdout, stderr = streamlit_process.communicate()
            print(f"✗ Streamlit 啟動後立即終止")
            print(f"  錯誤: {stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"✗ 啟動 Streamlit 失敗: {e}")

# 停止所有服務
def stop_all_services():
    global web_app_process, web_app22_process, streamlit_process

    if web_app_process:
        web_app_process.terminate()
        web_app_process.wait()
        print("✓ 韓文新聞系統已停止")

    if web_app22_process:
        web_app22_process.terminate()
        web_app22_process.wait()
        print("✓ 中文詞彙系統已停止")

    if streamlit_process:
        streamlit_process.terminate()
        streamlit_process.wait()
        print("✓ Streamlit TTS 系統已停止")

# 註冊清理函數
atexit.register(stop_all_services)

# 處理 SIGINT (Ctrl+C) 信號
def signal_handler(sig, frame):
    print("\n正在關閉所有服務...")
    stop_all_services()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# 密碼加密函數
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 首頁 - 重導向到登入頁
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# 登入頁面
@app.route('/login')
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 註冊頁面
@app.route('/register')
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

# 主控台頁面（需登入）
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

# 處理登入請求
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '請輸入帳號和密碼'}), 400

    # 查詢資料庫
    user = collection.find_one({'username': username})

    if user and user['password'] == hash_password(password):
        session['username'] = username
        session['user_id'] = str(user['_id'])

        # 更新最後登入時間
        collection.update_one(
            {'username': username},
            {'$set': {'last_login': datetime.now()}}
        )

        return jsonify({
            'success': True,
            'message': '登入成功',
            'username': username
        })
    else:
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'}), 401

# 處理註冊請求
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': '帳號和密碼不能為空'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': '密碼長度至少需要 6 個字元'}), 400

    # 檢查帳號是否已存在
    if collection.find_one({'username': username}):
        return jsonify({'success': False, 'message': '帳號已存在'}), 409

    # 檢查 email 是否已存在
    if email and collection.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Email 已被使用'}), 409

    # 建立新用戶
    new_user = {
        'username': username,
        'password': hash_password(password),
        'email': email,
        'created_at': datetime.now(),
        'last_login': None
    }

    collection.insert_one(new_user)

    return jsonify({
        'success': True,
        'message': '註冊成功，請登入',
        'username': username
    })

# 登出
@app.route('/api/logout', methods=['POST'])
def api_logout():
    username = session.get('username')
    session.clear()
    return jsonify({'success': True, 'message': '已登出', 'username': username})

# 檢查登入狀態
@app.route('/api/check_auth')
def check_auth():
    if 'username' in session:
        return jsonify({
            'authenticated': True,
            'username': session['username']
        })
    return jsonify({'authenticated': False})

# 代理路由：韓文新聞系統 (轉發到 port 5000)
@app.route('/korean-app', defaults={'path': ''})
@app.route('/korean-app/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy_korean(path):
    if 'username' not in session:
        return redirect(url_for('login'))

    # 構建目標 URL
    target_url = f'http://localhost:5000/{path}'
    if request.query_string:
        target_url += f'?{request.query_string.decode()}'

    # 準備請求參數
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    headers['X-User-ID'] = session.get('user_id', '')
    # URL 編碼 username 以避免中文字符導致 Latin-1 編碼錯誤
    username = session.get('username', '')
    headers['X-Username'] = urllib.parse.quote(username) if username else ''

    # 轉發請求
    try:
        if request.method == 'GET':
            resp = requests.get(target_url, headers=headers, stream=True)
        elif request.method == 'POST':
            resp = requests.post(target_url, headers=headers, data=request.get_data(), stream=True)
        elif request.method == 'DELETE':
            resp = requests.delete(target_url, headers=headers, stream=True)
        else:
            resp = requests.request(request.method, target_url, headers=headers, data=request.get_data(), stream=True)

        # 處理回應
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for name, value in resp.raw.headers.items()
                            if name.lower() not in excluded_headers]

        # 如果是 HTML 回應，重寫路徑
        response_content = resp.content
        content_type = 'application/octet-stream'

        if resp.headers.get('Content-Type', '').startswith('text/html'):
            html_content = response_content.decode('utf-8', errors='ignore')
            # 由於前端已經使用 getBasePath() 動態處理路徑，不需要在代理層重寫 HTML
            # 只需要確保正確的 Content-Type
            response_content = html_content.encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        elif resp.headers.get('Content-Type'):
            content_type = resp.headers.get('Content-Type')
            # 確保 JSON 回應也使用 UTF-8
            if 'application/json' in content_type and 'charset' not in content_type:
                content_type = 'application/json; charset=utf-8'

        # 過濾並更新 Content-Type header
        response_headers = [(name, value) for name, value in response_headers if name.lower() != 'content-type']
        response_headers.append(('Content-Type', content_type))

        return Response(response_content, resp.status_code, response_headers)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': '無法連接到韓文新聞系統', 'details': str(e)}), 503

# 代理路由：中文詞彙系統 (轉發到 port 5001)
@app.route('/chinese-app', defaults={'path': ''})
@app.route('/chinese-app/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy_chinese(path):
    if 'username' not in session:
        return redirect(url_for('login'))

    # 構建目標 URL
    target_url = f'http://localhost:5001/{path}'
    if request.query_string:
        target_url += f'?{request.query_string.decode()}'

    # 準備請求參數
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    headers['X-User-ID'] = session.get('user_id', '')
    # URL 編碼 username 以避免中文字符導致 Latin-1 編碼錯誤
    username = session.get('username', '')
    headers['X-Username'] = urllib.parse.quote(username) if username else ''

    # 轉發請求
    try:
        if request.method == 'GET':
            resp = requests.get(target_url, headers=headers, stream=True)
        elif request.method == 'POST':
            resp = requests.post(target_url, headers=headers, data=request.get_data(), stream=True)
        elif request.method == 'DELETE':
            resp = requests.delete(target_url, headers=headers, stream=True)
        else:
            resp = requests.request(request.method, target_url, headers=headers, data=request.get_data(), stream=True)

        # 處理回應
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for name, value in resp.raw.headers.items()
                            if name.lower() not in excluded_headers]

        # 如果是 HTML 回應，重寫路徑
        response_content = resp.content
        content_type = 'application/octet-stream'

        if resp.headers.get('Content-Type', '').startswith('text/html'):
            html_content = response_content.decode('utf-8', errors='ignore')
            # 由於前端已經使用 getBasePath() 動態處理路徑，不需要在代理層重寫 HTML
            # 只需要確保正確的 Content-Type
            response_content = html_content.encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        elif resp.headers.get('Content-Type'):
            content_type = resp.headers.get('Content-Type')
            # 確保 JSON 回應也使用 UTF-8
            if 'application/json' in content_type and 'charset' not in content_type:
                content_type = 'application/json; charset=utf-8'

        # 過濾並更新 Content-Type header
        response_headers = [(name, value) for name, value in response_headers if name.lower() != 'content-type']
        response_headers.append(('Content-Type', content_type))

        return Response(response_content, resp.status_code, response_headers)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': '無法連接到中文詞彙系統', 'details': str(e)}), 503

# TTS 頁面 (嵌入 Streamlit)
@app.route('/tts')
def tts_page():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session.get('username', '')

    # 創建嵌入 Streamlit 的 HTML 頁面
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini TTS 語音生成器</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .navbar {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 15px 30px;
            border-radius: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        .navbar a {{
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            transition: background 0.3s;
        }}
        .navbar a:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        .streamlit-container {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            height: calc(100vh - 120px);
        }}
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
    </style>
</head>
<body>
    <div class="navbar">
        <div>
            <span style="font-size: 1.3em; font-weight: bold;">🎙️ Gemini TTS 語音生成器</span>
            <span style="margin-left: 15px; opacity: 0.8;">用戶: {username}</span>
        </div>
        <a href="/dashboard">← 返回主控台</a>
    </div>
    <div class="streamlit-container">
        <iframe src="http://localhost:8501" allowfullscreen></iframe>
    </div>
</body>
</html>"""

    # 使用 Response 對象並明確設置 UTF-8 編碼
    return Response(html_content, mimetype='text/html; charset=utf-8')

if __name__ == '__main__':
    # 確保 MongoDB 連接成功
    try:
        client.server_info()
        print("✓ MongoDB 連接成功")
        print(f"✓ 使用資料庫: {db.name}")
        print(f"✓ 使用集合: {collection.name}")
    except Exception as e:
        print(f"✗ MongoDB 連接失敗: {e}")
        print("請確保 MongoDB 服務正在運行")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("正在啟動所有服務...")
    print("=" * 50)

    # 啟動所有子服務
    start_web_app()
    start_web_app22()
    start_streamlit()

    print("\n" + "=" * 50)
    print("所有服務已啟動：")
    print("  - 用戶系統: http://localhost:8080")
    print("  - 韓文新聞: http://localhost:5000 (代理: /korean-app)")
    print("  - 中文詞彙: http://localhost:5001 (代理: /chinese-app)")
    print("  - Gemini TTS: http://localhost:8501 (嵌入: /tts)")
    print("=" * 50)
    print("\n按 Ctrl+C 停止所有服務\n")

    try:
        app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)
    finally:
        stop_all_services()
