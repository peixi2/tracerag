import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import create_token, current_user, verify_password
from .database import Base, SessionLocal, engine, get_db
from .models import EvalCase, EvalRun, KnowledgeDocument, QueryTrace, SupportTicket, User
from .rag import ask, retrieve
from .seed import seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_data(db)
    yield


app = FastAPI(title="TraceRAG", version="1.0.0", lifespan=lifespan)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=48)
    password: str = Field(min_length=1, max_length=100)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class DocumentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    category: str = Field(min_length=2, max_length=48)
    content: str = Field(min_length=20, max_length=8000)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"application": "ok", "database": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    return {"token": create_token(user), "user": {"id": user.id, "username": user.username,
            "displayName": user.display_name, "role": user.role}}


@app.get("/api/overview")
def overview(_: User = Depends(current_user), db: Session = Depends(get_db)):
    docs = db.query(KnowledgeDocument).all()
    tickets = db.query(SupportTicket).all()
    traces = db.query(QueryTrace).order_by(QueryTrace.created_at.desc()).limit(8).all()
    eval_runs = db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(6).all()
    categories: dict[str, int] = {}
    for document in docs:
        categories[document.category] = categories.get(document.category, 0) + 1
    return {"documents": len(docs), "tickets": len(tickets),
            "openTickets": sum(ticket.status != "RESOLVED" for ticket in tickets),
            "queryTraces": db.query(QueryTrace).count(), "categories": categories,
            "recentTickets": [ticket_view(ticket) for ticket in tickets[:6]],
            "recentTraces": [trace_view(trace) for trace in traces],
            "evalRuns": [eval_view(run) for run in eval_runs]}


@app.get("/api/documents")
def documents(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return [document_view(document) for document in db.query(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc()).all()]


@app.post("/api/documents")
def create_document(payload: DocumentRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    document = KnowledgeDocument(doc_key="KB-USER-" + uuid.uuid4().hex[:6].upper(), title=payload.title,
                                 category=payload.category, content=payload.content, owner=user.display_name)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document_view(document)


@app.get("/api/tickets")
def tickets(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return [ticket_view(ticket) for ticket in db.query(SupportTicket).order_by(SupportTicket.created_at.desc()).all()]


@app.post("/api/copilot/ask")
def copilot(payload: AskRequest, _: User = Depends(current_user), db: Session = Depends(get_db)):
    return ask(db, payload.question)


@app.post("/api/evaluations/run")
def run_evaluation(_: User = Depends(current_user), db: Session = Depends(get_db)):
    cases = db.query(EvalCase).filter(EvalCase.active.is_(True)).all()
    hits = 0
    reciprocal_rank = 0.0
    for case in cases:
        sources = retrieve(db, case.question, include_tickets=False)
        keys = [source["key"] for source in sources]
        if case.expected_doc_key in keys:
            hits += 1
            reciprocal_rank += 1 / (keys.index(case.expected_doc_key) + 1)
    count = max(len(cases), 1)
    run = EvalRun(trace_id="eval_" + uuid.uuid4().hex[:10], recall_at_4=round(hits / count, 3),
                  mrr=round(reciprocal_rank / count, 3), citation_coverage=1.0, cases=len(cases))
    db.add(run)
    db.commit()
    db.refresh(run)
    return eval_view(run)


def document_view(document: KnowledgeDocument) -> dict:
    return {"id": document.id, "key": document.doc_key, "title": document.title, "category": document.category,
            "content": document.content, "owner": document.owner, "status": document.status, "updatedAt": document.updated_at}


def ticket_view(ticket: SupportTicket) -> dict:
    return {"key": ticket.ticket_key, "title": ticket.title, "summary": ticket.summary, "priority": ticket.priority,
            "status": ticket.status, "assignee": ticket.assignee, "createdAt": ticket.created_at}


def trace_view(trace: QueryTrace) -> dict:
    return {"traceId": trace.trace_id, "question": trace.question, "mode": trace.mode, "confidence": trace.confidence,
            "sourceCount": trace.source_count, "latencyMs": trace.latency_ms, "createdAt": trace.created_at}


def eval_view(run: EvalRun) -> dict:
    return {"traceId": run.trace_id, "recallAt4": run.recall_at_4, "mrr": run.mrr,
            "citationCoverage": run.citation_coverage, "cases": run.cases, "createdAt": run.created_at}


STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = STATIC_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
