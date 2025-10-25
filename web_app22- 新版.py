from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import re
import json
import csv
from smolagents import Tool, LiteLLMModel
from markdownify import markdownify
import threading
import time
from datetime import datetime
import urllib.parse  # 用於解碼 URL 編碼的用戶名

# 導入 Supabase 工具函數（中文單字版本）
from supabase_utils import (
    get_chinese_words,
    add_chinese_word,
    delete_chinese_word
)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 確保 JSON 回應正確處理中文

# 輔助函數：從 request headers 獲取 user_id
def get_user_id_from_headers():
    """從代理傳遞的 headers 中獲取 user_id"""
    user_id = request.headers.get('X-User-ID', '')
    if not user_id:
        # 如果沒有 user_id，使用 username 作為備用
        username = request.headers.get('X-Username', '')
        if username:
            user_id = urllib.parse.unquote(username)
        else:
            user_id = 'default_user'  # 默認用戶
    return user_id

# 載入中文詞彙分級資料
def load_chinese_vocabulary_levels():
    """載入CSV詞彙表，建立中文詞彙到分級的映射"""
    vocab_levels = {}
    # 使用相對路徑，讓程式在 Windows 和 WSL 都能運行
    csv_path = os.path.join(os.path.dirname(__file__), "14452詞語表202504.csv")

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get('word', '').strip()
                deng = row.get('deng', '').strip()  # 基礎/進階
                ji = row.get('ji', '').strip()      # 第1級/第2級等

                if word:
                    # 處理多個詞彙形式（例如：爸爸/爸）
                    words = word.split('/')
                    for w in words:
                        vocab_levels[w.strip()] = {
                            'level_category': deng,  # 基礎或進階
                            'level_number': ji,      # 級數
                            'full_level': f"{deng} {ji}"  # 完整分級
                        }

        print(f"成功載入 {len(vocab_levels)} 個中文詞彙分級資料")
        return vocab_levels
    except Exception as e:
        print(f"載入詞彙表失敗: {e}")
        return {}

# 全局詞彙分級字典
VOCAB_LEVELS = load_chinese_vocabulary_levels()

# 自訂抓取網頁內容工具
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

# 自訂中文詞彙分析翻譯工具
class ChineseWordAnalysisTool(Tool):
    name = "chinese_word_analysis"
    description = "Analyzes Chinese text: tokenizes, translates to English, provides definitions and example sentences."
    inputs = {"text": {"type": "string", "description": "Chinese text to analyze."}}
    output_type = "string"

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    def forward(self, text: str) -> str:
        prompt = f"""
請對以下中文內容進行詳細分析：

1. 首先進行分詞，找出所有重要的詞彙（名詞、動詞、形容詞等），忽略無關的標點符號和格式
2. 只提取中文詞彙（2-4個字為主）
3. 對每個詞彙提供以下資訊：
   - 中文詞彙（僅提供詞彙本身，不要包含其他說明）
   - 英文翻譯
   - 英文定義/解釋
   - 中文例句（使用該詞彙的簡單例句）
   - 例句的英文翻譯

請以JSON格式輸出，結構如下：
[
  {{
    "chinese": "中文詞彙",
    "english": "English translation",
    "definition": "English definition",
    "example_chinese": "中文例句",
    "example_english": "English translation of the example"
  }}
]

中文內容：
{text}
"""
        messages = [{"role": "user", "content": prompt}]
        response = self.model(messages)
        return response.content if hasattr(response, 'content') else str(response)

