import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../../device/data/device_api.dart';
import '../../../device/data/esp_ble_device_provisioner.dart';

const String _deviceCaptureUploadPath = '/api/device/capture';
final String _defaultDeviceCaptureUploadUrl = _joinUrl(
  ApiClient.defaultBaseUrl,
  _deviceCaptureUploadPath,
);

String _normalizeDeviceCaptureUploadUrl(String value) {
  final uploadUrl =
      value.trim().isEmpty ? _defaultDeviceCaptureUploadUrl : value.trim();
  final uri = Uri.tryParse(uploadUrl);
  if (uri == null ||
      !uri.hasScheme ||
      uri.host.isEmpty ||
      (uri.path.isNotEmpty && uri.path != '/')) {
    return uploadUrl;
  }

  return _joinUrl(uploadUrl, _deviceCaptureUploadPath);
}

String _joinUrl(String baseUrl, String path) {
  final base = baseUrl.trim().replaceFirst(RegExp(r'/+$'), '');
  final suffix = path.startsWith('/') ? path : '/$path';
  return '$base$suffix';
}

class LampConnectPage extends StatefulWidget {
  const LampConnectPage({
    super.key,
    this.deviceApi,
  });

  final DeviceApi? deviceApi;

  @override
  State<LampConnectPage> createState() => _LampConnectPageState();
}

