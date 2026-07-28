import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/time_format.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../chat/data/chat_api.dart';
import 'chat_conversation_page.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({
    super.key,
    this.chatApi,
  });

  final ChatApi? chatApi;

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  late final ChatApi _chatApi;
  late Future<ChatSessionsResponse> _sessionsFuture;
  bool _isMutating = false;

  @override
  void initState() {
    super.initState();
    _chatApi = widget.chatApi ?? ChatApi();
    _sessionsFuture = _loadSessions();
  }

  Future<ChatSessionsResponse> _loadSessions() {
    return _chatApi.getMySessions(limit: 50);
  }

  void _refresh() {
    setState(() {
      _sessionsFuture = _loadSessions();
    });
  }

  Future<void> _createNewSession() async {
    if (_isMutating) {
      return;
    }

    setState(() => _isMutating = true);
    try {
      final response = await _chatApi.createSession();
      if (!mounted) {
        return;
      }

      final sessionId = response.sessionId;
      if (sessionId == null || sessionId.isEmpty) {
        showAppSnackBar(context, '对话创建成功，但未返回会话 ID');
        _refresh();
        return;
      }

      await _openConversation(
        sessionId: sessionId,
        title: response.session?.displayTitle ?? '新对话',
      );
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      showAppSnackBar(context, error.message);
    } finally {
      if (mounted) {
        setState(() => _isMutating = false);
      }
    }
  }

  Future<void> _openConversation({
    required String sessionId,
    required String title,
  }) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => ChatConversationPage(
          sessionId: sessionId,
          title: title,
          chatApi: _chatApi,
        ),
      ),
    );
    if (mounted) {
      _refresh();
    }
  }

  Future<void> _renameSession(ChatSession session) async {
    final title = await _showRenameDialog(session);
    if (!mounted) {
      return;
    }
    if (title == null || title == session.displayTitle) {
      return;
    }

    setState(() => _isMutating = true);
    try {
      final response = await _chatApi.renameSession(
        sessionId: session.id,
        title: title,
      );
      if (!mounted) {
        return;
      }
      showAppSnackBar(context, response.message);
      _refresh();
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      showAppSnackBar(context, error.message);
    } finally {
      if (mounted) {
        setState(() => _isMutating = false);
      }
    }
  }

  Future<void> _deleteSession(ChatSession session) async {
    final confirmed = await _showDeleteDialog(session);
    if (!mounted) {
      return;
    }
    if (confirmed != true) {
      return;
    }

    setState(() => _isMutating = true);
    try {
      final response = await _chatApi.deleteSession(sessionId: session.id);
      if (!mounted) {
        return;
      }
      showAppSnackBar(context, response.message);
      _refresh();
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      showAppSnackBar(context, error.message);
    } finally {
      if (mounted) {
        setState(() => _isMutating = false);
      }
    }
  }

  Future<String?> _showRenameDialog(ChatSession session) async {
    final palette = AppThemePalette.of(context);
    return showDialog<String>(
      context: context,
      builder: (context) => _RenameSessionDialog(
        palette: palette,
        initialTitle: session.displayTitle,
      ),
    );
  }

  Future<bool?> _showDeleteDialog(ChatSession session) {
    final palette = AppThemePalette.of(context);
    return showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: palette.menuBg,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          title: Text(
            '删除对话',
            style: TextStyle(
              color: palette.textMain,
              fontWeight: FontWeight.w900,
            ),
          ),
          content: Text(
            '确定删除「${session.displayTitle}」吗？',
            style: TextStyle(color: palette.textSub),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text('取消', style: TextStyle(color: palette.textSub)),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(true),
              style: ElevatedButton.styleFrom(
                backgroundColor: palette.errorText,
                foregroundColor: Colors.white,
                elevation: 0,
              ),
              child: const Text('删除'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _ChatToolbar(
          palette: palette,
          onNewChat: _createNewSession,
          onRefresh: _refresh,
          isRefreshing: _isMutating,
        ),
        const SizedBox(height: 12),
        FutureBuilder<ChatSessionsResponse>(
          future: _sessionsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return _ChatMessageCard(
                palette: palette,
                child: const Center(
                  child: Padding(
                    padding: EdgeInsets.all(20),
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              );
            }

            if (snapshot.hasError) {
              return _ChatMessageCard(
                palette: palette,
                child: Column(
                  children: [
                    Text(
                      '对话列表加载失败',
                      style: TextStyle(
                        color: palette.textMain,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextButton(
                      onPressed: _refresh,
                      child: const Text('重新加载'),
                    ),
                  ],
                ),
              );
            }

            final response = snapshot.data;
            final sessions = response?.sessions ?? const <ChatSession>[];
            if (sessions.isEmpty) {
              return _ChatMessageCard(
                palette: palette,
                child: Text(
                  '暂无独立对话',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: palette.textSub,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              );
            }

            return Column(
              children: [
                for (final session in sessions)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _ChatSessionTile(
                      palette: palette,
                      session: session,
                      onTap: () => _openConversation(
                        sessionId: session.id,
                        title: session.displayTitle,
                      ),
                      onRename: () => _renameSession(session),
                      onDelete: () => _deleteSession(session),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _ChatToolbar extends StatelessWidget {
  const _ChatToolbar({
    required this.palette,
    required this.onNewChat,
    required this.onRefresh,
    required this.isRefreshing,
  });

  final AppThemePalette palette;
  final VoidCallback onNewChat;
  final VoidCallback onRefresh;
  final bool isRefreshing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            '对话',
            style: TextStyle(
              color: palette.textMain,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        IconButton(
          tooltip: '刷新',
          onPressed: isRefreshing ? null : onRefresh,
          icon: const Icon(Icons.refresh_rounded),
          color: palette.textSub,
        ),
        IconButton(
          tooltip: '新建对话',
          onPressed: onNewChat,
          icon: const Icon(Icons.add_rounded),
          color: palette.textMain,
        ),
      ],
    );
  }
}

class _RenameSessionDialog extends StatefulWidget {
  const _RenameSessionDialog({
    required this.palette,
    required this.initialTitle,
  });

  final AppThemePalette palette;
  final String initialTitle;

  @override
  State<_RenameSessionDialog> createState() => _RenameSessionDialogState();
}

class _RenameSessionDialogState extends State<_RenameSessionDialog> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialTitle);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final value = _controller.text.trim();
    if (value.isEmpty) {
      return;
    }
    Navigator.of(context).pop(value);
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.palette;

    return AlertDialog(
      backgroundColor: palette.menuBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Text(
        '重命名',
        style: TextStyle(
          color: palette.textMain,
          fontWeight: FontWeight.w900,
        ),
      ),
      content: TextField(
        controller: _controller,
        autofocus: true,
        maxLength: 40,
        onSubmitted: (_) => _submit(),
        style: TextStyle(color: palette.textMain),
        decoration: InputDecoration(
          hintText: '输入对话标题',
          hintStyle: TextStyle(color: palette.textSub),
          filled: true,
          fillColor: palette.panelBg,
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: palette.panelBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: palette.primary),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('取消', style: TextStyle(color: palette.textSub)),
        ),
        ElevatedButton(
          onPressed: _submit,
          style: ElevatedButton.styleFrom(
            backgroundColor: palette.primary,
            foregroundColor: Colors.white,
            elevation: 0,
          ),
          child: const Text('保存'),
        ),
      ],
    );
  }
}

class _ChatSessionTile extends StatelessWidget {
  const _ChatSessionTile({
    required this.palette,
    required this.session,
    required this.onTap,
    required this.onRename,
    required this.onDelete,
  });

  final AppThemePalette palette;
  final ChatSession session;
  final VoidCallback onTap;
  final VoidCallback onRename;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          decoration: BoxDecoration(
            color: palette.panelBg,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.panelBorder),
          ),
          child: Row(
            children: [
              Icon(
                Icons.chat_bubble_rounded,
                color: palette.primaryLight
                    .withOpacity(palette.isLight ? 0.42 : 0.46),
                size: 18,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      session.displayTitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: palette.textMain,
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      formatRelativeTime(
                        session.updatedAt ?? session.createdAt,
                      ),
                      style: TextStyle(
                        color: palette.textSub,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              _SessionMenu(
                palette: palette,
                onRename: onRename,
                onDelete: onDelete,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SessionMenu extends StatelessWidget {
  const _SessionMenu({
    required this.palette,
    required this.onRename,
    required this.onDelete,
  });

  final AppThemePalette palette;
  final VoidCallback onRename;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<_SessionAction>(
      tooltip: '更多',
      color: palette.menuBg,
      elevation: 10,
      offset: const Offset(0, 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: palette.panelBorder),
      ),
      icon: Icon(
        Icons.more_horiz_rounded,
        color: palette.textSub,
      ),
      onSelected: (value) {
        switch (value) {
          case _SessionAction.rename:
            onRename();
          case _SessionAction.delete:
            onDelete();
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem<_SessionAction>(
          value: _SessionAction.rename,
          child: Row(
            children: [
              Icon(Icons.edit_rounded, color: palette.textSub, size: 20),
              const SizedBox(width: 12),
              Text(
                '重命名',
                style: TextStyle(
                  color: palette.textMain,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
        PopupMenuItem<_SessionAction>(
          value: _SessionAction.delete,
          child: Row(
            children: [
              Icon(Icons.delete_rounded, color: palette.errorText, size: 20),
              const SizedBox(width: 12),
              Text(
                '删除',
                style: TextStyle(
                  color: palette.errorText,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ChatMessageCard extends StatelessWidget {
  const _ChatMessageCard({
    required this.palette,
    required this.child,
  });

  final AppThemePalette palette;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: palette.panelBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: palette.panelBorder),
      ),
      child: child,
    );
  }
}

enum _SessionAction { rename, delete }
