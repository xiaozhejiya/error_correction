import 'dart:async';

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../data/workspace_api.dart';
import 'split_history_page.dart';
import 'smart_input_process_page.dart';

import '../../../../core/network/api_client.dart';

class SmartInputPage extends StatefulWidget {
  const SmartInputPage({super.key});

  @override
  State<SmartInputPage> createState() => _SmartInputPageState();
}

class _SmartInputPageState extends State<SmartInputPage> {
  _SmartInputMode _mode = _SmartInputMode.examSplit;
  bool _eraseHandwriting = true;
  String? _selectedModelOptionId;
  _ModelSource? _selectedModelSource;
  bool _isUploading = false;
  final List<_UploadedFile> _files = [];
  bool _isLoadingModels = true;
  String? _modelError;
  final Set<String> _deletingFileKeys = {};
  int _uploadGeneration = 0;

  late final WorkspaceApi _workspaceApi;
  final List<WorkspaceModelOption> _hostedModels = [];
  final List<WorkspaceModelOption> _selfModels = [];

  List<WorkspaceModelOption> get _availableHostOptions =>
      _hostedModels.where((item) => item.configured).toList();

  List<WorkspaceModelOption> get _availableSelfOptions =>
      _selfModels.where((item) => item.configured).toList();

  @override
  void initState() {
    super.initState();
    _workspaceApi = WorkspaceApi();
    _fetchModelOptions();
  }

  @override
  void dispose() {
    final filesToCancel = List<_UploadedFile>.of(_files);
    _files.clear();
    _deletingFileKeys.clear();
    if (filesToCancel.isNotEmpty) {
      unawaited(_cancelUploadedFiles(filesToCancel));
    }
    super.dispose();
  }

  Future<void> _fetchModelOptions() async {
    setState(() {
      _isLoadingModels = true;
      _modelError = null;
    });

    try {
      final response = await _workspaceApi.getModelOptions();
      if (!mounted) {
        return;
      }

      final available =
          response.options.where((option) => option.configured).toList();
      final hosted = available
          .where((option) => option.isHostedSource)
          .toList(growable: false);
      final self = available
          .where((option) => option.isSelfSource)
          .toList(growable: false);
      final fallback = available
          .where((option) => !option.isHostedSource && !option.isSelfSource)
          .toList(growable: false);
      if (fallback.isNotEmpty) {
        self.addAll(fallback);
      }

      final defaultOptionId = response.defaultOptionId;
      WorkspaceModelOption? initialOption = defaultOptionId == null
          ? null
          : _findOptionById(available, defaultOptionId);

      initialOption ??= _findDefaultOrFirstOption(available);

      if (initialOption == null) {
        _hostedModels.clear();
        _selfModels.clear();
        _selectedModelOptionId = null;
        _selectedModelSource = null;
      } else {
        _hostedModels
          ..clear()
          ..addAll(hosted);
        _selfModels
          ..clear()
          ..addAll(self);

        _selectedModelOptionId = initialOption.optionId;
        _selectedModelSource = initialOption.isHostedSource
            ? _ModelSource.hosted
            : _ModelSource.self;
      }
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      _hostedModels.clear();
      _selfModels.clear();
      _selectedModelOptionId = null;
      _selectedModelSource = null;
      _modelError = error.message;
    } catch (_) {
      if (!mounted) {
        return;
      }
      _hostedModels.clear();
      _selfModels.clear();
      _selectedModelOptionId = null;
      _selectedModelSource = null;
      _modelError = '模型列表加载失败，请稍后再试';
    } finally {
      if (mounted) {
        setState(() => _isLoadingModels = false);
      }
    }
  }

