# AI 全栈岗位要求与项目证据

本文将 2027 届 AI 应用与全栈岗位的常见要求映射到 TraceRAG 的可验证实现。调研时间为 2026 年 10 月，信息来源包括字节跳动、腾讯、阿里巴巴、美团和京东校园招聘入口，以及牛客公开面经。不同团队对模型训练、平台工程和应用开发的侧重点不同，应以投递当天的职位描述为准。

## 高频要求

| 岗位要求 | TraceRAG 中的证据 | 面试演示入口 |
| --- | --- | --- |
| Python Web 服务 | FastAPI、Pydantic、SQLAlchemy、JWT 与统一 API | 登录和 Swagger 接口 |
| AI 应用完整链路 | 查询分词、BM25 召回、证据排序、受约束回答 | 知识 Copilot |
| RAG 可解释性 | 最多四条来源、相关度、置信度和 traceId | 回答右侧证据面板 |
| 模型可靠性 | DeepSeek 可选网关，超时或未配置时确定性降级 | `GROUNDED_FALLBACK` 模式 |
| 评测意识 | 固定用例计算 Recall@4、MRR 和引用覆盖率并持久化 | 质量评测页面 |
| 全栈交付 | Vue 3 工作台、REST API、MySQL、Docker、Render | 四个完整业务视图 |
| 数据与产品闭环 | 文档新增、工单数据、查询轨迹和评测历史 | 新增文档后重新检索 |

## 可讲亮点

1. 项目不把“调用一次大模型 API”包装成 RAG，而是完整展示检索、证据、生成或降级、追踪和评测。
2. 回答受检索证据约束并携带来源；模型不可用时仍能基于证据返回确定性摘要，公开演示不会变成空白页。
3. Recall@4 与 MRR 分别衡量“正确文档是否被召回”和“正确文档是否排在前面”，评测结果写入数据库形成回归记录。
4. 当前检索明确采用 BM25，适合小型企业知识库和可解释演示，不冒充向量检索。

## 下一步演进

- 对文档分块生成 embedding，引入向量数据库并实现 BM25 与向量混合召回。
- 增加 cross-encoder 重排序、无答案评测和事实一致性评测。
- 使用 SSE 输出流式回答，并增加租户级 Token 预算、缓存和敏感信息过滤。

## 调研入口

- 字节跳动校园招聘：https://jobs.bytedance.com/campus
- 腾讯校园招聘：https://join.qq.com
- 阿里巴巴校园招聘：https://campus.alibaba.com
- 美团校园招聘：https://zhaopin.meituan.com/web/campus
- 京东校园招聘：https://campus.jd.com
- 牛客公开面经：https://www.nowcoder.com
