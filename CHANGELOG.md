# 更新日誌

## [2024-12-04] Gemini TTS Flask 整合

### 🎉 主要更新

#### ✅ 完全移除 Streamlit 依賴
- 刪除 `gemini_tts_auth_app.py` (Streamlit 版本)
- 刪除 `gemini_tts_flask.py` (舊版本)
- 刪除 `templates/tts.html` 和 `templates/tts_flask.html`

#### ✅ TTS 功能整合到 auth_app.py
- 新增 `/tts` 路由 - 主 TTS 頁面
- 新增 `/api/tts/generate-from-url` - 從 URL 生成對話和音頻
- 新增 `/api/tts/generate-manual` - 手動輸入對話生成音頻
- 保留 `/api/tts/speak` - 單字語音生成
- 保留 `/api/tts/check` - 檢查 TTS 可用性

#### ✅ 新增檔案
- `templates/tts_main.html` - 主 TTS 介面（含可編輯對話功能）
- `templates/tts_login.html` - TTS 登入頁（備用）
- `templates/tts_register.html` - TTS 註冊頁（備用）
- `gemini_tts_flask_app.py` - 獨立 Flask TTS 應用（可選）
- `requirements_tts.txt` - TTS 所需套件
- `TTS_INTEGRATION_README.md` - 詳細說明文件

### 🎨 新功能

#### 1. 從 URL 生成 AI 對話音頻
- 輸入網址自動抓取內容
- AI 分析並生成對話
- 支援 16 種語言
- 5 種不同聲音選項

#### 2. 可編輯對話功能 ⭐ NEW
- 生成後可直接編輯對話內容
- 點擊「重新生成音頻」按鈕即可重新生成
- **無需重新抓取網頁**
- 支援多次迭代優化

#### 3. 手動輸入對話
- 直接輸入或貼上對話
- 快速生成音頻
- 支援所有語言和聲音選項

### 🔧 技術改進

#### 架構優化
**之前：**
```
auth_app.py (port 8080)
├── web_app.py (port 5000) - 韓文
├── web_app22.py (port 5001) - 中文
└── gemini_tts_auth_app.py (port 8501) - Streamlit TTS ❌
```

**現在：**
```
auth_app.py (port 8080)
├── web_app.py (port 5000) - 韓文
├── web_app22.py (port 5001) - 中文
└── /tts 路由 - Flask TTS ✅ (內建)
```

#### 資料庫
- ✅ 完全使用 Supabase
- ❌ 不再使用 MongoDB
- ✅ 統一認證系統

#### 部署
- ✅ 可部署到 Vercel
- ✅ 不需要獨立的 Streamlit 服務
- ✅ 資源使用更少
- ✅ 啟動速度更快

### 📊 變更統計

```
16 files changed
+2338 insertions
-2019 deletions
```

#### 新增檔案 (8)
- TTS_INTEGRATION_README.md
- VERCEL_DEPLOYMENT_GUIDE.md
- TODO_VERCEL_MERGE.md
- gemini_tts_flask_app.py
- requirements_tts.txt
- templates/tts_main.html
- templates/tts_login.html
- templates/tts_register.html

#### 刪除檔案 (4)
- gemini_tts_auth_app.py
- gemini_tts_flask.py
- templates/tts.html
- templates/tts_flask.html

#### 修改檔案 (1)
- auth_app.py (大幅更新)

### 🎯 支援的功能

#### 語言支援 (16)
- English
- 中文 (簡體/繁體)
- 한국어 (Korean)
- 日本語 (Japanese)
- Español (Spanish)
- Français (French)
- Deutsch (German)
- Italiano (Italian)
- Português (Portuguese)
- Русский (Russian)
- العربية (Arabic)
- ไทย (Thai)
- Tiếng Việt (Vietnamese)
- Bahasa Indonesia
- हिन्दी (Hindi)

#### 聲音選項 (5)
- Kore - 自然、平衡的聲音
- Puck - 充滿活力、俏皮的聲音
- Charon - 深沉、權威的聲音
- Fenrir - 強大、命令式的聲音
- Aoede - 旋律優美、富有表現力的聲音

### 🚀 使用方式

#### 安裝新依賴
```bash
pip install beautifulsoup4 markdownify google-genai
```

或使用完整 requirements：
```bash
pip install -r requirements_tts.txt
```

#### 啟動應用
```bash
python auth_app.py
```

#### 訪問 TTS
1. 登入到主控台：`http://localhost:8080`
2. 點擊「AI 語音對話生成器」卡片
3. 或直接訪問：`http://localhost:8080/tts`

### 📝 後續計劃

- [ ] 部署到 Vercel
- [ ] 添加音頻文件自動清理功能
- [ ] 添加使用量統計
- [ ] 添加收藏功能
- [ ] 優化大型網頁的處理速度

### 🙏 致謝

感謝使用本系統！如有任何問題或建議，歡迎提出 Issue。

---

## [2024-11-15] 用戶認證系統遷移

### 主要更新
- 將用戶認證從 MongoDB 遷移到 Supabase
- 更新所有用戶相關功能使用 Supabase
- 新增 `supabase_utils.py` 工具模組

詳見 commit: `289132e`
