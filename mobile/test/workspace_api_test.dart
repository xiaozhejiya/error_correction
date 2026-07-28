import 'dart:convert';

import 'package:error_log_app/core/network/api_client.dart';
import 'package:error_log_app/features/workspace/data/workspace_api.dart';
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

  test('获取错题库项目列表时携带 project_type=question 并解析数量', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/projects');
        expect(request.url.queryParameters['project_type'], 'question');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'projects': [
              {
                'id': 12,
                'public_id': 'pub-12',
                'name': 'math',
                'title': '数学',
                'project_type': 'question',
                'summary': '单元错题',
                'description': '数学错题',
                'color': '#8B72FF',
                'icon': 'database',
                'is_default': false,
                'question_count': 4,
                'note_count': 0,
                'updated_at': '2026-05-31T08:00:00',
              },
            ],
          })),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.getProjects(projectType: 'question');

    expect(response.success, isTrue);
    expect(response.projects, hasLength(1));
    expect(response.projects.single.id, 12);
    expect(response.projects.single.displayName, '数学');
    expect(response.projects.single.questionCount, 4);
    expect(response.projects.single.isQuestionProject, isTrue);
  });

  test('导入选中题目到错题库时发送后端要求的负载', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/save-to-db');
        expect(request.headers['cookie'], 'session=test-session');
        expect(
          jsonDecode(request.body),
          {
            'run_id': 'run-001',
            'project_id': 12,
            'selected_ids': ['0', '1'],
          },
        );

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '导入成功'})),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.saveSplitQuestionsToDb(
      runId: 'run-001',
      projectId: 12,
      selectedIds: const ['0', '1'],
    );

    expect(response.success, isTrue);
    expect(response.message, '导入成功');
  });

  test('重置上传会话时发送后端要求的空负载', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/upload/reset');
        expect(request.headers['cookie'], 'session=test-session');
        expect(jsonDecode(request.body), <String, dynamic>{});

        return http.Response.bytes(
          utf8.encode(jsonEncode({'success': true, 'message': '已重置'})),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.resetUploadSession();

    expect(response.success, isTrue);
    expect(response.message, '已重置');
  });

  test('整理笔记预览时上传原图文件且不传 project_id', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/notes/');
        expect(request.headers['cookie'], 'session=test-session');
        expect(
          request.headers['content-type'],
          contains('multipart/form-data'),
        );

        final bodyText = utf8.decode(request.bodyBytes, allowMalformed: true);
        expect(bodyText, contains('name="files"'));
        expect(bodyText, contains('note.jpg'));
        expect(bodyText, contains('name="model_provider"'));
        expect(bodyText, contains('openai'));
        expect(bodyText, contains('name="model_name"'));
        expect(bodyText, contains('gpt-4o-mini'));
        expect(bodyText, isNot(contains('name="project_id"')));

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'note_preview': {
              'title': '四边形笔记',
              'subject': '初中数学',
              'content_markdown': r'''## 平行四边形
$AB=CD$''',
              'knowledge_tags': ['平行四边形'],
              'source_images': ['/images/note.jpg'],
              'ocr_text': 'OCR 原文',
            },
          })),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.organizeNotePreview(
      files: const [
        UploadFileItem(filename: 'note.jpg', bytes: [1, 2, 3]),
      ],
      modelRequest: const SplitRequest(
        modelProvider: 'openai',
        modelName: 'gpt-4o-mini',
        providerSource: null,
        providerId: null,
      ),
    );

    expect(response.success, isTrue);
    expect(response.notePreview?.displayTitle, '四边形笔记');
    expect(response.notePreview?.displaySubject, '初中数学');
    expect(response.notePreview?.contentMarkdown, contains(r'$AB=CD$'));
    expect(response.notePreview?.knowledgeTags, contains('平行四边形'));
  });

  test('保存整理后的笔记预览时发送指定笔记本和预览内容', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/notes/save-organized');
        expect(request.headers['cookie'], 'session=test-session');
        expect(
          jsonDecode(request.body),
          {
            'project_id': 21,
            'title': '四边形笔记',
            'subject': '初中数学',
            'content_markdown': '## 平行四边形',
            'source_images': ['/images/note.jpg'],
            'ocr_text': 'OCR 原文',
            'knowledge_tags': ['平行四边形'],
          },
        );

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'note': {
              'id': 4,
              'title': '四边形笔记',
              'subject': '初中数学',
              'content_markdown': '## 平行四边形',
              'source_images': ['/images/note.jpg'],
              'knowledge_tags': ['平行四边形'],
            },
          })),
          201,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.saveOrganizedNote(
      projectId: 21,
      preview: const NotePreview(
        title: '四边形笔记',
        subject: '初中数学',
        contentMarkdown: '## 平行四边形',
        sourceImages: ['/images/note.jpg'],
        ocrText: 'OCR 原文',
        knowledgeTags: ['平行四边形'],
      ),
    );

    expect(response.success, isTrue);
    expect(response.note?.id, 4);
    expect(response.note?.displayTitle, '四边形笔记');
  });

  test('错题库综合查询时携带项目和分页参数并解析题目', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/error-bank');
        expect(request.url.queryParameters['project_id'], '12');
        expect(request.url.queryParameters['page'], '1');
        expect(request.url.queryParameters['page_size'], '10');
        expect(request.url.queryParameters['keyword'], '圆锥');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'total': 1,
            'grand_total': 1,
            'page': 1,
            'page_size': 10,
            'total_pages': 1,
            'items': [
              {
                'id': 34,
                'question_type': '选择题',
                'subject': '高中+数学',
                'content_json': jsonEncode([
                  {
                    'block_type': 'text',
                    'content': r'已知圆锥底面半径为 $\sqrt{3}$',
                  },
                ]),
                'options_json': jsonEncode(['A. \$\\pi\$', 'B. \$3\\pi\$']),
                'image_refs_json': jsonEncode(['/images/q34.png']),
                'knowledge_tags': jsonEncode(['立体几何', '圆锥体积']),
                'review_status': '待复习',
                'review_is_due': true,
                'review_count': 2,
                'review_interval_days': 7,
                'needs_correction': true,
                'original_filename': 'test2.jpg',
                'ease_factor': 2.5,
              },
            ],
          })),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.queryErrorBank(
      projectId: 12,
      keyword: '圆锥',
    );

    expect(response.success, isTrue);
    expect(response.items, hasLength(1));
    expect(response.items.single.id, 34);
    expect(response.items.single.previewText, contains(r'\sqrt{3}'));
    expect(response.items.single.options, hasLength(2));
    expect(response.items.single.imageRefs.single, '/images/q34.png');
    expect(response.items.single.knowledgeTags, contains('圆锥体积'));
    expect(response.items.single.reviewCount, 2);
    expect(response.items.single.needsCorrection, isTrue);
    expect(response.items.single.originalFilename, 'test2.jpg');
    expect(response.items.single.easeFactor, 2.5);
    expect(response.hasMore, isFalse);
  });

  test('分页查询笔记时携带项目和关键词并解析笔记', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/notes/');
        expect(request.url.queryParameters['project_id'], '21');
        expect(request.url.queryParameters['page'], '2');
        expect(request.url.queryParameters['limit'], '10');
        expect(request.url.queryParameters['keyword'], '四边形');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'total': 11,
            'page': 2,
            'limit': 10,
            'total_pages': 2,
            'items': [
              {
                'id': 116,
                'title': '第四章 四边形',
                'subject': '数学',
                'summary': '平行四边形定义与性质',
                'content_markdown': r'''## 第四章 四边形
![图](/images/quad.jpg)
$AB \parallel CD$''',
                'knowledge_tags': ['平行四边形'],
                'source_images': [
                  r'C:\Users\15184\Desktop\error_correction\backend\runtime_data\uploads\quad.jpg',
                ],
                'review_status': '待复习',
                'review_is_due': true,
                'review_count': 1,
                'review_interval_days': 3,
                'ease_factor': 2.5,
                'content_json': [
                  {
                    'block_type': 'text',
                    'content': '两组对边分别平行的四边形叫做平行四边形。',
                  },
                ],
              },
            ],
          })),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.queryNotes(
      projectId: 21,
      page: 2,
      keyword: '四边形',
    );

    expect(response.success, isTrue);
    expect(response.items, hasLength(1));
    expect(response.items.single.displayTitle, '第四章 四边形');
    expect(
        response.items.single.previewText, contains('![图](/images/quad.jpg)'));
    expect(response.items.single.imageRefs.single, contains('quad.jpg'));
    expect(response.items.single.reviewStatus, '待复习');
    expect(response.items.single.reviewCount, 1);
    expect(response.items.single.easeFactor, 2.5);
    expect(response.hasMore, isFalse);
  });

  test('查询最近分割记录时携带 limit 并解析记录', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/split-records');
        expect(request.url.queryParameters['limit'], '20');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'records': [
              {
                'id': 9,
                'run_id': 'run-history-9',
                'subject': null,
                'model_provider': 'openai',
                'file_names': ['test.jpg'],
                'question_count': 1,
                'created_at': '2026-06-01T12:52:00',
                'questions': [
                  {
                    'id': 101,
                    'uid': 'tmp-101',
                    'question_type': '选择题',
                    'content_blocks': [
                      {
                        'block_type': 'text',
                        'content': '若 a+b=1，求 a 的值。',
                      },
                    ],
                    'has_formula': true,
                    'has_image': false,
                    'needs_correction': false,
                    'knowledge_tags': ['代数'],
                  },
                ],
              },
            ],
          })),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.getSplitRecords(limit: 20);

    expect(response.success, isTrue);
    expect(response.records, hasLength(1));
    expect(response.records.single.displaySubject, '未识别');
    expect(response.records.single.runId, 'run-history-9');
    expect(response.records.single.fileNames.single, 'test.jpg');
    expect(response.records.single.questionCount, 1);
    expect(response.records.single.questions.single.uid, 'tmp-101');
    expect(response.records.single.questions.single.plainText, contains('a+b'));
  });

  test('获取分割记录详情时请求 record_id 并解析题目', () async {
    final client = ApiClient(
      baseUrl: 'http://server.test',
      httpClient: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/split-records/9');
        expect(request.headers['cookie'], 'session=test-session');

        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'success': true,
            'message': 'ok',
            'record': {
              'id': 9,
              'run_id': 'run-history-9',
              'subject': '小学数学',
              'model_provider': 'openai',
              'file_names': ['paper.jpg'],
              'question_count': 2,
              'created_at': '2026-06-01T12:52:00',
              'questions': [
                {
                  'id': 101,
                  'uid': 'tmp-101',
                  'question_type': '填空题',
                  'content_blocks': [
                    {
                      'block_type': 'text',
                      'content': '11 × 4 =',
                    },
                  ],
                  'has_formula': true,
                  'has_image': false,
                  'needs_correction': false,
                  'knowledge_tags': ['乘法估算'],
                },
              ],
            },
          })),
          200,
        );
      }),
    );

    final api = WorkspaceApi(client: client);
    final response = await api.getSplitRecordDetail(recordId: 9);

    expect(response.success, isTrue);
    expect(response.message, 'ok');
    expect(response.record, isNotNull);
    expect(response.record!.displaySubject, '小学数学');
    expect(response.record!.runId, 'run-history-9');
    expect(response.record!.questionCount, 2);
    expect(response.record!.questions.single.questionType, '填空题');
    expect(response.record!.questions.single.knowledgeTags.single, '乘法估算');
  });
}
