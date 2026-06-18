"""
微信小程序后端 API
- 登录：wx.login() code → openid → token
- 聊天：转发到 HR Copilot RAG API
- 知识库：简化列表
"""

import hashlib
import time
import httpx
from flask import Blueprint, request, jsonify
import database as db

miniapp_bp = Blueprint('miniapp', __name__, url_prefix='/api/miniapp')

WX_APPID = "wx605c33df1d030593"
WX_SECRET = "f575875a6ffda494d44ca8596677bc68"

# 简单内存 session（生产环境应换 Redis）
_sessions = {}  # token → {"openid": str, "expires": int}


def _make_token(openid: str) -> str:
    return hashlib.sha256(f"{openid}:{time.time()}".encode()).hexdigest()


@miniapp_bp.route('/login', methods=['POST'])
def login():
    """
    微信小程序登录
    1. 用 code 向微信服务器换取 openid
    2. 生成 token 返回给小程序
    """
    code = request.json.get('code', '') if request.json else ''
    if not code:
        return jsonify({'error': 'code 不能为空'}), 400

    # 调用微信官方接口换取 openid
    try:
        resp = httpx.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                'appid': WX_APPID,
                'secret': WX_SECRET,
                'js_code': code,
                'grant_type': 'authorization_code'
            },
            timeout=10
        )
        wx_data = resp.json()
    except Exception as e:
        return jsonify({'error': f'微信服务调用失败: {e}'}), 502

    if 'errcode' in wx_data and wx_data['errcode'] != 0:
        return jsonify({'error': wx_data.get('errmsg', '登录失败')}), 401

    openid = wx_data.get('openid')
    token = _make_token(openid)
    _sessions[token] = {
        'openid': openid,
        'expires': int(time.time()) + 86400 * 7  # 7天有效
    }

    return jsonify({
        'token': token,
        'openid': openid[:8] + '***',  # 部分脱敏
        'expires_in': 86400 * 7
    })


def _check_token():
    """校验 token 是否有效"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token or token not in _sessions:
        return None
    if time.time() > _sessions[token]['expires']:
        del _sessions[token]
        return None
    return _sessions[token]


@miniapp_bp.route('/chat', methods=['POST'])
def chat():
    """小程序聊天 — 转发到 HR Copilot RAG"""
    session = _check_token()
    if not session:
        return jsonify({'error': '未登录或 token 已过期'}), 401

    query = request.json.get('query', '').strip() if request.json else ''
    if not query:
        return jsonify({'error': '请输入问题'}), 400

    # 调用本地 RAG API
    try:
        resp = httpx.post(
            "http://127.0.0.1:5000/api/chat",
            json={"query": query, "role": "employee"},
            timeout=15
        )
        data = resp.json()
    except Exception as e:
        return jsonify({'error': f'AI 服务异常: {e}'}), 503

    # 简化返回格式（小程序适配）
    return jsonify({
        'answer': data.get('answer', ''),
        'source': data.get('source', ''),
        'cards': data.get('cards', []),
        'confidence': data.get('confidence', 0)
    })

