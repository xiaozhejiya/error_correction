import 'dart:async';
import 'dart:typed_data';
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../../core/widgets/markdown_math_text.dart';
import '../../data/workspace_api.dart';
import '../../data/workspace_project_store.dart';

/// 智能录入处理流程页。
class SmartInputProcessPage extends StatefulWidget {
  const SmartInputProcessPage({
    super.key,
    required this.files,
    required this.enableQuestionSplit,
    this.splitRequest,
    this.initialEraseHandwriting = true,
    this.onConfirmSplit,
  });

  /// 已上传文件。试卷流程使用 file_key，笔记整理预览会复用原始 bytes。
  final List<SmartInputUploadedFile> files;

  /// 仅试卷分割可开启擦除。笔记整理模式会强制走 OCR 流程。
  /// true：擦除中 -> 擦除完成 -> OCR 中 -> OCR 完成
  /// false：OCR 中 -> OCR 完成
  final bool initialEraseHandwriting;

  /// 仅试卷分割模式开启；笔记整理模式暂不调用 split。
  final bool enableQuestionSplit;

  /// /api/split 使用的模型参数。
  final SplitRequest? splitRequest;

  /// OCR 完成后点击「确认并分割」
  final VoidCallback? onConfirmSplit;

  @override
  State<SmartInputProcessPage> createState() => _SmartInputProcessPageState();
}

class SmartInputUploadedFile {
  const SmartInputUploadedFile({
    required this.fileKey,
    required this.name,
    required this.bytes,
  });

  final String fileKey;
  final String name;
  final List<int> bytes;
}

enum _SmartInputProcessStage {
  erasing,
  erasePreview,
  ocrProcessing,
  ocrPreview,
  noteOrganizing,
  notePreview,
  splitting,
  splitPreview,
}

