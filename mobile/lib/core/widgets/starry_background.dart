import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/theme/app_theme.dart';

class StarryBackground extends StatelessWidget {
  const StarryBackground({
    super.key,
    required this.child,
    this.showHomeOrnaments = false,
    this.showStars = true,
  });

  final Widget child;
  final bool showHomeOrnaments;
  final bool showStars;

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isLight
              ? const [AppTheme.lightBackground, AppTheme.lightBackgroundAlt]
              : const [AppTheme.background, AppTheme.backgroundAlt],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: [
          CustomPaint(
            painter: _CosmicBackgroundPainter(
              isLight: isLight,
              showHomeOrnaments: showHomeOrnaments,
            ),
          ),
          if (showStars)
            AnimatedStarField(
              key: const Key('global-star-field'),
              isLight: isLight,
            ),
          child,
        ],
      ),
    );
  }
}

class AnimatedStarField extends StatelessWidget {
  const AnimatedStarField(
      {super.key, this.starCount = 38, this.isLight = false});

  final int starCount;
  final bool isLight;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Stack(
            children: List.generate(starCount, (index) {
              final width = math.max(constraints.maxWidth, 1);
              final height = math.max(constraints.maxHeight, 1);
              final left = ((index * 37) % 100) / 100 * width;
              final top = ((index * 53) % 100) / 100 * height;
              final size = 1.2 + (index % 3) * 0.7;

              return Positioned(
                left: left,
                top: top,
                child: _TwinklingStar(
                  index: index,
                  size: size,
                  isLight: isLight,
                ),
              );
            }),
          );
        },
      ),
    );
  }
}

class _TwinklingStar extends StatefulWidget {
  const _TwinklingStar({
    required this.index,
    required this.size,
    required this.isLight,
  });

  final int index;
  final double size;
  final bool isLight;

  @override
  State<_TwinklingStar> createState() => _TwinklingStarState();
}

class _TwinklingStarState extends State<_TwinklingStar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 1200 + widget.index % 8 * 220),
      value: (widget.index % 10) / 10,
    )..repeat(reverse: true);
    _opacity = Tween<double>(begin: 0.16, end: 0.9).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          color: widget.isLight ? AppTheme.primary : AppTheme.textPrimary,
          borderRadius: BorderRadius.circular(widget.size),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primaryLight.withOpacity(
                widget.isLight ? 0.22 : 0.45,
              ),
              blurRadius: widget.size * 4,
            ),
          ],
        ),
      ),
    );
  }
}

class _CosmicBackgroundPainter extends CustomPainter {
  const _CosmicBackgroundPainter({
    required this.isLight,
    required this.showHomeOrnaments,
  });

  final bool isLight;
  final bool showHomeOrnaments;

  @override
  void paint(Canvas canvas, Size size) {
    _drawGlow(
      canvas,
      center: Offset(size.width * 0.2, size.height * 0.08),
      radius: size.shortestSide * (isLight ? 0.7 : 0.45),
      color: isLight
          ? AppTheme.primary.withOpacity(0.22)
          : AppTheme.primary.withOpacity(0.28),
    );

    if (!showHomeOrnaments) {
      return;
    }

    _drawGlow(
      canvas,
      center: Offset(size.width * 0.82, size.height * 0.58),
      radius: size.shortestSide * (isLight ? 0.62 : 0.4),
      color: isLight
          ? AppTheme.primary.withOpacity(0.3)
          : AppTheme.primaryLight.withOpacity(0.3),
    );
    if (isLight) {
      _drawGlow(
        canvas,
        center: Offset(size.width * 0.38, size.height * 0.42),
        radius: size.shortestSide * 0.48,
        color: AppTheme.primaryLight.withOpacity(0.14),
      );
    }

    final linePaint = Paint()
      ..color = (isLight ? AppTheme.lightBorder : AppTheme.border).withOpacity(
        isLight ? 0.12 : 0.08,
      )
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final topRibbonPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: isLight
            ? [
                AppTheme.primary.withOpacity(0.36),
                AppTheme.primaryLight.withOpacity(0.14),
                Colors.transparent,
              ]
            : [
                AppTheme.primary.withOpacity(0.22),
                AppTheme.primaryLight.withOpacity(0.08),
                Colors.transparent,
              ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height * 0.24));
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height * 0.24),
      topRibbonPaint,
    );

    for (var i = 0; i < 5; i++) {
      final y = size.height * (0.2 + i * 0.15);
      final path = Path()
        ..moveTo(-40, y)
        ..cubicTo(
          size.width * 0.25,
          y - 70,
          size.width * 0.62,
          y + 78,
          size.width + 40,
          y - 30,
        );
      canvas.drawPath(path, linePaint);
    }
  }

  void _drawGlow(
    Canvas canvas, {
    required Offset center,
    required double radius,
    required Color color,
  }) {
    final rect = Rect.fromCircle(center: center, radius: radius);
    final paint = Paint()
      ..shader = RadialGradient(
        colors: [color, Colors.transparent],
      ).createShader(rect);
    canvas.drawCircle(center, radius, paint);
  }

  @override
  bool shouldRepaint(covariant _CosmicBackgroundPainter oldDelegate) {
    return oldDelegate.isLight != isLight ||
        oldDelegate.showHomeOrnaments != showHomeOrnaments;
  }
}
