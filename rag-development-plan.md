# 错题库与笔记 RAG 开发方案

## 目标

为现有错题库检索和 AI 对话能力加入真正的 RAG 能力，使系统可以根据用户问题自动召回相关错题、笔记和知识点上下文，并把可追溯的引用内容提供给大模型生成回答。

当前项目已有两个可复用基础：

- 错题库已有轻量向量雏形：`backend/db/crud/questions.py` 中的 `local-hash-v1` 和 `QuestionEmbedding`。
- AI 对话已有手动引用上下文能力：`backend/routes/chat.py` 中的 `_build_project_context()` 可将用户选中的错题拼入 prompt。

本方案的核心改造是：将“手动引用 + 本地 hash 检索”升级为“真实 embedding + 自动召回 + 可评估的上下文注入”。

## 建设范围

### 1. 错题库检索模块

将现有 `/api/error-bank/find` 从本地 hash 相似度升级为语义检索。

需要索引的错题字段：

- 题干文本
- 选项
- 答案与解析
- 学科
- 题型
- 知识点标签
- 用户作答或错因记录，若后续有该字段

建议第一版继续使用 SQLite 存储向量，避免一开始引入复杂向量库。数据量超过单用户 5 万 chunk 或检索 P95 延迟超过验收阈值后，再切换 FAISS、Chroma 或 Qdrant。

### 2. 笔记模块

给笔记建立可检索索引，使 AI 回答可以结合用户自己的学习笔记。

需要索引的笔记字段：

- 笔记标题
- `content_markdown`
- `ocr_text`
- 学科
- 知识点标签
- 所属项目

笔记建议按段落切块，每块 300-800 中文字符，保留标题和标签作为 metadata。

## 推荐数据模型

优先新增统一索引表，而不是分别维护 `QuestionEmbedding` 和 `NoteEmbedding` 两套逻辑。

建议表名：`rag_document_chunks`

核心字段：

- `id`
- `user_id`
- `project_id`
- `source_type`: `question` 或 `note`
- `source_id`: 原始错题或笔记 ID
- `chunk_index`
- `content`: 用于 embedding 和注入 prompt 的文本
- `metadata_json`: 学科、题型、知识点、标题等
- `content_hash`: 判断是否需要重建索引
- `embedding_model`
- `vector_json`: 第一版可直接存 JSON 数组
- `created_at`
- `updated_at`

保留现有 `QuestionEmbedding` 可作为过渡，但新检索服务应优先读取统一 chunk 表。

## 后端模块设计

建议新增：

`backend/core/rag.py`

职责：

- `build_question_chunks(question)`: 将错题转换为可索引文本块
- `build_note_chunks(note)`: 将笔记切块
- `embed_texts(texts, provider=None)`: 批量生成 embedding
- `index_question(db, question_id)`: 建立或刷新错题索引
- `index_note(db, note_id)`: 建立或刷新笔记索引
- `retrieve_context(db, query, user_id, project_id=None, source_types=None, top_k=6)`: 统一召回
- `format_rag_context(results)`: 转成 AI 对话可注入的引用上下文

建议新增或调整接口：

- `POST /api/rag/reindex`: 管理员或开发调试用，重建当前用户/项目索引
- `GET /api/error-bank/find`: 复用 RAG 检索能力，替换 hash 检索
- `POST /api/chat/<session_id>/stream`: 在用户未手动引用资料时，自动调用 `retrieve_context`

## 索引触发点

错题索引：

- `save_questions_to_db()` 成功保存题目后触发
- 题目编辑、答案更新、知识点更新后触发
- 删除题目时删除对应 chunk

笔记索引：

- 新建或更新笔记后触发
- OCR 文本更新后触发
- 删除笔记时删除对应 chunk

第一版可以同步生成索引；如果保存接口变慢，再改为后台任务。

## AI 对话接入方式

当前流程：

用户手动选择错题 -> 前端发送 `context_refs` -> 后端按 ID 查内容 -> 注入 prompt

目标流程：

1. 用户发送问题。
2. 后端检查是否有手动 `context_refs`。
3. 如果没有手动引用，调用 `retrieve_context()` 自动召回错题和笔记。
4. 将召回结果放入 `<reference_material>`。
5. 大模型回答时要求优先基于引用内容，并在必要时说明引用来源。

建议策略：

- 手动引用优先级最高。
- 自动 RAG 只补充上下文，不覆盖手动引用。
- 召回结果必须按用户和项目权限过滤。
- 每条引用保留 `source_type/source_id/title/score`，便于前端展示来源。

