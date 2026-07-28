import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../auth/data/auth_api.dart';
import 'profile_avatar.dart';

class ProfileSettingsPage extends StatefulWidget {
  const ProfileSettingsPage({
    super.key,
    required this.authApi,
    required this.initialUser,
  });

  final AuthApi authApi;
  final AuthUser initialUser;

  @override
  State<ProfileSettingsPage> createState() => _ProfileSettingsPageState();
}

class _ProfileSettingsPageState extends State<ProfileSettingsPage> {
  late AuthUser _user;
  late final TextEditingController _displayNameController;
  late final TextEditingController _nicknameController;

  bool _isSaving = false;
  bool _isUploadingAvatar = false;
  bool _isDeletingAvatar = false;
  bool _hasChanges = false;

  @override
  void initState() {
    super.initState();
    _user = widget.initialUser;
    _displayNameController =
        TextEditingController(text: _user.displayName ?? _user.username);
    _nicknameController = TextEditingController(text: _user.nickname ?? '');
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    _nicknameController.dispose();
    super.dispose();
  }

  Future<void> _reloadUser() async {
    final user = await widget.authApi.me();
    if (!mounted) {
      return;
    }
    setState(() {
      _user = user;
      _displayNameController.text = user.displayName ?? user.username;
      _nicknameController.text = user.nickname ?? '';
    });
  }

  Future<void> _pickAvatar() async {
    if (_isUploadingAvatar) {
      return;
    }

    FilePickerResult? result;
    try {
      result = await FilePicker.pickFiles(
        allowMultiple: false,
        withData: true,
        type: FileType.custom,
        allowedExtensions: const ['png', 'jpg', 'jpeg', 'webp', 'bmp'],
      );
    } catch (error) {
      _showMessage('选择头像失败：$error');
      return;
    }

    final file =
        result == null || result.files.isEmpty ? null : result.files.first;
    final bytes = file?.bytes;
    if (file == null || bytes == null || bytes.isEmpty) {
      return;
    }

    if (bytes.length > 5 * 1024 * 1024) {
      _showMessage('头像不能超过 5MB');
      return;
    }

    setState(() => _isUploadingAvatar = true);
    try {
      final response = await widget.authApi.uploadAvatar(
        filename: file.name,
        bytes: bytes,
      );
      await _reloadUser();
      _hasChanges = true;
      _showMessage(response.message);
    } on ApiException catch (error) {
      _showMessage(error.message);
    } catch (error) {
      _showMessage('头像上传失败：$error');
    } finally {
      if (mounted) {
        setState(() => _isUploadingAvatar = false);
      }
    }
  }

  Future<void> _deleteAvatar() async {
    if (_isDeletingAvatar || (_user.avatarUrl ?? '').isEmpty) {
      return;
    }

    setState(() => _isDeletingAvatar = true);
    try {
      final response = await widget.authApi.deleteAvatar();
      await _reloadUser();
      _hasChanges = true;
      _showMessage(response.message);
    } on ApiException catch (error) {
      _showMessage(error.message);
    } catch (error) {
      _showMessage('删除头像失败：$error');
    } finally {
      if (mounted) {
        setState(() => _isDeletingAvatar = false);
      }
    }
  }

