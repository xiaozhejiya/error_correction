import 'package:flutter/material.dart';
import 'package:flutter_math_fork/flutter_math.dart';

import '../../app/theme/app_theme.dart';

typedef MarkdownImageBuilder = Widget Function(
  BuildContext context,
  String alt,
  String url,
);

class MarkdownMathText extends StatelessWidget {
  const MarkdownMathText({
    super.key,
    required this.text,
    required this.palette,
    this.style,
    this.imageBuilder,
  });

  final String text;
  final AppThemePalette palette;
  final TextStyle? style;
  final MarkdownImageBuilder? imageBuilder;

  @override
  Widget build(BuildContext context) {
    final effectiveStyle = DefaultTextStyle.of(context).style.merge(style);
    final renderer = _MarkdownRenderer(
      text: text,
      palette: palette,
      style: effectiveStyle,
      imageBuilder: imageBuilder,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: renderer.buildBlocks(context),
    );
  }
}

class _MarkdownRenderer {
  _MarkdownRenderer({
    required this.text,
    required this.palette,
    required this.style,
    required this.imageBuilder,
  });

  final String text;
  final AppThemePalette palette;
  final TextStyle style;
  final MarkdownImageBuilder? imageBuilder;

  List<Widget> buildBlocks(BuildContext context) {
    final normalized = text.replaceAll('\r\n', '\n');
    final lines = normalized.split('\n');
    final children = <Widget>[];
    var index = 0;

    while (index < lines.length) {
      final rawLine = lines[index].trimRight();
      final trimmed = rawLine.trim();

      if (trimmed.isEmpty) {
        children.add(const SizedBox(height: 8));
        index += 1;
        continue;
      }

      if (trimmed.startsWith('```')) {
        final codeLines = <String>[];
        index += 1;
        while (index < lines.length &&
            !lines[index].trimLeft().startsWith('```')) {
          codeLines.add(lines[index]);
          index += 1;
        }
        if (index < lines.length) {
          index += 1;
        }
        children.add(_buildCodeBlock(codeLines.join('\n')));
        continue;
      }

      if (_startsDisplayMath(trimmed)) {
        final result = _collectDisplayMath(lines, index);
        children.add(_buildDisplayMath(result.expression));
        index = result.nextIndex;
        continue;
      }

      if (_isHorizontalRule(trimmed)) {
        children.add(
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Divider(height: 1, color: palette.divider),
          ),
        );
        index += 1;
        continue;
      }

      if (_isHtmlTableStart(trimmed)) {
        final result = _collectHtmlTable(lines, index);
        children.add(_buildTable(context, result.rows));
        index = result.nextIndex;
        continue;
      }

      if (_isTableStart(lines, index)) {
        final result = _collectTable(lines, index);
        children.add(_buildTable(context, result.rows));
        index = result.nextIndex;
        continue;
      }

      final imageMatch = _imageMatch(trimmed);
      if (imageMatch != null) {
        children.add(_buildImage(
          context,
          imageMatch.alt,
          imageMatch.url,
        ));
        index += 1;
        continue;
      }

      if (trimmed.startsWith('>')) {
        final quoteLines = <String>[];
        while (
            index < lines.length && lines[index].trimLeft().startsWith('>')) {
          quoteLines.add(
            lines[index].trimLeft().replaceFirst(RegExp(r'^>\s?'), ''),
          );
          index += 1;
        }
        children.add(_buildQuote(quoteLines.join('\n')));
        continue;
      }

      final headingLevel = _headingLevel(trimmed);
      if (headingLevel > 0) {
        children.add(_buildHeading(
            trimmed.substring(headingLevel).trim(), headingLevel));
        index += 1;
        continue;
      }

      final listMatch = _listMatch(trimmed);
      if (listMatch != null) {
        children.add(_buildListItem(listMatch.marker, listMatch.content));
        index += 1;
        continue;
      }

      final paragraphLines = <String>[rawLine.trim()];
      index += 1;
      while (index < lines.length && !_isBlockBoundary(lines, index)) {
        paragraphLines.add(lines[index].trim());
        index += 1;
      }
      children.add(_buildParagraph(paragraphLines.join(' ')));
    }

