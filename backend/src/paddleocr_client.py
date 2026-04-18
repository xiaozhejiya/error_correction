"""
PaddleOCR 文档解析客户端
调用 PaddleOCR V2 异步任务 API 进行文档结构化解析
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests
import aiohttp
from rich.console import Console

console = Console()

# 任务轮询间隔（秒）
POLL_INTERVAL = 3
# 轮询最大超时（秒）
POLL_TIMEOUT = 300


class PaddleOCRClient:
    """PaddleOCR V2 异步任务 API 客户端"""

    def __init__(self, *, api_url=None, token=None, model=None,
                 use_doc_orientation=None, use_doc_unwarping=None,
                 use_chart_recognition=None):
        """初始化客户端

        优先使用传入参数，其次使用平台托管默认配置。
        """
        from core.config import settings

        managed_cfg = settings.get_managed_ocr_config()
        self.api_url = api_url or managed_cfg.get("api_url", "")
        self.token = token or managed_cfg.get("token", "")
        self.model = model or managed_cfg.get("model", "PaddleOCR-VL-1.5")
        self.use_doc_orientation = use_doc_orientation if use_doc_orientation is not None else managed_cfg.get("use_doc_orientation", False)
        self.use_doc_unwarping = use_doc_unwarping if use_doc_unwarping is not None else managed_cfg.get("use_doc_unwarping", False)
        self.use_chart_recognition = use_chart_recognition if use_chart_recognition is not None else managed_cfg.get("use_chart_recognition", False)
        if not self.api_url or not self.token:
            raise ValueError("缺少 PaddleOCR 配置，请先在设置中配置，或由管理员设置 APP_DEFAULT_PADDLEOCR_*")

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"bearer {self.token}"}

    @property
    def _optional_payload(self) -> Dict[str, Any]:
        return {
            "useDocOrientationClassify": self.use_doc_orientation,
            "useDocUnwarping": self.use_doc_unwarping,
            "useChartRecognition": self.use_chart_recognition,
        }

    # ── 同步方法 ──────────────────────────────────────────────

    def _submit_job(self, file_path: str) -> str:
        """提交 OCR 任务，返回 jobId"""
        data = {
            "model": self.model,
            "optionalPayload": json.dumps(self._optional_payload),
        }
        with open(file_path, "rb") as f:
            files = {"file": f}
            resp = requests.post(self.api_url, headers=self._headers, data=data, files=files)

        if resp.status_code != 200:
            raise Exception(f"提交 OCR 任务失败: HTTP {resp.status_code}, {resp.text}")

        return resp.json()["data"]["jobId"]

    def _poll_job(self, job_id: str) -> str:
        """轮询任务状态直到完成，返回 JSONL 结果 URL"""
        import time

        url = f"{self.api_url}/{job_id}"
        start_time = time.monotonic()
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > POLL_TIMEOUT:
                raise TimeoutError(f"OCR 任务轮询超时（已等待 {int(elapsed)}s，上限 {POLL_TIMEOUT}s）")

            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                raise Exception(f"查询任务状态失败: HTTP {resp.status_code}")

            state = resp.json()["data"]["state"]
            if state == "done":
                return resp.json()["data"]["resultUrl"]["jsonUrl"]
            elif state == "failed":
                error_msg = resp.json()["data"].get("errorMsg", "未知错误")
                raise Exception(f"OCR 任务失败: {error_msg}")
            elif state == "running":
                progress = resp.json()["data"].get("extractProgress", {})
                total = progress.get("totalPages", "?")
                extracted = progress.get("extractedPages", "?")
                console.print(f"  [dim]进度: {extracted}/{total} 页...[/dim]")

            time.sleep(POLL_INTERVAL)

    def _download_result(self, jsonl_url: str) -> List[Dict[str, Any]]:
        """下载 JSONL 结果并解析为结果列表"""
        resp = requests.get(jsonl_url)
        resp.raise_for_status()

        results = []
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            results.append(json.loads(line)["result"])
        return results

    def _parse_file(
        self,
        file_path: str,
        save_output: bool = True,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """解析文件并返回结构化结果（同步，任务轮询模式）"""
        if output_dir is None:
            from core.config import settings
            output_dir = settings.struct_dir

        console.print(f"[cyan]正在解析: {file_path}[/cyan]")

        # 提交 → 轮询 → 下载
        job_id = self._submit_job(file_path)
        console.print(f"[dim]任务已提交: {job_id}[/dim]")

        jsonl_url = self._poll_job(job_id)
        result_pages = self._download_result(jsonl_url)

        # 合并所有页面到一个 result（保持与下游兼容）
        result = self._merge_pages(result_pages)
        console.print(f"[green]✓ 解析成功: {file_path}[/green]")

        if save_output:
            os.makedirs(output_dir, exist_ok=True)
            filename = Path(file_path).stem + "_struct.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            console.print(f"[green]结构化结果已保存到: {output_path}[/green]")

            file_prefix = Path(file_path).stem
            self._save_images(result, output_dir, file_prefix)

        return result

    @staticmethod
    def _merge_pages(result_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将多页 JSONL 结果合并为单个 result 对象

        下游 simplify_ocr_results 期望每个 result 有 layoutParsingResults 列表。
        """
        merged_layouts = []
        for page_result in result_pages:
            merged_layouts.extend(page_result.get("layoutParsingResults", []))
        return {"layoutParsingResults": merged_layouts}

    def parse_image(self, image_path: str, save_output: bool = True, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """解析图片并返回结构化结果"""
        return self._parse_file(image_path, save_output=save_output, output_dir=output_dir)

    def parse_pdf(self, pdf_path: str, save_output: bool = True, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """解析 PDF 并返回结构化结果"""
        return self._parse_file(pdf_path, save_output=save_output, output_dir=output_dir)

    def _save_images(self, result: Dict[str, Any], output_dir: str, file_prefix: str = ""):
        """下载并保存结果中的图片资源"""
        for i, res in enumerate(result.get("layoutParsingResults", [])):
            markdown_text = res.get("markdown", {}).get("text", "")
            if markdown_text:
                md_filename = os.path.join(output_dir, f"{file_prefix}_doc_{i}.md")
                with open(md_filename, "w", encoding="utf-8") as md_file:
                    md_file.write(markdown_text)
                console.print(f"[green]Markdown 已保存: {md_filename}[/green]")

            images = res.get("markdown", {}).get("images", {})
            for img_path, img_url in images.items():
                full_img_path = os.path.join(output_dir, img_path)
                os.makedirs(os.path.dirname(full_img_path), exist_ok=True)
                try:
                    img_response = requests.get(img_url)
                    if img_response.status_code == 200:
                        with open(full_img_path, "wb") as img_file:
                            img_file.write(img_response.content)
                        console.print(f"[green]图片已保存: {full_img_path}[/green]")
                    else:
                        console.print(f"[yellow]图片下载失败: {img_path}[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]图片下载出错: {img_path} - {e}[/yellow]")

            output_images = res.get("outputImages", {})
            for img_name, img_url in output_images.items():
                try:
                    img_response = requests.get(img_url)
                    if img_response.status_code == 200:
                        filename = os.path.join(output_dir, f"{img_name}_{file_prefix}_{i}.jpg")
                        with open(filename, "wb") as f:
                            f.write(img_response.content)
                        console.print(f"[green]图片已保存: {filename}[/green]")
                except Exception as e:
                    console.print(f"[yellow]图片下载出错: {img_name} - {e}[/yellow]")

    # ── 异步方法 ──────────────────────────────────────────────

    async def _async_submit_job(self, session: aiohttp.ClientSession, file_path: str) -> str:
        """异步提交 OCR 任务，返回 jobId"""
        data = aiohttp.FormData()
        data.add_field("model", self.model)
        data.add_field("optionalPayload", json.dumps(self._optional_payload))

        with open(file_path, "rb") as f:
            file_bytes = f.read()
        data.add_field("file", file_bytes, filename=Path(file_path).name)

        async with session.post(self.api_url, headers=self._headers, data=data) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"提交 OCR 任务失败: HTTP {resp.status}, {text}")
            result = await resp.json()
            return result["data"]["jobId"]

    async def _async_poll_job(self, session: aiohttp.ClientSession, job_id: str) -> str:
        """异步轮询任务状态直到完成，返回 JSONL 结果 URL"""
        url = f"{self.api_url}/{job_id}"
        while True:
            async with session.get(url, headers=self._headers) as resp:
                if resp.status != 200:
                    raise Exception(f"查询任务状态失败: HTTP {resp.status}")
                data = await resp.json()

            state = data["data"]["state"]
            if state == "done":
                return data["data"]["resultUrl"]["jsonUrl"]
            elif state == "failed":
                error_msg = data["data"].get("errorMsg", "未知错误")
                raise Exception(f"OCR 任务失败: {error_msg}")
            elif state == "running":
                progress = data["data"].get("extractProgress", {})
                total = progress.get("totalPages", "?")
                extracted = progress.get("extractedPages", "?")
                console.print(f"  [dim]进度: {extracted}/{total} 页...[/dim]")

            await asyncio.sleep(POLL_INTERVAL)

    async def _async_download_result(self, session: aiohttp.ClientSession, jsonl_url: str) -> List[Dict[str, Any]]:
        """异步下载 JSONL 结果"""
        async with session.get(jsonl_url) as resp:
            resp.raise_for_status()
            text = await resp.text()

        results = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            results.append(json.loads(line)["result"])
        return results

    async def async_parse_image(
        self,
        session: aiohttp.ClientSession,
        image_path: str,
        save_output: bool = True,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """异步解析单张图片（提交任务 → 轮询 → 下载结果）"""
        if output_dir is None:
            from core.config import settings
            output_dir = settings.struct_dir

        console.print(f"[cyan]正在解析图片: {image_path}[/cyan]")

        # 提交 → 轮询 → 下载
        job_id = await self._async_submit_job(session, image_path)
        console.print(f"[dim]任务已提交: {job_id}[/dim]")

        jsonl_url = await self._async_poll_job(session, job_id)
        result_pages = await self._async_download_result(session, jsonl_url)

        result = self._merge_pages(result_pages)
        console.print(f"[green]✓ 解析成功: {image_path}[/green]")

        if save_output:
            os.makedirs(output_dir, exist_ok=True)
            filename = Path(image_path).stem + "_struct.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            console.print(f"[green]结构化结果已保存到: {output_path}[/green]")

            file_prefix = Path(image_path).stem
            await self._async_save_images(session, result, output_dir, file_prefix)

        return result

    async def _async_download_image(self, session: aiohttp.ClientSession, url: str, save_path: str):
        """异步下载单张图片"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(content)
                    console.print(f"[green]图片已保存: {save_path}[/green]")
                else:
                    console.print(f"[yellow]图片下载失败: {save_path}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]图片下载出错: {save_path} - {e}[/yellow]")

    async def _async_save_images(
        self,
        session: aiohttp.ClientSession,
        result: Dict[str, Any],
        output_dir: str,
        file_prefix: str = "",
    ):
        """异步下载并保存结果中的所有图片资源"""
        for i, res in enumerate(result.get("layoutParsingResults", [])):
            markdown_text = res.get("markdown", {}).get("text", "")
            if markdown_text:
                md_filename = os.path.join(output_dir, f"{file_prefix}_doc_{i}.md")
                with open(md_filename, "w", encoding="utf-8") as md_file:
                    md_file.write(markdown_text)
                console.print(f"[green]Markdown 已保存: {md_filename}[/green]")

            download_tasks = []
            images = res.get("markdown", {}).get("images", {})
            for img_path, img_url in images.items():
                full_img_path = os.path.join(output_dir, img_path)
                download_tasks.append(
                    self._async_download_image(session, img_url, full_img_path)
                )

            output_images = res.get("outputImages", {})
            for img_name, img_url in output_images.items():
                filename = os.path.join(output_dir, f"{img_name}_{file_prefix}_{i}.jpg")
                download_tasks.append(
                    self._async_download_image(session, img_url, filename)
                )

            if download_tasks:
                await asyncio.gather(*download_tasks)

    async def parse_images_async(
        self,
        image_paths: List[str],
        save_output: bool = True,
        output_dir: Optional[str] = None,
        stagger_delay: float = 1,
    ) -> List[Dict[str, Any]]:
        """异步并发解析多张图片

        所有图片的任务同时提交，然后各自独立轮询，最大化并行度。
        """
        console.print(f"[bold cyan]异步并发解析 {len(image_paths)} 张图片...[/bold cyan]")

        async def _delayed_parse(idx: int, path: str, session: aiohttp.ClientSession):
            if idx > 0 and stagger_delay > 0:
                await asyncio.sleep(idx * stagger_delay)
            return await self.async_parse_image(session, path, save_output, output_dir)

        async with aiohttp.ClientSession() as session:
            tasks = [
                _delayed_parse(i, path, session)
                for i, path in enumerate(image_paths)
            ]
            results = await asyncio.gather(*tasks)

        console.print(f"[bold green]✓ 全部 {len(results)} 张图片解析完成[/bold green]")
        return list(results)


def main():
    """测试函数"""
    client = PaddleOCRClient()

    test_image = "input/test.png"

    if os.path.exists(test_image):
        result = client.parse_image(test_image)
        console.print(f"\n[bold cyan]返回结果概览:[/bold cyan]")
        console.print(f"结果类型: {type(result)}")
        console.print(f"结果键: {list(result.keys())}")
    else:
        console.print(f"[red]测试图片不存在: {test_image}[/red]")
        console.print("[yellow]请在 input/ 目录下放置测试图片（命名为 test.png）[/yellow]")


if __name__ == "__main__":
    main()
