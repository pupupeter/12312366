"""
Gemini TTS Flask 應用
使用 Supabase 認證的 Flask 版本 TTS 服務
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import os
import wave
import requests
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import hashlib
import io

# 載入環境變數
load_dotenv()

# Supabase 用戶操作
from supabase_utils import (
    get_user_by_username,
    create_user,
    update_last_login
)

# Gemini TTS 相關
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-genai not installed")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# 語言選項
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

# 聲音選項
VOICE_OPTIONS = ["Kore", "Puck", "Charon", "Fenrir", "Aoede"]

# 密碼加密
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 檢查登入狀態
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Wave 文件保存
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """保存 PCM 音頻數據到 WAV 文件"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# 抓取網頁內容
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

# 使用 Gemini 生成對話
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

# ==================== 路由 ====================

@app.route('/')
def index():
    """主頁：重定向到登入或 TTS 頁面"""
    if 'username' in session:
        return redirect(url_for('tts'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登入頁面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('tts_login.html', error='請輸入帳號和密碼')

        user = get_user_by_username(username)
        if user and user.get('password') == hash_password(password):
            # 登入成功
            session['username'] = username
            session['user_id'] = user.get('id')
            update_last_login(username)
            return redirect(url_for('tts'))
        else:
            return render_template('tts_login.html', error='帳號或密碼錯誤')

    return render_template('tts_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """註冊頁面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email', '')

        # 驗證
        if not username or not password:
            return render_template('tts_register.html', error='帳號和密碼不能為空')

        if len(password) < 6:
            return render_template('tts_register.html', error='密碼長度至少需要 6 個字元')

        if password != password_confirm:
            return render_template('tts_register.html', error='兩次輸入的密碼不一致')

        # 創建用戶
        result = create_user(username, hash_password(password), email)

        if result.get('success'):
            return render_template('tts_register.html', success='註冊成功！請登入')
        else:
            error = result.get('error', 'unknown')
            if error == 'username_exists':
                return render_template('tts_register.html', error='帳號已存在')
            elif error == 'email_exists':
                return render_template('tts_register.html', error='Email 已被使用')
            else:
                return render_template('tts_register.html', error=f'註冊失敗: {error}')

    return render_template('tts_register.html')

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/tts')
@login_required
def tts():
    """TTS 主頁面"""
    return render_template('tts_main.html',
                         username=session.get('username'),
                         voices=VOICE_OPTIONS,
                         languages=LANGUAGE_OPTIONS)

# ==================== API 路由 ====================

@app.route('/api/generate-from-url', methods=['POST'])
@login_required
def generate_from_url():
    """從 URL 生成對話和音頻"""
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
        model = data.get('model', 'gemini-3.8-flash-lite-tts')

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
        wave_file(file_path, audio_data)

        return jsonify({
            'success': True,
            'conversation': conversation,
            'webpage_content': webpage_content[:1000],
            'audio_file': file_name,
            'audio_url': f'/static/audio/{file_name}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-manual', methods=['POST'])
@login_required
def generate_manual():
    """手動輸入對話生成音頻"""
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
        model = data.get('model', 'gemini-3.8-flash-lite-tts')

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
        wave_file(file_path, audio_data)

        return jsonify({
            'success': True,
            'audio_file': file_name,
            'audio_url': f'/static/audio/{file_name}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 確保靜態文件目錄存在
    os.makedirs('static/audio', exist_ok=True)

    print("\n" + "="*50)
    print("🎙️  Gemini TTS Flask 應用")
    print("="*50)
    print(f"✓ 使用 Supabase 認證")
    print(f"✓ Gemini API: {'可用' if GEMINI_AVAILABLE else '不可用'}")
    print(f"✓ 應用運行在: http://localhost:8502")
    print("="*50 + "\n")

    app.run(host='0.0.0.0', port=8502, debug=True)
