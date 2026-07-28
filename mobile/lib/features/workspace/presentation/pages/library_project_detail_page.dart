import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/time_format.dart';
import '../../../../core/widgets/markdown_math_text.dart';
import '../../../../core/widgets/protected_image.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../data/workspace_api.dart';

class LibraryProjectDetailPage extends StatefulWidget {
  const LibraryProjectDetailPage({
    super.key,
    required this.project,
    this.workspaceApi,
  });

  final WorkspaceProject project;
  final WorkspaceApi? workspaceApi;

  @override
  State<LibraryProjectDetailPage> createState() =>
      _LibraryProjectDetailPageState();
}

class _LibraryProjectDetailPageState extends State<LibraryProjectDetailPage> {
  late final WorkspaceApi _workspaceApi;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final List<LibraryQuestionItem> _questions = [];
  final List<LibraryNoteItem> _notes = [];
  Timer? _searchDebounce;

  int _page = 1;
  int _total = 0;
  bool _hasMore = false;
  bool _isLoading = false;
  bool _isLoadingMore = false;
  String? _errorMessage;
  String _keyword = '';

  static const int _pageSize = 10;

  bool get _isQuestionProject => widget.project.isQuestionProject;

  @override
  void initState() {
    super.initState();
    _workspaceApi = widget.workspaceApi ?? WorkspaceApi();
    _scrollController.addListener(_onScroll);
    unawaited(_loadItems(reset: true));
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.extentAfter < 360 &&
        _hasMore &&
        !_isLoading &&
        !_isLoadingMore) {
      unawaited(_loadItems(reset: false));
    }
  }

  void _onSearchChanged(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      final keyword = value.trim();
      if (keyword == _keyword) {
        return;
      }
      _keyword = keyword;
      unawaited(_loadItems(reset: true));
    });
  }

  Future<void> _loadItems({required bool reset}) async {
    if (reset) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
        _page = 1;
        _hasMore = false;
        _total = 0;
        _questions.clear();
        _notes.clear();
      });
    } else {
      if (_isLoadingMore || !_hasMore) {
        return;
      }
      setState(() => _isLoadingMore = true);
    }

    final nextPage = reset ? 1 : _page + 1;

    try {
      if (_isQuestionProject) {
        final response = await _workspaceApi.queryErrorBank(
          page: nextPage,
          pageSize: _pageSize,
          keyword: _keyword,
          projectId: widget.project.id,
        );
        if (!mounted) {
          return;
        }
        setState(() {
          _page = response.page;
          _total = response.total;
          _hasMore = response.hasMore;
          if (reset) {
            _questions
              ..clear()
              ..addAll(response.items);
          } else {
            _questions.addAll(response.items);
          }
        });
      } else {
        final response = await _workspaceApi.queryNotes(
          page: nextPage,
          limit: _pageSize,
          keyword: _keyword,
          projectId: widget.project.id,
        );
        if (!mounted) {
          return;
        }
        setState(() {
          _page = response.page;
          _total = response.total;
          _hasMore = response.hasMore;
          if (reset) {
            _notes
              ..clear()
              ..addAll(response.items);
          } else {
            _notes.addAll(response.items);
          }
        });
      }
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _errorMessage = error.message);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isLoadingMore = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          child: Column(
            children: [
              _LibraryDetailHeader(
                palette: palette,
                project: widget.project,
                total: _total,
                onBack: () => Navigator.of(context).maybePop(),
                onRefresh: () => unawaited(_loadItems(reset: true)),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 10),
                child: _buildSearchBar(palette),
              ),
              Expanded(child: _buildBody(palette)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSearchBar(AppThemePalette palette) {
    return TextField(
      controller: _searchController,
      onChanged: (value) {
        setState(() {});
        _onSearchChanged(value);
      },
      style: TextStyle(color: palette.textMain, fontSize: 14),
      decoration: InputDecoration(
        isDense: true,
        hintText: _isQuestionProject ? '搜索题干、知识点' : '搜索笔记、知识点',
        hintStyle: TextStyle(color: palette.textSub),
        prefixIcon: Icon(Icons.search_rounded, color: palette.textSub),
        suffixIcon: _searchController.text.trim().isEmpty
            ? null
            : IconButton(
                tooltip: '清空',
                onPressed: () {
                  _searchController.clear();
                  _onSearchChanged('');
                  setState(() {});
                },
                icon: Icon(Icons.close_rounded, color: palette.textSub),
              ),
        filled: true,
        fillColor: palette.panel,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: palette.panelBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: palette.panelBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: palette.primary),
        ),
      ),
    );
  }

  Widget _buildBody(AppThemePalette palette) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }

    if (_errorMessage != null) {
      return _LibraryMessageState(
        palette: palette,
        icon: Icons.error_outline_rounded,
        title: '加载失败',
        message: _errorMessage!,
        actionText: '重试',
        onAction: () => unawaited(_loadItems(reset: true)),
      );
    }

    final itemCount = _isQuestionProject ? _questions.length : _notes.length;
    if (itemCount == 0) {
      return _LibraryMessageState(
        palette: palette,
        icon: _isQuestionProject
            ? Icons.storage_rounded
            : Icons.menu_book_rounded,
        title: _keyword.isEmpty ? '暂无内容' : '没有匹配结果',
        message: _keyword.isEmpty
            ? (_isQuestionProject ? '这个错题库还没有题目' : '这个笔记本还没有笔记')
            : '换个关键词再试试',
      );
    }

    return RefreshIndicator(
      color: palette.primary,
      onRefresh: () => _loadItems(reset: true),
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.fromLTRB(18, 2, 18, 24),
        itemCount: itemCount + (_hasMore || _isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= itemCount) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Center(
                child: _isLoadingMore
                    ? const CircularProgressIndicator(strokeWidth: 2)
                    : TextButton(
                        onPressed: () => unawaited(_loadItems(reset: false)),
                        child: const Text('加载更多'),
                      ),
              ),
            );
          }

          if (_isQuestionProject) {
            final question = _questions[index];
            return Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: _QuestionListTile(
                  question: question,
                  palette: palette,
                  onTap: () => _openQuestionDetail(question),
                ),
              ),
            );
          }

          final note = _notes[index];
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: _NoteListTile(
                note: note,
                palette: palette,
                onTap: () => _openNoteDetail(note),
              ),
            ),
          );
        },
      ),
    );
  }

  void _openQuestionDetail(LibraryQuestionItem question) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LibraryQuestionDetailPage(
          project: widget.project,
          question: question,
          workspaceApi: _workspaceApi,
        ),
      ),
    );
  }

  void _openNoteDetail(LibraryNoteItem note) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LibraryNoteDetailPage(
          project: widget.project,
          note: note,
          workspaceApi: _workspaceApi,
        ),
      ),
    );
  }
}

