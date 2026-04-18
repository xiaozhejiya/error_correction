"""
基础网络模块：CBAM 注意力、编码/解码块，供 Generator 和 Discriminator 组合使用。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CBAM(nn.Module):
    """Convolutional Block Attention Module：通道注意力 + 空间注意力。

    Args:
        in_channels: 输入特征图通道数
        reduction:   通道注意力 MLP 的压缩比，越大参数越少但表达力越弱
    """
    def __init__(self, in_channels: int, reduction: int = 16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, in_channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(in_channels // reduction, in_channels, bias=False),
        )
        self.sigmoid = nn.Sigmoid()
        # 空间注意力：7×7 大感受野，无 BN（标准 CBAM）
        self.spatial = nn.Sequential(
            nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, h, w = x.shape

        # 通道注意力
        avg_out = self.mlp(self.avg_pool(x).view(b, c)).view(b, c, 1, 1)
        max_out = self.mlp(self.max_pool(x).view(b, c)).view(b, c, 1, 1)
        x = x * self.sigmoid(avg_out + max_out)

        # 空间注意力
        avg_s = torch.mean(x, dim=1, keepdim=True)
        max_s, _ = torch.max(x, dim=1, keepdim=True)
        x = x * self.spatial(torch.cat([avg_s, max_s], dim=1))

        return x


class DilatedConvBlock(nn.Module):
    """空洞卷积块，用于 RefineNet 解码器，扩大感受野而不损失分辨率。

    Args:
        dilation: 空洞率，默认 2；padding 自动计算以保持尺寸不变
    """
    def __init__(self, in_channels: int, out_channels: int, dilation: int = 2):
        super().__init__()
        padding = dilation * (3 - 1) // 2
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3,
                      padding=padding, dilation=dilation, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class DownSample(nn.Module):
    """U-Net 编码器下采样块：步长为 2 的卷积，分辨率减半。"""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.2, inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class ResBlock(nn.Module):
    """残差块，参照 EraseNet Residual：conv1(stride) → ReLU → conv2 + skip → BN → ReLU。

    stride=1 时要求 in_channels == out_channels（无投影）；
    stride=2 时自动添加 1×1 skip 投影以匹配通道和尺寸。
    """
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, in_channels, 3, stride=stride, padding=1)
        self.conv2 = nn.Conv2d(in_channels, out_channels, 3, padding=1)
        self.bn    = nn.BatchNorm2d(out_channels)
        self.skip  = (nn.Conv2d(in_channels, out_channels, 1, stride=stride)
                      if (stride != 1 or in_channels != out_channels) else None)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = F.relu(self.conv1(x))
        out = self.conv2(out)
        identity = self.skip(x) if self.skip is not None else x
        return F.relu(self.bn(out + identity))


class LateralConnection(nn.Module):
    """跳跃连接特征精炼：1×1 → 3×3 → 3×3 → 1×1，参照 EraseNet lateral_connection。

    输入输出通道数相同，中间扩张为 2×channels。
    """
    def __init__(self, channels: int):
        super().__init__()
        inner = channels * 2
        self.net = nn.Sequential(
            nn.Conv2d(channels, channels, 1),
            nn.Conv2d(channels, inner,    3, padding=1),
            nn.Conv2d(inner,    inner,    3, padding=1),
            nn.Conv2d(inner,    channels, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class UpSample(nn.Module):
    """U-Net 解码器上采样块：转置卷积，分辨率翻倍，可选 CBAM 注意力。"""
    def __init__(self, in_channels: int, out_channels: int,
                 use_cbam: bool = False, reduction: int = 16):
        super().__init__()
        self.conv = nn.Sequential(
            nn.ConvTranspose2d(in_channels, out_channels, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )
        self.cbam = CBAM(out_channels, reduction) if use_cbam else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.cbam(self.conv(x))
