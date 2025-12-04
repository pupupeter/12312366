"""
TOCFL 詞彙表載入器
"""
import csv
import os


class TOCFLVocab:
    def __init__(self, csv_path=None):
        if csv_path is None:
            # 預設路徑
            csv_path = os.path.join(os.path.dirname(__file__), '14452詞語表202504.csv')

        self.vocab_dict = {}
        self.load_vocab(csv_path)

    def load_vocab(self, csv_path):
        """載入 TOCFL 詞彙表"""
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    word = row.get('word', '').strip()
                    # 處理「詞1/詞2」格式，分別存儲
                    words = word.split('/')
                    for w in words:
                        w = w.strip()
                        if w:
                            self.vocab_dict[w] = {
                                'level': row.get('deng', ''),
                                'grade': row.get('ji', ''),
                                'pinyin': row.get('pinyin', ''),
                                'situation': row.get('situation', '')
                            }
            print(f"✓ 成功載入 {len(self.vocab_dict)} 個 TOCFL 詞彙")
        except Exception as e:
            print(f"✗ 載入 TOCFL 詞彙表失敗: {e}")
            self.vocab_dict = {}

    def get_word_info(self, word):
        """查詢詞彙的 TOCFL 信息"""
        return self.vocab_dict.get(word, None)

    def get_level_display(self, word):
        """獲取詞彙的級數顯示（例如：A1, B2, C1）"""
        info = self.get_word_info(word)
        if info:
            level = info['level']
            grade = info['grade']

            # 轉換為簡潔格式
            level_map = {
                '基礎': 'A',
                '進階': 'B',
                '高階': 'C',
                '流利': 'D',
                '精通': 'E'
            }
            level_short = level_map.get(level, level)
            grade_num = grade.replace('第', '').replace('級', '')

            return f"{level_short}{grade_num}"
        return None


# 全局實例
tocfl_vocab = None

def get_tocfl_vocab():
    """獲取全局 TOCFL 詞彙表實例"""
    global tocfl_vocab
    if tocfl_vocab is None:
        tocfl_vocab = TOCFLVocab()
    return tocfl_vocab
