import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../../core/widgets/markdown_math_text.dart';
import '../../../../core/widgets/math_rich_text.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../../chat/data/chat_api.dart';
import '../../data/workspace_api.dart';
import '../../data/workspace_project_store.dart';

class ChatConversationPage extends StatefulWidget {
  const ChatConversationPage({
    super.key,
    required this.sessionId,
    required this.title,
    this.chatApi,
    this.workspaceApi,
  });

  final String sessionId;
  final String title;
  final ChatApi? chatApi;
  final WorkspaceApi? workspaceApi;

  @override
  State<ChatConversationPage> createState() => _ChatConversationPageState();
}

class _ChatConversationPageState extends State<ChatConversationPage> {
  late final ChatApi _chatApi;
  late final WorkspaceApi _workspaceApi;
  final WorkspaceProjectStore _projectStore = WorkspaceProjectStore.instance;
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _messageScrollController = ScrollController();

  final List<_ChatMessageView> _messages = [];
  final List<_QuestionReference> _references = [];
  final List<WorkspaceModelOption> _hostedModels = [];
  final List<WorkspaceModelOption> _selfModels = [];

  bool _isLoadingMessages = false;
  bool _isLoadingOlderMessages = false;
  bool _isSending = false;
  bool _hasMoreMessages = false;
  int? _beforeMessageId;

  bool _isLoadingModels = false;
  String? _modelError;
  String? _selectedModelOptionId;
  _ModelSource? _selectedModelSource;
  bool _deepThink = false;

  @override
  void initState() {
    super.initState();
    _chatApi = widget.chatApi ?? ChatApi();
    _workspaceApi = widget.workspaceApi ?? WorkspaceApi();
    unawaited(_projectStore.ensureLoaded());
    unawaited(_fetchModelOptions());
    unawaited(_loadMessages(reset: true));
  }

  @override
  void dispose() {
    _inputController.dispose();
    _messageScrollController.dispose();
    super.dispose();
  }

  List<WorkspaceModelOption> get _availableHostOptions =>
      _hostedModels.where((item) => item.available && item.configured).toList();

  List<WorkspaceModelOption> get _availableSelfOptions =>
      _selfModels.where((item) => item.available && item.configured).toList();

  WorkspaceModelOption? get _selectedModelOption {
    final id = _selectedModelOptionId;
    if (id == null) {
      return null;
    }
    for (final option in [..._availableHostOptions, ..._availableSelfOptions]) {
      if (option.optionId == id) {
        return option;
      }
    }
    return null;
  }

  String? get _selectedModelDisplayName => _selectedModelOption?.displayName;

  Future<void> _fetchModelOptions() async {
    setState(() {
      _isLoadingModels = true;
      _modelError = null;
    });

    try {
      final response = await _workspaceApi.getModelOptions();
      final available =
          response.options.where((item) => item.available && item.configured);
      final defaultOption = _findDefaultOption(
        available.toList(),
        response.defaultOptionId,
      );

      if (!mounted) {
        return;
      }
      setState(() {
        _hostedModels
          ..clear()
          ..addAll(response.options.where((item) => item.isHostedSource));
        _selfModels
          ..clear()
          ..addAll(response.options.where((item) => item.isSelfSource));
        _selectedModelOptionId = defaultOption?.optionId;
        _selectedModelSource = defaultOption == null
            ? null
            : defaultOption.isHostedSource
                ? _ModelSource.hosted
                : _ModelSource.self;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _modelError = error.message;
        _selectedModelOptionId = null;
        _selectedModelSource = null;
      });
    } finally {
      if (mounted) {
        setState(() => _isLoadingModels = false);
      }
    }
  }

  WorkspaceModelOption? _findDefaultOption(
    List<WorkspaceModelOption> options,
    String? defaultOptionId,
  ) {
    if (options.isEmpty) {
      return null;
    }
    if (defaultOptionId != null) {
      for (final option in options) {
        if (option.optionId == defaultOptionId) {
          return option;
        }
      }
    }
    for (final option in options) {
      if (option.isDefault) {
        return option;
      }
    }
    return options.first;
  }