class _SmartInputProcessPageState extends State<SmartInputProcessPage>
    with TickerProviderStateMixin {
  static const List<String> _stepsWithErase = ['上传', '擦除', 'OCR', '分割', '导出'];
  static const List<String> _examStepsWithoutErase = ['上传', 'OCR', '分割', '导出'];
  static const List<String> _noteSteps = ['上传', 'OCR', '整理', '保存'];

  late final WorkspaceApi _workspaceApi;
  late final AnimationController _pulseController;
  late final AnimationController _loadingBarController;
  late _SmartInputProcessStage _stage;

  final PageController _pageController = PageController();
  final List<_DisplayItem> _displayItems = [];
  final List<OcrPage> _ocrPages = [];
  final List<SplitQuestion> _splitQuestions = [];
  final List<String> _splitWarnings = [];
  final Map<String, Future<Uint8List>> _imageFutures = {};
  final Set<String> _selectedQuestionIds = {};
  NotePreview? _notePreview;
  String? _splitRunId;

  int _currentPage = 0;
  String? _errorMessage;
  bool _isBusy = false;
  bool _isImporting = false;
  bool _didRequestUploadReset = false;

  @override
  void initState() {
    super.initState();

    _workspaceApi = WorkspaceApi();
    _stage = _usesErase
        ? _SmartInputProcessStage.erasing
        : _SmartInputProcessStage.ocrProcessing;

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();

    _loadingBarController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _resetDisplayItems();
    _startByStage();
  }

  @override
  void dispose() {
    unawaited(_resetUploadSessionOnExit());
    _pageController.dispose();
    _pulseController.dispose();
    _loadingBarController.dispose();
    super.dispose();
  }

  Future<void> _resetUploadSessionOnExit() async {
    if (_didRequestUploadReset) {
      return;
    }
    _didRequestUploadReset = true;

    try {
      await _workspaceApi.resetUploadSession();
    } catch (_) {
      // 离开流程页时的清理失败不阻断页面关闭。
    }
  }

  void _resetDisplayItems() {
    _displayItems
      ..clear()
      ..addAll(
        widget.files.map(
          (file) => _DisplayItem(fileKey: file.fileKey, fileName: file.name),
        ),
      );

    if (_displayItems.isEmpty) {
      _displayItems.add(const _DisplayItem(fileKey: '', fileName: '待处理文件'));
    }
    _currentPage = 0;
  }

  void _startByStage() {
    if (_stage == _SmartInputProcessStage.erasing) {
      unawaited(_startEraseProcess());
    } else if (_stage == _SmartInputProcessStage.ocrProcessing) {
      unawaited(_startOcrProcess());
    }
  }

  void _setPageTo0() {
    _currentPage = 0;
    if (_pageController.hasClients) {
      _pageController.jumpToPage(0);
    }
  }

  int get _totalImages => _displayItems.isEmpty ? 1 : _displayItems.length;

  int get _ocrPreviewCount => _ocrPages.isEmpty ? 1 : _ocrPages.length;

  _DisplayItem _itemAt(int index) {
    if (_displayItems.isEmpty) {
      return const _DisplayItem(fileKey: '', fileName: '待处理文件');
    }
    final safeIndex = index.clamp(0, _displayItems.length - 1);
    return _displayItems[safeIndex];
  }

  OcrPage? _ocrPageAt(int index) {
    if (_ocrPages.isEmpty) {
      return null;
    }
    final safeIndex = index.clamp(0, _ocrPages.length - 1);
    return _ocrPages[safeIndex];
  }

  bool get _usesErase =>
      widget.enableQuestionSplit && widget.initialEraseHandwriting;
  bool get _isNoteProcess => !widget.enableQuestionSplit;

  int get _activeStepIndex {
    if (_usesErase) {
      return switch (_stage) {
        _SmartInputProcessStage.erasing ||
        _SmartInputProcessStage.erasePreview =>
          1,
        _SmartInputProcessStage.ocrProcessing ||
        _SmartInputProcessStage.ocrPreview =>
          2,
        _SmartInputProcessStage.splitting => 3,
        _SmartInputProcessStage.splitPreview => 4,
        _SmartInputProcessStage.noteOrganizing ||
        _SmartInputProcessStage.notePreview =>
          0,
      };
    }

    if (_isNoteProcess) {
      return switch (_stage) {
        _SmartInputProcessStage.ocrProcessing => 1,
        _SmartInputProcessStage.ocrPreview => 1,
        _SmartInputProcessStage.noteOrganizing => 2,
        _SmartInputProcessStage.notePreview => 3,
        _ => 0,
      };
    }

    return switch (_stage) {
      _SmartInputProcessStage.ocrProcessing ||
      _SmartInputProcessStage.ocrPreview =>
        1,
      _SmartInputProcessStage.splitting => 2,
      _SmartInputProcessStage.splitPreview => 3,
      _ => 0,
    };
  }

  List<String> get _steps {
    if (_isNoteProcess) {
      return _noteSteps;
    }
    return _usesErase ? _stepsWithErase : _examStepsWithoutErase;
  }

  Set<int> get _doneStepIndexes {
    if (_isNoteProcess) {
      return switch (_stage) {
        _SmartInputProcessStage.ocrProcessing => const {0},
        _SmartInputProcessStage.ocrPreview => const {0},
        _SmartInputProcessStage.noteOrganizing => const {0, 1},
        _SmartInputProcessStage.notePreview => const {0, 1, 2},
        _ => const {0},
      };
    }

    if (!_usesErase) {
      return switch (_stage) {
        _SmartInputProcessStage.ocrProcessing => const {0},
        _SmartInputProcessStage.ocrPreview => const {0, 1},
        _SmartInputProcessStage.splitting => const {0, 1},
        _SmartInputProcessStage.splitPreview => const {0, 1, 2},
        _ => const {0},
      };
    }

    return switch (_stage) {
      _SmartInputProcessStage.erasing => const {0},
      _SmartInputProcessStage.erasePreview => const {0, 1},
      _SmartInputProcessStage.ocrProcessing => const {0, 1},
      _SmartInputProcessStage.ocrPreview => const {0, 1, 2},
      _SmartInputProcessStage.splitting => const {0, 1, 2},
      _SmartInputProcessStage.splitPreview => const {0, 1, 2, 3},
      _SmartInputProcessStage.noteOrganizing ||
      _SmartInputProcessStage.notePreview =>
        const {0},
    };
  }

  String get _pageTitle {
    return switch (_stage) {
      _SmartInputProcessStage.erasing => '智能录入与分析',
      _SmartInputProcessStage.erasePreview => '擦除结果预览',
      _SmartInputProcessStage.ocrProcessing => 'OCR 识别',
      _SmartInputProcessStage.ocrPreview => 'OCR 预览',
      _SmartInputProcessStage.noteOrganizing => '笔记整理',
      _SmartInputProcessStage.notePreview => '保存笔记',
      _SmartInputProcessStage.splitting => '题目分割',
      _SmartInputProcessStage.splitPreview => '分割结果预览',
    };
  }

  Future<void> _startEraseProcess() async {
    _resetDisplayItems();
    _setPageTo0();
    if (!mounted) {
      return;
    }

    setState(() {
      _isBusy = true;
      _errorMessage = null;
      _stage = _SmartInputProcessStage.erasing;
    });

    try {
      final response = await _workspaceApi.eraseUploadedFiles();

      if (!mounted) {
        return;
      }

      if (!response.success) {
        setState(() {
          _isBusy = false;
          _errorMessage = response.message;
        });
        return;
      }

      final merged = _mergeEraseResult(response);
      setState(() {
        _isBusy = false;
        _errorMessage = null;
        _displayItems
          ..clear()
          ..addAll(merged);
        _stage = _SmartInputProcessStage.erasePreview;
        _setPageTo0();
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = error.message;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = '擦除调用失败，请稍后重试';
      });
    }
  }

  List<_DisplayItem> _mergeEraseResult(EraseResponse response) {
    if (widget.files.isEmpty) {
      return const [_DisplayItem(fileKey: '', fileName: '待处理文件')];
    }

    final merged = <_DisplayItem>[];
    for (final input in widget.files) {
      final result = _findErasedResult(input.fileKey, response.files);
      merged.add(
        _DisplayItem(
          fileKey: input.fileKey,
          fileName: input.name,
          beforeImageUrl: _resolveImageUrl(result?.beforeImageUrl),
          afterImageUrl: _resolveImageUrl(result?.afterImageUrl),
        ),
      );
    }

    if (merged.every(
        (item) => item.beforeImageUrl == null && item.afterImageUrl == null)) {
      for (var i = 0; i < response.files.length && i < merged.length; i++) {
        final result = response.files[i];
        merged[i] = _DisplayItem(
          fileKey: merged[i].fileKey,
          fileName: merged[i].fileName,
          beforeImageUrl: _resolveImageUrl(result.beforeImageUrl),
          afterImageUrl: _resolveImageUrl(result.afterImageUrl),
        );
      }
    }

    return merged;
  }

  EraseResultFile? _findErasedResult(
    String fileKey,
    List<EraseResultFile> files,
  ) {
    for (final item in files) {
      if (item.fileKey == fileKey) {
        return item;
      }
    }

    for (final item in files) {
      if (item.beforeFileKey == fileKey || item.afterFileKey == fileKey) {
        return item;
      }
    }

    return null;
  }

  Future<void> _startOcrProcess() async {
    _setPageTo0();

    setState(() {
      _isBusy = true;
      _errorMessage = null;
      _stage = _SmartInputProcessStage.ocrProcessing;
      _ocrPages.clear();
    });

    try {
      final response = await _workspaceApi.runOcr();

      if (!mounted) {
        return;
      }

      if (!response.success || response.pages.isEmpty) {
        setState(() {
          _isBusy = false;
          _errorMessage = response.message;
        });
        return;
      }

      setState(() {
        _isBusy = false;
        _errorMessage = null;
        _ocrPages
          ..clear()
          ..addAll(response.pages);
        _stage = _SmartInputProcessStage.ocrPreview;
        _setPageTo0();
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = error.message;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = 'OCR 调用失败，请稍后重试';
      });
    }
  }

  void _restartErase() {
    unawaited(_startEraseProcess());
  }

  void _startOcr() {
    unawaited(_startOcrProcess());
  }

  void _restartOcr() {
    unawaited(_startOcrProcess());
  }

  Future<void> _startNoteOrganizeProcess() async {
    final request = widget.splitRequest;
    if (request == null) {
      setState(() {
        _stage = _SmartInputProcessStage.noteOrganizing;
        _isBusy = false;
        _errorMessage = '未检测到可用模型，请重新选择模型后再试';
      });
      return;
    }

    final files = widget.files
        .where((file) => file.bytes.isNotEmpty)
        .map(
          (file) => UploadFileItem(
            filename: file.name,
            bytes: file.bytes,
          ),
        )
        .toList(growable: false);

    if (files.isEmpty) {
      setState(() {
        _stage = _SmartInputProcessStage.noteOrganizing;
        _isBusy = false;
        _errorMessage = '缺少原始图片内容，请重新上传后再试';
      });
      return;
    }

    setState(() {
      _stage = _SmartInputProcessStage.noteOrganizing;
      _isBusy = true;
      _errorMessage = null;
      _notePreview = null;
    });

    try {
      final response = await _workspaceApi.organizeNotePreview(
        files: files,
        modelRequest: request,
      );

      if (!mounted) {
        return;
      }

      final preview = response.notePreview;
      if (!response.success || preview == null) {
        setState(() {
          _isBusy = false;
          _errorMessage = '笔记整理失败，请稍后重试';
        });
        return;
      }

      setState(() {
        _isBusy = false;
        _errorMessage = null;
        _notePreview = preview;
        _stage = _SmartInputProcessStage.notePreview;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = error.message;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = '笔记整理失败，请稍后重试';
      });
    }
  }

  Future<void> _startSplitProcess() async {
    if (!widget.enableQuestionSplit) {
      _finishProcess();
      return;
    }

    final request = widget.splitRequest;
    if (request == null) {
      setState(() {
        _stage = _SmartInputProcessStage.splitting;
        _isBusy = false;
        _errorMessage = '未检测到可用模型，请重新选择模型后再试';
      });
      return;
    }

    setState(() {
      _stage = _SmartInputProcessStage.splitting;
      _isBusy = true;
      _errorMessage = null;
      _splitQuestions.clear();
      _splitWarnings.clear();
      _selectedQuestionIds.clear();
      _splitRunId = null;
    });

    try {
      final response = await _workspaceApi.splitQuestions(request: request);

      if (!mounted) {
        return;
      }

      if (!response.success || response.questions.isEmpty) {
        setState(() {
          _isBusy = false;
          _errorMessage = response.message;
        });
        return;
      }

      setState(() {
        _isBusy = false;
        _errorMessage = null;
        _splitRunId = response.runId;
        _splitQuestions
          ..clear()
          ..addAll(response.questions);
        _splitWarnings
          ..clear()
          ..addAll(response.warnings);
        _selectedQuestionIds
          ..clear()
          ..addAll(
            response.questions.indexed.map(
              (entry) => _questionSelectionId(entry.$2, entry.$1),
            ),
          );
        _stage = _SmartInputProcessStage.splitPreview;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = error.message;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBusy = false;
        _errorMessage = '题目分割失败，请稍后重试';
      });
    }
  }

  void _confirmSplit() {
    if (_isNoteProcess) {
      unawaited(_startNoteOrganizeProcess());
      return;
    }
    unawaited(_startSplitProcess());
  }

  void _finishProcess() {
    if (widget.onConfirmSplit != null) {
      widget.onConfirmSplit!();
      return;
    }
    if (!mounted) {
      return;
    }
    Navigator.of(context).pop();
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

  Future<void> _openImportDialog() async {
    final runId = _splitRunId;
    final selectedIds = _selectedQuestionIds.toList(growable: false);

    if (selectedIds.isEmpty) {
      _showMessage('请先选择要导入的题目');
      return;
    }
    if (runId == null || runId.isEmpty) {
      _showMessage('缺少分割任务 ID，请重新分割后再导入');
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
      _showMessage(store.errorMessage ?? '暂无可导入的错题库');
      return;
    }

    final palette = AppThemePalette.of(context);
    final project = await showDialog<WorkspaceProject>(
      context: context,
      barrierDismissible: !_isImporting,
      builder: (context) => _ImportQuestionBankDialog(
        palette: palette,
        projects: store.questionProjects,
        selectedCount: selectedIds.length,
      ),
    );

    if (project == null) {
      return;
    }

    await _saveSelectedQuestions(project, runId, selectedIds);
  }

  Future<void> _saveSelectedQuestions(
    WorkspaceProject project,
    String runId,
    List<String> selectedIds,
  ) async {
    setState(() => _isImporting = true);

    try {
      final response = await _workspaceApi.saveSplitQuestionsToDb(
        runId: runId,
        projectId: project.id,
        selectedIds: selectedIds,
      );

      if (!mounted) {
        return;
      }

      if (!response.success) {
        _showMessage(response.message);
        return;
      }

      await WorkspaceProjectStore.instance.refresh();
      if (!mounted) {
        return;
      }

      _showMessage(response.message.isEmpty ? '导入成功' : response.message);
      _finishProcess();
    } on ApiException catch (error) {
      if (mounted) {
        _showMessage(error.message);
      }
    } catch (_) {
      if (mounted) {
        _showMessage('导入失败，请稍后重试');
      }
    } finally {
      if (mounted) {
        setState(() => _isImporting = false);
      }
    }
  }

  Future<void> _openSaveNoteDialog() async {
    final preview = _notePreview;
    if (preview == null) {
      _showMessage('缺少笔记预览，请重新整理后再保存');
      return;
    }

    setState(() => _isImporting = true);
    await WorkspaceProjectStore.instance.ensureLoaded();
    if (!mounted) {
      return;
    }
    setState(() => _isImporting = false);

    final store = WorkspaceProjectStore.instance;
    if (store.noteProjects.isEmpty) {
      _showMessage(store.errorMessage ?? '暂无可保存的笔记本');
      return;
    }

    final palette = AppThemePalette.of(context);
    final project = await showDialog<WorkspaceProject>(
      context: context,
      barrierDismissible: !_isImporting,
      builder: (context) => _SaveNoteDialog(
        palette: palette,
        projects: store.noteProjects,
        preview: preview,
      ),
    );

    if (project == null) {
      return;
    }

    await _saveOrganizedNote(project, preview);
  }

  Future<void> _saveOrganizedNote(
    WorkspaceProject project,
    NotePreview preview,
  ) async {
    setState(() => _isImporting = true);

    try {
      final response = await _workspaceApi.saveOrganizedNote(
        projectId: project.id,
        preview: preview,
      );

      if (!mounted) {
        return;
      }

      if (!response.success) {
        _showMessage('保存失败，请稍后重试');
        return;
      }

      await WorkspaceProjectStore.instance.refresh();
      if (!mounted) {
        return;
      }

      _showMessage('笔记已保存');
      _finishProcess();
    } on ApiException catch (error) {
      if (mounted) {
        _showMessage(error.message);
      }
    } catch (_) {
      if (mounted) {
        _showMessage('保存失败，请稍后重试');
      }
    } finally {
      if (mounted) {
        setState(() => _isImporting = false);
      }
    }
  }

  void _clearQuestionSelection() {
    setState(_selectedQuestionIds.clear);
  }

  void _showMessage(String message) {
    showAppSnackBar(context, message);
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      backgroundColor: palette.pageBg,
      body: SafeArea(
        child: Column(
          children: [
            _buildAppHeader(palette: palette),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
              child: _buildAppStepper(palette: palette),
            ),
            Expanded(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 260),
                child: _buildStageBody(palette: palette),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppHeader({required AppThemePalette palette}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.of(context).maybePop(),
            icon: const Icon(Icons.arrow_back_ios_new_rounded),
            color: palette.textMain,
            iconSize: 14,
          ),
          Expanded(
            child: Text(
              _pageTitle,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 14,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppStepper({required AppThemePalette palette}) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: palette.panelBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: List.generate(_steps.length, (index) {
          final isDone = _doneStepIndexes.contains(index);
          final isActive = _activeStepIndex == index;
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildStepDot(
                index,
                isDone: isDone,
                isActive: isActive,
                palette: palette,
              ),
              const SizedBox(width: 6),
              Text(
                _steps[index],
                style: TextStyle(
                  color:
                      isActive || isDone ? palette.textMain : palette.textSub,
                  fontWeight:
                      isActive || isDone ? FontWeight.w800 : FontWeight.w600,
                  fontSize: 12,
                ),
              ),
              if (index != _steps.length - 1) ...[
                const SizedBox(width: 10),
                Container(
                  width: 18,
                  height: 1,
                  color: isDone
                      ? palette.primary.withOpacity(0.9)
                      : palette.textSub.withOpacity(0.22),
                ),
              ],
            ],
          );
        }),
      ),
    );
  }

  Widget _buildStepDot(
    int index, {
    required bool isDone,
    required bool isActive,
    required AppThemePalette palette,
  }) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: 24,
      height: 24,
      decoration: BoxDecoration(
        color: isActive || isDone ? palette.primary : null,
        borderRadius: BorderRadius.circular(11),
        boxShadow: isActive
            ? [
                BoxShadow(
                  color: palette.primary.withOpacity(0.38),
                  blurRadius: 12,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
      alignment: Alignment.center,
      child: isDone
          ? Icon(Icons.check_rounded, color: Colors.white, size: 16)
          : Text(
              '${index + 1}',
              style: TextStyle(
                color: isActive ? Colors.white : palette.textSub,
                fontWeight: FontWeight.w800,
                fontSize: 12,
              ),
            ),
    );
  }

  Widget _buildStageBody({required AppThemePalette palette}) {
    switch (_stage) {
      case _SmartInputProcessStage.erasing:
        return _buildProcessingView(
          key: const ValueKey('erasing'),
          title: '正在擦除手写笔迹',
          subtitle: 'EnsExam 正在识别并移除手写内容',
          icon: Icons.auto_fix_high_rounded,
          palette: palette,
          onRetry: _isBusy ? null : _startEraseProcess,
        );

      case _SmartInputProcessStage.erasePreview:
        return _buildErasePreviewView(
          key: const ValueKey('erasePreview'),
          palette: palette,
        );

      case _SmartInputProcessStage.ocrProcessing:
        return _buildProcessingView(
          key: const ValueKey('ocrProcessing'),
          title: '正在执行 OCR 识别',
          subtitle: 'PaddleOCR 正在解析文档结构与文字内容',
          icon: Icons.auto_awesome,
          palette: palette,
          onRetry: _isBusy ? null : _startOcr,
        );

      case _SmartInputProcessStage.ocrPreview:
        return _buildOcrPreviewView(
          key: const ValueKey('ocrPreview'),
          palette: palette,
        );

      case _SmartInputProcessStage.noteOrganizing:
        return _buildProcessingView(
          key: const ValueKey('noteOrganizing'),
          title: '正在整理笔记',
          subtitle: 'AI 正在根据 OCR 结果生成结构化笔记预览',
          icon: Icons.menu_book_rounded,
          palette: palette,
          onRetry: _isBusy ? null : _startNoteOrganizeProcess,
        );

      case _SmartInputProcessStage.notePreview:
        return _buildNotePreviewView(
          key: const ValueKey('notePreview'),
          palette: palette,
        );

      case _SmartInputProcessStage.splitting:
        return _buildProcessingView(
          key: const ValueKey('splitting'),
          title: '正在分割题目',
          subtitle: 'AI 正在根据 OCR 结果拆分题目并整理知识点',
          icon: Icons.account_tree_rounded,
          palette: palette,
          onRetry: _isBusy ? null : _confirmSplit,
        );

      case _SmartInputProcessStage.splitPreview:
        return _buildSplitPreviewView(
          key: const ValueKey('splitPreview'),
          palette: palette,
        );
    }
  }

  Widget _buildProcessingView({
    required Key key,
    required String title,
    required String subtitle,
    required AppThemePalette palette,
    required IconData icon,
    required VoidCallback? onRetry,
  }) {
    return SizedBox(
      key: key,
      width: double.infinity,
      height: double.infinity,
      child: Stack(
        fit: StackFit.expand,
        children: [
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
              child: Container(color: Colors.black.withOpacity(0)),
            ),
          ),
          Column(
            children: [
              const SizedBox(height: 100),
              SizedBox(
                width: 156,
                height: 156,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    AnimatedBuilder(
                      animation: _pulseController,
                      builder: (context, child) {
                        final t = _pulseController.value;
                        return CustomPaint(
                          size: const Size(156, 156),
                          painter: _PulseRingPainter(
                            t: t,
                            color: palette.primary,
                          ),
                        );
                      },
                    ),
                    Container(
                      width: 72,
                      height: 72,
                      decoration: BoxDecoration(
                        color: palette.primaryDeep,
                        borderRadius: BorderRadius.circular(22),
                        gradient: LinearGradient(
                          colors: [
                            palette.primary,
                            palette.primary.withOpacity(0.55),
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: palette.primary.withOpacity(0.48),
                            blurRadius: 28,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      child: Icon(
                        icon,
                        color: Colors.white,
                        size: 34,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 30),
              Text(
                title,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: palette.textMain,
                  fontSize: 23,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: palette.textSub,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 30),
              _buildMovingProgressBar(palette),
              const SizedBox(height: 16),
              if (_errorMessage != null) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    _errorMessage!,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: palette.errorText,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                if (onRetry != null)
                  OutlinedButton(
                    onPressed: _isBusy ? null : onRetry,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: palette.primary,
                      side: BorderSide(color: palette.primary),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 10,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('重试'),
                  ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMovingProgressBar(AppThemePalette palette) {
    return SizedBox(
      width: 260,
      height: 10,
      child: LayoutBuilder(builder: (context, constraints) {
        final width = constraints.maxWidth;
        const barWidth = 86.0;
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            color: palette.textSub.withOpacity(0.1),
          ),
          child: AnimatedBuilder(
            animation: _loadingBarController,
            builder: (context, _) {
              final left = (width - barWidth).clamp(0.0, width).toDouble() *
                  _loadingBarController.value;
              return Stack(
                children: [
                  Positioned(
                    left: left,
                    top: 0,
                    bottom: 0,
                    child: Container(
                      width: barWidth,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(999),
                        gradient: LinearGradient(
                          colors: [
                            palette.primary.withOpacity(0.9),
                            palette.primaryLight.withOpacity(0.9),
                            Colors.white.withOpacity(0.2),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        );
      }),
    );
  }

  Widget _buildErasePreviewView({
    required Key key,
    required AppThemePalette palette,
  }) {
    return Column(
      key: key,
      children: [
        Expanded(
          child: PageView.builder(
            controller: _pageController,
            itemCount: _totalImages,
            onPageChanged: (index) => setState(() => _currentPage = index),
            itemBuilder: (context, index) {
              final item = _itemAt(index);
              return EraseImageCompareViewer(
                beforeImage: _loadProtectedImage(item.beforeImageUrl),
                afterImage: _loadProtectedImage(item.afterImageUrl),
                placeholderText: item.fileName,
                backgroundColor: palette.imageBg,
                dividerColor: palette.compareLine,
                textColor: palette.textSub,
              );
            },
          ),
        ),
        if (_totalImages > 1) _buildPageSwitcher(palette),
        const SizedBox(height: 10),
        _buildBottomActions(
          palette: palette,
          leftText: '重新擦除',
          rightText: '开始 OCR',
          onLeft: _restartErase,
          onRight: _startOcr,
        ),
      ],
    );
  }

  Widget _buildOcrPreviewView({
    required Key key,
    required AppThemePalette palette,
  }) {
    return Column(
      key: key,
      children: [
        Expanded(
          child: PageView.builder(
            controller: _pageController,
            itemCount: _ocrPreviewCount,
            onPageChanged: (index) => setState(() => _currentPage = index),
            itemBuilder: (context, index) {
              final page = _ocrPageAt(index);
              final item = _itemAt(index);
              final imageUrl = _resolveImageUrl(page?.imageUrl) ??
                  item.afterImageUrl ??
                  item.beforeImageUrl;
              final image = _loadProtectedImage(imageUrl);
              return _OcrAnnotatedFrame(
                image: image,
                title:
                    page == null ? item.fileName : '第 ${page.pageIndex + 1} 页',
                page: page,
                fallback: _buildEmptyPaper(palette: palette),
                palette: palette,
              );
            },
          ),
        ),
        if (_ocrPreviewCount > 1)
          _buildPageIndicator(palette, count: _ocrPreviewCount),
        const SizedBox(height: 10),
        _buildBottomActions(
          palette: palette,
          leftText: '重新识别',
          rightText: widget.enableQuestionSplit ? '确认并分割' : '确认并整理',
          onLeft: _restartOcr,
          onRight: _confirmSplit,
        ),
      ],
    );
  }

  Widget _buildSplitPreviewView({
    required Key key,
    required AppThemePalette palette,
  }) {
    return Column(
      key: key,
      children: [
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
            itemCount: _splitQuestions.length + 1,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              if (index == 0) {
                return _buildSplitSummary(palette);
              }

              return _buildSplitQuestionCard(
                question: _splitQuestions[index - 1],
                index: index - 1,
                palette: palette,
                selected: _selectedQuestionIds.contains(
                  _questionSelectionId(_splitQuestions[index - 1], index - 1),
                ),
                onToggle: () => _toggleQuestionSelection(
                  _splitQuestions[index - 1],
                  index - 1,
                ),
              );
            },
          ),
        ),
        _buildExportBottomBar(palette: palette),
      ],
    );
  }

  Widget _buildNotePreviewView({
    required Key key,
    required AppThemePalette palette,
  }) {
    final preview = _notePreview;
    if (preview == null) {
      return _buildProcessingView(
        key: key,
        title: '笔记预览不可用',
        subtitle: '请返回上一步重新整理',
        icon: Icons.error_outline_rounded,
        palette: palette,
        onRetry: _startNoteOrganizeProcess,
      );
    }

    return Column(
      key: key,
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
            children: [
              _buildNotePreviewHeader(preview, palette),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: palette.panelBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: palette.panelBorder),
                ),
                child: MarkdownMathText(
                  text: preview.contentMarkdown,
                  palette: palette,
                  style: TextStyle(
                    color: palette.textMain,
                    fontSize: 14,
                    height: 1.55,
                    fontWeight: FontWeight.w600,
                  ),
                  imageBuilder: (context, alt, url) =>
                      _buildMarkdownImage(alt, url, palette),
                ),
              ),
            ],
          ),
        ),
        _buildNoteSaveBottomBar(palette: palette),
      ],
    );
  }

  Widget _buildNotePreviewHeader(
    NotePreview preview,
    AppThemePalette palette,
  ) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.panelBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.check_circle_rounded,
                  color: palette.primary, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '笔记整理完成',
                  style: TextStyle(
                    color: palette.textMain,
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            preview.displayTitle,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 18,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _buildTag(preview.displaySubject, palette),
              ...preview.knowledgeTags.map((tag) => _buildTag(tag, palette)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMarkdownImage(
    String alt,
    String url,
    AppThemePalette palette,
  ) {
    final image = _loadProtectedImage(_resolveImageUrl(url));
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(minHeight: 120, maxHeight: 260),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: palette.imageBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: palette.panelBorder),
      ),
      child: image == null
          ? _CompareImagePlaceholder(
              text: alt.trim().isEmpty ? '图片' : alt.trim(),
              textColor: palette.textSub,
            )
          : _ProtectedImage(
              image: image,
              fit: BoxFit.contain,
              placeholderText: alt.trim().isEmpty ? '图片' : alt.trim(),
              textColor: palette.textSub,
            ),
    );
  }

  Widget _buildSplitSummary(AppThemePalette palette) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.panelBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.check_circle_rounded,
                color: palette.primary,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '成功分割 ${_splitQuestions.length} 道题目',
                  style: TextStyle(
                    color: palette.textMain,
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          if (_splitWarnings.isNotEmpty) ...[
            const SizedBox(height: 8),
            ..._splitWarnings.map(
              (warning) => Text(
                warning,
                style: TextStyle(
                  color: palette.errorText,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSplitQuestionCard({
    required SplitQuestion question,
    required int index,
    required AppThemePalette palette,
    required bool selected,
    required VoidCallback onToggle,
  }) {
    final imageUrls = _imageUrlsForQuestion(question);

    return GestureDetector(
      onTap: onToggle,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected
              ? palette.primary.withOpacity(palette.isLight ? 0.07 : 0.11)
              : palette.panelBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected
                ? palette.primary.withOpacity(0.45)
                : palette.panelBorder,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 30,
                  height: 30,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: palette.primary.withOpacity(0.14),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    question.questionId.isEmpty
                        ? '${index + 1}'
                        : question.questionId,
                    style: TextStyle(
                      color: palette.primary,
                      fontWeight: FontWeight.w900,
                      fontSize: 12,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        question.questionType ?? '题目',
                        style: TextStyle(
                          color: palette.textMain,
                          fontSize: 14,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      if (question.sectionTitle != null &&
                          question.sectionTitle!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            question.sectionTitle!,
                            style: TextStyle(
                              color: palette.textSub,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                _SelectionBadge(selected: selected, palette: palette),
              ],
            ),
            const SizedBox(height: 12),
            ...question.contentBlocks
                .where((block) => block.content.trim().isNotEmpty)
                .map((block) => block.isImage
                    ? Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _buildMarkdownImage(
                          '题目图片',
                          block.content,
                          palette,
                        ),
                      )
                    : _buildSplitTextBlock(block, palette)),
            if (imageUrls.isNotEmpty) ...[
              const SizedBox(height: 10),
              _buildSplitImages(imageUrls, palette),
            ],
            if (question.options.isNotEmpty) ...[
              const SizedBox(height: 10),
              ...List.generate(
                question.options.length,
                (optionIndex) => _buildSplitOption(
                  option: question.options[optionIndex],
                  optionImage: optionIndex < question.optionImages.length
                      ? question.optionImages[optionIndex]
                      : null,
                  palette: palette,
                ),
              ),
            ],
            if (question.knowledgeTags.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: question.knowledgeTags
                    .map((tag) => _buildTag(tag, palette))
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSplitTextBlock(
    SplitQuestionBlock block,
    AppThemePalette palette,
  ) {
    if (block.content.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: MarkdownMathText(
        text: block.content,
        palette: palette,
        style: TextStyle(
          color: palette.textMain,
          fontSize: 13,
          height: 1.55,
          fontWeight: FontWeight.w600,
        ),
        imageBuilder: (context, alt, url) =>
            _buildMarkdownImage(alt, url, palette),
      ),
    );
  }

  Widget _buildSplitOption({
    required String option,
    required String? optionImage,
    required AppThemePalette palette,
  }) {
    final hasImage = optionImage != null && optionImage.trim().isNotEmpty;

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 7),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: palette.badgeBg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: palette.panelBorder),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (hasImage) ...[
            SizedBox(
              width: 136,
              child: _buildSplitImages([optionImage!], palette),
            ),
            const SizedBox(width: 10),
          ],
          Expanded(
            child: MarkdownMathText(
              text: option,
              palette: palette,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 12,
                height: 1.45,
                fontWeight: FontWeight.w600,
              ),
              imageBuilder: (context, alt, url) =>
                  _buildMarkdownImage(alt, url, palette),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSplitImages(
    List<String> imageUrls,
    AppThemePalette palette,
  ) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: imageUrls
          .map(
            (url) => Container(
              width: 128,
              height: 96,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: palette.imageBg,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: palette.panelBorder),
              ),
              child: _ProtectedImage(
                image: _loadProtectedImage(_resolveImageUrl(url))!,
                fit: BoxFit.contain,
                placeholderText: '图片',
                textColor: palette.textSub,
              ),
            ),
          )
          .toList(),
    );
  }

  Widget _buildTag(String tag, AppThemePalette palette) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: palette.primary.withOpacity(0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        tag,
        style: TextStyle(
          color: palette.primary,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  List<String> _imageUrlsForQuestion(SplitQuestion question) {
    final urls = <String>[];
    final embeddedUrls = _embeddedImageUrlsForQuestion(question);

    void add(String? url) {
      if (url == null || url.trim().isEmpty) {
        return;
      }
      final resolvedUrl = _resolveImageUrl(url) ?? url.trim();
      final duplicated = urls.any((existing) {
        return (_resolveImageUrl(existing) ?? existing.trim()) == resolvedUrl;
      });
      if (duplicated || embeddedUrls.contains(resolvedUrl)) {
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
      if (value == null || value.trim().isEmpty) {
        return;
      }
      urls.add(_resolveImageUrl(value) ?? value.trim());
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

  Widget _buildPageIndicator(
    AppThemePalette palette, {
    int? count,
  }) {
    final itemCount = count ?? _totalImages;
    return Container(
      alignment: Alignment.center,
      margin: const EdgeInsets.only(top: 6),
      child: Wrap(
        spacing: 6,
        children: List.generate(itemCount, (index) {
          final active = index == _currentPage;
          return InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: () => _goToPage(index, count: itemCount),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: active ? 32 : 12,
              height: 12,
              decoration: BoxDecoration(
                color:
                    active ? palette.primary : palette.textSub.withOpacity(0.3),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildPageSwitcher(
    AppThemePalette palette, {
    int? count,
  }) {
    final itemCount = count ?? _totalImages;
    return _buildPageIndicator(
      palette,
      count: itemCount,
    );
  }

  void _goToPage(int index, {int? count}) {
    final itemCount = count ?? _totalImages;
    if (itemCount <= 0) {
      return;
    }

    final nextPage = index.clamp(0, itemCount - 1);
    setState(() => _currentPage = nextPage);

    if (_pageController.hasClients) {
      _pageController.animateToPage(
        nextPage,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
      );
    }
  }

  Widget _buildExportBottomBar({
    required AppThemePalette palette,
  }) {
    final selectedCount = _selectedQuestionIds.length;
    final canImport =
        selectedCount > 0 && _splitRunId != null && _isImporting == false;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: palette.panelBorder)),
      ),
      alignment: Alignment.center,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 560),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: palette.isLight
              ? Colors.white.withOpacity(0.88)
              : const Color(0xFF18191E).withOpacity(0.96),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: palette.panelBorder),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(palette.isLight ? 0.08 : 0.24),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 42,
              height: 42,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: palette.primary,
                shape: BoxShape.circle,
              ),
              child: Text(
                '$selectedCount',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                  fontSize: 15,
                ),
              ),
            ),
            Container(
              height: 34,
              width: 1,
              margin: const EdgeInsets.symmetric(horizontal: 16),
              color: palette.panelBorder,
            ),
            ElevatedButton.icon(
              onPressed: canImport ? _openImportDialog : null,
              icon: _isImporting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.storage_rounded, size: 18),
              label: Text(_isImporting ? '处理中' : '导入错题库'),
              style: ElevatedButton.styleFrom(
                backgroundColor: palette.primary,
                disabledBackgroundColor: palette.primary.withOpacity(0.35),
                foregroundColor: Colors.white,
                disabledForegroundColor: Colors.white.withOpacity(0.68),
                elevation: 0,
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                textStyle: const TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
            const SizedBox(width: 10),
            OutlinedButton(
              onPressed: selectedCount == 0 || _isImporting
                  ? null
                  : _clearQuestionSelection,
              style: OutlinedButton.styleFrom(
                foregroundColor: palette.textMain,
                side: BorderSide(color: palette.panelBorder),
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                '清除',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNoteSaveBottomBar({
    required AppThemePalette palette,
  }) {
    final canSave = _notePreview != null && !_isImporting;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: palette.panelBorder)),
      ),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: _isImporting ? null : _startNoteOrganizeProcess,
              style: OutlinedButton.styleFrom(
                foregroundColor: palette.textMain,
                side: BorderSide(color: palette.panelBorder),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
              ),
              child: const Text(
                '重新整理',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: canSave ? _openSaveNoteDialog : null,
              icon: _isImporting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.menu_book_rounded, size: 18),
              label: Text(_isImporting ? '保存中' : '保存到笔记本'),
              style: ElevatedButton.styleFrom(
                backgroundColor: palette.primary,
                disabledBackgroundColor: palette.primary.withOpacity(0.35),
                foregroundColor: Colors.white,
                disabledForegroundColor: Colors.white.withOpacity(0.68),
                padding: const EdgeInsets.symmetric(vertical: 14),
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
                textStyle: const TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomActions({
    required AppThemePalette palette,
    required String leftText,
    required String rightText,
    required VoidCallback onLeft,
    required VoidCallback onRight,
  }) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: palette.panelBorder),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: onLeft,
              style: OutlinedButton.styleFrom(
                foregroundColor: palette.textMain,
                side: BorderSide(color: palette.panelBorder),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
              ),
              child: Text(
                leftText,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: ElevatedButton(
              onPressed: onRight,
              style: ElevatedButton.styleFrom(
                backgroundColor: palette.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
              ),
              child: Text(
                rightText,
                style: const TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyPaper({required AppThemePalette palette}) {
    return Container(
      width: 260,
      height: 360,
      decoration: BoxDecoration(
        color: palette.emptyPaper,
        borderRadius: BorderRadius.circular(4),
      ),
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: List.generate(12, (i) {
          return Container(
            margin: const EdgeInsets.only(bottom: 14),
            width: i % 3 == 0 ? 180 : 220,
            height: 8,
            color: palette.emptyPaperLine,
          );
        }),
      ),
    );
  }

  Future<Uint8List>? _loadProtectedImage(String? url) {
    if (url == null || url.trim().isEmpty) {
      return null;
    }
    return _imageFutures.putIfAbsent(
      url,
      () => _workspaceApi.loadProtectedImage(url),
    );
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

    final base = ApiClient.defaultBaseUrl;
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

class _SelectionBadge extends StatelessWidget {
  const _SelectionBadge({
    required this.selected,
    required this.palette,
  });

  final bool selected;
  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          selected ? '已选择' : '未选择',
          style: TextStyle(
            color: selected ? palette.primaryLight : palette.textSub,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(width: 8),
        AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          width: 26,
          height: 26,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? palette.primary : Colors.transparent,
            shape: BoxShape.circle,
            border: Border.all(
              color: selected ? palette.primary : palette.panelBorderStrong,
            ),
          ),
          child: selected
              ? const Icon(Icons.check_rounded, color: Colors.white, size: 18)
              : null,
        ),
      ],
    );
  }
}

class _ImportQuestionBankDialog extends StatefulWidget {
  const _ImportQuestionBankDialog({
    required this.palette,
    required this.projects,
    required this.selectedCount,
  });

  final AppThemePalette palette;
  final List<WorkspaceProject> projects;
  final int selectedCount;

  @override
  State<_ImportQuestionBankDialog> createState() =>
      _ImportQuestionBankDialogState();
}

class _ImportQuestionBankDialogState extends State<_ImportQuestionBankDialog> {
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
        constraints: const BoxConstraints(maxWidth: 600),
        child: Container(
          decoration: BoxDecoration(
            color: palette.isLight
                ? Colors.white
                : const Color(0xFF18191D).withOpacity(0.98),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: palette.panelBorderStrong),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(30, 24, 24, 18),
                child: Row(
                  children: [
                    Container(
                      width: 46,
                      height: 46,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: palette.primary.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        Icons.storage_rounded,
                        color: palette.primaryLight,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        '导入错题库',
                        style: TextStyle(
                          color: palette.textMain,
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(Icons.close_rounded, color: palette.textSub),
                    ),
                  ],
                ),
              ),
              Divider(height: 1, color: palette.panelBorderStrong),
              Padding(
                padding: const EdgeInsets.fromLTRB(30, 16, 30, 12),
                child: Text(
                  '将 ${widget.selectedCount} 道已选题目导入到:',
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(30, 0, 30, 16),
                  itemCount: widget.projects.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final project = widget.projects[index];
                    final selected = project.id == _selectedProject.id;
                    return _buildProjectOption(project, selected, palette);
                  },
                ),
              ),
              Divider(height: 1, color: palette.panelBorderStrong),
              Padding(
                padding: const EdgeInsets.fromLTRB(30, 20, 30, 20),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: palette.textMain,
                        side: BorderSide(color: palette.panelBorderStrong),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: const Text(
                        '取消',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton(
                      onPressed: () =>
                          Navigator.of(context).pop(_selectedProject),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: palette.primary,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
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
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => setState(() => _selectedProject = project),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: selected
              ? palette.primary.withOpacity(palette.isLight ? 0.11 : 0.16)
              : (palette.isLight
                  ? const Color(0xFFF7F7FB)
                  : const Color(0xFF202126)),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected
                ? palette.primary.withOpacity(0.72)
                : palette.panelBorderStrong,
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.storage_rounded,
              color: selected ? palette.primaryLight : palette.textSub,
              size: 20,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                project.displayName,
                style: TextStyle(
                  color: selected ? palette.primaryLight : palette.textMain,
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                ),
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

class _SaveNoteDialog extends StatefulWidget {
  const _SaveNoteDialog({
    required this.palette,
    required this.projects,
    required this.preview,
  });

  final AppThemePalette palette;
  final List<WorkspaceProject> projects;
  final NotePreview preview;

  @override
  State<_SaveNoteDialog> createState() => _SaveNoteDialogState();
}

class _SaveNoteDialogState extends State<_SaveNoteDialog> {
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
        constraints: const BoxConstraints(maxWidth: 600),
        child: Container(
          decoration: BoxDecoration(
            color: palette.isLight
                ? Colors.white
                : const Color(0xFF18191D).withOpacity(0.98),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: palette.panelBorderStrong),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(30, 24, 24, 18),
                child: Row(
                  children: [
                    Container(
                      width: 46,
                      height: 46,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: palette.primary.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        Icons.menu_book_rounded,
                        color: palette.primaryLight,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '保存笔记',
                            style: TextStyle(
                              color: palette.textMain,
                              fontSize: 24,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            widget.preview.displayTitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: palette.textSub,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(Icons.close_rounded, color: palette.textSub),
                    ),
                  ],
                ),
              ),
              Divider(height: 1, color: palette.panelBorderStrong),
              Padding(
                padding: const EdgeInsets.fromLTRB(30, 16, 30, 12),
                child: Text(
                  '选择要保存到的笔记本:',
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(30, 0, 30, 16),
                  itemCount: widget.projects.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final project = widget.projects[index];
                    final selected = project.id == _selectedProject.id;
                    return _buildProjectOption(project, selected, palette);
                  },
                ),
              ),
              Divider(height: 1, color: palette.panelBorderStrong),
              Padding(
                padding: const EdgeInsets.fromLTRB(30, 20, 30, 20),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: palette.textMain,
                        side: BorderSide(color: palette.panelBorderStrong),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: const Text(
                        '取消',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton(
                      onPressed: () =>
                          Navigator.of(context).pop(_selectedProject),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: palette.primary,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: const Text(
                        '确认保存',
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
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => setState(() => _selectedProject = project),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: selected
              ? palette.primary.withOpacity(palette.isLight ? 0.11 : 0.16)
              : (palette.isLight
                  ? const Color(0xFFF7F7FB)
                  : const Color(0xFF202126)),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected
                ? palette.primary.withOpacity(0.72)
                : palette.panelBorderStrong,
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.menu_book_rounded,
              color: selected ? palette.primaryLight : palette.textSub,
              size: 20,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                project.displayName,
                style: TextStyle(
                  color: selected ? palette.primaryLight : palette.textMain,
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                ),
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

class _DisplayItem {
  const _DisplayItem({
    required this.fileKey,
    required this.fileName,
    this.beforeImageUrl,
    this.afterImageUrl,
  });

  final String fileKey;
  final String fileName;
  final String? beforeImageUrl;
  final String? afterImageUrl;
}

/// 擦除完成预览对比图（左右拖拽）
class EraseImageCompareViewer extends StatefulWidget {
  const EraseImageCompareViewer({
    super.key,
    required this.beforeImage,
    required this.afterImage,
    required this.placeholderText,
    this.backgroundColor = const Color(0xFF050517),
    this.dividerColor = const Color(0xFF8C78FF),
    this.textColor = Colors.white70,
  });

  final Future<Uint8List>? beforeImage;
  final Future<Uint8List>? afterImage;
  final String placeholderText;
  final Color backgroundColor;
  final Color dividerColor;
  final Color textColor;

  @override
  State<EraseImageCompareViewer> createState() =>
      _EraseImageCompareViewerState();
}

class _EraseImageCompareViewerState extends State<EraseImageCompareViewer> {
  late double _value;

  @override
  void initState() {
    super.initState();
    _value = 0.5;
  }

  void _updateValue(Offset localPosition, double width) {
    setState(() {
      _value = (localPosition.dx / width).clamp(0.0, 1.0);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: widget.backgroundColor,
      width: double.infinity,
      height: double.infinity,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final height = constraints.maxHeight;
          final dividerX = width * _value;

          return GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapDown: (details) {
              _updateValue(details.localPosition, width);
            },
            onHorizontalDragUpdate: (details) {
              _updateValue(details.localPosition, width);
            },
            child: Stack(
              alignment: Alignment.center,
              children: [
                _CompareImageLayer(
                  image: widget.beforeImage,
                  placeholderText: widget.placeholderText,
                  textColor: widget.textColor,
                ),
                Positioned.fill(
                  child: ClipPath(
                    clipper: _RightSideImageClipper(dividerX),
                    child: _CompareImageLayer(
                      image: widget.afterImage,
                      placeholderText: widget.placeholderText,
                      textColor: widget.textColor,
                    ),
                  ),
                ),
                Positioned(
                  left: dividerX - 1,
                  top: 0,
                  bottom: 0,
                  child: Container(
                    width: 2,
                    color: widget.dividerColor,
                  ),
                ),
                Positioned(
                  left: dividerX - 28,
                  top: height * 0.5 - 28,
                  child: _DragHandle(color: widget.dividerColor),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _RightSideImageClipper extends CustomClipper<Path> {
  const _RightSideImageClipper(this.dividerX);

  final double dividerX;

  @override
  Path getClip(Size size) {
    return Path()..addRect(Rect.fromLTRB(dividerX, 0, size.width, size.height));
  }

  @override
  bool shouldReclip(covariant _RightSideImageClipper oldClipper) {
    return oldClipper.dividerX != dividerX;
  }
}

class _CompareImageLayer extends StatelessWidget {
  const _CompareImageLayer({
    required this.image,
    required this.placeholderText,
    required this.textColor,
  });

  final Future<Uint8List>? image;
  final String placeholderText;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(36, 36, 36, 80),
      child: Center(
        child: image == null
            ? _CompareImagePlaceholder(
                text: placeholderText,
                textColor: textColor,
              )
            : _ProtectedImage(
                image: image!,
                fit: BoxFit.contain,
                placeholderText: placeholderText,
                textColor: textColor,
              ),
      ),
    );
  }
}

class _CompareImagePlaceholder extends StatelessWidget {
  const _CompareImagePlaceholder({
    required this.text,
    required this.textColor,
  });

  final String text;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints.expand(),
      alignment: Alignment.center,
      color: const Color(0xFF050517).withOpacity(0.55),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF11131A).withOpacity(0.8),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 12,
          ).copyWith(color: textColor),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}

class _ProtectedImage extends StatelessWidget {
  const _ProtectedImage({
    required this.image,
    required this.fit,
    required this.placeholderText,
    required this.textColor,
  });

  final Future<Uint8List> image;
  final BoxFit fit;
  final String placeholderText;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Uint8List>(
      future: image,
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          return Image.memory(snapshot.data!, fit: fit);
        }

        if (snapshot.hasError) {
          return _CompareImagePlaceholder(
            text: '图片加载失败',
            textColor: textColor,
          );
        }

        return Stack(
          alignment: Alignment.center,
          children: [
            _CompareImagePlaceholder(
              text: placeholderText,
              textColor: textColor,
            ),
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ],
        );
      },
    );
  }
}

class _DragHandle extends StatelessWidget {
  const _DragHandle({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.35),
            blurRadius: 24,
            spreadRadius: 4,
          ),
        ],
      ),
      child: const Icon(
        Icons.swap_horiz_rounded,
        color: Colors.white,
        size: 28,
      ),
    );
  }
}

/// OCR 完成页面里的 OCR 标注图区域
class _OcrAnnotatedFrame extends StatelessWidget {
  const _OcrAnnotatedFrame({
    required this.image,
    required this.title,
    required this.page,
    required this.fallback,
    required this.palette,
  });

  final Future<Uint8List>? image;
  final String title;
  final OcrPage? page;
  final Widget fallback;
  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    final pageWidth = page?.pageWidth ?? 1;
    final pageHeight = page?.pageHeight ?? 1;
    final aspectRatio =
        pageWidth > 0 && pageHeight > 0 ? pageWidth / pageHeight : 0.74;

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 18, 12, 58),
      child: Center(
        child: AspectRatio(
          aspectRatio: aspectRatio,
          child: Stack(
            fit: StackFit.expand,
            children: [
              image == null
                  ? FittedBox(fit: BoxFit.contain, child: fallback)
                  : _ProtectedImage(
                      image: image!,
                      fit: BoxFit.contain,
                      placeholderText: title,
                      textColor: palette.textSub,
                    ),
              
              Positioned.fill(
                child: CustomPaint(
                  painter: _OcrBoxPainter(
                    isLight: palette.isLight,
                    page: page,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OcrBoxPainter extends CustomPainter {
  const _OcrBoxPainter({
    required this.isLight,
    required this.page,
  });

  final bool isLight;
  final OcrPage? page;

  @override
  void paint(Canvas canvas, Size size) {
    final ocrPage = page;
    if (ocrPage == null ||
        ocrPage.blocks.isEmpty ||
        ocrPage.pageWidth <= 0 ||
        ocrPage.pageHeight <= 0) {
      return;
    }

    final scaleX = size.width / ocrPage.pageWidth;
    final scaleY = size.height / ocrPage.pageHeight;

    void rect({
      required Rect rect,
      required Color color,
      required String label,
    }) {
      final fill = Paint()..color = color.withOpacity(0.10);
      final stroke = Paint()
        ..color = color.withOpacity(0.9)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2;

      canvas.drawRect(rect, fill);
      canvas.drawRect(rect, stroke);

      final textPainter = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            color: Colors.white,
            backgroundColor: color.withOpacity(0.95),
            fontSize: 9,
            fontWeight: FontWeight.w800,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(canvas, Offset(rect.left, rect.top - 13));
    }

    for (final block in ocrPage.blocks) {
      if (!block.hasValidBox) {
        continue;
      }

      final box = block.bbox;
      final left = box[0] * scaleX;
      final top = box[1] * scaleY;
      final right = box[2] * scaleX;
      final bottom = box[3] * scaleY;
      rect(
        rect: Rect.fromLTRB(left, top, right, bottom),
        color: _colorForLabel(block.label),
        label: block.label,
      );
    }
  }

  Color _colorForLabel(String label) {
    final normalized = label.toLowerCase();
    if (normalized.contains('table')) {
      return isLight ? const Color(0xFFFF5CA6) : const Color(0xFFFF66B3);
    }
    if (normalized.contains('image')) {
      return isLight ? const Color(0xFF23C882) : const Color(0xFF35D98B);
    }
    if (normalized.contains('formula')) {
      return isLight ? const Color(0xFF8090A4) : const Color(0xFF9EA6B8);
    }
    if (normalized.contains('title')) {
      return isLight ? const Color(0xFF8C6CFF) : const Color(0xFFB39DFF);
    }
    if (normalized.contains('number')) {
      return isLight ? const Color(0xFFFF8A3D) : const Color(0xFFFFA15C);
    }
    if (normalized.contains('header') || normalized.contains('aside')) {
      return isLight ? const Color(0xFF607D8B) : const Color(0xFF90A4AE);
    }
    return isLight ? const Color(0xFF3B77F7) : const Color(0xFF4C8DFF);
  }

  @override
  bool shouldRepaint(covariant _OcrBoxPainter oldDelegate) {
    return oldDelegate.isLight != isLight || oldDelegate.page != page;
  }
}

class _PulseRingPainter extends CustomPainter {
  const _PulseRingPainter({
    required this.t,
    required this.color,
  });

  final double t;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);

    for (int i = 0; i < 3; i++) {
      final localT = (t + i * 0.24) % 1.0;
      final radius = 38 + localT * 48;
      final opacity = (1 - localT).clamp(0.0, 1.0);

      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2
        ..color = color.withOpacity(0.34 * opacity);

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _PulseRingPainter oldDelegate) {
    return oldDelegate.t != t || oldDelegate.color != color;
  }
}
