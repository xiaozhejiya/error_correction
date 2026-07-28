import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  ApiClient({
    String? baseUrl,
    http.Client? httpClient,
  })  : baseUrl = baseUrl ?? defaultBaseUrl,
        _httpClient = httpClient ?? http.Client();

  static const defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://lamp.dianchuang.club',
  );
  static const sessionCookieKey = 'auth_session_cookie';

  final String baseUrl;
  final http.Client _httpClient;

  Future<Map<String, dynamic>> getJson(
    String path, {
    Set<int> successCodes = const {200},
  }) {
    return _sendJson(
      method: 'GET',
      path: path,
      successCodes: successCodes,
    );
  }

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body, {
    Set<int> successCodes = const {200},
  }) {
    return _sendJson(
      method: 'POST',
      path: path,
      body: body,
      successCodes: successCodes,
    );
  }

  Future<Map<String, dynamic>> patchJson(
    String path,
    Map<String, dynamic> body, {
    Set<int> successCodes = const {200},
  }) {
    return _sendJson(
      method: 'PATCH',
      path: path,
      body: body,
      successCodes: successCodes,
    );
  }

  Future<Map<String, dynamic>> deleteJson(
    String path, {
    Map<String, dynamic>? body,
    Set<int> successCodes = const {200},
  }) {
    return _sendJson(
      method: 'DELETE',
      path: path,
      body: body,
      successCodes: successCodes,
    );
  }

  Future<Map<String, dynamic>> postMultipart(
    String path, {
    required Map<String, String> fields,
    required List<http.MultipartFile> files,
    Set<int> successCodes = const {200},
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final prefs = await SharedPreferences.getInstance();
    final sessionCookie = prefs.getString(sessionCookieKey);
    final request = http.MultipartRequest('POST', uri)
      ..fields.addAll(fields)
      ..files.addAll(files);
    request.headers.addAll({
      'Accept': 'application/json',
      if (sessionCookie != null && sessionCookie.isNotEmpty)
        'Cookie': sessionCookie,
    });

    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);

    await _saveSessionCookie(response.headers['set-cookie']);
    final payload = _decodeBody(response);

    if (!successCodes.contains(response.statusCode)) {
      throw ApiException(
        statusCode: response.statusCode,
        message: _errorMessage(payload, response.statusCode),
        payload: payload,
      );
    }

    return payload;
  }

  Stream<String> postEventStream(
    String path,
    Map<String, dynamic> body, {
    Set<int> successCodes = const {200},
  }) async* {
    final uri = Uri.parse('$baseUrl$path');
    final prefs = await SharedPreferences.getInstance();
    final sessionCookie = prefs.getString(sessionCookieKey);
    final request = http.Request('POST', uri)
      ..headers.addAll({
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json',
        if (sessionCookie != null && sessionCookie.isNotEmpty)
          'Cookie': sessionCookie,
      })
      ..body = jsonEncode(body);

    final response = await _httpClient.send(request);

    await _saveSessionCookie(response.headers['set-cookie']);

    if (!successCodes.contains(response.statusCode)) {
      final bodyBytes = await response.stream.toBytes();
      final payload = _decodeBytesPayload(bodyBytes);
      throw ApiException(
        statusCode: response.statusCode,
        message: _errorMessage(payload, response.statusCode),
        payload: payload,
      );
    }

    yield* response.stream.transform(utf8.decoder);
  }

  Future<Uint8List> getBytes(
    String pathOrUrl, {
    Set<int> successCodes = const {200},
  }) async {
    final uri = Uri.parse(
      pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')
          ? pathOrUrl
          : '$baseUrl$pathOrUrl',
    );
    final prefs = await SharedPreferences.getInstance();
    final sessionCookie = prefs.getString(sessionCookieKey);
    final response = await _httpClient.get(
      uri,
      headers: {
        'Accept': 'image/*,*/*',
        if (sessionCookie != null && sessionCookie.isNotEmpty)
          'Cookie': sessionCookie,
      },
    );

    await _saveSessionCookie(response.headers['set-cookie']);

    if (!successCodes.contains(response.statusCode)) {
      throw ApiException(
        statusCode: response.statusCode,
        message: _bytesErrorMessage(response),
      );
    }

    return response.bodyBytes;
  }

  Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(sessionCookieKey);
  }

  Future<bool> hasSession() async {
    final prefs = await SharedPreferences.getInstance();
    final sessionCookie = prefs.getString(sessionCookieKey);

    return sessionCookie != null && sessionCookie.isNotEmpty;
  }

  Future<Map<String, dynamic>> _sendJson({
    required String method,
    required String path,
    required Set<int> successCodes,
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final prefs = await SharedPreferences.getInstance();
    final sessionCookie = prefs.getString(sessionCookieKey);
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      if (sessionCookie != null && sessionCookie.isNotEmpty)
        'Cookie': sessionCookie,
    };

    final requestBody = body == null ? null : jsonEncode(body);
    final response = switch (method) {
      'GET' => await _httpClient.get(uri, headers: headers),
      'POST' =>
        await _httpClient.post(uri, headers: headers, body: requestBody),
      'PATCH' =>
        await _httpClient.patch(uri, headers: headers, body: requestBody),
      'DELETE' =>
        await _httpClient.delete(uri, headers: headers, body: requestBody),
      _ => throw ArgumentError.value(method, 'method', 'Unsupported method'),
    };

    await _saveSessionCookie(response.headers['set-cookie']);
    final payload = _decodeBody(response);

    if (!successCodes.contains(response.statusCode)) {
      throw ApiException(
        statusCode: response.statusCode,
        message: _errorMessage(payload, response.statusCode),
        payload: payload,
      );
    }

    return payload;
  }

  Map<String, dynamic> _decodeBody(http.Response response) {
    final rawBody = utf8.decode(response.bodyBytes);
    if (rawBody.trim().isEmpty) {
      return {};
    }

    final decoded = jsonDecode(rawBody);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }

    return {'data': decoded};
  }

  Map<String, dynamic> _decodeBytesPayload(List<int> bodyBytes) {
    final rawBody = utf8.decode(bodyBytes);
    if (rawBody.trim().isEmpty) {
      return {};
    }

    final decoded = jsonDecode(rawBody);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }

    return {'data': decoded};
  }

  Future<void> _saveSessionCookie(String? setCookie) async {
    if (setCookie == null || setCookie.isEmpty) {
      return;
    }

    final match = RegExp(r'session=[^;,]+').firstMatch(setCookie);
    if (match == null) {
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(sessionCookieKey, match.group(0)!);
  }

  String _errorMessage(Map<String, dynamic> payload, int statusCode) {
    final error = payload['error'] ?? payload['message'];
    if (error is String && error.trim().isNotEmpty) {
      return error;
    }

    return '请求失败，请稍后再试 ($statusCode)';
  }

  String _bytesErrorMessage(http.Response response) {
    try {
      final rawBody = utf8.decode(response.bodyBytes);
      if (rawBody.trim().isNotEmpty) {
        final decoded = jsonDecode(rawBody);
        if (decoded is Map<String, dynamic>) {
          return _errorMessage(decoded, response.statusCode);
        }
      }
    } catch (_) {
      // Ignore non-JSON image error responses.
    }

    return '资源加载失败，请稍后再试 (${response.statusCode})';
  }
}

class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.message,
    this.payload = const {},
  });

  final int statusCode;
  final String message;
  final Map<String, dynamic> payload;

  @override
  String toString() => 'ApiException($statusCode): $message';
}
