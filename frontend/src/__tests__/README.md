# 前端测试说明

## 技术栈

- **Vitest** — Vite 原生测试框架，兼容 Jest API
- **jsdom** — 浏览器环境模拟
- **@vue/test-utils** — Vue 3 官方测试工具库

## 运行测试

```bash
cd frontend

# 单次运行
npm test

# 监听模式（文件变更自动重跑）
npm run test:watch
```

## 测试文件一览

| 文件 | 测试数 | 说明 |
|------|--------|------|
| `utils.test.js` | 29 | 纯函数单元测试，覆盖 `fileKey`、`formatOption`、`isHtml`、`sanitizeHtml`、`clampScale` |
| `state.test.js` | 7 | 组件状态逻辑测试，覆盖主题切换、Toast 通知、图片预览弹窗、步骤指示器、文件上传区域 |
| `api.test.js` | 7 | API 交互测试，覆盖系统状态获取、HTTP 错误处理、网络异常处理、按钮禁用状态、重置行为 |

## 测试分层设计

参考后端 `tests/` 的测试风格，前端测试分为三层：

### 1. 纯函数测试（utils.test.js）

对应后端 `test_utils.py`。测试从 `App.vue` 提取到 `utils.js` 的纯函数，无需挂载组件，执行速度最快。

重点覆盖：
- 边界值（null、undefined、空字符串）
- XSS 防护（sanitizeHtml 过滤 script/iframe/style 等危险标签）
- 数值钳制（clampScale 的上下界）

### 2. 组件状态测试（state.test.js）

对应后端 `test_web_helpers.py`。通过挂载 App 组件验证内部状态管理逻辑。

重点覆盖：
- 暗色模式切换与 localStorage 持久化
- Toast 通知渲染
- 图片预览弹窗的显示/隐藏与键盘交互
- 步骤指示器的初始状态与样式
- 文件上传区域的键盘可访问性

### 3. API 交互测试（api.test.js）

对应后端 `test_question_tools.py`。通过 mock `global.fetch` 验证网络请求与错误处理。

重点覆盖：
- `fetchStatus` 成功/失败/异常三种路径
- 未上传文件时分割按钮禁用
- 未选择题目时导出按钮禁用
- 重置操作后状态归初始值

## 编写规范

- 测试描述使用中文，与 UI 文案保持一致
- 每个 `describe` 块对应一个功能模块
- 使用 `vi.fn()` / `vi.stubGlobal()` 进行 mock
- `afterEach` 中调用 `vi.restoreAllMocks()` 清理副作用
- HeadlessUI 组件使用 `stubs` 避免渲染依赖
