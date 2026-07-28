import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:esp_provisioning_ble/esp_provisioning_ble.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart' as ble;

class DeviceProvisioningRequest {
  const DeviceProvisioningRequest({
    required this.deviceId,
    required this.wifiSsid,
    required this.wifiPassword,
    required this.uploadUrl,
    required this.imageProfile,
  });

  final String deviceId;
  final String wifiSsid;
  final String wifiPassword;
  final String uploadUrl;
  final String imageProfile;

  void validateDeviceConfig() {
    if (!isValidDeviceConfigId(deviceId)) {
      throw const DeviceProvisioningException('设备 ID 无效');
    }
    if (!isValidDeviceUploadUrl(uploadUrl)) {
      throw const DeviceProvisioningException('上传地址无效');
    }
    if (!isValidDeviceImageProfile(imageProfile)) {
      throw const DeviceProvisioningException('图片档位无效');
    }
  }

  Map<String, String> toDeviceConfigJson() {
    return {
      'op': 'set',
      'device_id': deviceId.trim(),
      'upload_url': uploadUrl.trim(),
      'image_profile': imageProfile.trim(),
    };
  }
}

final RegExp _deviceConfigUuidPattern = RegExp(
  r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
);

const Set<String> _deviceImageProfiles = {'low', 'medium', 'high'};

bool isValidDeviceConfigId(String value) {
  return _deviceConfigUuidPattern.hasMatch(value.trim());
}

bool isValidDeviceUploadUrl(String value) {
  final trimmed = value.trim();
  return trimmed.length < 256 &&
      !trimmed.contains(RegExp(r'\s')) &&
      (trimmed.startsWith('http://') || trimmed.startsWith('https://'));
}

bool isValidDeviceImageProfile(String value) {
  return _deviceImageProfiles.contains(value.trim());
}

class DeviceProvisioningResult {
  const DeviceProvisioningResult({this.deviceIp});

  final String? deviceIp;
}

class DeviceProvisioningException implements Exception {
  const DeviceProvisioningException(this.message);

  final String message;

  @override
  String toString() => message;
}

class EspBleDeviceProvisioner {
  EspBleDeviceProvisioner({
    required ble.FlutterReactiveBle ble,
    required String bleDeviceId,
    required ble.Uuid provisioningServiceUuid,
    required bool Function() isConnected,
    this.onProgress,
    this.statusTimeout = const Duration(seconds: 45),
    this.statusPollInterval = const Duration(seconds: 2),
  }) : _transport = ReactiveBleProvTransport(
          ble: ble,
          deviceId: bleDeviceId,
          serviceUuid: provisioningServiceUuid,
          isConnected: isConnected,
        );

  final ReactiveBleProvTransport _transport;
  final void Function(String message)? onProgress;
  final Duration statusTimeout;
  final Duration statusPollInterval;

  Future<DeviceProvisioningResult> provision(
    DeviceProvisioningRequest request,
  ) async {
    request.validateDeviceConfig();

    final security = Security1();
    final prov = EspProv(transport: _transport, security: security);

    onProgress?.call('正在建立安全会话');
    final connected = await _transport.connect();
    _debugProvisioningLog('transport.connect => $connected');
    if (!connected) {
      throw const DeviceProvisioningException('设备连接已断开');
    }

    late final EstablishSessionStatus sessionStatus;
    try {
      sessionStatus =
          await prov.establishSession().timeout(const Duration(seconds: 20));
    } catch (error) {
      _debugProvisioningLog('establishSession error => $error');
      rethrow;
    }
    _debugProvisioningLog('establishSession => $sessionStatus');
    if (sessionStatus != EstablishSessionStatus.connected) {
      throw DeviceProvisioningException(
        sessionStatus == EstablishSessionStatus.keymismatch
            ? '安全会话校验失败'
            : '安全会话建立失败',
      );
    }

    onProgress?.call('正在发送 Wi-Fi 凭据');
    late final bool configSent;
    try {
      configSent = await prov
          .sendWifiConfig(
            ssid: request.wifiSsid,
            password: request.wifiPassword,
          )
          .timeout(const Duration(seconds: 20));
    } catch (error) {
      _debugProvisioningLog('sendWifiConfig error => $error');
      rethrow;
    }
    _debugProvisioningLog('sendWifiConfig => $configSent');
    if (!configSent) {
      throw const DeviceProvisioningException('Wi-Fi 凭据写入失败');
    }

    onProgress?.call('正在写入上传参数');
    await _sendDeviceConfig(security, request);

    onProgress?.call('正在应用 Wi-Fi 配置');
    late final bool configApplied;
    try {
      configApplied =
          await prov.applyWifiConfig().timeout(const Duration(seconds: 100));
    } catch (error) {
      _debugProvisioningLog('applyWifiConfig error => $error');
      rethrow;
    }
    _debugProvisioningLog('😢applyWifiConfig => $configApplied');
    if (!configApplied) {
      throw const DeviceProvisioningException('Wi-Fi 配置应用失败');
    }

    onProgress?.call('等待设备连接 Wi-Fi');
    final status = await _waitForWifiConnected(prov);
    return DeviceProvisioningResult(deviceIp: status.deviceIp);
  }

