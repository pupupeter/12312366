"""
Vercel Serverless Function Entry Point
為 auth_app.py 創建無伺服器函數包裝器
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
import hashlib
import os
from datetime import datetime
import requests
import re
import urllib.parse
import io
import wave
import sys

# 添加父目錄到路徑以便導入模組
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

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

# ==================== 路由 ====================

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

    user = get_user_by_username(session['username'])
    lang = 'zh-TW'
    if user and user.get('language'):
        lang = user.get('language', 'zh-TW')

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

    user = get_user_by_username(username)

    if user and user['password'] == hash_password(password):
        session['username'] = username
        session['user_id'] = str(user.get('id', username))
        update_last_login(username)

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

# TTS 主頁面
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

        client = genai.Client(api_key=api_key)
        webpage_content = fetch_webpage(url)
        conversation = generate_conversation_from_content(
            client, webpage_content, speaker1_name, speaker2_name, language_code
        )

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

        audio_data = response.candidates[0].content.parts[0].inline_data.data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = session.get('username', 'user')
        file_name = f"tts_{username}_{timestamp}.wav"
        file_path = os.path.join('/tmp', file_name)

        wave_file_to_path(file_path, audio_data)

        return jsonify({
            'success': True,
            'conversation': conversation,
            'webpage_content': webpage_content[:1000],
            'audio_file': file_name,
            'audio_url': f'/api/tts/download/{file_name}'
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

        client = genai.Client(api_key=api_key)
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

        audio_data = response.candidates[0].content.parts[0].inline_data.data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = session.get('username', 'user')
        file_name = f"tts_manual_{username}_{timestamp}.wav"
        file_path = os.path.join('/tmp', file_name)

        wave_file_to_path(file_path, audio_data)

        return jsonify({
            'success': True,
            'audio_file': file_name,
            'audio_url': f'/api/tts/download/{file_name}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/download/<filename>')
def download_audio(filename):
    """下載音頻文件"""
    try:
        file_path = os.path.join('/tmp', filename)
        return send_file(file_path, mimetype='audio/wav', as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# Vercel 需要的處理函數
def handler(request):
    """Vercel serverless function handler"""
    with app.request_context(request.environ):
        return app.full_dispatch_request()

# 本地測試
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
