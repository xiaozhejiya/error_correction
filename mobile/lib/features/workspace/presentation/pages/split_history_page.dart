import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../../core/widgets/markdown_math_text.dart';
import '../../../../core/widgets/protected_image.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../data/workspace_api.dart';
import '../../data/workspace_project_store.dart';

class SplitHistoryPage extends StatefulWidget {
  const SplitHistoryPage({
    super.key,
    this.workspaceApi,
  });

  final WorkspaceApi? workspaceApi;

  @override
  State<SplitHistoryPage> createState() => _SplitHistoryPageState();
}

class _SplitHistoryPageState extends State<SplitHistoryPage> {
  late final WorkspaceApi _workspaceApi;

  List<SplitRecord> _records = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _workspaceApi = widget.workspaceApi ?? WorkspaceApi();
    unawaited(_loadRecords());
  }

  Future<void> _loadRecords() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await _workspaceApi.getSplitRecords(limit: 20);
      if (!mounted) {
        return;
      }
      setState(() {
        _records = response.records;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '分割历史加载失败';
        _loading = false;
      });
    }
  }

  Future<void> _openRecordDetail(SplitRecord record) async {
    final importedCount = await Navigator.of(context).push<int>(
      MaterialPageRoute<int>(
        builder: (_) => SplitRecordDetailPage(
          recordSummary: record,
          workspaceApi: _workspaceApi,
        ),
      ),
    );
    if (!mounted || importedCount == null || importedCount <= 0) {
      return;
    }
    showAppSnackBar(context, '已导入 $importedCount 道题目');
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
              _SplitHistoryHeader(
                palette: palette,
                recordCount: _records.length,
                loading: _loading,
                onBack: () => Navigator.of(context).maybePop(),
                onRefresh: () => unawaited(_loadRecords()),
              ),
              Expanded(child: _buildBody(palette)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody(AppThemePalette palette) {
    if (_loading) {
      return Center(
        child: CircularProgressIndicator(
          color: palette.primaryLight,
          strokeWidth: 2,
        ),
      );
    }

    if (_error != null) {
      return _SplitHistoryStateView(
        palette: palette,
        icon: Icons.error_outline_rounded,
        title: '加载失败',
        message: _error!,
        actionText: '重试',
        onAction: () => unawaited(_loadRecords()),
      );
    }

    if (_records.isEmpty) {
      return RefreshIndicator(
        color: palette.primary,
        onRefresh: _loadRecords,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(24, 80, 24, 24),
          children: [
            _SplitHistoryStateView(
              palette: palette,
              icon: Icons.history_rounded,
              title: '暂无分割历史',
              message: '完成试卷分割后会显示在这里',
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      color: palette.primary,
      onRefresh: _loadRecords,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
        itemCount: _records.length,
        itemBuilder: (context, index) {
          final record = _records[index];
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: _SplitRecordTile(
                palette: palette,
                record: record,
                onTap: () => unawaited(_openRecordDetail(record)),
              ),
            ),
          );
        },
      ),
    );
  }
}

class SplitRecordDetailPage extends StatefulWidget {
  const SplitRecordDetailPage({
    super.key,
    required this.recordSummary,
    required this.workspaceApi,
  });

  final SplitRecord recordSummary;
  final WorkspaceApi workspaceApi;

  @override
  State<SplitRecordDetailPage> createState() => _SplitRecordDetailPageState();
}

class _SplitRecordDetailPageState extends State<SplitRecordDetailPage> {
  final Set<String> _selectedQuestionIds = {};

  SplitRecord? _record;
  bool _loading = true;
  bool _isImporting = false;
  bool _didInitSelection = false;
  String? _error;

  SplitRecord get _displayRecord => _record ?? widget.recordSummary;

  List<SplitQuestion> get _questions => _displayRecord.questions;

  List<String> get _orderedQuestionIds => _questions.indexed
      .map((entry) => _questionSelectionId(entry.$2, entry.$1))
      .toList(growable: false);

  List<String> get _selectedIdsInQuestionOrder => _orderedQuestionIds
      .where(_selectedQuestionIds.contains)
      .toList(growable: false);

  int get _selectedCount => _selectedIdsInQuestionOrder.length;

  bool get _allSelected =>
      _questions.isNotEmpty && _selectedCount == _questions.length;

  @override
  void initState() {
    super.initState();
    unawaited(_loadRecord());
  }

  Future<void> _loadRecord() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await widget.workspaceApi.getSplitRecordDetail(
        recordId: widget.recordSummary.id,
      );
      if (!mounted) {
        return;
      }

      if (!response.success || response.record == null) {
        setState(() {
          _error = response.message.isEmpty ? '分割详情加载失败' : response.message;
          _loading = false;
        });
        return;
      }

      final record = response.record!;
      setState(() {
        _record = record.questions.isEmpty &&
                widget.recordSummary.questions.isNotEmpty
            ? widget.recordSummary
            : record;
        _syncInitialSelection(_record!.questions);
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '分割详情加载失败';
        _loading = false;
      });
    }
  }

  void _syncInitialSelection(List<SplitQuestion> questions) {
    if (_didInitSelection) {
      return;
    }
    _selectedQuestionIds
      ..clear()
      ..addAll(
        questions.indexed.map(
          (entry) => _questionSelectionId(entry.$2, entry.$1),
        ),
      );
    _didInitSelection = true;
  }

  String _questionSelectionId(SplitQuestion question, int index) {
    if (question.uid.trim().isNotEmpty) {
      return question.uid.trim();
    }
    if (question.questionId.trim().isNotEmpty) {
      return question.questionId.trim();
    }
    return index.toString();
  }

  void _toggleQuestionSelection(SplitQuestion question, int index) {
    final id = _questionSelectionId(question, index);
    setState(() {
      if (_selectedQuestionIds.contains(id)) {
        _selectedQuestionIds.remove(id);
      } else {
        _selectedQuestionIds.add(id);
      }
    });
  }

  void _selectAllQuestions() {
    setState(() {
      _selectedQuestionIds
        ..clear()
        ..addAll(_orderedQuestionIds);
    });
  }

  void _clearQuestionSelection() {
    if (_selectedQuestionIds.isEmpty) {
      return;
    }
    setState(() {
      _selectedQuestionIds.clear();
    });
  }

  Future<void> _openImportDialog() async {
    final selectedIds = _selectedIdsInQuestionOrder;

    if (selectedIds.isEmpty) {
      showAppSnackBar(context, '请先选择题目');
      return;
    }

    setState(() => _isImporting = true);
    await WorkspaceProjectStore.instance.ensureLoaded();
    if (!mounted) {
      return;
    }
    setState(() => _isImporting = false);

    final store = WorkspaceProjectStore.instance;
    if (store.questionProjects.isEmpty) {
      showAppSnackBar(context, store.errorMessage ?? '暂无可导入的错题库');
      return;
    }

    final palette = AppThemePalette.of(context);
    final project = await showDialog<WorkspaceProject>(
      context: context,
      barrierDismissible: !_isImporting,
      builder: (context) => _SplitImportQuestionBankDialog(
        palette: palette,
        projects: store.questionProjects,
        selectedCount: selectedIds.length,
      ),
    );

    if (project == null) {
      return;
    }

    await _saveSelectedQuestions(project, widget.recordSummary.id, selectedIds);
  }

  Future<void> _saveSelectedQuestions(
    WorkspaceProject project,
    int id,
    List<String> selectedIds,
  ) async {
    setState(() => _isImporting = true);

    try {
      final response = await widget.workspaceApi.saveSplitQuestionsToDb(
        splitRecordId:id,
        projectId: project.id,
        selectedIds: selectedIds,
      );
      if (!mounted) {
        return;
      }

      if (!response.success) {
        showAppSnackBar(
          context,
          response.message.isEmpty ? '导入失败' : response.message,
        );
        return;
      }

      await WorkspaceProjectStore.instance.refresh();
      if (!mounted) {
        return;
      }

      Navigator.of(context).pop(selectedIds.length);
    } on ApiException catch (error) {
      if (mounted) {
        showAppSnackBar(context, error.message);
      }
    } catch (_) {
      if (mounted) {
        showAppSnackBar(context, '导入失败，请稍后重试');
      }
    } finally {
      if (mounted) {
        setState(() => _isImporting = false);
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
              _SplitRecordDetailHeader(
                palette: palette,
                record: _displayRecord,
                loading: _loading,
                importing: _isImporting,
                onBack: () => Navigator.of(context).maybePop(),
              ),
              Expanded(child: _buildDetailBody(palette)),
              if (!_loading && _error == null && _questions.isNotEmpty)
                _SplitRecordBottomBar(
                  palette: palette,
                  selectedCount: _selectedCount,
                  allSelected: _allSelected,
                  importing: _isImporting,
                  onToggleSelection: _allSelected
                      ? _clearQuestionSelection
                      : _selectAllQuestions,
                  onImportSelected: () => unawaited(_openImportDialog()),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailBody(AppThemePalette palette) {
    if (_loading) {
      return Center(
        child: CircularProgressIndicator(
          color: palette.primaryLight,
          strokeWidth: 2,
        ),
      );
    }

    if (_error != null) {
      return _SplitHistoryStateView(
        palette: palette,
        icon: Icons.error_outline_rounded,
        title: '加载失败',
        message: _error!,
        actionText: '重试',
        onAction: () => unawaited(_loadRecord()),
      );
    }

    if (_questions.isEmpty) {
      return _SplitHistoryStateView(
        palette: palette,
        icon: Icons.assignment_outlined,
        title: '暂无题目',
        message: '这条分割记录没有返回题目详情',
      );
    }

    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 28),
      itemCount: _questions.length,
      separatorBuilder: (context, index) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final question = _questions[index];
        final selected = _selectedQuestionIds.contains(
          _questionSelectionId(question, index),
        );
        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: _SplitQuestionCard(
              palette: palette,
              question: question,
              index: index,
              selected: selected,
              imageUrls: _imageUrlsForQuestion(question),
              resolveImageUrl: _resolveImageUrl,
              loadImageBytes: widget.workspaceApi.loadProtectedImage,
              onToggle: () => _toggleQuestionSelection(question, index),
            ),
          ),
        );
      },
    );
  }

  List<String> _imageUrlsForQuestion(SplitQuestion question) {
    final urls = <String>[];
    final embeddedUrls = _embeddedImageUrlsForQuestion(question);

    void add(String? value) {
      final url = _resolveImageUrl(value);
      if (url == null || urls.contains(url) || embeddedUrls.contains(url)) {
        return;
      }
      urls.add(url);
    }

    if (embeddedUrls.isEmpty) {
      for (final url in question.imageRefs) {
        add(url);
      }
      for (final url in question.optionImages) {
        add(url);
      }
    }
    return urls;
  }

  Set<String> _embeddedImageUrlsForQuestion(SplitQuestion question) {
    final urls = <String>{};
    final imagePattern = RegExp(
      r"""<img\b[^>]*\bsrc\s*=\s*(['"])(.*?)\1""",
      caseSensitive: false,
      dotAll: true,
    );
    final markdownImagePattern = RegExp(r'!\[[^\]]*\]\(([^)]+)\)');

    void add(String? value) {
      final url = _resolveImageUrl(value);
      if (url != null) {
        urls.add(url);
      }
    }

    for (final block in question.contentBlocks) {
      if (block.isImage) {
        add(block.content);
      }
      for (final match in imagePattern.allMatches(block.content)) {
        add(match.group(2));
      }
      for (final match in markdownImagePattern.allMatches(block.content)) {
        add(match.group(1));
      }
    }
    if (question.options.isNotEmpty) {
      for (final url in question.optionImages) {
        add(url);
      }
    }
    return urls;
  }

  String? _resolveImageUrl(String? raw) {
    if (raw == null) {
      return null;
    }

    final trimmed = raw.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }

    final base = widget.workspaceApi.baseUrl;
    if (base.isEmpty) {
      return null;
    }

    final normalizedBase =
        base.endsWith('/') ? base.substring(0, base.length - 1) : base;
    if (trimmed.contains('\\') || RegExp(r'^[A-Za-z]:').hasMatch(trimmed)) {
      final filename = trimmed.split(RegExp(r'[\\/]+')).last;
      if (filename.isEmpty) {
        return null;
      }
      return '$normalizedBase/api/image/$filename';
    }
    if (trimmed.startsWith('/')) {
      return '$normalizedBase$trimmed';
    }
    return '$normalizedBase/$trimmed';
  }
}

