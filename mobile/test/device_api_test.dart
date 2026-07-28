import 'dart:convert';

import 'package:error_log_app/core/network/api_client.dart';
import 'package:error_log_app/features/device/data/device_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });
  });

  test('创建设备绑定时发送 force_new 并携带 session cookie', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/device/bind');
        expect(request.headers['cookie'], 'session=abc123');
        expect(jsonDecode(request.body), {'force_new': false});

        return http.Response.bytes(
          utf8.encode(
            jsonEncode({
              'success': true,
              'device_uuid': '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
              'qr_payload':
                  'aiwb://bind?device_uuid=8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
            }),
          ),
          200,
        );
      }),
    );

    final api = DeviceApi(client: client);
    final response = await api.bindDevice();

    expect(response.success, isTrue);
    expect(response.deviceUuid, '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21');
  });

  test('可以请求强制生成新的设备 UUID', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(jsonDecode(request.body), {'force_new': true});

        return http.Response.bytes(
          utf8.encode(
            jsonEncode({
              'success': true,
              'device_uuid': 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb',
              'qr_payload':
                  'aiwb://bind?device_uuid=aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb',
            }),
          ),
          200,
        );
      }),
    );

    final api = DeviceApi(client: client);
    final response = await api.bindDevice(forceNew: true);

    expect(response.deviceUuid, 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb');
  });

  test('查询当前用户设备绑定状态', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/device/binding');
        expect(request.headers['cookie'], 'session=abc123');

        return http.Response.bytes(
          utf8.encode(
            jsonEncode({
              'success': true,
              'bound': true,
              'device_uuid': '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
              'qr_payload':
                  'aiwb://bind?device_uuid=8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
            }),
          ),
          200,
        );
      }),
    );

    final api = DeviceApi(client: client);
    final response = await api.getBinding();

    expect(response.success, isTrue);
    expect(response.bound, isTrue);
    expect(response.deviceUuid, '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21');
  });

  test('解绑当前用户设备时发送 device_uuid', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/device/unbind');
        expect(request.headers['cookie'], 'session=abc123');
        expect(jsonDecode(request.body), {
          'device_uuid': '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
        });

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': 'ok'})),
          200,
        );
      }),
    );

    final api = DeviceApi(client: client);
    final response = await api.unbindDevice(
      '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
    );

    expect(response.success, isTrue);
    expect(response.message, 'ok');
  });

  test('查询硬件上传图片列表', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/device/images');
        expect(
          request.url.queryParameters,
          {
            'device_uuid': '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
            'limit': '50',
          },
        );
        expect(request.headers['cookie'], 'session=abc123');

        return http.Response.bytes(
          utf8.encode(
            jsonEncode({
              'success': true,
              'images': [
                {
                  'id': 7,
                  'device_uuid': '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
                  'file_key': 'captures/capture.jpg',
                  'filename': 'capture.jpg',
                  'image_url': '/api/image/capture.jpg',
                  'content_type': 'image/jpeg',
                  'file_size': 2048,
                  'created_at': '2026-06-01T10:30:00Z',
                },
              ],
            }),
          ),
          200,
        );
      }),
    );

    final api = DeviceApi(client: client);
    final response = await api.getImages(
      deviceUuid: '8f4b8f6e-2c7a-4e3a-9c6a-4c1f2e7b9a21',
    );

    expect(response.success, isTrue);
    expect(response.images, hasLength(1));
    expect(response.images.single.displayName, 'capture.jpg');
    expect(response.images.single.imageUrl, '/api/image/capture.jpg');
    expect(response.images.single.fileSize, 2048);
  });
}
