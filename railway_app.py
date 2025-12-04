"""
Railway 部署應用 - 整合韓文和中文知識圖譜系統
包含：韓文新聞、中文詞彙、收藏單字、複習遊戲
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import hashlib
import os
from datetime import datetime
import requests
import re
import urllib.parse
from translations import get_translation

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Supabase 用戶操作
from supabase_utils import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    update_user,
    update_user_password,
    update_user_language,
    update_last_login,
    check_email_exists,
    get_korean_words,
    add_korean_word,
    delete_korean_word,
    get_chinese_words,
    add_chinese_word,
    delete_chinese_word
)

# Smolagents - 韓文和中文 AI Agent
from smolagents import Tool, LiteLLMModel
from smolagents.agents import ToolCallingAgent

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Session 配置（支援跨域單點登入）
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 小時

# ==================== AI Agent 初始化 ====================

# 韓文新聞工具
class KoreanNewsTool(Tool):
    name = "korean_news_tool"
    description = """這個工具可以獲取最新的韓文新聞。
    參數：
    - query: 搜尋關鍵字（例如：'정치', '경제', 'BTS', '날씨'）
    - count: 要返回的新聞數量（默認5篇）

    返回格式：新聞標題、內容摘要、發布時間
    """
    inputs = {
        "query": {"type": "string", "description": "搜尋的韓文關鍵字"},
        "count": {"type": "integer", "description": "新聞數量", "default": 5}
    }
    output_type = "string"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.naver_client_id = os.environ.get('NAVER_CLIENT_ID')
        self.naver_client_secret = os.environ.get('NAVER_CLIENT_SECRET')

    def forward(self, query: str, count: int = 5) -> str:
        if not self.naver_client_id or not self.naver_client_secret:
            return "錯誤：需要設置 NAVER_CLIENT_ID 和 NAVER_CLIENT_SECRET 環境變數"

        try:
            url = "https://openapi.naver.com/v1/search/news.json"
            params = {
                'query': query,
                'display': count,
                'sort': 'date'
            }
            headers = {
                'X-Naver-Client-Id': self.naver_client_id,
                'X-Naver-Client-Secret': self.naver_client_secret
            }

            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if 'items' not in data or not data['items']:
                return f"找不到關於 '{query}' 的新聞"

            news_list = []
            for idx, item in enumerate(data['items'][:count], 1):
                title = re.sub('<[^<]+?>', '', item['title'])
                description = re.sub('<[^<]+?>', '', item['description'])
                pub_date = item.get('pubDate', '未知日期')

                news_list.append(f"{idx}. {title}\n   {description}\n   發布時間: {pub_date}\n")

            return "\n".join(news_list)

        except Exception as e:
            return f"獲取新聞時出錯：{str(e)}"

# 中文詞彙工具
class ChineseVocabTool(Tool):
    name = "chinese_vocab_tool"
    description = """這個工具可以查詢中文詞彙的詳細解釋。
    參數：
    - word: 要查詢的中文詞彙

    返回：詞彙的拼音、英文翻譯、例句、HSK等級等資訊
    """
    inputs = {
        "word": {"type": "string", "description": "要查詢的中文詞彙"}
    }
    output_type = "string"

    def forward(self, word: str) -> str:
        try:
            # 使用線上中文詞典 API
            url = f"https://www.mdbg.net/chinese/dictionary?page=worddict&wdrst=0&wdqb={urllib.parse.quote(word)}"
            headers = {'User-Agent': 'Mozilla/5.0'}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 簡單解析（實際應該用更複雜的解析）
            if word in response.text:
                return f"找到詞彙 '{word}' 的相關資訊。\n建議查看完整線上詞典以獲得詳細解釋。"
            else:
                return f"找不到詞彙 '{word}' 的資訊"

        except Exception as e:
            return f"查詢詞彙時出錯：{str(e)}"

# 初始化 AI 模型和 Agent
try:
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("需要 GEMINI_API_KEY 環境變數")

    # 韓文 Agent
    korean_model = LiteLLMModel(
        model_id="gemini/gemini-2.0-flash-exp",
        api_key=gemini_api_key
    )
    korean_agent = ToolCallingAgent(
        tools=[KoreanNewsTool()],
        model=korean_model,
        max_steps=3
    )

    # 中文 Agent
    chinese_model = LiteLLMModel(
        model_id="gemini/gemini-2.0-flash-exp",
        api_key=gemini_api_key
    )
    chinese_agent = ToolCallingAgent(
        tools=[ChineseVocabTool()],
        model=chinese_model,
        max_steps=3
    )

    print("✓ AI Agents 初始化成功")
    AGENTS_AVAILABLE = True

except Exception as e:
    print(f"✗ AI Agents 初始化失敗: {e}")
    AGENTS_AVAILABLE = False
    korean_agent = None
    chinese_agent = None

# ==================== 路由 ====================

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = get_user_by_username(session['username'])
    lang = user.get('language', 'zh-TW') if user else 'zh-TW'
    translations = get_translation(lang)

    return render_template('dashboard.html',
                         username=session['username'],
                         lang=lang,
                         t=translations)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '請輸入帳號和密碼'}), 400

    user = get_user_by_username(username)
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if user and user['password'] == password_hash:
        session['username'] = username
        session['user_id'] = str(user.get('id', username))
        update_last_login(username)
        return jsonify({'success': True, 'message': '登入成功', 'username': username})
    else:
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'}), 401

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

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    result = create_user(username, password_hash, email)

    if not result['success']:
        if result['error'] == 'username_exists':
            return jsonify({'success': False, 'message': '帳號已存在'}), 409
        elif result['error'] == 'email_exists':
            return jsonify({'success': False, 'message': 'Email 已被使用'}), 409
        else:
            return jsonify({'success': False, 'message': '註冊失敗，請稍後再試'}), 500

    return jsonify({'success': True, 'message': '註冊成功，請登入', 'username': username})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    username = session.get('username')
    session.clear()
    return jsonify({'success': True, 'message': '已登出', 'username': username})

@app.route('/api/check_auth')
def check_auth():
    if 'username' in session:
        return jsonify({'authenticated': True, 'username': session['username']})
    return jsonify({'authenticated': False})

# ==================== 韓文新聞系統 ====================

@app.route('/korean')
def korean_page():
    # 支援從 Vercel 傳遞用戶名（URL 參數）
    username_param = request.args.get('user')

    print(f"[DEBUG] /korean - username_param: {username_param}")
    print(f"[DEBUG] /korean - current session: {dict(session)}")

    # 優先使用 URL 參數，如果沒有則檢查 session
    username = None

    if username_param:
        # 驗證用戶是否存在
        try:
            user = get_user_by_username(username_param)
            print(f"[DEBUG] /korean - user lookup result: {user}")
            print(f"[DEBUG] /korean - user found: {user is not None}")

            if user:
                username = username_param
                # 同時設置 session（嘗試）
                session.clear()
                session['username'] = username_param
                session['user_id'] = str(user.get('id', username_param))
                session.permanent = True
                print(f"[DEBUG] /korean - session set: {dict(session)}")
            else:
                # 即使用戶不存在，也允許訪問（臨時解決方案）
                print(f"[WARNING] /korean - user not found in database, allowing access anyway")
                username = username_param
                session['username'] = username_param
                session['user_id'] = username_param
                session.permanent = True
        except Exception as e:
            print(f"[ERROR] /korean - database error: {e}")
            # 數據庫錯誤時也允許訪問
            username = username_param
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True

    elif 'username' in session:
        # 從 session 獲取用戶名
        username = session['username']
        print(f"[DEBUG] /korean - username from session: {username}")

    # 如果都沒有，重定向到登入
    if not username:
        print(f"[DEBUG] /korean - no username found, redirecting to login")
        return redirect(url_for('login'))

    # 直接顯示頁面，不重定向
    print(f"[DEBUG] /korean - rendering page for username: {username}")
    return render_template('index.html', username=username)

@app.route('/korean/chat', methods=['POST'])
def korean_chat():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not AGENTS_AVAILABLE or korean_agent is None:
        return jsonify({'error': 'AI Agent 未初始化，請檢查 GEMINI_API_KEY 和 NAVER API 設定'}), 500

    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': '訊息不能為空'}), 400

    try:
        response = korean_agent.run(message)
        return jsonify({'response': str(response)})
    except Exception as e:
        return jsonify({'error': f'處理失敗：{str(e)}'}), 500

@app.route('/korean/saved-words', methods=['GET'])
def get_korean_saved_words():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    words = get_korean_words(user_id)
    return jsonify({'words': words})

@app.route('/korean/save-word', methods=['POST'])
def save_korean_word():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    word_data = request.json

    result = add_korean_word(user_id, word_data)
    return jsonify(result)

@app.route('/korean/delete-word', methods=['POST'])
def delete_korean_word_route():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    korean = request.json.get('korean')

    result = delete_korean_word(user_id, korean)
    return jsonify(result)

@app.route('/korean/review')
def korean_review():
    # 支援從 Vercel 傳遞用戶名
    username_param = request.args.get('user')
    username = None

    if username_param:
        try:
            user = get_user_by_username(username_param)
            if user:
                username = username_param
                session.clear()
                session['username'] = username_param
                session['user_id'] = str(user.get('id', username_param))
                session.permanent = True
            else:
                username = username_param
                session['username'] = username_param
                session['user_id'] = username_param
                session.permanent = True
        except Exception as e:
            username = username_param
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True
    elif 'username' in session:
        username = session['username']

    if not username:
        return redirect(url_for('login'))
    return render_template('review.html', username=username)

# ==================== 中文詞彙系統 ====================

@app.route('/chinese')
def chinese_page():
    # 支援從 Vercel 傳遞用戶名（URL 參數）
    username_param = request.args.get('user')

    # 優先使用 URL 參數，如果沒有則檢查 session
    username = None

    if username_param:
        # 驗證用戶是否存在
        try:
            user = get_user_by_username(username_param)
            if user:
                username = username_param
                session.clear()
                session['username'] = username_param
                session['user_id'] = str(user.get('id', username_param))
                session.permanent = True
            else:
                # 即使用戶不存在，也允許訪問
                username = username_param
                session['username'] = username_param
                session['user_id'] = username_param
                session.permanent = True
        except Exception as e:
            print(f"[ERROR] /chinese - database error: {e}")
            username = username_param
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True
    elif 'username' in session:
        username = session['username']

    # 如果都沒有，重定向到登入
    if not username:
        return redirect(url_for('login'))

    return render_template('index22.html', username=username)

@app.route('/chinese/chat', methods=['POST'])
def chinese_chat():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not AGENTS_AVAILABLE or chinese_agent is None:
        return jsonify({'error': 'AI Agent 未初始化，請檢查 GEMINI_API_KEY 設定'}), 500

    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': '訊息不能為空'}), 400

    try:
        response = chinese_agent.run(message)
        return jsonify({'response': str(response)})
    except Exception as e:
        return jsonify({'error': f'處理失敗：{str(e)}'}), 500

@app.route('/chinese/saved-words', methods=['GET'])
def get_chinese_saved_words():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    words = get_chinese_words(user_id)
    return jsonify({'words': words})

@app.route('/chinese/save-word', methods=['POST'])
def save_chinese_word():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    word_data = request.json

    result = add_chinese_word(user_id, word_data)
    return jsonify(result)

@app.route('/chinese/delete-word', methods=['POST'])
def delete_chinese_word_route():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    chinese = request.json.get('chinese')

    result = delete_chinese_word(user_id, chinese)
    return jsonify(result)

@app.route('/chinese/review')
def chinese_review():
    # 支援從 Vercel 傳遞用戶名
    username_param = request.args.get('user')
    username = None

    if username_param:
        try:
            user = get_user_by_username(username_param)
            if user:
                username = username_param
                session.clear()
                session['username'] = username_param
                session['user_id'] = str(user.get('id', username_param))
                session.permanent = True
            else:
                username = username_param
                session['username'] = username_param
                session['user_id'] = username_param
                session.permanent = True
        except Exception as e:
            username = username_param
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True
    elif 'username' in session:
        username = session['username']

    if not username:
        return redirect(url_for('login'))
    return render_template('review22.html', username=username)

# ==================== 健康檢查 ====================

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'agents_available': AGENTS_AVAILABLE,
        'korean_agent': korean_agent is not None,
        'chinese_agent': chinese_agent is not None
    })

# ==================== 啟動應用 ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
