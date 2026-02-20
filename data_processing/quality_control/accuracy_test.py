"""
数据质量检查脚本 (Data Quality Control)

用于评估 OCR 识别结果的准确率，使用以下核心指标：
- 编辑距离 (Levenshtein Distance)
- 字错率 (Character Error Rate, CER)
- 词错率 (Word Error Rate, WER)
"""

import os
import re
from typing import Tuple, Dict, List
from difflib import SequenceMatcher


class LevenshteinDistance:
    """编辑距离计算器"""
    
    @staticmethod
    def calculate(s1: str, s2: str) -> int:
        """
        计算两个字符串的编辑距离（Levenshtein Distance）
        
        编辑距离：从一个字符串转换为另一个字符串所需的最少操作次数
        （插入、删除、替换）
        
        Args:
            s1: 字符串 1
            s2: 字符串 2
            
        Returns:
            int: 编辑距离
        """
        if len(s1) < len(s2):
            return LevenshteinDistance.calculate(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        # 动态规划计算
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # 插入、删除、替换的成本
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


class OCRQualityMetrics:
    """OCR 质量评估指标"""
    
    @staticmethod
    def character_error_rate(predicted: str, ground_truth: str) -> float:
        """
        字错率 (Character Error Rate, CER)
        
        CER = (S + D + I) / N
        其中：
        - S：替换错误数
        - D：删除错误数
        - I：插入错误数
        - N：Ground Truth 总字符数
        
        Args:
            predicted: OCR 输出文本
            ground_truth: 标准文本
            
        Returns:
            float: 字错率（0-1）
        """
        if len(ground_truth) == 0:
            return 0.0 if len(predicted) == 0 else 1.0
        
        edit_distance = LevenshteinDistance.calculate(predicted, ground_truth)
        cer = edit_distance / len(ground_truth)
        return min(cer, 1.0)  # CER 最多为 1.0
    
    @staticmethod
    def word_error_rate(predicted: str, ground_truth: str) -> float:
        """
        词错率 (Word Error Rate, WER)
        
        WER 基于分词后的编辑距离
        
        Args:
            predicted: OCR 输出文本
            ground_truth: 标准文本
            
        Returns:
            float: 词错率（0-1）
        """
        # 简单分词：按空格和标点符号分割
        pred_words = re.findall(r'\w+', predicted)
        gt_words = re.findall(r'\w+', ground_truth)
        
        if len(gt_words) == 0:
            return 0.0 if len(pred_words) == 0 else 1.0
        
        edit_distance = LevenshteinDistance.calculate(
            ' '.join(pred_words),
            ' '.join(gt_words)
        )
        wer = edit_distance / len(gt_words)
        return min(wer, 1.0)
    
    @staticmethod
    def accuracy(predicted: str, ground_truth: str) -> float:
        """
        准确率 (Accuracy)
        
        Accuracy = (匹配字符数) / (Ground Truth 总字符数)
        
        Args:
            predicted: OCR 输出文本
            ground_truth: 标准文本
            
        Returns:
            float: 准确率（0-1）
        """
        cer = OCRQualityMetrics.character_error_rate(predicted, ground_truth)
        return 1.0 - cer


class BenchmarkEvaluator:
    """基准测试评估器"""
    
    def __init__(self, benchmark_dir: str):
        """
        初始化评估器
        
        Args:
            benchmark_dir: benchmark 目录路径
        """
        self.benchmark_dir = benchmark_dir
        self.raw_dir = os.path.join(benchmark_dir, 'raw')
        self.gt_dir = os.path.join(benchmark_dir, 'ground_truth')
    
    def load_annotations(self) -> Dict[str, str]:
        """
        加载所有 Ground Truth 标注
        
        Returns:
            Dict: {图像名称: 标注文本}
        """
        annotations = {}
        if not os.path.exists(self.gt_dir):
            print(f"警告：Ground Truth 目录不存在：{self.gt_dir}")
            return annotations
        
        for filename in os.listdir(self.gt_dir):
            if filename.endswith('_gt.txt'):
                filepath = os.path.join(self.gt_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    annotations[filename] = f.read()
        
        return annotations
    
    def evaluate(self, ocr_results: Dict[str, str]) -> Dict[str, any]:
        """
        评估 OCR 结果
        
        Args:
            ocr_results: {图像名称: OCR 输出文本}
            
        Returns:
            Dict: 包含各项指标的评估结果
        """
        annotations = self.load_annotations()
        
        if not annotations:
            print("警告：未找到标注文件，无法进行评估")
            return {}
        
        results = {
            'samples': {},
            'summary': {
                'avg_cer': 0.0,
                'avg_wer': 0.0,
                'avg_accuracy': 0.0,
                'total_samples': 0,
            }
        }
        
        total_cer = 0.0
        total_wer = 0.0
        total_accuracy = 0.0
        count = 0
        
        for gt_filename, gt_text in annotations.items():
            # 提取图像名称（e.g., 'img_01_gt.txt' -> 'img_01')
            img_name = gt_filename.replace('_gt.txt', '')
            
            if img_name not in ocr_results:
                print(f"警告：未找到 {img_name} 的 OCR 结果")
                continue
            
            predicted_text = ocr_results[img_name]
            
            # 计算指标
            cer = OCRQualityMetrics.character_error_rate(predicted_text, gt_text)
            wer = OCRQualityMetrics.word_error_rate(predicted_text, gt_text)
            accuracy = OCRQualityMetrics.accuracy(predicted_text, gt_text)
            edit_distance = LevenshteinDistance.calculate(predicted_text, gt_text)
            
            results['samples'][img_name] = {
                'cer': cer,
                'wer': wer,
                'accuracy': accuracy,
                'edit_distance': edit_distance,
                'gt_length': len(gt_text),
                'pred_length': len(predicted_text),
            }
            
            total_cer += cer
            total_wer += wer
            total_accuracy += accuracy
            count += 1
        
        if count > 0:
            results['summary']['avg_cer'] = total_cer / count
            results['summary']['avg_wer'] = total_wer / count
            results['summary']['avg_accuracy'] = total_accuracy / count
            results['summary']['total_samples'] = count
        
        return results
    
    def generate_report(self, results: Dict[str, any]) -> str:
        """
        生成评估报告
        
        Args:
            results: evaluate() 返回的评估结果
            
        Returns:
            str: 格式化的报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("OCR 质量评估报告 (Benchmark Results)")
        report.append("=" * 60)
        report.append("")
        
        # 摘要统计
        summary = results.get('summary', {})
        report.append("【汇总指标】")
        report.append(f"样本总数：{summary.get('total_samples', 0)}")
        report.append(f"平均字错率 (CER)：{summary.get('avg_cer', 0.0):.4f}")
        report.append(f"平均词错率 (WER)：{summary.get('avg_wer', 0.0):.4f}")
        report.append(f"平均准确率 (Accuracy)：{summary.get('avg_accuracy', 0.0):.4%}")
        report.append("")
        
        # 各样本详细信息
        report.append("【各样本详细指标】")
        report.append("-" * 60)
        
        samples = results.get('samples', {})
        for img_name in sorted(samples.keys()):
            metrics = samples[img_name]
            report.append(f"文件：{img_name}")
            report.append(f"  字错率 (CER)：{metrics['cer']:.4f}")
            report.append(f"  词错率 (WER)：{metrics['wer']:.4f}")
            report.append(f"  准确率 (Accuracy)：{metrics['accuracy']:.4%}")
            report.append(f"  编辑距离：{metrics['edit_distance']}")
            report.append(f"  GT 长度：{metrics['gt_length']} | 预测长度：{metrics['pred_length']}")
            report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == '__main__':
    """示例：如何使用质量检查脚本"""
    
    # 设置 benchmark 路径
    benchmark_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'benchmark'
    )
    
    # 初始化评估器
    evaluator = BenchmarkEvaluator(benchmark_path)
    
    # 模拟 OCR 结果（实际应由 OCR 模型输出）
    # 格式：{图像名称（不含扩展名）: OCR 输出文本}
    ocr_results_example = {
        'img_01': '第1题：1+1=\nA. 1\nB. 2\nC. 3\nD. 4',
        'img_02': '第2题：计算 2×3\nA. 5\nB. 6\nC. 7\nD. 8',
    }
    
    # 执行评估
    print("正在评估 OCR 质量...")
    results = evaluator.evaluate(ocr_results_example)
    
    # 生成报告
    report = evaluator.generate_report(results)
    print(report)
    
    # 可选：保存报告到文件
    report_path = os.path.join(
        os.path.dirname(__file__),
        'quality_report.txt'
    )
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存：{report_path}")


# ============================================================================
# API 接口
# ============================================================================

def calculate_metrics(ocr_output: str, ground_truth: str) -> Dict[str, float]:
    """
    便捷函数：计算单个样本的所有指标
    
    Args:
        ocr_output: OCR 输出文本
        ground_truth: 标准文本
        
    Returns:
        Dict: 包含 CER、WER、准确率、编辑距离的字典
    """
    return {
        'cer': OCRQualityMetrics.character_error_rate(ocr_output, ground_truth),
        'wer': OCRQualityMetrics.word_error_rate(ocr_output, ground_truth),
        'accuracy': OCRQualityMetrics.accuracy(ocr_output, ground_truth),
        'edit_distance': LevenshteinDistance.calculate(ocr_output, ground_truth),
    }
