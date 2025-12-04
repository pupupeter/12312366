"""
Railway 部署應用 - 整合韓文和中文知識圖譜系統
包含：韓文新聞、中文詞彙、收藏單字、複習遊戲
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
import hashlib
import os
from datetime import datetime
import requests
import re
import urllib.parse
import threading
import time
import json
from translations import get_translation
from korean_analysis import generate_graph_html
from chinese_analysis import generate_chinese_graph_html
from tocfl_loader import get_tocfl_vocab

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
from markdownify import markdownify

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

# 處理狀態追蹤
processing_status = {}

# ==================== AI Agent 初始化 ====================

# 訪問網頁工具
class VisitWebpageTool(Tool):
    name = "visit_webpage"
    description = "Fetches webpage content as Markdown."
    inputs = {"url": {"type": "string", "description": "The URL to visit."}}
    output_type = "string"

    def forward(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            markdown_content = markdownify(response.text).strip()
            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
            return markdown_content[:10000]  # 限制長度
        except requests.exceptions.Timeout:
            return "Request timed out. Try again later."
        except requests.exceptions.RequestException as e:
            return f"Error fetching the webpage: {str(e)}"

# 韓文分詞翻譯工具
class KoreanWordAnalysisTool(Tool):
    name = "korean_word_analysis"
    description = "Analyzes Korean text: tokenizes, translates, provides definitions and example sentences."
    inputs = {"text": {"type": "string", "description": "Korean text to analyze."}}
    output_type = "string"

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    def forward(self, text: str) -> str:
        prompt = f"""
請對以下韓文新聞內容進行詳細分析：

1. 首先進行分詞，找出所有重要的詞彙（名詞、動詞、形容詞等），忽略無關的標點符號和格式
2. 只提取韓文詞彙，忽略英文、數字等
3. 對每個詞彙提供以下資訊：
   - 韓文原文
   - 中文翻譯
   - 中文定義/解釋
   - 韓文例句（使用該詞彙的簡單例句）
   - 例句的中文翻譯

請以JSON格式輸出，結構如下：
[
  {{
    "korean": "韓文詞彙",
    "chinese": "中文翻譯",
    "definition": "中文定義解釋",
    "example_korean": "韓文例句",
    "example_chinese": "例句中文翻譯"
  }}
]

韓文新聞內容：
{text}
"""
        messages = [{"role": "user", "content": prompt}]
        response = self.model(messages)
        return response.content if hasattr(response, 'content') else str(response)

# 韓文新聞工具（保留原有的 Naver API 工具）
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

# 中文分詞翻譯工具
class ChineseWordAnalysisTool(Tool):
    name = "chinese_word_analysis"
    description = "Analyzes Chinese text: tokenizes, provides pinyin, definitions and example sentences."
    inputs = {"text": {"type": "string", "description": "Chinese text to analyze."}}
    output_type = "string"

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    def forward(self, text: str) -> str:
        prompt = f"""
請對以下中文內容進行詳細分析：

1. 首先進行分詞，找出所有重要的詞彙（名詞、動詞、形容詞等），忽略無關的標點符號和格式
2. 只提取中文詞彙，忽略英文、數字等
3. 對每個詞彙提供以下資訊：
   - 中文原文
   - 拼音（漢語拼音）
   - 中文定義/解釋
   - 中文例句（使用該詞彙的簡單例句）

請以JSON格式輸出，結構如下：
[
  {{
    "chinese": "中文詞彙",
    "pinyin": "漢語拼音",
    "definition": "中文定義解釋",
    "example": "中文例句"
  }}
]

