import 'dart:typed_data';

import 'package:flutter/material.dart';

class ProtectedImage extends StatefulWidget {
  const ProtectedImage({
    super.key,
    required this.url,
    required this.loadBytes,
    this.fit = BoxFit.cover,
    this.loading,
    this.error,
  });

  final String url;
  final Future<Uint8List> Function(String url) loadBytes;
  final BoxFit fit;
  final Widget? loading;
  final Widget? error;

  @override
  State<ProtectedImage> createState() => _ProtectedImageState();
}

class _ProtectedImageState extends State<ProtectedImage> {
  late Future<Uint8List> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.loadBytes(widget.url);
  }

  @override
  void didUpdateWidget(covariant ProtectedImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.url != widget.url ||
        oldWidget.loadBytes != widget.loadBytes) {
      _future = widget.loadBytes(widget.url);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Uint8List>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          return Image.memory(
            snapshot.data!,
            fit: widget.fit,
            gaplessPlayback: true,
          );
        }
        if (snapshot.hasError) {
          return widget.error ?? const SizedBox.shrink();
        }
        return widget.loading ?? const SizedBox.shrink();
      },
    );
  }
}
