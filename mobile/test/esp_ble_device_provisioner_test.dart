import 'dart:typed_data';

import 'package:error_log_app/features/device/data/esp_ble_device_provisioner.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('device-config 只包含上传参数，不包含 Wi-Fi 凭据', () {
    const request = DeviceProvisioningRequest(
      deviceId: '550e8400-e29b-41d4-a716-446655440000',
      wifiSsid: 'classroom',
      wifiPassword: 'secret',
      uploadUrl: 'http://10.1.86.71:5001',
      imageProfile: 'medium',
    );

    expect(request.toDeviceConfigJson(), {
      'op': 'set',
      'device_id': '550e8400-e29b-41d4-a716-446655440000',
      'upload_url': 'http://10.1.86.71:5001',
      'image_profile': 'medium',
    });
  });

  test('device-config 校验接受协议允许的字段', () {
    const request = DeviceProvisioningRequest(
      deviceId: '550E8400-E29B-41D4-A716-446655440000',
      wifiSsid: 'classroom',
      wifiPassword: 'secret',
      uploadUrl: 'https://lamp.dianchuang.club/api/device/capture',
      imageProfile: 'high',
    );

    expect(request.validateDeviceConfig, returnsNormally);
  });

  test('device-config 校验拒绝无效 device_id', () {
    const request = DeviceProvisioningRequest(
      deviceId: 'not-a-uuid',
      wifiSsid: 'classroom',
      wifiPassword: 'secret',
      uploadUrl: 'https://lamp.dianchuang.club/api/device/capture',
      imageProfile: 'medium',
    );

    expect(
      request.validateDeviceConfig,
      throwsA(isA<DeviceProvisioningException>()),
    );
  });

  test('device-config 校验拒绝包含空格或过长的 upload_url', () {
    final tooLongUrl = 'https://example.com/${'a' * 237}';

    expect(isValidDeviceUploadUrl('https://example.com/upload'), isTrue);
    expect(isValidDeviceUploadUrl('https://example.com/u pload'), isFalse);
    expect(isValidDeviceUploadUrl(tooLongUrl), isFalse);
  });

  test('device-config 校验拒绝协议外 image_profile', () {
    const request = DeviceProvisioningRequest(
      deviceId: '550e8400-e29b-41d4-a716-446655440000',
      wifiSsid: 'classroom',
      wifiPassword: 'secret',
      uploadUrl: 'https://lamp.dianchuang.club/api/device/capture',
      imageProfile: 'ultra',
    );

    expect(
      request.validateDeviceConfig,
      throwsA(isA<DeviceProvisioningException>()),
    );
  });

  test('device-config 返回可兼容固件 null terminator', () {
    final decoded = decodeDeviceConfigResponse(
      Uint8List.fromList('{"ok":true}\u0000'.codeUnits),
    );

    expect(decoded, {'ok': true});
  });

  test('device-config 返回可截取 JSON 对象', () {
    final decoded = decodeDeviceConfigResponse(
      Uint8List.fromList('noise{"ok":true}\u0000tail'.codeUnits),
    );

    expect(decoded, {'ok': true});
  });

  test('device-config 返回可兼容左括号误写', () {
    final decoded = decodeDeviceConfigResponse(
      Uint8List.fromList('("ok":true}'.codeUnits),
    );

    expect(decoded, {'ok': true});
  });

  test('按 Espressif protocomm 规则从 service UUID 推导 endpoint UUID', () {
    final serviceUuid = Uuid.parse('2f1f6e62-8ef5-43a4-9fa6-d7dbf8605e58');

    expect(
      ReactiveBleProvTransport.endpointUuid(serviceUuid, 0xff51).toString(),
      '2f1fff51-8ef5-43a4-9fa6-d7dbf8605e58',
    );
    expect(
      ReactiveBleProvTransport.endpointUuid(serviceUuid, 0xff54).toString(),
      '2f1fff54-8ef5-43a4-9fa6-d7dbf8605e58',
    );
  });
}
