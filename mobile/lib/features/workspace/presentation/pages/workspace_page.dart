import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../../auth/data/auth_api.dart';
import 'chat_page.dart';
import 'lamp_page.dart';
import 'library_page.dart';
import 'profile_page.dart';
import 'smart_input_page.dart';
import 'workspace_bottom_navigation_bar.dart';

class WorkspacePage extends StatefulWidget {
  const WorkspacePage({
    super.key,
    this.authApi,
    this.themeModeListenable,
    this.onToggleThemeMode,
  });

  final AuthApi? authApi;
  final ValueListenable<ThemeMode>? themeModeListenable;
  final VoidCallback? onToggleThemeMode;

  @override
  State<WorkspacePage> createState() => _WorkspacePageState();
}

class _WorkspacePageState extends State<WorkspacePage> {
  int _currentIndex = 0;
  late final AuthApi _authApi;
  ValueNotifier<ThemeMode>? _localThemeModeNotifier;

  ValueListenable<ThemeMode> get _themeModeListenable =>
      widget.themeModeListenable ?? _localThemeModeNotifier!;

  @override
  void initState() {
    super.initState();
    _authApi = widget.authApi ?? AuthApi();
    if (widget.themeModeListenable == null) {
      _localThemeModeNotifier = ValueNotifier<ThemeMode>(ThemeMode.dark);
    }
  }

  @override
  void dispose() {
    _localThemeModeNotifier?.dispose();
    super.dispose();
  }

  void _toggleLocalThemeMode() {
    final notifier = _localThemeModeNotifier;
    if (notifier == null) {
      return;
    }

    notifier.value =
        notifier.value == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: StarryBackground(
        showHomeOrnaments: false,
        child: SafeArea(
          top: true,
          child: Column(
            children: [
              Expanded(
                child: _buildActiveTabView(
                  palette: palette,
                ),
              ),
              WorkspaceBottomNavigationBar(
                selectedIndex: _currentIndex,
                onDestinationSelected: (index) {
                  setState(() {
                    _currentIndex = index;
                  });
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActiveTabView({
    required AppThemePalette palette,
  }) {
    final current = switch (_currentIndex) {
      0 => const SmartInputPage(),
      1 => const LibraryPage(),
      2 => const LampPage(),
      3 => const ChatPage(),
      _ => ProfilePage(
          authApi: _authApi,
          themeModeListenable: _themeModeListenable,
          onToggleThemeMode: widget.onToggleThemeMode ?? _toggleLocalThemeMode,
        ),
    };

    if (_currentIndex == 0) {
      return current;
    }

    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 18, 24, 0),
        child: current,
      ),
    );
  }
}
