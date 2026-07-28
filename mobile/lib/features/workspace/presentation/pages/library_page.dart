import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/utils/time_format.dart';
import '../../data/workspace_api.dart';
import '../../data/workspace_project_store.dart';
import 'library_project_detail_page.dart';

enum _LibraryFilter { all, question, note }

class LibraryPage extends StatefulWidget {
  const LibraryPage({super.key});

  @override
  State<LibraryPage> createState() => _LibraryPageState();
}

class _LibraryPageState extends State<LibraryPage> {
  final WorkspaceProjectStore _store = WorkspaceProjectStore.instance;
  final TextEditingController _searchController = TextEditingController();
  _LibraryFilter _filter = _LibraryFilter.all;

  @override
  void initState() {
    super.initState();
    unawaited(_store.ensureLoaded());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return AnimatedBuilder(
      animation: _store,
      builder: (context, _) {
        final projects = _filteredProjects;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '库',
              style: TextStyle(
                color: palette.textMain,
                fontWeight: FontWeight.w800,
                fontSize: 22,
              ),
            ),
            const SizedBox(height: 16),
            _buildStats(palette),
            const SizedBox(height: 16),
            Divider(color: palette.border),
            const SizedBox(height: 14),
            _buildToolbar(palette),
            const SizedBox(height: 14),
            _buildTableHeader(palette),
            const SizedBox(height: 8),
            if (_store.isLoading && _store.projects.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 40),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_store.errorMessage != null && _store.projects.isEmpty)
              _buildMessage(
                palette,
                _store.errorMessage!,
                actionText: '重试',
                onAction: () => unawaited(_store.refresh()),
              )
            else if (projects.isEmpty)
              _buildMessage(palette, '暂无匹配项目')
            else
              ...projects.map((project) => _buildProjectRow(project, palette)),
          ],
        );
      },
    );
  }

  List<WorkspaceProject> get _filteredProjects {
    final keyword = _searchController.text.trim().toLowerCase();
    return _store.projects.where((project) {
      final typeMatched = switch (_filter) {
        _LibraryFilter.all => true,
        _LibraryFilter.question => project.isQuestionProject,
        _LibraryFilter.note => project.isNoteProject,
      };
      if (!typeMatched) {
        return false;
      }
      if (keyword.isEmpty) {
        return true;
      }
      return project.displayName.toLowerCase().contains(keyword) ||
          project.displayDescription.toLowerCase().contains(keyword);
    }).toList();
  }

  Widget _buildStats(AppThemePalette palette) {
    final cards = [
      _StatItem(
        title: '全部项目',
        value: _store.projects.length.toString(),
        icon: Icons.inventory_2_rounded,
        color: palette.primary,
      ),
      _StatItem(
        title: '错题库',
        value: _store.questionProjects.length.toString(),
        icon: Icons.storage_rounded,
        color: const Color(0xFF58A6FF),
      ),
      _StatItem(
        title: '笔记本',
        value: _store.noteProjects.length.toString(),
        icon: Icons.menu_book_rounded,
        color: const Color(0xFF32D99C),
      ),
      _StatItem(
        title: '总题目',
        value: _store.totalQuestionCount.toString(),
        icon: Icons.format_list_numbered_rounded,
        color: const Color(0xFFFFB020),
      ),
      _StatItem(
        title: '总笔记',
        value: _store.totalNoteCount.toString(),
        icon: Icons.sticky_note_2_rounded,
        color: const Color(0xFFFF8A3D),
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 12.0;
        final width = constraints.maxWidth;
        final columns = width >= 300
            ? 3
            : width >= 210
                ? 2
                : 1;
        final itemWidth = (width - gap * (columns - 1)) / columns;
        final compact = itemWidth < 136;

        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: cards
              .map(
                (item) => SizedBox(
                  width: itemWidth,
                  child: _StatCard(
                    item: item,
                    palette: palette,
                    compact: compact,
                  ),
                ),
              )
              .toList(),
        );
      },
    );
  }

  Widget _buildToolbar(AppThemePalette palette) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final filters = Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildFilterButton(
              _LibraryFilter.all,
              '全部 ${_store.projects.length}',
              palette,
            ),
            const SizedBox(width: 6),
            _buildFilterButton(
              _LibraryFilter.question,
              '错题库 ${_store.questionProjects.length}',
              palette,
            ),
            const SizedBox(width: 6),
            _buildFilterButton(
              _LibraryFilter.note,
              '笔记本 ${_store.noteProjects.length}',
              palette,
            ),
          ],
        );
        if (constraints.maxWidth < 760) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: filters,
              ),
            ],
          );
        }

        return Row(
          children: [
            filters,
            const Spacer(),
          ],
        );
      },
    );
  }

  Widget _buildFilterButton(
    _LibraryFilter filter,
    String text,
    AppThemePalette palette,
  ) {
    final selected = _filter == filter;
    return Padding(
      padding: const EdgeInsets.only(right: 2),
      child: TextButton(
        onPressed: () => setState(() => _filter = filter),
        style: TextButton.styleFrom(
          backgroundColor: selected ? palette.primary : palette.panel,
          foregroundColor: selected ? Colors.white : palette.textSub,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
        ),
        child: Text(
          text,
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12),
        ),
      ),
    );
  }

  Widget _buildTableHeader(AppThemePalette palette) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
      child: Row(
        children: [
          Expanded(
            flex: 5,
            child: Text('项目', style: _headerStyle(palette)),
          ),
          Expanded(
            flex: 2,
            child: Text('内容', style: _headerStyle(palette)),
          ),
          Expanded(
            flex: 2,
            child: Text('最近更新', style: _headerStyle(palette)),
          ),
        ],
      ),
    );
  }

  Widget _buildProjectRow(WorkspaceProject project, AppThemePalette palette) {
    final iconColor = palette.primaryLight.withOpacity(0.5);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _openProject(project),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 14),
          decoration: BoxDecoration(
            border: Border.all(color: palette.panelBorder),
            borderRadius: BorderRadius.circular(12),
            color: palette.cardBg,
          ),
          child: Row(
            children: [
              Expanded(
                flex: 5,
                child: Row(
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: palette.panel,
                        borderRadius: BorderRadius.circular(7),
                      ),
                      child: Icon(
                        project.isQuestionProject
                            ? Icons.storage_rounded
                            : Icons.menu_book_rounded,
                        color: iconColor,
                        size: 16,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            project.displayName,
                            style: TextStyle(
                              color: palette.textMain,
                              fontSize: 14,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            project.displayDescription,
                            style: TextStyle(
                              color: palette.textSub,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  project.isQuestionProject
                      ? '${project.questionCount} 道题'
                      : '${project.noteCount} 篇笔记',
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        formatRelativeTime(
                          project.updatedAt ?? project.createdAt,
                        ),
                        style: TextStyle(
                          color: palette.textSub,
                          fontWeight: FontWeight.w700,
                          fontSize: 11,
                        ),
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: palette.textSub,
                      size: 18,
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

  void _openProject(WorkspaceProject project) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => LibraryProjectDetailPage(project: project),
      ),
    );
  }

  Widget _buildMessage(
    AppThemePalette palette,
    String message, {
    String? actionText,
    VoidCallback? onAction,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 44),
      child: Center(
        child: Column(
          children: [
            Text(
              message,
              style: TextStyle(
                color: palette.textSub,
                fontWeight: FontWeight.w700,
              ),
            ),
            if (actionText != null && onAction != null) ...[
              const SizedBox(height: 10),
              OutlinedButton(onPressed: onAction, child: Text(actionText)),
            ],
          ],
        ),
      ),
    );
  }

  TextStyle _headerStyle(AppThemePalette palette) {
    return TextStyle(
      color: palette.textSub,
      fontSize: 12,
      fontWeight: FontWeight.w800,
    );
  }
}

class _StatItem {
  const _StatItem({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color color;
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.item,
    required this.palette,
    required this.compact,
  });

  final _StatItem item;
  final AppThemePalette palette;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(minHeight: compact ? 94 : 68),
      padding: EdgeInsets.all(compact ? 10 : 14),
      decoration: BoxDecoration(
        color: palette.panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.border),
      ),
      child: compact ? _buildCompact() : _buildRegular(),
    );
  }

  Widget _buildRegular() {
    return Row(
      children: [
        _buildIcon(size: 40, iconSize: 20),
        const SizedBox(width: 12),
        Expanded(
            child: _buildTexts(crossAxisAlignment: CrossAxisAlignment.start)),
      ],
    );
  }

  Widget _buildCompact() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildIcon(size: 32, iconSize: 17),
        const SizedBox(height: 8),
        _buildTexts(crossAxisAlignment: CrossAxisAlignment.start),
      ],
    );
  }

  Widget _buildIcon({
    required double size,
    required double iconSize,
  }) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: item.color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(item.icon, color: item.color, size: iconSize),
    );
  }

  Widget _buildTexts({
    required CrossAxisAlignment crossAxisAlignment,
  }) {
    return Column(
      crossAxisAlignment: crossAxisAlignment,
      children: [
        Text(
          item.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: palette.textSub,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          item.value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: palette.textMain,
            fontSize: compact ? 17 : 18,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    );
  }
}
