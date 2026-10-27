import math
import os
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from .models import KnowledgeDocument, QueryTrace, SupportTicket


@dataclass
class SearchItem:
    key: str
    title: str
    content: str
    category: str
    kind: str


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    english = re.findall(r"[a-z0-9_\-]+", lowered)
    chinese_blocks = re.findall(r"[\u4e00-\u9fff]+", lowered)
    chinese: list[str] = []
    for block in chinese_blocks:
        chinese.extend(list(block))
        chinese.extend(block[i:i + 2] for i in range(len(block) - 1))
    return english + chinese


def retrieve(db: Session, question: str, limit: int = 4, include_tickets: bool = True) -> list[dict]:
    items = [SearchItem(d.doc_key, d.title, d.content, d.category, "KNOWLEDGE")
             for d in db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "PUBLISHED").all()]
    if include_tickets:
        items.extend(SearchItem(t.ticket_key, t.title, t.summary, t.priority, "TICKET")
                     for t in db.query(SupportTicket).all())
    query_tokens = tokenize(question)
    docs = [tokenize(f"{item.title} {item.content} {item.category}") for item in items]
    if not query_tokens or not docs:
        return []
    avg_length = sum(map(len, docs)) / len(docs)
    document_frequency = Counter(token for tokens in docs for token in set(tokens))
    scored = []
    for item, tokens in zip(items, docs):
        counts = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            if not counts[token]:
                continue
            idf = math.log(1 + (len(docs) - document_frequency[token] + 0.5) / (document_frequency[token] + 0.5))
            tf = counts[token]
            score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * len(tokens) / max(avg_length, 1)))
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda value: value[0], reverse=True)
    top = scored[:limit]
    max_score = top[0][0] if top else 1
    return [{"key": item.key, "title": item.title, "category": item.category, "kind": item.kind,
             "snippet": item.content[:180], "score": round(score / max_score, 3)} for score, item in top]


def fallback_answer(question: str, sources: list[dict]) -> str:
    if not sources:
        return "当前知识库中没有足够证据回答这个问题。请补充产品模块、错误码或具体场景后重试。"
    lines = [f"根据当前知识库，关于“{question}”可以确认："]
    for source in sources[:3]:
        sentence = re.split(r"[。；]", source["snippet"])[0].strip()
        lines.append(f"- {sentence}。【{source['key']}】")
    lines.append("以上结论仅来自列出的内部资料；如需执行变更，请按对应文档的权限与审计要求操作。")
    return "\n".join(lines)


def model_answer(question: str, sources: list[dict]) -> tuple[str, str]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or not sources:
        return fallback_answer(question, sources), "GROUNDED_FALLBACK"
    context = "\n\n".join(f"[{s['key']}] {s['title']}\n{s['snippet']}" for s in sources)
    try:
        response = httpx.post(
            os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), "temperature": 0.2,
                  "messages": [
                      {"role": "system", "content": "你是企业知识助手。只能依据提供的证据回答，每个关键结论必须引用 [资料编号]，证据不足时明确拒答。"},
                      {"role": "user", "content": f"问题：{question}\n\n证据：\n{context}"}
                  ]}, timeout=httpx.Timeout(18, connect=5))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"], "DEEPSEEK"
    except Exception:
        return fallback_answer(question, sources), "GROUNDED_FALLBACK"


def ask(db: Session, question: str) -> dict:
    trace_id = "tr_" + uuid.uuid4().hex[:12]
    started = time.perf_counter()
    stage_started = time.perf_counter()
    normalized = re.sub(r"\s+", " ", question.strip())
    rewrite_ms = int((time.perf_counter() - stage_started) * 1000)
    stage_started = time.perf_counter()
    sources = retrieve(db, normalized)
    retrieve_ms = int((time.perf_counter() - stage_started) * 1000)
    stage_started = time.perf_counter()
    answer, mode = model_answer(normalized, sources)
    generate_ms = int((time.perf_counter() - stage_started) * 1000)
    total_ms = int((time.perf_counter() - started) * 1000)
    confidence = round(sum(source["score"] for source in sources[:2]) / max(2, min(len(sources), 2)), 3) if sources else 0
    trace = [
        {"stage": "QUERY_REWRITE", "durationMs": rewrite_ms, "detail": f"标准化问题并抽取 {len(set(tokenize(normalized)))} 个检索词"},
        {"stage": "RETRIEVE_RANK", "durationMs": retrieve_ms, "detail": f"BM25 召回并排序 {len(sources)} 条证据"},
        {"stage": "GROUNDED_GENERATE", "durationMs": generate_ms, "detail": f"{mode} 模式生成并绑定引用"},
    ]
    db.add(QueryTrace(trace_id=trace_id, question=normalized, mode=mode, confidence=confidence,
                      source_count=len(sources), latency_ms=total_ms))
    db.commit()
    return {"traceId": trace_id, "answer": answer, "mode": mode, "confidence": confidence,
            "latencyMs": total_ms, "sources": sources, "trace": trace}

