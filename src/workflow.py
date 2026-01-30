"""
错题本生成工作流
编排5个步骤的执行
"""

import os
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

from .utils import prepare_input, build_preview, export_wrongbook

load_dotenv()
console = Console()


def _is_remote_ocr_configured():
    """检查远程 PaddleOCR API 是否已配置"""
    api_url = os.getenv("PADDLEOCR_API_URL", "")
    api_token = os.getenv("PADDLEOCR_API_TOKEN", "")
    return (api_url and api_url != "your_paddleocr_api_url_here" and
            api_token and api_token != "your_paddleocr_api_token_here")


class ErrorCorrectionWorkflow:
    """错题本生成工作流"""

    def __init__(self):
        """初始化工作流"""
        self.use_local_ocr = not _is_remote_ocr_configured()

        if self.use_local_ocr:
            console.print("[yellow]远程 PaddleOCR API 未配置，使用本地 PaddleOCR[/yellow]")
            from .local_ocr import get_ocr_instance
            self.local_ocr = get_ocr_instance()
        else:
            from .paddleocr_client import PaddleOCRClient
            self.paddleocr_client = PaddleOCRClient()

        self.image_paths = []
        self.ocr_results = []
        self.questions = []

    def run(self, input_file: str, auto_split: bool = False) -> Dict[str, Any]:
        """
        运行完整工作流

        Args:
            input_file: 输入文件路径（PDF或图片）
            auto_split: 是否自动调用Agent分割题目（默认False，需要手动调用）

        Returns:
            Dict: 包含各步骤结果的字典
        """
        console.print("\n[bold cyan]========== 错题本生成工作流 ==========[/bold cyan]\n")

        # 步骤1: 准备输入
        console.print("[bold yellow]步骤 1/5: 准备输入文件[/bold yellow]")
        new_image_paths = prepare_input(input_file)
        self.image_paths.extend(new_image_paths)

        # 步骤2: PaddleOCR解析（只解析新增的图片）
        console.print("\n[bold yellow]步骤 2/5: PaddleOCR解析[/bold yellow]")
        new_ocr_results = self.paddleocr_parse(new_image_paths)
        self.ocr_results.extend(new_ocr_results)

        # 步骤3: 分割题目（需要Agent）
        console.print("\n[bold yellow]步骤 3/5: 分割题目（需要Agent）[/bold yellow]")
        if auto_split:
            self.questions = self.split_questions_auto()
        else:
            console.print("[yellow]自动分割未启用。请手动调用 split_questions_with_agent() 方法[/yellow]")
            console.print(f"[yellow]OCR结果已保存，可以在后续步骤中处理[/yellow]")

        # 步骤4和5需要在题目分割后才能执行
        if self.questions:
            # 步骤4: 生成预览
            console.print("\n[bold yellow]步骤 4/5: 生成HTML预览[/bold yellow]")
            preview_path = build_preview(self.questions)

            console.print("\n[bold green]✓ 工作流执行完成![/bold green]")
            console.print(f"请打开预览文件选择题目: {preview_path}")
        else:
            console.print("\n[yellow]题目尚未分割，跳过预览生成[/yellow]")

        return {
            "image_paths": new_image_paths,
            "ocr_results": new_ocr_results,
            "questions": self.questions,
        }

    def paddleocr_parse(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        步骤2: 调用PaddleOCR解析文档结构
        支持远程API和本地PaddleOCR两种模式

        Args:
            image_paths: 图片路径列表

        Returns:
            List[Dict]: 每张图片的PaddleOCR解析结果
        """
        results = []

        if self.use_local_ocr:
            # 使用本地 PaddleOCR
            from .local_ocr import recognize_image
            for image_path in image_paths:
                console.print(f"[cyan]本地 OCR 解析: {image_path}[/cyan]")
                ocr_result = recognize_image(image_path)
                if ocr_result["success"]:
                    # 转换为与远程 API 兼容的格式
                    result = {
                        "layoutParsingResults": [{
                            "prunedResult": {
                                "parsing_res_list": [
                                    {"block_type": "text", "content": t["text"]}
                                    for t in ocr_result["texts"]
                                ]
                            },
                            "block_order": list(range(len(ocr_result["texts"]))),
                            "markdown": {
                                "text": ocr_result["full_text"],
                                "images": {}
                            }
                        }]
                    }
                    results.append(result)
                else:
                    console.print(f"[red]OCR 失败: {ocr_result['error']}[/red]")
                    results.append({"layoutParsingResults": []})
        else:
            # 使用远程 PaddleOCR API
            for image_path in image_paths:
                result = self.paddleocr_client.parse_image(
                    image_path,
                    save_output=True
                )
                results.append(result)

        console.print(f"[green]✓ 成功解析 {len(results)} 张图片[/green]")

        return results

    def split_questions_with_agent(self) -> List[Dict[str, Any]]:
        """
        步骤3: 使用Agent智能分割题目

        这是核心步骤，使用LLM Agent来:
        - 识别题目边界
        - 提取题干、选项、答案
        - 处理公式和图片

        Returns:
            List[Dict]: 分割后的题目列表
        """
        from error_correction_agent.agent import create_question_split_agent

        console.print("[cyan]正在启动题目分割Agent...[/cyan]")

        # 创建Agent
        agent = create_question_split_agent()

        # 准备输入数据
        # 将OCR结果简化为Agent友好的格式
        simplified_results = []
        for result in self.ocr_results:
            if "layoutParsingResults" in result:
                for page in result["layoutParsingResults"]:
                    if "prunedResult" in page:
                        parsing_res = page["prunedResult"].get("parsing_res_list", [])
                        simplified_results.append({
                            "blocks": parsing_res,
                            "block_order": page.get("block_order", [])
                        })

        # 调用Agent
        console.print("[cyan]Agent正在分析题目...[/cyan]")

        # 构建提示
        prompt = f"""请分析以下OCR识别结果，将其分割为独立的题目。

OCR结果包含 {len(simplified_results)} 页内容。

每页的数据结构：
- blocks: 包含所有识别的内容块（文本、公式、图片等）
- block_order: 推荐的阅读顺序

请仔细分析题号、内容结构，将题目准确分割，并使用 save_questions 工具保存结果。

如果遇到不确定的情况，请使用 log_issue 工具记录。
"""

        # 调用Agent
        response = agent.invoke({
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "user", "content": f"OCR数据: {simplified_results}"}
            ]
        })

        console.print("[green]✓ Agent分析完成[/green]")

        # 从结果目录读取保存的题目
        results_dir = os.getenv("RESULTS_DIR", "results")
        questions_file = os.path.join(results_dir, "questions.json")

        if os.path.exists(questions_file):
            import json
            with open(questions_file, 'r', encoding='utf-8') as f:
                self.questions = json.load(f)
            console.print(f"[green]✓ 成功加载 {len(self.questions)} 道题目[/green]")
        else:
            console.print("[yellow]⚠ Agent未保存题目，请检查执行日志[/yellow]")
            self.questions = []

        return self.questions

    def split_questions_auto(self) -> List[Dict[str, Any]]:
        """自动调用Agent分割题目（run方法的auto_split选项）"""
        return self.split_questions_with_agent()

    def export_selected(self, selected_ids: List[str], output_path: str = None) -> str:
        """
        步骤5: 导出选中的题目为错题本

        Args:
            selected_ids: 用户选择的题目ID列表
            output_path: 输出路径（可选）

        Returns:
            str: 导出文件路径
        """
        if not self.questions:
            console.print("[red]错误: 尚未分割题目，请先调用 split_questions_with_agent()[/red]")
            return None

        console.print("\n[bold yellow]步骤 5/5: 导出错题本[/bold yellow]")
        return export_wrongbook(self.questions, selected_ids, output_path)


def main():
    """
    示例用法
    """
    # 创建工作流
    workflow = ErrorCorrectionWorkflow()

    # 运行工作流（不自动分割，需要手动调用Agent）
    workflow.run("input/test.jpg", auto_split=False)

    # 手动调用Agent分割题目
    # workflow.split_questions_with_agent()

    # 导出选中的题目
    # workflow.export_selected(["1", "2", "3"])


if __name__ == "__main__":
    main()
