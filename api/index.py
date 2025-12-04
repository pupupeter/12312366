"""
Vercel Serverless Function - 僅包含 TTS 功能
簡化版本，移除所有需要子進程的功能
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import hashlib
import os
from datetime import datetime
import requests
import io
import wave
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# 導入 Supabase 工具
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase_utils import (
    get_user_by_username,
    create_user,
    update_last_login
)

from translations import get_translation

# Gemini TTS
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_AS_ASCII'] = False

# TTS 配置
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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def fetch_webpage(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        markdown_content = md(str(soup), heading_style="ATX")
        if len(markdown_content) > 10000:
            markdown_content = markdown_content[:10000]
        return markdown_content
    except Exception as e:
        raise Exception(f"Failed to fetch webpage: {str(e)}")

def generate_conversation_from_content(client, content, speaker1_name, speaker2_name, language_code='en'):
    try:
        language_instructions = {
            'en': 'in English', 'zh-cn': 'in Simplified Chinese (简体中文)',
            'zh-tw': 'in Traditional Chinese (繁體中文)', 'ko': 'in Korean (한국어)',
            'ja': 'in Japanese (日本語)', 'es': 'in Spanish (Español)',
            'fr': 'in French (Français)', 'de': 'in German (Deutsch)',
            'it': 'in Italian (Italiano)', 'pt': 'in Portuguese (Português)',
            'ru': 'in Russian (Русский)', 'ar': 'in Arabic (العربية)',
            'th': 'in Thai (ไทย)', 'vi': 'in Vietnamese (Tiếng Việt)',
            'id': 'in Indonesian (Bahasa Indonesia)', 'hi': 'in Hindi (हिन्दी)'
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

        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Failed to generate conversation: {str(e)}")

def wave_file_to_buffer(pcm, channels=1, rate=24000, sample_width=2):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    buffer.seek(0)
    return buffer

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
    if user and user['password'] == hash_password(password):
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

    result = create_user(username, hash_password(password), email)

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

# ==================== TTS 路由 ====================

@app.route('/tts')
def tts_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('tts_main.html',
                         username=session.get('username'),
                         voices=VOICE_OPTIONS,
                         languages=LANGUAGE_OPTIONS)

@app.route('/api/tts/generate-from-url', methods=['POST'])
def tts_generate_from_url():
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

        # 將音頻轉為 base64 直接返回（避免文件系統問題）
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            'success': True,
            'conversation': conversation,
            'webpage_content': webpage_content[:1000],
            'audio_data': audio_base64
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/generate-manual', methods=['POST'])
def tts_generate_manual():
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

        # 將音頻轉為 base64
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            'success': True,
            'audio_data': audio_base64
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel handler - WSGI 應用入口
app.debug = False

# 這是 Vercel 需要的應用對象
application = app
