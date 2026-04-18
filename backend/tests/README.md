# 单元测试


## 运行测试

```bash
# 在 backend/ 目录下执行
cd backend

# 运行全部单元测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_workflow_helpers.py -v
python -m pytest tests/test_crud.py -v

# 运行某个测试类
python -m pytest tests/test_workflow_helpers.py::TestSimplifyOcrResults -v

# 运行某个测试方法
python -m pytest tests/test_crud.py::TestComputeContentHash::test_unicode -v

# 只运行名称包含关键词的测试
python -m pytest tests/ -v -k "dedup"
```

## 测试文件说明

```
backend/tests/
├── conftest.py                  # pytest 配置，公共 fixture（db / make_question）
├── fixtures/                    # 测试数据
│   └── sample_ocr_data.json    # OCR 测试数据（split_integration 使用）
├── test_workflow_helpers.py     # workflow.py 纯函数测试
├── test_export.py               # export_wrongbook 导出测试
├── test_web_helpers.py          # web_app.py 纯函数测试
├── test_web_routes.py           # Flask 路由集成测试（内存数据库）
├── test_crud.py                 # 数据库 CRUD 测试
├── test_schemas.py              # Pydantic schema 校验测试
├── test_question_tools.py       # 题目工具函数测试
├── test_correct_node.py         # 纠错节点合并逻辑测试
├── test_utils.py                # 通用工具函数测试
├── test_benchmark_metrics.py    # benchmark 评测指标测试
├── test_solve_schemas.py        # 解题结果 schema 测试
├── test_ocr_api.py              # PaddleOCR API 集成测试（需要 API 配置）
├── test_split_integration.py    # 分割集成测试（需要 API Key）
└── test_solve_integration.py    # 解题集成测试（需要 API Key）
```

---

### test_utils.py

测试 `backend/src/utils.py` 中的通用工具函数：

| 测试类 | 被测函数 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestPrepareInput` | `prepare_input` | 6 | PDF 直接复制、图片直接复制（jpg/png）、文件不存在、格式不支持、自动创建目录 |

### test_workflow_helpers.py

测试 `backend/src/workflow.py` 和 `backend/src/utils.py` 中不依赖外部服务的纯函数：

| 测试类 | 被测函数 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestSimplifyOcrResults` | `_simplify_ocr_results` | 12 | OCR 原始数据简化：text/image/chart block 处理、bbox 路径生成、多页索引、字段过滤 |
| `TestBuildOverlappingBatches` | `_build_overlapping_batches` | 9 | 重叠批次构建：边界情况、不同页数/batch_size/overlap 组合 |
| `TestQuestionRichness` | `_question_richness` | 6 | 题目丰富度计算：content_blocks + options 字符数 |
| `TestSortKey` | `_sort_key` | 7 | 题号排序：数字优先、混合排序 |
| `TestDedupQuestions` | `_dedup_questions` | 9 | 按 question_id 去重：保留更丰富版本、空 id 跳过、输出排序 |
| `TestIdentifySubject` | `_identify_subject` | 15 | 科目识别：DB 优先匹配、关键词匹配、指标词推断、只读前 2 页、忽略非文本 block |
| `TestMergePages` | `PaddleOCRClient._merge_pages` | 4 | JSONL 多页合并：空输入、单页、多页合并、缺失 key 跳过 |
| `TestRunOcrAndSimplifyFileTypes` | `_run_ocr_and_simplify` | 5 | 混合文件分发：纯图片、纯 PDF、混合文件、大小写不敏感、空输入 |

### test_export.py

测试 `backend/src/utils.py` 中的 `export_wrongbook` 函数：

| 测试方法 | 说明 |
|----------|------|
| `test_basic_export` | 基本导出，选中题目出现在输出中 |
| `test_filter_selected_ids` | 只导出用户选中的题目 |
| `test_empty_selection` | 空选择时生成空错题本 |
| `test_options_rendered` | 选项正确渲染 |
| `test_image_block_rendered` | image block 渲染为 markdown 图片 |
| `test_question_type_shown` | 题目类型显示 |
| `test_answer_sections_present` | 包含答案/解析等固定区域 |
| `test_image_refs_fallback` | image_refs 兜底渲染未覆盖的图片 |
| `test_image_refs_not_duplicated` | 已渲染的图片不重复出现 |
| `test_multiple_questions_numbered` | 多题编号正确 |

### test_web_helpers.py

测试 `backend/web_app.py` 中不依赖 Flask 请求上下文的纯函数：