  Future<void> _saveProfile() async {
    if (_isSaving) {
      return;
    }

    final displayName = _displayNameController.text.trim();
    final nickname = _nicknameController.text.trim();

    setState(() => _isSaving = true);
    try {
      final response = await widget.authApi.updateProfile(
        displayName: displayName,
        nickname: nickname,
      );
      await _reloadUser();
      _hasChanges = true;
      _showMessage(response.message);
    } on ApiException catch (error) {
      _showMessage(error.message);
    } catch (error) {
      _showMessage('保存失败：$error');
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    showAppSnackBar(context, message);
  }

  void _close() {
    Navigator.of(context).pop(_hasChanges);
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppThemePalette.of(context);

    return Scaffold(
      backgroundColor: palette.pageBg,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(palette),
              const SizedBox(height: 12),
              _AvatarEditor(
                palette: palette,
                user: _user,
                authApi: widget.authApi,
                isUploading: _isUploadingAvatar,
                isDeleting: _isDeletingAvatar,
                onPickAvatar: _pickAvatar,
                onDeleteAvatar: _deleteAvatar,
              ),
              const SizedBox(height: 28),
              Text(
                '账户信息',
                style: TextStyle(
                  color: palette.textMain,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 14),
              _buildAccountCard(palette),
              const SizedBox(height: 28),
              Center(
                child: SizedBox(
                  width: 400,
                  child: ElevatedButton(
                    onPressed: _isSaving ? null : _saveProfile,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: palette.primary,
                      disabledBackgroundColor: palette.primary.withOpacity(0.4),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 17),
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(13),
                      ),
                    ),
                    child: _isSaving
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text(
                            '保存更改',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(AppThemePalette palette) {
    return Row(
      children: [
        IconButton(
          onPressed: _close,
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          color: palette.textMain,
          tooltip: '返回',
        ),
        Expanded(
          child: Text(
            '用户资料设置',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: palette.textMain,
              fontSize: 17,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        const SizedBox(width: 48),
      ],
    );
  }

  Widget _buildAccountCard(AppThemePalette palette) {
    return Container(
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.panelBorder),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
      child: Column(
        children: [
          _ReadOnlyAccountRow(
            palette: palette,
            title: '用户名',
            subtitle: '您的唯一登录凭证',
            value: '@${_user.username}',
          ),
          _Divider(palette: palette),
          _EditableAccountRow(
            palette: palette,
            title: '显示名称',
            subtitle: '用于在应用中展示的主要名称',
            controller: _displayNameController,
            hintText: '例如：Admin',
          ),
          _Divider(palette: palette),
          _EditableAccountRow(
            palette: palette,
            title: '当前昵称',
            subtitle: '可选的个性化称呼',
            controller: _nicknameController,
            hintText: '例如：数学冲刺版',
          ),
        ],
      ),
    );
  }
}

class _AvatarEditor extends StatelessWidget {
  const _AvatarEditor({
    required this.palette,
    required this.user,
    required this.authApi,
    required this.isUploading,
    required this.isDeleting,
    required this.onPickAvatar,
    required this.onDeleteAvatar,
  });

  final AppThemePalette palette;
  final AuthUser user;
  final AuthApi authApi;
  final bool isUploading;
  final bool isDeleting;
  final VoidCallback onPickAvatar;
  final VoidCallback onDeleteAvatar;

  @override
  Widget build(BuildContext context) {
    final hasAvatar = (user.avatarUrl ?? '').isNotEmpty;
    final title = user.displayName?.trim().isNotEmpty == true
        ? user.displayName!.trim()
        : user.username;

    return Column(
      children: [
        SizedBox(
          width: 132,
          height: 132,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned.fill(
                child: GestureDetector(
                  onTap: isUploading ? null : onPickAvatar,
                  child: ProfileAvatar(
                    palette: palette,
                    authApi: authApi,
                    avatarUrl: user.avatarUrl,
                    title: title,
                    borderRadius: 36,
                    letterSize: 34,
                  ),
                ),
              ),
              if (isUploading)
                Positioned.fill(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(36),
                    child: Container(
                      color: Colors.black.withOpacity(0.28),
                      child: const Center(
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ),
              Positioned(
                right: -2,
                bottom: -2,
                child: Tooltip(
                  message: '更换头像',
                  child: Material(
                    color: palette.primary,
                    shape: const CircleBorder(),
                    elevation: 0,
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: isUploading ? null : onPickAvatar,
                      child: const SizedBox(
                        width: 42,
                        height: 42,
                        child: Icon(
                          Icons.edit_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        if (hasAvatar) ...[
          const SizedBox(height: 14),
          TextButton.icon(
            onPressed: isDeleting ? null : onDeleteAvatar,
            icon: isDeleting
                ? SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: palette.errorText,
                    ),
                  )
                : const Icon(Icons.close_rounded, size: 18),
            label: const Text('移除头像'),
            style: TextButton.styleFrom(
              foregroundColor: palette.errorText,
              textStyle: const TextStyle(
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _ReadOnlyAccountRow extends StatelessWidget {
  const _ReadOnlyAccountRow({
    required this.palette,
    required this.title,
    required this.subtitle,
    required this.value,
  });

  final AppThemePalette palette;
  final String title;
  final String subtitle;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 15),
      child: Row(
        children: [
          Expanded(
            child: _AccountRowLabel(
              palette: palette,
              title: title,
              subtitle: subtitle,
            ),
          ),
          const SizedBox(width: 16),
          Flexible(
            child: Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
              style: TextStyle(
                color: palette.textMain,
                fontSize: 15,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EditableAccountRow extends StatelessWidget {
  const _EditableAccountRow({
    required this.palette,
    required this.title,
    required this.subtitle,
    required this.controller,
    required this.hintText,
  });

  final AppThemePalette palette;
  final String title;
  final String subtitle;
  final TextEditingController controller;
  final String hintText;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 15),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 560;
          final label = _AccountRowLabel(
            palette: palette,
            title: title,
            subtitle: subtitle,
          );
          final input = _buildInput();

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                label,
                const SizedBox(height: 10),
                input,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: label),
              const SizedBox(width: 18),
              SizedBox(width: 260, child: input),
            ],
          );
        },
      ),
    );
  }

  Widget _buildInput() {
    return TextField(
      controller: controller,
      style: TextStyle(
        color: palette.textMain,
        fontSize: 14,
        fontWeight: FontWeight.w700,
      ),
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: TextStyle(color: palette.textSub),
        filled: true,
        fillColor: palette.panelBg,
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(13),
          borderSide: BorderSide(color: palette.panelBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(13),
          borderSide: BorderSide(color: palette.primary),
        ),
      ),
    );
  }
}

class _AccountRowLabel extends StatelessWidget {
  const _AccountRowLabel({
    required this.palette,
    required this.title,
    required this.subtitle,
  });

  final AppThemePalette palette;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            color: palette.textMain,
            fontSize: 15,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 5),
        Text(
          subtitle,
          style: TextStyle(
            color: palette.textSub,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _Divider extends StatelessWidget {
  const _Divider({required this.palette});

  final AppThemePalette palette;

  @override
  Widget build(BuildContext context) {
    return Divider(height: 1, color: palette.panelBorder);
  }
}
