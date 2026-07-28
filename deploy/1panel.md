# 1Panel 服务器初始化

目标服务器：

- SSH 主机：`95.40.143.1`
- SSH 用户：`ubuntu`
- 站点：`https://lamp.dianchuang.club/`
- 后端：同域名下的 `/api/*`，不需要单独 API 域名
- 后端本机端口：`127.0.0.1:15001`

## 1. 安装服务器依赖

服务器需要 Git、Git LFS、Docker 和 Docker Compose 插件。以 Ubuntu 为例：

```bash
sudo apt-get update
sudo apt-get install -y git git-lfs
git lfs install
docker --version
docker compose version
```

将 `ubuntu` 加入 Docker 用户组后需要重新登录：

```bash
sudo usermod -aG docker ubuntu
```

## 2. 初始化后端仓库

```bash
sudo mkdir -p /opt/error_correction
sudo chown ubuntu:ubuntu /opt/error_correction
git clone https://github.com/IDhammaI/error_correction.git /opt/error_correction
cd /opt/error_correction
git lfs pull
cp backend/.env.example .env
```

编辑 `/opt/error_correction/.env`，至少设置强随机 `SECRET_KEY`，并保持：

```dotenv
FLASK_DEBUG=false
```

SMTP 和平台托管 Provider 按实际需要配置。用户级 LLM/OCR Provider 可在部署后通过
系统设置页面写入持久化 SQLite。

首次启动：

```bash
cd /opt/error_correction
docker compose up -d --build
curl --fail http://127.0.0.1:15001/api/health
```

## 3. 初始化 1Panel 网站

在 1Panel 创建静态网站 `lamp.dianchuang.club` 并申请 HTTPS 证书。确认实际网站目录；
默认预期为：

```text
/opt/1panel/www/sites/lamp.dianchuang.club/index
```

若实际目录不同，需要同步修改 GitHub Environment Variable
`FRONTEND_DEPLOY_PATH`。

授权部署用户替换静态目录：

```bash
SITE_PARENT=/opt/1panel/www/sites/lamp.dianchuang.club
sudo chown ubuntu:ubuntu "$SITE_PARENT"
sudo chown -R ubuntu:ubuntu "$SITE_PARENT/index"
sudo chmod 755 "$SITE_PARENT"
sudo find "$SITE_PARENT/index" -type d -exec chmod 755 {} +
sudo find "$SITE_PARENT/index" -type f -exec chmod 644 {} +
```

将 `deploy/nginx.conf` 中的配置合并到该网站的 OpenResty 配置并重载。
`/api`、文件预览和下载路径均反向代理到后端，其他路径由 Vue SPA 处理。

## 4. 配置 SSH 部署密钥

为 CI/CD 单独生成密钥，不复用个人登录私钥。将公钥追加到：

```text
/home/ubuntu/.ssh/authorized_keys
```

私钥全文保存到 GitHub `production` Environment Secret
`DEPLOY_SSH_KEY`。

从可信终端获取主机公钥，并人工核对服务器指纹后保存为
`DEPLOY_KNOWN_HOSTS`：

```bash
ssh-keyscan -p 22 95.40.143.1
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

不要只依赖流水线运行时临时扫描到的主机密钥。

## 5. 资源说明

服务器为 2 核 4 GB 时保持：

- Gunicorn worker：1
- Gunicorn threads：4
- CPU 版 PyTorch
- Docker 构建期间避免同时运行其他高内存任务

擦除模型约 346 MB，Git LFS 和 Docker 镜像会占用额外磁盘空间。建议定期执行：

```bash
docker image prune
```

不要删除 Docker 命名卷 `error_correction_backend_runtime`，其中包含生产 SQLite
数据库及运行文件。
