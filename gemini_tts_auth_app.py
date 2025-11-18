import streamlit as st
from google import genai
from google.genai import types
import wave
import os
from datetime import datetime
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pymongo import MongoClient
import hashlib

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Gemini TTS Generator - Auth",
    page_icon="🎙️",
    layout="wide"
)

# MongoDB connection
@st.cache_resource
def get_mongo_client():
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['local']
        collection = db['帳號密碼']
        # Test connection
        client.server_info()
        return collection
    except Exception as e:
        st.error(f"❌ MongoDB 連接失敗: {str(e)}")
        return None

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication functions
def login_user(username, password, collection):
    """Login user and return success status"""
    user = collection.find_one({'username': username})
    if user and user['password'] == hash_password(password):
        # Update last login
        collection.update_one(
            {'username': username},
            {'$set': {'last_login': datetime.now()}}
        )
        return True, user
    return False, None

def register_user(username, password, email, collection):
    """Register new user"""
    # Check if username exists
    if collection.find_one({'username': username}):
        return False, '帳號已存在'

    # Check if email exists
    if email and collection.find_one({'email': email}):
        return False, 'Email 已被使用'

    # Create new user
    new_user = {
        'username': username,
        'password': hash_password(password),
        'email': email,
        'created_at': datetime.now(),
        'last_login': None
    }

    collection.insert_one(new_user)
    return True, '註冊成功！'

