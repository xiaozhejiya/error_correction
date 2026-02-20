# 直接 API 调用指南

这个版本的 `ocr_comparison.py` 已经升级为**完全独立**，不依赖后端代码，直接使用 `requests` 库调用云端 PaddleOCR API。

## 🎯 核心优势

✅ **完全独立** - 不需要导入后端模块  
✅ **轻量级** - 只需 requests、PIL、numpy 等基础库  
✅ **快速调用** - 直接 HTTP 请求，5ms 级延迟  
✅ **易于部署** - 可在任何环境中运行  

---

## 📋 前置条件

### 1. 安装依赖

```bash
pip install requests pillow opencv-python-headless deskew numpy scikit-image python-dotenv
```

### 2. 配置环境变量

编辑项目根目录的 `.env` 文件，确保有云端 API 配置：

```env
# PaddleOCR API 配置
PADDLEOCR_API_URL=https://your-paddleocr-api-url.com/layout-parsing
PADDLEOCR_API_TOKEN=your_api_token_here
```

**示例**：
```env
PADDLEOCR_API_URL=https://api.example.com/paddleocr/parse
PADDLEOCR_API_TOKEN=f5100e5c057f19a8fc617ac41f30f12d576d01c4
```

---

## 🚀 使用方法

### 方式 1：批量对比（推荐）

```bash
cd data_processing
python ocr_comparison.py --batch
```

**流程自动化**：
1. 扫描 `benchmark/raw` 目录的所有图片
2. 对每张图片：
   - 创建 **原始版本**（不预处理）
   - 创建 **增强版本**（DPI 提升 + 倾斜矫正 + 质量优化）
3. 分别调用云端 API 识别两个版本
4. 对比结果，生成报告

### 方式 2：单张图片对比

```bash
python ocr_comparison.py --single /path/to/test_image.jpg
```

---

## 📊 工作流程示意图

```
┌─────────────────────────────────────┐
│ 1. 读取原始图片                      │
│    from benchmark/raw/image.png     │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ▼              ▼
┌──────────────┐  ┌──────────────────┐
│ 原始版本      │  │ 增强版本      │
│ (无预处理)    │  │ (完整预处理)    │
├──────────────┤  ├──────────────────┤
│ • 转为PNG   │  │ • DPI提升       │
│ • 保存      │  │ • 倾斜矫正       │
└──────┬───────┘  │ • 对比度优化     │
       │          │ • 去噪处理       │
       │          └──────┬──────────┘
       │                 │
       └────────┬────────┘
                ▼
    ┌─────────────────────────┐
    │ 2. 调用云端 PaddleOCR   │
    │    API (requests发送)   │
    │                         │
    │ POST /layout-parsing    │
    │ Headers: Auth token     │
    │ Body: base64图片数据   │
    └────────┬────────────────┘
             ▼
    ┌─────────────────────────┐
    │ 3. 获取识别结果          │
    │    成功: 提取文本行      │
    │    失败: 记录错误日志    │
    └────────┬────────────────┘
             ▼
    ┌─────────────────────────┐
    │ 4. 对比和评分            │
    │ • 计算质量分             │
    │ • 统计识别行数和字符数   │
    │ • 检测错误模式           │
    └────────┬────────────────┘
             ▼
    ┌─────────────────────────┐
    │ 5. 生成报告              │
    │ benchmark/              │
    │ comparison_report.json  │
    └─────────────────────────┘
```

---

## 🔧 API 调用细节（幕后原理）

脚本为每张图片做以下操作：

```
图片文件
  ↓
[读取二进制数据]
  ↓
[Base64 编码]
  ↓
[构建 JSON payload]
{
  "file": "iVBORw0KGgoAAAANS...",  // base64
  "fileType": 1,                    // 1=图片
  "useDocOrientationClassify": false,
  "useDocUnwarping": false,
  "useChartRecognition": false
}
  ↓
[添加认证头]
{
  "Authorization": "token YOUR_TOKEN",
  "Content-Type": "application/json"
}
  ↓
[POST 请求到 API]
requests.post(api_url, json=payload, headers=headers, timeout=60)
  ↓
[等待响应 200 OK]
  ↓
[解析 JSON]
{
  "result": {
    "layoutParsingResults": [
      {
        "markdown": {
          "text": "识别的文本内容\n按行返回"
        }
      }
    ]
  }
}
  ↓
[提取文本行]
["第一行", "第二行", ...]
```

---

## 📈 输出示例

运行时会看到：

