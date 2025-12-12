

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
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
import io
import wave
from translations import get_translation
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# 載入環境變數
load_dotenv()

# Supabase 用戶操作
from supabase_utils import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    update_user,
    update_user_password,
    update_user_language,
    update_last_login,
    check_email_exists
)

# Gemini TTS 相關
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-genai not installed, Gemini TTS will not be available")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))  # 用於 session 加密
app.config['JSON_AS_ASCII'] = False  # 確保 JSON 回應正確處理中文
app.config['TEMPLATES_AUTO_RELOAD'] = True  # 自動重載模板
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用靜態文件緩存

# TTS 語言和聲音選項
LANGUAGE_OPTIONS = {
    "English": "en",
    "中文 (Chinese Simplified)": "zh-cn",
    "繁體中文 (Chinese Traditional)": "zh-tw",
    "한국어 (Korean)": "ko",
    "日本語 (Japanese)": "ja",
    "Español (Spanish)": "es",
    "Français (French)": "fr",
    "Deutsch (German)": "de",
    "Italiano (Italian)": "it",
    "Português (Portuguese)": "pt",
    "Русский (Russian)": "ru",
    "العربية (Arabic)": "ar",
    "ไทย (Thai)": "th",
    "Tiếng Việt (Vietnamese)": "vi",
    "Bahasa Indonesia (Indonesian)": "id",
    "हिन्दी (Hindi)": "hi"
}

VOICE_OPTIONS = ["Kore", "Puck", "Charon", "Fenrir", "Aoede"]

# 全局變量存儲子進程
web_app_process = None
web_app22_process = None

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

# 停止所有服務
def stop_all_services():
    global web_app_process, web_app22_process

    if web_app_process:
        web_app_process.terminate()
        web_app_process.wait()
        print("✓ 韓文新聞系統已停止")

    if web_app22_process:
        web_app22_process.terminate()
        web_app22_process.wait()
        print("✓ 中文詞彙系統已停止")

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

# ==================== TTS 輔助函數 ====================

def fetch_webpage(url):
    """抓取並轉換網頁為 markdown"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # 移除 script 和 style 元素
        for script in soup(["script", "style"]):
            script.decompose()

        # 轉換為 markdown
        markdown_content = md(str(soup), heading_style="ATX")

        # 限制內容長度
        if len(markdown_content) > 10000:
            markdown_content = markdown_content[:10000]

        return markdown_content
    except Exception as e:
        raise Exception(f"Failed to fetch webpage: {str(e)}")

def generate_conversation_from_content(client, content, speaker1_name, speaker2_name, language_code='en'):
    """使用 Gemini 2.5 Flash 分析內容並生成對話"""
    try:
        language_instructions = {
            'en': 'in English',
            'zh-cn': 'in Simplified Chinese (简体中文)',
            'zh-tw': 'in Traditional Chinese (繁體中文)',
            'ko': 'in Korean (한국어)',
            'ja': 'in Japanese (日本語)',
            'es': 'in Spanish (Español)',
            'fr': 'in French (Français)',
            'de': 'in German (Deutsch)',
            'it': 'in Italian (Italiano)',
            'pt': 'in Portuguese (Português)',
            'ru': 'in Russian (Русский)',
            'ar': 'in Arabic (العربية)',
            'th': 'in Thai (ไทย)',
            'vi': 'in Vietnamese (Tiếng Việt)',
            'id': 'in Indonesian (Bahasa Indonesia)',
            'hi': 'in Hindi (हिन्दी)'
        }

        lang_instruction = language_instructions.get(language_code, 'in English')

        prompt = f"""Based on the following content, create an engaging and informative conversation between {speaker1_name} and {speaker2_name} {lang_instruction}.

The conversation should:
1. Discuss the main points and key insights from the content
2. Be natural and conversational {lang_instruction}
3. Include questions and answers between the two speakers
4. Be around 8-12 exchanges (lines of dialogue)
5. Format: Each line should start with the speaker's name followed by a colon
6. IMPORTANT: The ENTIRE conversation must be {lang_instruction}

Content:
{content}

Generate the conversation in this exact format:
{speaker1_name}: [dialogue {lang_instruction}]
{speaker2_name}: [dialogue {lang_instruction}]
{speaker1_name}: [dialogue {lang_instruction}]
...and so on.

Only output the conversation, nothing else. Remember: ALL dialogue must be {lang_instruction}."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        conversation = response.text.strip()
        return conversation
    except Exception as e:
        raise Exception(f"Failed to generate conversation: {str(e)}")

