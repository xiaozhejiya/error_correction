import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../app/router/app_router.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../../auth/data/auth_api.dart';
import '../widgets/home_hero.dart';
import '../widgets/home_top_bar.dart';

class HomePage extends StatelessWidget {
  const HomePage({
    super.key,
    required this.authApi,
    required this.themeModeListenable,
    required this.onToggleThemeMode,
  });

  final AuthApi authApi;
  final ValueListenable<ThemeMode> themeModeListenable;
  final VoidCallback onToggleThemeMode;

  @override
  Widget build(BuildContext context) {
    Future<void> openEntry() async {
      final navigator = Navigator.of(context);
      final hasSession = await authApi.hasStoredSession();
      if (!context.mounted) {
        return;
      }

      if (!hasSession) {
        navigator.pushNamed(AppRoutes.login);
        return;
      }

      try {
        await authApi.me();
        if (!context.mounted) {
          return;
        }
        navigator.pushNamed(AppRoutes.workspace);
      } catch (_) {
        await authApi.clearStoredSession();
        if (!context.mounted) {
          return;
        }
        navigator.pushNamed(AppRoutes.login);
      }
    }

    return Scaffold(
      body: StarryBackground(
        showHomeOrnaments: true,
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final compact =
                  constraints.maxWidth < 620 || constraints.maxHeight < 680;
              final horizontal = constraints.maxWidth < 600 ? 20.0 : 32.0;

              final content = Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: horizontal,
                  vertical: 20,
                ),
                child: Column(
                  children: [
                    HomeTopBar(
                      onEnterWorkspace: openEntry,
                      themeModeListenable: themeModeListenable,
                      onToggleThemeMode: onToggleThemeMode,
                    ),
                    SizedBox(height: compact ? 88 : 0),
                    if (!compact) const Spacer(),
                    HomeHero(onStart: openEntry),
                    if (!compact) const Spacer(flex: 2),
                    if (compact) const SizedBox(height: 96),
                  ],
                ),
              );

              if (!compact) {
                return content;
              }

              return SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: content,
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
