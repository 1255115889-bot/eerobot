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


# ====== 微信服务器验证（回调 URL） ======

WX_VERIFY_TOKEN = "HermesWxBot2026"


@miniapp_bp.route('/weixin', methods=['GET', 'POST'])
def weixin_callback():
    """微信服务器回调：GET 验证接入 / POST 接收消息"""
    import xml.etree.ElementTree as ET

    signature = request.args.get('signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')

    # SHA1 签名校验
    tmp_list = sorted([WX_VERIFY_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list)
    calc = hashlib.sha1(tmp_str.encode()).hexdigest()
    if calc != signature:
        return 'signature mismatch', 403

    # GET 请求 — 接入验证
    if request.method == 'GET':
        return request.args.get('echostr', '')

    # POST 请求 — 接收用户消息
    xml_data = request.data.decode('utf-8')
    root = ET.fromstring(xml_data)
    msg_type = root.find('MsgType')
    msg_type = msg_type.text if msg_type is not None else 'text'

    from_user = root.find('FromUserName')
    to_user = root.find('ToUserName')
    from_user = from_user.text if from_user is not None else ''
    to_user = to_user.text if to_user is not None else ''

    if msg_type == 'text':
        content = root.find('Content')
        query = content.text if content is not None else ''

        # 调用 RAG 获取回答
        try:
            resp = httpx.post(
                "http://127.0.0.1:5000/api/chat",
                json={"query": query, "role": "employee"},
                timeout=15
            )
            ai_data = resp.json()
            reply = ai_data.get('answer', '抱歉，我暂时无法回答这个问题。')
            if ai_data.get('source'):
                reply += f"\n\n📋 {ai_data['source']}"
        except Exception:
            reply = 'AI 服务暂时不可用，请稍后再试。'

        return _build_text_reply_xml(from_user, to_user, reply)

    # 默认回复
    return _build_text_reply_xml(from_user, to_user, '您好！发送文字即可与我对话 😊')


def _build_text_reply_xml(to_user, from_user, content):
    return f'''<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>'''


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