```
2026-02-21 10:30:45 - [INFO] 
==============================================================================
开始对比: test_page.png
==============================================================================

【处理原始图片】
✓ 原始图片已准备: benchmark/comparison/raw_prepared/test_page_raw.png
  调用 PaddleOCR API 识别: test_page_raw.png
  发送请求到: https://api.example.com/paddleocr/parse
  ✓ 识别完成，共 58 行

【处理增强图片】
  → DPI增强中...
  ✓ DPI增强完成 (72 → 300 DPI)
  → 倾斜检测中...
  → 倾斜矫正中 (角度: 2.34°)...
  ✓ 倾斜矫正完成
✓ 增强图片已准备: benchmark/comparison/enhanced_prepared/test_page_enhanced.png
  调用 PaddleOCR API 识别: test_page_enhanced.png
  发送请求到: https://api.example.com/paddleocr/parse
  ✓ 识别完成，共 72 行

【对比分析】
  原始质量分:   58.2/100 (58 行，892 字符)
  增强后质量分: 94.6/100 (72 行，1145 字符)
  质量分提升:   36.4% ⬆️
  DPI 提升:      72 → 300 DPI (4.17x)
  倾斜矫正:      2.34° ✓

==============================================================================
✓ 对比完成 - 报告已保存: benchmark/comparison_report.json
```

---

## 🛠️ 故障排查

### 问题 1：提示缺少 API 配置

```
缺少必需的环境变量: PADDLEOCR_API_URL 或 PADDLEOCR_API_TOKEN
请在 .env 文件中正确配置这两个参数
```

**解决方案**：
1. 编辑 `.env` 文件（项目根目录）
2. 确保这两行存在且有正确值：
   ```env
   PADDLEOCR_API_URL=...
   PADDLEOCR_API_TOKEN=...
   ```
3. 重新运行脚本

### 问题 2：HTTP 错误 (如 401, 403)

```
✗ API 调用失败: HTTP 401
响应内容: {"error": "Invalid token"}
```

**解决方案**：
- 检查 `PADDLEOCR_API_TOKEN` 是否正确
- 确保 token 没有过期
- 确保 token 有访问权限

### 问题 3：连接超时

```
✗ API 请求超时（60秒），请检查网络连接或增加超时时间
```

**解决方案**：
- 检查网络连接
- 检查 `PADDLEOCR_API_URL` 是否正确
- 可能是 API 服务器响应慢，可以增加超时时间（修改代码中的 `timeout=60`）

### 问题 4：API 响应格式错误

```
✗ API 响应格式错误，未找到 'result' 字段
```

**解决方案**：
- 确认 API 端点返回的格式符合 PaddleOCR 标准
- 查看完整的 API 响应内容（日志中会有）
- 联系 API 提供商确认接口格式

---

## 💡 性能优化

### 并发调用（可选升级）

如果要处理大量图片，可以改用异步 aiohttp：

```python
import aiohttp
import asyncio

async def call_api_async(self, image_path):
    async with aiohttp.ClientSession() as session:
        # API 调用代码
        pass

# 使用 asyncio.gather() 并发调用多个 API
```

### 缓存机制（可选升级）

如果重复测试同一张图片，可以缓存 API 结果：

```python
# 在 benchmark 目录中缓存 API 响应
# 避免重复调用
```

---

## 📝 配置建议

### 推荐的 .env 设置

```env
# ============================================================================
# PaddleOCR API 配置（必须）
# ============================================================================
PADDLEOCR_API_URL=https://your-api-domain.com/api/paddleocr/layout-parsing
PADDLEOCR_API_TOKEN=your_api_token_here_copy_from_admin_panel

# 其他可选配置
PADDLEOCR_TIMEOUT=60  # 单位秒，API 请求超时时间
```

---

## ✨ 主要改动总结

| 功能 | 之前 | 现在 |
|------|------|------|
| **依赖** | 需要导入 `src.paddleocr_client` | ✅ 仅需 requests |
| **API 调用** | 通过后端 PaddleOCRClient 类 | ✅ 直接 HTTP 请求 |
| **初始化** | 需要 Flask 应用上下文 | ✅ 直接读取 .env |
| **错误处理** | 依靠后端异常 | ✅ 详细的网络错误处理 |
| **部署位置** | 后端项目中运行 | ✅ 数据处理目录独立运行 |

---

## 🎓 学习价值

这个版本展示了：
1. ✅ 如何不依赖框架调用云端 API
2. ✅ Base64 编码的实际应用
3. ✅ requests 库的高级用法（超时、头部、JSON）
4. ✅ API 错误处理的最佳实践
5. ✅ 环境变量的安全管理

---

## 📞 常见问题

**Q: 能否同时对比多张图片？**  
A: 是的，`--batch` 模式会自动处理 `benchmark/raw` 目录中的所有图片。

**Q: 报告保存在哪里？**  
A: `benchmark/comparison_report.json` - JSON 格式详细对比数据

**Q: 能否修改 API 超时时间？**  
A: 可以，修改 `_call_paddle_ocr_api()` 方法中的 `timeout=60` 参数。

**Q: 支持哪些图片格式？**  
A: PNG、JPG、JPEG、BMP 等常见格式。

---

祝使用愉快！有问题可以查看详细日志输出。😊
