"""
Flask 版本的 Gemini TTS Generator
模仿 web_app.py 的架構，使用 Flask + 純前端 HTML/JS
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
from google import genai
from google.genai import types
import wave
import io
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import threading
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 全域變數儲存處理狀態
processing_status = {}

# Available voice options
VOICE_OPTIONS = ["Kore", "Puck", "Charon", "Fenrir", "Aoede"]

# Language options
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

def create_wave_file(pcm, channels=1, rate=24000, sample_width=2):
    """Create WAV file in memory"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    buffer.seek(0)
    return buffer

def fetch_webpage(url):
    """Fetch and convert webpage to markdown"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Convert to markdown
        markdown_content = md(str(soup), heading_style="ATX")

        # Limit content length
        if len(markdown_content) > 10000:
            markdown_content = markdown_content[:10000]

        return markdown_content
    except Exception as e:
        raise Exception(f"Failed to fetch webpage: {str(e)}")

def generate_conversation_from_content(api_key, content, speaker1_name, speaker2_name, language_code='en'):
    """Use Gemini to analyze content and generate a conversation"""
    try:
        client = genai.Client(api_key=api_key)

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

        return response.text.strip()
    except Exception as e:
        raise Exception(f"Failed to generate conversation: {str(e)}")

def generate_tts_audio(api_key, conversation, speaker1_name, speaker2_name,
                       speaker1_voice, speaker2_voice, model):
    """Generate TTS audio from conversation"""
    try:
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

        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        return audio_data
    except Exception as e:
        raise Exception(f"Failed to generate audio: {str(e)}")

def process_tts_generation(process_id, url, conversation_text, api_key, speaker1_name, speaker2_name,
                          speaker1_voice, speaker2_voice, language, model, mode):
    """背景處理 TTS 生成"""
    try:
        # Step 1: 抓取網頁或使用手動輸入
        if mode == 'url':
            processing_status[process_id] = {
                'status': 'processing',
                'message': '📥 Step 1/3: 正在抓取網頁內容...',
                'progress': 10
            }
            content = fetch_webpage(url)
            processing_status[process_id] = {
                'status': 'processing',
                'message': '✅ Step 1/3: 網頁內容抓取完成',
                'progress': 20
            }
        else:
            content = conversation_text
            processing_status[process_id] = {
                'status': 'processing',
                'message': '📝 Step 1/2: 正在準備對話內容...',
                'progress': 20
            }

        # Step 2: 如果是 URL 模式，生成對話
        if mode == 'url':
            processing_status[process_id] = {
                'status': 'processing',
                'message': '🤖 Step 2/3: 正在使用 AI 生成對話...',
                'progress': 30
            }
            conversation = generate_conversation_from_content(
                api_key, content, speaker1_name, speaker2_name, language
            )
            processing_status[process_id] = {
                'status': 'processing',
                'message': '✅ Step 2/3: AI 對話生成完成',
                'progress': 50
            }
        else:
            conversation = content

        # Step 3: 生成 TTS 音頻
        if mode == 'url':
            processing_status[process_id] = {
                'status': 'processing',
                'message': '🎵 Step 3/3: 正在生成語音音頻（這可能需要一些時間）...',
                'progress': 60
            }
        else:
            processing_status[process_id] = {
                'status': 'processing',
                'message': '🎵 Step 2/2: 正在生成語音音頻（這可能需要一些時間）...',
                'progress': 50
            }

        audio_data = generate_tts_audio(
            api_key, conversation, speaker1_name, speaker2_name,
            speaker1_voice, speaker2_voice, model
        )

        # Step 4: 儲存音頻檔案
        processing_status[process_id] = {
            'status': 'processing',
            'message': '💾 正在儲存音頻檔案...',
            'progress': 90
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tts_{timestamp}.wav"
        filepath = os.path.join('static', filename)

        # 確保 static 目錄存在
        os.makedirs('static', exist_ok=True)

        # 儲存檔案
        audio_buffer = create_wave_file(audio_data)
        with open(filepath, 'wb') as f:
            f.write(audio_buffer.read())

        # 完成
        processing_status[process_id] = {
            'status': 'completed',
            'message': '🎉 所有步驟完成！語音已成功生成！',
            'progress': 100,
            'filename': filename,
            'conversation': conversation,
            'content_preview': content[:500] + '...' if mode == 'url' and len(content) > 500 else (content if mode == 'url' else None)
        }

    except Exception as e:
        processing_status[process_id] = {
            'status': 'error',
            'message': f'處理失敗: {str(e)}'
        }

# ==================== Routes ====================

@app.route('/tts')
def tts_page():
    """TTS 主頁面"""
    return render_template('tts_flask.html')

@app.route('/tts/process', methods=['POST'])
def process_tts():
    """開始處理 TTS 生成"""
    try:
        data = request.json

        # 取得參數
        url = data.get('url', '')
        conversation_text = data.get('conversation', '')
        api_key = data.get('api_key', os.getenv('GEMINI_API_KEY'))
        speaker1_name = data.get('speaker1_name', 'Joe')
        speaker2_name = data.get('speaker2_name', 'Jane')
        speaker1_voice = data.get('speaker1_voice', 'Kore')
        speaker2_voice = data.get('speaker2_voice', 'Puck')
        language = data.get('language', 'en')
        model = data.get('model', 'gemini-2.5-flash-preview-tts')
        mode = data.get('mode', 'url')  # 'url' or 'manual'

        # 驗證輸入
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        if mode == 'url' and not url:
            return jsonify({'error': 'URL is required in URL mode'}), 400

        if mode == 'manual' and not conversation_text:
            return jsonify({'error': 'Conversation text is required in manual mode'}), 400

        # 生成處理 ID
        process_id = str(uuid.uuid4())

        # 初始化狀態
        processing_status[process_id] = {
            'status': 'processing',
            'message': '開始處理...',
            'progress': 0
        }

        # 在背景執行處理
        thread = threading.Thread(
            target=process_tts_generation,
            args=(process_id, url, conversation_text, api_key, speaker1_name, speaker2_name,
                  speaker1_voice, speaker2_voice, language, model, mode)
        )
        thread.start()

        return jsonify({
            'process_id': process_id,
            'message': 'Processing started'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tts/status/<process_id>')
def get_tts_status(process_id):
    """取得處理狀態"""
    status = processing_status.get(process_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/tts/download/<filename>')
def download_tts_audio(filename):
    """下載音頻檔案"""
    try:
        filepath = os.path.join('static', filename)
        return send_file(filepath, mimetype='audio/wav', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/tts/play/<filename>')
def play_tts_audio(filename):
    """播放音頻檔案（用於 audio player）"""
    try:
        filepath = os.path.join('static', filename)
        return send_file(filepath, mimetype='audio/wav')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
