import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../core/network/api_client.dart';
import '../../../core/utils/time_format.dart';

class WorkspaceApi {
  WorkspaceApi({ApiClient? client}) : _client = client ?? ApiClient();

  final ApiClient _client;

  Future<ModelOptionsResponse> getModelOptions() async {
    final payload = await _client.getJson('/api/models/options');
    return ModelOptionsResponse.fromJson(payload);
  }

  Future<SystemStatusResponse> getSystemStatus() async {
    final payload = await _client.getJson('/api/status');
    return SystemStatusResponse.fromJson(payload);
  }

  Future<UploadResponse> uploadFiles({
    required List<UploadFileItem> files,
    bool resetSession = false,
  }) async {
    if (files.isEmpty) {
      return const UploadResponse(
        success: false,
        message: '未选择文件',
        result: UploadResult(
          fileCount: 0,
          files: [],
        ),
      );
    }

    final multipartFiles = <http.MultipartFile>[];

    for (final file in files) {
      multipartFiles.add(
        http.MultipartFile.fromBytes(
          'files',
          file.bytes,
          filename: file.filename,
        ),
      );
    }

    final payload = await _client.postMultipart(
      '/api/upload',
      fields: {
        'reset_session': resetSession ? 'true' : 'false',
      },
      files: multipartFiles,
    );

    return UploadResponse.fromJson(payload);
  }

  Future<CancelUploadedFileResponse> cancelUploadedFile({
    required String fileKey,
  }) async {
    final payload = await _client.postJson(
      '/api/cancel_file',
      {'file_key': fileKey},
    );
    return CancelUploadedFileResponse.fromJson(payload);
  }

  Future<ResetUploadSessionResponse> resetUploadSession() async {
    final payload = await _client.postJson('/api/upload/reset', const {});
    return ResetUploadSessionResponse.fromJson(payload);
  }

  Future<EraseResponse> eraseUploadedFiles() async {
    final payload = await _client.postJson('/api/erase', const {});
    return EraseResponse.fromJson(payload);
  }

  Future<OcrResponse> runOcr() async {
    final payload = await _client.postJson('/api/ocr', const {});
    return OcrResponse.fromJson(payload);
  }

  Future<SplitResponse> splitQuestions({
    required SplitRequest request,
  }) async {
    final payload = await _client.postJson('/api/split', request.toJson());
    return SplitResponse.fromJson(payload);
  }

  Future<SplitRecordsResponse> getSplitRecords({int limit = 10}) async {
    final path = Uri(
      path: '/api/split-records',
      queryParameters: {'limit': '${limit.clamp(1, 100)}'},
    ).toString();
    final payload = await _client.getJson(path);
    return SplitRecordsResponse.fromJson(payload);
  }

  Future<SplitRecordDetailResponse> getSplitRecordDetail({
    required int recordId,
  }) async {
    final payload = await _client.getJson('/api/split-records/$recordId');
    return SplitRecordDetailResponse.fromJson(payload);
  }

  Future<ProjectsResponse> getProjects({String? projectType}) async {
    final path = Uri(
      path: '/api/projects',
      queryParameters: {
        if (projectType != null && projectType.isNotEmpty)
          'project_type': projectType,
      },
    ).toString();
    final payload = await _client.getJson(path);
    return ProjectsResponse.fromJson(payload);
  }

  Future<SaveToDbResponse> saveSplitQuestionsToDb({
    String? runId,
    int? splitRecordId,
    required int projectId,
    required List<String> selectedIds,
    List<Map<String, dynamic>> answers = const [],
  }) async {
    final normalizedRunId = runId?.trim();
    final hasRunId = normalizedRunId != null && normalizedRunId.isNotEmpty;
    final hasSplitRecordId = splitRecordId != null && splitRecordId > 0;

    if (!hasRunId && !hasSplitRecordId) {
      throw const ApiException(
        statusCode: 0,
        message: '缺少分割任务 ID 或分割记录 ID',
      );
    }

    final payload = await _client.postJson('/api/save-to-db', {
      if (hasRunId) 'run_id': normalizedRunId,
      if (hasSplitRecordId) 'split_record_id': splitRecordId,
      'project_id': projectId,
      'selected_ids': selectedIds,
      'answers': answers,
    });

    return SaveToDbResponse.fromJson(payload);
  }

  Future<NotePreviewResponse> organizeNotePreview({
    required List<UploadFileItem> files,
    SplitRequest? modelRequest,
  }) async {
    final multipartFiles = files
        .map(
          (file) => http.MultipartFile.fromBytes(
            'files',
            file.bytes,
            filename: file.filename,
          ),
        )
        .toList();

    final payload = await _client.postMultipart(
      '/api/notes/',
      fields: {
        if (modelRequest != null) ...{
          'model_provider': modelRequest.modelProvider,
          if (_hasValue(modelRequest.modelName))
            'model_name': modelRequest.modelName!,
          if (_hasValue(modelRequest.providerSource))
            'provider_source': modelRequest.providerSource!,
          if (_hasValue(modelRequest.providerId))
            'provider_id': modelRequest.providerId!,
        },
      },
      files: multipartFiles,
      successCodes: const {200, 201},
    );

    return NotePreviewResponse.fromJson(payload);
  }