# Initialize session state for auth
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# Wave file saving function
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM audio data to a WAV file"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# Fetch webpage content
def fetch_webpage(url):
    """Fetch and convert webpage to markdown"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Convert HTML to markdown
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

# Generate conversation from content using Gemini
def generate_conversation_from_content(client, content, speaker1_name, speaker2_name, language_code='en'):
    """Use Gemini 2.0 Flash to analyze content and generate a conversation in the specified language"""
    try:
        # Language-specific instructions
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

# Available voice options
VOICE_OPTIONS = [
    "Kore", "Puck", "Charon", "Fenrir", "Aoede"
]

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

# Authentication UI
def show_login_page():
    """Display login/register page"""
    st.title("🎙️ Gemini TTS Generator")
    st.markdown("### 請先登入使用")

    tab1, tab2 = st.tabs(["登入", "註冊"])

    collection = get_mongo_client()
    if collection is None:
        st.error("無法連接到資料庫，請確保 MongoDB 正在運行")
        return

    with tab1:
        st.subheader("登入")
        login_username = st.text_input("帳號", key="login_username")
        login_password = st.text_input("密碼", type="password", key="login_password")

        if st.button("登入", type="primary", use_container_width=True):
            if not login_username or not login_password:
                st.error("請輸入帳號和密碼")
            else:
                success, user = login_user(login_username, login_password, collection)
                if success:
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = login_username
                    st.session_state['user_id'] = str(user['_id'])
                    st.success(f"✅ 歡迎回來，{login_username}！")
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤")

    with tab2:
        st.subheader("註冊新帳號")
        reg_username = st.text_input("帳號", key="reg_username")
        reg_email = st.text_input("Email (選填)", key="reg_email")
        reg_password = st.text_input("密碼", type="password", key="reg_password")
        reg_password_confirm = st.text_input("確認密碼", type="password", key="reg_password_confirm")

        if st.button("註冊", type="primary", use_container_width=True):
            if not reg_username or not reg_password:
                st.error("帳號和密碼不能為空")
            elif len(reg_password) < 6:
                st.error("密碼長度至少需要 6 個字元")
            elif reg_password != reg_password_confirm:
                st.error("兩次輸入的密碼不一致")
            else:
                success, message = register_user(reg_username, reg_password, reg_email, collection)
                if success:
                    st.success(f"✅ {message}")
                    st.info("請切換到登入頁面進行登入")
                else:
                    st.error(f"❌ {message}")

# Main TTS app (shown after login)
def show_tts_app():
    """Display main TTS application"""

    # Header with logout button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🎙️ Gemini Multi-Speaker TTS Generator")
        st.markdown(f"歡迎，**{st.session_state['username']}**！")
    with col2:
        st.write("")  # Spacing
        if st.button("🚪 登出", use_container_width=True):
            st.session_state['authenticated'] = False
            st.session_state['username'] = None
            st.session_state['user_id'] = None
            st.rerun()

    st.markdown("Generate realistic conversations using Google's Gemini TTS with multiple speakers")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            value=os.environ.get("GEMINI_API_KEY", ""),
            type="password",
            help="Enter your Gemini API key or set it in .env file"
        )

        st.divider()

        # Language selection
        st.subheader("🌍 Language Settings")
        selected_language_name = st.selectbox(
            "Conversation Language",
            options=list(LANGUAGE_OPTIONS.keys()),
            index=0,
            help="Select the language for the generated conversation"
        )
        selected_language = LANGUAGE_OPTIONS[selected_language_name]

        st.divider()

        # Model selection
        model = st.selectbox(
            "TTS Model",
            ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"],
            help="Select the TTS model to use"
        )

        st.divider()

        # Speaker configuration
        st.subheader("🗣️ Speaker Settings")

        speaker1_name = st.text_input("Speaker 1 Name", value="Joe")
        speaker1_voice = st.selectbox("Speaker 1 Voice", VOICE_OPTIONS, index=0)

        speaker2_name = st.text_input("Speaker 2 Name", value="Jane")
        speaker2_voice = st.selectbox("Speaker 2 Voice", VOICE_OPTIONS, index=1)

    # Initialize session state for TTS
    if 'generated_conversation' not in st.session_state:
        st.session_state['generated_conversation'] = None
    if 'audio_file' not in st.session_state:
        st.session_state['audio_file'] = None
    if 'webpage_content' not in st.session_state:
        st.session_state['webpage_content'] = None
    if 'selected_language_name' not in st.session_state:
        st.session_state['selected_language_name'] = None

    # Main content area
    tab1, tab2, tab3 = st.tabs(["🌐 URL to Conversation", "💬 Manual Conversation", "ℹ️ About"])

    with tab1:
        st.subheader("🔗 Generate Conversation from URL")
        st.markdown("Enter a URL to analyze the webpage content and generate an AI conversation")

        # URL input
        url_input = st.text_input(
            "Enter webpage URL",
            placeholder="https://example.com/article",
            help="Enter the URL of any webpage to analyze"
        )

        # Single button for complete workflow
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_all_btn = st.button(
                "🎬 Generate Conversation & Audio",
                use_container_width=True,
                type="primary",
                key="url_generate_all"
            )

        if generate_all_btn:
            if not api_key:
                st.error("❌ Please provide a Gemini API key in the sidebar")
            elif not url_input.strip():
                st.error("❌ Please enter a URL")
            else:
                try:
                    # Initialize client
                    client = genai.Client(api_key=api_key)

                    # Step 1: Fetch webpage
                    with st.spinner("📥 Step 1/3: Fetching webpage content..."):
                        webpage_content = fetch_webpage(url_input)
                        st.session_state['webpage_content'] = webpage_content
                    st.success("✅ Webpage fetched successfully!")

                    # Step 2: Generate conversation
                    with st.spinner(f"🤖 Step 2/3: Generating conversation in {selected_language_name}..."):
                        generated_conversation = generate_conversation_from_content(
                            client, webpage_content, speaker1_name, speaker2_name, selected_language
                        )
                        st.session_state['generated_conversation'] = generated_conversation
                        st.session_state['selected_language_name'] = selected_language_name
                    st.success(f"✅ Conversation generated in {selected_language_name}!")

                    # Step 3: Generate TTS
                    with st.spinner("🎵 Step 3/3: Generating audio... This may take a moment"):
                        # Prepare prompt
                        prompt = f"TTS the following conversation between {speaker1_name} and {speaker2_name}:\n{generated_conversation}"

                        # Generate TTS
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
                        data = response.candidates[0].content.parts[0].inline_data.data

                        # Generate filename with timestamp and username
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_name = f"tts_{st.session_state['username']}_{timestamp}.wav"

                        # Save to file
                        wave_file(file_name, data)

                        # Store in session state
                        st.session_state['audio_file'] = file_name

                    st.success("🎉 All done! Audio generated successfully!")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.exception(e)

        # Display results if they exist in session state
        if st.session_state['generated_conversation']:
            st.divider()

            # Show selected language
            if st.session_state['selected_language_name']:
                st.info(f"🌍 **Generated Language:** {st.session_state['selected_language_name']}")

            # Show fetched content (preview)
            if st.session_state['webpage_content']:
                with st.expander("📄 View Fetched Content (Preview)"):
                    st.text(st.session_state['webpage_content'][:1000] + "..." if len(st.session_state['webpage_content']) > 1000 else st.session_state['webpage_content'])

            # Show generated conversation
            st.subheader(f"📝 Generated Conversation ({st.session_state['selected_language_name'] or 'Default'})")
            st.text_area(
                "Conversation",
                value=st.session_state['generated_conversation'],
                height=300,
                key="generated_conv_display"
            )

            # Show audio player if audio exists
            if st.session_state['audio_file']:
                st.divider()
                st.subheader("🎧 Listen to Generated Audio")

                try:
                    with open(st.session_state['audio_file'], "rb") as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format="audio/wav")

                    # Download button
                    st.download_button(
                        label="📥 Download Audio File",
                        data=audio_bytes,
                        file_name=st.session_state['audio_file'],
                        mime="audio/wav",
                        key="download_audio_url"
                    )

                    # Display file info
                    st.info(f"📁 Saved as: `{st.session_state['audio_file']}`")
                except FileNotFoundError:
                    st.warning("Audio file not found. Please regenerate.")

        # Clear button
        if st.session_state['generated_conversation'] or st.session_state['audio_file']:
            st.divider()
            if st.button("🗑️ Clear Results", key="clear_url_results"):
                st.session_state['generated_conversation'] = None
                st.session_state['audio_file'] = None
                st.session_state['webpage_content'] = None
                st.session_state['selected_language_name'] = None
                st.rerun()

    with tab2:
        # Conversation input
        st.subheader("Enter Conversation Manually")

        # Example conversation
        example_conversation = f"""{speaker1_name}: How's it going today {speaker2_name}?
{speaker2_name}: Not too bad, how about you?"""

        conversation = st.text_area(
            "Type or paste your conversation below",
            value=example_conversation,
            height=200,
            help=f"Format: {speaker1_name}: dialogue\\n{speaker2_name}: dialogue"
        )

        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_btn = st.button("🎵 Generate Audio", use_container_width=True, type="primary", key="manual_generate")

        # Generation logic
        if generate_btn:
            if not api_key:
                st.error("❌ Please provide a Gemini API key in the sidebar")
            elif not conversation.strip():
                st.error("❌ Please enter a conversation")
            else:
                try:
                    with st.spinner("🔄 Generating audio... This may take a moment"):
                        # Initialize client
                        client = genai.Client(api_key=api_key)

                        # Prepare prompt
                        prompt = f"TTS the following conversation between {speaker1_name} and {speaker2_name}:\n{conversation}"

                        # Generate content
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
                        data = response.candidates[0].content.parts[0].inline_data.data

                        # Generate filename with timestamp and username
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_name = f"tts_manual_{st.session_state['username']}_{timestamp}.wav"

                        # Save to file
                        wave_file(file_name, data)

                        st.success(f"✅ Audio generated successfully!")

                        # Display audio player
                        st.subheader("🎧 Listen to Generated Audio")
                        with open(file_name, "rb") as audio_file:
                            audio_bytes = audio_file.read()
                            st.audio(audio_bytes, format="audio/wav")

                        # Download button
                        st.download_button(
                            label="📥 Download Audio File",
                            data=audio_bytes,
                            file_name=file_name,
                            mime="audio/wav",
                            key="download_audio_manual"
                        )

                        # Display file info
                        st.info(f"📁 Saved as: `{file_name}`")

                except Exception as e:
                    st.error(f"❌ Error generating audio: {str(e)}")
                    st.exception(e)

    with tab3:
        st.subheader("About This App")
        st.markdown("""
        This application uses Google's Gemini API to analyze web content and generate realistic multi-speaker conversations with TTS.

        ### Features:
        - 🔐 **User Authentication**: Secure login system with MongoDB
        - 🌐 **URL Analysis**: Automatically fetch and analyze webpage content
        - 🤖 **AI Conversation Generation**: Use Gemini 2.0 Flash to create engaging dialogues
        - 🌍 **Multi-Language Support**: Generate conversations in 16 different languages
        - 🎭 **Multi-Speaker Support**: Configure up to 2 different speakers with unique voices
        - 🎨 **Voice Selection**: Choose from multiple prebuilt voice options
        - 💾 **Audio Export**: Download generated conversations as WAV files
        - 🎵 **Instant Playback**: Listen to generated audio directly in the app

        ### Available Voices:
        - **Kore**: Natural, balanced voice
        - **Puck**: Energetic, playful voice
        - **Charon**: Deep, authoritative voice
        - **Fenrir**: Strong, commanding voice
        - **Aoede**: Melodic, expressive voice

        ### Supported Languages:
        English, Chinese (Simplified/Traditional), Korean, Japanese, Spanish, French, German, Italian, Portuguese, Russian, Arabic, Thai, Vietnamese, Indonesian, Hindi

        ### Requirements:
        ```bash
        pip install streamlit google-genai python-dotenv requests beautifulsoup4 markdownify pymongo
        ```

        ### MongoDB Setup:
        Make sure MongoDB is running on `localhost:27017` with database `local` and collection `帳號密碼`.

        ### API Key:
        Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

        ### How to Run:
        ```bash
        streamlit run gemini_tts_auth_app.py
        ```
        """)

    # Footer
    st.divider()
    st.caption(f"Made with Streamlit and Google Gemini TTS API | User: {st.session_state['username']}")

# Main app logic
def main():
    if not st.session_state['authenticated']:
        show_login_page()
    else:
        show_tts_app()

if __name__ == "__main__":
    main()