# HTML生成工具
def generate_graph_html(words_data, url):
    # 準備圖形數據
    nodes = []
    links = []

    # 創建節點，並匹配詞彙分級
    for i, word in enumerate(words_data):
        chinese_word = word.get('chinese', 'N/A').strip()

        # 查詢詞彙分級
        level_info = VOCAB_LEVELS.get(chinese_word, {})
        level_category = level_info.get('level_category', '未分級')
        level_number = level_info.get('level_number', '')
        full_level = level_info.get('full_level', '未分級')

        # 根據分級決定組別（用於顏色）
        # 基礎第1級=0, 基礎第2級=1, 基礎第3級=2, 進階第3級=3, 進階第4級=4, 進階第5級=5, 未分級=6
        group = 6  # 預設未分級
        if level_category == '基礎':
            if '第1級' in level_number:
                group = 0
            elif '第2級' in level_number:
                group = 1
            elif '第3級' in level_number:
                group = 2
        elif level_category == '進階':
            if '第3級' in level_number:
                group = 3
            elif '第4級' in level_number:
                group = 4
            elif '第5級' in level_number:
                group = 5

        nodes.append({
            'id': i,
            'chinese': chinese_word,
            'english': word.get('english', 'N/A'),
            'definition': word.get('definition', 'N/A'),
            'example_chinese': word.get('example_chinese', 'N/A'),
            'example_english': word.get('example_english', 'N/A'),
            'level': full_level,
            'level_category': level_category,
            'level_number': level_number,
            'group': group
        })

    # 創建隨機連接（基於詞彙相似性或共同主題）
    import random
    for i in range(len(nodes)):
        # 每個節點連接1-3個其他節點
        if len(nodes) > 1:
            connections = random.sample(range(len(nodes)), min(3, len(nodes)-1))
            for target in connections:
                if target != i:
                    links.append({
                        'source': i,
                        'target': target,
                        'value': random.randint(1, 3)
                    })

    html_template = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中文詞彙知識圖譜 | Chinese Vocabulary Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: 'Malgun Gothic', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .source {{
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .source a {{
            color: #ffeb3b;
            text-decoration: none;
        }}
        #graph-container {{
            width: 100%;
            height: 80vh;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 10px;
            position: relative;
            background: rgba(255,255,255,0.05);
        }}
        .tooltip {{
            position: absolute;
            text-align: center;
            padding: 15px;
            font: 14px sans-serif;
            background: rgba(0,0,0,0.9);
            border: 1px solid #fff;
            border-radius: 8px;
            pointer-events: none;
            color: white;
            max-width: 300px;
            z-index: 1000;
        }}
        .tooltip .korean {{
            font-size: 18px;
            font-weight: bold;
            color: #ffeb3b;
            margin-bottom: 5px;
        }}
        .tooltip .chinese {{
            font-size: 16px;
            color: #ff5722;
            margin-bottom: 8px;
        }}
        .tooltip .definition {{
            margin-bottom: 8px;
            font-size: 12px;
        }}
        .tooltip .example {{
            font-style: italic;
            font-size: 11px;
            color: #ccc;
        }}
        .controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            padding: 10px;
            border-radius: 5px;
        }}
        .controls button {{
            margin: 2px;
            padding: 5px 10px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }}
        .controls button:hover {{
            background: #1976D2;
        }}
        .back-button {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            padding: 10px;
            border-radius: 5px;
        }}
        .back-button a {{
            color: #ffeb3b;
            text-decoration: none;
            font-weight: bold;
        }}
        .saved-indicator {{
            position: absolute;
            top: -5px;
            right: -5px;
            background: #ff6b6b;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
        }}
        .notification {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            border: 2px solid #4ecdc4;
        }}
        @keyframes slideIn {{
            from {{
                transform: translateX(400px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        .legend {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 15px;
            border-radius: 5px;
            font-size: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 8px;
            border: 2px solid white;
        }}
    </style>
</head>
<body>
    <div class="back-button">
        <a href="/dashboard">← 返回首頁</a>
        <a href="javascript:void(0)" id="reviewLink" onclick="goToReview()" style="margin-left: 10px;">📚 我的收藏</a>
    </div>

    <div class="header">
        <h1>🇨🇳 中文詞彙知識圖譜 | Chinese Vocabulary Knowledge Graph</h1>
        <p>互動式詞彙學習網絡 - Interactive Vocabulary Learning Network</p>
    </div>

    <div class="source">
        <strong>資料來源 Data Source:</strong>
        <a href="{url}" target="_blank">{url}</a>
        <br>
        <strong>共 {len(words_data)} 個中文詞彙 | Total {len(words_data)} Chinese Words</strong>
    </div>

    <div id="graph-container">
        <div class="controls">
            <button onclick="restartSimulation()">重新排列 Rearrange</button>
            <button onclick="centerGraph()">居中顯示 Center</button>
        </div>
        <div class="legend">
            <div style="font-weight: bold; margin-bottom: 10px;">📊 詞彙分級圖例</div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #4CAF50;"></div>
                <span>基礎 第1級</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #2196F3;"></div>
                <span>基礎 第2級</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #9C27B0;"></div>
                <span>基礎 第3級</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #FF9800;"></div>
                <span>進階 第3級</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #F44336;"></div>
                <span>進階 第4級</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #D32F2F;"></div>
                <span>進階 第5級</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #9E9E9E;"></div>
                <span>未分級</span>
            </div>
        </div>
    </div>

    <script>
        // 檢測當前路徑,自動適應代理環境
        function getBasePath() {{
            const path = window.location.pathname;
            if (path.startsWith('/chinese-app')) {{
                return '/chinese-app';
            }}
            return '';
        }}

        // 導航函數
        function goHome() {{
            const protocol = window.location.protocol;
            const host = window.location.host;
            const homeUrl = `${{protocol}}//${{host}}/dashboard`;
            console.log('Current URL:', window.location.href);
            console.log('Navigating to dashboard:', homeUrl);
            window.location.href = homeUrl;
        }}

        function goToReview() {{
            const basePath = getBasePath();
            const reviewUrl = basePath + '/review';
            console.log('Navigating to review:', reviewUrl);
            window.location.href = reviewUrl;
        }}

        const nodes = {json.dumps(nodes, ensure_ascii=False)};
        const links = {json.dumps(links, ensure_ascii=False)};

        const width = document.getElementById('graph-container').clientWidth;
        const height = document.getElementById('graph-container').clientHeight;

        const svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g");

        // 添加縮放功能
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', function(event) {{
                g.attr('transform', event.transform);
            }});

        svg.call(zoom);

        // 顏色比例尺（依據詞彙分級）
        // 0=基礎第1級(綠), 1=基礎第2級(藍), 2=基礎第3級(紫), 3=進階第3級(橙), 4=進階第4級(紅), 5=進階第5級(深紅), 6=未分級(灰)
        const color = d3.scaleOrdinal()
            .domain([0, 1, 2, 3, 4, 5, 6])
            .range(['#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#F44336', '#D32F2F', '#9E9E9E']);

        // 力模擬
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(40));

        // 創建連接線
        const link = g.append("g")
            .selectAll("line")
            .data(links)
            .enter().append("line")
            .attr("stroke", "rgba(255,255,255,0.3)")
            .attr("stroke-width", d => Math.sqrt(d.value) * 2);

        // 創建節點
        const node = g.append("g")
            .selectAll("g")
            .data(nodes)
            .enter().append("g")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        // 節點圓圈
        node.append("circle")
            .attr("r", 25)
            .attr("fill", d => color(d.group))
            .attr("stroke", "#fff")
            .attr("stroke-width", 3);

        // 節點文字（中文）
        node.append("text")
            .text(d => d.chinese)
            .attr("x", 0)
            .attr("y", 0)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("font-size", "12px")
            .attr("font-weight", "bold")
            .attr("fill", "white")
            .attr("pointer-events", "none");

        // 英文翻譯標籤
        node.append("text")
            .text(d => d.english)
            .attr("x", 0)
            .attr("y", 35)
            .attr("text-anchor", "middle")
            .attr("font-size", "10px")
            .attr("fill", "#ffeb3b")
            .attr("pointer-events", "none");

        // 工具提示
        const tooltip = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);

        // 顯示通知
        function showNotification(message, isSuccess = true) {{
            const notification = document.createElement('div');
            notification.className = 'notification';
            notification.style.borderColor = isSuccess ? '#4ecdc4' : '#ff6b6b';
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {{
                notification.remove();
            }}, 3000);
        }}

        // 收藏單字功能
        function saveWord(wordData) {{
            const basePath = getBasePath();
            fetch(`${{basePath}}/api/saved-words`, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify({{ word: wordData }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.exists) {{
                    showNotification('⚠️ 單字已在收藏中', false);
                }} else {{
                    showNotification('✅ 單字已收藏！');
                    // 標記此節點為已收藏
                    markNodeAsSaved(wordData.chinese);
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                showNotification('❌ 收藏失敗', false);
            }});
        }}

        // 標記節點為已收藏
        function markNodeAsSaved(chinese) {{
            node.each(function(d) {{
                if (d.chinese === chinese) {{
                    const nodeGroup = d3.select(this);
                    // 檢查是否已有標記
                    if (nodeGroup.select('.saved-indicator').empty()) {{
                        nodeGroup.append('text')
                            .attr('class', 'saved-indicator')
                            .text('⭐')
                            .attr('x', 20)
                            .attr('y', -20)
                            .attr('font-size', '16px')
                            .attr('pointer-events', 'none');
                    }}
                }}
            }});
        }}

        // 載入已收藏的單字並標記
        (function() {{
            const basePath = getBasePath();
            fetch(`${{basePath}}/api/saved-words`)
                .then(response => response.json())
                .then(data => {{
                    const savedChinese = data.words.map(w => w.chinese);
                    savedChinese.forEach(chinese => {{
                        markNodeAsSaved(chinese);
                    }});
                }})
                .catch(error => console.error('Error loading saved words:', error));
        }})();

        // 節點事件
        node.on("mouseover", function(event, d) {{
            tooltip.transition()
                .duration(200)
                .style("opacity", .9);

            // 根據分級顯示不同顏色的標籤
            let levelColor = '#9E9E9E';  // 預設灰色
            if (d.level_category === '基礎') {{
                levelColor = '#4CAF50';  // 綠色系
            }} else if (d.level_category === '進階') {{
                levelColor = '#F44336';  // 紅色系
            }}

            tooltip.html(`
                <div class="korean">${{d.chinese}}</div>
                <div class="chinese">${{d.english}}</div>
                <div style="background-color: ${{levelColor}}; padding: 3px 8px; border-radius: 3px; margin: 5px 0; display: inline-block;">
                    <strong>分級 Level:</strong> ${{d.level}}
                </div>
                <div class="definition"><strong>Definition:</strong> ${{d.definition}}</div>
                <div class="example"><strong>中文例句:</strong> ${{d.example_chinese}}</div>
                <div class="example"><strong>English:</strong> ${{d.example_english}}</div>
                <div style="margin-top: 10px; font-size: 10px; color: #4ecdc4;">💡 雙擊節點收藏單字 Double-click to save</div>
            `)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        }})
        .on("mouseout", function(d) {{
            tooltip.transition()
                .duration(500)
                .style("opacity", 0);
        }})
        .on("dblclick", function(event, d) {{
            event.stopPropagation();
            saveWord({{
                chinese: d.chinese,
                english: d.english,
                definition: d.definition,
                example_chinese: d.example_chinese,
                example_english: d.example_english,
                level: d.level,
                level_category: d.level_category,
                level_number: d.level_number
            }});
        }});

        // 模擬更新
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});

        // 拖拽功能
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        // 控制功能
        function restartSimulation() {{
            simulation.alpha(1).restart();
        }}

        function centerGraph() {{
            const transform = d3.zoomIdentity.translate(width / 2, height / 2).scale(1);
            svg.transition().duration(750).call(zoom.transform, transform);
        }}
    </script>
