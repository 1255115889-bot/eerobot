#!/usr/bin/env python3
"""云资源监控 — 每10分钟运行, 仅 >75% 时预警"""
import subprocess, json, sys
from datetime import datetime

def get(name, cmd, parse_fn):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
    return parse_fn(r.stdout.strip())

# CPU: load / cores
cores = int(get("cores", "nproc", lambda o: o))
load = float(get("load", "uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}'", lambda o: float(o.strip())))
cpu_pct = round(load / cores * 100, 1)

# Memory
mem = get("mem", "free | awk '/Mem:/{printf \"%.0f %.0f\", $3,$2}'",
    lambda o: (int(o.split()[0]), int(o.split()[1])))
mem_pct = round(mem[0] / mem[1] * 100, 1)

# Disk
disk = get("disk", "df / | awk 'NR==2{printf \"%.0f %.0f\", $3,$2}'",
    lambda o: (int(o.split()[0]), int(o.split()[1])))
disk_pct = round(disk[0] / disk[1] * 100, 1)

THRESHOLD = 75
alerts = []
if mem_pct >= THRESHOLD: alerts.append(f"内存 {mem_pct}%")
if cpu_pct >= THRESHOLD: alerts.append(f"CPU {cpu_pct}%")
if disk_pct >= THRESHOLD: alerts.append(f"磁盘 {disk_pct}%")

if alerts:
    now = datetime.now().strftime('%m-%d %H:%M')
    print(f"⚠️ {now} | {' | '.join(alerts)} | 详情: CPU核{cores}/{load}/{cpu_pct}% 内存{mem[1]/1024:.0f}G用{mem[0]/1024:.1f}G 磁盘{disk[1]/1024**2:.0f}G用{disk[0]/1024**2:.0f}G")
