import 'dart:convert';

import 'package:error_log_app/core/network/api_client.dart';
import 'package:error_log_app/features/auth/data/auth_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('登录成功后保存后端下发的 session cookie', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/auth/login');
        expect(
          jsonDecode(request.body),
          {'identifier': 'student@example.com', 'password': '123456'},
        );

        return http.Response(
          jsonEncode({
            'user': {
              'id': 1,
              'email': 'student@example.com',
              'username': 'student01',
              'is_admin': false,
              'quota': {},
            },
          }),
          200,
          headers: {'set-cookie': 'session=abc123; HttpOnly; Path=/'},
        );
      }),
    );

    final api = AuthApi(client: client);
    final user = await api.login(
      identifier: 'student@example.com',
      password: '123456',
    );
    final prefs = await SharedPreferences.getInstance();

    expect(user.email, 'student@example.com');
    expect(prefs.getString(ApiClient.sessionCookieKey), 'session=abc123');
  });

  test('注册使用后端要求的字段并返回用户', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/auth/register');
        expect(
          jsonDecode(request.body),
          {
            'email': 'student@example.com',
            'username': 'student01',
            'password': '123456',
            'code': '654321',
          },
        );

        return http.Response(
          jsonEncode({
            'success': true,
            'user': {
              'id': 2,
              'email': 'student@example.com',
              'username': 'student01',
              'is_admin': false,
              'quota': {},
            },
          }),
          201,
          headers: {'set-cookie': 'session=registered; Path=/'},
        );
      }),
    );

    final api = AuthApi(client: client);
    final user = await api.register(
      email: 'student@example.com',
      username: 'student01',
      password: '123456',
      code: '654321',
    );
    final prefs = await SharedPreferences.getInstance();

    expect(user.id, 2);
    expect(prefs.getString(ApiClient.sessionCookieKey), 'session=registered');
  });

  test('发送验证码失败时抛出后端错误信息', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': false, 'error': '邮箱格式错误'})),
          400,
        );
      }),
    );

    final api = AuthApi(client: client);

    expect(
      () => api.sendCode(email: 'bad-email', type: 'register'),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          '邮箱格式错误',
        ),
      ),
    );
  });

  test('可以判断本地是否已有 session cookie', () async {
    final client = ApiClient(baseUrl: 'http://server.test');

    expect(await client.hasSession(), isFalse);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ApiClient.sessionCookieKey, 'session=abc123');

    expect(await client.hasSession(), isTrue);
  });

  test('更新当前用户资料时发送 PATCH 请求并携带 session cookie', () async {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/api/auth/profile');
        expect(request.headers['cookie'], 'session=abc123');
        expect(
          jsonDecode(request.body),
          {
            'display_name': 'Admin',
            'nickname': '数学冲刺版',
          },
        );

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '更新成功'})),
          200,
        );
      }),
    );

    final api = AuthApi(client: client);
    final response = await api.updateProfile(
      displayName: 'Admin',
      nickname: '数学冲刺版',
    );

    expect(response.success, isTrue);
    expect(response.message, '更新成功');
  });

  test('上传头像时使用 multipart file 字段并携带 session cookie', () async {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/auth/profile/avatar');
        expect(request.headers['cookie'], 'session=abc123');
        expect(
            request.headers['content-type'], contains('multipart/form-data'));

        final bodyText = utf8.decode(request.bodyBytes, allowMalformed: true);
        expect(bodyText, contains('name="file"'));
        expect(bodyText, contains('avatar.png'));

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '上传成功'})),
          200,
        );
      }),
    );

    final api = AuthApi(client: client);
    final response = await api.uploadAvatar(
      filename: 'avatar.png',
      bytes: const [1, 2, 3],
    );

    expect(response.success, isTrue);
    expect(response.message, '上传成功');
  });

  test('删除头像时发送 DELETE 请求', () async {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/api/auth/profile/avatar');
        expect(request.headers['cookie'], 'session=abc123');

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '删除成功'})),
          200,
        );
      }),
    );

    final api = AuthApi(client: client);
    final response = await api.deleteAvatar();

    expect(response.success, isTrue);
    expect(response.message, '删除成功');
  });
}
