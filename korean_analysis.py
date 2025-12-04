"""
韓文新聞分析輔助函數
包含 HTML 生成和網頁抓取處理
"""
import json
import random


def generate_graph_html(words_data, url):
    """生成韓文知識圖譜 HTML"""
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

    # 創建隨機連接
    for i in range(len(nodes)):
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
    </style>
</head>
<body>
    <div class="back-button">
        <a href="/korean">← 返回首頁</a>
        <a href="/korean/review" style="margin-left: 10px;">📚 我的收藏</a>
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
            fetch('/korean/save-word', {{
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
                    markNodeAsSaved(wordData.korean);
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                showNotification('❌ 收藏失敗', false);
            }});
        }}

        // 標記節點為已收藏
        function markNodeAsSaved(korean) {{
            node.each(function(d) {{
                if (d.korean === korean) {{
                    const nodeGroup = d3.select(this);
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
            fetch('/korean/saved-words')
                .then(response => response.json())
                .then(data => {{
                    const savedKoreans = data.words.map(w => w.korean);
                    savedKoreans.forEach(korean => {{
                        markNodeAsSaved(korean);
                    }});
                }})
                .catch(error => console.error('Error loading saved words:', error));
        }})();

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
                <div style="margin-top: 10px; font-size: 10px; color: #4ecdc4;">💡 雙擊節點收藏單字</div>
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
                korean: d.korean,
                chinese: d.chinese,
                definition: d.definition,
                example_korean: d.example_korean,
                example_chinese: d.example_chinese
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
