

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
import hashlib
import os
from datetime import datetime
import subprocess
import atexit
import signal
import sys

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用於 session 加密

# MongoDB 連接
client = MongoClient('mongodb://localhost:27017/')
db = client['local']  # 資料庫名稱
collection = db['帳號密碼']  # 集合名稱

# 全局變量存儲 web_app 子進程
web_app_process = None

# 啟動 web_app.py
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

# 停止 web_app.py
def stop_web_app():
    global web_app_process
    if web_app_process:
        web_app_process.terminate()
        web_app_process.wait()
        print("✓ 韓文新聞系統已停止")

# 註冊清理函數
atexit.register(stop_web_app)

# 處理 SIGINT (Ctrl+C) 信號
def signal_handler(sig, frame):
    print("\n正在關閉所有服務...")
    stop_web_app()
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

    app.run(debug=True, host='0.0.0.0', port=5001)
    # 啟動 web_app.py
    start_web_app()

    print("✓ 用戶系統已在 port 5001 啟動")
    print("=" * 50)
    print("所有服務已啟動：")
    print("  - 用戶系統: http://localhost:5001")
    print("  - 韓文新聞: http://localhost:5000")
    print("=" * 50)

    try:
        app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
    finally:
        stop_web_app()