  Future<NoteSavedResponse> saveOrganizedNote({
    required int projectId,
    required NotePreview preview,
  }) async {
    final payload = await _client.postJson(
      '/api/notes/save-organized',
      preview.toSaveJson(projectId: projectId),
      successCodes: const {200, 201},
    );
    return NoteSavedResponse.fromJson(payload);
  }

  Future<LibraryQuestionListResponse> queryErrorBank({
    int page = 1,
    int pageSize = 10,
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
        if (_hasValue(subject)) 'subject': subject!.trim(),
        if (_hasValue(knowledgeTag)) 'knowledge_tag': knowledgeTag!.trim(),
        if (_hasValue(questionType)) 'question_type': questionType!.trim(),
        if (_hasValue(keyword)) 'keyword': keyword!.trim(),
        if (projectId != null) 'project_id': '$projectId',
        if (_hasValue(reviewStatus)) 'review_status': reviewStatus!.trim(),
        if (_hasValue(startDate)) 'start_date': startDate!.trim(),
        if (_hasValue(endDate)) 'end_date': endDate!.trim(),
      },
    ).toString();
    final payload = await _client.getJson(path);
    return LibraryQuestionListResponse.fromJson(payload);
  }

  Future<LibraryNoteListResponse> queryNotes({
    int page = 1,
    int limit = 10,
    String? subject,
    String? knowledgeTag,
    String? keyword,
    int? projectId,
  }) async {
    final path = Uri(
      path: '/api/notes/',
      queryParameters: {
        'page': '$page',
        'limit': '$limit',
        if (_hasValue(subject)) 'subject': subject!.trim(),
        if (_hasValue(knowledgeTag)) 'knowledge_tag': knowledgeTag!.trim(),
        if (_hasValue(keyword)) 'keyword': keyword!.trim(),
        if (projectId != null) 'project_id': '$projectId',
      },
    ).toString();
    final payload = await _client.getJson(path);
    return LibraryNoteListResponse.fromJson(payload);
  }

  Future<Uint8List> loadProtectedImage(String url) {
    return _client.getBytes(url);
  }

  String get baseUrl => _client.baseUrl;
}

class UploadFileItem {
  const UploadFileItem({
    required this.filename,
    required this.bytes,
  });

  final String filename;
  final List<int> bytes;
}

class UploadResponse {
  const UploadResponse({
    required this.success,
    required this.message,
    required this.result,
  });

  final bool success;
  final String message;
  final UploadResult result;

  factory UploadResponse.fromJson(Map<String, dynamic> json) {
    return UploadResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '上传失败',
      result: UploadResult.fromJson(
        (json['result'] as Map?)?.cast<String, dynamic>() ?? {},
      ),
    );
  }
}

class UploadResult {
  const UploadResult({
    required this.fileCount,
    required this.files,
  });

  final int fileCount;
  final List<UploadedFile> files;

  factory UploadResult.fromJson(Map<String, dynamic> json) {
    final rawFiles = (json['files'] as List?) ?? const [];
    return UploadResult(
      fileCount: (json['file_count'] as int?) ?? rawFiles.length,
      files: rawFiles
          .whereType<Map<String, dynamic>>()
          .map(UploadedFile.fromJson)
          .toList(),
    );
  }
}

class UploadedFile {
  const UploadedFile({
    required this.fileKey,
    required this.filename,
  });

  final String fileKey;
  final String filename;

  factory UploadedFile.fromJson(Map<String, dynamic> json) {
    return UploadedFile(
      fileKey: json['file_key'] as String? ?? '',
      filename: json['filename'] as String? ?? '',
    );
  }
}

class CancelUploadedFileResponse {
  const CancelUploadedFileResponse({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;

  factory CancelUploadedFileResponse.fromJson(Map<String, dynamic> json) {
    return CancelUploadedFileResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '操作失败',
    );
  }
}

class ResetUploadSessionResponse {
  const ResetUploadSessionResponse({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;

  factory ResetUploadSessionResponse.fromJson(Map<String, dynamic> json) {
    return ResetUploadSessionResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '操作失败',
    );
  }
}

class EraseResponse {
  const EraseResponse({
    required this.success,
    required this.message,
    required this.files,
  });

  final bool success;
  final String message;
  final List<EraseResultFile> files;

  factory EraseResponse.fromJson(Map<String, dynamic> json) {
    final rawResult = json['result'];
    final fileList = <EraseResultFile>[];

    void collectFiles(dynamic rawFiles) {
      if (rawFiles is! List) {
        return;
      }

      for (final item in rawFiles) {
        if (item is Map) {
          fileList.add(EraseResultFile.fromJson(item.cast<String, dynamic>()));
        }
      }
    }

    if (rawResult is List) {
      collectFiles(rawResult);
    } else if (rawResult is Map) {
      collectFiles(rawResult['files']);
      collectFiles(rawResult['images']);
    }

    collectFiles(json['files']);
    collectFiles(json['images']);

    fileList.sort((a, b) {
      final left = a.index;
      final right = b.index;
      if (left == null && right == null) {
        return 0;
      }
      if (left == null) {
        return 1;
      }
      if (right == null) {
        return -1;
      }
      return left.compareTo(right);
    });

    return EraseResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '操作失败',
      files: fileList,
    );
  }
}

class EraseResultFile {
  const EraseResultFile({
    required this.fileKey,
    required this.beforeFileKey,
    required this.afterFileKey,
    required this.beforeImageUrl,
    required this.afterImageUrl,
    this.index,
  });

