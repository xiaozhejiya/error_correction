import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../../app/theme/app_theme.dart';
import '../../../../core/constants/app_assets.dart';
import '../../../home/presentation/widgets/home_hero.dart';

class LoginHeroPanel extends StatelessWidget {
  const LoginHeroPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;
    final titleColor = Theme.of(context).colorScheme.onSurface;

    return Stack(
      fit: StackFit.expand,
      children: [
        const Positioned.fill(child: FlowingLoginWave()),
        Padding(
          padding: const EdgeInsets.fromLTRB(36, 28, 36, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 50,
                    height: 50,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.primary,
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.primary.withOpacity(0.28),
                          blurRadius: 28,
                          offset: const Offset(0, 12),
                        ),
                      ],
                    ),
                    child: SvgPicture.asset(
                      AppAssets.logo,
                      colorFilter: const ColorFilter.mode(
                        AppTheme.textPrimary,
                        BlendMode.srcIn,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Text(
                    '智卷错题本',
                    style: TextStyle(
                      color: titleColor,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Text(
                '重塑错题整理',
                style: TextStyle(
                  color: titleColor,
                  fontSize: 28,
                  height: 1.1,
                  fontWeight: FontWeight.w900,
                ),
              ),
              FlowingGradientText(
                text: '一键生成知识图谱',
                style: const TextStyle(
                  fontSize: 32,
                  height: 1.12,
                  fontWeight: FontWeight.w900,
                ),
                colors: [
                  AppTheme.primary,
                  isLight ? AppTheme.primaryLight : AppTheme.textPrimary,
                  AppTheme.primaryLight,
                  AppTheme.primary,
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class FlowingLoginWave extends StatefulWidget {
  const FlowingLoginWave({super.key});

  @override
  State<FlowingLoginWave> createState() => _FlowingLoginWaveState();
}

class _FlowingLoginWaveState extends State<FlowingLoginWave>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return CustomPaint(
          painter: LoginWavePainter(
            progress: _controller.value,
            isLight: isLight,
          ),
        );
      },
    );
  }
}

class LoginWavePainter extends CustomPainter {
  const LoginWavePainter({
    required this.progress,
    required this.isLight,
  });

  final double progress;
  final bool isLight;

  @visibleForTesting
  Path buildWavePath(Size size) {
    final w = size.width;
    final h = size.height;

    final baseY = h * 0.74;
    final amplitude = h * 0.2;

    return Path()
      ..moveTo(-w * 0.18, baseY)
      ..cubicTo(
        w * 0.02,
        baseY + amplitude * 0.55,
        w * 0.18,
        baseY + amplitude * 1.15,
        w * 0.34,
        baseY + amplitude * 0.42,
      )
      ..cubicTo(
        w * 0.48,
        baseY - amplitude * 0.28,
        w * 0.58,
        baseY - amplitude * 1.55,
        w * 0.74,
        baseY - amplitude * 0.7,
      )
      ..cubicTo(
        w * 0.88,
        baseY + amplitude * 0.05,
        w * 0.98,
        baseY + amplitude * 0.95,
        w * 1.12,
        baseY + amplitude * 0.28,
      )
      ..cubicTo(
        w * 1.22,
        baseY - amplitude * 0.22,
        w * 1.3,
        baseY - amplitude * 0.62,
        w * 1.42,
        baseY - amplitude * 0.18,
      );
  }

  @visibleForTesting
  Rect buildShaderRect(Size size) {
    final shaderWidth = size.width * 2.4;
    final dx = shaderWidth * progress;

    return Rect.fromLTWH(
      -shaderWidth + dx,
      0,
      shaderWidth,
      size.height,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    final path = buildWavePath(size);

    final baseColor = isLight
        ? AppTheme.primary.withOpacity(0.24)
        : AppTheme.primaryLight.withOpacity(0.18);

    final basePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = baseColor;

    canvas.drawPath(path, basePaint);

    final shaderRect = buildShaderRect(size);

    final movingPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.6
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..shader = LinearGradient(
        begin: Alignment.centerLeft,
        end: Alignment.centerRight,
        tileMode: TileMode.repeated,
        colors: [
          Colors.white.withOpacity(isLight ? 0.12 : 0.1),
          Colors.white.withOpacity(isLight ? 0.28 : 0.2),
          AppTheme.primaryLight.withOpacity(isLight ? 0.12 : 0.1),
          AppTheme.primaryLight.withOpacity(isLight ? 0.58 : 0.38),
          AppTheme.primary.withOpacity(isLight ? 0.78 : 0.56),
          Colors.white.withOpacity(isLight ? 0.12 : 0.1),
        ],
        stops: const [
          0.0,
          0.22,
          0.42,
          0.62,
          0.82,
          1.0,
        ],
      ).createShader(shaderRect);

    canvas.drawPath(path, movingPaint);
  }

  @override
  bool shouldRepaint(covariant LoginWavePainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.isLight != isLight;
  }
}
