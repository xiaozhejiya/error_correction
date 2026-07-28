import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../features/auth/data/auth_api.dart';
import '../../features/home/presentation/pages/home_page.dart';
import '../../features/login/presentation/pages/login_page.dart';
import '../../features/workspace/presentation/pages/workspace_page.dart';

class AppRoutes {
  static const String home = '/';
  static const String login = '/login';
  static const String workspace = '/workspace';
}

class AppRouter {
  static Route<dynamic> onGenerateRoute(
    RouteSettings settings, {
    required AuthApi authApi,
    required ValueListenable<ThemeMode> themeModeListenable,
    required VoidCallback onToggleThemeMode,
  }) {
    final Widget page = switch (settings.name) {
      AppRoutes.login => LoginPage(authApi: authApi),
      AppRoutes.workspace => WorkspacePage(
          authApi: authApi,
          themeModeListenable: themeModeListenable,
          onToggleThemeMode: onToggleThemeMode,
        ),
      AppRoutes.home || null => HomePage(
          authApi: authApi,
          themeModeListenable: themeModeListenable,
          onToggleThemeMode: onToggleThemeMode,
        ),
      _ => HomePage(
          authApi: authApi,
          themeModeListenable: themeModeListenable,
          onToggleThemeMode: onToggleThemeMode,
        ),
    };

    return MaterialPageRoute<void>(
      settings: settings,
      builder: (_) => page,
    );
  }
}
