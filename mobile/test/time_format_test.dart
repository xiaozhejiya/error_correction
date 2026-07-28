import 'package:error_log_app/core/utils/time_format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('后端无时区时间按 UTC 解析，避免本地显示早 8 小时', () {
    final parsed = parseBackendDateTime('2026-05-31T07:28:05.564490');

    expect(parsed?.toUtc(), DateTime.utc(2026, 5, 31, 7, 28, 5, 564, 490));
  });

  test('后端显式时区时间保留原时区语义', () {
    final parsed = parseBackendDateTime('2026-05-31T07:28:05+08:00');

    expect(parsed?.toUtc(), DateTime.utc(2026, 5, 30, 23, 28, 5));
  });

  test('相对时间使用统一文案', () {
    final text = formatRelativeTime(DateTime.now());

    expect(text, '刚刚更新');
  });
}
