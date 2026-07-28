import 'package:flutter/material.dart';
import 'package:flutter_math_fork/flutter_math.dart';

/// Renders plain text mixed with TeX fragments.
///
/// Supported delimiters:
/// - `$...$` for inline math
/// - `$$...$$` for display math
class MathRichText extends StatelessWidget {
  const MathRichText({
    super.key,
    required this.text,
    this.style,
    this.textAlign = TextAlign.start,
    this.maxLines,
    this.overflow = TextOverflow.clip,
    this.softWrap = true,
  });

  final String text;
  final TextStyle? style;
  final TextAlign textAlign;
  final int? maxLines;
  final TextOverflow overflow;
  final bool softWrap;

  @override
  Widget build(BuildContext context) {
    final effectiveStyle = DefaultTextStyle.of(context).style.merge(style);
    final segments = _parseMathSegments(text);

    if (!segments.any((segment) => segment.isDisplayMath)) {
      return _InlineMathText(
        segments: segments,
        style: effectiveStyle,
        textAlign: textAlign,
        maxLines: maxLines,
        overflow: overflow,
        softWrap: softWrap,
      );
    }

    final children = <Widget>[];
    final inlineBuffer = <_MathSegment>[];

    void flushInline() {
      if (inlineBuffer.isEmpty) {
        return;
      }
      children.add(
        _InlineMathText(
          segments: List<_MathSegment>.of(inlineBuffer),
          style: effectiveStyle,
          textAlign: textAlign,
          maxLines: maxLines,
          overflow: overflow,
          softWrap: softWrap,
        ),
      );
      inlineBuffer.clear();
    }

    for (final segment in segments) {
      if (!segment.isDisplayMath) {
        inlineBuffer.add(segment);
        continue;
      }

      flushInline();
      children.add(
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Math.tex(
              segment.value,
              mathStyle: MathStyle.display,
              textStyle: effectiveStyle,
              onErrorFallback: (_) => Text(
                '\$\$${segment.value}\$\$',
                style: effectiveStyle,
              ),
            ),
          ),
        ),
      );
    }

    flushInline();

    return Column(
      crossAxisAlignment: _crossAxisAlignmentFor(textAlign),
      children: children,
    );
  }
}

class _InlineMathText extends StatelessWidget {
  const _InlineMathText({
    required this.segments,
    required this.style,
    required this.textAlign,
    required this.maxLines,
    required this.overflow,
    required this.softWrap,
  });

  final List<_MathSegment> segments;
  final TextStyle style;
  final TextAlign textAlign;
  final int? maxLines;
  final TextOverflow overflow;
  final bool softWrap;

  @override
  Widget build(BuildContext context) {
    return RichText(
      textAlign: textAlign,
      maxLines: maxLines,
      overflow: overflow,
      softWrap: softWrap,
      text: TextSpan(
        style: style,
        children: segments.map((segment) {
          if (!segment.isMath) {
            return TextSpan(text: segment.value);
          }

          final raw = '\$${segment.value}\$';
          return WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: Math.tex(
              segment.value,
              mathStyle: MathStyle.text,
              textStyle: style,
              onErrorFallback: (_) => Text(raw, style: style),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _MathSegment {
  const _MathSegment.text(this.value)
      : isMath = false,
        isDisplayMath = false;

  const _MathSegment.math(this.value, {required this.isDisplayMath})
      : isMath = true;

  final String value;
  final bool isMath;
  final bool isDisplayMath;
}

List<_MathSegment> _parseMathSegments(String input) {
  final segments = <_MathSegment>[];
  final textBuffer = StringBuffer();
  var index = 0;

  void flushText() {
    if (textBuffer.isEmpty) {
      return;
    }
    segments.add(_MathSegment.text(_normalizePlainText(textBuffer.toString())));
    textBuffer.clear();
  }

  while (index < input.length) {
    final char = input[index];
    if (char != r'$' || _isEscaped(input, index)) {
      textBuffer.write(char);
      index += 1;
      continue;
    }

    final isDisplay = index + 1 < input.length && input[index + 1] == r'$';
    final delimiterLength = isDisplay ? 2 : 1;
    final closeIndex = _findClosingDelimiter(
      input,
      index + delimiterLength,
      delimiterLength,
    );

    if (closeIndex == -1) {
      textBuffer.write(char);
      index += 1;
      continue;
    }

    final expression = input.substring(index + delimiterLength, closeIndex);
    if (expression.trim().isEmpty) {
      textBuffer.write(input.substring(index, closeIndex + delimiterLength));
      index = closeIndex + delimiterLength;
      continue;
    }

    flushText();
    segments.add(_MathSegment.math(
      expression.trim(),
      isDisplayMath: isDisplay,
    ));
    index = closeIndex + delimiterLength;
  }

  flushText();
  return segments.isEmpty ? [_MathSegment.text(input)] : segments;
}

int _findClosingDelimiter(String input, int start, int delimiterLength) {
  var index = start;
  while (index < input.length) {
    if (_isEscaped(input, index) || input[index] != r'$') {
      index += 1;
      continue;
    }

    if (delimiterLength == 1) {
      return index;
    }

    if (index + 1 < input.length && input[index + 1] == r'$') {
      return index;
    }
    index += 1;
  }
  return -1;
}

bool _isEscaped(String input, int index) {
  var slashCount = 0;
  var cursor = index - 1;
  while (cursor >= 0 && input[cursor] == r'\') {
    slashCount += 1;
    cursor -= 1;
  }
  return slashCount.isOdd;
}

String _normalizePlainText(String value) {
  return value.replaceAll(r'\$', r'$');
}

CrossAxisAlignment _crossAxisAlignmentFor(TextAlign textAlign) {
  switch (textAlign) {
    case TextAlign.center:
      return CrossAxisAlignment.center;
    case TextAlign.right:
    case TextAlign.end:
      return CrossAxisAlignment.end;
    case TextAlign.left:
    case TextAlign.start:
    case TextAlign.justify:
      return CrossAxisAlignment.start;
  }
}
