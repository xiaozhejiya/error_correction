import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import 'workspace_api.dart';

class WorkspaceProjectStore extends ChangeNotifier {
  WorkspaceProjectStore._({WorkspaceApi? api}) : _api = api ?? WorkspaceApi();

  static final WorkspaceProjectStore instance = WorkspaceProjectStore._();

  final WorkspaceApi _api;

  final List<WorkspaceProject> _projects = [];
  Future<void>? _loadingFuture;
  bool _isLoading = false;
  String? _errorMessage;

  List<WorkspaceProject> get projects => List.unmodifiable(_projects);
  List<WorkspaceProject> get questionProjects =>
      _projects.where((project) => project.isQuestionProject).toList();
  List<WorkspaceProject> get noteProjects =>
      _projects.where((project) => project.isNoteProject).toList();

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  int get totalQuestionCount =>
      _projects.fold(0, (total, project) => total + project.questionCount);
  int get totalNoteCount =>
      _projects.fold(0, (total, project) => total + project.noteCount);

  Future<void> ensureLoaded() {
    if (_projects.isNotEmpty) {
      return Future.value();
    }
    return refresh();
  }

  Future<void> refresh() {
    if (_loadingFuture != null) {
      return _loadingFuture!;
    }

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    _loadingFuture = _api.getProjects().then((response) {
      _projects
        ..clear()
        ..addAll(response.projects);
      _errorMessage = response.success ? null : '项目列表加载失败';
    }).catchError((error) {
      _errorMessage = error is ApiException ? error.message : '项目列表加载失败';
    }).whenComplete(() {
      _isLoading = false;
      _loadingFuture = null;
      notifyListeners();
    });

    return _loadingFuture!;
  }
}