  final String fileKey;
  final String? beforeFileKey;
  final String? afterFileKey;
  final String? beforeImageUrl;
  final String? afterImageUrl;
  final int? index;

  factory EraseResultFile.fromJson(Map<String, dynamic> json) {
    final rawIndex = json['index'];
    final index = rawIndex is int ? rawIndex : int.tryParse('$rawIndex');

    return EraseResultFile(
      fileKey:
          (json['file_key'] ?? json['name'] ?? json['index'] ?? '').toString(),
      beforeFileKey: json['before_file_key']?.toString(),
      afterFileKey: json['after_file_key']?.toString(),
      beforeImageUrl:
          (json['before_image_url'] ?? json['original_url'])?.toString(),
      afterImageUrl:
          (json['after_image_url'] ?? json['erased_url'])?.toString(),
      index: index,
    );
  }
}

class OcrResponse {
  const OcrResponse({
    required this.success,
    required this.message,
    required this.pages,
    required this.totalBlocks,
  });

  final bool success;
  final String message;
  final List<OcrPage> pages;
  final int totalBlocks;

  factory OcrResponse.fromJson(Map<String, dynamic> json) {
    final rawPages = (json['pages'] as List?) ?? const [];
    return OcrResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? 'OCR 失败',
      pages: rawPages
          .whereType<Map<String, dynamic>>()
          .map(OcrPage.fromJson)
          .toList()
        ..sort((a, b) => a.pageIndex.compareTo(b.pageIndex)),
      totalBlocks: _readInt(json['total_blocks']) ?? 0,
    );
  }
}

class OcrPage {
  const OcrPage({
    required this.pageIndex,
    required this.pageWidth,
    required this.pageHeight,
    required this.imageUrl,
    required this.blocks,
  });

  final int pageIndex;
  final double pageWidth;
  final double pageHeight;
  final String? imageUrl;
  final List<OcrBlock> blocks;

  factory OcrPage.fromJson(Map<String, dynamic> json) {
    final rawBlocks = (json['blocks'] as List?) ?? const [];
    return OcrPage(
      pageIndex: _readInt(json['page_index']) ?? 0,
      pageWidth: (_readNum(json['page_width']) ?? 1).toDouble(),
      pageHeight: (_readNum(json['page_height']) ?? 1).toDouble(),
      imageUrl: json['image_url']?.toString(),
      blocks: rawBlocks
          .whereType<Map<String, dynamic>>()
          .map(OcrBlock.fromJson)
          .toList(),
    );
  }
}

class OcrBlock {
  const OcrBlock({
    required this.bbox,
    required this.content,
    required this.label,
  });

  final List<double> bbox;
  final String content;
  final String label;

  bool get hasValidBox =>
      bbox.length == 4 && bbox[2] > bbox[0] && bbox[3] > bbox[1];

  factory OcrBlock.fromJson(Map<String, dynamic> json) {
    final rawBox = (json['bbox'] as List?) ?? const [];
    return OcrBlock(
      bbox: rawBox
          .map(_readNum)
          .whereType<num>()
          .map((item) => item.toDouble())
          .toList(growable: false),
      content: json['content']?.toString() ?? '',
      label: json['label']?.toString() ?? 'text',
    );
  }
}

class SplitRequest {
  const SplitRequest({
    required this.modelProvider,
    required this.modelName,
    required this.providerSource,
    required this.providerId,
  });

  final String modelProvider;
  final String? modelName;
  final String? providerSource;
  final String? providerId;

  Map<String, dynamic> toJson() {
    return {
      'model_provider': modelProvider,
      'model_name': modelName,
      'provider_source': providerSource,
      'provider_id': providerId,
    };
  }
}

class SplitResponse {
  const SplitResponse({
    required this.success,
    required this.message,
    required this.runId,
    required this.questions,
    required this.warnings,
  });

  final bool success;
  final String message;
  final String? runId;
  final List<SplitQuestion> questions;
  final List<String> warnings;

  factory SplitResponse.fromJson(Map<String, dynamic> json) {
    final rawQuestions = (json['questions'] as List?) ?? const [];
    final rawWarnings = (json['warnings'] as List?) ?? const [];
    return SplitResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '题目分割失败',
      runId: json['run_id']?.toString(),
      questions: rawQuestions
          .whereType<Map<String, dynamic>>()
          .map(SplitQuestion.fromJson)
          .toList(),
      warnings: rawWarnings.map((item) => item.toString()).toList(),
    );
  }
}

class SplitQuestion {
  const SplitQuestion({
    required this.uid,
    required this.questionId,
    required this.questionType,
    required this.sectionTitle,
    required this.contentBlocks,
    required this.options,
    required this.imageRefs,
    required this.optionImages,
    required this.hasFormula,
    required this.hasImage,
    required this.needsCorrection,
    required this.knowledgeTags,
  });

  final String uid;
  final String questionId;
  final String? questionType;
  final String? sectionTitle;
  final List<SplitQuestionBlock> contentBlocks;
  final List<String> options;
  final List<String> imageRefs;
  final List<String> optionImages;
  final bool hasFormula;
  final bool hasImage;
  final bool needsCorrection;
  final List<String> knowledgeTags;

  String get plainText {
    return contentBlocks
        .map((block) => block.content)
        .where((text) => text.trim().isNotEmpty)
        .join('\n');
  }

