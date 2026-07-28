import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../app/router/app_router.dart';
import '../../../../app/theme/app_theme.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../auth/data/auth_api.dart';
import 'profile_avatar.dart';
import 'profile_settings_page.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({
    super.key,
    required this.authApi,
    required this.themeModeListenable,
    required this.onToggleThemeMode,
  });

  final AuthApi authApi;
  final ValueListenable<ThemeMode> themeModeListenable;
  final VoidCallback onToggleThemeMode;

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  late Future<AuthUser> _userFuture;
  bool _isLoggingOut = false;

  @override
  void initState() {
    super.initState();
    _userFuture = widget.authApi.me();
  }

  Future<void> _logout() async {
    if (_isLoggingOut) {
      return;
    }

    setState(() => _isLoggingOut = true);

    try {
      await widget.authApi.logout();
    } catch (_) {
      await widget.authApi.clearStoredSession();
    }

    if (!mounted) {
      return;
    }

    Navigator.of(context).pushNamedAndRemoveUntil(
      AppRoutes.login,
      (route) => false,
    );
  }

  Future<void> _openSettings(AuthUser? user) async {
    if (user == null) {
      showAppSnackBar(context, '用户信息加载完成后再修改资料');
      return;
    }

    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => ProfileSettingsPage(
          authApi: widget.authApi,
          initialUser: user,
        ),
      ),
    );

    if (changed == true && mounted) {
      setState(() {
        _userFuture = widget.authApi.me();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return FutureBuilder<AuthUser>(
      future: _userFuture,
      builder: (context, snapshot) {
        final user = snapshot.data;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '我的',
              style: TextStyle(
                color: palette.textMain,
                fontWeight: FontWeight.w800,
                fontSize: 22,
              ),
            ),
            const SizedBox(height: 16),
            _ProfileHeader(
              palette: palette,
              authApi: widget.authApi,
              user: user,
              isLoading: snapshot.connectionState != ConnectionState.done,
              hasError: snapshot.hasError,
            ),
            const SizedBox(height: 16),
            _SettingsSection(
              palette: palette,
              themeModeListenable: widget.themeModeListenable,
              onToggleThemeMode: widget.onToggleThemeMode,
              onOpenSettings: () => _openSettings(user),
              onLogout: _logout,
              isLoggingOut: _isLoggingOut,
            ),
          ],
        );
      },
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({
    required this.palette,
    required this.authApi,
    required this.user,
    required this.isLoading,
    required this.hasError,
  });

  final AppThemePalette palette;
  final AuthApi authApi;
  final AuthUser? user;
  final bool isLoading;
  final bool hasError;

  @override
  Widget build(BuildContext context) {
    final title = user?.displayName?.trim().isNotEmpty == true
        ? user!.displayName!.trim()
        : user?.username ?? (isLoading ? '同步用户信息' : '未登录');
    final accountState = hasError ? '用户信息加载失败' : _accountStateText(user);
    final quotaText = _quotaText(user?.quota);

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 52,
            height: 52,
            child: ProfileAvatar(
              palette: palette,
              authApi: authApi,
              avatarUrl: user?.avatarUrl,
              title: title,
              borderRadius: 18,
              letterSize: 20,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: palette.textMain,
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    if (user?.isAdmin == true) ...[
                      const SizedBox(width: 8),
                      _AdminBadge(palette: palette),
                    ],
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  accountState,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: palette.textSub,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  quotaText,
                  style: TextStyle(
                    color: palette.primaryLight,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _quotaText(Map<String, dynamic>? quota) {
    if (quota == null || quota.isEmpty) {
      return '额度信息待同步';
    }

    final remaining = quota['remaining'] ??
        quota['remaining_today'] ??
        quota['daily_remaining'] ??
        quota['left'];
    final total = quota['total'] ?? quota['limit'] ?? quota['daily_limit'];

    if (remaining != null && total != null) {
      return '今日剩余 $remaining / $total 次';
    }

    if (remaining != null) {
      return '今日剩余 $remaining 次';
    }

    return '额度信息待同步';
  }

  static String _accountStateText(AuthUser? user) {
    if (user == null) {
      return '正在读取账号信息';
    }

    return '@${user.username}';
  }
}

class _AdminBadge extends StatelessWidget {
  const _AdminBadge({required this.palette});

  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: palette.primary.withOpacity(0.14),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        'Admin',
        style: TextStyle(
          color: palette.primaryLight,
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  const _SettingsSection({
    required this.palette,
    required this.themeModeListenable,
    required this.onToggleThemeMode,
    required this.onOpenSettings,
    required this.onLogout,
    required this.isLoggingOut,
  });

  final AppThemePalette palette;
  final ValueListenable<ThemeMode> themeModeListenable;
  final VoidCallback onToggleThemeMode;
  final VoidCallback onOpenSettings;
  final VoidCallback onLogout;
  final bool isLoggingOut;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              '设置',
              style: TextStyle(
                color: palette.textSub,
                fontSize: 13,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          ValueListenableBuilder<ThemeMode>(
            valueListenable: themeModeListenable,
            builder: (context, themeMode, _) {
              final isDark = themeMode == ThemeMode.dark;
              return _ProfileActionTile(
                palette: palette,
                icon:
                    isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
                title: isDark ? '切换为日间模式' : '切换为夜间模式',
                subtitle: isDark ? '当前为夜间模式' : '当前为日间模式',
                onTap: onToggleThemeMode,
              );
            },
          ),
          _ProfileActionTile(
            palette: palette,
            icon: Icons.person_rounded,
            title: '用户资料设置',
            subtitle: '昵称和头像管理',
            onTap: onOpenSettings,
          ),
          _ProfileActionTile(
            palette: palette,
            icon: Icons.logout_rounded,
            title: isLoggingOut ? '正在退出' : '退出登录',
            subtitle: '清除当前账号登录状态',
            isDanger: true,
            trailing: isLoggingOut
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: palette.errorText,
                    ),
                  )
                : null,
            onTap: isLoggingOut ? null : onLogout,
          ),
        ],
      ),
    );
  }
}

class _ProfileActionTile extends StatelessWidget {
  const _ProfileActionTile({
    required this.palette,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.isDanger = false,
    this.trailing,
  });

  final AppThemePalette palette;
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final bool isDanger;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final titleColor = isDanger ? palette.errorText : palette.textMain;
    final iconColor = isDanger ? palette.errorText : palette.primaryLight;

    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: iconColor.withOpacity(palette.isLight ? 0.12 : 0.16),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: titleColor,
                      fontSize: 15,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: palette.textSub,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            trailing ??
                Icon(
                  Icons.chevron_right_rounded,
                  color: palette.textSub,
                  size: 22,
                ),
          ],
        ),
      ),
    );
  }
}
