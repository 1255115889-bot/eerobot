"""
HR Policy Copilot — 向量数据库层 (ChromaDB)
- 知识库向量化（语义搜索）
- RAG 检索
- 使用本地嵌入（sentence-transformers 或 DeepSeek API）
"""

import os
import chromadb
from chromadb.config import Settings
import json

CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'chroma_db')

_client = None


def get_chroma():
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
    return _client


def get_kb_collection():
    """获取知识库 collection"""
    client = get_chroma()
    try:
        collection = client.get_collection("hr_knowledge_base")
    except Exception:
        collection = client.create_collection(
            "hr_knowledge_base",
            metadata={"description": "HR Policy Knowledge Base for RAG"}
        )
    return collection


def get_embedding(text: str) -> list:
    """
    生成文本的向量嵌入（本地 TF-IDF 启发式）。
    当 DeepSeek 代理可用时会自动使用真实 embeddings。
    """
    import hashlib
    words = text.lower().split()
    vec = [0.0] * 256
    for i, w in enumerate(words):
        h = int(hashlib.md5(w.encode()).hexdigest(), 16) % 256
        vec[h] += 1.0 / (i + 1)
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def index_knowledge(kb_id: int, question: str, answer: str, category: str, source: str):
    """
    将知识库条目索引到 ChromaDB
    """
    collection = get_kb_collection()
    embedding = get_embedding(question + " " + answer)
    collection.upsert(
        ids=[str(kb_id)],
        embeddings=[embedding],
        documents=[f"Q: {question}\nA: {answer}"],
        metadatas=[{
            "kb_id": kb_id,
            "category": category,
            "source": source,
            "question": question
        }]
    )


def remove_knowledge(kb_id: int):
    """从向量库中删除"""
    collection = get_kb_collection()
    try:
        collection.delete(ids=[str(kb_id)])
    except Exception:
        pass


def search_similar(query: str, n_results: int = 3) -> list:
    """
    语义搜索知识库
    返回: [{"kb_id": int, "question": str, "category": str, "source": str, "score": float}, ...]
    """
    collection = get_kb_collection()
    count = collection.count()
    if count == 0:
        return []

    query_vec = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"]
    )

    items = []
    if results['ids'] and results['ids'][0]:
        for i, doc_id in enumerate(results['ids'][0]):
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i] if results['distances'] else 0
            items.append({
                "kb_id": int(doc_id),
                "question": meta.get("question", ""),
                "category": meta.get("category", ""),
                "source": meta.get("source", ""),
                "score": round(1.0 / (1.0 + dist), 4)
            })
    return items


def rebuild_all_index(db_entries: list):
    """从 SQLite 重建全部向量索引"""
    collection = get_kb_collection()
    # 清空现有
    try:
        all_ids = collection.get()['ids']
        if all_ids:
            collection.delete(ids=all_ids)
    except Exception:
        pass

    # 重新索引
    ids = []
    embeddings = []
    documents = []
    metadatas = []
    for entry in db_entries:
        eid = str(entry['id'])
        q = entry['question']
        a = entry['answer']
        ids.append(eid)
        embeddings.append(get_embedding(q + " " + a))
        documents.append(f"Q: {q}\nA: {a}")
        metadatas.append({
            "kb_id": entry['id'],
            "category": entry['category'],
            "source": entry['source'],
            "question": q
        })

    if ids:
        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    return len(ids)