中文內容：
{text}
"""
        messages = [{"role": "user", "content": prompt}]
        response = self.model(messages)
        return response.content if hasattr(response, 'content') else str(response)

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
@app.route('/korean/api/saved-words', methods=['GET'])
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
@app.route('/korean/api/saved-words/<korean>', methods=['DELETE'])
def delete_korean_word_route(korean=None):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])

    # 支援兩種方式：POST 的 JSON body 或 DELETE 的 URL 參數
    if korean is None:
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

# 韓文新聞分析路由
@app.route('/korean/process', methods=['POST'])
def korean_process():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    url = data.get('url')
    text = data.get('text')
    input_type = data.get('type', 'url')

    if not url and not text:
        return jsonify({'error': '請提供網址或純文字'}), 400

    # 生成唯一的處理ID
    process_id = str(int(time.time() * 1000))
    processing_status[process_id] = {
        'status': 'processing',
        'message': '正在處理中...',
        'progress': 0
    }

    # 在背景執行處理
    if input_type == 'text' and text:
        thread = threading.Thread(target=process_text_analysis, args=(text, process_id))
    else:
        if not url.startswith('http'):
            url = 'https://' + url
        thread = threading.Thread(target=process_korean_url_analysis, args=(url, process_id))
    thread.start()

    return jsonify({'process_id': process_id})

@app.route('/korean/status/<process_id>')
def korean_status(process_id):
    status = processing_status.get(process_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/korean/result/<filename>')
def korean_result(filename):
    try:
        return send_file(filename, as_attachment=False, mimetype='text/html; charset=utf-8')
    except FileNotFoundError:
        return jsonify({'error': '文件未找到'}), 404

def process_text_analysis(text, process_id):
    """處理純文字輸入的韓文分析"""
    try:
        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在初始化AI模型...',
            'progress': 10
        }

        model = LiteLLMModel(model_id="gemini/gemini-2.0-flash", token=os.getenv("GEMINI_API_KEY"))
        korean_tool = KoreanWordAnalysisTool(model=model)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在進行韓文詞彙分析...',
            'progress': 40
        }

        content = text[:10000]
        words_json_str = korean_tool.forward(content)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在解析分析結果...',
            'progress': 70
        }

        # 解析JSON
        cleaned_json = words_json_str.strip()
        start_idx = cleaned_json.find('[')
        end_idx = cleaned_json.rfind(']')

        if start_idx != -1 and end_idx != -1:
            json_part = cleaned_json[start_idx:end_idx+1]
            words = json.loads(json_part)

            processing_status[process_id] = {
                'status': 'processing',
                'message': '正在生成知識圖譜...',
                'progress': 90
            }

            html_content = generate_graph_html(words, '純文字輸入')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"korean_graph_{len(words)}words_{timestamp}.html"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            processing_status[process_id] = {
                'status': 'completed',
                'message': f'成功生成 {len(words)} 個韓文詞彙的知識圖譜',
                'progress': 100,
                'filename': filename,
                'word_count': len(words)
            }
        else:
            raise ValueError("無法找到有效的JSON數組")

    except Exception as e:
        processing_status[process_id] = {
            'status': 'error',
            'message': f'處理失敗: {str(e)}'
        }

def process_korean_url_analysis(url, process_id):
    """處理URL輸入的韓文分析"""
    try:
        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在初始化AI模型...',
            'progress': 10
        }

        model = LiteLLMModel(model_id="gemini/gemini-2.0-flash", token=os.getenv("GEMINI_API_KEY"))
        visit_tool = VisitWebpageTool()
        korean_tool = KoreanWordAnalysisTool(model=model)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在抓取網頁內容...',
            'progress': 30
        }

        content = visit_tool.forward(url)
        if content.startswith("Request timed out") or content.startswith("Error"):
            processing_status[process_id] = {
                'status': 'error',
                'message': f'抓取網頁失敗: {content}'
            }
            return

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在進行韓文詞彙分析...',
            'progress': 60
        }

        words_json_str = korean_tool.forward(content)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在解析分析結果...',
            'progress': 80
        }

        # 解析JSON
        cleaned_json = words_json_str.strip()
        start_idx = cleaned_json.find('[')
        end_idx = cleaned_json.rfind(']')

        if start_idx != -1 and end_idx != -1:
            json_part = cleaned_json[start_idx:end_idx+1]
            words = json.loads(json_part)

            processing_status[process_id] = {
                'status': 'processing',
                'message': '正在生成知識圖譜...',
                'progress': 90
            }

            html_content = generate_graph_html(words, url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"korean_graph_{len(words)}words_{timestamp}.html"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            processing_status[process_id] = {
                'status': 'completed',
                'message': f'成功生成 {len(words)} 個韓文詞彙的知識圖譜',
                'progress': 100,
                'filename': filename,
                'word_count': len(words)
            }
        else:
            raise ValueError("無法找到有效的JSON數組")

    except Exception as e:
        processing_status[process_id] = {
            'status': 'error',
            'message': f'處理失敗: {str(e)}'
        }

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
@app.route('/chinese/api/saved-words', methods=['GET'])
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
@app.route('/chinese/api/saved-words/<chinese>', methods=['DELETE'])
def delete_chinese_word_route(chinese=None):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session.get('user_id', session['username'])
    if chinese is None:
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

# 中文文章分析路由
@app.route('/chinese/process', methods=['POST'])
def chinese_process():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    url = data.get('url')
    text = data.get('text')
    input_type = data.get('type', 'url')

    if not url and not text:
        return jsonify({'error': '請提供網址或純文字'}), 400

    # 生成唯一的處理ID
    process_id = str(int(time.time() * 1000))
    processing_status[process_id] = {
        'status': 'processing',
        'message': '正在處理中...',
        'progress': 0
    }

    # 在背景執行處理
    if input_type == 'text' and text:
        thread = threading.Thread(target=process_chinese_text_analysis, args=(text, process_id))
    else:
        if not url.startswith('http'):
            url = 'https://' + url
        thread = threading.Thread(target=process_chinese_url_analysis, args=(url, process_id))
    thread.start()

    return jsonify({'process_id': process_id})

@app.route('/chinese/status/<process_id>')
def chinese_status(process_id):
    status = processing_status.get(process_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/chinese/result/<filename>')
def chinese_result(filename):
    try:
        return send_file(filename, as_attachment=False, mimetype='text/html; charset=utf-8')
    except FileNotFoundError:
        return jsonify({'error': '文件未找到'}), 404

def process_chinese_text_analysis(text, process_id):
    """處理純文字輸入的中文分析"""
    try:
        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在初始化AI模型...',
            'progress': 10
        }

        model = LiteLLMModel(model_id="gemini/gemini-2.0-flash", token=os.getenv("GEMINI_API_KEY"))
        chinese_tool = ChineseWordAnalysisTool(model=model)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在進行中文詞彙分析...',
            'progress': 40
        }

        content = text[:10000]
        words_json_str = chinese_tool.forward(content)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在解析分析結果...',
            'progress': 70
        }

        # 解析JSON
        cleaned_json = words_json_str.strip()
        start_idx = cleaned_json.find('[')
        end_idx = cleaned_json.rfind(']')

        if start_idx != -1 and end_idx != -1:
            json_part = cleaned_json[start_idx:end_idx+1]
            words = json.loads(json_part)

            processing_status[process_id] = {
                'status': 'processing',
                'message': '正在添加 TOCFL 級數...',
                'progress': 85
            }

            # 添加 TOCFL 級數
            tocfl = get_tocfl_vocab()
            for word in words:
                chinese = word.get('chinese', '')
                tocfl_level = tocfl.get_level_display(chinese)
                word['tocfl_level'] = tocfl_level if tocfl_level else '未分級'

            processing_status[process_id] = {
                'status': 'processing',
                'message': '正在生成知識圖譜...',
                'progress': 90
            }

            html_content = generate_chinese_graph_html(words, '純文字輸入')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chinese_graph_{len(words)}words_{timestamp}.html"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            processing_status[process_id] = {
                'status': 'completed',
                'message': f'成功生成 {len(words)} 個中文詞彙的知識圖譜',
                'progress': 100,
                'filename': filename,
                'word_count': len(words)
            }
        else:
            raise ValueError("無法找到有效的JSON數組")

    except Exception as e:
        processing_status[process_id] = {
            'status': 'error',
            'message': f'處理失敗: {str(e)}'
        }

def process_chinese_url_analysis(url, process_id):
    """處理URL輸入的中文分析"""
    try:
        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在初始化AI模型...',
            'progress': 10
        }

        model = LiteLLMModel(model_id="gemini/gemini-2.0-flash", token=os.getenv("GEMINI_API_KEY"))
        visit_tool = VisitWebpageTool()
        chinese_tool = ChineseWordAnalysisTool(model=model)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在抓取網頁內容...',
            'progress': 30
        }

        content = visit_tool.forward(url)
        if content.startswith("Request timed out") or content.startswith("Error"):
            processing_status[process_id] = {
                'status': 'error',
                'message': f'抓取網頁失敗: {content}'
            }
            return

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在進行中文詞彙分析...',
            'progress': 60
        }

        words_json_str = chinese_tool.forward(content)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在解析分析結果...',
            'progress': 80
        }

        # 解析JSON
        cleaned_json = words_json_str.strip()
        start_idx = cleaned_json.find('[')
        end_idx = cleaned_json.rfind(']')

        if start_idx != -1 and end_idx != -1:
            json_part = cleaned_json[start_idx:end_idx+1]
            words = json.loads(json_part)

            processing_status[process_id] = {
                'status': 'processing',
                'message': '正在添加 TOCFL 級數...',
                'progress': 85
            }

            # 添加 TOCFL 級數
            tocfl = get_tocfl_vocab()
            for word in words:
                chinese = word.get('chinese', '')
                tocfl_level = tocfl.get_level_display(chinese)
                word['tocfl_level'] = tocfl_level if tocfl_level else '未分級'

            processing_status[process_id] = {
                'status': 'processing',
                'message': '正在生成知識圖譜...',
                'progress': 90
            }

            html_content = generate_chinese_graph_html(words, url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chinese_graph_{len(words)}words_{timestamp}.html"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            processing_status[process_id] = {
                'status': 'completed',
                'message': f'成功生成 {len(words)} 個中文詞彙的知識圖譜',
                'progress': 100,
                'filename': filename,
                'word_count': len(words)
            }
        else:
            raise ValueError("無法找到有效的JSON數組")

    except Exception as e:
        processing_status[process_id] = {
            'status': 'error',
            'message': f'處理失敗: {str(e)}'
        }

# ==================== 遊戲系統 ====================

@app.route('/games')
def games_menu():
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

    return render_template('games/menu.html', username=username)

@app.route('/games/matching')
def games_matching():
    if 'username' not in session:
        username_param = request.args.get('user')
        if username_param:
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True
        else:
            return redirect(url_for('login'))
    return render_template('games/matching.html', username=session['username'])

@app.route('/games/typing')
def games_typing():
    if 'username' not in session:
        username_param = request.args.get('user')
        if username_param:
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True
        else:
            return redirect(url_for('login'))
    return render_template('games/typing.html', username=session['username'])

@app.route('/games/listening')
def games_listening():
    if 'username' not in session:
        username_param = request.args.get('user')
        if username_param:
            session['username'] = username_param
            session['user_id'] = username_param
            session.permanent = True
        else:
            return redirect(url_for('login'))
    return render_template('games/listening.html', username=session['username'])

# ==================== 健康檢查 ====================

@app.route('/health')
def health():
    gemini_key = os.getenv("GEMINI_API_KEY")
    return jsonify({
        'status': 'healthy',
        'agents_available': AGENTS_AVAILABLE,
        'korean_agent': korean_agent is not None,
        'chinese_agent': chinese_agent is not None,
        'gemini_key_exists': gemini_key is not None,
        'gemini_key_length': len(gemini_key) if gemini_key else 0,
        'gemini_key_preview': gemini_key[:10] + '...' if gemini_key else 'NOT SET'
    })

# ==================== 啟動應用 ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