| 测试类 | 被测函数 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestAllowedFile` | `allowed_file` | 11 | 文件扩展名校验：合法格式、非法格式、大小写、多点文件名、空字符串 |
| `TestSafeJoin` | `_safe_join` | 6 | 路径安全拼接：正常路径、目录遍历攻击（`../`）、空路径 |
| `TestViteCollectImports` | `_vite_collect_imports` | 7 | Vite manifest 依赖收集：线性链、循环依赖、菱形依赖、缺失入口 |

### test_crud.py

测试 `backend/db/crud.py` 中所有 CRUD 函数，使用 **SQLite 内存数据库**（每个测试用例独立数据库）：

| 测试类 | 被测函数 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestComputeContentHash` | `compute_content_hash` | 8 | 哈希计算：text block 拼接、忽略 image block、空列表回退 JSON、Unicode |
| `TestGetOrCreateTag` | `get_or_create_tag` | 3 | 标签创建/获取：新建、复用、同名不同科目 |
| `TestSaveQuestionsToDB` | `save_questions_to_db` | 5 | 批量入库：基本保存、内容哈希去重、空内容跳过、标签关联、默认科目 |
| `TestQuestionExists` | `question_exists` | 2 | 题目存在性检查 |
| `TestGetExistingSubjects` | `get_existing_subjects` | 2 | 科目查询：空库、去重 |
| `TestGetExistingTagNames` | `get_existing_tag_names` | 3 | 标签名查询：空库、返回结果、按科目筛选 |
| `TestGetQuestionsBySubject` | `get_questions_by_subject` | 3 | 按科目查题：空结果、筛选、分页 |
| `TestGetQuestionsByTag` | `get_questions_by_tag` | 2 | 按标签查题 |
| `TestGetAllTags` | `get_all_tags` | 2 | 获取全部标签：空库、按科目筛选 |
| `TestGetStatistics` | `get_statistics` | 2 | 统计信息：空库、有数据 |

### test_schemas.py

测试 `backend/error_correction_agent/schemas.py` 中 Pydantic 模型的校验逻辑：

| 测试类 | 被测模型 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestContentBlock` | `ContentBlock` | 4 | text/image block、非法类型拒绝、缺字段拒绝 |
| `TestQuestion` | `Question` | 8 | 最小构造、4 种题型、非法题型拒绝、选项/图片/标签/OCR 标记 |
| `TestQuestionSplitResult` | `QuestionSplitResult` | 2 | 空列表、包含题目 |
| `TestCorrectedQuestion` | `CorrectedQuestion` | 2 | 正常构造、缺 corrections_applied 拒绝 |
| `TestCorrectionResult` | `CorrectionResult` | 2 | 空列表、包含纠错结果 |

### test_question_tools.py

测试 `backend/error_correction_agent/tools/question_tools.py` 中的文件 I/O 工具（使用 `tmp_path`）：

| 测试类 | 被测函数 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestSaveQuestions` | `save_questions` | 4 | 新建文件、追加数据、科目元数据保存、空科目不生成元数据 |
| `TestLogIssue` | `log_issue` | 3 | 基本记录、附带 block_info、多次追加（JSONL 格式）|

### test_correct_node.py

测试 `backend/src/workflow.py` 中 `correct_questions_node` 的合并逻辑（mock 纠错工具）：

| 测试方法 | 说明 |
|----------|------|
| `test_skip_when_no_questions` | 空题目列表直接跳过 |
| `test_skip_when_no_flagged` | 无 needs_correction 标记时跳过 |
| `test_merge_corrected` | 纠错结果按 question_id 合并回原列表，未标记题目不受影响 |
| `test_invalid_json_keeps_original` | 纠错返回无效 JSON 时保留原始题目 |

### test_benchmark_metrics.py

测试 `backend/benchmark/metrics.py` 中的评测指标函数：