    return children;
  }

  Widget _buildParagraph(String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: _InlineMarkdownMathText(
        text: value,
        style: style,
        palette: palette,
      ),
    );
  }

  Widget _buildHeading(String value, int level) {
    final size = switch (level) {
      1 => 22.0,
      2 => 19.0,
      3 => 17.0,
      _ => 15.5,
    };
    return Padding(
      padding: const EdgeInsets.only(top: 12, bottom: 6),
      child: _InlineMarkdownMathText(
        text: value,
        style: style.copyWith(
          fontSize: size,
          fontWeight: FontWeight.w900,
          height: 1.35,
        ),
        palette: palette,
      ),
    );
  }

  Widget _buildListItem(String marker, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 28,
            child: Text(
              marker,
              style: style.copyWith(
                color: palette.textSub,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          Expanded(
            child: _InlineMarkdownMathText(
              text: value,
              style: style,
              palette: palette,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuote(String value) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: palette.primary.withOpacity(0.08),
        border: Border(
          left: BorderSide(color: palette.primary, width: 3),
        ),
      ),
      child: MarkdownMathText(
        text: value,
        style: style.copyWith(
          color: palette.textSub,
          fontWeight: FontWeight.w700,
        ),
        palette: palette,
        imageBuilder: imageBuilder,
      ),
    );
  }

  Widget _buildImage(BuildContext context, String alt, String url) {
    final builder = imageBuilder;
    if (builder != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: builder(context, alt, url),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(
        alt.trim().isEmpty ? url : alt,
        style: style.copyWith(
          color: palette.primaryLight,
          decoration: TextDecoration.underline,
          decorationColor: palette.primaryLight,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _buildCodeBlock(String value) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: palette.panelBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: palette.panelBorder),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: SelectableText(
          value,
          style: style.copyWith(
            fontFamily: 'monospace',
            color: palette.textMain,
            fontWeight: FontWeight.w600,
            height: 1.55,
          ),
        ),
      ),
    );
  }

  Widget _buildDisplayMath(String expression) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
      decoration: BoxDecoration(
        color: palette.panelBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: palette.panelBorder),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Math.tex(
          expression.trim(),
          mathStyle: MathStyle.display,
          textStyle: style,
          onErrorFallback: (_) => Text(
            '\$\$${expression.trim()}\$\$',
            style: style,
          ),
        ),
      ),
    );
  }

  Widget _buildTable(BuildContext context, List<List<_TableCell>> rows) {
    if (rows.isEmpty) {
      return const SizedBox.shrink();
    }

    final maxColumns = rows.fold<int>(
      0,
      (max, row) => row.length > max ? row.length : max,
    );

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        border: Border.all(color: palette.panelBorder),
        borderRadius: BorderRadius.circular(10),
      ),
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Table(
          defaultColumnWidth: const IntrinsicColumnWidth(),
          border: TableBorder(
            horizontalInside: BorderSide(color: palette.panelBorder),
            verticalInside: BorderSide(color: palette.panelBorder),
          ),
          children: rows.asMap().entries.map((entry) {
            final rowIndex = entry.key;
            final row = entry.value;
            return TableRow(
              decoration: BoxDecoration(
                color: rowIndex == 0 ? palette.subtleOverlay : null,
              ),
              children: List.generate(maxColumns, (columnIndex) {
                final value = columnIndex < row.length
                    ? row[columnIndex]
                    : const _TableCell('');
                return Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 180),
                    child: _buildTableCell(
                      context,
                      value,
                      style.copyWith(
                        fontWeight:
                            rowIndex == 0 ? FontWeight.w900 : style.fontWeight,
                      ),
                    ),
                  ),
                );
              }),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildTableCell(
    BuildContext context,
    _TableCell cell,
    TextStyle cellStyle,
  ) {
    if (!cell.isHtml) {
      return _InlineMarkdownMathText(
        text: cell.value,
        style: cellStyle,
        palette: palette,
      );
    }

    final segments = _parseHtmlCellSegments(cell.value);
    if (segments.length == 1 && segments.single.imageUrl == null) {
      return _InlineMarkdownMathText(
        text: segments.single.text ?? '',
        style: cellStyle,
        palette: palette,
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: segments.map((segment) {
        final imageUrl = segment.imageUrl;
        if (imageUrl != null) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: _buildImage(
              context,
              segment.alt ?? 'Image',
              imageUrl,
            ),
          );
        }

        final text = segment.text?.trim();
        if (text == null || text.isEmpty) {
          return const SizedBox.shrink();
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: _InlineMarkdownMathText(
            text: text,
            style: cellStyle,
            palette: palette,
          ),
        );
      }).toList(growable: false),
    );
  }

  bool _isBlockBoundary(List<String> lines, int index) {
    final trimmed = lines[index].trim();
    return trimmed.isEmpty ||
        trimmed.startsWith('```') ||
        _startsDisplayMath(trimmed) ||
        _isHorizontalRule(trimmed) ||
        _isHtmlTableStart(trimmed) ||
        _isTableStart(lines, index) ||
        _imageMatch(trimmed) != null ||
        trimmed.startsWith('>') ||
        _headingLevel(trimmed) > 0 ||
        _listMatch(trimmed) != null;
  }

  bool _isHorizontalRule(String line) {
    return RegExp(r'^ {0,3}([-*_])(?:\s*\1){2,}\s*$').hasMatch(line);
  }

  bool _startsDisplayMath(String line) {
    return line.startsWith(r'$$') || line.startsWith(r'\[');
  }

  bool _isHtmlTableStart(String line) {
    return RegExp(r'<table[\s>]', caseSensitive: false).hasMatch(line);
  }

  _ImageMatch? _imageMatch(String line) {
    final match =
        RegExp(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$').firstMatch(line.trim());
    if (match == null) {
      return null;
    }
    return _ImageMatch(match.group(1) ?? '', match.group(2) ?? '');
  }

  _DisplayMathResult _collectDisplayMath(List<String> lines, int startIndex) {
    final first = lines[startIndex].trim();

    if (first.startsWith(r'\[')) {
      final sameLineEnd = first.indexOf(r'\]', 2);
      if (sameLineEnd != -1) {
        return _DisplayMathResult(
            first.substring(2, sameLineEnd), startIndex + 1);
      }
      final buffer = StringBuffer(first.substring(2));
      var index = startIndex + 1;
      while (index < lines.length) {
        final line = lines[index];
        final closeIndex = line.indexOf(r'\]');
        if (closeIndex != -1) {
          buffer
            ..write('\n')
            ..write(line.substring(0, closeIndex));
          return _DisplayMathResult(buffer.toString(), index + 1);
        }
        buffer
          ..write('\n')
          ..write(line);
        index += 1;
      }
      return _DisplayMathResult(buffer.toString(), index);
    }

    final sameLineClose = first.indexOf(r'$$', 2);
    if (sameLineClose != -1) {
      return _DisplayMathResult(
          first.substring(2, sameLineClose), startIndex + 1);
    }

    final buffer = StringBuffer(first.substring(2));
    var index = startIndex + 1;
    while (index < lines.length) {
      final line = lines[index];
      final closeIndex = line.indexOf(r'$$');
      if (closeIndex != -1) {
        buffer
          ..write('\n')
          ..write(line.substring(0, closeIndex));
        return _DisplayMathResult(buffer.toString(), index + 1);
      }
      buffer
        ..write('\n')
        ..write(line);
      index += 1;
    }
    return _DisplayMathResult(buffer.toString(), index);
  }

  bool _isTableStart(List<String> lines, int index) {
    if (index + 1 >= lines.length) {
      return false;
    }
    final current = lines[index].trim();
    final next = lines[index + 1].trim();
    return current.contains('|') &&
        RegExp(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$').hasMatch(next);
  }

  _TableResult _collectTable(List<String> lines, int startIndex) {
    final rows = <List<_TableCell>>[_splitTableRow(lines[startIndex])];
    var index = startIndex + 2;
    while (index < lines.length && lines[index].trim().contains('|')) {
      rows.add(_splitTableRow(lines[index]));
      index += 1;
    }
    return _TableResult(rows, index);
  }

  _TableResult _collectHtmlTable(List<String> lines, int startIndex) {
    final buffer = StringBuffer(lines[startIndex].trim());
    var index = startIndex + 1;
    while (index < lines.length &&
        !RegExp(r'</table>', caseSensitive: false)
            .hasMatch(buffer.toString())) {
      buffer.write(lines[index].trim());
      index += 1;
    }
    return _TableResult(_parseHtmlTableRows(buffer.toString()), index);
  }

  List<List<_TableCell>> _parseHtmlTableRows(String html) {
    final rows = <List<_TableCell>>[];
    final rowPattern = RegExp(
      r'<tr[^>]*>(.*?)</tr>',
      caseSensitive: false,
      dotAll: true,
    );
    final cellPattern = RegExp(
      r'<t[dh][^>]*>(.*?)</t[dh]>',
      caseSensitive: false,
      dotAll: true,
    );

    for (final rowMatch in rowPattern.allMatches(html)) {
      final rowHtml = rowMatch.group(1) ?? '';
      final cells = cellPattern
          .allMatches(rowHtml)
          .map((cell) => _TableCell(cell.group(1) ?? '', isHtml: true))
          .toList();
      if (cells.isNotEmpty) {
        rows.add(cells);
      }
    }

    return rows;
  }

  List<_TableCell> _splitTableRow(String line) {
    var value = line.trim();
    if (value.startsWith('|')) {
      value = value.substring(1);
    }
    if (value.endsWith('|')) {
      value = value.substring(0, value.length - 1);
    }
    return value.split('|').map((cell) => _TableCell(cell.trim())).toList();
  }

  int _headingLevel(String line) {
    var count = 0;
    while (count < line.length && line[count] == '#') {
      count += 1;
    }
    if (count > 0 && count <= 6 && count < line.length && line[count] == ' ') {
      return count;
    }
    return 0;
  }

  _ListMatch? _listMatch(String line) {
    final task = RegExp(r'^[-*+]\s+\[([ xX])\]\s+(.+)$').firstMatch(line);
    if (task != null) {
      final checked = task.group(1)!.trim().isNotEmpty;
      return _ListMatch(checked ? '☑' : '☐', task.group(2)!.trim());
    }

    final unordered = RegExp(r'^[-*+]\s+(.+)$').firstMatch(line);
    if (unordered != null) {
      return _ListMatch('•', unordered.group(1)!.trim());
    }

    final ordered = RegExp(r'^(\d+)[.)]\s+(.+)$').firstMatch(line);
    if (ordered != null) {
      return _ListMatch('${ordered.group(1)!}.', ordered.group(2)!.trim());
    }

    return null;
  }
}

class _InlineMarkdownMathText extends StatelessWidget {
  const _InlineMarkdownMathText({
    required this.text,
    required this.style,
    required this.palette,
  });

  final String text;
  final TextStyle style;
  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        style: style,
        children: _parseInline(text, style, palette),
      ),
    );
  }
}

