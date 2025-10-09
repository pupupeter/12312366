from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import re
import json
from smolagents import Tool, LiteLLMModel
from markdownify import markdownify
import threading
import time
from datetime import datetime

app = Flask(__name__)

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

# 自訂韓文分詞翻譯工具
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

# HTML生成工具
def generate_graph_html(words_data, url):
    # 準備圖形數據
    nodes = []
    links = []

    # 創建節點
    for i, word in enumerate(words_data):
        nodes.append({
            'id': i,
            'korean': word.get('korean', 'N/A'),
            'chinese': word.get('chinese', 'N/A'),
            'definition': word.get('definition', 'N/A'),
            'example_korean': word.get('example_korean', 'N/A'),
            'example_chinese': word.get('example_chinese', 'N/A'),
            'group': i % 5  # 用於顏色分組
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
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>韓文詞彙知識圖譜</title>
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
    </style>
</head>
<body>
    <div class="back-button">
        <a href="/">← 返回首頁</a>
    </div>

    <div class="header">
        <h1>🇰🇷 韓文詞彙知識圖譜</h1>
        <p>互動式詞彙學習網絡 - 點擊節點查看詳細資訊</p>
    </div>

    <div class="source">
        <strong>資料來源:</strong>
        <a href="{url}" target="_blank">{url}</a>
        <br>
        <strong>共 {len(words_data)} 個韓文詞彙</strong>
    </div>

    <div id="graph-container">
        <div class="controls">
            <button onclick="restartSimulation()">重新排列</button>
            <button onclick="centerGraph()">居中顯示</button>
        </div>
    </div>

    <script>
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

        // 顏色比例尺
        const color = d3.scaleOrdinal()
            .domain([0, 1, 2, 3, 4])
            .range(['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']);

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

        // 節點文字（韓文）
        node.append("text")
            .text(d => d.korean)
            .attr("x", 0)
            .attr("y", 0)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("font-size", "12px")
            .attr("font-weight", "bold")
            .attr("fill", "white")
            .attr("pointer-events", "none");

        // 中文翻譯標籤
        node.append("text")
            .text(d => d.chinese)
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

        // 節點事件
        node.on("mouseover", function(event, d) {{
            tooltip.transition()
                .duration(200)
                .style("opacity", .9);
            tooltip.html(`
                <div class="korean">${{d.korean}}</div>
                <div class="chinese">${{d.chinese}}</div>
                <div class="definition"><strong>定義:</strong> ${{d.definition}}</div>
                <div class="example"><strong>例句:</strong> ${{d.example_korean}}</div>
                <div class="example"><strong>翻譯:</strong> ${{d.example_chinese}}</div>
            `)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        }})
        .on("mouseout", function(d) {{
            tooltip.transition()
                .duration(500)
                .style("opacity", 0);
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
    return render_template('index.html')

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
        return send_file(filename, as_attachment=False)
    except FileNotFoundError:
        return jsonify({'error': '文件未找到'}), 404

def process_korean_analysis(url, process_id):
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

            # 生成HTML文件
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)