</body>
</html>
    """

    return html_template

# 全局變量存儲處理狀態
processing_status = {}

@app.route('/')
def index():
    return render_template('index22.html')

@app.route('/process', methods=['POST'])
def process_url():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': '請提供網址'}), 400

    if not url.startswith('http'):
        url = 'https://' + url

    # 生成唯一的處理ID
    process_id = str(int(time.time() * 1000))
    processing_status[process_id] = {
        'status': 'processing',
        'message': '正在處理中...',
        'progress': 0
    }

    # 在背景執行處理
    thread = threading.Thread(target=process_korean_analysis, args=(url, process_id))
    thread.start()

    return jsonify({'process_id': process_id})

@app.route('/status/<process_id>')
def get_status(process_id):
    status = processing_status.get(process_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/result/<filename>')
def get_result(filename):
    try:
        return send_file(filename, as_attachment=False, mimetype='text/html; charset=utf-8')
    except FileNotFoundError:
        return jsonify({'error': '文件未找到'}), 404

# API: 獲取所有收藏的單字
@app.route('/api/saved-words', methods=['GET'])
def get_saved_words():
    user_id = get_user_id_from_headers()
    words = get_chinese_words(user_id)
    return jsonify({'words': words})

# API: 添加單字到收藏
@app.route('/api/saved-words', methods=['POST'])
def add_saved_word():
    user_id = get_user_id_from_headers()
    data = request.json
    word = data.get('word')

    if not word:
        return jsonify({'error': '單字資料不完整'}), 400

    result = add_chinese_word(user_id, word)
    return jsonify(result)

# API: 刪除收藏的單字
@app.route('/api/saved-words/<chinese>', methods=['DELETE'])
def delete_saved_word(chinese):
    user_id = get_user_id_from_headers()
    result = delete_chinese_word(user_id, chinese)
    return jsonify(result)

# 複習頁面
@app.route('/review')
def review():
    return render_template('review22.html')

def process_korean_analysis(url, process_id):
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
            'message': '正在抓取網頁內容... Fetching webpage...',
            'progress': 30
        }

        content = visit_tool.forward(url)
        if content.startswith("Request timed out") or content.startswith("Error"):
            processing_status[process_id] = {
                'status': 'error',
                'message': f'抓取網頁失敗 Failed to fetch: {content}'
            }
            return

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在進行中文詞彙分析... Analyzing Chinese vocabulary...',
            'progress': 60
        }

        words_json_str = chinese_tool.forward(content)

        processing_status[process_id] = {
            'status': 'processing',
            'message': '正在解析分析結果... Parsing results...',
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
                'message': '正在生成知識圖譜... Generating knowledge graph...',
                'progress': 90
            }

            # 生成HTML文件
            html_content = generate_graph_html(words, url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chinese_graph_{len(words)}words_{timestamp}.html"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            processing_status[process_id] = {
                'status': 'completed',
                'message': f'成功生成 {len(words)} 個中文詞彙的知識圖譜 | Successfully generated {len(words)} Chinese words',
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)