List<InlineSpan> _parseInline(
  String input,
  TextStyle style,
  AppThemePalette palette,
) {
  final spans = <InlineSpan>[];
  final buffer = StringBuffer();
  var index = 0;

  void flushText() {
    if (buffer.isEmpty) {
      return;
    }
    spans.add(TextSpan(text: _normalizeInlineText(buffer.toString())));
    buffer.clear();
  }

  while (index < input.length) {
    if (_startsWithUnescaped(input, index, r'$')) {
      final closeIndex = _findClosingDelimiter(input, index + 1, r'$');
      if (closeIndex != -1) {
        final expression = input.substring(index + 1, closeIndex).trim();
        if (expression.isNotEmpty) {
          flushText();
          spans.add(
            WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: Math.tex(
                expression,
                mathStyle: MathStyle.text,
                textStyle: style,
                onErrorFallback: (_) => Text('\$$expression\$', style: style),
              ),
            ),
          );
          index = closeIndex + 1;
          continue;
        }
      }
    }

    if (_startsWithUnescaped(input, index, '`')) {
      final closeIndex = _findClosingDelimiter(input, index + 1, '`');
      if (closeIndex != -1) {
        flushText();
        spans.add(
          WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: palette.subtleOverlay,
                borderRadius: BorderRadius.circular(5),
              ),
              child: Text(
                input.substring(index + 1, closeIndex),
                style: style.copyWith(
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        );
        index = closeIndex + 1;
        continue;
      }
    }

    final boldDelimiter = _startsWithUnescaped(input, index, '**')
        ? '**'
        : _startsWithUnescaped(input, index, '__')
            ? '__'
            : null;
    if (boldDelimiter != null) {
      final closeIndex = _findClosingDelimiter(
        input,
        index + boldDelimiter.length,
        boldDelimiter,
      );
      if (closeIndex != -1) {
        flushText();
        spans.add(
          TextSpan(
            children: _parseInline(
              input.substring(index + boldDelimiter.length, closeIndex),
              style.copyWith(fontWeight: FontWeight.w900),
              palette,
            ),
          ),
        );
        index = closeIndex + boldDelimiter.length;
        continue;
      }
    }

    final italicDelimiter = _startsWithUnescaped(input, index, '*')
        ? '*'
        : _startsWithUnescaped(input, index, '_')
            ? '_'
            : null;
    if (italicDelimiter != null) {
      final closeIndex = _findClosingDelimiter(
        input,
        index + 1,
        italicDelimiter,
      );
      if (closeIndex != -1) {
        flushText();
        spans.add(
          TextSpan(
            style: const TextStyle(fontStyle: FontStyle.italic),
            children: _parseInline(
              input.substring(index + 1, closeIndex),
              style.copyWith(fontStyle: FontStyle.italic),
              palette,
            ),
          ),
        );
        index = closeIndex + 1;
        continue;
      }
    }

    if (_startsWithUnescaped(input, index, '[')) {
      final labelEnd = _findClosingDelimiter(input, index + 1, ']');
      if (labelEnd != -1 &&
          labelEnd + 1 < input.length &&
          input[labelEnd + 1] == '(') {
        final urlEnd = _findClosingDelimiter(input, labelEnd + 2, ')');
        if (urlEnd != -1) {
          flushText();
          spans.add(
            TextSpan(
              style: TextStyle(
                color: palette.primaryLight,
                decoration: TextDecoration.underline,
                decorationColor: palette.primaryLight,
                fontWeight: FontWeight.w800,
              ),
              children: _parseInline(
                input.substring(index + 1, labelEnd),
                style.copyWith(color: palette.primaryLight),
                palette,
              ),
            ),
          );
          index = urlEnd + 1;
          continue;
        }
      }
    }

    if (_startsWithUnescaped(input, index, r'\')) {
      if (index + 1 < input.length) {
        buffer.write(input[index + 1]);
        index += 2;
        continue;
      }
    }

    buffer.write(input[index]);
    index += 1;
  }

  flushText();
  return spans;
}

bool _startsWithUnescaped(String input, int index, String value) {
  return input.startsWith(value, index) && !_isEscaped(input, index);
}

int _findClosingDelimiter(String input, int start, String delimiter) {
  var index = start;
  while (index < input.length) {
    if (_startsWithUnescaped(input, index, delimiter)) {
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

String _normalizeInlineText(String value) {
  return value.replaceAll(r'\$', r'$');
}

class _DisplayMathResult {
  const _DisplayMathResult(this.expression, this.nextIndex);

  final String expression;
  final int nextIndex;
}

class _TableResult {
  const _TableResult(this.rows, this.nextIndex);

  final List<List<_TableCell>> rows;
  final int nextIndex;
}

class _TableCell {
  const _TableCell(this.value, {this.isHtml = false});

  final String value;
  final bool isHtml;
}

class _TableCellSegment {
  const _TableCellSegment.text(this.text)
      : imageUrl = null,
        alt = null;

  const _TableCellSegment.image(this.imageUrl, this.alt) : text = null;

  final String? text;
  final String? imageUrl;
  final String? alt;
}

List<_TableCellSegment> _parseHtmlCellSegments(String value) {
  final segments = <_TableCellSegment>[];
  final imagePattern = RegExp(
    r'<img\b[^>]*>',
    caseSensitive: false,
    dotAll: true,
  );
  var cursor = 0;

  void addText(String raw) {
    final text = _htmlCellText(raw);
    if (text.isNotEmpty) {
      segments.add(_TableCellSegment.text(text));
    }
  }

  for (final match in imagePattern.allMatches(value)) {
    addText(value.substring(cursor, match.start));
    final imageTag = match.group(0) ?? '';
    final src = _readHtmlAttribute(imageTag, 'src');
    if (src != null && src.trim().isNotEmpty) {
      segments.add(
        _TableCellSegment.image(
          _decodeHtmlEntities(src.trim()),
          _decodeHtmlEntities(_readHtmlAttribute(imageTag, 'alt') ?? 'Image'),
        ),
      );
    }
    cursor = match.end;
  }

  addText(value.substring(cursor));
  return segments.isEmpty ? const [_TableCellSegment.text('')] : segments;
}

String? _readHtmlAttribute(String tag, String name) {
  final quoted = RegExp(
    "$name\\s*=\\s*(['\"])(.*?)\\1",
    caseSensitive: false,
    dotAll: true,
  ).firstMatch(tag);
  if (quoted != null) {
    return quoted.group(2);
  }

  final unquoted = RegExp(
    '$name\\s*=\\s*([^\\s>]+)',
    caseSensitive: false,
    dotAll: true,
  ).firstMatch(tag);
  return unquoted?.group(1);
}

String _htmlCellText(String value) {
  return _decodeHtmlEntities(
    value
        .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
        .replaceAll(RegExp(r'<[^>]+>'), '')
        .trim(),
  );
}

String _decodeHtmlEntities(String value) {
  return value
      .replaceAll('&nbsp;', ' ')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&amp;', '&')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'")
      .replaceAll('&apos;', "'");
}

class _ListMatch {
  const _ListMatch(this.marker, this.content);

  final String marker;
  final String content;
}

class _ImageMatch {
  const _ImageMatch(this.alt, this.url);

  final String alt;
  final String url;
}