  Future<void> _sendDeviceConfig(
    ProvSecurity security,
    DeviceProvisioningRequest request,
  ) async {
    _debugProvisioningLog(
      'device-config request => ${jsonEncode(request.toDeviceConfigJson())}',
    );
    final requestBytes = Uint8List.fromList(
      utf8.encode(jsonEncode(request.toDeviceConfigJson())),
    );
    final encrypted = await security.encrypt(requestBytes);
    late final Uint8List rawResponse;
    try {
      rawResponse = await _transport
          .sendReceive('device-config', encrypted)
          .timeout(const Duration(seconds: 20));
    } catch (error) {
      _debugProvisioningLog('device-config error => $error');
      rethrow;
    }
    if (rawResponse.isEmpty) {
      throw const DeviceProvisioningException('设备配置没有返回结果');
    }

    final decrypted = await security.decrypt(rawResponse);
    _debugProvisioningLog(
      'device-config raw response => ${_printableDeviceConfigResponse(utf8.decode(decrypted, allowMalformed: true))}',
    );
    final decoded = decodeDeviceConfigResponse(decrypted);
    _debugProvisioningLog('device-config decoded response => $decoded');

    if (decoded['ok'] == true) {
      return;
    }

    final error = decoded['error']?.toString();
    throw DeviceProvisioningException(_deviceConfigErrorMessage(error));
  }

  Future<ConnectionStatus> _waitForWifiConnected(EspProv prov) async {
    final deadline = DateTime.now().add(statusTimeout);

    while (DateTime.now().isBefore(deadline)) {
      late final ConnectionStatus status;
      try {
        status = await prov.getStatus().timeout(const Duration(seconds: 10));
        _debugProvisioningLog(
          'getStatus => state=${status.state}, failedReason=${status.failedReason}, deviceIp=${status.deviceIp}',
        );
      } catch (error) {
        _debugProvisioningLog('getStatus error => $error');
        if (!await _transport.checkConnect()) {
          onProgress?.call('设备已退出配网模式');
          return ConnectionStatus(state: WifiConnectionState.Connected);
        }
        rethrow;
      }

      switch (status.state) {
        case WifiConnectionState.Connected:
          return status;
        case WifiConnectionState.ConnectionFailed:
          throw DeviceProvisioningException(
            _wifiFailureMessage(status.failedReason),
          );
        case WifiConnectionState.Connecting:
        case WifiConnectionState.Disconnected:
          await Future<void>.delayed(statusPollInterval);
      }
    }

    throw const DeviceProvisioningException('等待 Wi-Fi 连接超时');
  }

  String _wifiFailureMessage(WifiConnectFailedReason? reason) {
    return switch (reason) {
      WifiConnectFailedReason.AuthError => 'Wi-Fi 密码错误',
      WifiConnectFailedReason.NetworkNotFound => '没有找到 Wi-Fi 网络',
      _ => 'Wi-Fi 连接失败',
    };
  }

  String _deviceConfigErrorMessage(String? error) {
    return switch (error) {
      'invalid_json' => '上传参数格式错误',
      'invalid_op' => '设备配置操作不支持',
      'invalid_device_id' => '设备 ID 无效',
      'invalid_upload_url' => '上传地址无效',
      'invalid_image_profile' => '图片档位无效',
      'storage_failed' => '设备保存配置失败',
      'not_ready' => '设备尚未准备好',
      _ => error == null || error.isEmpty ? '上传参数写入失败' : error,
    };
  }
}

void _debugProvisioningLog(String message) {
  // ignore: avoid_print
  print('[DeviceProvisioning] $message');
}

