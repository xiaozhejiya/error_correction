import 'dart:typed_data';

import '../../../core/network/api_client.dart';
import 'package:http/http.dart' as http;

class AuthApi {
  AuthApi({ApiClient? client}) : _client = client ?? ApiClient();

  final ApiClient _client;

  Future<bool> hasStoredSession() {
    return _client.hasSession();
  }

  Future<void> sendCode({
    required String email,
    String type = 'register',
  }) async {
    await _client.postJson(
      '/api/auth/send-code',
      {'email': email, 'type': type},
    );
  }

  Future<AuthUser> register({
    required String email,
    required String username,
    required String password,
    required String code,
  }) async {
    final payload = await _client.postJson(
      '/api/auth/register',
      {
        'email': email,
        'username': username,
        'password': password,
        'code': code,
      },
      successCodes: const {201},
    );

    return AuthUser.fromJson(payload['user'] as Map<String, dynamic>);
  }

  Future<AuthUser> login({
    required String identifier,
    required String password,
  }) async {
    final payload = await _client.postJson(
      '/api/auth/login',
      {'identifier': identifier, 'password': password},
    );

    return AuthUser.fromJson(payload['user'] as Map<String, dynamic>);
  }

  Future<AuthUser> me() async {
    final payload = await _client.getJson('/api/auth/me');

    return AuthUser.fromJson(payload['user'] as Map<String, dynamic>);
  }

  Future<void> logout() async {
    await _client.postJson('/api/auth/logout', {});
    await _client.clearSession();
  }

  Future<AuthActionResponse> updateProfile({
    String? displayName,
    String? nickname,
    String? email,
    String? code,
  }) async {
    final body = <String, dynamic>{
      if (displayName != null) 'display_name': displayName,
      if (nickname != null) 'nickname': nickname,
      if (email != null) 'email': email,
      if (code != null) 'code': code,
    };

    final payload = await _client.patchJson('/api/auth/profile', body);
    return AuthActionResponse.fromJson(payload, fallbackMessage: '资料已更新');
  }

  Future<AuthActionResponse> uploadAvatar({
    required String filename,
    required List<int> bytes,
  }) async {
    final payload = await _client.postMultipart(
      '/api/auth/profile/avatar',
      fields: const {},
      files: [
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      ],
    );

    return AuthActionResponse.fromJson(payload, fallbackMessage: '头像已上传');
  }

  Future<AuthActionResponse> deleteAvatar() async {
    final payload = await _client.deleteJson('/api/auth/profile/avatar');
    return AuthActionResponse.fromJson(payload, fallbackMessage: '头像已删除');
  }

  Future<Uint8List> loadProtectedImage(String url) {
    return _client.getBytes(url);
  }

  Future<void> clearStoredSession() {
    return _client.clearSession();
  }
}

class AuthActionResponse {
  const AuthActionResponse({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;

  factory AuthActionResponse.fromJson(
    Map<String, dynamic> json, {
    required String fallbackMessage,
  }) {
    return AuthActionResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString() ?? fallbackMessage,
    );
  }
}

class AuthUser {
  const AuthUser({
    required this.id,
    required this.email,
    required this.username,
    required this.isAdmin,
    this.displayName,
    this.nickname,
    this.avatarUrl,
    this.quota = const {},
  });

  final int id;
  final String email;
  final String username;
  final bool isAdmin;
  final String? displayName;
  final String? nickname;
  final String? avatarUrl;
  final Map<String, dynamic> quota;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as int,
      email: json['email'] as String,
      username: json['username'] as String,
      isAdmin: json['is_admin'] as bool? ?? false,
      displayName: json['display_name'] as String?,
      nickname: json['nickname'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      quota: (json['quota'] as Map?)?.cast<String, dynamic>() ?? const {},
    );
  }
}
