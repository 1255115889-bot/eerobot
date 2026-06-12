#!/usr/bin/env python3
"""eerobot 项目测试"""
import os

# 测试 HTML 文件
html_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'index.html')
with open(html_path) as f:
    html = f.read()

checks = ['countdown', 'cd-days', '2026-07-01']
for c in checks:
    assert c in html, f'MISSING: {c}'

print(f"✅ All {len(checks)} tests passed")
print(f"File: {len(html)} bytes, {html.count(chr(10))+1} lines")
