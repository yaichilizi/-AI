# 职启AI Web 版

这是一个可本地运行、可部署到公网、可绑定正式域名的网页版求职助手。

## 功能

- 简历导入与解析
- 简历诊断与评分建议
- 岗位匹配
- 模拟面试题生成
- 面试回答复盘
- 招聘网站搜索入口
- DeepSeek AI 增强分析

## 本地启动

```powershell
cd C:\Users\ZhuanZ（无密码）\Documents\Codex\2026-06-11\职启AI\work\ai-career-coach
pip install -r requirements.txt
$env:DEEPSEEK_API_KEY="你的 DeepSeek Key"
python .\main.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

运行 `python .\main.py` 或 `python .\app.py` 时，本地环境会自动打开浏览器。

## 生产部署

项目已包含：

- `requirements.txt`
- `render.yaml`
- `/healthz` 健康检查接口
- `gunicorn` 启动方式

推荐部署到 Render。

## 环境变量

至少需要配置：

```text
DEEPSEEK_API_KEY=你的 DeepSeek Key
```

本地开发可参考 `.env.example`。

## Render 部署步骤

1. 把项目推到 GitHub。
2. 在 Render 创建新的 Web Service。
3. 连接仓库后，Render 会读取 `render.yaml`。
4. 在 Render 控制台配置环境变量 `DEEPSEEK_API_KEY`。
5. 部署完成后先验证：

```text
https://你的-render-地址/healthz
```

## 正式域名

部署成功后，可在 Render 后台给服务绑定自定义域名，例如：

```text
app.yourdomain.com
```

然后按 Render 提示去你的域名服务商添加 DNS 记录。

## 目录结构

```text
ai-career-coach/
  app.py
  main.py
  requirements.txt
  render.yaml
  .env.example
  data/
    jobs.json
    sample_resume.txt
  templates/
    index.html
  static/
    styles.css
    app.js
```

## 安全说明

不要把真实 API Key 写死在源码里。建议将此前暴露过的 DeepSeek Key 立即轮换，并仅通过环境变量配置。