class _LampConnectPageState extends State<LampConnectPage>
    with SingleTickerProviderStateMixin {
  static const String _deviceNamePrefix = '智能学习台灯-';
  static final Uuid _provisioningServiceUuid = Uuid.parse(
    '72135ce8-61d6-4aae-bdcb-5dfb935d0bd1',
  );

  late final DeviceApi _deviceApi;
  final FlutterReactiveBle _ble = FlutterReactiveBle();
  final Map<String, DiscoveredDevice> _devices = {};
  final TextEditingController _wifiSsidController = TextEditingController();
  final TextEditingController _wifiPasswordController = TextEditingController();
  final TextEditingController _uploadUrlController =
      TextEditingController(text: _defaultDeviceCaptureUploadUrl);

  StreamSubscription<BleStatus>? _bleStatusSub;
  StreamSubscription<DiscoveredDevice>? _scanSub;
  StreamSubscription<ConnectionStateUpdate>? _connectionSub;

  BleStatus _bleStatus = BleStatus.unknown;
  DiscoveredDevice? _selectedDevice;
  List<Service> _services = [];

  bool _bindingLoading = false;
  bool _checking = true;
  bool _permissionReady = false;
  bool _bluetoothReady = false;
  bool _scanning = false;
  bool _connecting = false;
  bool _connected = false;
  bool _discoveringServices = false;
  bool _autoConfigDialogShown = false;
  bool _provisioning = false;
  bool _provisioningComplete = false;

  String? _message;
  String? _error;
  String? _deviceIp;
  String? _activeBindingDeviceUuid;
  String _imageProfile = 'medium';
  Map<String, String>? _pendingConfigPayload;

  late final AnimationController _scanController;

  @override
  void initState() {
    super.initState();
    _deviceApi = widget.deviceApi ?? DeviceApi();
    _scanController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();

    _bleStatusSub = _ble.statusStream.listen((status) {
      if (!mounted) {
        return;
      }

      setState(() {
        _bleStatus = status;
        _bluetoothReady = status == BleStatus.ready;
      });

      if (status == BleStatus.ready && _permissionReady && !_scanning) {
        unawaited(_startScan());
      }
    });

    unawaited(_init());
  }

  @override
  void dispose() {
    _bleStatusSub?.cancel();
    _scanSub?.cancel();
    _connectionSub?.cancel();
    _wifiSsidController.dispose();
    _wifiPasswordController.dispose();
    _uploadUrlController.dispose();
    _scanController.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    setState(() {
      _checking = true;
      _message = '正在检查蓝牙权限';
      _error = null;
    });

    final permissionReady = await _requestPermissions();

    if (!mounted) {
      return;
    }

    setState(() {
      _permissionReady = permissionReady;
      _checking = false;
    });

    if (!permissionReady) {
      setState(() {
        _error = '缺少蓝牙权限，请在系统设置中允许蓝牙访问';
        _message = null;
      });
      return;
    }

    if (_bleStatus == BleStatus.ready) {
      await _startScan();
    } else {
      setState(() => _message = '请先打开手机蓝牙');
    }
  }

  Future<bool> _requestPermissions() async {
    if (kIsWeb) {
      return true;
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      final statuses = await [
        Permission.bluetoothScan,
        Permission.bluetoothConnect,
        Permission.locationWhenInUse,
      ].request();

      return (statuses[Permission.bluetoothScan]?.isGranted ?? false) &&
          (statuses[Permission.bluetoothConnect]?.isGranted ?? false) &&
          (statuses[Permission.locationWhenInUse]?.isGranted ?? false);
    }

    if (defaultTargetPlatform == TargetPlatform.iOS) {
      final bluetooth = await Permission.bluetooth.request();
      return bluetooth.isGranted || bluetooth.isLimited;
    }

    return true;
  }

  Future<void> _startScan() async {
    if (!_permissionReady) {
      await _init();
      return;
    }

    if (_bleStatus != BleStatus.ready) {
      setState(() {
        _message = '请先打开手机蓝牙';
        _error = null;
      });
      return;
    }

    await _scanSub?.cancel();
    await _connectionSub?.cancel();

    setState(() {
      _devices.clear();
      _selectedDevice = null;
      _services = [];
      _scanning = true;
      _connected = false;
      _connecting = false;
      _discoveringServices = false;
      _autoConfigDialogShown = false;
      _provisioning = false;
      _bindingLoading = false;
      _provisioningComplete = false;
      _deviceIp = null;
      _activeBindingDeviceUuid = null;
      _pendingConfigPayload = null;
      _error = null;
      _message = '正在搜索附近产品';
    });

    _scanSub = _ble
        .scanForDevices(
      withServices: _scanServiceUuids,
      scanMode: ScanMode.lowLatency,
    )
        .listen(
      (device) {
        final name = device.name.trim();
        if (!mounted || !name.startsWith(_deviceNamePrefix)) {
          return;
        }

        setState(() => _devices[device.id] = device);
      },
      onError: (Object error) {
        if (!mounted) {
          return;
        }

        setState(() {
          _scanning = false;
          _error = '扫描失败：$error';
          _message = null;
        });
      },
    );

    Future<void>.delayed(const Duration(seconds: 12), () async {
      if (!mounted || !_scanning) {
        return;
      }

      await _scanSub?.cancel();
      _scanSub = null;

      setState(() {
        _scanning = false;
        _message =
            _devices.isEmpty ? '没有搜索到设备，请确认台灯处于配网模式' : '请确认要连接的设备，并点击进入连接';
      });
    });
  }

  Future<void> _connectDevice(DiscoveredDevice device) async {
    await _scanSub?.cancel();
    await _connectionSub?.cancel();

    setState(() {
      _selectedDevice = device;
      _scanning = false;
      _connecting = true;
      _connected = false;
      _discoveringServices = false;
      _services = [];
      _error = null;
      _message = '正在连接 ${_deviceLabel(device)}';
    });

    _connectionSub = _ble
        .connectToDevice(
      id: device.id,
      connectionTimeout: const Duration(seconds: 15),
    )
        .listen(
      (update) async {
        if (!mounted) {
          return;
        }

        if (update.connectionState == DeviceConnectionState.connected) {
          setState(() {
            _connecting = false;
            _connected = true;
            _message = '连接成功，正在发现服务';
          });

          await _discoverServices(device.id);
          _scheduleConfigDialog();
        } else if (update.connectionState ==
            DeviceConnectionState.disconnected) {
          setState(() {
            _connecting = false;
            _connected = false;
            _discoveringServices = false;
            _autoConfigDialogShown = false;
            if (_provisioning) {
              _message = '设备已退出配网模式，正在确认结果';
            } else {
              _message = _provisioningComplete ? '配网完成，设备已退出配网模式' : '设备已断开连接';
            }
          });
        }
      },
      onError: (Object error) {
        if (!mounted) {
          return;
        }

        setState(() {
          _connecting = false;
          _connected = false;
          _discoveringServices = false;
          _provisioning = false;
          _error = '连接失败：$error';
          _message = null;
        });
      },
    );
  }

  Future<void> _disconnect({String message = '已断开连接'}) async {
    await _connectionSub?.cancel();

    setState(() {
      _connecting = false;
      _connected = false;
      _discoveringServices = false;
      _autoConfigDialogShown = false;
      _provisioning = false;
      _provisioningComplete = false;
      _selectedDevice = null;
      _services = [];
      _deviceIp = null;
      _activeBindingDeviceUuid = null;
      _pendingConfigPayload = null;
      _message = message;
    });
  }

  void _scheduleConfigDialog() {
    if (_autoConfigDialogShown || !_connected) {
      return;
    }

    _autoConfigDialogShown = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_connected) {
        return;
      }
      unawaited(_openConfigDialog());
    });
  }

  Future<void> _openConfigDialog() async {
    if (!_connected) {
      return;
    }

    _ensureDefaultUploadUrl();

    final hadConfig = _pendingConfigPayload != null;
    final configured = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final palette = AppThemePalette.of(context);

            return MediaQuery.removeViewInsets(
              removeBottom: true,
              context: context,
              child: Dialog(
                backgroundColor: palette.pageBg,
                insetPadding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 24,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 520),
                  child: _PanelShell(
                    palette: palette,
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '设备配网',
                                style: TextStyle(
                                  color: palette.textMain,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                            IconButton(
                              onPressed: _provisioning
                                  ? null
                                  : () =>
                                      Navigator.of(dialogContext).pop(false),
                              icon: Icon(
                                Icons.close_rounded,
                                color: palette.textSub,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '点击配置后会先创建后端设备绑定，随后写入 Wi-Fi 和上传参数；关闭窗口将断开当前连接。',
                          style: TextStyle(
                            color: palette.textSub,
                            fontSize: 12,
                            height: 1.45,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 14),
                        _ProvisioningConfigPanel(
                          palette: palette,
                          ssidController: _wifiSsidController,
                          passwordController: _wifiPasswordController,
                          uploadUrlController: _uploadUrlController,
                          imageProfile: _imageProfile,
                          onImageProfileChanged: (value) {
                            setState(() {
                              _imageProfile = value;
                            });
                            setDialogState(() {});
                          },
                        ),
                        if (_provisioning || _message != null) ...[
                          const SizedBox(height: 10),
                          _InlineNotice(
                            text: _message ?? '正在配置设备',
                            palette: palette,
                          ),
                        ],
                        if (_error != null) ...[
                          const SizedBox(height: 10),
                          _InlineNotice(
                            text: _error!,
                            palette: palette,
                            isError: true,
                          ),
                        ],
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: _LampSecondaryButton(
                                text: '取消',
                                icon: Icons.close_rounded,
                                palette: palette,
                                onPressed: _provisioning
                                    ? null
                                    : () =>
                                        Navigator.of(dialogContext).pop(false),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: _LampPrimaryButton(
                                text: _bindingLoading
                                    ? '绑定中'
                                    : _provisioning
                                        ? '配置中'
                                        : '配置',
                                icon: _provisioning || _bindingLoading
                                    ? Icons.sync_rounded
                                    : Icons.send_rounded,
                                palette: palette,
                                onPressed: _provisioning || _bindingLoading
                                    ? null
                                    : () async {
                                        setDialogState(() {});
                                        final accepted =
                                            await _submitProvisioningConfig(
                                          onStateChanged: () {
                                            if (dialogContext.mounted) {
                                              setDialogState(() {});
                                            }
                                          },
                                        );
                                        if (!dialogContext.mounted) {
                                          return;
                                        }
                                        setDialogState(() {});

                                        if (accepted) {
                                          Navigator.of(dialogContext).pop(true);
                                        }
                                      },
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        );
      },
    );

    if (!mounted || !_connected || configured == true || hadConfig) {
      return;
    }

    await _disconnect(message: '未完成配网，已断开连接');
  }

  void _ensureDefaultUploadUrl() {
    if (_uploadUrlController.text.trim().isNotEmpty) {
      return;
    }

    _uploadUrlController.text = _defaultDeviceCaptureUploadUrl;
  }

  Future<bool> _submitProvisioningConfig({
    VoidCallback? onStateChanged,
  }) async {
    final ssid = _wifiSsidController.text.trim();
    final password = _wifiPasswordController.text;
    final uploadUrl = _normalizeDeviceCaptureUploadUrl(
      _uploadUrlController.text.trim(),
    );

    String? validationError;
    if (ssid.isEmpty) {
      validationError = '请输入 Wi-Fi 名称';
    } else if (!_isValidUploadUrl(uploadUrl)) {
      validationError = '请输入有效的上传地址';
    }

    if (validationError != null) {
      setState(() {
        _error = validationError;
      });
      onStateChanged?.call();
      return false;
    }

    if (_uploadUrlController.text.trim() != uploadUrl) {
      _uploadUrlController.text = uploadUrl;
    }

    setState(() {
      _error = null;
      _message = '正在创建设备绑定';
      _bindingLoading = true;
      _provisioning = true;
    });
    onStateChanged?.call();

    String? createdDeviceUuid;

    try {
      final binding = await _deviceApi.bindDevice();
      final deviceUuid = binding.deviceUuid.trim();

      if (!binding.success || deviceUuid.isEmpty) {
        throw const DeviceProvisioningException('设备绑定创建失败');
      }

      createdDeviceUuid = deviceUuid;

      if (!mounted) {
        await _rollbackDeviceBinding(deviceUuid);
        return false;
      }

      setState(() {
        _bindingLoading = false;
        _activeBindingDeviceUuid = deviceUuid;
        _message = '正在准备配网';
      });
      onStateChanged?.call();

      final result = await _provisionDevice(
        DeviceProvisioningRequest(
          deviceId: deviceUuid,
          wifiSsid: ssid,
          wifiPassword: password,
          uploadUrl: uploadUrl,
          imageProfile: _imageProfile,
        ),
        onStateChanged: onStateChanged,
      );

      if (!mounted) {
        return false;
      }

      setState(() {
        _pendingConfigPayload = {
          'device_id': deviceUuid,
          'upload_url': uploadUrl,
          'image_profile': _imageProfile,
        };
        _activeBindingDeviceUuid = null;
        _bindingLoading = false;
        _provisioning = false;
        _provisioningComplete = true;
        _deviceIp = result.deviceIp;
        _error = null;
        _message = result.deviceIp == null || result.deviceIp!.isEmpty
            ? '配网完成'
            : '配网完成，设备 IP：${result.deviceIp}';
      });
      onStateChanged?.call();
      return true;
    } catch (error) {
      if (createdDeviceUuid != null && createdDeviceUuid.isNotEmpty) {
        final clearActiveBinding =
            _activeBindingDeviceUuid == createdDeviceUuid;
        if (mounted) {
          setState(() {
            if (clearActiveBinding) {
              _activeBindingDeviceUuid = null;
            }
            _bindingLoading = false;
            _message = '配网失败，正在回滚设备绑定';
          });
          onStateChanged?.call();
        }
        await _rollbackDeviceBinding(createdDeviceUuid);
      }

      if (!mounted) {
        return false;
      }

      setState(() {
        _activeBindingDeviceUuid = null;
        _bindingLoading = false;
        _provisioning = false;
        _error = error is DeviceProvisioningException
            ? error.message
            : '配网失败：$error';
        _message = null;
      });
      onStateChanged?.call();
      return false;
    }
  }

  Future<void> _rollbackDeviceBinding(String deviceUuid) async {
    try {
      await _deviceApi.unbindDevice(deviceUuid);
    } catch (_) {
      // The original provisioning failure is more useful to show here.
    }
  }

  Future<DeviceProvisioningResult> _provisionDevice(
      DeviceProvisioningRequest request,
      {VoidCallback? onStateChanged}) {
    final device = _selectedDevice;
    if (device == null) {
      throw const DeviceProvisioningException('没有可配置的设备连接');
    }

    final provisioner = EspBleDeviceProvisioner(
      ble: _ble,
      bleDeviceId: device.id,
      provisioningServiceUuid: _provisioningServiceUuid,
      isConnected: () => _connected,
      onProgress: (message) {
        if (!mounted) {
          return;
        }
        setState(() {
          _message = message;
          _error = null;
        });
        onStateChanged?.call();
      },
    );

    return provisioner.provision(request);
  }

  bool _isValidUploadUrl(String value) {
    return isValidDeviceUploadUrl(value);
  }

  Future<void> _discoverServices(String deviceId) async {
    setState(() {
      _discoveringServices = true;
      _message = '正在发现设备服务';
    });

    try {
      await _ble.discoverAllServices(deviceId);
      final services = await _ble.getDiscoveredServices(deviceId);

      if (!mounted) {
        return;
      }

      setState(() {
        _services = services;
        _discoveringServices = false;
        _message = '已连接设备';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _discoveringServices = false;
        _error = '发现服务失败：$error';
        _message = null;
      });
    }
  }

  bool get _isBusy =>
      _bindingLoading ||
      _checking ||
      _scanning ||
      _connecting ||
      _discoveringServices ||
      _provisioning;

  List<Uuid> get _scanServiceUuids => [_provisioningServiceUuid];

  String get _titleText {
    if (_checking) {
      return '准备蓝牙搜索';
    }
    if (_connected) {
      return _provisioning ? '正在配置设备' : '设备已连接';
    }
    if (_provisioningComplete) {
      return '配网完成';
    }
    if (_connecting) {
      return '正在建立连接';
    }
    return '搜索附近设备';
  }

  String get _subtitleText {
    if (_checking) {
      return '正在检查蓝牙权限';
    }
    if (!_permissionReady) {
      return '允许蓝牙权限后，才能发现并连接附近的学习台灯';
    }
    if (!_bluetoothReady) {
      return '请开启手机蓝牙，并确保设备处于可连接状态';
    }
    if (_connected) {
      return _provisioning ? '正在写入 Wi-Fi 和上传参数' : '连接已建立，请完成设备配网';
    }
    if (_provisioningComplete) {
      return '设备已完成配置并退出配网模式';
    }
    return '正在搜索处于配网模式的智能学习台灯';
  }

  String get _statusLabel {
    if (_bindingLoading) {
      return '绑定中';
    }
    if (_checking) {
      return '检查中';
    }
    if (_provisioning) {
      return '配置中';
    }
    if (_provisioningComplete) {
      return '已完成';
    }
    if (_connected) {
      return '已连接';
    }
    if (_connecting) {
      return '连接中';
    }
    if (_scanning) {
      return '搜索中';
    }
    if (!_permissionReady) {
      return '待授权';
    }
    if (!_bluetoothReady) {
      return '蓝牙未就绪';
    }
    return '待搜索';
  }

  IconData get _statusIcon {
    if (_provisioningComplete) {
      return Icons.check_rounded;
    }
    if (_connected) {
      return Icons.link_rounded;
    }
    if (_checking || _connecting || _scanning || _provisioning) {
      return Icons.sync_rounded;
    }
    if (!_permissionReady) {
      return Icons.lock_outline_rounded;
    }
    if (!_bluetoothReady) {
      return Icons.bluetooth_disabled_rounded;
    }
    return Icons.bluetooth_searching_rounded;
  }

  Color _statusColor(AppThemePalette palette) {
    if (_checking || _connecting || _scanning || _provisioning) {
      return const Color(0xFFD0A35C);
    }
    if (_error != null || !_permissionReady || !_bluetoothReady) {
      return palette.errorText;
    }
    if (_connected || _provisioningComplete) {
      return const Color(0xFF63C9B2);
    }
    return palette.primary;
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final maxWidth =
                  constraints.maxWidth >= 760 ? 680.0 : constraints.maxWidth;

              return SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                child: Center(
                  child: ConstrainedBox(
                    constraints: BoxConstraints(maxWidth: maxWidth),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _SearchTopBar(
                          palette: palette,
                          statusLabel: _statusLabel,
                          statusIcon: _statusIcon,
                          statusColor: _statusColor(palette),
                          onBack: () => Navigator.of(context).pop(),
                        ),
                        const SizedBox(height: 14),
                        _SearchPanel(
                          palette: palette,
                          title: _titleText,
                          subtitle: _subtitleText,
                          statusLabel: _statusLabel,
                          statusIcon: _statusIcon,
                          statusColor: _statusColor(palette),
                          controller: _scanController,
                          active: _isBusy,
                          connected: _connected,
                          action: _buildActionArea(palette),
                          message: _message,
                          error: _error,
                        ),
                        if (_devices.isNotEmpty && !_connected) ...[
                          const SizedBox(height: 14),
                          _buildDeviceList(palette),
                        ],
                        if (_connected) ...[
                          const SizedBox(height: 14),
                          _buildConnectedPanel(palette),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildActionArea(AppThemePalette palette) {
    if (!_permissionReady) {
      return _LampPrimaryButton(
        text: '允许蓝牙权限',
        icon: Icons.lock_open_rounded,
        palette: palette,
        onPressed: _init,
      );
    }

    if (!_bluetoothReady) {
      return _LampPrimaryButton(
        text: '重新检查蓝牙',
        icon: Icons.bluetooth_rounded,
        palette: palette,
        onPressed: _init,
      );
    }

    return _LampPrimaryButton(
      text: _scanning ? '正在搜索' : '重新搜索',
      icon: Icons.bluetooth_searching_rounded,
      palette: palette,
      onPressed: _scanning ? null : _startScan,
    );
  }

  Widget _buildDeviceList(AppThemePalette palette) {
    final devices = _devices.values.toList()
      ..sort((a, b) => b.rssi.compareTo(a.rssi));

    return _PanelShell(
      palette: palette,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            palette: palette,
            title: '可连接设备',
            trailing: '${devices.length} 台',
          ),
          const SizedBox(height: 10),
          ...devices.map(
            (device) => _DeviceTile(
              device: device,
              palette: palette,
              connecting: _connecting && _selectedDevice?.id == device.id,
              onTap: _connecting ? null : () => _connectDevice(device),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConnectedPanel(AppThemePalette palette) {
    final device = _selectedDevice;

    return _InfoPanel(
      palette: palette,
      title: '当前连接',
      rows: [
        _InfoRowData(label: '设备名称', value: _deviceLabel(device)),
        _InfoRowData(label: '连接状态', value: _connected ? '已连接' : '未连接'),
        _InfoRowData(label: '服务数量', value: '${_services.length}'),
        _InfoRowData(
          label: '配置状态',
          value: _configStateText,
        ),
        if (_deviceIp != null && _deviceIp!.isNotEmpty)
          _InfoRowData(label: '设备 IP', value: _deviceIp!),
      ],
    );
  }

  String get _configStateText {
    if (_provisioning) {
      return '写入中';
    }
    if (_provisioningComplete) {
      return '已完成';
    }
    return _pendingConfigPayload == null ? '待配置' : '已写入';
  }

  String _deviceLabel(DiscoveredDevice? device) {
    if (device == null) {
      return '-';
    }

    final name = device.name.trim();
    return name.isEmpty ? '未命名设备' : name;
  }
}

class _SearchTopBar extends StatelessWidget {
  const _SearchTopBar({
    required this.palette,
    required this.statusLabel,
    required this.statusIcon,
    required this.statusColor,
    required this.onBack,
  });

  final AppThemePalette palette;
  final String statusLabel;
  final IconData statusIcon;
  final Color statusColor;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Icon(Icons.arrow_back_ios_new_rounded),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '台灯搜索',
                style: TextStyle(
                  color: palette.textMain,
                  fontWeight: FontWeight.w900,
                  fontSize: 18,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SearchPanel extends StatelessWidget {
  const _SearchPanel({
    required this.palette,
    required this.title,
    required this.subtitle,
    required this.statusLabel,
    required this.statusIcon,
    required this.statusColor,
    required this.controller,
    required this.active,
    required this.connected,
    required this.action,
    required this.message,
    required this.error,
  });

  final AppThemePalette palette;
  final String title;
  final String subtitle;
  final String statusLabel;
  final IconData statusIcon;
  final Color statusColor;
  final AnimationController controller;
  final bool active;
  final bool connected;
  final Widget action;
  final String? message;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return _PanelShell(
      palette: palette,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 22,
                        height: 1.2,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: palette.textSub,
                        fontSize: 13,
                        height: 1.45,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _StatusBadge(
                palette: palette,
                label: statusLabel,
                icon: statusIcon,
                color: statusColor,
              ),
            ],
          ),
          const SizedBox(height: 18),
          _SearchRadar(
            palette: palette,
            controller: controller,
            active: active,
            connected: connected,
          ),
          const SizedBox(height: 16),
          action,
          if (message != null) ...[
            const SizedBox(height: 6),
            _InlineNotice(text: message!, palette: palette),
          ],
          if (error != null) ...[
            const SizedBox(height: 6),
            _InlineNotice(text: error!, palette: palette, isError: true),
          ],
        ],
      ),
    );
  }
}

class _SearchRadar extends StatelessWidget {
  const _SearchRadar({
    required this.palette,
    required this.controller,
    required this.active,
    required this.connected,
  });

  final AppThemePalette palette;
  final AnimationController controller;
  final bool active;
  final bool connected;

  @override
  Widget build(BuildContext context) {
    final accent = connected ? palette.primaryLight : palette.primary;

    return Center(
      child: AnimatedBuilder(
        animation: controller,
        builder: (context, child) {
          final progress = active ? controller.value : 0.35;
          final pulseScale = 0.62 + progress * 0.36;
          final pulseOpacity = active ? 0.18 + (1 - progress) * 0.12 : 0.16;

          return SizedBox(
            width: 236,
            height: 236,
            child: Stack(
              alignment: Alignment.center,
              children: [
                _RadarRing(size: 236, opacity: 0.11, accent: accent),
                _RadarRing(size: 176, opacity: 0.15, accent: accent),
                _RadarRing(size: 116, opacity: 0.19, accent: accent),
                if (active)
                  Transform.scale(
                    scale: pulseScale,
                    child: Container(
                      width: 236,
                      height: 236,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: accent.withOpacity(pulseOpacity),
                      ),
                    ),
                  ),
                Container(
                  width: 82,
                  height: 82,
                  decoration: BoxDecoration(
                    color: palette.isLight
                        ? Colors.white.withOpacity(0.92)
                        : Colors.white.withOpacity(0.08),
                    shape: BoxShape.circle,
                    border: Border.all(color: accent.withOpacity(0.24)),
                    boxShadow: [
                      BoxShadow(
                        color: accent.withOpacity(0.16),
                        blurRadius: 28,
                        offset: const Offset(0, 12),
                      ),
                    ],
                  ),
                  child: Icon(
                    connected
                        ? Icons.check_rounded
                        : Icons.bluetooth_searching_rounded,
                    color: accent,
                    size: 34,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _RadarRing extends StatelessWidget {
  const _RadarRing({
    required this.size,
    required this.opacity,
    required this.accent,
  });

  final double size;
  final double opacity;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: accent.withOpacity(opacity * 0.38),
        border: Border.all(color: accent.withOpacity(opacity)),
      ),
    );
  }
}

class _ProvisioningConfigPanel extends StatelessWidget {
  const _ProvisioningConfigPanel({
    required this.palette,
    required this.ssidController,
    required this.passwordController,
    required this.uploadUrlController,
    required this.imageProfile,
    required this.onImageProfileChanged,
  });

  final AppThemePalette palette;
  final TextEditingController ssidController;
  final TextEditingController passwordController;
  final TextEditingController uploadUrlController;
  final String imageProfile;
  final ValueChanged<String> onImageProfileChanged;

  @override
  Widget build(BuildContext context) {
    return _PanelShell(
      palette: palette,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(palette: palette, title: '配网参数'),
          const SizedBox(height: 12),
          _ConfigTextField(
            palette: palette,
            controller: ssidController,
            label: 'Wi-Fi 名称',
            hintText: '输入要连接的 SSID',
            icon: Icons.wifi_rounded,
          ),
          const SizedBox(height: 10),
          _ConfigTextField(
            palette: palette,
            controller: passwordController,
            label: 'Wi-Fi 密码',
            hintText: '输入 Wi-Fi 密码',
            icon: Icons.lock_outline_rounded,
            obscureText: true,
          ),
          const SizedBox(height: 10),
          _ConfigTextField(
            palette: palette,
            controller: uploadUrlController,
            label: '上传地址',
            hintText: _defaultDeviceCaptureUploadUrl,
            icon: Icons.cloud_upload_outlined,
            keyboardType: TextInputType.url,
          ),
          const SizedBox(height: 12),
          Text(
            '图片档位',
            style: TextStyle(
              color: palette.textSub,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _ProfileOption(
                palette: palette,
                label: '低',
                value: 'low',
                selectedValue: imageProfile,
                onSelected: onImageProfileChanged,
              ),
              const SizedBox(width: 8),
              _ProfileOption(
                palette: palette,
                label: '中',
                value: 'medium',
                selectedValue: imageProfile,
                onSelected: onImageProfileChanged,
              ),
              const SizedBox(width: 8),
              _ProfileOption(
                palette: palette,
                label: '高',
                value: 'high',
                selectedValue: imageProfile,
                onSelected: onImageProfileChanged,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ConfigTextField extends StatelessWidget {
  const _ConfigTextField({
    required this.palette,
    required this.controller,
    required this.label,
    required this.hintText,
    required this.icon,
    this.obscureText = false,
    this.keyboardType,
  });

  final AppThemePalette palette;
  final TextEditingController controller;
  final String label;
  final String hintText;
  final IconData icon;
  final bool obscureText;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      style: TextStyle(
        color: palette.textMain,
        fontSize: 13,
        fontWeight: FontWeight.w700,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        prefixIcon: Icon(icon, color: palette.textSub, size: 18),
        labelStyle: TextStyle(
          color: palette.textSub,
          fontWeight: FontWeight.w700,
        ),
        hintStyle: TextStyle(
          color: palette.textSub.withOpacity(0.66),
          fontWeight: FontWeight.w600,
        ),
        filled: true,
        fillColor: palette.selectedBg,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: palette.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(
            color: palette.primary.withOpacity(0.72),
          ),
        ),
      ),
    );
  }
}

class _ProfileOption extends StatelessWidget {
  const _ProfileOption({
    required this.palette,
    required this.label,
    required this.value,
    required this.selectedValue,
    required this.onSelected,
  });

  final AppThemePalette palette;
  final String label;
  final String value;
  final String selectedValue;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final selected = value == selectedValue;

    return Expanded(
      child: InkWell(
        onTap: () => onSelected(value),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected
                ? palette.primary.withOpacity(0.16)
                : palette.selectedBg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color:
                  selected ? palette.primary.withOpacity(0.36) : palette.border,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: selected ? palette.primaryLight : palette.textSub,
              fontSize: 13,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
      ),
    );
  }
}

class _DeviceTile extends StatelessWidget {
  const _DeviceTile({
    required this.device,
    required this.palette,
    required this.connecting,
    required this.onTap,
  });

  final DiscoveredDevice device;
  final AppThemePalette palette;
  final bool connecting;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final name = device.name.trim().isEmpty ? '未命名设备' : device.name.trim();

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: palette.selectedBg,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: palette.border),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.light,
                  color: palette.primaryLight,
                  size: 26,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: TextStyle(
                          color: palette.textMain,
                          fontWeight: FontWeight.w900,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                if (connecting)
                  SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: palette.primaryLight,
                    ),
                  )
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel({
    required this.palette,
    required this.title,
    required this.rows,
  });

  final AppThemePalette palette;
  final String title;
  final List<_InfoRowData> rows;

  @override
  Widget build(BuildContext context) {
    return _PanelShell(
      palette: palette,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(palette: palette, title: title),
          const SizedBox(height: 12),
          ...rows.map(
            (row) => Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 82,
                    child: Text(
                      row.label,
                      style: TextStyle(
                        color: palette.textSub,
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      row.value,
                      style: TextStyle(
                        color: palette.textMain,
                        fontWeight: FontWeight.w800,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRowData {
  const _InfoRowData({required this.label, required this.value});

  final String label;
  final String value;
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.palette,
    required this.title,
    this.trailing,
  });

  final AppThemePalette palette;
  final String title;
  final String? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 15,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        if (trailing != null)
          Text(
            trailing!,
            style: TextStyle(
              color: palette.textSub,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
      ],
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.palette,
    required this.label,
    required this.icon,
    required this.color,
  });

  final AppThemePalette palette;
  final String label;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: color.withOpacity(palette.isLight ? 0.10 : 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withOpacity(0.20)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 14),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({
    required this.text,
    required this.palette,
    this.isError = false,
  });

  final String text;
  final AppThemePalette palette;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final color = isError ? palette.errorText : palette.textSub;

    return Text(
      text,
      textAlign: TextAlign.center,
      style: TextStyle(
        color: color,
        fontSize: 13,
        height: 1.45,
        fontWeight: FontWeight.w800,
      ),
    );
  }
}

class _PanelShell extends StatelessWidget {
  const _PanelShell({
    required this.palette,
    required this.child,
    required this.padding,
  });

  final AppThemePalette palette;
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      child: child,
    );
  }
}

class _LampPrimaryButton extends StatelessWidget {
  const _LampPrimaryButton({
    required this.text,
    required this.icon,
    required this.palette,
    required this.onPressed,
  });

  final String text;
  final IconData icon;
  final AppThemePalette palette;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 50,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(10),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: palette.primaryLight, size: 18),
            const SizedBox(width: 8),
            Text(
              text,
              style: TextStyle(
                color: palette.primaryLight,
                fontSize: 14,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LampSecondaryButton extends StatelessWidget {
  const _LampSecondaryButton({
    required this.text,
    required this.icon,
    required this.palette,
    required this.onPressed,
  });

  final String text;
  final IconData icon;
  final AppThemePalette palette;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 50,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(10),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: palette.textSub, size: 18),
            const SizedBox(width: 8),
            Text(
              text,
              style: TextStyle(
                color: palette.textSub,
                fontSize: 14,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