| 测试类 | 被测函数 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestNormalizeAnswer` | `normalize_answer` | 10 | 空白去除、选择题字母大写+排序、判断题统一格式、普通文本原样返回 |
| `TestCompareAnswers` | `compare_answers` | 9 | 大小写、多选排序无关、判断题跨格式比较、空白容忍 |
| `TestComputeAccuracy` | `compute_accuracy` | 7 | 空结果、全对、全错、混合、分题型统计、未知题型兜底 |

### test_solve_schemas.py

测试 `backend/solve_agent/schemas.py` 中解题结果 Pydantic 模型：

| 测试类 | 被测模型 | 用例数 | 说明 |
|--------|----------|--------|------|
| `TestSolveResult` | `SolveResult` | 4 | 最小构造、自定义 confidence、缺 answer 拒绝、缺 reasoning 拒绝 |
| `TestSolveBatchResult` | `SolveBatchResult` | 3 | 空列表、包含结果、model_dump 完整性 |

### test_ocr_api.py

**集成测试**：验证 PaddleOCR V2 异步任务 API 的连通性与结果格式兼容性。需要配置 `PADDLEOCR_API_URL`、`PADDLEOCR_API_TOKEN`。测试文件使用 `example_uploads/` 下的 `test.jpg`（图片）和 `test4.pdf`（PDF）。

```bash
pytest tests/test_ocr_api.py -v -s
```

| 测试类 | 用例数 | 说明 |
|--------|--------|------|
| `TestImageApiConnection` | 4 | 图片 API 连通性：任务提交、完成、结果 URL、提取进度 |
| `TestImageResultFormat` | 7 | 图片结果格式：layoutParsingResults / prunedResult / parsing_res_list 结构、block 必填字段、markdown 输出、block_label 类型 |
| `TestPdfApiConnection` | 3 | PDF API 连通性：任务提交、完成、多页解析 |
| `TestPdfResultFormat` | 3 | PDF 结果格式：非空结果、layoutParsingResults 结构、block 必填字段 |
| `TestOcrClientImage` | 3 | PaddleOCRClient 图片解析：parse_image 返回值、_struct.json 保存、simplify_ocr_results 兼容 |
| `TestOcrClientPdf` | 3 | PaddleOCRClient PDF 解析：parse_pdf 返回值、simplify_ocr_results 兼容、多页 page_index 连续性 |

> **注意**：此测试会消耗 API 配额。图片和 PDF 各使用 module 级 fixture 共享一次 API 调用（`Connection` + `ResultFormat` 测试类共享），`OcrClient*` 测试类独立调用客户端方法验证端到端流程。无 API 配置或测试文件缺失时自动 skip。

---

### test_split_integration.py

**集成测试**：调用真实大模型 API 验证 `split_batch` 的分割效果。需要配置对应的 API Key 环境变量。

通过 `--model-provider` 参数指定模型供应商：

```bash
# 使用 deepseek（默认）
python -m pytest tests/test_split_integration.py -v -s

# 使用文心一言
python -m pytest tests/test_split_integration.py -v -s --model-provider ernie
```

| 测试方法 | 说明 |
|----------|------|
| `test_returns_non_empty` | 至少分割出一道题目 |
| `test_question_schema` | 每道题符合 Question Pydantic schema |
| `test_covers_all_questions` | 覆盖 OCR 数据中所有题号 |
| `test_choice_questions_have_options` | 选择题包含选项 |
| `test_formula_detection` | 含 LaTeX 的题目标记 has_formula |
| `test_knowledge_tags` | 至少一半题目有知识点标注 |

> **注意**：此测试会消耗 API 配额，使用 session 级 fixture 共享一次调用结果以减少开销。测试数据来自 `tests/fixtures/sample_ocr_data.json`。

### test_solve_integration.py

**集成测试**：调用真实 LLM API 验证解题智能体的解题能力。需要配置 API Key 环境变量。

```bash
# 使用 deepseek（默认）
python -m pytest tests/test_solve_integration.py -v -s

# 使用文心一言
python -m pytest tests/test_solve_integration.py -v -s --model-provider ernie
```

| 测试方法 | 说明 |
|----------|------|
| `test_returns_all_answers` | 返回与输入题目数量相同的答案 |
| `test_question_ids_match` | question_id 与输入一致 |
| `test_choice_answer_correct` | 选择题（集合交集）答案正确 |
| `test_fill_answer_correct` | 填空题（2³+3²）答案正确 |
| `test_judge_answer_correct` | 判断题（π是有理数）答案正确 |
| `test_has_reasoning` | 每道题包含非空推理过程 |
| `test_confidence_in_range` | 置信度在 0-1 范围内 |

> **注意**：使用 session 级 fixture 共享一次 API 调用（3 道题：选择题+填空题+判断题），减少配额消耗。

---

## 测试范围与设计原则

**纯函数优先**：优先测试不依赖外部服务的确定性函数，输入相同则输出一定相同。

**数据库测试用内存 SQLite**：`test_crud.py` 使用 `sqlite:///:memory:`，每个测试用例独立数据库，不写磁盘、不污染环境。

**文件 I/O 测试用 tmp_path**：`test_question_tools.py` 和 `test_export.py` 使用 pytest 的 `tmp_path` fixture，测试完自动清理。

**需要 mock 的场景**：`test_correct_node.py` mock 了 `correct_batch` 工具调用，只测试节点自身的筛选/合并逻辑。


**新增函数时**：请在对应测试文件中补充测试用例，保持覆盖率。
