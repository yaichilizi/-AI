# 职启AI 桌面版

这是一个用于展示以下流程的本地桌面版 MVP：

- 简历导入与解析
- 简历诊断与评分建议
- 岗位匹配
- 模拟面试题生成
- 面试回答复盘
- 招聘网站搜索入口

## 启动方式

```powershell
cd C:\Users\ZhuanZ（无密码）\Documents\Codex\2026-06-11\职启AI\work\ai-career-coach
python .\main.py
```

兼容入口：

```powershell
python .\app.py
```

## 可选依赖

如果需要导入 PDF 或 Word 简历，再额外安装：

```powershell
pip install PyPDF2 pdfplumber python-docx
```

## 目录结构

```text
ai-career-coach/
  app.py
  main.py
  data/
    jobs.json
    sample_resume.txt
```

## 当前实现说明

- 使用 `tkinter` 构建本地桌面界面
- 简历分析和岗位匹配基于本地规则逻辑
- 岗位数据来自 `data/jobs.json`