## 验收指标

### 检索效果指标

需要准备一套离线评测集，建议不少于 200 条查询。

评测集来源：

- 用户自然语言描述：“我想找那道关于二次函数顶点式的题”
- 题干改写
- 知识点查询
- 错因描述
- 笔记主题查询

每条查询标注 1-3 条正确目标错题或笔记。

验收线：

- `Recall@5 >= 75%`: 前 5 条召回中包含至少一条标注正确结果。
- `Recall@10 >= 85%`
- `MRR@10 >= 0.55`: 正确结果越靠前越好。
- `Context Precision@5 >= 55%`: 前 5 条中相关内容比例不低于 55%。
- 无权限数据泄漏率 `0%`。

### 对话回答指标

抽样不少于 100 条 AI 对话问题，其中 50 条需要依赖错题库或笔记上下文。

验收线：

- RAG 命中率 `>= 80%`: 需要上下文的问题中，系统成功召回至少一条相关资料。
- 引用有效率 `>= 85%`: AI 实际使用的引用内容与问题相关。
- 回答可溯源率 `>= 90%`: 需要引用时，回答能对应到具体错题或笔记来源。
- 幻觉引用率 `<= 3%`: 不允许编造不存在的题目、笔记或知识点。
- 人工评分平均分 `>= 4/5`: 从相关性、准确性、解释清晰度三项打分。

### 性能指标

第一版 SQLite 向量检索验收线：

- 单用户 1 万 chunk 内，检索 P95 延迟 `<= 800ms`。
- 单用户 5 万 chunk 内，检索 P95 延迟 `<= 2000ms`。
- AI 对话因 RAG 增加的额外 P95 延迟 `<= 1500ms`。
- 索引生成成功率 `>= 99%`。
- 题目或笔记更新后，索引可用时间 `<= 5s`。

如果超过以上延迟，应评估迁移到专用向量库。

### 数据一致性指标

- 新增题目后，对应 chunk 覆盖率 `100%`。
- 更新题目或笔记后，旧 content hash 不应继续作为有效索引。
- 删除题目或笔记后，关联 chunk 删除率 `100%`。
- 不同用户、不同项目之间检索隔离测试全部通过。

## 分阶段实施

### 第一期：错题库 RAG

目标：

- 新增统一 chunk 表。
- 实现真实 embedding 生成和 SQLite top-k 检索。
- 将 `/api/error-bank/find` 接入 RAG 检索。

验收：

- `Recall@5 >= 75%`
- `Recall@10 >= 85%`
- 错题新增、更新、删除时索引同步正确

### 第二期：AI 对话自动召回

目标：

- `stream_chat()` 自动根据用户消息召回错题上下文。
- 保留手动引用优先级。
- 回答中可展示引用来源。

验收：

- RAG 命中率 `>= 80%`
- 回答可溯源率 `>= 90%`
- 幻觉引用率 `<= 3%`

### 第三期：笔记 RAG

目标：

- 笔记切块与索引。
- 对话召回同时支持错题和笔记。
- 错题解析时可结合笔记内容。

验收：

- 笔记查询 `Recall@5 >= 70%`
- 混合查询中错题和笔记均可被召回
- 笔记更新后索引 5 秒内刷新

### 第四期：混合检索与排序优化

目标：

- 结合关键词、知识点过滤、embedding 相似度和 recency。
- 支持按项目、学科、题型过滤。
- 需要时加入 reranker。

验收：

- `MRR@10 >= 0.65`
- `Context Precision@5 >= 65%`
- 检索 P95 延迟仍满足性能指标

## 风险与约束

- embedding provider 未配置时，需要降级到现有 `local-hash-v1`，但前端和日志应标识为“降级检索”。
- 向量 JSON 存 SQLite 适合第一版，数据量增大后性能会下降。
- RAG 召回内容可能增加 token 成本，需要限制 `top_k` 和总字符数。
- 用户数据隔离必须优先于召回效果，所有检索必须带 `user_id/project_id` 过滤。

## 建议默认参数

- `top_k`: 6
- 单条 chunk 长度：300-800 中文字符
- 注入 prompt 的总上下文上限：8000-12000 字符
- 相似度阈值：先用 `0.25` 起步，按评测集调参
- 混合排序初始权重：embedding `0.70`，关键词 `0.20`，知识点/学科过滤 `0.10`

