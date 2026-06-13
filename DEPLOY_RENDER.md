# Render 部署与正式域名接入

## 目标

把 `职启AI` 部署到 Render，并绑定正式域名，例如：

- `app.yourdomain.com`
- `zhiqi.yourdomain.com`

## 代码已准备好的内容

- `requirements.txt`
- `render.yaml`
- `gunicorn` 启动命令
- `0.0.0.0:$PORT` 兼容
- `/healthz` 健康检查
- `DEEPSEEK_API_KEY` 环境变量配置

## 一次性准备

1. 把项目推到 GitHub 仓库。
2. 准备一个你自己可管理 DNS 的域名。
3. 到 Render 注册并登录。

## Render 部署

1. 进入 Render Dashboard。
2. 选择 `New` -> `Web Service`。
3. 连接你的 GitHub 仓库。
4. 选择这个项目所在仓库。
5. 如果 Render 识别到 `render.yaml`，直接按配置创建服务。
6. 在环境变量里配置：

```text
DEEPSEEK_API_KEY=你的真实 DeepSeek Key
```

7. 部署完成后先访问：

```text
https://你的服务名.onrender.com/healthz
```

返回 `ok: true` 就说明服务正常。

## 绑定正式域名

推荐优先绑定子域名，例如：

```text
app.yourdomain.com
```

这样最简单。

### 子域名绑定

1. 在 Render 服务的 `Settings` -> `Custom Domains` 添加：

```text
app.yourdomain.com
```

2. 到你的域名 DNS 服务商后台添加一条 `CNAME`：

```text
Host: app
Type: CNAME
Value: 你的服务名.onrender.com
```

3. 回到 Render 点击 `Verify`。

### 根域名绑定

如果你要直接绑定：

```text
yourdomain.com
```

优先使用 DNS 提供商支持的：

- `ANAME`
- `ALIAS`

目标指向：

```text
你的服务名.onrender.com
```

如果 DNS 服务商不支持 `ANAME` 或 `ALIAS`，再使用：

```text
A -> 216.24.57.1
```

然后在 Render 里验证。

## 注意事项

- 删除域名上的 `AAAA` 记录，避免和 Render 的 IPv4 解析冲突。
- Render 会自动签发并续期 HTTPS 证书。
- 正式域名生效通常取决于 DNS 传播时间，可能几分钟到数小时。

## 推荐做法

- 优先用子域名：`app.yourdomain.com`
- 不要把 API Key 写进源码
- 立即轮换之前暴露过的 DeepSeek Key
