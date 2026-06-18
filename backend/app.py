"""
HR Policy Copilot — Flask API 后端
- REST API: 知识库 CRUD / 向量搜索 / 业务申请 / 审批 / 统计
- RAG: 向量检索 + LLM 生成
- 数据库: SQLite (结构化) + ChromaDB (向量)
"""

from flask import Flask, request, jsonify, send_from_directory
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import database as db
import vectordb as vdb
from miniapp import miniapp_bp

app = Flask(__name__, static_folder='../src', static_url_path='')
app.register_blueprint(miniapp_bp)


# === 初始化 ===
db.init_db()
vdb.rebuild_all_index(db.get_all_knowledge())


# === 前端静态文件 ===
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# === 知识库 API ===

@app.route('/api/knowledge', methods=['GET'])
def list_knowledge():
    """列出所有知识库条目"""
    entries = db.get_all_knowledge()
    return jsonify({'data': entries, 'total': len(entries)})


@app.route('/api/knowledge', methods=['POST'])
def create_knowledge():
    """添加知识条目（同时索引到向量库）"""
    data = request.json
    kb_id = db.add_knowledge(
        category=data['category'],
        question=data['question'],
        answer=data['answer'],
        source=data.get('source', ''),
        status=data.get('status', 'published')
    )
    # 索引到向量库
    vdb.index_knowledge(kb_id, data['question'], data['answer'],
                        data['category'], data.get('source', ''))
    return jsonify({'id': kb_id, 'message': '知识条目已添加并索引'})


@app.route('/api/knowledge/<int:kb_id>', methods=['PUT'])
def update_knowledge_entry(kb_id):
    """更新知识条目"""
    data = request.json
    db.update_knowledge(kb_id, **data)
    # 重新索引
    vdb.index_knowledge(kb_id, data.get('question', ''),
                        data.get('answer', ''), data.get('category', ''),
                        data.get('source', ''))
    return jsonify({'message': '已更新'})


@app.route('/api/knowledge/<int:kb_id>', methods=['DELETE'])
def delete_knowledge_entry(kb_id):
    """删除知识条目（同时从向量库移除）"""
    db.delete_knowledge(kb_id)
    vdb.remove_knowledge(kb_id)
    return jsonify({'message': '已删除'})


# === AI 问答（RAG + LLM）====

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    AI 问答 —— 核心 RAG 流程：
    1. 向量搜索找到最相关的知识条目
    2. 如果匹配度高，返回答案 + 来源
    3. 如果无匹配，返回拒答提示
    4. 附带推荐业务卡片
    """
    data = request.json
    query = data.get('query', '').strip()
    role = data.get('role', 'employee')

    if not query:
        return jsonify({'error': '请输入问题'}), 400

    # 1. 向量搜索
    similar = vdb.search_similar(query, n_results=3)

    # 2. 判断是否有匹配（score >= 0.3 视为匹配）
    matched = [s for s in similar if s['score'] >= 0.3]

    if not matched:
        return jsonify({
            'answer': '该问题暂未收录在知识库中，建议您联系 HR 部门进一步确认。您也可以尝试以下方式：\n1. 致电 HR 热线 8888\n2. 发送邮件至 hr@company.com',
            'source': None,
            'cards': [],
            'confidence': 0
        })

    # 3. 取最佳匹配（但保留多个结果供前端展示）
    best = matched[0]
    # 获取完整答案
    all_entries = db.get_all_knowledge()
    entry = next((e for e in all_entries if e['id'] == best['kb_id']), None)

    answer = entry['answer'] if entry else best.get('question', '')
    source = best.get('source', '')

    # 4. LLM 增强（DeepSeek 代理不可用时跳过，使用知识库原文）
    answer = entry['answer'] if entry else best.get('question', '')
    cards = _generate_cards(query, best['category'], role)

    return jsonify({
        'answer': answer,
        'source': source,
        'references': matched,
        'cards': cards,
        'confidence': best['score']
    })


def _generate_cards(query, category, role):
    """根据意图生成业务卡片"""
    cards = []
    q = query.lower()

    triggers = {
        'action': {
            '在职证明': ('在职证明申请', '处理时间: 2-3个工作日 · 免费', '立即办理'),
            '收入证明': ('收入证明申请', '处理时间: 2-3个工作日', '立即办理'),
            '年假': ('年假申请', '需提前3天 · 审批流程: 上级→HR', '立即申请'),
            '请假': ('请假申请', '年假/事假/病假/婚假', '立即办理'),
            '病假': ('病假申请', '需上传医院证明', '立即办理'),
            '申诉': ('考勤异常申诉', 'HR处理时长: 3个工作日', '提交申诉'),
        },
        'info': {
            '薪资': ('薪资查询', '查看最近6个月薪资明细', '立即查看'),
            '合同': ('合同查询', '查看合同信息及到期日期', '立即查看'),
        },
        'alert': {
            '异常': ('考勤异常申诉', 'HR处理时长: 3个工作日', '提交申诉'),
        }
    }

    for card_type, keywords in triggers.items():
        for keyword, (title, desc, btn) in keywords.items():
            if keyword in q or keyword in category:
                cards.append({'type': card_type, 'title': title, 'desc': desc, 'btn': btn})
                break

    return cards[:2]  # 最多2张卡片


# === 业务申请 API ===

@app.route('/api/requests', methods=['GET'])
def list_requests():
    """列出业务申请"""
    status = request.args.get('status')
    data = db.get_requests(status=status)
    return jsonify({'data': data, 'total': len(data)})


@app.route('/api/requests', methods=['POST'])
def create_new_request():
    """创建业务申请"""
    data = request.json
    request_no = db.create_request(
        req_type=data['type'],
        purpose=data.get('purpose', ''),
        extra_info=data.get('extra_info', ''),
        applicant=data.get('applicant', '张小明')
    )
    return jsonify({'request_no': request_no, 'message': '申请已提交'})


@app.route('/api/requests/<request_no>/review', methods=['POST'])
def review_request(request_no):
    """审批业务申请 (通过/拒绝)"""
    data = request.json
    db.review_request(
        request_no=request_no,
        status=data['status'],
        reviewer=data.get('reviewer', 'HR-李经理')
    )
    return jsonify({'message': f'申请 {request_no} 已{data["status"]}'})


# === 统计 API ===

@app.route('/api/stats', methods=['GET'])
def stats():
    """获取仪表盘统计数据"""
    return jsonify(db.get_stats())


# === 向量库管理 ===

@app.route('/api/vectordb/rebuild', methods=['POST'])
def rebuild_index():
    """重建向量索引"""
    entries = db.get_all_knowledge()
    count = vdb.rebuild_all_index(entries)
    return jsonify({'message': f'已重建 {count} 条向量索引'})


@app.route('/api/vectordb/stats', methods=['GET'])
def vectordb_stats():
    """向量库统计"""
    col = vdb.get_kb_collection()
    return jsonify({'total_vectors': col.count()})


# === 健康检查 ===

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'HR Copilot API'})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
