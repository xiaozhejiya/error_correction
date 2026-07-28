import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/widgets/protected_image.dart';
import '../../../auth/data/auth_api.dart';

class ProfileAvatar extends StatelessWidget {
  const ProfileAvatar({
    super.key,
    required this.palette,
    required this.authApi,
    required this.avatarUrl,
    required this.title,
    required this.borderRadius,
    required this.letterSize,
  });

  final AppThemePalette palette;
  final AuthApi authApi;
  final String? avatarUrl;
  final String title;
  final double borderRadius;
  final double letterSize;

  @override
  Widget build(BuildContext context) {
    final imageUrl = avatarUrl;
    final hasAvatar = imageUrl != null && imageUrl.isNotEmpty;

    return SizedBox.expand(
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          gradient: hasAvatar
              ? null
              : LinearGradient(
                  colors: [palette.primary, palette.primaryLight],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
          color: palette.panelBg,
          borderRadius: BorderRadius.circular(borderRadius),
          border: Border.all(color: palette.panelBorder),
          boxShadow: [
            BoxShadow(
              color: palette.primary.withOpacity(0.22),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: hasAvatar
            ? ProtectedImage(
                url: imageUrl,
                loadBytes: authApi.loadProtectedImage,
                fit: BoxFit.cover,
                loading: _AvatarLetter(title: title, fontSize: letterSize),
                error: _AvatarLetter(title: title, fontSize: letterSize),
              )
            : _AvatarLetter(title: title, fontSize: letterSize),
      ),
    );
  }
}

class _AvatarLetter extends StatelessWidget {
  const _AvatarLetter({
    required this.title,
    required this.fontSize,
  });

  final String title;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        _avatarLetter(title),
        style: TextStyle(
          color: Colors.white,
          fontSize: fontSize,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }

  static String _avatarLetter(String title) {
    final trimmed = title.trim();
    if (trimmed.isEmpty) {
      return '我';
    }
    return trimmed.characters.first.toUpperCase();
  }
}
