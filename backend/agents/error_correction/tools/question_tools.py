"""
题目处理相关工具
"""

import os
import json
import logging
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from core.config import settings
from src.utils import simplify_ocr_results, run_async

load_dotenv()
logger = logging.getLogger(__name__)


def _retry_invoke(fn, prompt, provider, task_name, max_retries=3):
    """带指数退避的 LLM 调用重试

    Args:
        fn: 调用函数，签名为 fn(prompt, provider=provider)
        prompt: 用户 prompt
        provider: 模型供应商
        task_name: 任务名称（用于日志）
        max_retries: 最大重试次数

    Returns:
        结构化输出结果

    Raises:
        RuntimeError: 所有重试均失败
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            structured = fn(prompt, provider=provider)
            if structured:
                return structured
            last_error = "未获得 structured_response"
            logger.warning(f"{task_name}: 第 {attempt} 次未获得 structured_response，重试")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"{task_name}: 第 {attempt}/{max_retries} 次失败: {last_error}")

        if attempt < max_retries:
            wait = 2 ** attempt  # 2s, 4s
            logger.info(f"{task_name}: 等待 {wait}s 后重试...")
            time.sleep(wait)

    raise RuntimeError(f"{task_name}: {max_retries} 次尝试均失败: {last_error}")

@tool(parse_docstring=True)
def save_questions(questions: List[Dict[str, Any]], subject: str = "", output_path: str = None) -> str:
    """保存分割后的题目列表到JSON文件

    将Agent分割后的题目列表保存为结构化JSON文件，供后续步骤使用。
    同时保存科目等元数据到 split_metadata.json，供导出入库时使用。

    Args:
        questions: 题目列表，每个题目是一个字典，包含question_id、question_type、content_blocks等字段
        subject: 识别出的试卷科目（如 "高中数学"），每次调用都应传入
        output_path: 输出文件路径，如果不提供则使用默认路径（settings.results_dir/questions.json）

    Returns:
        保存成功的文件路径
    """
    logger.info(f"save_questions called: {len(questions)} questions, subject={subject}")
    try:
        # 使用默认路径
        if output_path is None:
            os.makedirs(settings.results_dir, exist_ok=True)
            output_path = os.path.join(settings.results_dir, "questions.json")

        # 读取已有数据（支持多次调用追加）
        existing = []
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        # 合并已有数据和新数据
        all_questions = existing + questions

        # 保存JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=2)

        # 保存元数据（科目信息供导出入库时使用）
        if subject.strip():
            meta_path = os.path.join(settings.results_dir, "split_metadata.json")
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            meta["subject"] = subject.strip()
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

        msg = f"成功保存 {len(questions)} 道题目（总计 {len(all_questions)} 道）到: {output_path}"
        logger.info(f"save_questions done: {msg}")
        return msg

    except Exception as e:
        msg = f"保存失败: {str(e)}"
        logger.error(f"save_questions error: {msg}")
        return msg


@tool(parse_docstring=True)
def log_issue(issue_type: str, description: str, block_info: Dict[str, Any] = None) -> str:
    """记录题目分割过程中遇到的问题

    当Agent在分割题目时遇到不确定或异常情况时，使用此工具记录问题，
    以便后续人工审核或改进算法。

    Args:
        issue_type: 问题类型，如 "unclear_boundary"（边界不清）、"missing_question_number"（缺少题号）、
                   "complex_structure"（复杂结构）等
        description: 问题描述，详细说明遇到的情况
        block_info: 相关block信息（可选），包含block_id、content等

    Returns:
        记录结果消息
    """
    try:
        os.makedirs(settings.results_dir, exist_ok=True)
        log_path = os.path.join(settings.results_dir, "split_issues.jsonl")

        # 构建日志条目
        log_entry = {
            "issue_type": issue_type,
            "description": description,
        }
        if block_info:
            log_entry["block_info"] = block_info

        # 追加到JSONL文件
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        return f"问题已记录: {issue_type}"

    except Exception as e:
        return f"记录失败: {str(e)}"


@tool(parse_docstring=True)
def split_batch(ocr_data: str, subject: str = "", existing_tags: str = "", model_provider: str = "openai", model_name: str = "") -> str:
    """对一批OCR数据进行题目分割，返回结构化题目列表JSON

    将1-2页的OCR数据发送给内层分割智能体（create_agent + ToolStrategy），
    返回经过Pydantic校验的结构化题目列表。

    Args:
        ocr_data: 一批OCR数据的JSON字符串，包含1-2页的blocks数据
        subject: 试卷所属科目（如 "高中数学"、"初中物理"），用于辅助知识点标注
        existing_tags: 前面批次已使用的知识点标签，用逗号分隔（如 "复数,集合,立体几何"），用于保持标签一致性
        model_provider: 模型供应商，"openai"（默认）或 "anthropic"
        model_name: 指定模型名称（可选），为空时使用 provider 默认模型

    Returns:
        题目列表的JSON字符串，如 '[{"question_id": "1", ...}, ...]'
    """
    logger.info(f"split_batch called (provider={model_provider}, model={model_name or 'default'})")

    tags_instruction = ""
    if subject.strip() or existing_tags.strip():
        tags_instruction = "\n**知识点标注上下文**："
        if subject.strip():
            tags_instruction += f"\n- 本试卷科目：{subject}"
        if existing_tags.strip():
            tags_instruction += f"\n- 已有知识点标签池（请优先复用）：{existing_tags}"

    prompt = f"""请分析以下OCR识别结果，将其分割为独立的题目。

