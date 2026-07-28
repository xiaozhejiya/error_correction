# 单仓库 CI/CD

项目使用单仓库管理后端、前端和组件文档站。生产发布对标 `shunyuan`
项目的 Tag 发布方式：

- Pull Request 和 `main` 更新时，前后端按路径分别触发 CI。
- 推送 `v数字.数字.数字` Tag（例如 `v1.0.0`）时，执行完整测试、构建和部署。
- 也可以在 GitHub Actions 页面手动执行 `Application CI/CD`。
- 后端使用 Docker Compose，前端发布到 1Panel OpenResty 静态网站目录。
- 本机和公网健康检查失败时自动恢复上一版后端提交和前端静态文件。

## GitHub production 环境

在 fork 仓库 `IDhammaI/error_correction` 的
`Settings > Environments` 中创建 `production`。

Environment secrets：

| 名称 | 必填 | 说明 |
| --- | --- | --- |
| `DEPLOY_HOST` | 是 | SSH 主机，填写 `95.40.143.1`，不带协议。 |
| `DEPLOY_USER` | 是 | SSH 用户，填写 `ubuntu`。 |
| `DEPLOY_SSH_KEY` | 是 | CI/CD 专用 SSH 私钥全文。 |
| `DEPLOY_KNOWN_HOSTS` | 是 | 经人工核对指纹后的 SSH 主机公钥记录。 |

Environment variables：

| 名称 | 默认值 | 说明 |
| --- | --- | --- |
| `DEPLOY_PORT` | `22` | SSH 端口。 |
| `DEPLOY_PATH` | `/opt/error_correction` | 服务器仓库目录。 |
| `FRONTEND_DEPLOY_PATH` | `/opt/1panel/www/sites/lamp.dianchuang.club/index` | 1Panel 静态网站目录。 |
| `PRODUCTION_URL` | `https://lamp.dianchuang.club/` | 前端和 API 共用的公网入口。 |

不要把 SSH 密码、私钥、`.env`、SMTP 授权码或 Provider Token 提交到仓库。

## 发布

确认 `main` 已包含准备发布的内容后创建版本 Tag：

```bash
git switch main
git pull --ff-only
git tag v1.0.0
git push fork v1.0.0
```

流水线将依次执行：

1. 后端依赖安装、Pytest、Git LFS 模型检查和生产镜像构建。
2. 前端依赖安装、Vitest、TypeScript 检查和 Vite 生产构建。
3. 通过 SSH 在服务器检出 Tag 对应的精确提交。
4. 下载 Git LFS 擦除模型并执行 `docker compose up -d --build`。
5. 检查服务器本机 `/api/health`。
6. 原子替换 1Panel 静态网站目录。
7. 从 GitHub Runner 检查首页和公网 `/api/health`。

后端运行数据由 Docker 命名卷 `error_correction_backend_runtime` 保存。
重新构建容器不会主动删除 SQLite、上传文件、OCR 结果和日志。
