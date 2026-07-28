import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/app_snack_bar.dart';
import '../../../auth/data/auth_api.dart';

enum _AuthMode { login, register }

class LoginFormPanel extends StatefulWidget {
  const LoginFormPanel({super.key, required this.onLogin, this.authApi});

  final VoidCallback onLogin;
  final AuthApi? authApi;

  @override
  State<LoginFormPanel> createState() => _LoginFormPanelState();
}

class _LoginFormPanelState extends State<LoginFormPanel> {
  late final AuthApi _authApi;
  final _identifierController = TextEditingController();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  _AuthMode _mode = _AuthMode.login;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _isSubmitting = false;
  bool _isSendingCode = false;

  @override
  void initState() {
    super.initState();
    _authApi = widget.authApi ?? AuthApi();
  }

  @override
  void dispose() {
    _identifierController.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;
    final colorScheme = Theme.of(context).colorScheme;
    final textColor = colorScheme.onSurface;
    final secondaryColor =
        isLight ? AppTheme.lightTextSecondary : AppTheme.textSecondary;
    final fieldFill = isLight ? Colors.white : const Color(0xFF15151D);
    final panelBorder =
        isLight ? const Color(0xFFE3E5EE) : const Color(0xFF2A2A35);
    final isRegister = _mode == _AuthMode.register;
    final keyboardInset = MediaQuery.viewInsetsOf(context).bottom;
    final fieldScrollPadding = EdgeInsets.fromLTRB(
      20,
      20,
      20,
      keyboardInset + 96,
    );

    return Padding(
      padding: const EdgeInsets.fromLTRB(36, 28, 36, 36),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isRegister ? '创建账户' : '欢迎回来',
              style: TextStyle(
                color: textColor,
                fontSize: 30,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              isRegister ? '免费注册，开始智能错题整理' : '登录以继续使用你的错题本',
              style: TextStyle(color: secondaryColor, fontSize: 17),
            ),
            const SizedBox(height: 34),
            Container(
              height: 56,
              padding: const EdgeInsets.all(5),
              decoration: BoxDecoration(
                color:
                    isLight ? const Color(0xFFF1F2F6) : const Color(0xFF12121A),
                borderRadius: BorderRadius.circular(15),
                border: Border.all(color: panelBorder),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: _SegmentButton(
                      label: '登录',
                      selected: !isRegister,
                      onTap: () {
                        setState(() {
                          _mode = _AuthMode.login;
                        });
                      },
                    ),
                  ),
                  Expanded(
                    child: _SegmentButton(
                      label: '注册',
                      selected: isRegister,
                      onTap: () {
                        setState(() {
                          _mode = _AuthMode.register;
                        });
                      },
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            if (isRegister)
              ..._buildRegisterFields(
                textColor: textColor,
                secondaryColor: secondaryColor,
                fieldFill: fieldFill,
                panelBorder: panelBorder,
                isLight: isLight,
                scrollPadding: fieldScrollPadding,
              )
            else
              ..._buildLoginFields(
                textColor: textColor,
                secondaryColor: secondaryColor,
                fieldFill: fieldFill,
                panelBorder: panelBorder,
                scrollPadding: fieldScrollPadding,
              ),
            const SizedBox(height: 22),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppTheme.primary, AppTheme.primaryLight],
                  ),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: TextButton(
                  onPressed: _isSubmitting ? null : _handlePrimaryPressed,
                  style: TextButton.styleFrom(
                    foregroundColor: AppTheme.textPrimary,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: Text(
                    _primaryButtonText(isRegister),
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _primaryButtonText(bool isRegister) {
    if (_isSubmitting) {
      return isRegister ? '创建中...' : '登录中...';
    }

    return isRegister ? '创建账户' : '登录';
  }

  Future<void> _handlePrimaryPressed() async {
    if (_mode == _AuthMode.register) {
      await _register();
    } else {
      await _login();
    }
  }

  Future<void> _login() async {
    final identifier = _identifierController.text.trim();
    final password = _passwordController.text;
    if (identifier.isEmpty) {
      _showMessage('请输入邮箱或用户名');
      return;
    }
    if (password.isEmpty) {
      _showMessage('请输入密码');
      return;
    }

    setState(() {
      _isSubmitting = true;
    });
    try {
      await _authApi.login(identifier: identifier, password: password);
      if (mounted) {
        widget.onLogin();
      }
    } on ApiException catch (error, stackTrace) {
      debugPrint('[Login] api error: $error');
      debugPrintStack(
        label: '[Login] api stack',
        stackTrace: stackTrace,
        maxFrames: 20,
      );
      _showMessage(error.message);
    } catch (error, stackTrace) {
      debugPrint('[Login] unexpected error: $error');
      debugPrintStack(
        label: '[Login] unexpected stack',
        stackTrace: stackTrace,
        maxFrames: 20,
      );
      _showMessage('登录失败：$error');
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _register() async {
    final username = _usernameController.text.trim();
    final email = _emailController.text.trim();
    final code = _codeController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (username.isEmpty) {
      _showMessage('请输入用户名');
      return;
    }
    if (email.isEmpty) {
      _showMessage('请输入邮箱');
      return;
    }
    if (code.isEmpty) {
      _showMessage('请输入验证码');
      return;
    }
    if (password.length < 6) {
      _showMessage('密码至少 6 位');
      return;
    }
    if (password != confirmPassword) {
      _showMessage('两次输入的密码不一致');
      return;
    }

    setState(() {
      _isSubmitting = true;
    });
    try {
      await _authApi.register(
        email: email,
        username: username,
        password: password,
        code: code,
      );
      if (mounted) {
        widget.onLogin();
      }
    } on ApiException catch (error) {
      _showMessage(error.message);
    } catch (_) {
      _showMessage('注册失败，请稍后再试');
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _sendCode() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      _showMessage('请输入邮箱');
      return;
    }

    setState(() {
      _isSendingCode = true;
    });
    try {
      await _authApi.sendCode(email: email, type: 'register');
      _showMessage('验证码已发送');
    } on ApiException catch (error) {
      _showMessage(error.message);
    } catch (_) {
      _showMessage('验证码发送失败，请稍后再试');
    } finally {
      if (mounted) {
        setState(() {
          _isSendingCode = false;
        });
      }
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    showAppSnackBar(context, message);
  }

  List<Widget> _buildLoginFields({
    required Color textColor,
    required Color secondaryColor,
    required Color fieldFill,
    required Color panelBorder,
    required EdgeInsets scrollPadding,
  }) {
    return [
      Text('账号', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      _KeyboardAwareTextField(
        controller: _identifierController,
        scrollPadding: scrollPadding,
        textInputAction: TextInputAction.next,
        decoration: _fieldDecoration(
          hintText: '请输入邮箱或用户名',
          fillColor: fieldFill,
          borderColor: panelBorder,
        ),
      ),
      const SizedBox(height: 24),
      Text('密码', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      _KeyboardAwareTextField(
        controller: _passwordController,
        scrollPadding: scrollPadding,
        textInputAction: TextInputAction.done,
        obscureText: _obscurePassword,
        decoration: _fieldDecoration(
          hintText: '请输入密码',
          fillColor: fieldFill,
          borderColor: panelBorder,
          suffixIcon: _PasswordVisibilityButton(
            obscure: _obscurePassword,
            color: secondaryColor,
            onPressed: () {
              setState(() {
                _obscurePassword = !_obscurePassword;
              });
            },
          ),
        ),
      ),
      const SizedBox(height: 14),
      Align(
        alignment: Alignment.centerRight,
        child: Text(
          '忘记密码?',
          style: TextStyle(color: secondaryColor, fontSize: 14),
        ),
      ),
    ];
  }

  List<Widget> _buildRegisterFields({
    required Color textColor,
    required Color secondaryColor,
    required Color fieldFill,
    required Color panelBorder,
    required bool isLight,
    required EdgeInsets scrollPadding,
  }) {
    return [
      Text('用户名', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      _KeyboardAwareTextField(
        controller: _usernameController,
        scrollPadding: scrollPadding,
        textInputAction: TextInputAction.next,
        decoration: _fieldDecoration(
          hintText: '您的昵称',
          fillColor: fieldFill,
          borderColor: panelBorder,
        ),
      ),
      const SizedBox(height: 22),
      Text('邮箱', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      Row(
        children: [
          Expanded(
            child: _KeyboardAwareTextField(
              controller: _emailController,
              scrollPadding: scrollPadding,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              decoration: _fieldDecoration(
                hintText: 'your@email.com',
                fillColor: fieldFill,
                borderColor: panelBorder,
              ),
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 118,
            height: 52,
            child: TextButton(
              onPressed: _isSendingCode ? null : _sendCode,
              style: TextButton.styleFrom(
                foregroundColor: textColor,
                backgroundColor: fieldFill,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(15),
                  side: BorderSide(color: panelBorder),
                ),
              ),
              child: Text(
                _isSendingCode ? '发送中...' : '发送验证码',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
              ),
            ),
          ),
        ],
      ),
      const SizedBox(height: 22),
      Text('验证码', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      _KeyboardAwareTextField(
        controller: _codeController,
        scrollPadding: scrollPadding,
        keyboardType: TextInputType.number,
        textInputAction: TextInputAction.next,
        decoration: _fieldDecoration(
          hintText: '6 位验证码',
          fillColor: fieldFill,
          borderColor: panelBorder,
        ),
      ),
      const SizedBox(height: 22),
      Text('密码', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      _KeyboardAwareTextField(
        controller: _passwordController,
        scrollPadding: scrollPadding,
        textInputAction: TextInputAction.next,
        obscureText: _obscurePassword,
        decoration: _fieldDecoration(
          hintText: '至少 6 位',
          fillColor: fieldFill,
          borderColor: panelBorder,
          suffixIcon: _PasswordVisibilityButton(
            obscure: _obscurePassword,
            color: secondaryColor,
            onPressed: () {
              setState(() {
                _obscurePassword = !_obscurePassword;
              });
            },
          ),
        ),
      ),
      const SizedBox(height: 22),
      Text('确认密码', style: TextStyle(color: textColor, fontSize: 16)),
      const SizedBox(height: 10),
      _KeyboardAwareTextField(
        controller: _confirmPasswordController,
        scrollPadding: scrollPadding,
        textInputAction: TextInputAction.done,
        obscureText: _obscureConfirmPassword,
        decoration: _fieldDecoration(
          hintText: '再次输入密码',
          fillColor: fieldFill,
          borderColor: panelBorder,
          suffixIcon: _PasswordVisibilityButton(
            obscure: _obscureConfirmPassword,
            color: secondaryColor,
            onPressed: () {
              setState(() {
                _obscureConfirmPassword = !_obscureConfirmPassword;
              });
            },
          ),
        ),
      ),
    ];
  }

  InputDecoration _fieldDecoration({
    required String hintText,
    required Color fillColor,
    required Color borderColor,
    Color? focusedBorderColor,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      hintText: hintText,
      suffixIcon: suffixIcon,
      filled: true,
      fillColor: fillColor,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(15),
        borderSide: BorderSide(color: borderColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(15),
        borderSide: BorderSide(color: borderColor),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(15),
        borderSide: BorderSide(color: focusedBorderColor ?? AppTheme.primary),
      ),
    );
  }
}

class _SegmentButton extends StatelessWidget {
  const _SegmentButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Ink(
          decoration: BoxDecoration(
            color: selected
                ? (isLight ? Colors.white : const Color(0xFF2A2A32))
                : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurface,
                fontSize: 16,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _KeyboardAwareTextField extends StatefulWidget {
  const _KeyboardAwareTextField({
    required this.controller,
    required this.decoration,
    required this.scrollPadding,
    this.keyboardType,
    this.textInputAction,
    this.obscureText = false,
  });

  final TextEditingController controller;
  final InputDecoration decoration;
  final EdgeInsets scrollPadding;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final bool obscureText;

  @override
  State<_KeyboardAwareTextField> createState() =>
      _KeyboardAwareTextFieldState();
}

class _KeyboardAwareTextFieldState extends State<_KeyboardAwareTextField> {
  final FocusNode _focusNode = FocusNode();
  int _ensureVisibleToken = 0;

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(_handleFocusChange);
  }

  @override
  void dispose() {
    _focusNode
      ..removeListener(_handleFocusChange)
      ..dispose();
    super.dispose();
  }

  void _handleFocusChange() {
    if (!_focusNode.hasFocus) {
      return;
    }

    _scheduleEnsureVisible();
  }

  void _scheduleEnsureVisible() {
    final token = ++_ensureVisibleToken;
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => _ensureVisible(token, duration: const Duration(milliseconds: 180)),
    );
    Future<void>.delayed(
      const Duration(milliseconds: 140),
      () => _ensureVisible(
        token,
        duration: const Duration(milliseconds: 260),
      ),
    );
    Future<void>.delayed(
      const Duration(milliseconds: 340),
      () => _ensureVisible(
        token,
        duration: const Duration(milliseconds: 220),
      ),
    );
  }

  void _ensureVisible(
    int token, {
    required Duration duration,
  }) {
    if (!mounted || !_focusNode.hasFocus || token != _ensureVisibleToken) {
      return;
    }

    final scrollable = Scrollable.maybeOf(context);
    final renderObject = context.findRenderObject();
    if (scrollable == null || renderObject is! RenderBox) {
      return;
    }

    final keyboardInset = MediaQuery.viewInsetsOf(context).bottom;
    final screenHeight = MediaQuery.sizeOf(context).height;
    final safeBottom = MediaQuery.paddingOf(context).bottom;
    final visibleBottom = screenHeight - keyboardInset - safeBottom - 24;
    final fieldBottom =
        renderObject.localToGlobal(Offset(0, renderObject.size.height)).dy;
    final coveredDistance = fieldBottom - visibleBottom;

    if (coveredDistance > 6) {
      final position = scrollable.position;
      final target = (position.pixels + coveredDistance + 18).clamp(
        position.minScrollExtent,
        position.maxScrollExtent,
      );
      if ((target - position.pixels).abs() < 2) {
        return;
      }
      position.animateTo(
        target,
        duration: duration,
        curve: Curves.easeOutCubic,
      );
      return;
    }

    Scrollable.ensureVisible(
      context,
      duration: duration,
      curve: Curves.easeOutCubic,
      alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtEnd,
    );
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      focusNode: _focusNode,
      controller: widget.controller,
      keyboardType: widget.keyboardType,
      scrollPadding: widget.scrollPadding,
      textInputAction: widget.textInputAction,
      obscureText: widget.obscureText,
      decoration: widget.decoration,
      onTap: _scheduleEnsureVisible,
    );
  }
}

class _PasswordVisibilityButton extends StatelessWidget {
  const _PasswordVisibilityButton({
    required this.obscure,
    required this.color,
    required this.onPressed,
  });

  final bool obscure;
  final Color color;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: onPressed,
      icon: Icon(
        obscure ? Icons.visibility_rounded : Icons.visibility_off_rounded,
        color: color,
      ),
    );
  }
}