  factory SplitQuestion.fromJson(Map<String, dynamic> json) {
    final rawBlocks = (json['content_blocks'] as List?) ??
        (json['content_json'] as List?) ??
        const [];
    final rawOptions = (json['options'] as List?) ??
        (json['options_json'] as List?) ??
        const [];
    final rawTags = (json['knowledge_tags'] as List?) ?? const [];
    final rawImageRefs = (json['image_refs'] as List?) ?? const [];
    final rawOptionImages = (json['option_images'] as List?) ?? const [];

    return SplitQuestion(
      uid: (json['uid'] ?? json['id'] ?? '').toString(),
      questionId: (json['question_id'] ?? json['id'] ?? '').toString(),
      questionType: json['question_type']?.toString(),
      sectionTitle: json['section_title']?.toString(),
      contentBlocks: rawBlocks
          .whereType<Map<String, dynamic>>()
          .map(SplitQuestionBlock.fromJson)
          .toList(),
      options: rawOptions.map((item) => item.toString()).toList(),
      imageRefs: rawImageRefs.map((item) => item.toString()).toList(),
      optionImages: rawOptionImages.map((item) => item.toString()).toList(),
      hasFormula: json['has_formula'] as bool? ?? false,
      hasImage: json['has_image'] as bool? ?? false,
      needsCorrection: json['needs_correction'] as bool? ?? false,
      knowledgeTags: rawTags.map((item) => item.toString()).toList(),
    );
  }
}

class SplitQuestionBlock {
  const SplitQuestionBlock({
    required this.blockType,
    required this.content,
  });

  final String blockType;
  final String content;

  bool get isImage => blockType.toLowerCase() == 'image';

  factory SplitQuestionBlock.fromJson(Map<String, dynamic> json) {
    return SplitQuestionBlock(
      blockType: json['block_type']?.toString() ?? 'text',
      content: json['content']?.toString() ?? '',
    );
  }
}

class SplitRecordsResponse {
  const SplitRecordsResponse({
    required this.success,
    required this.records,
  });

  final bool success;
  final List<SplitRecord> records;

  factory SplitRecordsResponse.fromJson(Map<String, dynamic> json) {
    final rawRecords = (json['records'] as List?) ?? const [];
    return SplitRecordsResponse(
      success: json['success'] as bool? ?? false,
      records: rawRecords
          .whereType<Map<String, dynamic>>()
          .map(SplitRecord.fromJson)
          .toList(growable: false),
    );
  }
}

class SplitRecordDetailResponse {
  const SplitRecordDetailResponse({
    required this.success,
    required this.message,
    required this.record,
  });

  final bool success;
  final String message;
  final SplitRecord? record;

  factory SplitRecordDetailResponse.fromJson(Map<String, dynamic> json) {
    final recordJson = _readSplitRecordJson(json);
    return SplitRecordDetailResponse(
      success: json['success'] as bool? ?? false,
      message: (json['message'] ?? json['error'] ?? '').toString(),
      record: recordJson == null ? null : SplitRecord.fromJson(recordJson),
    );
  }

  static Map<String, dynamic>? _readSplitRecordJson(
    Map<String, dynamic> json,
  ) {
    for (final key in const ['record', 'split_record', 'data', 'result']) {
      final value = json[key];
      if (value is! Map<String, dynamic>) {
        continue;
      }

      final nestedRecord = value['record'];
      if (nestedRecord is Map<String, dynamic>) {
        return nestedRecord;
      }
      return value;
    }

    if (json.containsKey('id') ||
        json.containsKey('questions') ||
        json.containsKey('question_count')) {
      return json;
    }
    return null;
  }
}

class SplitRecord {
  const SplitRecord({
    required this.id,
    required this.subject,
    required this.modelProvider,
    required this.fileNames,
    required this.originalImages,
    required this.questionCount,
    required this.createdAt,
    required this.questions,
  });

  final int id;
  final String? subject;
  final String? modelProvider;
  final List<String> fileNames;
  final List<String> originalImages;
  final int questionCount;
  final DateTime? createdAt;
  final List<SplitQuestion> questions;

  String get displaySubject {
    final value = subject?.trim();
    return value == null || value.isEmpty ? '未识别' : value;
  }

  factory SplitRecord.fromJson(Map<String, dynamic> json) {
    final rawFileNames = (json['file_names'] as List?) ?? const [];
    final rawOriginalImages = (json['original_images'] as List?) ?? const [];
    final rawQuestions = (json['questions'] as List?) ?? const [];
    return SplitRecord(
      id: _readInt(json['id']) ?? 0,
      subject: json['subject']?.toString(),
      modelProvider: json['model_provider']?.toString(),
      fileNames: rawFileNames.map((item) => item.toString()).toList(),
      originalImages: rawOriginalImages.map((item) => item.toString()).toList(),
      questionCount: _readInt(json['question_count']) ?? rawQuestions.length,
      createdAt: _readDateTime(json['created_at']),
      questions: rawQuestions
          .whereType<Map<String, dynamic>>()
          .map(SplitQuestion.fromJson)
          .toList(growable: false),
    );
  }
}

class ProjectsResponse {
  const ProjectsResponse({
    required this.success,
    required this.projects,
  });

  final bool success;
  final List<WorkspaceProject> projects;

