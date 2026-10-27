# TraceRAG 架构说明

```text
Vue 3 SPA -> FastAPI/JWT -> SQLAlchemy -> MySQL
                    |
                    +-> query normalize
                    +-> BM25 retrieve + rank
                    +-> grounded generate -> DeepSeek (optional)
                                           -> deterministic fallback
                    +-> sources + trace + confidence
```

## 检索链路

1. Query rewrite：清理空白并抽取英文词、中文单字和双字词。
2. Retrieve：对知识文档和工单计算 BM25 分数。
3. Rank：按得分选择前 4 条并归一化相关度。
4. Generate：将问题和证据传给模型，或在失败时生成确定性摘要。
5. Grounding：返回来源、置信度、模式、traceId 和阶段耗时，并把轨迹写入 MySQL。

## 评测

- Recall@4：期望文档是否进入前 4 条。
- MRR：期望文档排名的倒数均值。
- Citation Coverage：回答是否绑定检索来源。

生产演进可增加文档切块、embedding、向量库、cross-encoder reranker、权限过滤、Prompt 版本和在线反馈，但不会用这些名词描述当前未部署能力。