  Future<void> _loadMessages({required bool reset}) async {
    if (reset) {
      setState(() {
        _isLoadingMessages = true;
        _messages.clear();
        _beforeMessageId = null;
        _hasMoreMessages = false;
      });
    } else {
      if (_isLoadingOlderMessages || !_hasMoreMessages) {
        return;
      }
      setState(() => _isLoadingOlderMessages = true);
    }

    try {
      final response = await _chatApi.getMessages(
        sessionId: widget.sessionId,
        limit: 30,
        beforeId: reset ? null : _beforeMessageId,
      );
      final loaded = response.messages.map(_ChatMessageView.fromApi).toList()
        ..sort(_compareMessages);

      if (!mounted) {
        return;
      }
      setState(() {
        if (reset) {
          _messages
            ..clear()
            ..addAll(loaded);
        } else {
          _messages.insertAll(0, loaded);
        }
        _hasMoreMessages = response.hasMore;
        _beforeMessageId = response.nextBeforeId ??
            (_messages.isEmpty ? null : _messages.first.id);
      });

      if (reset) {
        _scrollToBottom();
      }
    } on ApiException catch (error) {
      if (mounted) {
        showAppSnackBar(context, error.message);
      }
    } finally {
      if (mounted) {
        setState(() {
          if (reset) {
            _isLoadingMessages = false;
          } else {
            _isLoadingOlderMessages = false;
          }
        });
      }
    }
  }