  factory ProjectsResponse.fromJson(Map<String, dynamic> json) {
    final rawProjects = (json['projects'] as List?) ?? const [];
    return ProjectsResponse(
      success: json['success'] as bool? ?? false,
      projects: rawProjects
          .whereType<Map<String, dynamic>>()
          .map(WorkspaceProject.fromJson)
          .toList(),
    );
  }
}

class WorkspaceProject {
  const WorkspaceProject({
    required this.id,
    required this.publicId,
    required this.name,
    required this.title,
    required this.projectType,
    required this.summary,
    required this.description,
    required this.color,
    required this.icon,
    required this.isDefault,
    required this.questionCount,
    required this.noteCount,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final String publicId;
  final String name;
  final String title;
  final String projectType;
  final String summary;
  final String description;
  final String color;
  final String icon;
  final bool isDefault;
  final int questionCount;
  final int noteCount;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  bool get isQuestionProject => projectType == 'question';
  bool get isNoteProject => projectType == 'note';
  String get displayName => title.trim().isNotEmpty ? title : name;
  String get displayDescription {
    if (summary.trim().isNotEmpty) {
      return summary;
    }
    if (description.trim().isNotEmpty) {
      return description;
    }
    return '暂无描述';
  }

  int get itemCount => isQuestionProject ? questionCount : noteCount;

  factory WorkspaceProject.fromJson(Map<String, dynamic> json) {
    return WorkspaceProject(
      id: _readInt(json['id']) ?? 0,
      publicId: json['public_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      projectType: json['project_type']?.toString() ?? '',
      summary: json['summary']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      color: json['color']?.toString() ?? '',
      icon: json['icon']?.toString() ?? '',
      isDefault: json['is_default'] as bool? ?? false,
      questionCount: _readInt(json['question_count']) ?? 0,
      noteCount: _readInt(json['note_count']) ?? 0,
      createdAt: _readDateTime(json['created_at']),
      updatedAt: _readDateTime(json['updated_at']),
    );
  }
}

class SaveToDbResponse {
  const SaveToDbResponse({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;

  factory SaveToDbResponse.fromJson(Map<String, dynamic> json) {
    return SaveToDbResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString() ?? '导入失败',
    );
  }
}

class NotePreviewResponse {
  const NotePreviewResponse({
    required this.success,
    required this.notePreview,
  });

  final bool success;
  final NotePreview? notePreview;

  factory NotePreviewResponse.fromJson(Map<String, dynamic> json) {
    final rawPreview = json['note_preview'];
    return NotePreviewResponse(
      success: json['success'] as bool? ?? false,
      notePreview: rawPreview is Map
          ? NotePreview.fromJson(rawPreview.cast<String, dynamic>())
          : null,
    );
  }
}

class NotePreview {
  const NotePreview({
    required this.title,
    required this.subject,
    required this.contentMarkdown,
    required this.knowledgeTags,
    required this.sourceImages,
    required this.ocrText,
  });

  final String title;
  final String subject;
  final String contentMarkdown;
  final List<String> knowledgeTags;
  final List<String> sourceImages;
  final String ocrText;

  String get displayTitle => title.trim().isEmpty ? '未命名笔记' : title.trim();
  String get displaySubject => subject.trim().isEmpty ? '未知' : subject.trim();

  Map<String, dynamic> toSaveJson({required int projectId}) {
    return {
      'project_id': projectId,
      'title': displayTitle,
      'subject': displaySubject,
      'content_markdown': contentMarkdown,
      'source_images': sourceImages,
      'ocr_text': ocrText,
      'knowledge_tags': knowledgeTags,
    };
  }

  factory NotePreview.fromJson(Map<String, dynamic> json) {
    return NotePreview(
      title: json['title']?.toString() ?? '',
      subject: json['subject']?.toString() ?? '',
      contentMarkdown: json['content_markdown']?.toString() ?? '',
      knowledgeTags: _readStringList(json['knowledge_tags']),
      sourceImages: _readStringList(json['source_images']),
      ocrText: json['ocr_text']?.toString() ?? '',
    );
  }
}

class NoteSavedResponse {
  const NoteSavedResponse({
    required this.success,
    required this.note,
  });

  final bool success;
  final LibraryNoteItem? note;

  factory NoteSavedResponse.fromJson(Map<String, dynamic> json) {
    final rawNote = json['note'];
    return NoteSavedResponse(
      success: json['success'] as bool? ?? false,
      note: rawNote is Map
          ? LibraryNoteItem.fromJson(rawNote.cast<String, dynamic>())
          : null,
    );
  }
}

class LibraryQuestionListResponse {
  const LibraryQuestionListResponse({
    required this.success,
    required this.items,
    required this.total,
    required this.grandTotal,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });

  final bool success;
  final List<LibraryQuestionItem> items;
  final int total;
  final int grandTotal;
  final int page;
  final int pageSize;
  final int totalPages;

  bool get hasMore => page < totalPages;

  factory LibraryQuestionListResponse.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] ??
            json['questions'] ??
            json['records'] ??
            json['data']) as List? ??
        const [];
    final items = rawItems
        .whereType<Map<String, dynamic>>()
        .map(LibraryQuestionItem.fromJson)
        .toList();
    final pageSize = _readInt(json['page_size'] ?? json['pageSize']) ?? 10;
    final total = _readInt(json['total']) ?? items.length;
    final computedPages =
        pageSize <= 0 ? 1 : ((total + pageSize - 1) ~/ pageSize);
    final totalPages = _readInt(json['total_pages'] ?? json['totalPages']) ??
        (computedPages < 1 ? 1 : computedPages);

    return LibraryQuestionListResponse(
      success: json['success'] as bool? ?? false,
      items: items,
      total: total,
      grandTotal: _readInt(json['grand_total']) ?? total,
      page: _readInt(json['page']) ?? 1,
      pageSize: pageSize,
      totalPages: totalPages,
    );
  }
}

class LibraryQuestionItem {
  const LibraryQuestionItem({
    required this.id,
    required this.questionType,
    required this.subject,
    required this.contentBlocks,
    required this.options,
    required this.imageRefs,
    required this.knowledgeTags,
    required this.reviewStatus,
    required this.reviewIsDue,
    required this.reviewCount,
    required this.reviewIntervalDays,
    required this.reviewDueAt,
    required this.reviewLastAt,
    required this.reviewPriority,
    required this.needsCorrection,
    required this.hasFormula,
    required this.hasImage,
    required this.originalFilename,
    required this.easeFactor,
    required this.answer,
    required this.userAnswer,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final String questionType;
  final String subject;
  final List<LibraryContentBlock> contentBlocks;
  final List<String> options;
  final List<String> imageRefs;
  final List<String> knowledgeTags;
  final String reviewStatus;
  final bool reviewIsDue;
  final int reviewCount;
  final int reviewIntervalDays;
  final DateTime? reviewDueAt;
  final DateTime? reviewLastAt;
  final int? reviewPriority;
  final bool needsCorrection;
  final bool hasFormula;
  final bool hasImage;
  final String originalFilename;
  final double? easeFactor;
  final String? answer;
  final String? userAnswer;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  String get previewText {
    final text = contentBlocks
        .where((block) => !block.isImage)
        .map((block) => block.content.trim())
        .where((item) => item.isNotEmpty)
        .join('\n\n');
    return text.isEmpty ? '暂无题干' : text;
  }

  factory LibraryQuestionItem.fromJson(Map<String, dynamic> json) {
    final rawBlocks = _readMapList(
      json['content_blocks'] ?? json['content_json'] ?? json['blocks'],
    );
    final options = _readStringList(json['options'] ?? json['options_json']);
    final imageRefs =
        _readStringList(json['image_refs'] ?? json['image_refs_json']);
    final knowledgeTags = _readStringList(json['knowledge_tags']);

    return LibraryQuestionItem(
      id: _readInt(json['id'] ?? json['question_id']) ?? 0,
      questionType: json['question_type']?.toString() ?? '',
      subject: json['subject']?.toString() ?? '',
      contentBlocks: rawBlocks.map(LibraryContentBlock.fromJson).toList(),
      options: options,
      imageRefs: imageRefs,
      knowledgeTags: knowledgeTags,
      reviewStatus: json['review_status']?.toString() ?? '',
      reviewIsDue: json['review_is_due'] as bool? ?? false,
      reviewCount: _readInt(json['review_count']) ?? 0,
      reviewIntervalDays: _readInt(json['review_interval_days']) ?? 0,
      reviewDueAt: _readDateTime(json['review_due_at']),
      reviewLastAt: _readDateTime(json['review_last_at']),
      reviewPriority: _readInt(json['review_priority']),
      needsCorrection: json['needs_correction'] as bool? ?? false,
      hasFormula: json['has_formula'] as bool? ?? false,
      hasImage: json['has_image'] as bool? ?? false,
      originalFilename: json['original_filename']?.toString() ?? '',
      easeFactor: _readNum(json['ease_factor'])?.toDouble(),
      answer: json['answer']?.toString(),
      userAnswer: json['user_answer']?.toString(),
      createdAt: _readDateTime(json['created_at']),
      updatedAt: _readDateTime(json['updated_at']),
    );
  }
}

class LibraryNoteListResponse {
  const LibraryNoteListResponse({
    required this.success,
    required this.items,
    required this.total,
    required this.page,
    required this.limit,
    required this.totalPages,
  });

  final bool success;
  final List<LibraryNoteItem> items;
  final int total;
  final int page;
  final int limit;
  final int totalPages;

  bool get hasMore => page < totalPages;

  factory LibraryNoteListResponse.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] ??
            json['notes'] ??
            json['records'] ??
            json['data']) as List? ??
        const [];
    final items = rawItems
        .whereType<Map<String, dynamic>>()
        .map(LibraryNoteItem.fromJson)
        .toList();
    final limit = _readInt(json['limit'] ?? json['page_size']) ?? 10;
    final total = _readInt(json['total']) ?? items.length;
    final computedPages = limit <= 0 ? 1 : ((total + limit - 1) ~/ limit);
    final totalPages = _readInt(json['total_pages'] ?? json['totalPages']) ??
        (computedPages < 1 ? 1 : computedPages);