每页的数据结构：
- page_index: 页码索引
- blocks: 内容块列表，每个 block 有 block_label、block_content、block_order 三个字段

请按 page_index 和 block_order 顺序处理，返回结构化的题目列表。
{tags_instruction}

OCR数据：
{ocr_data}"""

    from ..agent import invoke_split

    effective_model = model_name if model_name else None

    try:
        structured = _retry_invoke(
            lambda p, provider: invoke_split(p, provider=provider, model_name=effective_model),
            prompt, model_provider, "split_batch",
        )
        questions = [q.model_dump() for q in structured.questions]
        logger.info(f"split_batch done: {len(questions)} questions")
        return json.dumps(questions, ensure_ascii=False)
    except RuntimeError as e:
        logger.error(str(e))
        return f"分割失败: {e}"


@tool(parse_docstring=True)
def correct_batch(questions_json: str, ocr_context: str, model_provider: str = "openai", model_name: str = "") -> str:
    """对一批疑似OCR错误的题目进行纠错，返回纠错后的题目列表JSON

    将标记了 needs_correction 的题目发送给内层纠错智能体（create_agent + ToolStrategy），
    返回经过Pydantic校验的纠错结果。

    Args:
        questions_json: 待纠错题目列表的JSON字符串
        ocr_context: 对应页面的原始OCR数据JSON字符串，作为纠错参考上下文
        model_provider: 模型供应商，"openai"（默认）或 "anthropic"
        model_name: 指定模型名称（可选），为空时使用 provider 默认模型

    Returns:
        纠错后的题目列表JSON字符串
    """
    logger.info(f"correct_batch called (provider={model_provider}, model={model_name or 'default'})")

    from ..agent import invoke_correction

    effective_model = model_name if model_name else None

    prompt = f"""请修复以下题目中的 OCR 错误。

## 待纠错题目
{questions_json}

## 原始 OCR 参考数据
以下是这些题目对应页面的原始 OCR block 数据，可作为纠错参考：
{ocr_context}

请逐题修复标记的 OCR 问题，输出纠错后的结构化数据。"""

    try:
        structured = _retry_invoke(
            lambda p, provider: invoke_correction(p, provider=provider, model_name=effective_model),
            prompt, model_provider, "correct_batch",
        )
        corrected = [q.model_dump() for q in structured.corrected_questions]
        logger.info(f"correct_batch done: {len(corrected)} questions corrected")
        return json.dumps(corrected, ensure_ascii=False)
    except RuntimeError as e:
        logger.error(str(e))
        return f"纠错失败: {e}"


@tool(parse_docstring=True)
def retry_ocr(image_paths_json: str) -> str:
    """当 OCR 中间件解析失败时，手动重试 OCR 解析

    此工具供编排智能体在 OCR 中间件失败后调用。
    它会重新执行 PaddleOCR 解析、简化结果、保存 agent_input.json，
    并返回可直接传给 split_batch 的 OCR 数据 JSON。

    Args:
        image_paths_json: 图片路径列表的 JSON 字符串，如 '["path/to/img1.png", "path/to/img2.png"]'

    Returns:
        简化后的 OCR 数据 JSON 字符串，可直接传给 split_batch 的 ocr_data 参数
    """
    logger.info("retry_ocr called")
    try:
        image_paths = json.loads(image_paths_json)
        if not isinstance(image_paths, list) or not image_paths:
            return "错误: image_paths_json 必须是非空的路径列表 JSON"

        from src.paddleocr_client import PaddleOCRClient

        client = PaddleOCRClient()

        # 执行异步 OCR（兼容已有事件循环）
        ocr_results = run_async(
            client.parse_images_async(image_paths, save_output=True)
        )

        # 简化 OCR 结果
        simplified = simplify_ocr_results(ocr_results)

        # 保存 agent_input.json
        os.makedirs(settings.results_dir, exist_ok=True)
        agent_input_path = os.path.join(settings.results_dir, "agent_input.json")
        with open(agent_input_path, 'w', encoding='utf-8') as f:
            json.dump(simplified, f, ensure_ascii=False, indent=2)

        total_blocks = sum(len(r.get("blocks", [])) for r in simplified)
        logger.info(f"retry_ocr done: {len(simplified)} pages, {total_blocks} blocks")

        return json.dumps(simplified, ensure_ascii=False)

    except Exception as e:
        logger.error(f"retry_ocr error: {str(e)}")
        return f"OCR 重试失败: {str(e)}"