  static int _compareMessages(_ChatMessageView left, _ChatMessageView right) {
    final leftId = left.id;
    final rightId = right.id;
    if (leftId != null && rightId != null) {
      return leftId.compareTo(rightId);
    }
    return left.localOrder.compareTo(right.localOrder);
  }

  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _isSending) {
      return;
    }

    final model = _selectedModelOption;
    if (model == null) {
      showAppSnackBar(context, _modelError ?? '请先选择可用模型');
      return;
    }

    final userMessage = _ChatMessageView.local(
      role: 'user',
      content: text,
    );
    final assistantMessage = _ChatMessageView.local(
      role: 'assistant',
      content: '',
      streaming: true,
    );

    setState(() {
      _isSending = true;
      _inputController.clear();
      _messages
        ..add(userMessage)
        ..add(assistantMessage);
    });
    _scrollToBottom();

    try {
      await for (final event in _chatApi.streamMessage(
        sessionId: widget.sessionId,
        request: ChatStreamRequest(
          message: text,
          modelProvider: model.category.isNotEmpty ? model.category : 'openai',
          modelName: model.modelName.isNotEmpty ? model.modelName : null,
          providerSource: model.source.isNotEmpty ? model.source : null,
          providerId: model.providerId.isNotEmpty ? model.providerId : null,
          deepThink: _deepThink,
          contextRefs: _buildContextRefs(),
        ),
      )) {
        if (!mounted) {
          return;
        }

        if (event.error != null && event.error!.isNotEmpty) {
          setState(() {
            assistantMessage
              ..content = event.error!
              ..isStreaming = false
              ..hasError = true;
          });
          showAppSnackBar(context, event.error!);
          break;
        }

        setState(() {
          if (event.reasoning != null) {
            assistantMessage.reasoning += event.reasoning!;
          }
          if (event.token != null) {
            assistantMessage.content += event.token!;
          }
          if (event.done) {
            assistantMessage.isStreaming = false;
          }
        });
        _scrollToBottom();
      }
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          assistantMessage
            ..content = error.message
            ..isStreaming = false
            ..hasError = true;
        });
        showAppSnackBar(context, error.message);
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
          assistantMessage.isStreaming = false;
        });
      }
    }
  }

  List<ChatContextRef> _buildContextRefs() {
    final grouped = <int, List<int>>{};
    for (final reference in _references) {
      grouped
          .putIfAbsent(reference.project.id, () => [])
          .add(reference.question.id);
    }
    return grouped.entries
        .map(
          (entry) => ChatContextRef(
            type: 'question',
            projectId: entry.key,
            questionIds: entry.value,
          ),
        )
        .toList();
  }

  Future<void> _openReferenceDialog() async {
    await _projectStore.ensureLoaded();
    final projects = _projectStore.questionProjects;
    if (!mounted) {
      return;
    }
    if (projects.isEmpty) {
      showAppSnackBar(context, '暂无可引用的错题库');
      return;
    }

    final result = await showDialog<List<_QuestionReference>>(
      context: context,
      builder: (context) {
        return _QuestionReferenceDialog(
          chatApi: _chatApi,
          projects: projects,
          initialReferences: _references,
        );
      },
    );

    if (!mounted || result == null) {
      return;
    }
    setState(() {
      _references
        ..clear()
        ..addAll(result);
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_messageScrollController.hasClients) {
        return;
      }
      _messageScrollController.animateTo(
        _messageScrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          child: Column(
            children: [
              _ConversationHeader(
                palette: palette,
                title: widget.title,
                onBack: () => Navigator.of(context).maybePop(),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(18, 0, 18, 0),
                  child: _buildMessageArea(palette),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 8, 18, 16),
                child: _ChatComposer(
                  palette: palette,
                  controller: _inputController,
                  isSending: _isSending,
                  deepThink: _deepThink,
                  referenceLabel: _referenceLabel,
                  modelSelector: _ModelSelector(
                    isLight: palette.isLight,
                    isLoading: _isLoadingModels,
                    selectedModelId: _selectedModelOptionId,
                    selectedModelName: _selectedModelDisplayName,
                    selectedSource: _selectedModelSource,
                    hosted: _availableHostOptions,
                    self: _availableSelfOptions,
                    modelError: _modelError,
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
                    onPickSettings: () =>
                        showAppSnackBar(context, 'API 设置入口待接入'),
                    onPickEmpty: () => showAppSnackBar(context, '当前暂无可用模型'),
                    panelBg: palette.panelBg,
                    border: palette.panelBorder,
                  ),
                  onToggleDeepThink: () =>
                      setState(() => _deepThink = !_deepThink),
                  onPickReferences: _openReferenceDialog,
                  onClearReferences: () => setState(_references.clear),
                  onSend: _sendMessage,
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  '内容由 AI 生成，仅供参考',
                  style: TextStyle(
                    color: palette.textSub.withOpacity(0.65),
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessageArea(AppThemePalette palette) {
    if (_isLoadingMessages) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }

    if (_messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Hi, Admin',
              style: TextStyle(
                color: palette.textMain,
                fontSize: 30,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              '有问题，尽管问',
              style: TextStyle(
                color: palette.textSub,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _messageScrollController,
      padding: const EdgeInsets.fromLTRB(4, 12, 4, 12),
      itemCount: _messages.length + (_hasMoreMessages ? 1 : 0),
      itemBuilder: (context, index) {
        if (_hasMoreMessages && index == 0) {
          return Center(
            child: TextButton(
              onPressed: _isLoadingOlderMessages
                  ? null
                  : () => _loadMessages(reset: false),
              child: Text(_isLoadingOlderMessages ? '加载中...' : '加载更早消息'),
            ),
          );
        }

        final messageIndex = index - (_hasMoreMessages ? 1 : 0);
        return _ChatBubble(
          palette: palette,
          message: _messages[messageIndex],
        );
      },
    );
  }

  String? get _referenceLabel {
    if (_references.isEmpty) {
      return null;
    }
    final projectName = _references.first.project.displayName;
    return '$projectName · ${_references.length} 题';
  }
}

class _ConversationHeader extends StatelessWidget {
  const _ConversationHeader({
    required this.palette,
    required this.title,
    required this.onBack,
  });

  final AppThemePalette palette;
  final String title;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 8, 14, 8),
      child: Row(
        children: [
          IconButton(
            onPressed: onBack,
            icon: const Icon(Icons.arrow_back_ios_new_rounded),
            color: palette.textMain,
          ),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatComposer extends StatelessWidget {
  const _ChatComposer({
    required this.palette,
    required this.controller,
    required this.isSending,
    required this.deepThink,
    required this.modelSelector,
    required this.onToggleDeepThink,
    required this.onPickReferences,
    required this.onClearReferences,
    required this.onSend,
    this.referenceLabel,
  });

  final AppThemePalette palette;
  final TextEditingController controller;
  final bool isSending;
  final bool deepThink;
  final Widget modelSelector;
  final String? referenceLabel;
  final VoidCallback onToggleDeepThink;
  final VoidCallback onPickReferences;
  final VoidCallback onClearReferences;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.panelBorder),
      ),
      child: Column(
        children: [
          TextField(
            controller: controller,
            minLines: 1,
            maxLines: 5,
            textInputAction: TextInputAction.newline,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
            decoration: InputDecoration(
              isDense: true,
              border: InputBorder.none,
              hintText: '有问题，尽管问，shift+enter 换行',
              hintStyle: TextStyle(
                color: palette.textSub,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    modelSelector,
                    TextButton.icon(
                      onPressed: onToggleDeepThink,
                      style: TextButton.styleFrom(
                        backgroundColor:
                            deepThink ? palette.primary : palette.panelBg,
                        foregroundColor:
                            deepThink ? Colors.white : palette.textSub,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 8),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      icon: const Icon(Icons.psychology_rounded, size: 17),
                      label: const Text(
                        '深度思考',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    if (referenceLabel != null)
                      Container(
                        constraints: const BoxConstraints(maxWidth: 180),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 9, vertical: 7),
                        decoration: BoxDecoration(
                          color: palette.primary.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(9),
                          border: Border.all(
                            color: palette.primary.withOpacity(0.45),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.storage_rounded,
                              color: palette.primaryLight,
                              size: 14,
                            ),
                            const SizedBox(width: 5),
                            Flexible(
                              child: Text(
                                referenceLabel!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: palette.primaryLight,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                            const SizedBox(width: 4),
                            GestureDetector(
                              onTap: onClearReferences,
                              child: Icon(
                                Icons.close_rounded,
                                color: palette.textSub,
                                size: 15,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              IconButton(
                tooltip: '引用错题',
                onPressed: onPickReferences,
                icon: const Icon(Icons.add_rounded),
                color: palette.textSub,
              ),
              IconButton(
                tooltip: '发送',
                onPressed: isSending ? null : onSend,
                icon: isSending
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.arrow_upward_rounded),
                color: palette.textMain,
                style: IconButton.styleFrom(
                  backgroundColor: palette.subtleOverlay,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({
    required this.palette,
    required this.message,
  });

  final AppThemePalette palette;
  final _ChatMessageView message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 760),
        margin: EdgeInsets.only(
          left: isUser ? 54 : 0,
          right: isUser ? 0 : 54,
          bottom: 18,
        ),
        padding: isUser
            ? const EdgeInsets.symmetric(horizontal: 16, vertical: 12)
            : EdgeInsets.zero,
        decoration: BoxDecoration(
          color: isUser
              ? palette.primary
              : message.hasError
                  ? palette.errorText.withOpacity(0.12)
                  : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
        ),
        child: isUser
            ? MathRichText(
                text: message.content,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  height: 1.55,
                ),
              )
            : _AssistantMessageBody(
                palette: palette,
                message: message,
              ),
      ),
    );
  }
}

class _AssistantMessageBody extends StatelessWidget {
  const _AssistantMessageBody({
    required this.palette,
    required this.message,
  });

  final AppThemePalette palette;
  final _ChatMessageView message;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (message.reasoning.trim().isNotEmpty)
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: palette.primary.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: palette.primary.withOpacity(0.18)),
            ),
            child: MathRichText(
              text: message.reasoning,
              style: TextStyle(
                color: palette.textSub,
                fontSize: 13,
                height: 1.5,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        if (message.content.trim().isEmpty && message.isStreaming)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: palette.primary,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '正在生成',
                style: TextStyle(
                  color: palette.textSub,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          )
        else
          MarkdownMathText(
            text: message.content,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 15,
              height: 1.65,
              fontWeight: FontWeight.w700,
            ),
            palette: palette,
          ),
      ],
    );
  }
}

class _QuestionReferenceDialog extends StatefulWidget {
  const _QuestionReferenceDialog({
    required this.chatApi,
    required this.projects,
    required this.initialReferences,
  });

  final ChatApi chatApi;
  final List<WorkspaceProject> projects;
  final List<_QuestionReference> initialReferences;

  @override
  State<_QuestionReferenceDialog> createState() =>
      _QuestionReferenceDialogState();
}

class _QuestionReferenceDialogState extends State<_QuestionReferenceDialog> {
  late WorkspaceProject _selectedProject;
  final TextEditingController _keywordController = TextEditingController();
  final List<ErrorBankQuestion> _questions = [];
  final Map<int, _QuestionReference> _selected = {};
  int _page = 1;
  bool _hasMore = false;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _selectedProject = widget.projects.first;
    for (final reference in widget.initialReferences) {
      _selected[reference.question.id] = reference;
    }
    unawaited(_loadQuestions(reset: true));
  }

  @override
  void dispose() {
    _keywordController.dispose();
    super.dispose();
  }

  Future<void> _loadQuestions({required bool reset}) async {
    if (_isLoading) {
      return;
    }
    setState(() => _isLoading = true);

    try {
      final page = reset ? 1 : _page + 1;
      final response = await widget.chatApi.queryErrorBank(
        page: page,
        pageSize: 20,
        projectId: _selectedProject.id,
        keyword: _keywordController.text.trim(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        if (reset) {
          _questions.clear();
        }
        _questions.addAll(response.questions);
        _page = page;
        _hasMore = _questions.length < response.total;
      });
    } on ApiException catch (error) {
      if (mounted) {
        showAppSnackBar(context, error.message);
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _selectProject(WorkspaceProject project) {
    if (project.id == _selectedProject.id) {
      return;
    }
    setState(() => _selectedProject = project);
    unawaited(_loadQuestions(reset: true));
  }

  void _toggleQuestion(ErrorBankQuestion question) {
    setState(() {
      if (_selected.containsKey(question.id)) {
        _selected.remove(question.id);
      } else {
        _selected[question.id] = _QuestionReference(
          project: _selectedProject,
          question: question,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Dialog(
      backgroundColor: palette.menuBg,
      insetPadding: const EdgeInsets.all(18),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: palette.panelBorderStrong),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 980, maxHeight: 720),
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(22, 18, 18, 18),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: palette.primary.withOpacity(0.18),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(Icons.storage_rounded,
                        color: palette.primaryLight),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      '引用错题回答',
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close_rounded),
                    color: palette.textSub,
                  ),
                ],
              ),
            ),
            Divider(height: 1, color: palette.divider),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final compact = constraints.maxWidth < 700;
                  final projectList = _buildProjectList(palette, compact);
                  final questionList = _buildQuestionList(palette);
                  if (compact) {
                    return Column(
                      children: [
                        SizedBox(height: 86, child: projectList),
                        Divider(height: 1, color: palette.divider),
                        Expanded(child: questionList),
                      ],
                    );
                  }
                  return Row(
                    children: [
                      SizedBox(width: 300, child: projectList),
                      VerticalDivider(width: 1, color: palette.divider),
                      Expanded(child: questionList),
                    ],
                  );
                },
              ),
            ),
            Divider(height: 1, color: palette.divider),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
              child: Row(
                children: [
                  Icon(Icons.link_rounded, color: palette.textSub, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    '已选择 ${_selected.length} 题',
                    style: TextStyle(
                      color: palette.textSub,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text('取消', style: TextStyle(color: palette.textSub)),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: () =>
                        Navigator.of(context).pop(_selected.values.toList()),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: palette.primary,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text(
                      '确定引用',
                      style: TextStyle(fontWeight: FontWeight.w900),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProjectList(AppThemePalette palette, bool compact) {
    return ListView.builder(
      scrollDirection: compact ? Axis.horizontal : Axis.vertical,
      padding: const EdgeInsets.all(14),
      itemCount: widget.projects.length,
      itemBuilder: (context, index) {
        final project = widget.projects[index];
        final selected = project.id == _selectedProject.id;
        return Padding(
          padding: EdgeInsets.only(
            right: compact ? 8 : 0,
            bottom: compact ? 0 : 8,
          ),
          child: InkWell(
            onTap: () => _selectProject(project),
            borderRadius: BorderRadius.circular(10),
            child: Container(
              width: compact ? 150 : double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: selected
                    ? palette.primary.withOpacity(0.18)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.storage_rounded,
                    color: selected ? palette.primaryLight : palette.textSub,
                    size: 17,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      project.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color:
                            selected ? palette.primaryLight : palette.textSub,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildQuestionList(AppThemePalette palette) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _selectedProject.displayName,
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '选择本次对话要参考的具体题目',
                      style: TextStyle(
                        color: palette.textSub,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              TextButton(
                onPressed:
                    _selected.isEmpty ? null : () => setState(_selected.clear),
                child: const Text('清空'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
          child: TextField(
            controller: _keywordController,
            onSubmitted: (_) => _loadQuestions(reset: true),
            style: TextStyle(color: palette.textMain),
            decoration: InputDecoration(
              isDense: true,
              hintText: '搜索错题',
              hintStyle: TextStyle(color: palette.textSub),
              prefixIcon: Icon(Icons.search_rounded, color: palette.textSub),
              filled: true,
              fillColor: palette.panelBg,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: palette.panelBorder),
              ),
            ),
          ),
        ),
        Expanded(
          child: _isLoading && _questions.isEmpty
              ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
              : _questions.isEmpty
                  ? Center(
                      child: Text(
                        '暂无错题',
                        style: TextStyle(
                          color: palette.textSub,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                      itemCount: _questions.length + (_hasMore ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (_hasMore && index == _questions.length) {
                          return Center(
                            child: TextButton(
                              onPressed: _isLoading
                                  ? null
                                  : () => _loadQuestions(reset: false),
                              child: Text(_isLoading ? '加载中...' : '加载更多'),
                            ),
                          );
                        }

                        final question = _questions[index];
                        return _ReferenceQuestionTile(
                          palette: palette,
                          question: question,
                          selected: _selected.containsKey(question.id),
                          onTap: () => _toggleQuestion(question),
                        );
                      },
                    ),
        ),
      ],
    );
  }
}

class _ReferenceQuestionTile extends StatelessWidget {
  const _ReferenceQuestionTile({
    required this.palette,
    required this.question,
    required this.selected,
    required this.onTap,
  });

  final AppThemePalette palette;
  final ErrorBankQuestion question;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected ? palette.primary.withOpacity(0.15) : palette.cardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected
                ? palette.primary.withOpacity(0.55)
                : palette.panelBorder,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              selected
                  ? Icons.check_box_rounded
                  : Icons.check_box_outline_blank_rounded,
              color: selected ? palette.primaryLight : palette.textSub,
              size: 22,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _QuestionChip(
                        text: '#${question.id}',
                        palette: palette,
                        highlighted: false,
                      ),
                      if (question.questionType.isNotEmpty)
                        _QuestionChip(
                          text: question.questionType,
                          palette: palette,
                          highlighted: false,
                        ),
                      if (question.subject.isNotEmpty)
                        _QuestionChip(
                          text: question.subject,
                          palette: palette,
                          highlighted: true,
                        ),
                    ],
                  ),
                  const SizedBox(height: 9),
                  MathRichText(
                    text: question.previewText,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: palette.textMain,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      height: 1.55,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuestionChip extends StatelessWidget {
  const _QuestionChip({
    required this.text,
    required this.palette,
    required this.highlighted,
  });

  final String text;
  final AppThemePalette palette;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: highlighted
            ? palette.primary.withOpacity(0.2)
            : palette.subtleOverlay,
        borderRadius: BorderRadius.circular(7),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: highlighted ? palette.primaryLight : palette.textSub,
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
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
    final hasSelected = selectedModelId != null &&
        selectedModelName != null &&
        selectedModelName!.isNotEmpty;
    final hasModels = hosted.isNotEmpty || self.isNotEmpty;
    final allOptions = [...hosted, ...self];
    final palette = AppThemePalette(isLight: isLight);

    return PopupMenuButton<String>(
      tooltip: '模型选择',
      enabled: !isLoading,
      color: palette.menuBg,
      elevation: 12,
      offset: const Offset(0, 10),
      constraints: const BoxConstraints(minWidth: 274, maxWidth: 320),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: palette.subtleOverlay),
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
            const PopupMenuItem<String>(
              enabled: false,
              child: Row(
                children: [
                  SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 10),
                  Text('模型加载中...'),
                ],
              ),
            ),
          ];
        }

        if (!hasModels) {
          return [
            PopupMenuItem<String>(
              enabled: false,
              child: Text(modelError ?? '当前暂无可用模型'),
            ),
            _buildDivider(palette),
            _buildApiSettingsItem(palette),
          ];
        }

        return [
          _buildSectionTitle('平台托管', palette.textSub),
          for (final item in hosted)
            _buildModelItem(
              option: item,
              palette: palette,
              selected: selectedModelId == item.optionId &&
                  selectedSource == _ModelSource.hosted,
              showDefault: item.isDefault,
            ),
          _buildDivider(palette),
          _buildSectionTitle('自己设置', palette.textSub),
          for (final item in self)
            _buildModelItem(
              option: item,
              palette: palette,
              selected: selectedModelId == item.optionId &&
                  selectedSource == _ModelSource.self,
              showDefault: false,
            ),
          _buildDivider(palette),
          _buildApiSettingsItem(palette),
        ];
      },
      child: Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(
          color: panelBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: border),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.auto_awesome_rounded,
                color: palette.primaryLight, size: 16),
            const SizedBox(width: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 100),
              child: Text(
                hasSelected ? (selectedModelName ?? '选择模型') : '选择模型',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: palette.textMain,
                  fontWeight: FontWeight.w900,
                  fontSize: 13,
                ),
              ),
            ),
            if (selectedSource != null) ...[
              const SizedBox(width: 7),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                decoration: BoxDecoration(
                  color: palette.subtleOverlay,
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Text(
                  selectedSource == _ModelSource.hosted ? '平台' : '自设',
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    height: 1,
                  ),
                ),
              ),
            ],
            Icon(
              Icons.keyboard_arrow_down_rounded,
              size: 18,
              color: palette.textSub,
            ),
          ],
        ),
      ),
    );
  }

  PopupMenuItem<String> _buildSectionTitle(String title, Color color) {
    return PopupMenuItem<String>(
      enabled: false,
      height: 34,
      child: Text(
        title,
        style: TextStyle(
          color: color,
          fontSize: 13,
          fontWeight: FontWeight.w800,
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
    return PopupMenuItem<String>(
      value: option.optionId,
      child: Row(
        children: [
          Icon(
            selected
                ? Icons.check_circle_rounded
                : Icons.radio_button_unchecked_rounded,
            color: selected ? palette.primary : palette.textSub,
            size: 18,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              option.displayName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: palette.textMain,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          if (showDefault)
            Text(
              '默认',
              style: TextStyle(
                color: palette.primaryLight,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
        ],
      ),
    );
  }

  PopupMenuItem<String> _buildApiSettingsItem(AppThemePalette palette) {
    return PopupMenuItem<String>(
      value: _apiSettingsValue,
      child: Row(
        children: [
          Icon(Icons.tune_rounded, color: palette.textSub, size: 18),
          const SizedBox(width: 10),
          Text(
            'API 设置',
            style: TextStyle(
              color: palette.textMain,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  PopupMenuItem<String> _buildDivider(AppThemePalette palette) {
    return PopupMenuItem<String>(
      enabled: false,
      height: 1,
      padding: EdgeInsets.zero,
      child: Divider(height: 1, color: palette.divider),
    );
  }
}

class _ChatMessageView {
  _ChatMessageView({
    required this.id,
    required this.role,
    required this.content,
    required this.reasoning,
    required this.localOrder,
    this.isStreaming = false,
  });

  final int? id;
  final String role;
  String content;
  String reasoning;
  final int localOrder;
  bool isStreaming;
  bool hasError = false;

  static int _nextLocalOrder = 0;

  factory _ChatMessageView.fromApi(ChatMessage message) {
    return _ChatMessageView(
      id: message.id,
      role: message.role,
      content: message.content,
      reasoning: message.reasoning,
      localOrder: _nextLocalOrder++,
    );
  }

  factory _ChatMessageView.local({
    required String role,
    required String content,
    bool streaming = false,
  }) {
    return _ChatMessageView(
      id: null,
      role: role,
      content: content,
      reasoning: '',
      localOrder: _nextLocalOrder++,
      isStreaming: streaming,
    );
  }
}

class _QuestionReference {
  const _QuestionReference({
    required this.project,
    required this.question,
  });

  final WorkspaceProject project;
  final ErrorBankQuestion question;
}

enum _ModelSource { hosted, self }