    return LibraryNoteListResponse(
      success: json['success'] as bool? ?? false,
      items: items,
      total: total,
      page: _readInt(json['page']) ?? 1,
      limit: limit,
      totalPages: totalPages,
    );
  }
}

class LibraryNoteItem {
  const LibraryNoteItem({
    required this.id,
    required this.title,
    required this.subject,
    required this.summary,
    required this.contentMarkdown,
    required this.contentBlocks,
    required this.imageRefs,
    required this.knowledgeTags,
    required this.reviewStatus,
    required this.reviewIsDue,
    required this.reviewCount,
    required this.reviewIntervalDays,
    required this.reviewDueAt,
    required this.reviewLastAt,
    required this.reviewPriority,
    required this.easeFactor,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final String title;
  final String subject;
  final String summary;
  final String contentMarkdown;
  final List<LibraryContentBlock> contentBlocks;
  final List<String> imageRefs;
  final List<String> knowledgeTags;
  final String reviewStatus;
  final bool reviewIsDue;
  final int reviewCount;
  final int reviewIntervalDays;
  final DateTime? reviewDueAt;
  final DateTime? reviewLastAt;
  final int? reviewPriority;
  final double? easeFactor;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  String get displayTitle => title.trim().isEmpty ? '未命名笔记' : title.trim();

  String get previewText {
    if (contentMarkdown.trim().isNotEmpty) {
      return contentMarkdown.trim();
    }
    final text = contentBlocks
        .where((block) => !block.isImage)
        .map((block) => block.content.trim())
        .where((item) => item.isNotEmpty)
        .join('\n\n');
    if (text.isNotEmpty) {
      return text;
    }
    return summary.trim().isEmpty ? '暂无内容' : summary.trim();
  }

  factory LibraryNoteItem.fromJson(Map<String, dynamic> json) {
    final rawBlocks = _readMapList(
      json['content_blocks'] ?? json['content_json'] ?? json['blocks'],
    );
    final rawTags = _readStringList(json['knowledge_tags']);
    final rawImages = [
      ..._readStringList(json['image_refs']),
      ..._readStringList(json['image_refs_json']),
      ..._readStringList(json['source_images']),
    ];
    final content = json['content']?.toString();
    final contentMarkdown = json['content_markdown']?.toString() ?? '';

    return LibraryNoteItem(
      id: _readInt(json['id'] ?? json['note_id']) ?? 0,
      title: (json['title'] ?? json['name'] ?? '').toString(),
      subject: json['subject']?.toString() ?? '',
      summary: (json['summary'] ?? json['description'] ?? '').toString(),
      contentMarkdown: contentMarkdown,
      contentBlocks: [
        ...rawBlocks.map(LibraryContentBlock.fromJson),
        if (_hasValue(content))
          LibraryContentBlock(blockType: 'text', content: content!.trim()),
      ],
      imageRefs: rawImages,
      knowledgeTags: rawTags,
      reviewStatus: json['review_status']?.toString() ?? '',
      reviewIsDue: json['review_is_due'] as bool? ?? false,
      reviewCount: _readInt(json['review_count']) ?? 0,
      reviewIntervalDays: _readInt(json['review_interval_days']) ?? 0,
      reviewDueAt: _readDateTime(json['review_due_at']),
      reviewLastAt: _readDateTime(json['review_last_at']),
      reviewPriority: _readInt(json['review_priority']),
      easeFactor: _readNum(json['ease_factor'])?.toDouble(),
      createdAt: _readDateTime(json['created_at']),
      updatedAt: _readDateTime(json['updated_at']),
    );
  }
}

class LibraryContentBlock {
  const LibraryContentBlock({
    required this.blockType,
    required this.content,
  });

  final String blockType;
  final String content;

  bool get isImage => blockType.toLowerCase() == 'image';

  factory LibraryContentBlock.fromJson(Map<String, dynamic> json) {
    return LibraryContentBlock(
      blockType: json['block_type']?.toString() ?? 'text',
      content: json['content']?.toString() ?? '',
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

num? _readNum(dynamic value) {
  if (value is num) {
    return value;
  }
  return num.tryParse('$value');
}

List<String> _readStringList(dynamic value) {
  if (value == null) {
    return const [];
  }
  if (value is List) {
    return value.map((item) => item.toString()).toList();
  }
  if (value is String) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || trimmed == 'null') {
      return const [];
    }
    try {
      final decoded = jsonDecode(trimmed);
      if (decoded is List) {
        return decoded.map((item) => item.toString()).toList();
      }
    } catch (_) {
      // Treat plain strings as a single item.
    }
    return [trimmed];
  }
  return [value.toString()];
}

List<Map<String, dynamic>> _readMapList(dynamic value) {
  if (value == null) {
    return const [];
  }
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }
  if (value is String) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || trimmed == 'null') {
      return const [];
    }
    try {
      final decoded = jsonDecode(trimmed);
      if (decoded is List) {
        return _readMapList(decoded);
      }
    } catch (_) {
      // Ignore malformed JSON content.
    }
  }
  return const [];
}

