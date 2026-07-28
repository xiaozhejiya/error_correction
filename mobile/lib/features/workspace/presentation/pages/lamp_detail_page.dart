import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/protected_image.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../../device/data/device_api.dart';

class LampDetailPage extends StatefulWidget {
  const LampDetailPage({
    super.key,
    required this.deviceUuid,
    this.deviceApi,
  });

  final String deviceUuid;
  final DeviceApi? deviceApi;

  @override
  State<LampDetailPage> createState() => _LampDetailPageState();
}

class _LampDetailPageState extends State<LampDetailPage> {
  late final DeviceApi _deviceApi;

  List<DeviceCapture> _images = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _deviceApi = widget.deviceApi ?? DeviceApi();
    unawaited(_loadImages());
  }

  Future<void> _loadImages() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await _deviceApi.getImages(
        deviceUuid: widget.deviceUuid,
        limit: 50,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _images = response.images;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _error = error is ApiException ? error.message : '图片列表加载失败';
      });
    }
  }

  void _openPreview(DeviceCapture capture) {
    final imageUrl = _normaliseDeviceImageUrl(capture.imageUrl);
    if (imageUrl.isEmpty) {
      return;
    }

    showDialog<void>(
      context: context,
      builder: (context) {
        final palette = AppThemePalette.of(context);

        return Dialog.fullscreen(
          backgroundColor: palette.pageBg,
          child: SafeArea(
            child: Column(
              children: [
                _LampPreviewHeader(
                  palette: palette,
                  title: capture.displayName,
                  onClose: () => Navigator.of(context).pop(),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 6, 16, 18),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: ColoredBox(
                        color: Colors.transparent,
                        child: ProtectedImage(
                          url: imageUrl,
                          loadBytes: _deviceApi.loadImageBytes,
                          fit: BoxFit.contain,
                          loading: _ImageLoading(palette: palette),
                          error: _ImagePlaceholder(
                            palette: palette,
                            icon: Icons.broken_image_rounded,
                            text: '图片加载失败',
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          child: Column(
            children: [
              _LampDetailHeader(
                palette: palette,
                count: _images.length,
                onBack: () => Navigator.of(context).maybePop(),
                onRefresh: () => unawaited(_loadImages()),
              ),
              Expanded(child: _buildBody(palette)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody(AppThemePalette palette) {
    if (_loading) {
      return Center(
        child: CircularProgressIndicator(
          color: palette.primaryLight,
          strokeWidth: 2,
        ),
      );
    }

    if (_error != null) {
      return _LampDetailStateView(
        palette: palette,
        icon: Icons.error_outline_rounded,
        title: '加载失败',
        message: _error!,
        actionText: '重试',
        onAction: () => unawaited(_loadImages()),
      );
    }

    if (_images.isEmpty) {
      return RefreshIndicator(
        color: palette.primary,
        onRefresh: _loadImages,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(24, 70, 24, 24),
          children: [
            _LampDetailStateView(
              palette: palette,
              icon: Icons.photo_library_outlined,
              title: '暂无上传图片',
              message: '设备拍摄上传后会显示在这里',
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      color: palette.primary,
      onRefresh: _loadImages,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final crossAxisCount = constraints.maxWidth >= 720 ? 3 : 2;
          return GridView.builder(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(18, 10, 18, 24),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 0.78,
            ),
            itemCount: _images.length,
            itemBuilder: (context, index) {
              final capture = _images[index];
              return _DeviceImageCard(
                capture: capture,
                palette: palette,
                loadBytes: _deviceApi.loadImageBytes,
                onTap: () => _openPreview(capture),
              );
            },
          );
        },
      ),
    );
  }
}

class _LampDetailHeader extends StatelessWidget {
  const _LampDetailHeader({
    required this.palette,
    required this.count,
    required this.onBack,
    required this.onRefresh,
  });

  final AppThemePalette palette;
  final int count;
  final VoidCallback onBack;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 12, 8),
      child: Row(
        children: [
          IconButton(
            tooltip: '返回',
            onPressed: onBack,
            icon: const Icon(Icons.arrow_back_ios_new_rounded),
            color: palette.textMain,
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '智能学习台灯',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: palette.textMain,
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                
              ],
            ),
          ),
          IconButton(
            tooltip: '刷新',
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh_rounded),
            color: palette.textMain,
          ),
        ],
      ),
    );
  }
}

class _DeviceImageCard extends StatelessWidget {
  const _DeviceImageCard({
    required this.capture,
    required this.palette,
    required this.loadBytes,
    required this.onTap,
  });

  final DeviceCapture capture;
  final AppThemePalette palette;
  final Future<Uint8List> Function(String url) loadBytes;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final imageUrl = _normaliseDeviceImageUrl(capture.imageUrl);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: imageUrl.isEmpty ? null : onTap,
        borderRadius: BorderRadius.circular(8),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: palette.panelBorder),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(8),
                  ),
                  child: ColoredBox(
                    color: palette.imageBg,
                    child: imageUrl.isEmpty
                        ? _ImagePlaceholder(
                            palette: palette,
                            icon: Icons.image_not_supported_outlined,
                            text: '无图片地址',
                          )
                        : ProtectedImage(
                            url: imageUrl,
                            loadBytes: loadBytes,
                            fit: BoxFit.cover,
                            loading: _ImageLoading(palette: palette),
                            error: _ImagePlaceholder(
                              palette: palette,
                              icon: Icons.broken_image_rounded,
                              text: '加载失败',
                            ),
                          ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(10, 9, 10, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      _captureMeta(capture),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: palette.textSub,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LampDetailStateView extends StatelessWidget {
  const _LampDetailStateView({
    required this.palette,
    required this.icon,
    required this.title,
    required this.message,
    this.actionText,
    this.onAction,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String title;
  final String message;
  final String? actionText;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: palette.primaryLight, size: 36),
            const SizedBox(height: 12),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.textSub,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                height: 1.35,
              ),
            ),
            if (actionText != null && onAction != null) ...[
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: Text(actionText!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LampPreviewHeader extends StatelessWidget {
  const _LampPreviewHeader({
    required this.palette,
    required this.title,
    required this.onClose,
  });

  final AppThemePalette palette;
  final String title;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 12, 8),
      child: Row(
        children: [
          IconButton(
            tooltip: '关闭',
            onPressed: onClose,
            icon: const Icon(Icons.close_rounded),
            color: palette.textMain,
          ),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ImageLoading extends StatelessWidget {
  const _ImageLoading({required this.palette});

  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(
          color: palette.primaryLight,
          strokeWidth: 2,
        ),
      ),
    );
  }
}

class _ImagePlaceholder extends StatelessWidget {
  const _ImagePlaceholder({
    required this.palette,
    required this.icon,
    required this.text,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: palette.textSub, size: 24),
          const SizedBox(height: 6),
          Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: palette.textSub,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

String _normaliseDeviceImageUrl(String? raw) {
  final value = raw?.trim() ?? '';
  if (value.isEmpty ||
      value.startsWith('http://') ||
      value.startsWith('https://') ||
      value.startsWith('/')) {
    return value;
  }
  return '/$value';
}

String _captureMeta(DeviceCapture capture) {
  final parts = [
    _formatCaptureTime(capture.createdAt),
    if (capture.fileSize != null) _formatFileSize(capture.fileSize!),
  ];
  return parts.join(' · ');
}

String _formatCaptureTime(DateTime? time) {
  if (time == null) {
    return '暂无时间';
  }

  final local = time.toLocal();
  final minute = local.minute.toString().padLeft(2, '0');
  final hour = local.hour.toString().padLeft(2, '0');
  return '${local.month}月${local.day}日 $hour:$minute';
}

String _formatFileSize(int bytes) {
  if (bytes < 1024) {
    return '$bytes B';
  }
  if (bytes < 1024 * 1024) {
    return '${(bytes / 1024).toStringAsFixed(1)} KB';
  }
  return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
}