def wave_file_to_path(filename, pcm, channels=1, rate=24000, sample_width=2):
    """保存 PCM 音頻數據到 WAV 文件"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

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

    # 獲取用戶的語言設定
    user = get_user_by_username(session['username'])
    lang = 'zh-TW'
    if user and user.get('language'):
        lang = user.get('language', 'zh-TW')

    # 獲取翻譯
    translations = get_translation(lang)

    return render_template('dashboard.html',
                         username=session['username'],
                         lang=lang,
                         t=translations)

# 處理登入請求
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '請輸入帳號和密碼'}), 400

    # 查詢資料庫
    user = get_user_by_username(username)

    if user and user['password'] == hash_password(password):
        session['username'] = username
        session['user_id'] = str(user.get('id', username))

        # 更新最後登入時間
        update_last_login(username)

        # 記錄登入活動
        log_activity(username, 'login', '用戶登入系統')

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
    email = data.get('email', '').strip() or None

    if not username or not password:
        return jsonify({'success': False, 'message': '帳號和密碼不能為空'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': '密碼長度至少需要 6 個字元'}), 400

    # 建立新用戶 (create_user 會自動檢查是否已存在)
    result = create_user(username, hash_password(password), email)

    if not result['success']:
        if result['error'] == 'username_exists':
            return jsonify({'success': False, 'message': '帳號已存在'}), 409
        elif result['error'] == 'email_exists':
            return jsonify({'success': False, 'message': 'Email 已被使用'}), 409
        else:
            return jsonify({'success': False, 'message': '註冊失敗，請稍後再試'}), 500

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

# 獲取用戶資料
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    user = get_user_by_username(session['username'])
    if user:
        return jsonify({
            'success': True,
            'user': {
                'username': user['username'],
                'email': user.get('email', ''),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login'),
                'settings': {
                    'notifications': True,
                    'theme': 'default',
                    'language': user.get('language', 'zh-TW')
                }
            }
        })
    return jsonify({'success': False, 'message': '用戶不存在'}), 404

# 更新用戶資料
@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    data = request.json
    email = data.get('email', '').strip() or None

    # 檢查 email 是否被其他用戶使用
    if email:
        if check_email_exists(email, exclude_username=session['username']):
            return jsonify({'success': False, 'message': 'Email 已被使用'}), 409

    # 更新用戶資料
    update_user(session['username'], {'email': email})

    return jsonify({'success': True, 'message': '資料更新成功'})

# 修改密碼
@app.route('/api/user/password', methods=['PUT'])
def change_password():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'success': False, 'message': '請填寫所有欄位'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密碼長度至少需要 6 個字元'}), 400

    # 驗證舊密碼
    user = get_user_by_username(session['username'])
    if not user or user['password'] != hash_password(old_password):
        return jsonify({'success': False, 'message': '舊密碼錯誤'}), 401

    # 更新密碼
    update_user_password(session['username'], hash_password(new_password))

    return jsonify({'success': True, 'message': '密碼修改成功'})

# 獲取用戶設定
@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    user = get_user_by_username(session['username'])
    if user:
        settings = {
            'notifications': True,
            'theme': 'default',
            'language': user.get('language', 'zh-TW'),
            'email_notifications': False
        }
        return jsonify({'success': True, 'settings': settings})
    return jsonify({'success': False, 'message': '用戶不存在'}), 404

# 更新用戶設定
@app.route('/api/user/settings', methods=['PUT'])
def update_user_settings():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    data = request.json
    language = data.get('language', 'zh-TW')

    # 只更新語言設定到資料庫
    update_user_language(session['username'], language)

    # 記錄設定更新活動
    log_activity(session['username'], 'settings_update', '更新系統設定')

    return jsonify({'success': True, 'message': '設定已儲存'})

# 獲取翻譯 API (可選 - 用於前端動態切換語言而不重新載入)
@app.route('/api/translations/<lang_code>', methods=['GET'])
def get_translations(lang_code):
    """獲取指定語言的翻譯"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    translations = get_translation(lang_code)
    return jsonify({'success': True, 'translations': translations, 'lang': lang_code})

# 記錄用戶活動 (簡化版 - 僅記錄到 console)
def log_activity(username, activity_type, description):
    """記錄用戶活動到 console"""
    try:
        print(f"[Activity] {datetime.now().isoformat()} - {username}: {activity_type} - {description}")
    except Exception as e:
        print(f"記錄活動失敗: {e}")

# 獲取活動記錄 (簡化版 - 活動記錄已移除)
@app.route('/api/user/activities', methods=['GET'])
def get_user_activities():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    # 活動記錄功能已簡化，返回空列表
    return jsonify({'success': True, 'activities': []})