Map<String, dynamic> decodeDeviceConfigResponse(Uint8List data) {
  final rawText = utf8.decode(data, allowMalformed: true);
  final normalized = _normalizeDeviceConfigJson(rawText);

  try {
    final decoded = jsonDecode(normalized);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
  } on FormatException {
    // Fall through to the contextual error below.
  }

  throw DeviceProvisioningException(
    '设备配置返回不是有效 JSON：${_printableDeviceConfigResponse(rawText)}',
  );
}

String _normalizeDeviceConfigJson(String rawText) {
  final text = rawText.replaceAll('\u0000', '').trim();
  final objectStart = text.indexOf('{');
  final objectEnd = text.lastIndexOf('}');

  if (objectStart >= 0 && objectEnd >= objectStart) {
    return text.substring(objectStart, objectEnd + 1);
  }

  if (text.startsWith('(') && text.endsWith('}')) {
    return '{${text.substring(1)}';
  }

  return text;
}

String _printableDeviceConfigResponse(String rawText) {
  return rawText
      .replaceAll('\u0000', r'\0')
      .replaceAll('\r', r'\r')
      .replaceAll('\n', r'\n');
}

class ReactiveBleProvTransport implements ProvTransport {
  ReactiveBleProvTransport({
    required ble.FlutterReactiveBle ble,
    required String deviceId,
    required ble.Uuid serviceUuid,
    required bool Function() isConnected,
    this.timeout = const Duration(seconds: 12),
    Map<String, int>? endpointIds,
  })  : _ble = ble,
        _deviceId = deviceId,
        _serviceUuid = serviceUuid.expanded,
        _isConnected = isConnected,
        _endpointIds = {
          ...defaultEndpointIds,
          if (endpointIds != null) ...endpointIds,
        };

  static const Map<String, int> defaultEndpointIds = {
    'prov-scan': 0xff50,
    'prov-session': 0xff51,
    'prov-config': 0xff52,
    'proto-ver': 0xff53,
    'custom-data': 0xff54,
    'device-config': 0xff54,
  };

  final ble.FlutterReactiveBle _ble;
  final String _deviceId;
  final ble.Uuid _serviceUuid;
  final bool Function() _isConnected;
  final Duration timeout;
  final Map<String, int> _endpointIds;

  bool _prepared = false;

  @override
  Future<bool> connect() async {
    if (!await checkConnect()) {
      return false;
    }

    try {
      await _ble.requestMtu(deviceId: _deviceId, mtu: 256).timeout(timeout);
    } catch (_) {
      // MTU negotiation is best-effort; provisioning still works with smaller packets.
    }

    await _ble.discoverAllServices(_deviceId).timeout(timeout);
    _prepared = true;
    return true;
  }

  @override
  Future<bool> checkConnect() async => _isConnected();

  @override
  Future<bool> disconnect() async {
    _prepared = false;
    return true;
  }

  @override
  Future<Uint8List> sendReceive(String epName, Uint8List data) async {
    if (!await checkConnect()) {
      throw const DeviceProvisioningException('设备连接已断开');
    }

    if (!_prepared) {
      final connected = await connect();
      if (!connected) {
        throw const DeviceProvisioningException('设备连接已断开');
      }
    }

    final characteristic = ble.QualifiedCharacteristic(
      characteristicId: characteristicUuidForEndpoint(epName),
      serviceId: _serviceUuid,
      deviceId: _deviceId,
    );

    if (data.isNotEmpty) {
      await _ble
          .writeCharacteristicWithResponse(characteristic, value: data)
          .timeout(timeout);
    }

    final response = await _ble.readCharacteristic(characteristic).timeout(
          timeout,
        );
    return Uint8List.fromList(response);
  }

  ble.Uuid characteristicUuidForEndpoint(String endpointName) {
    final endpointId = _endpointIds[endpointName];
    if (endpointId == null) {
      throw DeviceProvisioningException('未知设备端点：$endpointName');
    }

    return endpointUuid(_serviceUuid, endpointId);
  }

  static ble.Uuid endpointUuid(ble.Uuid serviceUuid, int endpointId) {
    final bytes = List<int>.from(serviceUuid.expanded.data);
    if (bytes.length != 16) {
      throw const DeviceProvisioningException('Service UUID 格式错误');
    }

    bytes[2] = (endpointId >> 8) & 0xff;
    bytes[3] = endpointId & 0xff;
    return ble.Uuid(bytes);
  }
}
