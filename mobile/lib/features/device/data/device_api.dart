import 'dart:typed_data';

import '../../../core/network/api_client.dart';

class DeviceApi {
  DeviceApi({ApiClient? client}) : _client = client ?? ApiClient();

  final ApiClient _client;

  Future<DeviceBindResponse> bindDevice({bool forceNew = false}) async {
    final payload = await _client.postJson(
      '/api/device/bind',
      {'force_new': forceNew},
    );
    return DeviceBindResponse.fromJson(payload);
  }

  Future<DeviceBindingResponse> getBinding() async {
    final payload = await _client.getJson('/api/device/binding');
    return DeviceBindingResponse.fromJson(payload);
  }

  Future<DeviceImagesResponse> getImages({
    String? deviceUuid,
    String? deviceId,
    int limit = 50,
  }) async {
    final query = <String, String>{
      if (deviceUuid != null && deviceUuid.trim().isNotEmpty)
        'device_uuid': deviceUuid.trim(),
      if (deviceId != null && deviceId.trim().isNotEmpty)
        'device_id': deviceId.trim(),
      'limit': limit.clamp(1, 200).toString(),
    };
    final path = Uri(
      path: '/api/device/images',
      queryParameters: query,
    ).toString();
    final payload = await _client.getJson(path);
    return DeviceImagesResponse.fromJson(payload);
  }

  Future<Uint8List> loadImageBytes(String imageUrl) {
    return _client.getBytes(imageUrl);
  }

  Future<DeviceActionResponse> unbindDevice(String deviceUuid) async {
    final payload = await _client.postJson(
      '/api/device/unbind',
      {'device_uuid': deviceUuid},
    );
    return DeviceActionResponse.fromJson(payload);
  }
}

class DeviceBindResponse {
  const DeviceBindResponse({
    required this.success,
    required this.deviceUuid,
    required this.qrPayload,
  });

  final bool success;
  final String deviceUuid;
  final String qrPayload;

  factory DeviceBindResponse.fromJson(Map<String, dynamic> json) {
    return DeviceBindResponse(
      success: json['success'] as bool? ?? false,
      deviceUuid: json['device_uuid']?.toString() ?? '',
      qrPayload: json['qr_payload']?.toString() ?? '',
    );
  }
}

class DeviceBindingResponse {
  const DeviceBindingResponse({
    required this.success,
    required this.bound,
    this.deviceUuid,
    this.qrPayload,
  });

  final bool success;
  final bool bound;
  final String? deviceUuid;
  final String? qrPayload;

  factory DeviceBindingResponse.fromJson(Map<String, dynamic> json) {
    return DeviceBindingResponse(
      success: json['success'] as bool? ?? false,
      bound: json['bound'] as bool? ?? false,
      deviceUuid: json['device_uuid']?.toString(),
      qrPayload: json['qr_payload']?.toString(),
    );
  }
}

class DeviceActionResponse {
  const DeviceActionResponse({
    required this.success,
    this.message,
  });

  final bool success;
  final String? message;

  factory DeviceActionResponse.fromJson(Map<String, dynamic> json) {
    return DeviceActionResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString(),
    );
  }
}

class DeviceImagesResponse {
  const DeviceImagesResponse({
    required this.success,
    required this.images,
  });

  final bool success;
  final List<DeviceCapture> images;

  factory DeviceImagesResponse.fromJson(Map<String, dynamic> json) {
    final rawImages = json['images'];
    return DeviceImagesResponse(
      success: json['success'] as bool? ?? false,
      images: rawImages is List
          ? rawImages
              .whereType<Map<String, dynamic>>()
              .map(DeviceCapture.fromJson)
              .toList(growable: false)
          : const [],
    );
  }
}

class DeviceCapture {
  const DeviceCapture({
    this.id,
    this.deviceUuid,
    this.fileKey,
    this.filename,
    this.imageUrl,
    this.contentType,
    this.fileSize,
    this.createdAt,
  });

  final int? id;
  final String? deviceUuid;
  final String? fileKey;
  final String? filename;
  final String? imageUrl;
  final String? contentType;
  final int? fileSize;
  final DateTime? createdAt;

  factory DeviceCapture.fromJson(Map<String, dynamic> json) {
    return DeviceCapture(
      id: _readInt(json['id']),
      deviceUuid: json['device_uuid']?.toString(),
      fileKey: json['file_key']?.toString(),
      filename: json['filename']?.toString(),
      imageUrl: json['image_url']?.toString(),
      contentType: json['content_type']?.toString(),
      fileSize: _readInt(json['file_size']),
      createdAt: _readDateTime(json['created_at']),
    );
  }

  String get displayName {
    final value = filename?.trim();
    if (value != null && value.isNotEmpty) {
      return value;
    }

    final key = fileKey?.trim();
    if (key != null && key.isNotEmpty) {
      return key.split(RegExp(r'[\\/]+')).last;
    }

    return 'capture.jpg';
  }
}

int? _readInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '');
}

DateTime? _readDateTime(Object? value) {
  final text = value?.toString().trim();
  if (text == null || text.isEmpty) {
    return null;
  }
  return DateTime.tryParse(text);
}
