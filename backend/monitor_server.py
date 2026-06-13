#!/usr/bin/env python3
"""阿里云服务器资源监控 —— 超 75% 阈值才报警，静默运行"""

import subprocess
import sys

THRESHOLD = 75
ALERTS = []

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, timeout=10).strip()
    except Exception as e:
        ALERTS.append(f"⚠️ 监控命令失败: {cmd[:50]}... -> {e}")
        return ""

# --- CPU ---
cpu_raw = run("top -bn1 | grep 'Cpu(s)' | awk '{print $2+$4+$6}'")
if cpu_raw:
    try:
        cpu = float(cpu_raw)
        if cpu > THRESHOLD:
            ALERTS.append(f"🔴 CPU使用率 {cpu:.1f}% (阈值 {THRESHOLD}%)")
    except ValueError:
        pass

# --- Memory ---
mem_raw = run("free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2}'")
if mem_raw:
    try:
        mem = float(mem_raw)
        if mem > THRESHOLD:
            ALERTS.append(f"🔴 内存使用率 {mem:.1f}% (阈值 {THRESHOLD}%)")
    except ValueError:
        pass

# --- Disk ---
disk_raw = run("df -h / | awk 'NR==2{gsub(/%/,\"\",$5); print $5}'")
if disk_raw:
    try:
        disk = float(disk_raw)
        if disk > THRESHOLD:
            ALERTS.append(f"🔴 磁盘使用率 {disk:.1f}% (阈值 {THRESHOLD}%)")
    except ValueError:
        pass

# --- Processes ---
load_raw = run("uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs")
if load_raw:
    try:
        load = float(load_raw)
        procs = run("nproc")
        cores = int(procs) if procs else 1
        load_pct = (load / cores) * 100
        if load_pct > THRESHOLD:
            ALERTS.append(f"🔴 CPU负载 {load} (平均/{cores}核 = {load_pct:.1f}%, 阈值 {THRESHOLD}%)")
    except ValueError:
        pass

# --- Top processes if anything is high ---
top_procs = []
if ALERTS:
    top = run("ps aux --sort=-%cpu | head -6 | awk '{print $3\"% \"$11}'")
    if top:
        top_procs.append(f"Top CPU: {top}")

# --- Result ---
if ALERTS:
    report = "🚨 服务器资源告警 🚨\n\n"
    report += "\n".join(ALERTS)
    if top_procs:
        report += "\n\n" + "\n".join(top_procs)
    report += f"\n\n一键检查: ssh到服务器运行 'htop'"
    print(report)
    sys.exit(1)

# 静默 — 一切正常
sys.exit(0)