class _SplitHistoryHeader extends StatelessWidget {
  const _SplitHistoryHeader({
    required this.palette,
    required this.recordCount,
    required this.loading,
    required this.onBack,
    required this.onRefresh,
  });

  final AppThemePalette palette;
  final int recordCount;
  final bool loading;
  final VoidCallback onBack;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: palette.divider)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(4, 8, 8, 10),
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
                color: palette.primary.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.history_rounded,
                color: palette.primaryLight,
                size: 22,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '分割历史',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: palette.textMain,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      _SplitMetaChip(
                        palette: palette,
                        icon: Icons.segment_rounded,
                        label: '最近记录',
                      ),
                      _SplitMetaChip(
                        palette: palette,
                        icon: loading
                            ? Icons.sync_rounded
                            : Icons.format_list_numbered_rounded,
                        label: loading ? '同步中' : '$recordCount 条',
                      ),
                    ],
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: '刷新',
              onPressed: loading ? null : onRefresh,
              icon: const Icon(Icons.refresh_rounded),
              color: palette.textSub,
            ),
          ],
        ),
      ),
    );
  }
}

class _SplitMetaChip extends StatelessWidget {
  const _SplitMetaChip({
    required this.palette,
    required this.label,
    this.icon,
    this.highlighted = false,
  });

