"""
生成器网络：CoarseNet（粗擦除 + 掩码预测） + RefineNet（精细修复）。

结构对照 EraseNet (STRnet2)，核心改动：
  - 编码器：EraseNet 残差块风格（conv1/conva/convb + ResBlock×8）
  - 跳跃连接：LateralConnection 特征精炼（替代简单 cat）
  - 掩码分支：从 x_mask（瓶颈前 H/16 特征）出发，与 EraseNet 对齐
  - 保留：CBAM 注意力、双 sigmoid 掩码（Ms/Mb）、RefineNet 输入含 Ms
  - RefineNet：EraseNet 风格多尺度空洞卷积，输入保持 cat([Iin, Ms, Ic1])
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

from models.blocks import (DownSample, UpSample, DilatedConvBlock,
                            ResBlock, LateralConnection)


class CoarseNet(nn.Module):
    """粗擦除网络：EraseNet 残差编码器 + 双解码器（修复 + 掩码）。

    Args:
        in_channels:    输入通道数，RGB 固定为 3
        cbam_reduction: CBAM 通道压缩比
    """
    def __init__(self, in_channels: int = 3, cbam_reduction: int = 16):
        super().__init__()
        r = cbam_reduction

        # ── 编码器（EraseNet 风格） ──────────────────────────────────────
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, 32, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32), nn.LeakyReLU(0.2, inplace=True))   # H/2,  32
        self.conva = nn.Sequential(
            nn.Conv2d(32, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32), nn.LeakyReLU(0.2, inplace=True))   # H/2,  32
        self.convb = nn.Sequential(
            nn.Conv2d(32, 64, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64), nn.LeakyReLU(0.2, inplace=True))   # H/4,  64
        self.res1  = ResBlock(64,  64)
        self.res2  = ResBlock(64,  64)
        self.res3  = ResBlock(64,  128, stride=2)                   # H/8,  128
        self.res4  = ResBlock(128, 128)
        self.res5  = ResBlock(128, 256, stride=2)                   # H/16, 256
        self.res6  = ResBlock(256, 256)
        self.res7  = ResBlock(256, 512, stride=2)                   # H/32, 512
        self.res8  = ResBlock(512, 512)
        self.conv2 = nn.Conv2d(512, 512, 1)                         # H/32, 512（瓶颈）

        # ── 修复解码器（LateralConnection + CBAM UpSample） ─────────────
        self.lat1    = LateralConnection(256)
        self.lat2    = LateralConnection(128)
        self.lat3    = LateralConnection(64)
        self.lat4    = LateralConnection(32)
        self.up1     = UpSample(512, 256, use_cbam=True, reduction=r)
        self.up2     = UpSample(512, 128, use_cbam=True, reduction=r)
        self.up3     = UpSample(256, 64,  use_cbam=True, reduction=r)
        self.up4     = UpSample(128, 32,  use_cbam=True, reduction=r)
        self.up5     = UpSample(64,  32,  use_cbam=True, reduction=r)
        self.out_ic4 = nn.Conv2d(64, 3, 1)
        self.out_ic2 = nn.Conv2d(32, 3, 1)
        self.out_ic1 = nn.Conv2d(32, 3, 3, padding=1)

        # ── 掩码解码器（从瓶颈 d5 出发，保留全局上下文，双 sigmoid 头） ──
        self.mask_up_0   = UpSample(512, 256, use_cbam=True, reduction=r)  # H/32→H/16
        self.mask_up_a   = UpSample(512, 256, use_cbam=True, reduction=r)
        self.mask_conv_a = nn.Sequential(
            nn.Conv2d(256, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True))
        self.mask_up_b   = UpSample(256, 128, use_cbam=True, reduction=r)
        self.mask_conv_b = nn.Sequential(
            nn.Conv2d(128, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True))
        self.mask_up_c   = UpSample(128, 64, use_cbam=True, reduction=r)
        self.mask_conv_c = nn.Sequential(
            nn.Conv2d(64, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True))
        self.mask_up_d   = UpSample(64, 32, use_cbam=True, reduction=r)
        self.out_ms      = nn.Conv2d(32, 1, 1)                      # 软笔画掩码
        self.out_mb      = nn.Conv2d(32, 1, 1)                      # 文本块掩码

    def forward(self, x: torch.Tensor):
        # 编码
        x      = self.conv1(x)
        x      = self.conva(x)
        con_x1 = x                                   # H/2,  32
        x      = self.convb(x)
        x      = self.res1(x)
        con_x2 = x                                   # H/4,  64
        x      = self.res2(x)
        x      = self.res3(x)
        con_x3 = x                                   # H/8,  128
        x      = self.res4(x)
        x      = self.res5(x)
        con_x4 = x                                   # H/16, 256
        x      = self.res6(x)
        x      = self.res7(x)
        x      = self.res8(x)
        d5     = self.conv2(x)                       # H/32, 512（瓶颈）

        # 修复解码
        u1  = torch.cat([self.lat1(con_x4), self.up1(d5)],  dim=1)  # H/16, 512
        u2  = torch.cat([self.lat2(con_x3), self.up2(u1)],  dim=1)  # H/8,  256
        xo1 = self.up3(u2)                                           # H/4,  64
        Ic4 = torch.tanh(self.out_ic4(xo1))
        u3  = torch.cat([self.lat3(con_x2), xo1], dim=1)            # H/4,  128
        xo2 = self.up4(u3)                                           # H/2,  32
        Ic2 = torch.tanh(self.out_ic2(xo2))
        u4  = torch.cat([self.lat4(con_x1), xo2], dim=1)            # H/2,  64
        Ic1 = torch.tanh(self.out_ic1(self.up5(u4)))                 # H,    3

        # 掩码解码（从瓶颈 d5 出发，保留全局上下文）
        mm = self.mask_up_a(torch.cat([self.mask_up_0(d5), con_x4], dim=1))  # H/8,  256
        mm = self.mask_conv_a(mm)                                     # H/8,  128
        mm = self.mask_up_b(torch.cat([mm, con_x3], dim=1))         # H/4,  128
        mm = self.mask_conv_b(mm)                                     # H/4,  64
        mm = self.mask_up_c(torch.cat([mm, con_x2], dim=1))         # H/2,  64
        mm = self.mask_conv_c(mm)                                     # H/2,  32
        mm = self.mask_up_d(torch.cat([mm, con_x1], dim=1))         # H,    32
        Ms = torch.sigmoid(self.out_ms(mm))
        Mb = torch.sigmoid(self.out_mb(mm))

        return Ms, Mb, Ic4, Ic2, Ic1


class RefineNet(nn.Module):
    """精细修复网络：EraseNet 风格多尺度空洞卷积，感受野更大。

    Args:
        in_channels: 输入通道数 = Iin(3) + Ms(1) + Ic1(3) = 7
    """
    def __init__(self, in_channels: int = 7):
        super().__init__()
        cnum = 32

        # 编码
        self.conva = nn.Sequential(
            nn.Conv2d(in_channels, cnum, 5, padding=2, bias=False),
            nn.BatchNorm2d(cnum), nn.ReLU(inplace=True))
        self.down1 = DownSample(cnum,     cnum * 2)                  # H/2, 64
        self.convc = nn.Sequential(
            nn.Conv2d(cnum * 2, cnum * 2, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum * 2), nn.ReLU(inplace=True))
        self.down2 = DownSample(cnum * 2, cnum * 4)                  # H/4, 128
        self.conve = nn.Sequential(
            nn.Conv2d(cnum * 4, cnum * 4, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum * 4), nn.ReLU(inplace=True))
        self.convf = nn.Sequential(
            nn.Conv2d(cnum * 4, cnum * 4, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum * 4), nn.ReLU(inplace=True))

        # 多尺度空洞卷积（参照 EraseNet astrous_net）
        self.astrous = nn.Sequential(
            DilatedConvBlock(cnum * 4, cnum * 4, dilation=2),
            DilatedConvBlock(cnum * 4, cnum * 4, dilation=4),
            DilatedConvBlock(cnum * 4, cnum * 4, dilation=8),
            DilatedConvBlock(cnum * 4, cnum * 4, dilation=16),
        )
        self.convk = nn.Sequential(
            nn.Conv2d(cnum * 4, cnum * 4, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum * 4), nn.ReLU(inplace=True))
        self.convl = nn.Sequential(
            nn.Conv2d(cnum * 4, cnum * 4, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum * 4), nn.ReLU(inplace=True))

        # 解码（cat 自身跳跃连接）
        self.up1   = UpSample(cnum * 8, cnum * 2)                    # cat([x,x_c2]) H/4→H/2
        self.convm = nn.Sequential(
            nn.Conv2d(cnum * 2, cnum * 2, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum * 2), nn.ReLU(inplace=True))
        self.up2   = UpSample(cnum * 4, cnum)                        # cat([x,x_c1]) H/2→H
        self.convn = nn.Sequential(
            nn.Conv2d(cnum, cnum // 2, 3, padding=1, bias=False),
            nn.BatchNorm2d(cnum // 2), nn.ReLU(inplace=True),
            nn.Conv2d(cnum // 2, 3, 3, padding=1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x    = self.conva(x)
        x    = self.down1(x)
        x    = self.convc(x)
        x_c1 = x                                      # H/2, 64
        x    = self.down2(x)
        x    = self.conve(x)
        x    = self.convf(x)
        x_c2 = x                                      # H/4, 128
        x    = self.astrous(x)
        x    = self.convk(x)
        x    = self.convl(x)
        x    = self.up1(torch.cat([x, x_c2], dim=1)) # H/2, 64
        x    = self.convm(x)
        x    = self.up2(torch.cat([x, x_c1], dim=1)) # H,   32
        return torch.tanh(self.convn(x))


class Generator(nn.Module):
    """完整生成器：CoarseNet → RefineNet → 融合输出。

    Args:
        cfg: model 子配置字典，含 coarse_in_channels / refine_in_channels / cbam_reduction
    """
    def __init__(self, cfg: dict = None):
        super().__init__()
        if cfg is None:
            cfg = {'coarse_in_channels': 3, 'refine_in_channels': 7, 'cbam_reduction': 16}
        self.coarse = CoarseNet(in_channels=cfg['coarse_in_channels'],
                                cbam_reduction=cfg['cbam_reduction'])
        self.refine = RefineNet(in_channels=cfg['refine_in_channels'])

    def forward(self, Iin: torch.Tensor):
        Ms, Mb, Ic4, Ic2, Ic1 = self.coarse(Iin)
        Ire   = self.refine(torch.cat([Iin, Ms, Ic1], dim=1))
        Icomp = Ire * Mb + Iin * (1 - Mb)
        return Ms, Mb, Ic4, Ic2, Ic1, Ire, Icomp
