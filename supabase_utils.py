"""
Supabase 工具模塊
提供單字收藏的數據庫操作功能
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# 加載環境變量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

# 全局客戶端
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """獲取或創建 Supabase 客戶端"""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("請在 .env 文件中設置 SUPABASE_URL 和 SUPABASE_ANON_KEY")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

# ==================== 韓文單字操作 ====================

def get_korean_words(user_id: str) -> List[Dict]:
    """獲取用戶的所有韓文單字"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('korean_words')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('saved_at', desc=True)\
            .execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching Korean words: {e}")
        return []

def add_korean_word(user_id: str, word_data: Dict) -> Dict:
    """添加韓文單字到收藏"""
    try:
        supabase = get_supabase_client()

        # 檢查是否已存在
        existing = supabase.table('korean_words')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('korean', word_data.get('korean'))\
            .execute()

        if existing.data:
            return {'message': '單字已存在於收藏中', 'exists': True}

        # 準備數據
        data = {
            'user_id': user_id,
            'korean': word_data.get('korean'),
            'chinese': word_data.get('chinese'),
            'definition': word_data.get('definition'),
            'example_korean': word_data.get('example_korean'),
            'example_chinese': word_data.get('example_chinese'),
            'level': word_data.get('level', '未分級'),
            'saved_at': datetime.now().isoformat()
        }

        # 插入數據
        response = supabase.table('korean_words').insert(data).execute()

        return {'message': '單字已收藏', 'exists': False, 'data': response.data}

    except Exception as e:
        print(f"Error adding Korean word: {e}")
        return {'error': str(e)}, 500

def delete_korean_word(user_id: str, korean: str) -> Dict:
    """刪除韓文單字"""
    try:
        supabase = get_supabase_client()

        response = supabase.table('korean_words')\
            .delete()\
            .eq('user_id', user_id)\
            .eq('korean', korean)\
            .execute()

        return {'message': '單字已移除'}

    except Exception as e:
        print(f"Error deleting Korean word: {e}")
        return {'error': str(e)}, 500

# ==================== 中文單字操作 ====================

def get_chinese_words(user_id: str) -> List[Dict]:
    """獲取用戶的所有中文單字"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('chinese_words')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('saved_at', desc=True)\
            .execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching Chinese words: {e}")
        return []

def add_chinese_word(user_id: str, word_data: Dict) -> Dict:
    """添加中文單字到收藏"""
    try:
        supabase = get_supabase_client()

        # 檢查是否已存在
        existing = supabase.table('chinese_words')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('chinese', word_data.get('chinese'))\
            .execute()

        if existing.data:
            return {'message': '單字已存在於收藏中', 'exists': True}

        # 準備數據
        data = {
            'user_id': user_id,
            'chinese': word_data.get('chinese'),
            'english': word_data.get('english'),
            'definition': word_data.get('definition'),
            'example_chinese': word_data.get('example_chinese'),
            'example_english': word_data.get('example_english'),
            'level': word_data.get('level', '未分級'),
            'level_category': word_data.get('level_category', '未分級'),
            'level_number': word_data.get('level_number', ''),
            'saved_at': datetime.now().isoformat()
        }

        # 插入數據
        response = supabase.table('chinese_words').insert(data).execute()

        return {'message': '單字已收藏', 'exists': False, 'data': response.data}

    except Exception as e:
        print(f"Error adding Chinese word: {e}")
        return {'error': str(e)}, 500

def delete_chinese_word(user_id: str, chinese: str) -> Dict:
    """刪除中文單字"""
    try:
        supabase = get_supabase_client()

        response = supabase.table('chinese_words')\
            .delete()\
            .eq('user_id', user_id)\
            .eq('chinese', chinese)\
            .execute()

        return {'message': '單字已移除'}

    except Exception as e:
        print(f"Error deleting Chinese word: {e}")
        return {'error': str(e)}, 500

# ==================== 用戶帳號操作 ====================

def get_user_by_username(username: str) -> Optional[Dict]:
    """根據用戶名獲取用戶資料"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('users')\
            .select('*')\
            .eq('username', username)\
            .execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching user by username: {e}")
        return None

def get_user_by_email(email: str) -> Optional[Dict]:
    """根據 email 獲取用戶資料"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('users')\
            .select('*')\
            .eq('email', email)\
            .execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching user by email: {e}")
        return None

def create_user(username: str, password_hash: str, email: str = None, language: str = 'zh-TW') -> Dict:
    """創建新用戶"""
    try:
        supabase = get_supabase_client()

        # 檢查用戶名是否已存在
        existing = get_user_by_username(username)
        if existing:
            return {'success': False, 'error': 'username_exists'}

        # 檢查 email 是否已存在
        if email:
            existing_email = get_user_by_email(email)
            if existing_email:
                return {'success': False, 'error': 'email_exists'}

        # 準備數據
        data = {
            'username': username,
            'password': password_hash,
            'email': email,
            'language': language,
            'created_at': datetime.now().isoformat()
        }

        # 插入數據
        response = supabase.table('users').insert(data).execute()

        if response.data:
            return {'success': True, 'user': response.data[0]}
        return {'success': False, 'error': 'insert_failed'}

    except Exception as e:
        print(f"Error creating user: {e}")
        return {'success': False, 'error': str(e)}

def update_user(username: str, updates: Dict) -> Dict:
    """更新用戶資料"""
    try:
        supabase = get_supabase_client()

        response = supabase.table('users')\
            .update(updates)\
            .eq('username', username)\
            .execute()

        if response.data:
            return {'success': True, 'user': response.data[0]}
        return {'success': False, 'error': 'update_failed'}

    except Exception as e:
        print(f"Error updating user: {e}")
        return {'success': False, 'error': str(e)}

def update_user_password(username: str, new_password_hash: str) -> Dict:
    """更新用戶密碼"""
    return update_user(username, {'password': new_password_hash})

def update_user_language(username: str, language: str) -> Dict:
    """更新用戶語言設定"""
    return update_user(username, {'language': language})

def update_last_login(username: str) -> Dict:
    """更新最後登入時間"""
    return update_user(username, {'last_login': datetime.now().isoformat()})

def check_email_exists(email: str, exclude_username: str = None) -> bool:
    """檢查 email 是否已被使用（可排除特定用戶）"""
    try:
        supabase = get_supabase_client()
        query = supabase.table('users').select('username').eq('email', email)

        if exclude_username:
            query = query.neq('username', exclude_username)

        response = query.execute()
        return len(response.data) > 0 if response.data else False

    except Exception as e:
        print(f"Error checking email: {e}")
        return False
