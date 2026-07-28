import 'package:error_log_app/main.dart';
import 'package:error_log_app/core/network/api_client.dart';
import 'package:error_log_app/features/auth/data/auth_api.dart';
import 'package:error_log_app/features/login/presentation/pages/login_page.dart';
import 'package:error_log_app/features/login/presentation/widgets/login_form_panel.dart';
import 'package:error_log_app/features/login/presentation/widgets/login_hero_panel.dart';
import 'package:error_log_app/features/home/presentation/widgets/home_hero.dart';
import 'package:error_log_app/features/workspace/presentation/pages/workspace_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('首页显示品牌、主视觉文案和操作按钮', (tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('智卷错题本'), findsOneWidget);
    expect(find.text('AI 驱动 · 专为学生设计'), findsOneWidget);
    expect(find.text('重塑错题整理'), findsOneWidget);
    expect(find.text('一键生成知识图谱'), findsOneWidget);
    expect(find.text('开始使用'), findsOneWidget);
    expect(find.text('查看演示'), findsNothing);
    expect(find.text('进入工作台'), findsNothing);
  });

  testWidgets('点击开始使用后显示登录页', (tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('欢迎回来'), findsOneWidget);
    expect(find.text('登录以继续使用你的错题本'), findsOneWidget);
    expect(find.text('请输入邮箱或用户名'), findsOneWidget);
    expect(find.text('请输入密码'), findsOneWidget);
  });

  testWidgets('登录页点击登录后进入工作台', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        routes: {
          '/': (_) => LoginPage(authApi: _FakeAuthApi()),
          '/workspace': (_) => const Scaffold(body: Text('工作台页面搭建中')),
        },
      ),
    );

    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), 'student@example.com');
    await tester.enterText(fields.at(1), '123456');
    await tester.ensureVisible(find.text('登录').last);
    await tester.pump();
    await tester.tap(find.text('登录').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('工作台页面搭建中'), findsOneWidget);
  });

  testWidgets('注册页可以发送验证码并创建账户', (tester) async {
    final authApi = _FakeAuthApi();
    var enteredWorkspace = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: LoginFormPanel(
              authApi: authApi,
              onLogin: () {
                enteredWorkspace = true;
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('注册'));
    await tester.pump();
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), 'student01');
    await tester.enterText(fields.at(1), 'student@example.com');
    await tester.enterText(fields.at(2), '654321');
    await tester.enterText(fields.at(3), '123456');
    await tester.enterText(fields.at(4), '123456');
    await tester.ensureVisible(find.text('发送验证码'));
    await tester.pump();
    await tester.tap(find.text('发送验证码'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(authApi.sentCodeEmail, 'student@example.com');
    expect(find.text('验证码已发送'), findsOneWidget);

    ScaffoldMessenger.of(tester.element(find.byType(LoginFormPanel)))
        .clearSnackBars();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 250));
    await tester.ensureVisible(find.text('创建账户').last);
    await tester.pump();
    await tester.tap(find.text('创建账户').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(authApi.registeredEmail, 'student@example.com');
    expect(enteredWorkspace, isTrue);
  });

  testWidgets('首页渲染 logo 和全局闪烁星空层', (tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.byKey(const Key('app-logo')), findsOneWidget);
    expect(find.byKey(const Key('global-star-field')), findsOneWidget);
  });

  testWidgets('首页 logo 使用白色 SVG', (tester) async {
    await tester.pumpWidget(const MyApp());

    final logo = tester.widget<SvgPicture>(find.byKey(const Key('app-logo')));
    expect(logo.colorFilter.toString(), contains('Color(0xffffffff)'));
  });

  testWidgets('知识图谱标题使用流动渐变文字', (tester) async {
    await tester.pumpWidget(const MyApp());

    final flowingTitle = find.byType(FlowingGradientText);
    expect(flowingTitle, findsOneWidget);

    final widget = tester.widget<FlowingGradientText>(flowingTitle);
    expect(widget.text, '一键生成知识图谱');
    expect(widget.colors.length, greaterThanOrEqualTo(3));
  });

  testWidgets('登录页有专属流动波浪', (tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byType(FlowingLoginWave), findsOneWidget);
  });

  test('登录页波浪固定路径并只移动颜色渐变', () {
    const size = Size(820, 420);
    const startPainter = LoginWavePainter(progress: 0, isLight: false);
    const middlePainter = LoginWavePainter(progress: 0.5, isLight: false);

    expect(startPainter.buildWavePath(size).getBounds(),
        middlePainter.buildWavePath(size).getBounds());
    expect(startPainter.buildShaderRect(size),
        isNot(middlePainter.buildShaderRect(size)));
  });

  testWidgets('登录页可以切换到注册表单', (tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('注册'));
    await tester.pump();

    expect(find.text('创建账户'), findsNWidgets(2));
    expect(find.text('免费注册，开始智能错题整理'), findsOneWidget);
    expect(find.text('用户名'), findsOneWidget);
    expect(find.text('邮箱'), findsOneWidget);
    expect(find.text('发送验证码'), findsOneWidget);
    expect(find.text('验证码'), findsOneWidget);
    expect(find.text('确认密码'), findsOneWidget);
    expect(find.text('您的昵称'), findsOneWidget);
    expect(find.text('your@email.com'), findsOneWidget);
    expect(find.text('6 位验证码'), findsOneWidget);
    expect(find.text('至少 6 位'), findsOneWidget);
    expect(find.text('再次输入密码'), findsOneWidget);
  });

  testWidgets('注册表单可以切回登录表单', (tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('注册'));
    await tester.pump();
    await tester.tap(find.text('登录').first);
    await tester.pump();

    expect(find.text('欢迎回来'), findsOneWidget);
    expect(find.text('登录以继续使用你的错题本'), findsOneWidget);
    expect(find.text('创建账户'), findsNothing);
  });

  testWidgets('首页提供全局太阳月亮主题切换按钮', (tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.byKey(const Key('theme-toggle-button')), findsOneWidget);
    expect(find.byIcon(Icons.light_mode_rounded), findsOneWidget);

    await tester.tap(find.byKey(const Key('theme-toggle-button')));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byIcon(Icons.dark_mode_rounded), findsOneWidget);
  });

  testWidgets('主题切换会记录到本地缓存', (tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.byKey(const Key('theme-toggle-button')));
    await tester.pump();

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('theme_mode'), 'light');
  });

  testWidgets('启动时读取本地缓存里的主题', (tester) async {
    SharedPreferences.setMockInitialValues({'theme_mode': 'light'});

    await tester.pumpWidget(const MyApp());
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byIcon(Icons.dark_mode_rounded), findsOneWidget);
  });

  testWidgets('点击开始使用时有有效 session 会进入工作台', (tester) async {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });

    await tester.pumpWidget(MyApp(authApi: _FakeAuthApi(hasSession: true)));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('开始使用'), findsOneWidget);
    expect(find.text('智能录入'), findsNothing);

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('智能录入'), findsOneWidget);
    expect(find.text('库'), findsOneWidget);
    expect(find.text('对话'), findsOneWidget);
    expect(find.text('我的'), findsOneWidget);
  });

  testWidgets('工作台键盘弹出时不压缩底部栏布局', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: WorkspacePage(),
      ),
    );

    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
    expect(scaffold.resizeToAvoidBottomInset, isFalse);
  });

  testWidgets('我的页可以切换主题并退出登录', (tester) async {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });
    final authApi = _FakeAuthApi(hasSession: true);

    await tester.pumpWidget(MyApp(authApi: authApi));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('我的'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('student01'), findsOneWidget);
    expect(find.text('@student01'), findsOneWidget);
    expect(find.text('切换为日间模式'), findsOneWidget);
    expect(find.text('退出登录'), findsOneWidget);

    await tester.tap(find.text('切换为日间模式'));
    await tester.pump();
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('theme_mode'), 'light');

    await tester.tap(find.text('退出登录'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(authApi.loggedOut, isTrue);
    expect(find.text('欢迎回来'), findsOneWidget);
  });

  testWidgets('用户资料设置页显示账户信息表单', (tester) async {
    SharedPreferences.setMockInitialValues({
      ApiClient.sessionCookieKey: 'session=abc123',
    });
    final authApi = _FakeAuthApi(hasSession: true);

    await tester.pumpWidget(MyApp(authApi: authApi));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.text('开始使用'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('我的'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('用户资料设置'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('账户信息'), findsOneWidget);
    expect(find.text('用户名'), findsOneWidget);
    expect(find.text('注册邮箱'), findsNothing);
    expect(find.text('显示名称'), findsOneWidget);
    expect(find.text('当前昵称'), findsOneWidget);
    expect(find.text('保存更改'), findsOneWidget);
  });
}

class _FakeAuthApi extends AuthApi {
  _FakeAuthApi({this.hasSession = false})
      : super(client: ApiClient(baseUrl: 'http://test'));

  String? sentCodeEmail;
  String? registeredEmail;
  bool loggedOut = false;
  final bool hasSession;

  @override
  Future<bool> hasStoredSession() async {
    return hasSession;
  }

  @override
  Future<AuthUser> me() async {
    return const AuthUser(
      id: 1,
      email: 'student@example.com',
      username: 'student01',
      isAdmin: false,
    );
  }

  @override
  Future<void> sendCode({
    required String email,
    String type = 'register',
  }) async {
    sentCodeEmail = email;
  }

  @override
  Future<AuthUser> login({
    required String identifier,
    required String password,
  }) async {
    return const AuthUser(
      id: 1,
      email: 'student@example.com',
      username: 'student01',
      isAdmin: false,
    );
  }

  @override
  Future<AuthUser> register({
    required String email,
    required String username,
    required String password,
    required String code,
  }) async {
    registeredEmail = email;
    return AuthUser(
      id: 2,
      email: email,
      username: username,
      isAdmin: false,
    );
  }

  @override
  Future<void> logout() async {
    loggedOut = true;
    await clearStoredSession();
  }
}
