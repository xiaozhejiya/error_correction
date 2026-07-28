import 'package:flutter/material.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/widgets/gradient_action_button.dart';

class HomeHero extends StatelessWidget {
  const HomeHero({super.key, required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final titleSize = width < 420 ? 34.0 : 44.0;
    final colorScheme = Theme.of(context).colorScheme;
    final secondaryTextColor = Theme.of(context).brightness == Brightness.light
        ? AppTheme.lightTextSecondary
        : AppTheme.textSecondary;

    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 720),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.primary, AppTheme.primaryLight],
              ),
              borderRadius: BorderRadius.circular(999),
            ),
            child: const Text(
              'AI 驱动 · 专为学生设计',
              style: TextStyle(
                color: AppTheme.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 28),
          Text(
            '重塑错题整理',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: colorScheme.onSurface,
              fontSize: titleSize,
              fontWeight: FontWeight.w900,
              height: 1.16,
            ),
          ),
          FlowingGradientText(
            text: '一键生成知识图谱',
            style: TextStyle(
              fontSize: titleSize,
              fontWeight: FontWeight.w900,
              height: 1.16,
            ),
          ),
          const SizedBox(height: 28),
          Text(
            '上传试卷或手写笔记，AI 自动完成 OCR 识别、题目分割、公式还原、知识点标注。',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: secondaryTextColor,
              fontSize: 18,
              height: 1.7,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 34),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 14,
            runSpacing: 12,
            children: [
              GradientActionButton(
                label: '开始使用',
                icon: Icons.cloud_upload_outlined,
                onPressed: onStart,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class FlowingGradientText extends StatefulWidget {
  const FlowingGradientText({
    super.key,
    required this.text,
    required this.style,
    this.colors = const [
      AppTheme.primaryLight,
      AppTheme.textPrimary,
      AppTheme.primary,
      AppTheme.primaryLight,
    ],
  });

  final String text;
  final TextStyle style;
  final List<Color> colors;

  @override
  State<FlowingGradientText> createState() => _FlowingGradientTextState();
}

class _FlowingGradientTextState extends State<FlowingGradientText>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2600),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return ShaderMask(
          blendMode: BlendMode.srcIn,
          shaderCallback: (bounds) {
            final flowOffset = bounds.width * (_controller.value * 2 - 1);
            final shaderBounds = Rect.fromLTWH(
              bounds.left + flowOffset,
              bounds.top,
              bounds.width * 2,
              bounds.height,
            );
            return LinearGradient(
              colors: widget.colors,
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
            ).createShader(shaderBounds);
          },
          child: child,
        );
      },
      child: Text(
        widget.text,
        textAlign: TextAlign.center,
        style: widget.style.copyWith(color: AppTheme.textPrimary),
      ),
    );
  }
}
