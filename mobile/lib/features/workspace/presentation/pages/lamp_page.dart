import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../device/data/device_api.dart';
import 'lamp_connect_page.dart';
import 'lamp_detail_page.dart';

class LampPage extends StatefulWidget {
  const LampPage({super.key, this.deviceApi});

  final DeviceApi? deviceApi;

  @override
  State<LampPage> createState() => _LampPageState();
}

class _LampPageState extends State<LampPage> {
  late final DeviceApi _deviceApi;

  DeviceBindingResponse? _binding;
  bool _loading = true;
  bool _unbinding = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _deviceApi = widget.deviceApi ?? DeviceApi();
    _loadBinding();
  }

  Future<void> _loadBinding() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final binding = await _deviceApi.getBinding();
      if (!mounted) {
        return;
      }
      setState(() {
        _binding = binding;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _error = error is ApiException ? error.message : '设备绑定状态加载失败';
      });
    }
  }

  Future<void> _openConnectPage() async {
    if (_binding?.bound == true) {
      return;
    }

    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => const LampConnectPage(),
      ),
    );

    if (mounted) {
      await _loadBinding();
    }
  }

  Future<void> _openDetailPage() async {
    final deviceUuid = _binding?.deviceUuid;
    if (_binding?.bound != true || deviceUuid == null || deviceUuid.isEmpty) {
      return;
    }

    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LampDetailPage(
          deviceUuid: deviceUuid,
          deviceApi: _deviceApi,
        ),
      ),
    );
  }

  Future<void> _unbind() async {
    final deviceUuid = _binding?.deviceUuid;
    if (deviceUuid == null || deviceUuid.isEmpty || _unbinding) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        final palette = AppThemePalette.of(context);

        return AlertDialog(
          backgroundColor: palette.menuBg,
          title: Text(
            '解除绑定',
            style: TextStyle(
              color: palette.textMain,
              fontWeight: FontWeight.w900,
            ),
          ),
          content: Text(
            '解除后可以重新绑定另一台智能学习台灯。',
            style: TextStyle(
              color: palette.textSub,
              fontWeight: FontWeight.w700,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text('取消', style: TextStyle(color: palette.textSub)),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text('解除', style: TextStyle(color: palette.errorText)),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _unbinding = true;
      _error = null;
    });

    try {
      await _deviceApi.unbindDevice(deviceUuid);
      if (mounted) {
        await _loadBinding();
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error is ApiException ? error.message : '解除绑定失败';
      });
    } finally {
      if (mounted) {
        setState(() => _unbinding = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);
    final bound = _binding?.bound == true && _binding?.deviceUuid != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              '智能学习台灯',
              style: TextStyle(
                color: palette.textMain,
                fontWeight: FontWeight.w800,
                fontSize: 22,
              ),
            ),
            const Spacer(),
            if (!bound && !_loading)
              _AddLampButton(palette: palette, onTap: _openConnectPage),
          ],
        ),
        const SizedBox(height: 16),
        if (_loading)
          _LampLoadingCard(palette: palette)
        else if (bound)
          _BoundLampCard(
            palette: palette,
            unbinding: _unbinding,
            onTap: _openDetailPage,
            onUnbind: _unbind,
          )
        else
          _EmptyLampCard(palette: palette, onTap: _openConnectPage),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(
            _error!,
            style: TextStyle(
              color: palette.errorText,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ],
    );
  }
}

class _AddLampButton extends StatelessWidget {
  const _AddLampButton({required this.palette, required this.onTap});

  final AppThemePalette palette;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        width: 64,
        height: 64,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: palette.cardBg,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: palette.panelBorder),
        ),
        child: Icon(
          Icons.add_rounded,
          color: palette.primaryLight,
          size: 34,
          semanticLabel: '添加学习台灯',
        ),
      ),
    );
  }
}

class _BoundLampCard extends StatelessWidget {
  const _BoundLampCard({
    required this.palette,
    required this.unbinding,
    required this.onTap,
    required this.onUnbind,
  });

  final AppThemePalette palette;
  final bool unbinding;
  final VoidCallback onTap;
  final VoidCallback onUnbind;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: palette.cardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: palette.panelBorder),
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: palette.selectedBg,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.light, color: palette.primaryLight, size: 30),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '智能学习台灯',
                    style: TextStyle(
                      color: palette.textMain,
                      fontWeight: FontWeight.w900,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '已绑定',
                    style: TextStyle(
                      color: palette.textSub,
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: unbinding ? null : onUnbind,
              tooltip: '解除绑定',
              icon: unbinding
                  ? SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: palette.textSub,
                      ),
                    )
                  : Icon(Icons.link_off_rounded, color: palette.textSub),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyLampCard extends StatelessWidget {
  const _EmptyLampCard({required this.palette, required this.onTap});

  final AppThemePalette palette;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: palette.cardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: palette.panelBorder),
        ),
        child: Row(
          children: [
            Icon(Icons.add_rounded, color: palette.primaryLight, size: 28),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                '添加智能学习台灯',
                style: TextStyle(
                  color: palette.textMain,
                  fontWeight: FontWeight.w900,
                  fontSize: 15,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LampLoadingCard extends StatelessWidget {
  const _LampLoadingCard({required this.palette});

  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 84,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.panelBorder),
      ),
      child: CircularProgressIndicator(color: palette.primaryLight),
    );
  }
}