DateTime? _readDateTime(dynamic value) {
  return parseBackendDateTime(value);
}

bool _hasValue(String? value) => value != null && value.trim().isNotEmpty;

class ModelOptionsResponse {
  const ModelOptionsResponse({
    required this.success,
    required this.defaultOptionId,
    required this.groups,
    required this.options,
  });

  final bool success;
  final String? defaultOptionId;
  final List<ModelOptionGroup> groups;
  final List<WorkspaceModelOption> options;

  factory ModelOptionsResponse.fromJson(Map<String, dynamic> json) {
    final rawGroups = (json['groups'] as List?) ?? const [];
    final rawOptions = (json['options'] as List?) ?? const [];

    return ModelOptionsResponse(
      success: json['success'] as bool? ?? false,
      defaultOptionId: json['default_option_id'] as String?,
      groups: rawGroups
          .whereType<Map<String, dynamic>>()
          .map(ModelOptionGroup.fromJson)
          .toList(),
      options: rawOptions
          .whereType<Map<String, dynamic>>()
          .map(WorkspaceModelOption.fromJson)
          .toList(),
    );
  }
}

class ModelOptionGroup {
  const ModelOptionGroup({
    required this.key,
    required this.label,
  });

  final String key;
  final String label;

  factory ModelOptionGroup.fromJson(Map<String, dynamic> json) {
    return ModelOptionGroup(
      key: json['key'] as String? ?? '',
      label: json['label'] as String? ?? '',
    );
  }
}

