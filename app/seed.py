import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .auth import hash_password
from .models import EvalCase, KnowledgeDocument, SupportTicket, User


DOCUMENTS = [
    ("KB-AUTH-001", "企业 SSO 登录异常排查", "身份与权限", "SSO 登录失败时先确认租户域名与回调地址一致，再检查浏览器 SameSite Cookie、服务器时钟偏差和身份提供方证书有效期。若错误码为 invalid_redirect_uri，应在身份提供方白名单中加入生产 HTTPS 回调地址。", "周岚"),
    ("KB-BILL-002", "订阅续费与扣款失败处理", "计费", "自动续费失败通常由银行卡过期、余额不足或支付风控引起。系统会在第 1、3、7 天重试，并通过站内信和邮件通知管理员。宽限期为 7 天，期间数据保持可读。", "陈序"),
    ("KB-API-003", "开放 API 限流策略", "开发者平台", "标准版每个租户每分钟 600 次请求，专业版为 3000 次。超过配额返回 HTTP 429，并携带 Retry-After。客户端应使用指数退避和随机抖动，不应立即无间隔重试。", "顾思远"),
    ("KB-DATA-004", "数据导出与隐私脱敏规范", "数据安全", "导出成员数据需要管理员权限。手机号、邮箱和证件号默认脱敏，审计日志保留导出人、筛选条件和文件摘要。导出链接 24 小时后失效，禁止通过公共网盘长期共享。", "林然"),
    ("KB-WEBHOOK-005", "Webhook 重试与签名校验", "开发者平台", "Webhook 使用 HMAC-SHA256 签名。接收方应校验时间戳并以 event_id 做幂等；服务端在 10 秒未收到 2xx 时按指数退避重试，最多 8 次。重复事件的负载保持一致。", "周岚"),
    ("KB-BACKUP-006", "备份恢复与数据保留", "可靠性", "生产数据库每天全量备份并保留 14 天，事务日志支持 7 天内按时间点恢复。恢复演练每季度执行一次，恢复目标 RPO 15 分钟、RTO 2 小时。", "陈序"),
    ("KB-ROLE-007", "工作区角色与权限边界", "身份与权限", "Owner 可管理计费和成员；Admin 可管理配置与内容；Editor 可编辑知识库；Viewer 只读。权限在服务端按资源归属校验，前端隐藏按钮不能替代鉴权。", "顾思远"),
    ("KB-SEARCH-008", "知识检索质量调优", "AI 平台", "检索质量应分别评估 Recall@K、MRR 和无答案拒答。短查询先做术语扩展，长文档按语义段落切分；召回后可结合字段权重和更新时间排序，并要求回答携带来源。", "林然"),
    ("KB-AI-009", "生成式回答的幻觉控制", "AI 平台", "回答必须限制在检索证据范围内并返回来源。低置信度时明确拒答；提示词之外还需要检索评测、引用校验、敏感信息过滤和 traceId 追踪。模型超时应降级为确定性摘要。", "周岚"),
    ("KB-SLA-010", "故障等级与响应 SLA", "可靠性", "P0 表示核心服务完全不可用，5 分钟内响应；P1 为关键功能大面积受损，15 分钟内响应；P2 为局部功能异常，2 小时内响应。升级时需附 traceId、影响范围和首次发生时间。", "陈序"),
    ("KB-IMPORT-011", "批量导入失败项处理", "数据操作", "批量导入采用校验、预览、提交三阶段。错误行不会阻塞合法数据，系统生成失败明细。重复业务键采用幂等更新，超过 5000 行建议拆批并在低峰期执行。", "顾思远"),
    ("KB-TOKEN-012", "模型 Token 预算与成本控制", "AI 平台", "请求按租户设置日预算与单次最大 Token。上下文先去重再按相关度截断，缓存高频问题的检索结果。超出预算时切换轻量模型或返回基于证据的模板摘要。", "林然"),
]

TICKETS = [
    ("SUP-1042", "客户 SSO 回调地址校验失败", "客户更换域名后登录返回 invalid_redirect_uri，需要核对生产回调白名单。", "P1", "IN_PROGRESS", "周岚"),
    ("SUP-1039", "Webhook 偶发重复消费", "下游未按 event_id 去重，重试后产生两条通知。", "P1", "WAITING_CUSTOMER", "陈序"),
    ("SUP-1036", "专业版 API 出现 429", "单租户一分钟突发请求超过套餐配额，需要加入退避与抖动。", "P2", "IN_PROGRESS", "顾思远"),
    ("SUP-1032", "知识助手回答未展示来源", "旧版客户端未渲染 sources 字段，后端返回正常。", "P2", "RESOLVED", "林然"),
    ("SUP-1028", "数据导出链接提前失效", "用户设备时间偏差导致签名校验失败。", "P2", "RESOLVED", "周岚"),
    ("SUP-1025", "续费扣款失败", "银行卡已过期，客户处于 7 天宽限期。", "P1", "WAITING_CUSTOMER", "陈序"),
    ("SUP-1021", "批量导入部分行失败", "存在重复业务键与非法邮箱，已生成失败明细。", "P3", "RESOLVED", "顾思远"),
    ("SUP-1018", "模型日预算触顶", "租户大量重复提问，建议开启结果缓存并调整预算。", "P2", "IN_PROGRESS", "林然"),
]

EVAL_CASES = [
    ("EVAL-001", "SSO 登录提示 invalid_redirect_uri 怎么处理？", "KB-AUTH-001"),
    ("EVAL-002", "Webhook 为什么会重复，接收方应该怎么做？", "KB-WEBHOOK-005"),
    ("EVAL-003", "API 返回 429 后可以立即重试吗？", "KB-API-003"),
    ("EVAL-004", "数据库备份保留多久，RPO 是多少？", "KB-BACKUP-006"),
    ("EVAL-005", "怎样降低知识助手幻觉？", "KB-AI-009"),
    ("EVAL-006", "批量导入有错误行会全部失败吗？", "KB-IMPORT-011"),
]


def seed_data(db: Session) -> None:
    username = os.getenv("DEMO_USERNAME", "admin")
    password = os.getenv("DEMO_PASSWORD", "admin123")
    if not db.query(User).filter(User.username == username).first():
        db.add(User(username=username, password_hash=hash_password(password), display_name="林然", role="ADMIN"))
    for key, title, category, content, owner in DOCUMENTS:
        if not db.query(KnowledgeDocument).filter(KnowledgeDocument.doc_key == key).first():
            db.add(KnowledgeDocument(doc_key=key, title=title, category=category, content=content, owner=owner))
    for index, (key, title, summary, priority, status, assignee) in enumerate(TICKETS):
        if not db.query(SupportTicket).filter(SupportTicket.ticket_key == key).first():
            db.add(SupportTicket(ticket_key=key, title=title, summary=summary, priority=priority,
                                 status=status, assignee=assignee, created_at=datetime.utcnow() - timedelta(hours=index * 9 + 2)))
    for key, question, expected in EVAL_CASES:
        if not db.query(EvalCase).filter(EvalCase.case_key == key).first():
            db.add(EvalCase(case_key=key, question=question, expected_doc_key=expected, active=True))
    db.commit()
