import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/constants/app_assets.dart';

class HomeTopBar extends StatelessWidget {
  const HomeTopBar({
    super.key,
    required this.onEnterWorkspace,
    required this.themeModeListenable,
    required this.onToggleThemeMode,
  });

  final VoidCallback onEnterWorkspace;
  final ValueListenable<ThemeMode> themeModeListenable;
  final VoidCallback onToggleThemeMode;

  @override
  Widget build(BuildContext context) {
    final textColor = Theme.of(context).colorScheme.onSurface;

    return Row(
      children: [
        Container(
          width: 38,
          height: 38,
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            color: AppTheme.primary,
            borderRadius: BorderRadius.circular(11),
            boxShadow: [
              BoxShadow(
                color: AppTheme.primary.withOpacity(0.35),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: SvgPicture.asset(
            AppAssets.logo,
            key: const Key('app-logo'),
            colorFilter: const ColorFilter.mode(
              AppTheme.textPrimary,
              BlendMode.srcIn,
            ),
            placeholderBuilder: (_) => const Icon(
              Icons.edit_document,
              color: AppTheme.textPrimary,
              size: 18,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            '智卷错题本',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: textColor,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        const Spacer(),
        ValueListenableBuilder<ThemeMode>(
          valueListenable: themeModeListenable,
          builder: (context, themeMode, _) {
            final isDarkTheme = themeMode == ThemeMode.dark;

            return IconButton(
              key: const Key('theme-toggle-button'),
              tooltip: isDarkTheme ? '切换为日间主题' : '切换为夜间主题',
              onPressed: onToggleThemeMode,
              icon: Icon(
                isDarkTheme
                    ? Icons.light_mode_rounded
                    : Icons.dark_mode_rounded,
                color: textColor,
              ),
            );
          },
        ),
      ],
    );
  }
}
