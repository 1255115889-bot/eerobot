# HR Copilot Demo — 部署说明

## 一、服务器信息

| 项目 | 详情 |
|------|------|
| 云平台 | 阿里云 |
| OS | Ubuntu 24.04 |
| 公网 IP | 47.253.87.142 |
| 内网 IP | 172.22.51.250 |
| 域名 | cccarolyn.top (HTTPS, Let's Encrypt) |
| 项目路径 | /root/eerobot |

---

## 二、技术架构

```
                    浏览器
                HTTPS :443
                      │
                 ┌────▼────┐
                 │  Nginx  │
                 │ :80/443 │
                 └─┬───┬───┘
        /ai-policy- │   │ /api/*
        advisor/*   │   │
    ┌───────────────▼┐ ┌─▼──────────────┐
    │  静态 SPA       │ │  Flask :5000    │
    │  (index.html)   │ │  REST API       │
    └────────────────┘ └─┬──────────┬────┘
                         │          │
                  ┌──────▼───┐ ┌───▼────────┐
                  │  SQLite  │ │  ChromaDB   │
                  │  数据库   │ │  向量数据库  │
                  └──────────┘ └─────────────┘
```

---

## 三、项目结构

```
/root/eerobot/
├── src/
│   └── index.html          # 前端 SPA (7 页面)
├── backend/
│   ├── app.py              # Flask API 主入口 (8 端点)
│   ├── database.py         # SQLite 数据层 (3 表)
│   ├── vectordb.py         # ChromaDB 向量层 (RAG)
│   └── requirements.txt
├── data/
│   ├── hr_copilot.db       # SQLite 数据库
│   └── chroma_db/          # ChromaDB 持久化向量
└── .gitignore
```

---

## 四、环境依赖

| 依赖 | 版本/来源 | 说明 |
|------|-----------|------|
| Python 3 | 3.12.3 (系统) | Ubuntu 24.04 自带 |
| Flask | apt: python3-flask | Web 框架 |
| ChromaDB | pip3 (--break-system-packages) | 向量数据库 |
| httpx | pip3 (--break-system-packages) | HTTP 客户端 |
| Nginx | 1.24 (apt) | 反向代理 + 静态文件 |

### 安装后端起手式

```bash
# 安装 ChromaDB (如未安装)
pip3 install chromadb httpx --break-system-packages

# 验证关键模块
python3 -c "import flask; print('Flask:', flask.__version__)"
python3 -c "import chromadb; print('ChromaDB OK')"
```

---

## 五、启动与停止

### 启动 Flask 后端

```bash
cd /root/eerobot && python3 backend/app.py &
```

进程默认监听 `127.0.0.1:5000`。

### 验证后端

```bash
# 健康检查
curl http://127.0.0.1:5000/api/health
# 返回: {"status":"ok","service":"HR Copilot API"}

# 测试 RAG 问答
curl -X POST http://127.0.0.1:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"年假怎么申请"}'
```

### 停止后端

```bash
pkill -f "python3 backend/app.py"
```

---

## 六、Nginx 配置

配置文件: `/etc/nginx/sites-available/hr-policy`

关键配置段：

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name cccarolyn.top;

    ssl_certificate /etc/letsencrypt/live/cccarolyn.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cccarolyn.top/privkey.pem;

    root /var/www/hr-policy;

    # SPA 应用
    location /ai-policy-advisor {
        alias /var/www/hr-policy/ai-policy-advisor;
        try_files $uri $uri/ /ai-policy-advisor/index.html;
    }

    # API 代理到 Flask
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 部署/重载 Nginx

```bash
# 复制前端文件
sudo cp /root/eerobot/src/index.html /var/www/hr-policy/ai-policy-advisor/index.html

# 验证配置
sudo nginx -t

# 重载
sudo systemctl reload nginx
```

---

## 七、数据库说明

### SQLite (结构化数据)

路径: `/root/eerobot/data/hr_copilot.db`

| 表名 | 字段 | 说明 |
|------|------|------|
| `knowledge_base` | id, category, question, answer, source, status | 知识库(8条预置) |
| `business_requests` | id, request_no, applicant, type, status | 业务申请 |
| `employees` | id, name, role, department, email | 员工信息(2条预置) |

### ChromaDB (向量数据)

路径: `/root/eerobot/data/chroma_db/`

| 项目 | 值 |
|------|-----|
| Collection 名 | `hr_knowledge_base` |
| 向量维度 | 256 (TF-IDF 启发式) |
| 条目数 | 8 |

> 当 DeepSeek 代理 (`:8787`) 恢复后，将自动切换为真实 embedding。

---

## 八、API 端点清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/knowledge` | 知识库列表 |
| POST | `/api/knowledge` | 添加条目(+向量索引) |
| PUT | `/api/knowledge/<id>` | 更新条目 |
| DELETE | `/api/knowledge/<id>` | 删除条目(+清向量) |
| POST | `/api/chat` | AI 问答(RAG) |
| GET | `/api/requests` | 业务申请列表 |
| POST | `/api/requests` | 创建申请 |
| POST | `/api/requests/<no>/review` | 审批(approved/rejected) |
| GET | `/api/stats` | 统计数据 |

---

## 九、访问地址

| 用途 | 地址 |
|------|------|
| 🌐 生产环境 | https://cccarolyn.top/ai-policy-advisor/ |
| 🖥️ 直连(公网) | http://47.253.87.142:8081 |
| 📡 API | https://cccarolyn.top/api/ |
| 📦 代码仓库 | https://github.com/1255115889-bot/eerobot |

---

## 十、常见问题

### 1. 前端页面能打开但 AI 问答无响应
→ 检查 Flask 后端是否运行: `curl http://127.0.0.1:5000/api/health`

### 2. Flask 启动时卡住
→ 如 DeepSeek 代理 `:8787` 宕机，embedding 需等待超时。当前已改为纯本地模式，秒级启动。

### 3. 如何重置数据库
```bash
rm /root/eerobot/data/hr_copilot.db
rm -rf /root/eerobot/data/chroma_db/
# 重启 Flask，数据库自动重建并预置条目
```

### 4. 向量搜索精度低 (匹配度 ~33%)
→ 当前使用本地 TF-IDF 启发式(256维)。待 DeepSeek 代理恢复后自动切换真实 embedding，精度可提升至 80%+。