# 上傳用戶頭像
@app.route('/api/user/avatar', methods=['POST'])
def upload_avatar():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    data = request.json
    avatar_data = data.get('avatar', '')

    # 驗證是否為 base64 圖片
    if not avatar_data.startswith('data:image/'):
        return jsonify({'success': False, 'message': '無效的圖片格式'}), 400

    # 檢查大小（base64 字符串長度，約 2MB 限制）
    if len(avatar_data) > 2 * 1024 * 1024 * 1.37:  # base64 會比原始大小大約 37%
        return jsonify({'success': False, 'message': '圖片大小超過 2MB 限制'}), 400

    # 更新用戶頭像
    try:
        result = update_user(session['username'], {'avatar': avatar_data})
        if result.get('success'):
            return jsonify({'success': True, 'message': '頭像更新成功'})
        else:
            return jsonify({'success': False, 'message': '更新失敗'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失敗: {str(e)}'}), 500

# 獲取用戶頭像
@app.route('/api/user/avatar', methods=['GET'])
def get_avatar():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    user = get_user_by_username(session['username'])
    if user and 'avatar' in user:
        return jsonify({'success': True, 'avatar': user['avatar']})
    return jsonify({'success': True, 'avatar': None})

# 獲取系統統計
@app.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登入'}), 401

    try:
        user = get_user_by_username(session['username'])

        # 計算使用天數
        days_active = 0
        member_since = None
        if user and user.get('created_at'):
            created_at_str = user.get('created_at')
            try:
                # 處理 ISO 格式的日期字串
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                else:
                    created_at = created_at_str
                days_active = (datetime.now() - created_at.replace(tzinfo=None)).days + 1
                member_since = created_at_str
            except:
                days_active = 1
                member_since = created_at_str

        return jsonify({
            'success': True,
            'stats': {
                'login_count': 0,  # 活動記錄已簡化
                'total_activities': 0,  # 活動記錄已簡化
                'days_active': days_active,
                'member_since': member_since
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'獲取統計失敗: {str(e)}'}), 500

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

# 遊戲選單頁面
@app.route('/games')
def games_menu():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('games/menu.html', username=session['username'])

# 配對遊戲頁面
@app.route('/games/matching')
def matching_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('games/matching.html', username=session['username'])

# 打字遊戲頁面
@app.route('/games/typing')
def typing_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('games/typing.html', username=session['username'])

# 聽力遊戲頁面
@app.route('/games/listening')
def listening_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('games/listening.html', username=session['username'])

# ==================== 單字 TTS API ====================

def create_wave_file(pcm_data, channels=1, rate=24000, sample_width=2):
    """將 PCM 資料轉換為 WAV 格式"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    buffer.seek(0)
    return buffer

@app.route('/api/tts/speak', methods=['POST'])
def tts_speak():
    """生成單字語音的 API"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not GEMINI_AVAILABLE:
        return jsonify({'error': 'Gemini TTS not available'}), 503

    try:
        data = request.json
        text = data.get('text', '')
        lang = data.get('lang', 'zh')  # 'zh' 或 'ko'

        if not text:
            return jsonify({'error': 'Text is required'}), 400

        # 取得 API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'GEMINI_API_KEY not configured'}), 500

        # 建立 Gemini 客戶端
        client = genai.Client(api_key=api_key)

        # 選擇適合的語音
        voice_name = "Kore"  # 預設語音，支援多語言

        # 生成語音
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                )
            )
        )

        # 取得音頻資料
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # 轉換為 WAV
        wav_buffer = create_wave_file(audio_data)

        return send_file(
            wav_buffer,
            mimetype='audio/wav',
            as_attachment=False
        )

    except Exception as e:
        print(f"TTS Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/check')
def tts_check():
    """檢查 TTS 是否可用"""
    api_key = os.getenv('GEMINI_API_KEY')
    return jsonify({
        'available': GEMINI_AVAILABLE and bool(api_key),
        'gemini_installed': GEMINI_AVAILABLE,
        'api_key_configured': bool(api_key)
    })

# TTS 主頁面 (Flask 版本)
@app.route('/tts')
def tts_page():
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template('tts_main.html',
                         username=session.get('username'),
                         voices=VOICE_OPTIONS,
                         languages=LANGUAGE_OPTIONS)

# ==================== TTS API 路由 ====================

@app.route('/api/tts/generate-from-url', methods=['POST'])
def tts_generate_from_url():
    """從 URL 生成對話和音頻"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not GEMINI_AVAILABLE:
        return jsonify({'error': 'Gemini API not available'}), 500

    try:
        data = request.json
        url = data.get('url')
        api_key = data.get('api_key')
        speaker1_name = data.get('speaker1_name', 'Joe')
        speaker2_name = data.get('speaker2_name', 'Jane')
        speaker1_voice = data.get('speaker1_voice', 'Kore')
        speaker2_voice = data.get('speaker2_voice', 'Puck')
        language_code = data.get('language', 'en')
        model = data.get('model', 'gemini-2.5-flash-preview-tts')

        if not url or not api_key:
            return jsonify({'error': '缺少必要參數'}), 400

        # 初始化 client
        client = genai.Client(api_key=api_key)

        # Step 1: 抓取網頁
        webpage_content = fetch_webpage(url)

        # Step 2: 生成對話
        conversation = generate_conversation_from_content(
            client, webpage_content, speaker1_name, speaker2_name, language_code
        )

        # Step 3: 生成 TTS
        prompt = f"TTS the following conversation between {speaker1_name} and {speaker2_name}:\n{conversation}"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker=speaker1_name,
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=speaker1_voice,
                                    )
                                )
                            ),
                            types.SpeakerVoiceConfig(
                                speaker=speaker2_name,
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=speaker2_voice,
                                    )
                                )
                            ),
                        ]
                    )
                )
            )
        )

        # 提取音頻數據
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = session.get('username', 'user')
        file_name = f"tts_{username}_{timestamp}.wav"
        file_path = os.path.join('static', 'audio', file_name)

        # 確保目錄存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 保存文件
        wave_file_to_path(file_path, audio_data)

        return jsonify({
            'success': True,
            'conversation': conversation,
            'webpage_content': webpage_content[:1000],
            'audio_file': file_name,
            'audio_url': f'/static/audio/{file_name}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/generate-manual', methods=['POST'])
def tts_generate_manual():
    """手動輸入對話生成音頻"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not GEMINI_AVAILABLE:
        return jsonify({'error': 'Gemini API not available'}), 500

    try:
        data = request.json
        conversation = data.get('conversation')
        api_key = data.get('api_key')
        speaker1_name = data.get('speaker1_name', 'Joe')
        speaker2_name = data.get('speaker2_name', 'Jane')
        speaker1_voice = data.get('speaker1_voice', 'Kore')
        speaker2_voice = data.get('speaker2_voice', 'Puck')
        model = data.get('model', 'gemini-2.5-flash-preview-tts')

        if not conversation or not api_key:
            return jsonify({'error': '缺少必要參數'}), 400

        # 初始化 client
        client = genai.Client(api_key=api_key)

        # 生成 TTS
        prompt = f"TTS the following conversation between {speaker1_name} and {speaker2_name}:\n{conversation}"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker=speaker1_name,
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=speaker1_voice,
                                    )
                                )
                            ),
                            types.SpeakerVoiceConfig(
                                speaker=speaker2_name,
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=speaker2_voice,
                                    )
                                )
                            ),
                        ]
                    )
                )
            )
        )

        # 提取音頻數據
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = session.get('username', 'user')
        file_name = f"tts_manual_{username}_{timestamp}.wav"
        file_path = os.path.join('static', 'audio', file_name)

        # 確保目錄存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 保存文件
        wave_file_to_path(file_path, audio_data)

        return jsonify({
            'success': True,
            'audio_file': file_name,
            'audio_url': f'/static/audio/{file_name}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 確保 Supabase 連接成功
    try:
        from supabase_utils import get_supabase_client
        supabase = get_supabase_client()
        print("✓ Supabase 連接成功")
    except Exception as e:
        print(f"✗ Supabase 連接失敗: {e}")
        print("請確保 .env 中已設置 SUPABASE_URL 和 SUPABASE_ANON_KEY")
        sys.exit(1)

    # 確保靜態文件目錄存在
    os.makedirs('static/audio', exist_ok=True)

    print("\n" + "=" * 50)
    print("正在啟動所有服務...")
    print("=" * 50)

    # 啟動所有子服務
    start_web_app()
    start_web_app22()

    print("\n" + "=" * 50)
    print("所有服務已啟動：")
    print("  - 用戶系統: http://localhost:8080")
    print("  - 韓文新聞: http://localhost:5000 (代理: /korean-app)")
    print("  - 中文詞彙: http://localhost:5001 (代理: /chinese-app)")
    print("  - Gemini TTS: http://localhost:8080/tts (Flask 內建)")
    print("=" * 50)
    print("\n按 Ctrl+C 停止所有服務\n")

    try:
        app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)
    finally:
        stop_all_services()
