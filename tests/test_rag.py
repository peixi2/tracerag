from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import KnowledgeDocument
from app.rag import ask, retrieve, tokenize


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_chinese_tokenization_contains_bigrams():
    tokens = tokenize("Webhook 重复消费如何处理")
    assert "重复" in tokens
    assert "消费" in tokens
    assert "webhook" in tokens


def test_retrieval_ranks_matching_document_first():
    db = session()
    db.add_all([
        KnowledgeDocument(doc_key="KB-1", title="Webhook 幂等", category="API", content="使用 event_id 去重并校验 HMAC 签名", owner="A"),
        KnowledgeDocument(doc_key="KB-2", title="数据备份", category="可靠性", content="每天执行全量备份", owner="B"),
    ])
    db.commit()
    result = retrieve(db, "Webhook 重复事件如何去重", include_tickets=False)
    assert result[0]["key"] == "KB-1"


def test_fallback_answer_has_sources(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    db = session()
    db.add(KnowledgeDocument(doc_key="KB-1", title="API 限流", category="API", content="返回 429 后使用指数退避", owner="A"))
    db.commit()
    result = ask(db, "API 返回 429 怎么办")
    assert result["mode"] == "GROUNDED_FALLBACK"
    assert result["sources"][0]["key"] == "KB-1"
    assert "【KB-1】" in result["answer"]
    assert len(result["trace"]) == 3
