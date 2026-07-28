import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../../../core/utils/time_format.dart';

class ChatApi {
  ChatApi({ApiClient? client}) : _client = client ?? ApiClient();

  final ApiClient _client;

  Future<ChatSessionsResponse> getMySessions({
    int page = 1,
    int limit = 20,
  }) async {
    final path = Uri(
      path: '/api/chat/my-sessions',
      queryParameters: {
        'page': '$page',
        'limit': '$limit',
      },
    ).toString();
    final payload = await _client.getJson(path);
    return ChatSessionsResponse.fromJson(payload);
  }

  Future<CreateChatSessionResponse> createSession({
    String title = '新对话',
    int? questionId,
  }) async {
    final payload = await _client.postJson('/api/chat', {
      'title': title,
      'question_id': questionId,
    });
    return CreateChatSessionResponse.fromJson(payload);
  }

  Future<ChatMessagesResponse> getMessages({
    required String sessionId,
    int limit = 30,
    int? beforeId,
  }) async {
    final path = Uri(
      path: '/api/chat/${Uri.encodeComponent(sessionId)}/messages',
      queryParameters: {
        'limit': '$limit',
        if (beforeId != null) 'before_id': '$beforeId',
      },
    ).toString();
    final payload = await _client.getJson(path);
    return ChatMessagesResponse.fromJson(payload);
  }

  Future<ErrorBankResponse> queryErrorBank({
    int page = 1,
    int pageSize = 20,
    String? subject,
    String? knowledgeTag,
    String? questionType,
    String? keyword,
    int? projectId,
    String? reviewStatus,
    String? startDate,
    String? endDate,
  }) async {
    final path = Uri(
      path: '/api/error-bank',
      queryParameters: {
        'page': '$page',
        'page_size': '$pageSize',
        if (_hasValue(subject)) 'subject': subject!,
        if (_hasValue(knowledgeTag)) 'knowledge_tag': knowledgeTag!,
        if (_hasValue(questionType)) 'question_type': questionType!,
        if (_hasValue(keyword)) 'keyword': keyword!,
        if (projectId != null) 'project_id': '$projectId',
        if (_hasValue(reviewStatus)) 'review_status': reviewStatus!,
        if (_hasValue(startDate)) 'start_date': startDate!,
        if (_hasValue(endDate)) 'end_date': endDate!,
      },
    ).toString();
    final payload = await _client.getJson(path);
    return ErrorBankResponse.fromJson(payload);
  }

  Stream<ChatStreamEvent> streamMessage({
    required String sessionId,
    required ChatStreamRequest request,
  }) {
    final chunks = _client.postEventStream(
      '/api/chat/${Uri.encodeComponent(sessionId)}/stream',
      request.toJson(),
    );
    return _parseSseEvents(chunks);
  }

  Future<ChatActionResponse> renameSession({
    required String sessionId,
    required String title,
  }) async {
    final payload = await _client.patchJson(
      '/api/chat/${Uri.encodeComponent(sessionId)}',
      {'title': title},
    );
    return ChatActionResponse.fromJson(payload, fallbackMessage: '标题已更新');
  }

  Future<ChatActionResponse> deleteSession({
    required String sessionId,
  }) async {
    final payload = await _client.deleteJson(
      '/api/chat/${Uri.encodeComponent(sessionId)}',
    );
    return ChatActionResponse.fromJson(payload, fallbackMessage: '对话已删除');
  }
}

class ChatSessionsResponse {
  const ChatSessionsResponse({
    required this.success,
    required this.sessions,
    required this.total,
  });

  final bool success;
  final List<ChatSession> sessions;
  final int total;

  factory ChatSessionsResponse.fromJson(Map<String, dynamic> json) {
    final rawSessions = (json['sessions'] as List?) ?? const [];
    return ChatSessionsResponse(
      success: json['success'] as bool? ?? false,
      sessions: rawSessions
          .whereType<Map<String, dynamic>>()
          .map(ChatSession.fromJson)
          .toList(),
      total: _readInt(json['total']) ?? rawSessions.length,
    );
  }
}

