"""
评测主逻辑

加载题目和标准答案，调用不同模型解题，对比正确率。

用法:
    cd backend
    python -m benchmark.evaluate                          # 默认评测全部模型
    python -m benchmark.evaluate --provider openai        # 只评测 openai
    python -m benchmark.evaluate --provider anthropic     # 只评测 anthropic
"""

import os
import json
import logging
import argparse
from typing import List, Dict, Any

from .metrics import compare_answers, compute_accuracy

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TARGET_DIR = os.path.join(DATA_DIR, "target")
BENCHMARK_RESULTS_DIR = os.path.join(DATA_DIR, "results")


def load_targets(subject: str = None) -> List[Dict[str, Any]]:
    """从 target/{科目}/{试卷名}.json 加载所有标准答案

    可通过 subject 参数筛选特定科目。
    """
    if not os.path.isdir(TARGET_DIR):
        raise FileNotFoundError(
            f"标准答案目录不存在: {TARGET_DIR}\n"
            f"请先运行 python -m benchmark.collect 采集数据"
        )

    targets = []
    for root, _dirs, files in os.walk(TARGET_DIR):
        rel = os.path.relpath(root, TARGET_DIR)
        if subject and subject not in rel:
            continue
        for fname in sorted(files):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                targets.extend(json.load(f))

    logger.info(f"加载 {len(targets)} 道标准答案")
    return targets


def run_evaluation(provider: str, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """对指定模型进行评测

    Args:
        provider: 模型供应商 "openai" 或 "anthropic"
        targets: 标准答案列表

    Returns:
        评测报告 dict
    """
    from agents.solve import invoke_solve

    # 提取题目数据
    questions = []
    for t in targets:
        if "question" in t:
            questions.append(t["question"])
        else:
            # 最小题目结构
            questions.append({
                "question_id": t["question_id"],
                "question_type": t.get("question_type", "解答题"),
                "content_blocks": [{"block_type": "text", "content": t.get("content", "")}],
            })

    logger.info(f"开始评测: provider={provider}, 题目数={len(questions)}")
    solve_result = invoke_solve(questions, provider=provider)

    # 构建答案映射
    predicted_map = {r.question_id: r for r in solve_result.results}

    # 逐题对比
    results = []
    for t in targets:
        qid = t["question_id"]
        predicted = predicted_map.get(qid)
        if predicted is None:
            logger.warning(f"模型未返回题目 {qid} 的答案")
            results.append({
                "question_id": qid,
                "question_type": t.get("question_type", "未知"),
                "predicted": "",
                "target": t["answer"],
                "correct": False,
                "reasoning": "",
                "confidence": 0.0,
            })
            continue

        correct = compare_answers(predicted.answer, t["answer"])
        results.append({
            "question_id": qid,
            "question_type": t.get("question_type", "未知"),
            "predicted": predicted.answer,
            "target": t["answer"],
            "correct": correct,
            "reasoning": predicted.reasoning,
            "confidence": predicted.confidence,
        })

    report = compute_accuracy(results)
    report["provider"] = provider
    report["details"] = results

    return report


def save_report(report: Dict[str, Any], provider: str) -> str:
    """保存评测报告"""
    os.makedirs(BENCHMARK_RESULTS_DIR, exist_ok=True)
    path = os.path.join(BENCHMARK_RESULTS_DIR, f"report_{provider}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def print_report(report: Dict[str, Any]):
    """打印评测报告"""
    provider = report["provider"]
    print(f"\n{'='*50}")
    print(f"模型: {provider}")
    print(f"总正确率: {report['overall_accuracy']:.1%} ({report['correct']}/{report['total']})")
    print(f"{'─'*50}")
    for qtype, stats in report["by_type"].items():
        print(f"  {qtype}: {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")
    print(f"{'='*50}")

    # 打印错题详情
    wrong = [d for d in report["details"] if not d["correct"]]
    if wrong:
        print(f"\n错误题目 ({len(wrong)} 道):")
        for d in wrong:
            print(f"  题 {d['question_id']}: 预测={d['predicted']}, 标准={d['target']}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="解题模型评测")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default=None,
                        help="指定评测模型，不指定则评测全部")
    parser.add_argument("--subject", "-s", default=None,
                        help="筛选科目关键词（如 '高中数学'），不指定则全部")
    args = parser.parse_args()

    targets = load_targets(subject=args.subject)
    providers = [args.provider] if args.provider else ["openai", "anthropic"]

    for provider in providers:
        try:
            report = run_evaluation(provider, targets)
            path = save_report(report, provider)
            print_report(report)
            print(f"报告已保存: {path}")
        except Exception as e:
            logger.error(f"{provider} 评测失败: {e}")
            print(f"\n{provider} 评测失败: {e}")


if __name__ == "__main__":
    main()