  Future<void> _openSplitHistory() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SplitHistoryPage(workspaceApi: _workspaceApi),
      ),
    );
  }

  WorkspaceModelOption? _findOptionById(
    List<WorkspaceModelOption> options,
    String optionId,
  ) {
    for (final option in options) {
      if (option.optionId == optionId) {
        return option;
      }
    }
    return null;
  }

  WorkspaceModelOption? _findDefaultOrFirstOption(
    List<WorkspaceModelOption> options,
  ) {
    for (final option in options) {
      if (option.isDefault) {
        return option;
      }
    }

    if (options.isNotEmpty) {
      return options.first;
    }

    return null;
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);
    final isLight = palette.isLight;
    final pageText = palette.textMain;
    final helperText = palette.textSub;
    final border = palette.panelBorder;
    final panelBg = palette.panelBg;
    final cardBg = palette.cardBg;

    final steps = _steps;
    final titles = _mode == _SmartInputMode.examSplit
        ? ('智能录入与分析工作台', _examDescription)
        : ('智能笔记整理工作台', _noteDescription);

    return Stack(
      children: [
        Positioned.fill(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
            child: SingleChildScrollView(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1100),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildTopBar(
                      isLight: isLight,
                      titleColor: pageText,
                      helperText: helperText,
                      border: border,
                      panelBg: panelBg,
                    ),
                    const SizedBox(height: 14),
                    _buildModeAndEraseSwitch(
                      pageText: pageText,
                      border: border,
                      isLight: isLight,
                      panelBg: panelBg,
                      palette: palette,
                    ),
                    const SizedBox(height: 14),
                    _buildStepper(
                      steps: steps,
                      isLight: isLight,
                      pageText: pageText,
                      helperText: helperText,
                      border: border,
                      panelBg: panelBg,
                    ),
                    const SizedBox(height: 32),
                    _buildHeroTitle(
                      title: titles.$1,
                      description: titles.$2,
                      pageText: pageText,
                      helperText: helperText,
                    ),
                    const SizedBox(height: 14),
                    _buildFeatureCards(
                      cards: _mode == _SmartInputMode.examSplit
                          ? _examFeatureCards
                          : _noteFeatureCards,
                      isLight: isLight,
                      pageText: pageText,
                      helperText: helperText,
                      border: border,
                      panelBg: panelBg,
                    ),
                    const SizedBox(height: 14),
                    _buildUploadPanel(
                      isLight: isLight,
                      helperText: helperText,
                      panelBg: panelBg,
                      border: border,
                      onTap: _pickAndUploadFiles,
                    ),
                    const SizedBox(height: 12),
                    if (_files.isNotEmpty)
                      _buildFileCards(
                        files: _files,
                        cardBg: cardBg,
                        border: border,
                        helperText: helperText,
                        onRemove: _removeFile,
                      ),
                    const SizedBox(height: 12),
                    _buildPrimaryActionButton(
                      isLight: isLight,
                      helperText: helperText,
                      border: border,
                      panelBg: panelBg,
                    ),
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTopBar({
    required bool isLight,
    required Color titleColor,
    required Color helperText,
    required Color border,
    required Color panelBg,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 460;

        final selector = _ModelSelector(
          isLight: isLight,
          isLoading: _isLoadingModels,
          selectedModelId: _selectedModelOptionId,
          selectedModelName: _selectedModelDisplayName,
          selectedSource: _selectedModelSource,
          hosted: _availableHostOptions,
          self: _availableSelfOptions,
          modelError: _modelError,
          panelBg: panelBg,
          border: border,
          onPickHosted: (option) {
            setState(() {
              _selectedModelOptionId = option.optionId;
              _selectedModelSource = _ModelSource.hosted;
            });
          },
          onPickSelf: (option) {
            setState(() {
              _selectedModelOptionId = option.optionId;
              _selectedModelSource = _ModelSource.self;
            });
          },
          onPickSettings: () {
            _showHint('API 设置入口预留');
          },
          onPickEmpty: () {
            _showHint('暂无可用模型');
          },
        );

        if (compact) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  '智能录入与分析',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: titleColor,
                    fontWeight: FontWeight.w800,
                    fontSize: 22,
                  ),
                ),
              ),
              _SplitHistoryButton(
                isLight: isLight,
                panelBg: panelBg,
                border: border,
                helperText: helperText,
                compact: true,
                onTap: _openSplitHistory,
              ),
              const SizedBox(width: 8),
              selector,
            ],
          );
        }

        return Row(
          children: [
            Text(
              '智能录入与分析',
              style: TextStyle(
                color: titleColor,
                fontWeight: FontWeight.w800,
                fontSize: 22,
              ),
            ),
            const Spacer(),
            _SplitHistoryButton(
              isLight: isLight,
              panelBg: panelBg,
              border: border,
              helperText: helperText,
              compact: false,
              onTap: _openSplitHistory,
            ),
            const SizedBox(width: 10),
            selector,
          ],
        );
      },
    );
  }

  Widget _buildStepper({
    required List<String> steps,
    required bool isLight,
    required Color pageText,
    required Color helperText,
    required Color border,
    required Color panelBg,
  }) {
    final active = _files.isNotEmpty ? 0 : -1;

    return Container(
      decoration: BoxDecoration(
        color: panelBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: List.generate(steps.length, (index) {
          final isActive = index == active;
          final isDone = index < active;
          final hasPassed = index < active;
          final isLast = index == steps.length - 1;

          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _StepNode(
                index: index + 1,
                label: steps[index],
                isActive: isActive,
                isDone: isDone,
                isLight: isLight,
                pageText: pageText,
                helperText: helperText,
              ),
              if (!isLast) ...[
                const SizedBox(width: 8),
                Container(
                  width: 18,
                  height: 1,
                  color: hasPassed
                      ? AppTheme.primary.withOpacity(0.7)
                      : helperText.withOpacity(0.3),
                ),
              ],
            ],
          );
        }),
      ),
    );
  }

  Widget _buildModeAndEraseSwitch({
    required Color pageText,
    required Color border,
    required bool isLight,
    required Color panelBg,
    required AppThemePalette palette,
  }) {
    final Color selectedBg = isLight
        ? AppTheme.primary.withOpacity(0.14)
        : AppTheme.primary.withOpacity(0.9);

    final Color selectedText = isLight ? AppTheme.primary : Colors.white;

    final Color inactiveText =
        isLight ? pageText.withOpacity(0.5) : pageText.withOpacity(0.42);

    final Color dividerColor = border.withOpacity(isLight ? 0.45 : 0.35);

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            height: 42,
            decoration: BoxDecoration(
              color: panelBg,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: border,
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildModeTab(
                  mode: _SmartInputMode.examSplit,
                  label: '试卷分割',
                  icon: Icons.description_rounded,
                  selectedBg: selectedBg,
                  selectedText: selectedText,
                  inactiveText: inactiveText,
                  isLight: isLight,
                ),
                const SizedBox(width: 3),
                _buildModeTab(
                  mode: _SmartInputMode.noteOrganize,
                  label: '笔记整理',
                  icon: Icons.menu_book_rounded,
                  selectedBg: selectedBg,
                  selectedText: selectedText,
                  inactiveText: inactiveText,
                  isLight: isLight,
                ),
              ],
            ),
          ),
          if (_canEraseHandwriting) ...[
            const SizedBox(width: 14),
            Container(
              width: 1,
              height: 22,
              color: dividerColor,
            ),
            const SizedBox(width: 14),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildCompactSwitch(
                  value: _eraseHandwriting,
                  palette: palette,
                  onChanged: (value) {
                    setState(() {
                      _eraseHandwriting = value;
                    });
                  },
                ),
                const SizedBox(width: 8),
                Text(
                  '擦除笔迹',
                  style: TextStyle(
                    color: _eraseHandwriting
                        ? pageText.withOpacity(0.78)
                        : pageText.withOpacity(0.48),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    height: 1,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCompactSwitch({
    required bool value,
    required AppThemePalette palette,
    required ValueChanged<bool> onChanged,
  }) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => onChanged(!value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        width: 34,
        height: 20,
        padding: const EdgeInsets.all(2),
        decoration: BoxDecoration(
          color: value ? AppTheme.primary : palette.controlInactiveBg,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: value
                ? AppTheme.primary.withOpacity(0.85)
                : palette.subtleOverlay,
            width: 1,
          ),
        ),
        child: AnimatedAlign(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          alignment: value ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.22),
                  blurRadius: 4,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildModeTab({
    required _SmartInputMode mode,
    required String label,
    required IconData icon,
    required Color selectedBg,
    required Color selectedText,
    required Color inactiveText,
    required bool isLight,
  }) {
    final bool selected = _mode == mode;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: () => _switchMode(mode),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          height: 42,
          padding: const EdgeInsets.symmetric(horizontal: 13),
          decoration: BoxDecoration(
            color: selected ? selectedBg : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
            boxShadow: selected && !isLight
                ? [
                    BoxShadow(
                      color: AppTheme.primary.withOpacity(0.28),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 15,
                color: selected ? selectedText : inactiveText,
              ),
              const SizedBox(width: 5),
              Text(
                label,
                style: TextStyle(
                  color: selected ? selectedText : inactiveText,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  height: 1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeroTitle({
    required String title,
    required String description,
    required Color pageText,
    required Color helperText,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        RichText(
          text: TextSpan(
            children: [
              TextSpan(
                text: title.split('工作台').first,
                style: TextStyle(
                  color: pageText,
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const TextSpan(
                text: '工作台',
                style: TextStyle(
                  color: AppTheme.primary,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Text(
          description,
          style: TextStyle(
            color: helperText,
            fontSize: 14,
            height: 1.45,
          ),
        ),
      ],
    );
  }

  Widget _buildFeatureCards({
    required List<_FeatureItem> cards,
    required bool isLight,
    required Color pageText,
    required Color helperText,
    required Color panelBg,
    required Color border,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;

        final int crossAxisCount = width >= 900 ? 4 : 2;

        const double gap = 12;
        final double itemWidth =
            (width - gap * (crossAxisCount - 1)) / crossAxisCount;

        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: cards.map((card) {
            return SizedBox(
              width: itemWidth,
              child: Container(
                alignment: Alignment.center,
                padding: const EdgeInsets.all(14),
                constraints: const BoxConstraints(
                  minHeight: 108,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: border,
                  ),
                  color: panelBg,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withOpacity(
                          isLight ? 0.13 : 0.22,
                        ),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: AppTheme.primary.withOpacity(
                            isLight ? 0.08 : 0.18,
                          ),
                        ),
                      ),
                      child: Icon(
                        card.icon,
                        size: 18,
                        color:
                            isLight ? AppTheme.primary : AppTheme.primaryLight,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      card.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: pageText,
                        fontSize: width < 360 ? 13 : 14,
                        fontWeight: FontWeight.w800,
                        height: 1.25,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        );
      },
    );
  }

  Widget _buildUploadPanel({
    required bool isLight,
    required Color helperText,
    required Color panelBg,
    required Color border,
    required Future<void> Function() onTap,
  }) {
    final canPick = !_isUploading && _hasSelectedModel;
    final disabledText = _isUploading ? '正在上传...' : '当前暂无可用模型，上传功能暂时不可用';

    return InkWell(
      onTap: canPick ? () => onTap() : null,
      borderRadius: BorderRadius.circular(14),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        height: 170,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: border,
          ),
          color: panelBg,
        ),
        child: Center(
          child: canPick
              ? Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.cloud_upload_rounded,
                      size: 40,
                      color: isLight ? AppTheme.primary : AppTheme.primaryLight,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '点击上传文件',
                      style: TextStyle(
                        color: helperText,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '浏览文件',
                      style: TextStyle(
                        color:
                            isLight ? AppTheme.primary : AppTheme.primaryLight,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'PDF, PNG, JPG',
                      style: TextStyle(
                        color: helperText,
                        fontSize: 12,
                      ),
                    ),
                  ],
                )
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    disabledText,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: helperText,
                      fontSize: 14,
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  Widget _buildFileCards({
    required List<_UploadedFile> files,
    required Color cardBg,
    required Color border,
    required Color helperText,
    required Future<void> Function(_UploadedFile) onRemove,
  }) {
    final palette = AppThemePalette.of(context);
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: files
          .map(
            (file) => Container(
              width: 280,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: border),
              ),
              child: Row(
                children: [
                  if (_deletingFileKeys.contains(file.fileKey))
                    Padding(
                      padding: const EdgeInsets.only(left: 4),
                      child: const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  else
                    Icon(
                      _iconForFile(file.name),
                      color: AppTheme.primary,
                    ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          file.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: palette.textMain,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 6),
                        LinearProgressIndicator(
                          value: file.progress / 100,
                          minHeight: 4,
                          backgroundColor: palette.progressTrack,
                          valueColor: const AlwaysStoppedAnimation<Color>(
                            AppTheme.primary,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${file.progress.toInt()}%',
                          style: TextStyle(color: helperText, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: '删除',
                    iconSize: 18,
                    icon: const Icon(Icons.close_rounded),
                    onPressed: _deletingFileKeys.contains(file.fileKey) ||
                            file.fileKey.isEmpty
                        ? null
                        : () => onRemove(file),
                    color: helperText,
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }

  Widget _buildPrimaryActionButton({
    required bool isLight,
    required Color helperText,
    required Color border,
    required Color panelBg,
  }) {
    final canStart = _hasSelectedModel && _files.isNotEmpty;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        TextButton(
          onPressed: canStart ? _onPrimaryAction : null,
          style: TextButton.styleFrom(
            padding: EdgeInsets.zero,
            backgroundColor: panelBg,
            disabledBackgroundColor: panelBg,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            side: BorderSide(color: border),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: canStart
                ? DecoratedBox(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [AppTheme.primary, AppTheme.primaryLight],
                      ),
                    ),
                    child: Container(
                      alignment: Alignment.center,
                      height: 50,
                      width: double.infinity,
                      child: _buildPrimaryActionLabel(
                        active: true,
                      ),
                    ),
                  )
                : Container(
                    alignment: Alignment.center,
                    height: 50,
                    width: double.infinity,
                    child: _buildPrimaryActionLabel(
                      active: false,
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildPrimaryActionLabel({
    required bool active,
  }) {
    return Text(
      _primaryButtonLabel,
      style: TextStyle(
        color: active ? Colors.white : AppThemePalette.of(context).textSub,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  Future<void> _onPrimaryAction() async {
    if (!_hasSelectedModel) {
      _showHint('当前暂无可用模型，请先完成 API 设置');
      return;
    }
    if (_files.isEmpty) {
      _showHint('请先上传文件');
      return;
    }

    if (!mounted) {
      return;
    }

    final finished = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (routeContext) => SmartInputProcessPage(
          files: _files
              .map(
                (item) => SmartInputUploadedFile(
                  fileKey: item.fileKey,
                  name: item.name,
                  bytes: item.bytes,
                ),
              )
              .toList(growable: false),
          enableQuestionSplit: _mode == _SmartInputMode.examSplit,
          splitRequest: _buildSplitRequest(),
          initialEraseHandwriting: _effectiveEraseHandwriting,
          onConfirmSplit: () {
            Navigator.of(routeContext).pop(true);
          },
        ),
      ),
    );

    if (!mounted) {
      return;
    }

    if (_files.isNotEmpty) {
      setState(_clearLocalFiles);
    }

    if (finished == true) {
      _showHint(
        _mode == _SmartInputMode.noteOrganize ? '笔记整理已完成' : '分割已完成',
      );
    }
  }

  Future<void> _pickAndUploadFiles() async {
    if (!_hasSelectedModel) {
      _showHint('请先在模型配置完成后再上传');
      return;
    }

    FilePickerResult? result;
    try {
      result = await FilePicker.pickFiles(
        allowMultiple: true,
        withData: true,
        type: FileType.custom,
        allowedExtensions: const ['pdf', 'png', 'jpg', 'jpeg'],
      );
    } catch (error) {
      _showHint('选择文件失败：$error');
      return;
    }

    if (result == null || result.files.isEmpty) {
      return;
    }

    final selectedFiles = result.files
        .where((file) => file.bytes != null && file.bytes!.isNotEmpty)
        .toList();

    if (selectedFiles.isEmpty) {
      _showHint('未检测到可上传文件内容');
      return;
    }

    final uploadGeneration = _uploadGeneration;

    setState(() {
      _isUploading = true;
    });

    try {
      final uploadItems = selectedFiles
          .map((file) => UploadFileItem(
                filename: file.name,
                bytes: file.bytes!,
              ))
          .toList();

      final response = await _workspaceApi.uploadFiles(
        files: uploadItems,
        resetSession: _files.isEmpty,
      );

      if (!mounted || uploadGeneration != _uploadGeneration) {
        return;
      }

      if (!response.success) {
        _showHint(response.message);
        return;
      }

      for (var i = 0; i < response.result.files.length; i++) {
        final item = response.result.files[i];
        final uploadItem =
            uploadItems[i < uploadItems.length ? i : uploadItems.length - 1];
        _files.add(
          _UploadedFile(
            name: item.filename,
            fileKey: item.fileKey,
            bytes: uploadItem.bytes,
            progress: 100,
          ),
        );
      }

      _showHint(
        response.result.files.length == 1
            ? '上传成功：${response.result.files.first.filename}'
            : '上传成功：${response.result.files.length} 个文件',
      );
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      _showHint(error.message);
    } catch (_) {
      if (!mounted) {
        return;
      }
      _showHint('上传失败，请稍后重试');
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  IconData _iconForFile(String name) {
    final lower = name.toLowerCase();
    if (lower.endsWith('.pdf')) {
      return Icons.picture_as_pdf_outlined;
    }
    if (lower.endsWith('.png') || lower.endsWith('.jpg')) {
      return Icons.image_outlined;
    }
    return Icons.insert_drive_file_outlined;
  }

  Future<void> _removeFile(_UploadedFile target) async {
    if (_deletingFileKeys.contains(target.fileKey)) {
      return;
    }

    if (target.fileKey.isEmpty) {
      setState(() => _files.remove(target));
      return;
    }

    setState(() {
      _deletingFileKeys.add(target.fileKey);
    });

    try {
      final response = await _workspaceApi.cancelUploadedFile(
        fileKey: target.fileKey,
      );

      if (!mounted) {
        return;
      }

      if (response.success) {
        setState(() {
          _files.removeWhere((item) => item.fileKey == target.fileKey);
        });
        _showHint('已移除：${target.name}');
      } else {
        _showHint(response.message);
      }
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      _showHint(error.message);
    } catch (_) {
      if (!mounted) {
        return;
      }
      _showHint('撤销失败，请稍后重试');
    } finally {
      if (mounted) {
        setState(() {
          _deletingFileKeys.remove(target.fileKey);
        });
      }
    }
  }

  void _showHint(String message) {
    if (!mounted) {
      return;
    }
    showAppSnackBar(context, message);
  }

  bool get _hasSelectedModel =>
      _selectedModelOptionId != null && _selectedModelDisplayName != null;

  WorkspaceModelOption? get _selectedModelOption {
    if (_selectedModelOptionId == null) {
      return null;
    }

    return _findOptionById(
      [..._availableHostOptions, ..._availableSelfOptions],
      _selectedModelOptionId!,
    );
  }

  String? get _selectedModelDisplayName {
    return _selectedModelOption?.displayName;
  }

  void _switchMode(_SmartInputMode mode) {
    if (_mode == mode) {
      return;
    }

    final filesToCancel = List<_UploadedFile>.of(_files);
    setState(() {
      _mode = mode;
      if (_mode == _SmartInputMode.noteOrganize) {
        _eraseHandwriting = false;
      }
      _clearLocalFiles();
    });

    if (filesToCancel.isNotEmpty) {
      unawaited(
        _cancelUploadedFiles(
          filesToCancel,
          showError: true,
        ),
      );
    }
  }

  void _clearLocalFiles() {
    _uploadGeneration++;
    _files.clear();
    _deletingFileKeys.clear();
    _isUploading = false;
  }

  Future<void> _cancelUploadedFiles(
    List<_UploadedFile> files, {
    bool showError = false,
  }) async {
    final fileKeys = files
        .map((file) => file.fileKey)
        .where((fileKey) => fileKey.isNotEmpty)
        .toSet()
        .toList(growable: false);
    if (fileKeys.isEmpty) {
      return;
    }

    try {
      await Future.wait(
        fileKeys.map(
          (fileKey) => _workspaceApi.cancelUploadedFile(fileKey: fileKey),
        ),
        eagerError: false,
      );
    } catch (_) {
      if (showError && mounted) {
        _showHint('部分文件撤销失败，请稍后重试');
      }
    }
  }

  SplitRequest? _buildSplitRequest() {
    final option = _selectedModelOption;
    if (option == null) {
      return null;
    }

    return SplitRequest(
      modelProvider: option.category.isNotEmpty ? option.category : 'openai',
      modelName: option.modelName.isNotEmpty ? option.modelName : null,
      providerSource: option.source.isNotEmpty ? option.source : null,
      providerId: option.providerId.isNotEmpty ? option.providerId : null,
    );
  }

  String get _primaryButtonLabel {
    if (_effectiveEraseHandwriting) {
      return '开始擦除笔迹';
    }
    return _mode == _SmartInputMode.examSplit ? '开始 OCR 识别' : '启动 AI 笔记整理';
  }

  List<String> get _steps {
    final base = switch (_mode) {
      _SmartInputMode.examSplit => const ['上传', 'OCR', '分割', '导出'],
      _SmartInputMode.noteOrganize => const ['上传', 'OCR', '整理', '保存'],
    };
    if (_effectiveEraseHandwriting) {
      return ['上传', '擦除', ...base.sublist(1)];
    }
    return base;
  }

  bool get _canEraseHandwriting => _mode == _SmartInputMode.examSplit;
  bool get _effectiveEraseHandwriting =>
      _canEraseHandwriting && _eraseHandwriting;

  String get _examDescription => '支持 PDF 和图片格式，AI 将自动完成 OCR 识别、题目分割和知识点标注';

  String get _noteDescription => '支持拍照或扫描件，AI 将自动识别内容并整理为结构化笔记';

  List<_FeatureItem> get _examFeatureCards => const [
        _FeatureItem(
          title: '上传文件',
          icon: Icons.upload_file_outlined,
        ),
        _FeatureItem(
          title: 'AI 识别',
          icon: Icons.auto_awesome_rounded,
        ),
        _FeatureItem(
          title: '分割纠错',
          icon: Icons.find_replace_outlined,
        ),
        _FeatureItem(
          title: '导出归档',
          icon: Icons.archive_outlined,
        ),
      ];

  List<_FeatureItem> get _noteFeatureCards => const [
        _FeatureItem(
          title: '上传笔记',
          icon: Icons.note_add_outlined,
        ),
        _FeatureItem(
          title: 'AI 识别',
          icon: Icons.auto_awesome_rounded,
        ),
        _FeatureItem(
          title: '智能整理',
          icon: Icons.format_list_bulleted,
        ),
        _FeatureItem(
          title: '保存笔记',
          icon: Icons.save_outlined,
        ),
      ];
}

enum _SmartInputMode {
  examSplit,
  noteOrganize,
}

enum _ModelSource {
  hosted,
  self,
}

class _UploadedFile {
  _UploadedFile({
    required this.name,
    required this.fileKey,
    required this.bytes,
    required this.progress,
  });

  final String name;
  final String fileKey;
  final List<int> bytes;
  double progress;
}

class _FeatureItem {
  const _FeatureItem({
    required this.title,
    required this.icon,
  });

  final String title;
  final IconData icon;
}

class _StepNode extends StatelessWidget {
  const _StepNode({
    required this.index,
    required this.label,
    required this.isActive,
    required this.isDone,
    required this.isLight,
    required this.pageText,
    required this.helperText,
  });

  final int index;
  final String label;
  final bool isActive;
  final bool isDone;
  final bool isLight;
  final Color pageText;
  final Color helperText;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircleAvatar(
          radius: 11,
          backgroundColor: isDone
              ? AppTheme.primary.withOpacity(0.25)
              : isActive
                  ? (isLight ? AppTheme.primary : AppTheme.primaryLight)
                  : Colors.transparent,
          foregroundColor: isDone
              ? AppTheme.primary
              : (isActive ? Colors.white : helperText),
          child: Text(
            '$index',
            style: const TextStyle(fontSize: 10),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            color: isActive
                ? pageText
                : helperText.withOpacity(isDone ? 0.9 : 0.65),
            fontSize: 12,
            fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

class _ModelSelector extends StatelessWidget {
  const _ModelSelector({
    required this.isLight,
    required this.isLoading,
    required this.selectedModelId,
    required this.selectedModelName,
    required this.selectedSource,
    required this.hosted,
    required this.self,
    required this.modelError,
    required this.onPickHosted,
    required this.onPickSelf,
    required this.onPickSettings,
    required this.onPickEmpty,
    required this.panelBg,
    required this.border,
  });

  final bool isLight;
  final bool isLoading;
  final String? selectedModelId;
  final String? selectedModelName;
  final _ModelSource? selectedSource;
  final List<WorkspaceModelOption> hosted;
  final List<WorkspaceModelOption> self;
  final String? modelError;
  final ValueChanged<WorkspaceModelOption> onPickHosted;
  final ValueChanged<WorkspaceModelOption> onPickSelf;
  final VoidCallback onPickSettings;
  final VoidCallback onPickEmpty;
  final Color panelBg;
  final Color border;

  static const String _apiSettingsValue = '__api_settings__';

  @override
  Widget build(BuildContext context) {
    final bool hasSelected = selectedModelId != null &&
        selectedModelName != null &&
        selectedModelName!.isNotEmpty;
    final bool hasModels = hosted.isNotEmpty || self.isNotEmpty;
    final allOptions = [...hosted, ...self];
    final palette = AppThemePalette(isLight: isLight);

    final Color triggerText = palette.textMain;
    final Color mutedText = palette.textSub;
    final Color menuBg = palette.menuBg;

    return PopupMenuButton<String>(
      tooltip: '模型选择',
      enabled: !isLoading,
      color: menuBg,
      elevation: 12,
      offset: const Offset(0, 10),
      constraints: const BoxConstraints(
        minWidth: 274,
        maxWidth: 320,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: palette.subtleOverlay,
        ),
      ),
      padding: EdgeInsets.zero,
      onSelected: (value) {
        if (value == _apiSettingsValue) {
          onPickSettings();
          return;
        }

        WorkspaceModelOption? selected;
        for (final option in allOptions) {
          if (option.optionId == value) {
            selected = option;
            break;
          }
        }

        if (selected == null) {
          onPickEmpty();
          return;
        }

        if (selected.isHostedSource) {
          onPickHosted(selected);
        } else {
          onPickSelf(selected);
        }
      },
      itemBuilder: (context) {
        if (isLoading) {
          return [
            PopupMenuItem<String>(
              enabled: false,
              height: 52,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: const [
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                      ),
                    ),
                    SizedBox(width: 10),
                    Text(
                      '模型加载中...',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ];
        }

        if (!hasModels) {
          return [
            PopupMenuItem<String>(
              enabled: false,
              height: 56,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Text(
                  modelError ?? '当前暂无可用模型',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: triggerText,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
            _buildDivider(palette),
            PopupMenuItem<String>(
              value: _apiSettingsValue,
              height: 46,
              padding: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Row(
                  children: [
                    Icon(
                      Icons.tune_rounded,
                      size: 18,
                      color: mutedText,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'API 设置',
                        style: TextStyle(
                          color: triggerText,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ];
        }

        return [
          _buildSectionTitle('平台托管', mutedText),
          for (final item in hosted)
            _buildModelItem(
              option: item,
              palette: palette,
              selected: selectedModelId == item.optionId &&
                  selectedSource == _ModelSource.hosted,
              showDefault: item.isDefault,
            ),
          _buildDivider(palette),
          _buildSectionTitle('自己设置', mutedText),
          for (final item in self)
            _buildModelItem(
              option: item,
              palette: palette,
              selected: selectedModelId == item.optionId &&
                  selectedSource == _ModelSource.self,
              showDefault: false,
            ),
          _buildDivider(palette),
          PopupMenuItem<String>(
            value: _apiSettingsValue,
            height: 46,
            padding: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(
                children: [
                  Icon(
                    Icons.tune_rounded,
                    size: 18,
                    color: mutedText,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'API 设置',
                      style: TextStyle(
                        color: triggerText,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ];
      },
      child: Container(
        height: 32,
        padding: const EdgeInsets.symmetric(horizontal: 4),
        decoration: BoxDecoration(
          color: panelBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: border),
          boxShadow: [
            if (!isLight)
              BoxShadow(
                color: Colors.black.withOpacity(0.18),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(width: 9),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 70),
              child: Text(
                hasSelected ? (selectedModelName ?? '选择模型') : '选择模型',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: triggerText,
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
            ),
            if (selectedSource != null) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                decoration: BoxDecoration(
                  color: isLight
                      ? Colors.black.withOpacity(0.05)
                      : Colors.white.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Tooltip(
                  message: selectedSource == _ModelSource.hosted
                      ? '平台托管'
                      : '自己设置',
                  child: Icon(
                    selectedSource == _ModelSource.hosted
                        ? Icons.business_rounded
                        : Icons.person_rounded,
                    color: mutedText,
                    size: 12,
                  ),
                ),
              ),
            ],
            Icon(
              Icons.keyboard_arrow_down_rounded,
              size: 17,
              color: mutedText,
            ),
          ],
        ),
      ),
    );
  }

  PopupMenuItem<String> _buildSectionTitle(String title, Color color) {
    return PopupMenuItem<String>(
      enabled: false,
      height: 36,
      padding: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: Text(
          title,
          style: TextStyle(
            color: color,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }

  PopupMenuItem<String> _buildModelItem({
    required WorkspaceModelOption option,
    required AppThemePalette palette,
    required bool selected,
    required bool showDefault,
  }) {
    final Color textColor = palette.textMain;
    final Color mutedText = palette.textSub;
    final Color selectedBg = palette.selectedBg;

    return PopupMenuItem<String>(
      value: option.optionId,
      height: 44,
      padding: EdgeInsets.zero,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? selectedBg : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                option.displayName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: textColor,
                  fontSize: 14,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                ),
              ),
            ),
            if (showDefault) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                decoration: BoxDecoration(
                  color: palette.badgeBg,
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Text(
                  '默认',
                  style: TextStyle(
                    color: mutedText,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    height: 1,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  PopupMenuItem<String> _buildDivider(AppThemePalette palette) {
    return PopupMenuItem<String>(
      enabled: false,
      height: 12,
      padding: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Divider(
          height: 1,
          thickness: 1,
          color: palette.divider,
        ),
      ),
    );
  }
}

class _SplitHistoryButton extends StatelessWidget {
  const _SplitHistoryButton({
    required this.isLight,
    required this.panelBg,
    required this.border,
    required this.helperText,
    required this.compact,
    required this.onTap,
  });

  final bool isLight;
  final Color panelBg;
  final Color border;
  final Color helperText;
  final bool compact;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final textColor = AppThemePalette.of(context).textMain;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Ink(
          height: 32,
          padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 10),
          decoration: BoxDecoration(
            color: panelBg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: border),
            boxShadow: [
              if (!isLight)
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.18),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.history_rounded,
                size: 17,
                color: helperText,
              ),
              if (!compact) ...[
                const SizedBox(width: 7),
                Text(
                  '分割历史',
                  style: TextStyle(
                    color: textColor,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