class ChatSession {
  const ChatSession({
    required this.id,
    required this.title,
    required this.questionId,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String title;
  final int? questionId;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  String get displayTitle => title.trim().isEmpty ? '新对话' : title.trim();

  factory ChatSession.fromJson(Map<String, dynamic> json) {
    return ChatSession(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '新对话',
      questionId: _readInt(json['question_id']),
      createdAt: _readDateTime(json['created_at']),
      updatedAt: _readDateTime(json['updated_at']),
    );
  }
}

class CreateChatSessionResponse {
  const CreateChatSessionResponse({
    required this.success,
    required this.message,
    required this.session,
    required this.sessionId,
  });

  final bool success;
  final String message;
  final ChatSession? session;
  final String? sessionId;

  factory CreateChatSessionResponse.fromJson(Map<String, dynamic> json) {
    final rawSession = json['session'];
    final session = rawSession is Map
        ? ChatSession.fromJson(rawSession.cast<String, dynamic>())
        : null;
    return CreateChatSessionResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString() ?? '创建成功',
      session: session,
      sessionId: session?.id ?? (json['session_id'] ?? json['id'])?.toString(),
    );
  }
}

class ChatMessagesResponse {
  const ChatMessagesResponse({
    required this.success,
    required this.messages,
    required this.hasMore,
    required this.nextBeforeId,
  });

  final bool success;
  final List<ChatMessage> messages;
  final bool hasMore;
  final int? nextBeforeId;

  factory ChatMessagesResponse.fromJson(Map<String, dynamic> json) {
    final rawMessages =
        (json['messages'] ?? json['items'] ?? json['data']) as List? ??
            const [];
    final messages = rawMessages
        .whereType<Map<String, dynamic>>()
        .map(ChatMessage.fromJson)
        .toList();
    return ChatMessagesResponse(
      success: json['success'] as bool? ?? false,
      messages: messages,
      hasMore: json['has_more'] as bool? ?? false,
      nextBeforeId: _readInt(json['next_before_id']) ??
          (messages.isEmpty ? null : messages.first.id),
    );
  }
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.reasoning,
    required this.createdAt,
  });

  final int? id;
  final String role;
  final String content;
  final String reasoning;
  final DateTime? createdAt;

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: _readInt(json['id'] ?? json['message_id']),
      role: json['role']?.toString() ?? 'assistant',
      content: json['content']?.toString() ?? '',
      reasoning: json['reasoning']?.toString() ?? '',
      createdAt: _readDateTime(json['created_at']),
    );
  }
}

class ErrorBankResponse {
  const ErrorBankResponse({
    required this.success,
    required this.questions,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final bool success;
  final List<ErrorBankQuestion> questions;
  final int total;
  final int page;
  final int pageSize;

  factory ErrorBankResponse.fromJson(Map<String, dynamic> json) {
    final rawQuestions = (json['questions'] ??
            json['items'] ??
            json['records'] ??
            json['data']) as List? ??
        const [];
    final questions = rawQuestions
        .whereType<Map<String, dynamic>>()
        .map(ErrorBankQuestion.fromJson)
        .toList();
    return ErrorBankResponse(
      success: json['success'] as bool? ?? false,
      questions: questions,
      total: _readInt(json['total']) ?? questions.length,
      page: _readInt(json['page']) ?? 1,
      pageSize: _readInt(json['page_size'] ?? json['pageSize']) ?? 20,
    );
  }
}

class ErrorBankQuestion {
  const ErrorBankQuestion({
    required this.id,
    required this.questionType,
    required this.subject,
    required this.sectionTitle,
    required this.contentBlocks,
    required this.options,
    required this.knowledgeTags,
  });

  final int id;
  final String questionType;
  final String subject;
  final String sectionTitle;
  final List<ErrorBankQuestionBlock> contentBlocks;
  final List<String> options;
  final List<String> knowledgeTags;

  String get previewText {
    final blocksText = contentBlocks
        .where((block) => !block.isImage)
        .map((block) => block.content.trim())
        .where((text) => text.isNotEmpty)
        .join('\n');
    if (blocksText.isNotEmpty) {
      return blocksText;
    }
    return sectionTitle;
  }

  factory ErrorBankQuestion.fromJson(Map<String, dynamic> json) {
    final rawBlocks = (json['content_blocks'] ??
            json['content_json'] ??
            json['blocks']) as List? ??
        const [];
    final rawOptions =
        (json['options'] ?? json['options_json']) as List? ?? const [];
    final rawTags = json['knowledge_tags'] as List? ?? const [];
    return ErrorBankQuestion(
      id: _readInt(json['id'] ?? json['question_id']) ?? 0,
      questionType: json['question_type']?.toString() ?? '',
      subject: json['subject']?.toString() ?? '',
      sectionTitle: json['section_title']?.toString() ?? '',
      contentBlocks: rawBlocks
          .whereType<Map<String, dynamic>>()
          .map(ErrorBankQuestionBlock.fromJson)
          .toList(),
      options: rawOptions.map((item) => item.toString()).toList(),
      knowledgeTags: rawTags.map((item) => item.toString()).toList(),
    );
  }
}

class ErrorBankQuestionBlock {
  const ErrorBankQuestionBlock({
    required this.blockType,
    required this.content,
  });

  final String blockType;
  final String content;

  bool get isImage => blockType.toLowerCase() == 'image';

  factory ErrorBankQuestionBlock.fromJson(Map<String, dynamic> json) {
    return ErrorBankQuestionBlock(
      blockType: json['block_type']?.toString() ?? 'text',
      content: json['content']?.toString() ?? '',
    );
  }
}

class ChatStreamRequest {
  const ChatStreamRequest({
    required this.message,
    this.modelProvider = 'openai',
    this.modelName,
    this.providerSource,
    this.providerId,
    this.deepThink = false,
    this.contextRefs = const [],
  });

  final String message;
  final String modelProvider;
  final String? modelName;
  final String? providerSource;
  final String? providerId;
  final bool deepThink;
  final List<ChatContextRef> contextRefs;

  Map<String, dynamic> toJson() {
    return {
      'message': message,
      'model_provider': modelProvider,
      if (_hasValue(modelName)) 'model_name': modelName,
      if (_hasValue(providerSource)) 'provider_source': providerSource,
      if (_hasValue(providerId)) 'provider_id': providerId,
      'deep_think': deepThink,
      if (contextRefs.isNotEmpty)
        'context_refs': contextRefs.map((item) => item.toJson()).toList(),
    };
  }
}

class ChatContextRef {
  const ChatContextRef({
    required this.type,
    required this.projectId,
    required this.questionIds,
  });

  final String type;
  final int projectId;
  final List<int> questionIds;

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'project_id': projectId,
      'question_ids': questionIds,
    };
  }
}

