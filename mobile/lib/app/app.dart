import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../features/auth/data/auth_api.dart';
import 'router/app_router.dart';
import 'theme/app_theme.dart';

class MyApp extends StatefulWidget {
  const MyApp({super.key, this.authApi});

  final AuthApi? authApi;

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  static const String _themeModeCacheKey = 'theme_mode';

  late final ValueNotifier<ThemeMode> _themeModeNotifier =
      ValueNotifier<ThemeMode>(ThemeMode.dark);
  late final AuthApi _authApi;

  @override
  void initState() {
    super.initState();
    _authApi = widget.authApi ?? AuthApi();
    _loadThemeMode();
  }

  Future<void> _loadThemeMode() async {
    final prefs = await SharedPreferences.getInstance();
    final cachedThemeMode = prefs.getString(_themeModeCacheKey);

    if (!mounted || cachedThemeMode == null) {
      return;
    }

    _themeModeNotifier.value =
        cachedThemeMode == 'light' ? ThemeMode.light : ThemeMode.dark;
  }

  Future<void> _toggleThemeMode() async {
    final nextThemeMode = _themeModeNotifier.value == ThemeMode.dark
        ? ThemeMode.light
        : ThemeMode.dark;

    _themeModeNotifier.value = nextThemeMode;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _themeModeCacheKey,
      nextThemeMode == ThemeMode.light ? 'light' : 'dark',
    );
  }

  @override
  void dispose() {
    _themeModeNotifier.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: _themeModeNotifier,
      builder: (context, themeMode, _) {
        return MaterialApp(
          title: '智卷错题本',
          theme: AppTheme.lightTheme,
          darkTheme: AppTheme.darkTheme,
          themeMode: themeMode,
          initialRoute: AppRoutes.home,
          onGenerateRoute: (settings) => AppRouter.onGenerateRoute(
            settings,
            authApi: _authApi,
            themeModeListenable: _themeModeNotifier,
            onToggleThemeMode: _toggleThemeMode,
          ),
          debugShowCheckedModeBanner: false,
        );
      },
    );
  }
}
