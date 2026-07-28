import 'package:flutter/material.dart';

import '../../../../app/router/app_router.dart';
import '../../../../core/widgets/starry_background.dart';
import '../../../auth/data/auth_api.dart';
import '../widgets/login_form_panel.dart';
import '../widgets/login_hero_panel.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key, this.authApi});

  final AuthApi? authApi;

  @override
  Widget build(BuildContext context) {
    void openWorkspace() {
      Navigator.of(context).pushReplacementNamed(AppRoutes.workspace);
    }

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: StarryBackground(
        showHomeOrnaments: false,
        showStars: true,
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxHeight < 760;
              final keyboardInset = MediaQuery.viewInsetsOf(context).bottom;

              return AnimatedPadding(
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                padding: EdgeInsets.only(bottom: keyboardInset),
                child: SingleChildScrollView(
                  keyboardDismissBehavior:
                      ScrollViewKeyboardDismissBehavior.onDrag,
                  padding: const EdgeInsets.only(bottom: 16),
                  child: ConstrainedBox(
                    constraints:
                        BoxConstraints(minHeight: constraints.maxHeight),
                    child: Column(
                      children: [
                        SizedBox(
                          height: compact ? 200 : 220,
                          child: const LoginHeroPanel(),
                        ),
                        LoginFormPanel(
                          authApi: authApi,
                          onLogin: openWorkspace,
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
