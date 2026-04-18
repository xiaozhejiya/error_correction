"""
GAN 文字擦除模型推理引擎

职责：
- 懒加载 Generator 权重（进程内单例，首次调用时初始化）
- 图像预处理（归一化到 [-1,1]，padding 到 512 的整数倍）
- 大图滑动窗口推理（patch_size=512，overlap 可配置）
- 后处理（还原 [0,255]，裁剪掉 padding）
"""
import io
import logging
import threading

import numpy as np
import torch
from PIL import Image

from models.model import Generator

# cuDNN v8 frontend 与 A30+PyTorch2.1 不兼容
torch.backends.cudnn.enabled = False

logger = logging.getLogger(__name__)

_PATCH_SIZE = 512
_OVERLAP = 32


class InferenceEngine:
    """单例推理引擎，线程安全懒加载"""

    _instance = None
    _class_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._model = None
                    inst._device = None
                    inst._model_lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------

    def _load_model(self):
        """首次调用时从磁盘加载权重，后续调用直接复用"""
        if self._model is not None:
            return

        with self._model_lock:
            if self._model is not None:
                return

            from core.config import settings

            model_path = settings.model_path
            if not model_path.exists():
                raise FileNotFoundError(
                    f"模型权重不存在，请将 best.pth 放到: {model_path}"
                )

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            generator = Generator().to(device)

            ckpt = torch.load(model_path, map_location=device, weights_only=False)
            state_dict = (
                ckpt.get("G_state_dict")
                or ckpt.get("generator_state_dict")
                or ckpt
            )
            generator.load_state_dict(state_dict)
            generator.eval()

            self._model = generator
            self._device = device
            logger.info("推理引擎初始化完成，设备: %s，权重: %s", device, model_path)

    # ------------------------------------------------------------------
    # 图像预处理 / 后处理
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess(pil_img: Image.Image):
        """PIL → float ndarray [-1, 1]，并 padding 到 512 的整数倍

        Returns:
            arr_padded (np.ndarray): shape (H_pad, W_pad, 3)，float32 in [-1,1]
            orig_w, orig_h: 原始尺寸，用于最终裁剪
        """
        img = pil_img.convert("RGB")
        orig_w, orig_h = img.size

        pad_w = (_PATCH_SIZE - orig_w % _PATCH_SIZE) % _PATCH_SIZE
        pad_h = (_PATCH_SIZE - orig_h % _PATCH_SIZE) % _PATCH_SIZE

        if pad_w or pad_h:
            canvas = Image.new("RGB", (orig_w + pad_w, orig_h + pad_h), (255, 255, 255))
            canvas.paste(img, (0, 0))
            img = canvas

        arr = np.array(img, dtype=np.float32) / 127.5 - 1.0
        return arr, orig_w, orig_h

    def _to_tensor(self, arr: np.ndarray) -> torch.Tensor:
        """(H, W, 3) ndarray → (1, 3, H, W) Tensor on device"""
        return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(self._device)

    @staticmethod
    def _to_numpy(tensor: torch.Tensor) -> np.ndarray:
        """(1, 3, H, W) Tensor → (H, W, 3) uint8 ndarray"""
        arr = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        return np.clip((arr + 1.0) * 127.5, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # 推理
    # ------------------------------------------------------------------

    def _infer_sliding_window(self, arr: np.ndarray) -> np.ndarray:
        """滑动窗口推理，patch 重叠区域做加权平均以消除接缝"""
        h, w, _ = arr.shape
        result = np.zeros((h, w, 3), dtype=np.float32)
        weight = np.zeros((h, w, 1), dtype=np.float32)

        stride = _PATCH_SIZE - _OVERLAP

        def _ticks(total):
            pts = list(range(0, total - _PATCH_SIZE + 1, stride))
            if not pts or pts[-1] + _PATCH_SIZE < total:
                pts.append(total - _PATCH_SIZE)
            return pts

        with torch.no_grad():
            for y in _ticks(h):
                for x in _ticks(w):
                    patch = arr[y:y + _PATCH_SIZE, x:x + _PATCH_SIZE]
                    tensor = self._to_tensor(patch)
                    *_, Icomp = self._model(tensor)
                    out = (Icomp.squeeze(0).permute(1, 2, 0).cpu().numpy() + 1.0) * 127.5
                    result[y:y + _PATCH_SIZE, x:x + _PATCH_SIZE] += out
                    weight[y:y + _PATCH_SIZE, x:x + _PATCH_SIZE] += 1.0

        return np.clip(result / weight, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run(self, image_bytes: bytes) -> Image.Image:
        """推理主入口

        Args:
            image_bytes: 原始图片字节（支持 JPEG/PNG/BMP 等 PIL 可读格式）

        Returns:
            擦除文字后的 PIL 图像（RGB）
        """
        self._load_model()

        pil_img = Image.open(io.BytesIO(image_bytes))
        arr, orig_w, orig_h = self._preprocess(pil_img)

        result_arr = self._infer_sliding_window(arr)

        # 裁剪掉 padding，还原到原始尺寸
        result_arr = result_arr[:orig_h, :orig_w]
        return Image.fromarray(result_arr)