class WorkspaceModelOption {
  const WorkspaceModelOption({
    required this.optionId,
    required this.label,
    required this.modelName,
    required this.source,
    required this.groupLabel,
    required this.groupKey,
    required this.providerName,
    required this.providerId,
    required this.category,
    required this.configured,
    required this.isDefault,
    required this.available,
    required this.supportsFunctionCalling,
    required this.reason,
  });

  final String optionId;
  final String label;
  final String modelName;
  final String source;
  final String groupLabel;
  final String groupKey;
  final String providerName;
  final String providerId;
  final String category;
  final bool configured;
  final bool isDefault;
  final bool available;
  final bool supportsFunctionCalling;
  final String reason;

  bool get isHostedSource =>
      source == 'system' ||
      source == 'hosted' ||
      groupKey == 'system' ||
      groupLabel == '平台托管';
  bool get isSelfSource =>
      source == 'personal' ||
      source == 'self' ||
      groupKey == 'personal' ||
      groupLabel == '自己设置';

  String get displayName => modelName.isNotEmpty ? modelName : label;

  factory WorkspaceModelOption.fromJson(Map<String, dynamic> json) {
    return WorkspaceModelOption(
      optionId: json['option_id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      modelName: json['model_name'] as String? ?? '',
      source: json['source'] as String? ?? '',
      groupLabel: json['group_label'] as String? ?? '',
      groupKey: json['group_key'] as String? ?? '',
      providerName: json['provider_name'] as String? ?? '',
      providerId: json['provider_id'] as String? ?? '',
      category: json['category'] as String? ?? '',
      configured: json['configured'] as bool? ?? false,
      isDefault: json['is_default'] as bool? ?? false,
      available: json['available'] as bool? ?? false,
      supportsFunctionCalling:
          json['supports_function_calling'] as bool? ?? false,
      reason: json['reason'] as String? ?? '',
    );
  }
}

class SystemStatusResponse {
  const SystemStatusResponse({
    required this.success,
    required this.status,
  });

  final bool success;
  final WorkspaceSystemStatus status;

  factory SystemStatusResponse.fromJson(Map<String, dynamic> json) {
    return SystemStatusResponse(
      success: json['success'] as bool? ?? false,
      status: WorkspaceSystemStatus.fromJson(
        (json['status'] as Map?)?.cast<String, dynamic>() ?? {},
      ),
    );
  }
}

class WorkspaceSystemStatus {
  const WorkspaceSystemStatus({
    required this.paddleocrConfigured,
    required this.ensexamConfigured,
    required this.langsmithEnabled,
    required this.availableModels,
    required this.outputDirs,
  });

  final bool paddleocrConfigured;
  final bool ensexamConfigured;
  final bool langsmithEnabled;
  final List<AvailableModelStatus> availableModels;
  final Map<String, String> outputDirs;

  factory WorkspaceSystemStatus.fromJson(Map<String, dynamic> json) {
    final rawModels = (json['available_models'] as List?) ?? const [];
    final rawOutputDirs = (json['output_dirs'] as Map?) ?? const {};

    return WorkspaceSystemStatus(
      paddleocrConfigured: json['paddleocr_configured'] as bool? ?? false,
      ensexamConfigured: json['ensexam_configured'] as bool? ?? false,
      langsmithEnabled: json['langsmith_enabled'] as bool? ?? false,
      availableModels: rawModels
          .whereType<Map<String, dynamic>>()
          .map(AvailableModelStatus.fromJson)
          .toList(),
      outputDirs: rawOutputDirs.map(
        (key, value) => MapEntry(
          key.toString(),
          value?.toString() ?? '',
        ),
      ),
    );
  }
}

class AvailableModelStatus {
  const AvailableModelStatus({
    required this.configured,
    required this.defaultModel,
    required this.label,
    required this.managed,
    required this.models,
    required this.status,
    required this.value,
  });

  final bool configured;
  final String defaultModel;
  final String label;
  final bool managed;
  final List<String> models;
  final String status;
  final String value;

  factory AvailableModelStatus.fromJson(Map<String, dynamic> json) {
    final rawModels = (json['models'] as List?) ?? const [];
    return AvailableModelStatus(
      configured: json['configured'] as bool? ?? false,
      defaultModel: json['default_model'] as String? ?? '',
      label: json['label'] as String? ?? '',
      managed: json['managed'] as bool? ?? false,
      models:
          rawModels.whereType<String>().map((item) => item.toString()).toList(),
      status: json['status'] as String? ?? '',
      value: json['value'] as String? ?? '',
    );
  }
}