class ChatStreamEvent {
  const ChatStreamEvent({
    this.token,
    this.reasoning,
    this.error,
    this.done = false,
    this.raw = const {},
  });

  final String? token;
  final String? reasoning;
  final String? error;
  final bool done;
  final Map<String, dynamic> raw;

  factory ChatStreamEvent.fromJson(Map<String, dynamic> json) {
    return ChatStreamEvent(
      token: json['token']?.toString(),
      reasoning: json['reasoning']?.toString(),
      error: json['error']?.toString(),
      done: json['done'] as bool? ?? false,
      raw: json,
    );
  }
}

class ChatActionResponse {
  const ChatActionResponse({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;

  factory ChatActionResponse.fromJson(
    Map<String, dynamic> json, {
    required String fallbackMessage,
  }) {
    return ChatActionResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString() ?? fallbackMessage,
    );
  }
}

int? _readInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse('$value');
}

DateTime? _readDateTime(dynamic value) {
  return parseBackendDateTime(value);
}

bool _hasValue(String? value) => value != null && value.trim().isNotEmpty;

Stream<ChatStreamEvent> _parseSseEvents(Stream<String> chunks) async* {
  final buffer = StringBuffer();

  await for (final chunk in chunks) {
    buffer.write(chunk);
    var text = buffer.toString();
    var boundary = _findSseBoundary(text);

    while (boundary != -1) {
      final frame = text.substring(0, boundary).trim();
      text = text.substring(_boundaryEndIndex(text, boundary));

      final event = _parseSseFrame(frame);
      if (event != null) {
        yield event;
      }

      boundary = _findSseBoundary(text);
    }

    buffer
      ..clear()
      ..write(text);
  }

  final tail = buffer.toString().trim();
  final event = _parseSseFrame(tail);
  if (event != null) {
    yield event;
  }
}

int _findSseBoundary(String text) {
  final lf = text.indexOf('\n\n');
  final crlf = text.indexOf('\r\n\r\n');
  if (lf == -1) {
    return crlf;
  }
  if (crlf == -1) {
    return lf;
  }
  return lf < crlf ? lf : crlf;
}

int _boundaryEndIndex(String text, int boundary) {
  return text.startsWith('\r\n\r\n', boundary) ? boundary + 4 : boundary + 2;
}

ChatStreamEvent? _parseSseFrame(String frame) {
  if (frame.isEmpty) {
    return null;
  }

  final dataLines = frame
      .split(RegExp(r'\r?\n'))
      .where((line) => line.startsWith('data:'))
      .map((line) => line.substring(5).trim())
      .where((line) => line.isNotEmpty)
      .toList();

  if (dataLines.isEmpty) {
    return null;
  }

  final data = dataLines.join('\n');
  if (data == '[DONE]') {
    return const ChatStreamEvent(done: true);
  }

  final decoded = jsonDecode(data);
  if (decoded is Map<String, dynamic>) {
    return ChatStreamEvent.fromJson(decoded);
  }
  if (decoded is Map) {
    return ChatStreamEvent.fromJson(decoded.cast<String, dynamic>());
  }

  return ChatStreamEvent(token: decoded.toString());
}
