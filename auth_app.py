from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用於 session 加密

# MongoDB 連接
client = MongoClient('mongodb://localhost:27017/')
db = client['帳號密碼']  # 資料庫名稱
collection = db['帳號密碼']  # 集合名稱

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
