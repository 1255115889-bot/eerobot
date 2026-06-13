"""
HR Policy Copilot — 数据库层 (SQLite)
- 知识库表
- 审批/申请表
- 员工信息表
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'hr_copilot.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """创建所有表并插入预置数据"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT DEFAULT 'published' CHECK(status IN ('draft','published','archived')),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS business_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_no TEXT UNIQUE NOT NULL,
            applicant TEXT NOT NULL DEFAULT '张小明',
            type TEXT NOT NULL,
            purpose TEXT,
            extra_info TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
            reviewer TEXT,
            reviewed_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'employee' CHECK(role IN ('employee','hr_admin')),
            department TEXT,
            email TEXT
        );
    """)

    # 插入预置知识库条目
    entries = [
        ('休假政策', '年假怎么申请？',
         '员工每年享有 5-15 天带薪年假（根据工龄）。请通过 OA 系统「休假管理」提交申请，需提前 3 个工作日。审批流程：直属上级 → HR 确认。',
         '《员工手册》第 3.2 节 · 休假管理制度'),
        ('证明文件', '在职证明怎么开？',
         '在职证明可通过 HR Copilot 在线申请或 OA 系统「证明文件」模块办理。2-3 个工作日内开具，电子版发送至您的官方邮箱。',
         '《行政管理制度》第 5.1 节 · 证明文件管理'),
        ('薪资', '薪资什么时候发？',
         '每月 15 日发放上月薪资（遇节假日顺延至下一个工作日）。薪资明细可在 OA「我的薪资」中查看。',
         '《薪酬管理制度》第 2.1 节 · 薪资发放'),
        ('合同', '怎么查看我的合同？',
         '登录 OA 系统 → 个人信息 → 合同管理，可查看或下载您的劳动合同。合同到期前 30 天系统自动提醒。',
         '《劳动合同管理制度》第 4 节 · 合同查询'),
        ('出勤', '考勤异常怎么处理？',
         '发现考勤异常（缺卡/迟到/早退），可在 OA「考勤管理」提交异常申诉。HR 将在 3 个工作日内处理。每月有 3 次补卡机会。',
         '《考勤管理制度》第 6 节 · 异常处理'),
        ('证明文件', '收入证明怎么开？',
         '收入证明申请流程与在职证明类似。通过 HR Copilot 或 OA 提交，选择「收入证明」类型。包含月收入信息，2-3 个工作日开具。',
         '《行政管理制度》第 5.2 节'),
        ('休假政策', '病假怎么请？',
         '病假需提供二级甲等及以上医院开具的病假证明。医疗期内按工龄比例发放薪资。通过 OA「休假管理」-「病假」提交并上传医院证明。',
         '《考勤与休假管理制度》第 4 节 · 病假管理'),
        ('休假政策', '请假流程是什么？',
         '通过 OA「休假管理」提交申请，根据类别（年假/事假/病假/婚假等）有不同审批流程。年假按工龄计算，病假需医院证明。',
         '《考勤与休假管理制度》第 2-5 节'),
    ]

    existing = conn.execute("SELECT COUNT(*) FROM knowledge_base").fetchone()[0]
    if existing == 0:
        conn.executemany(
            "INSERT INTO knowledge_base (category, question, answer, source) VALUES (?, ?, ?, ?)",
            entries
        )

    # 插入预置员工
    emp_existing = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if emp_existing == 0:
        conn.executemany("INSERT INTO employees (name, role, department, email) VALUES (?, ?, ?, ?)", [
            ('张小明', 'employee', '技术部', 'zhangxm@company.com'),
            ('HR-李经理', 'hr_admin', '人力资源部', 'hr_li@company.com'),
        ])

    conn.commit()
    conn.close()


# === 知识库操作 ===

def get_all_knowledge():
    conn = get_db()
    rows = conn.execute("SELECT * FROM knowledge_base ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_knowledge(category, question, answer, source, status='published'):
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = conn.execute(
        "INSERT INTO knowledge_base (category, question, answer, source, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (category, question, answer, source, status, now, now)
    )
    conn.commit()
    kb_id = cur.lastrowid
    conn.close()
    return kb_id


def update_knowledge(kb_id, **kwargs):
    conn = get_db()
    allowed = {'category', 'question', 'answer', 'source', 'status'}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        conn.close()
        return
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE knowledge_base SET {set_clause} WHERE id=?", (*updates.values(), kb_id))
    conn.commit()
    conn.close()


def delete_knowledge(kb_id):
    conn = get_db()
    conn.execute("DELETE FROM knowledge_base WHERE id=?", (kb_id,))
    conn.commit()
    conn.close()


# === 业务申请操作 ===

def create_request(req_type, purpose='', extra_info='', applicant='张小明'):
    conn = get_db()
    import random
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    request_no = f"REQ-{now[:10].replace('-','')}-{random.randint(1000,9999)}"
    conn.execute(
        "INSERT INTO business_requests (request_no, applicant, type, purpose, extra_info, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (request_no, applicant, req_type, purpose, extra_info, now)
    )
    conn.commit()
    conn.close()
    return request_no


def get_requests(status=None):
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM business_requests WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM business_requests ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def review_request(request_no, status, reviewer='HR-李经理'):
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "UPDATE business_requests SET status=?, reviewer=?, reviewed_at=? WHERE request_no=?",
        (status, reviewer, now, request_no)
    )
    conn.commit()
    conn.close()


# === 统计 ===

def get_stats():
    conn = get_db()
    total_kb = conn.execute("SELECT COUNT(*) FROM knowledge_base WHERE status='published'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM business_requests WHERE status='pending'").fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM business_requests WHERE status='approved'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM business_requests WHERE status='rejected'").fetchone()[0]
    conn.close()
    return {'total_kb': total_kb, 'pending': pending, 'approved': approved, 'rejected': rejected}
