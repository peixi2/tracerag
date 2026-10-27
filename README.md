# TraceRAG

面向 2027 届 AI 全栈岗位的可溯源企业知识助手。项目覆盖知识库管理、BM25 检索、证据排序、受约束回答、执行轨迹和离线评测，并提供完整 Vue 3 工作台。

- 在线演示：https://tracerag-demo.onrender.com
- 演示账号：`admin` / `admin123`
- 技术栈：Python 3.12、FastAPI、SQLAlchemy、MySQL、Vue 3、BM25、DeepSeek 兼容接口、Docker、Render

## 核心能力

- 对知识文档和支持工单进行中英文分词、BM25 召回与相关性排序。
- Copilot 返回最多 4 条来源、相关度、置信度、traceId 和三阶段耗时。
- 可选接入 DeepSeek；未配置、超时或限流时使用确定性 grounded fallback，公开演示始终可用。
- 固定评测集计算 Recall@4、MRR 和引用覆盖率，结果持久化到数据库。
- JWT 认证、知识文档新增、查询轨迹与评测历史均写入云 MySQL。
- 内置 12 篇知识文档、8 条支持工单和 6 条评测用例，打开即有真实使用痕迹。

## 本地运行

```bash
docker compose up --build
```

访问 http://localhost:8000。

## 测试

```bash
pytest -q
```

## 文档

- [使用与演示路线](docs/USAGE_GUIDE.md)
- [RAG 架构与评测](docs/ARCHITECTURE.md)
- [AI 全栈面试问答](docs/INTERVIEW_GUIDE.md)
- [岗位要求与项目证据](docs/JOB_ALIGNMENT.md)

## 真实性边界

当前检索器是可解释的 BM25，不冒充向量检索。仓库没有声称已经部署向量数据库、重排序模型或 SSE；这些能力在架构文档中作为下一阶段演进方案说明。

