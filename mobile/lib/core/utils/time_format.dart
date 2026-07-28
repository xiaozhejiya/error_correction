DateTime? parseBackendDateTime(Object? value) {
  final text = value?.toString().trim();
  if (text == null || text.isEmpty || text == 'null') {
    return null;
  }

  final normalized = text.contains(' ') && !text.contains('T')
      ? text.replaceFirst(' ', 'T')
      : text;
  final hasClock =
      RegExp(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}').hasMatch(normalized);
  final hasTimeZone =
      RegExp(r'(?:[zZ]|[+-]\d{2}:?\d{2})$').hasMatch(normalized);
  final parseText = hasClock && !hasTimeZone ? '${normalized}Z' : normalized;

  return DateTime.tryParse(parseText)?.toLocal();
}

String formatRelativeTime(DateTime? time) {
  if (time == null) {
    return '暂无更新时间';
  }

  final local = time.toLocal();
  final diff = DateTime.now().difference(local);
  if (diff.inMinutes < 1) {
    return '刚刚更新';
  }
  if (diff.inHours < 1) {
    return '${diff.inMinutes} 分钟前';
  }
  if (diff.inDays < 1) {
    return '${diff.inHours} 小时前';
  }
  if (diff.inDays < 30) {
    return '${diff.inDays} 天前';
  }

  return '${local.month}月${local.day}日';
}
