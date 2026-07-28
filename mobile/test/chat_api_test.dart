import 'dart:convert';

import 'package:error_log_app/core/network/api_client.dart';
import 'package:error_log_app/features/chat/data/chat_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=test-session',
    });
  });

  test('获取当前用户独立对话列表时携带分页参数和 session cookie', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/chat/my-sessions');
        expect(request.url.queryParameters['page'], '2');
        expect(request.url.queryParameters['limit'], '30');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'total': 1,
            'sessions': [
              {
                'id': 'session-001',
                'question_id': null,
                'title': '你好',
                'created_at': '2026-05-20T01:16:39.020457',
                'updated_at': '2026-05-31T07:28:05.564490',
              },
            ],
          })),
          200,
        );
      }),
    );

    final api = ChatApi(client: client);
    final response = await api.getMySessions(page: 2, limit: 30);

    expect(response.success, isTrue);
    expect(response.total, 1);
    expect(response.sessions.single.id, 'session-001');
    expect(response.sessions.single.title, '你好');
  });

  test('修改对话标题时发送 PATCH 请求', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/api/chat/session-001');
        expect(request.headers['cookie'], 'session=test-session');
        expect(jsonDecode(request.body), {'title': '新的标题'});

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '修改成功'})),
          200,
        );
      }),
    );

    final api = ChatApi(client: client);
    final response = await api.renameSession(
      sessionId: 'session-001',
      title: '新的标题',
    );

    expect(response.success, isTrue);
    expect(response.message, '修改成功');
  });

  test('删除对话时发送 DELETE 请求', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/api/chat/session-001');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '删除成功'})),
          200,
        );
      }),
    );

    final api = ChatApi(client: client);
    final response = await api.deleteSession(sessionId: 'session-001');

    expect(response.success, isTrue);
    expect(response.message, '删除成功');
  });

  test('创建新对话时发送 POST 请求并解析 session id', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/chat');
        expect(request.headers['cookie'], 'session=test-session');
        expect(jsonDecode(request.body), {
          'title': '新对话',
          'question_id': 101,
        });

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'message': '创建成功',
            'session': {
              'id': 'session-new',
              'question_id': 101,
              'title': '新对话',
            },
          })),
          200,
        );
      }),
    );

    final api = ChatApi(client: client);
    final response = await api.createSession(
      title: '新对话',
      questionId: 101,
    );

    expect(response.success, isTrue);
    expect(response.sessionId, 'session-new');
    expect(response.session?.questionId, 101);
  });

  test('游标分页获取对话消息时携带 before_id', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/chat/session-001/messages');
        expect(request.url.queryParameters['limit'], '30');
        expect(request.url.queryParameters['before_id'], '88');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'messages': [
              {
                'id': 90,
                'role': 'assistant',
                'content': r'答案是 $x^2$',
                'reasoning': '推理过程',
                'created_at': '2026-05-31T07:28:05.564490',
              },
            ],
            'has_more': true,
          })),
          200,
        );
      }),
    );

    final api = ChatApi(client: client);
    final response = await api.getMessages(
      sessionId: 'session-001',
      limit: 30,
      beforeId: 88,
    );

    expect(response.success, isTrue);
    expect(response.hasMore, isTrue);
    expect(response.messages.single.id, 90);
    expect(response.messages.single.content, r'答案是 $x^2$');
  });

  test('错题库综合查询时携带项目和分页参数并解析题目', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/error-bank');
        expect(request.url.queryParameters['page'], '2');
        expect(request.url.queryParameters['page_size'], '20');
        expect(request.url.queryParameters['project_id'], '12');
        expect(request.url.queryParameters['keyword'], '圆锥');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'total': 1,
            'questions': [
              {
                'id': 34,
                'question_type': '选择题',
                'subject': '高中+数学',
                'content_blocks': [
                  {
                    'block_type': 'text',
                    'content': r'已知圆锥底面半径为 $\sqrt{3}$',
                  },
                ],
                'knowledge_tags': ['圆锥', '体积'],
              },
            ],
          })),
          200,
        );
      }),
    );

    final api = ChatApi(client: client);
    final response = await api.queryErrorBank(
      page: 2,
      pageSize: 20,
      projectId: 12,
      keyword: '圆锥',
    );

    expect(response.success, isTrue);
    expect(response.total, 1);
    expect(response.questions.single.id, 34);
    expect(response.questions.single.previewText, contains('圆锥'));
  });

  test('SSE 流式对话发送模型和引用题目参数并解析事件', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/chat/session-001/stream');
        expect(request.headers['accept'], 'text/event-stream');
        expect(request.headers['cookie'], 'session=test-session');
        expect(jsonDecode(request.body), {
          'message': '讲一下这道题',
          'model_provider': 'openai',
          'model_name': 'deepseek-v4-flash',
          'provider_source': 'system',
          'provider_id': 'provider-001',
          'deep_think': true,
          'context_refs': [
            {
              'type': 'question',
              'project_id': 12,
              'question_ids': [34, 35],
            },
          ],
        });

        return http.Response.bytes(
          utf8.encode(
            'data: {"token":"你好"}\n\n'
            'data: {"reasoning":"先分析"}\n\n'
            'data: {"done":true}\n\n',
          ),
          200,
          headers: {'content-type': 'text/event-stream'},
        );
      }),
    );

    final api = ChatApi(client: client);
    final events = await api
        .streamMessage(
          sessionId: 'session-001',
          request: const ChatStreamRequest(
            message: '讲一下这道题',
            modelProvider: 'openai',
            modelName: 'deepseek-v4-flash',
            providerSource: 'system',
            providerId: 'provider-001',
            deepThink: true,
            contextRefs: [
              ChatContextRef(
                type: 'question',
                projectId: 12,
                questionIds: [34, 35],
              ),
            ],
          ),
        )
        .toList();

    expect(events.map((event) => event.token).whereType<String>(), ['你好']);
    expect(events.map((event) => event.reasoning).whereType<String>(), ['先分析']);
    expect(events.last.done, isTrue);
  });
}