  final AppThemePalette palette;
  final String label;
  final IconData? icon;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    final color = highlighted ? palette.primary : palette.textSub;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: highlighted
            ? palette.primary.withValues(alpha: 0.12)
            : palette.badgeBg,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(
          color: highlighted
              ? palette.primary.withValues(alpha: 0.22)
              : palette.panelBorder,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, color: color, size: 12),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              height: 1,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _SplitRecordTile extends StatelessWidget {
  const _SplitRecordTile({
    required this.palette,
    required this.record,
    required this.onTap,
  });

  final AppThemePalette palette;
  final SplitRecord record;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final provider = record.modelProvider?.trim();

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
          decoration: BoxDecoration(
            color: palette.cardBg,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.panelBorder),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 34,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: palette.primary.withValues(alpha: 0.13),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.description_rounded,
                  color: palette.primaryLight,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      record.displaySubject,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 15,
                        height: 1.2,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 7,
                      runSpacing: 7,
                      children: [
                        _SplitMetaChip(
                          palette: palette,
                          icon: Icons.attach_file_rounded,
                          label: '${record.fileNames.length} 个文件',
                        ),
                        _SplitMetaChip(
                          palette: palette,
                          icon: Icons.schedule_rounded,
                          label: _formatRecordTime(record.createdAt),
                        ),
                        if (provider != null && provider.isNotEmpty)
                          _SplitMetaChip(
                            palette: palette,
                            icon: Icons.memory_rounded,
                            label: provider,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: palette.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '${record.questionCount} 题',
                  style: TextStyle(
                    color: palette.primaryLight,
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
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

class _SplitRecordDetailHeader extends StatelessWidget {
  const _SplitRecordDetailHeader({
    required this.palette,
    required this.record,
    required this.loading,
    required this.importing,
    required this.onBack,
  });

  final AppThemePalette palette;
  final SplitRecord record;
  final bool loading;
  final bool importing;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: palette.divider)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                IconButton(
                  tooltip: '返回',
                  onPressed: loading || importing ? null : onBack,
                  icon: const Icon(Icons.arrow_back_ios_new_rounded),
                  color: palette.textMain,
                ),
                Container(
                  width: 42,
                  height: 42,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: palette.primary.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    Icons.description_rounded,
                    color: palette.primaryLight,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        record.displaySubject,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: palette.textMain,
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Wrap(
                        spacing: 8,
                        runSpacing: 6,
                        children: [
                          _SplitMetaChip(
                            palette: palette,
                            icon: Icons.format_list_numbered_rounded,
                            label: '${record.questionCount} 题',
                            highlighted: true,
                          ),
                          _SplitMetaChip(
                            palette: palette,
                            icon: Icons.attach_file_rounded,
                            label: '${record.fileNames.length} 个文件',
                          ),
                          _SplitMetaChip(
                            palette: palette,
                            icon: Icons.schedule_rounded,
                            label: _formatRecordTime(record.createdAt),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SplitRecordBottomBar extends StatelessWidget {
  const _SplitRecordBottomBar({
    required this.palette,
    required this.selectedCount,
    required this.allSelected,
    required this.importing,
    required this.onToggleSelection,
    required this.onImportSelected,
  });

  final AppThemePalette palette;
  final int selectedCount;
  final bool allSelected;
  final bool importing;
  final VoidCallback onToggleSelection;
  final VoidCallback onImportSelected;

  @override
  Widget build(BuildContext context) {
    final disabled = importing;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: palette.panelBorder)),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: palette.panelBg,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: palette.panelBorder),
            ),
            child: Row(
              children: [
                Expanded(
                  flex: 4,
                  child: _SplitActionButton(
                    palette: palette,
                    label: allSelected ? '取消' : '全选',
                    icon: allSelected
                        ? Icons.check_box_outline_blank_rounded
                        : Icons.select_all_rounded,
                    onPressed: disabled ? null : onToggleSelection,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 7,
                  child: _SplitPrimaryActionButton(
                    palette: palette,
                    label: importing ? '导入中' : '导入错题库',
                    selectedCount: selectedCount,
                    importing: importing,
                    onPressed: disabled || selectedCount == 0
                        ? null
                        : onImportSelected,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SplitActionButton extends StatelessWidget {
  const _SplitActionButton({
    required this.palette,
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final AppThemePalette palette;
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final compact = MediaQuery.sizeOf(context).width < 420;
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 16),
      label: Text(label),
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 38),
        padding: EdgeInsets.symmetric(horizontal: compact ? 6 : 10),
        foregroundColor: palette.textMain,
        side: BorderSide(color: palette.panelBorderStrong),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        textStyle: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _SplitPrimaryActionButton extends StatelessWidget {
  const _SplitPrimaryActionButton({
    required this.palette,
    required this.label,
    required this.selectedCount,
    required this.importing,
    required this.onPressed,
  });

  final AppThemePalette palette;
  final String label;
  final int selectedCount;
  final bool importing;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final compact = MediaQuery.sizeOf(context).width < 420;
    return FilledButton.icon(
      onPressed: onPressed,
      icon: importing
          ? const SizedBox(
              width: 15,
              height: 15,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.storage_rounded, size: 17),
      label: FittedBox(
        fit: BoxFit.scaleDown,
        child: Text('$label $selectedCount'),
      ),
      style: FilledButton.styleFrom(
        minimumSize: const Size(0, 38),
        padding: EdgeInsets.symmetric(horizontal: compact ? 6 : 10),
        backgroundColor: palette.primary,
        disabledBackgroundColor: palette.primary.withValues(alpha: 0.35),
        foregroundColor: Colors.white,
        disabledForegroundColor: Colors.white.withValues(alpha: 0.68),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        textStyle: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _SplitImportQuestionBankDialog extends StatefulWidget {
  const _SplitImportQuestionBankDialog({
    required this.palette,
    required this.projects,
    required this.selectedCount,
  });

  final AppThemePalette palette;
  final List<WorkspaceProject> projects;
  final int selectedCount;

  @override
  State<_SplitImportQuestionBankDialog> createState() =>
      _SplitImportQuestionBankDialogState();
}

class _SplitImportQuestionBankDialogState
    extends State<_SplitImportQuestionBankDialog> {
  late WorkspaceProject _selectedProject;

  @override
  void initState() {
    super.initState();
    _selectedProject = widget.projects.firstWhere(
      (project) => project.isDefault,
      orElse: () => widget.projects.first,
    );
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.palette;

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 24),
      backgroundColor: Colors.transparent,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: Container(
          decoration: BoxDecoration(
            color: palette.isLight
                ? Colors.white
                : const Color(0xFF18191D).withValues(alpha: 0.98),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.panelBorderStrong),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 12, 14),
                child: Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: palette.primary.withValues(alpha: 0.16),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: Icon(
                        Icons.storage_rounded,
                        color: palette.primaryLight,
                        size: 21,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        '导入错题库',
                        style: TextStyle(
                          color: palette.textMain,
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: '关闭',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(
                        Icons.close_rounded,
                        color: palette.textSub,
                      ),
                    ),
                  ],
                ),
              ),
              Divider(height: 1, color: palette.panelBorderStrong),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 10),
                child: Text(
                  '将 ${widget.selectedCount} 道已选题目导入到:',
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
                  itemCount: widget.projects.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final project = widget.projects[index];
                    final selected = project.id == _selectedProject.id;
                    return _buildProjectOption(project, selected, palette);
                  },
                ),
              ),
              Divider(height: 1, color: palette.panelBorderStrong),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: palette.textMain,
                        side: BorderSide(color: palette.panelBorderStrong),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: const Text(
                        '取消',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(width: 10),
                    FilledButton(
                      onPressed: () =>
                          Navigator.of(context).pop(_selectedProject),
                      style: FilledButton.styleFrom(
                        backgroundColor: palette.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: const Text(
                        '确认导入',
                        style: TextStyle(fontWeight: FontWeight.w900),
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

  Widget _buildProjectOption(
    WorkspaceProject project,
    bool selected,
    AppThemePalette palette,
  ) {
    final selectedBg =
        palette.primary.withValues(alpha: palette.isLight ? 0.10 : 0.16);

    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => setState(() => _selectedProject = project),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: selected ? selectedBg : palette.badgeBg,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected
                ? palette.primary.withValues(alpha: 0.72)
                : palette.panelBorderStrong,
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.folder_rounded,
              color: selected ? palette.primaryLight : palette.textSub,
              size: 20,
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
                      color: selected ? palette.primaryLight : palette.textMain,
                      fontSize: 14,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${project.questionCount} 题',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: palette.textSub,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            if (selected)
              Icon(
                Icons.check_rounded,
                color: palette.primaryLight,
                size: 20,
              ),
          ],
        ),
      ),
    );
  }
}

class _SplitQuestionCard extends StatelessWidget {
  const _SplitQuestionCard({
    required this.palette,
    required this.question,
    required this.index,
    required this.selected,
    required this.imageUrls,
    required this.resolveImageUrl,
    required this.loadImageBytes,
    required this.onToggle,
  });

  final AppThemePalette palette;
  final SplitQuestion question;
  final int index;
  final bool selected;
  final List<String> imageUrls;
  final String? Function(String? raw) resolveImageUrl;
  final Future<Uint8List> Function(String url) loadImageBytes;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final contentBlocks = question.contentBlocks
        .where((block) => block.content.trim().isNotEmpty)
        .toList(growable: false);
    final contentStyle = TextStyle(
      color: palette.textMain,
      fontSize: 13,
      height: 1.55,
      fontWeight: FontWeight.w600,
    );
    final contentWidgets = contentBlocks.isEmpty
        ? <Widget>[
            Text(
              '暂无题干内容',
              style: contentStyle.copyWith(color: palette.textSub),
            ),
          ]
        : contentBlocks
            .map<Widget>(
              (block) => Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: block.isImage
                    ? _QuestionMarkdownImage(
                        palette: palette,
                        url: block.content,
                        alt: '题目图片',
                        resolveImageUrl: resolveImageUrl,
                        loadImageBytes: loadImageBytes,
                      )
                    : _QuestionContentBlock(
                        content: block.content,
                        palette: palette,
                        resolveImageUrl: resolveImageUrl,
                        loadImageBytes: loadImageBytes,
                        style: contentStyle,
                      ),
              ),
            )
            .toList(growable: false);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: selected
                ? palette.primary.withValues(
                    alpha: palette.isLight ? 0.07 : 0.12,
                  )
                : palette.panelBg,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected
                  ? palette.primary.withValues(alpha: 0.45)
                  : palette.panelBorder,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  _SelectionBox(selected: selected, palette: palette),
                  const SizedBox(width: 10),
                  Container(
                    width: 24,
                    height: 24,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: palette.primary.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      question.questionId.isEmpty
                          ? '${index + 1}'
                          : question.questionId,
                      style: TextStyle(
                        color: palette.primary,
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        _QuestionMetaChip(
                          palette: palette,
                          icon: Icons.article_outlined,
                          label: question.questionType ?? '题目',
                        ),
                        if (question.hasFormula)
                          _QuestionIconChip(
                            palette: palette,
                            icon: Icons.functions_rounded,
                            tooltip: '含公式',
                          ),
                        if (question.hasImage || imageUrls.isNotEmpty)
                          _QuestionIconChip(
                            palette: palette,
                            icon: Icons.image_rounded,
                            tooltip: '含图片',
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              if (question.sectionTitle != null &&
                  question.sectionTitle!.trim().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  question.sectionTitle!.trim(),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 11,
                    height: 1.35,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
              const SizedBox(height: 10),
              ...contentWidgets,
              if (question.options.isNotEmpty) ...[
                const SizedBox(height: 2),
                _QuestionOptions(
                  palette: palette,
                  options: question.options,
                  optionImages: question.optionImages,
                  resolveImageUrl: resolveImageUrl,
                  loadImageBytes: loadImageBytes,
                ),
              ],
              if (imageUrls.isNotEmpty) ...[
                const SizedBox(height: 8),
                _QuestionImages(
                  palette: palette,
                  imageUrls: imageUrls,
                  loadImageBytes: loadImageBytes,
                ),
              ],
              if (question.knowledgeTags.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: question.knowledgeTags
                      .map(
                        (tag) => _QuestionTag(
                          palette: palette,
                          tag: tag,
                        ),
                      )
                      .toList(growable: false),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _QuestionOptions extends StatelessWidget {
  const _QuestionOptions({
    required this.palette,
    required this.options,
    required this.optionImages,
    required this.resolveImageUrl,
    required this.loadImageBytes,
  });

  final AppThemePalette palette;
  final List<String> options;
  final List<String> optionImages;
  final String? Function(String? raw) resolveImageUrl;
  final Future<Uint8List> Function(String url) loadImageBytes;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(options.length, (index) {
        final option = options[index];
        final imageUrl =
            index < optionImages.length ? optionImages[index] : null;
        final hasImage = imageUrl != null && imageUrl.trim().isNotEmpty;

        return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 7),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: palette.badgeBg,
            borderRadius: BorderRadius.circular(7),
            border: Border.all(color: palette.panelBorder),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (hasImage) ...[
                _QuestionMarkdownImage(
                  palette: palette,
                  url: imageUrl!,
                  alt: '选项图片',
                  resolveImageUrl: resolveImageUrl,
                  loadImageBytes: loadImageBytes,
                  width: 92,
                  height: 70,
                  maxHeight: 70,
                ),
                const SizedBox(width: 9),
              ],
              Expanded(
                child: MarkdownMathText(
                  text: option,
                  palette: palette,
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 12,
                    height: 1.45,
                    fontWeight: FontWeight.w700,
                  ),
                  imageBuilder: (context, alt, url) {
                    return _QuestionMarkdownImage(
                      palette: palette,
                      url: url,
                      alt: alt,
                      resolveImageUrl: resolveImageUrl,
                      loadImageBytes: loadImageBytes,
                      maxHeight: 130,
                    );
                  },
                ),
              ),
            ],
          ),
        );
      }),
    );
  }
}

class _QuestionContentBlock extends StatelessWidget {
  const _QuestionContentBlock({
    required this.content,
    required this.palette,
    required this.resolveImageUrl,
    required this.loadImageBytes,
    required this.style,
  });

  final String content;
  final AppThemePalette palette;
  final String? Function(String? raw) resolveImageUrl;
  final Future<Uint8List> Function(String url) loadImageBytes;
  final TextStyle style;

  @override
  Widget build(BuildContext context) {
    return MarkdownMathText(
      text: content,
      palette: palette,
      style: style,
      imageBuilder: (context, alt, url) {
        return _QuestionMarkdownImage(
          palette: palette,
          url: url,
          alt: alt,
          resolveImageUrl: resolveImageUrl,
          loadImageBytes: loadImageBytes,
        );
      },
    );
  }
}

class _QuestionMarkdownImage extends StatelessWidget {
  const _QuestionMarkdownImage({
    required this.palette,
    required this.url,
    required this.alt,
    required this.resolveImageUrl,
    required this.loadImageBytes,
    this.width,
    this.height,
    this.maxHeight = 180,
  });

  final AppThemePalette palette;
  final String url;
  final String alt;
  final String? Function(String? raw) resolveImageUrl;
  final Future<Uint8List> Function(String url) loadImageBytes;
  final double? width;
  final double? height;
  final double maxHeight;

  @override
  Widget build(BuildContext context) {
    final resolvedUrl = resolveImageUrl(url);
    if (resolvedUrl == null) {
      return Text(
        alt.trim().isEmpty ? '图片地址无效' : alt,
        style: TextStyle(
          color: palette.textSub,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      );
    }

    return Container(
      width: width ?? double.infinity,
      height: height,
      constraints: height == null
          ? BoxConstraints(
              minHeight: 86,
              maxHeight: maxHeight,
            )
          : null,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: palette.imageBg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: palette.panelBorder),
      ),
      child: ProtectedImage(
        url: resolvedUrl,
        loadBytes: loadImageBytes,
        fit: BoxFit.contain,
        loading: Center(
          child: SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(
              color: palette.primaryLight,
              strokeWidth: 2,
            ),
          ),
        ),
        error: Center(
          child: Icon(
            Icons.broken_image_outlined,
            color: palette.textSub,
            size: 22,
          ),
        ),
      ),
    );
  }
}

class _QuestionImages extends StatelessWidget {
  const _QuestionImages({
    required this.palette,
    required this.imageUrls,
    required this.loadImageBytes,
  });

  final AppThemePalette palette;
  final List<String> imageUrls;
  final Future<Uint8List> Function(String url) loadImageBytes;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: imageUrls
          .map(
            (url) => Container(
              width: 118,
              height: 88,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: palette.imageBg,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: palette.panelBorder),
              ),
              child: ProtectedImage(
                url: url,
                loadBytes: loadImageBytes,
                fit: BoxFit.contain,
                loading: Center(
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      color: palette.primaryLight,
                      strokeWidth: 2,
                    ),
                  ),
                ),
                error: Center(
                  child: Icon(
                    Icons.broken_image_outlined,
                    color: palette.textSub,
                    size: 22,
                  ),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _SelectionBox extends StatelessWidget {
  const _SelectionBox({
    required this.selected,
    required this.palette,
  });

  final bool selected;
  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      width: 20,
      height: 20,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: selected ? palette.primary : Colors.transparent,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: selected ? palette.primary : palette.panelBorderStrong,
        ),
      ),
      child: selected
          ? const Icon(Icons.check_rounded, color: Colors.white, size: 15)
          : null,
    );
  }
}

class _QuestionMetaChip extends StatelessWidget {
  const _QuestionMetaChip({
    required this.palette,
    required this.icon,
    required this.label,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: palette.badgeBg,
        borderRadius: BorderRadius.circular(5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: palette.textSub),
          const SizedBox(width: 3),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: palette.textSub,
                fontSize: 10,
                height: 1,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _QuestionIconChip extends StatelessWidget {
  const _QuestionIconChip({
    required this.palette,
    required this.icon,
    required this.tooltip,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Container(
        width: 20,
        height: 20,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: palette.primary.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(5),
        ),
        child: Icon(icon, size: 12, color: palette.primaryLight),
      ),
    );
  }
}

class _QuestionTag extends StatelessWidget {
  const _QuestionTag({
    required this.palette,
    required this.tag,
  });

  final AppThemePalette palette;
  final String tag;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: palette.primary.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(
        tag,
        style: TextStyle(
          color: palette.primary,
          fontSize: 10,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _SplitHistoryStateView extends StatelessWidget {
  const _SplitHistoryStateView({
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
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        margin: const EdgeInsets.symmetric(horizontal: 24),
        padding: const EdgeInsets.fromLTRB(22, 24, 22, 22),
        decoration: BoxDecoration(
          color: palette.panelBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: palette.panelBorder),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 44,
              height: 44,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: palette.primary.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: palette.primaryLight, size: 24),
            ),
            const SizedBox(height: 14),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.textSub,
                fontSize: 13,
                height: 1.35,
                fontWeight: FontWeight.w700,
              ),
            ),
            if (actionText != null && onAction != null) ...[
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: Text(actionText!),
                style: FilledButton.styleFrom(
                  backgroundColor: palette.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String _formatRecordTime(DateTime? time) {
  if (time == null) {
    return '暂无时间';
  }

  final local = time.toLocal();
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '$month-$day $hour:$minute';
}