class LibraryQuestionDetailPage extends StatelessWidget {
  const LibraryQuestionDetailPage({
    super.key,
    required this.project,
    required this.question,
    required this.workspaceApi,
  });

  final WorkspaceProject project;
  final LibraryQuestionItem question;
  final WorkspaceApi workspaceApi;

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          child: Column(
            children: [
              _LibraryItemDetailHeader(
                palette: palette,
                icon: Icons.storage_rounded,
                title: project.displayName,
                meta: question.questionType.isEmpty
                    ? '错题详情'
                    : question.questionType,
                onBack: () => Navigator.of(context).maybePop(),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
                  children: [
                    Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 760),
                        child: _QuestionCard(
                          question: question,
                          palette: palette,
                          workspaceApi: workspaceApi,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LibraryNoteDetailPage extends StatelessWidget {
  const LibraryNoteDetailPage({
    super.key,
    required this.project,
    required this.note,
    required this.workspaceApi,
  });

  final WorkspaceProject project;
  final LibraryNoteItem note;
  final WorkspaceApi workspaceApi;

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          child: Column(
            children: [
              _LibraryItemDetailHeader(
                palette: palette,
                icon: Icons.menu_book_rounded,
                title: note.displayTitle,
                meta: project.displayName,
                onBack: () => Navigator.of(context).maybePop(),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
                  children: [
                    Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 760),
                        child: _NoteCard(
                          note: note,
                          palette: palette,
                          workspaceApi: workspaceApi,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LibraryItemDetailHeader extends StatelessWidget {
  const _LibraryItemDetailHeader({
    required this.palette,
    required this.icon,
    required this.title,
    required this.meta,
    required this.onBack,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String title;
  final String meta;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: palette.divider)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(4, 8, 16, 12),
        child: Row(
          children: [
            IconButton(
              tooltip: '返回',
              onPressed: onBack,
              icon: const Icon(Icons.arrow_back_ios_new_rounded),
              color: palette.textMain,
            ),
            Container(
              width: 42,
              height: 42,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: palette.primary.withOpacity(0.16),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: palette.primaryLight, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: palette.textMain,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 5),
                  _MetaChip(label: meta, palette: palette),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuestionListTile extends StatelessWidget {
  const _QuestionListTile({
    required this.question,
    required this.palette,
    required this.onTap,
  });

  final LibraryQuestionItem question;
  final AppThemePalette palette;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return _LibrarySummaryTile(
      palette: palette,
      title: question.questionType.isEmpty ? '错题' : question.questionType,
      preview: question.previewText,
      meta: [
        if (question.subject.isNotEmpty)
          _SummaryMetaItem.subject(question.subject),
        if (question.reviewStatus.isNotEmpty)
          _SummaryMetaItem.status(question.reviewStatus),
        if (question.knowledgeTags.isNotEmpty)
          _SummaryMetaItem.knowledge(question.knowledgeTags.first),
        _SummaryMetaItem.time(formatRelativeTime(
          question.updatedAt ?? question.createdAt,
        )),
      ],
      highlighted: question.needsCorrection || question.reviewIsDue,
      onTap: onTap,
    );
  }
}

class _NoteListTile extends StatelessWidget {
  const _NoteListTile({
    required this.note,
    required this.palette,
    required this.onTap,
  });

  final LibraryNoteItem note;
  final AppThemePalette palette;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return _LibrarySummaryTile(
      palette: palette,
      title: note.displayTitle,
      preview: note.summary.trim().isEmpty ? note.previewText : note.summary,
      meta: [
        if (note.subject.isNotEmpty) _SummaryMetaItem.subject(note.subject),
        if (note.reviewStatus.isNotEmpty)
          _SummaryMetaItem.status(note.reviewStatus),
        if (note.knowledgeTags.isNotEmpty)
          _SummaryMetaItem.knowledge(note.knowledgeTags.first),
        _SummaryMetaItem.time(formatRelativeTime(
          note.updatedAt ?? note.createdAt,
        )),
      ],
      highlighted: false,
      onTap: onTap,
    );
  }
}

class _LibrarySummaryTile extends StatelessWidget {
  const _LibrarySummaryTile({
    required this.palette,
    required this.title,
    required this.preview,
    required this.meta,
    required this.highlighted,
    required this.onTap,
    this.countLabel,
  });

  final AppThemePalette palette;
  final String title;
  final String preview;
  final List<_SummaryMetaItem> meta;
  final bool highlighted;
  final VoidCallback onTap;
  final String? countLabel;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
          decoration: BoxDecoration(
            color: palette.cardBg,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 15,
                        height: 1.2,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _compactPreview(preview),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: palette.textSub,
                        fontSize: 12,
                        height: 1.45,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 7,
                      runSpacing: 7,
                      children: meta
                          .where((item) => item.label.trim().isNotEmpty)
                          .take(4)
                          .map(
                            (item) => _SummaryMetaChip(
                              item: item,
                              palette: palette,
                              highlighted: highlighted,
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ],
                ),
              ),
              if (countLabel != null && countLabel!.isNotEmpty) ...[
                const SizedBox(width: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: palette.primary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    countLabel!,
                    style: TextStyle(
                      color: palette.primaryLight,
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
              const SizedBox(width: 4),
              Icon(
                Icons.chevron_right_rounded,
                color: palette.textSub,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

enum _SummaryMetaKind { subject, knowledge, status, time }

class _SummaryMetaItem {
  const _SummaryMetaItem._(this.kind, this.label);

  factory _SummaryMetaItem.subject(String label) {
    return _SummaryMetaItem._(_SummaryMetaKind.subject, label);
  }

  factory _SummaryMetaItem.knowledge(String label) {
    return _SummaryMetaItem._(_SummaryMetaKind.knowledge, label);
  }

  factory _SummaryMetaItem.status(String label) {
    return _SummaryMetaItem._(_SummaryMetaKind.status, label);
  }

  factory _SummaryMetaItem.time(String label) {
    return _SummaryMetaItem._(_SummaryMetaKind.time, label);
  }

  final _SummaryMetaKind kind;
  final String label;
}

class _SummaryMetaChip extends StatelessWidget {
  const _SummaryMetaChip({
    required this.item,
    required this.palette,
    required this.highlighted,
  });

  final _SummaryMetaItem item;
  final AppThemePalette palette;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    final tone = _tone();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: tone.$1,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.$2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(tone.$4, size: 12, color: tone.$3),
          const SizedBox(width: 4),
          Text(
            item.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: tone.$3,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  (Color, Color, Color, IconData) _tone() {
    return switch (item.kind) {
      _SummaryMetaKind.subject => (
          palette.primary.withOpacity(0.14),
          palette.primary.withOpacity(0.12),
          palette.primaryLight,
          Icons.school_rounded,
        ),
      _SummaryMetaKind.knowledge => (
          palette.isLight
              ? const Color(0xFFE8ECF8)
              : Colors.white.withOpacity(0.08),
          palette.panelBorder,
          palette.textSub,
          Icons.sell_rounded,
        ),
      _SummaryMetaKind.status => _statusTone(),
      _SummaryMetaKind.time => (
          palette.badgeBg,
          palette.panelBorder,
          palette.textSub.withOpacity(0.82),
          Icons.schedule_rounded,
        ),
    };
  }

  (Color, Color, Color, IconData) _statusTone() {
    final color = _ReviewStatusTone.fromStatus(item.label).color;
    return (
      color.withOpacity(palette.isLight ? 0.12 : 0.18),
      color.withOpacity(0.22),
      color,
      highlighted ? Icons.priority_high_rounded : Icons.flag_rounded,
    );
  }
}

String _compactPreview(String value) {
  final text = value
      .replaceAll(RegExp(r'```[\s\S]*?```'), ' ')
      .replaceAll(RegExp(r'!\[[^\]]*\]\([^)]+\)'), ' ')
      .replaceAllMapped(RegExp(r'\[([^\]]+)\]\([^)]+\)'), (match) {
        return match.group(1) ?? '';
      })
      .replaceAllMapped(RegExp(r'`([^`]*)`'), (match) {
        return match.group(1) ?? '';
      })
      .replaceAll(RegExp(r'<[^>]+>'), ' ')
      .replaceAll(RegExp(r'#{1,6}\s*'), ' ')
      .replaceAll(r'\parallel', '∥')
      .replaceAll(RegExp(r'\$\$?'), ' ')
      .replaceAll(RegExp(r'[*_~>]'), '')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
  return text.isEmpty ? '暂无内容' : text;
}

class _LibraryDetailHeader extends StatelessWidget {
  const _LibraryDetailHeader({
    required this.palette,
    required this.project,
    required this.total,
    required this.onBack,
    required this.onRefresh,
  });

  final AppThemePalette palette;
  final WorkspaceProject project;
  final int total;
  final VoidCallback onBack;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final isQuestion = project.isQuestionProject;
    final typeLabel = isQuestion ? '错题库' : '笔记本';
    final icon = isQuestion ? Icons.storage_rounded : Icons.menu_book_rounded;

    return Row(
      children: [
        IconButton(
          tooltip: '返回',
          onPressed: onBack,
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          color: palette.textMain,
        ),
        Container(
          width: 42,
          height: 42,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: palette.primary.withOpacity(0.16),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: palette.primaryLight, size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                project.displayName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: palette.textMain,
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  _MetaChip(label: typeLabel, palette: palette),
                  _MetaChip(label: '$total 条内容', palette: palette),
                ],
              ),
            ],
          ),
        ),
        IconButton(
          tooltip: '刷新',
          onPressed: onRefresh,
          icon: const Icon(Icons.refresh_rounded),
          color: palette.textSub,
        ),
      ],
    );
  }
}

class _QuestionCard extends StatelessWidget {
  const _QuestionCard({
    required this.question,
    required this.palette,
    required this.workspaceApi,
  });

  final LibraryQuestionItem question;
  final AppThemePalette palette;
  final WorkspaceApi workspaceApi;

  @override
  Widget build(BuildContext context) {
    final embeddedImages = _embeddedImageUrls(question.previewText);
    final images = _imageUrls([
      ...question.contentBlocks
          .where((block) => block.isImage)
          .map((block) => block.content),
      ...question.imageRefs,
    ], excluded: embeddedImages);

    return _LibraryCard(
      palette: palette,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildMeta(),
          const SizedBox(height: 14),
          MarkdownMathText(
            text: question.previewText,
            palette: palette,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 15,
              height: 1.55,
              fontWeight: FontWeight.w700,
            ),
            imageBuilder: (context, alt, url) => _MarkdownProtectedImage(
              url: url,
              alt: alt,
              palette: palette,
              workspaceApi: workspaceApi,
            ),
          ),
          if (images.isNotEmpty) ...[
            const SizedBox(height: 12),
            _ImageStrip(
              title: '关联原图',
              urls: images,
              palette: palette,
              workspaceApi: workspaceApi,
            ),
          ],
          if (question.options.isNotEmpty) ...[
            const SizedBox(height: 14),
            _OptionsGrid(options: question.options, palette: palette),
          ],
          if (_hasValue(question.answer) || _hasValue(question.userAnswer)) ...[
            const SizedBox(height: 12),
            Divider(color: palette.panelBorder),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (_hasValue(question.answer))
                  _MetaChip(label: '答案 ${question.answer}', palette: palette),
                if (_hasValue(question.userAnswer))
                  _MetaChip(
                    label: '我的答案 ${question.userAnswer}',
                    palette: palette,
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMeta() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        if (question.questionType.isNotEmpty)
          _MetaChip(label: question.questionType, palette: palette),
        if (question.subject.isNotEmpty)
          _MetaChip(label: question.subject, palette: palette),
        if (question.reviewStatus.isNotEmpty)
          _ReviewStatusChip(status: question.reviewStatus, palette: palette),
        if (question.needsCorrection)
          _MetaChip(label: '需校对', palette: palette, highlighted: true),
        if (question.reviewCount > 0)
          _MetaChip(label: '复习 ${question.reviewCount} 次', palette: palette),
        if (question.reviewIntervalDays > 0)
          _MetaChip(
            label: '${question.reviewIntervalDays} 天间隔',
            palette: palette,
          ),
        ...question.knowledgeTags.take(4).map(
              (tag) => _MetaChip(
                label: tag,
                palette: palette,
                highlighted: true,
              ),
            ),
      ],
    );
  }
}

class _NoteCard extends StatelessWidget {
  const _NoteCard({
    required this.note,
    required this.palette,
    required this.workspaceApi,
  });

  final LibraryNoteItem note;
  final AppThemePalette palette;
  final WorkspaceApi workspaceApi;

  @override
  Widget build(BuildContext context) {
    final embeddedImages = _embeddedImageUrls(note.previewText);
    final images = _imageUrls([
      ...note.contentBlocks.where((block) => block.isImage).map(
            (block) => block.content,
          ),
      ...note.imageRefs,
    ], excluded: embeddedImages);

    return _LibraryCard(
      palette: palette,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (note.subject.isNotEmpty)
                _MetaChip(label: note.subject, palette: palette),
              if (note.reviewStatus.isNotEmpty)
                _ReviewStatusChip(status: note.reviewStatus, palette: palette),
              if (note.reviewCount > 0)
                _MetaChip(label: '复习 ${note.reviewCount} 次', palette: palette),
              if (note.reviewIntervalDays > 0)
                _MetaChip(
                  label: '${note.reviewIntervalDays} 天间隔',
                  palette: palette,
                ),
              ...note.knowledgeTags.take(4).map(
                    (tag) => _MetaChip(
                      label: tag,
                      palette: palette,
                      highlighted: true,
                    ),
                  ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            note.displayTitle,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 16,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          MarkdownMathText(
            text: note.previewText,
            palette: palette,
            style: TextStyle(
              color: palette.textMain.withOpacity(0.9),
              fontSize: 14,
              height: 1.55,
              fontWeight: FontWeight.w600,
            ),
            imageBuilder: (context, alt, url) => _MarkdownProtectedImage(
              url: url,
              alt: alt,
              palette: palette,
              workspaceApi: workspaceApi,
            ),
          ),
          if (images.isNotEmpty) ...[
            const SizedBox(height: 12),
            _ImageStrip(
              title: '来源图片',
              urls: images,
              palette: palette,
              workspaceApi: workspaceApi,
            ),
          ],
          const SizedBox(height: 10),
          Text(
            formatRelativeTime(note.updatedAt ?? note.createdAt),
            style: TextStyle(
              color: palette.textSub,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _OptionsGrid extends StatelessWidget {
  const _OptionsGrid({
    required this.options,
    required this.palette,
  });

  final List<String> options;
  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 10.0;
        final columns = constraints.maxWidth >= 680 ? 2 : 1;
        final width = (constraints.maxWidth - gap * (columns - 1)) / columns;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: options
              .map(
                (option) => SizedBox(
                  width: width,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: palette.panel,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: palette.panelBorder),
                    ),
                    child: MarkdownMathText(
                      text: option,
                      palette: palette,
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 13,
                        height: 1.45,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        );
      },
    );
  }
}

class _ImageStrip extends StatelessWidget {
  const _ImageStrip({
    required this.title,
    required this.urls,
    required this.palette,
    required this.workspaceApi,
  });

  final String title;
  final List<String> urls;
  final AppThemePalette palette;
  final WorkspaceApi workspaceApi;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: palette.panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.image_rounded,
                color: palette.primaryLight,
                size: 16,
              ),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  color: palette.textMain,
                  fontSize: 13,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(width: 8),
              _MetaChip(label: '${urls.length} 张', palette: palette),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: urls
                .map(
                  (url) => ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 400,
                      height: 300,
                      child: ProtectedImage(
                        url: _normaliseImageUrl(url),
                        loadBytes: workspaceApi.loadProtectedImage,
                        fit: BoxFit.cover,
                        loading: Center(
                          child: SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: palette.primary,
                            ),
                          ),
                        ),
                        error: Center(
                          child: Icon(
                            Icons.broken_image_rounded,
                            color: palette.textSub,
                          ),
                        ),
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _MarkdownProtectedImage extends StatelessWidget {
  const _MarkdownProtectedImage({
    required this.url,
    required this.alt,
    required this.palette,
    required this.workspaceApi,
  });

  final String url;
  final String alt;
  final AppThemePalette palette;
  final WorkspaceApi workspaceApi;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: const BoxConstraints(maxHeight: 260),
        width: double.infinity,
        child: ProtectedImage(
          url: _normaliseImageUrl(url),
          loadBytes: workspaceApi.loadProtectedImage,
          fit: BoxFit.contain,
          loading: SizedBox(
            height: 140,
            child: Center(
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: palette.primary,
                ),
              ),
            ),
          ),
          error: SizedBox(
            height: 92,
            child: Center(
              child: Text(
                alt.trim().isEmpty ? '图片加载失败' : alt.trim(),
                style: TextStyle(
                  color: palette.textSub,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LibraryCard extends StatelessWidget {
  const _LibraryCard({
    required this.palette,
    required this.child,
  });

  final AppThemePalette palette;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.panelBorder),
      ),
      child: child,
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.label,
    required this.palette,
    this.highlighted = false,
  });

  final String label;
  final AppThemePalette palette;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: highlighted ? palette.primary.withOpacity(0.18) : palette.chip,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: highlighted ? palette.primaryLight : palette.textSub,
          fontSize: 12,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _ReviewStatusChip extends StatelessWidget {
  const _ReviewStatusChip({
    required this.status,
    required this.palette,
  });

  final String status;
  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    final tone = _ReviewStatusTone.fromStatus(status);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: tone.color.withOpacity(palette.isLight ? 0.14 : 0.18),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.color.withOpacity(0.22)),
      ),
      child: Text(
        status,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: tone.color,
          fontSize: 12,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _ReviewStatusTone {
  const _ReviewStatusTone(this.color);

  final Color color;

  factory _ReviewStatusTone.fromStatus(String status) {
    if (status.contains('待复习')) {
      return const _ReviewStatusTone(Color(0xFFFFB020));
    }
    if (status.contains('复习中')) {
      return const _ReviewStatusTone(Color(0xFF58A6FF));
    }
    if (status.contains('已掌握')) {
      return const _ReviewStatusTone(Color(0xFF32D99C));
    }
    if (status.contains('逾期') || status.contains('需')) {
      return const _ReviewStatusTone(Color(0xFFFF6B6B));
    }
    return const _ReviewStatusTone(Color(0xFFA796FF));
  }
}

class _LibraryMessageState extends StatelessWidget {
  const _LibraryMessageState({
    required this.palette,
    required this.icon,
    required this.title,
    required this.message,
    this.actionText,
    this.onAction,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String title;
  final String message;
  final String? actionText;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: palette.textSub, size: 34),
            const SizedBox(height: 12),
            Text(
              title,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.textSub,
                fontWeight: FontWeight.w700,
              ),
            ),
            if (actionText != null && onAction != null) ...[
              const SizedBox(height: 14),
              ElevatedButton(
                onPressed: onAction,
                style: ElevatedButton.styleFrom(
                  backgroundColor: palette.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                ),
                child: Text(actionText!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

List<String> _imageUrls(
  Iterable<String> urls, {
  Set<String> excluded = const {},
}) {
  final seen = <String>{};
  final result = <String>[];
  for (final raw in urls) {
    final value = raw.trim();
    final normalized = _normaliseImageUrl(value);
    if (value.isEmpty ||
        seen.contains(normalized) ||
        excluded.contains(normalized)) {
      continue;
    }
    seen.add(normalized);
    result.add(value);
  }
  return result;
}

Set<String> _embeddedImageUrls(String content) {
  final urls = <String>{};
  final htmlImagePattern = RegExp(
    r"""<img\b[^>]*\bsrc\s*=\s*(['"])(.*?)\1""",
    caseSensitive: false,
    dotAll: true,
  );
  final markdownImagePattern = RegExp(r'!\[[^\]]*\]\(([^)]+)\)');

  for (final match in htmlImagePattern.allMatches(content)) {
    final value = match.group(2)?.trim();
    if (value != null && value.isNotEmpty) {
      urls.add(_normaliseImageUrl(value));
    }
  }
  for (final match in markdownImagePattern.allMatches(content)) {
    final value = match.group(1)?.trim();
    if (value != null && value.isNotEmpty) {
      urls.add(_normaliseImageUrl(value));
    }
  }
  return urls;
}

String _normaliseImageUrl(String url) {
  final value = url.trim();
  if (value.startsWith('http://') ||
      value.startsWith('https://') ||
      value.startsWith('/')) {
    return value;
  }
  if (value.contains('\\') || value.contains(':')) {
    final filename = value.split(RegExp(r'[\\/]+')).last;
    return filename.isEmpty ? value : '/api/image/$filename';
  }
  return '/$value';
}

bool _hasValue(String? value) => value != null && value.trim().isNotEmpty;
