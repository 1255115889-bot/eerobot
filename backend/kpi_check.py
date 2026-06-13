#!/usr/bin/env python3
"""KPI 自动检查脚本 — 每小时运行，检查服务健康，计算得分"""

import sys
import json
import subprocess
from datetime import datetime

def check(label, cmd, pass_condition):
    """运行 shell 命令，返回 (passed, output)"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        out = r.stdout.strip() or r.stderr.strip()
        passed = pass_condition(r.returncode, out)
        return passed, out[:200]
    except Exception as e:
        return False, str(e)[:200]

def run_all():
    results = {}
    score = 100
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 3.1 Flask
    ok, out = check("Flask", "curl -s --max-time 5 http://127.0.0.1:5000/api/health",
                    lambda rc, out: '"status":"ok"' in out)
    results['flask'] = {'passed': ok, 'output': out}
    if not ok: score -= 10

    # 3.2 Nginx
    ok, out = check("Nginx", "curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://cccarolyn.top/ai-policy-advisor/",
                    lambda rc, out: '200' in out)
    results['nginx'] = {'passed': ok, 'output': out}
    if not ok: score -= 10

    # 3.3 DeepSeek
    ok, out = check("DeepSeek", "curl -s --max-time 5 http://127.0.0.1:8787/v1/models",
                    lambda rc, out: rc == 0 or 'status' in out.lower())
    results['deepseek'] = {'passed': ok, 'output': out}
    if not ok: score -= 3

    # 3.4 ChromaDB
    ok, out = check("ChromaDB", "curl -s --max-time 5 http://127.0.0.1:5000/api/vectordb/stats",
                    lambda rc, out: 'total_vectors' in out)
    results['chromadb'] = {'passed': ok, 'output': out}
    if not ok: score -= 5

    # 5.1 Git
    ok, out = check("GitPush", "cd /root/eerobot && git status --short",
                    lambda rc, out: rc == 0)
    results['git'] = {'passed': ok, 'output': out if out else 'clean'}

    report = {
        'timestamp': now,
        'score': max(0, score),
        'grade': '🟢' if score >= 90 else '🟡' if score >= 75 else '🟠' if score >= 60 else '🔴',
        'checks': results
    }

    # 只在有问题时打印
    if score < 100:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(run_all())
