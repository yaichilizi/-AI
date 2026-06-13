from __future__ import annotations

import json
import os
import re
import threading
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import requests
from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"
ASSETS_DIR = PUBLIC_DIR / "assets"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

SKILL_KEYWORDS = {
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "sql": "SQL",
    "mysql": "MySQL",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "机器学习": "机器学习",
    "深度学习": "深度学习",
    "自然语言处理": "自然语言处理",
    "nlp": "自然语言处理",
    "计算机视觉": "计算机视觉",
    "cv": "计算机视觉",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "vue": "Vue",
    "react": "React",
    "数据分析": "数据分析",
    "数据挖掘": "数据挖掘",
    "推荐系统": "推荐系统",
    "大模型": "大模型",
    "llm": "大模型",
    "rag": "RAG",
    "向量数据库": "向量数据库",
    "xgboost": "XGBoost",
    "随机森林": "随机森林",
    "excel": "Excel",
}

ACTION_WORDS = ["负责", "设计", "开发", "实现", "优化", "构建", "训练", "部署", "分析", "提升"]
SECTION_TITLES = (
    "教育背景",
    "技能",
    "专业技能",
    "项目经历",
    "项目经验",
    "实习经历",
    "工作经历",
    "竞赛经历",
    "校园经历",
    "自我评价",
    "个人优势",
)
PROJECT_SECTION_TITLES = ("项目经历", "项目经验", "项目", "科研项目", "课程项目")


@dataclass
class ResumeProfile:
    name: str
    major: str
    text: str
    skills: list[str]
    projects: list[str]


@dataclass
class Job:
    title: str
    company: str
    description: str
    required_skills: list[str]
    interview_focus: list[str]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_jobs(path: Path) -> list[Job]:
    data = load_json(path)
    return [Job(**item) for item in data["jobs"]]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_skills(text: str) -> list[str]:
    lower_text = normalize_text(text)
    skills = {
        normalized
        for keyword, normalized in SKILL_KEYWORDS.items()
        if re.search(rf"(?<![a-z0-9+]){re.escape(keyword.lower())}(?![a-z0-9+])", lower_text)
    }
    return sorted(skills)


def split_projects(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    projects: list[str] = []
    in_project_section = False
    current_project: list[str] = []

    def flush_current() -> None:
        if current_project:
            project = " ".join(current_project).strip()
            if project and project not in projects:
                projects.append(project)
            current_project.clear()

    for line in lines:
        title = line.rstrip("：:")
        is_section_title = line.endswith(("：", ":")) and title in SECTION_TITLES
        if is_section_title:
            flush_current()
            in_project_section = title in PROJECT_SECTION_TITLES
            continue

        numbered = re.match(r"^\s*(?:\d+[.、]|[-*•])\s*(.+)", line)
        has_project_hint = bool(re.search(r"(项目|平台|系统|模型|应用|助手|网站|小程序|算法|分析)", line))
        has_action_hint = any(word in line for word in ACTION_WORDS)

        if numbered:
            flush_current()
            candidate = numbered.group(1).strip()
            if in_project_section or has_project_hint:
                current_project.append(candidate)
            continue

        if in_project_section and (has_project_hint or has_action_hint):
            if current_project and len(" ".join(current_project)) < 120:
                current_project.append(line)
            else:
                flush_current()
                current_project.append(line)

    flush_current()
    return projects[:5]


def find_field(text: str, field: str) -> str | None:
    pattern = rf"{re.escape(field)}[：:]\s*(.+)"
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1).strip()


def parse_resume(text: str) -> ResumeProfile:
    return ResumeProfile(
        name=find_field(text, "姓名") or "未填写",
        major=find_field(text, "专业") or "未填写",
        text=text,
        skills=extract_skills(text),
        projects=split_projects(text),
    )


def score_resume(resume: ResumeProfile, job: Job | None = None) -> dict[str, Any]:
    text = resume.text
    score = 35
    suggestions: list[str] = []
    breakdown: list[str] = []

    if len(resume.skills) >= 5:
        score += 20
        breakdown.append("技能覆盖：20/20")
    else:
        partial = len(resume.skills) * 3
        score += partial
        breakdown.append(f"技能覆盖：{partial}/20")
        suggestions.append("技能关键词偏少，建议补充与目标岗位相关的技术栈。")

    if len(resume.projects) >= 2:
        score += 18
        breakdown.append("项目经历：18/18")
    else:
        partial = len(resume.projects) * 9
        score += partial
        breakdown.append(f"项目经历：{partial}/18")
        suggestions.append("项目经历偏少，建议至少补充 2 个可量化项目。")

    if any(char.isdigit() for char in text):
        score += 12
        breakdown.append("量化成果：12/12")
    else:
        breakdown.append("量化成果：0/12")
        suggestions.append("简历缺少量化成果，例如准确率、响应时间、用户数、排名等。")

    if any(word in text for word in ACTION_WORDS):
        score += 10
        breakdown.append("行动表达：10/10")
    else:
        breakdown.append("行动表达：0/10")
        suggestions.append('经历描述缺少动作动词，建议用“负责/实现/优化/部署”等表达贡献。')

    if job:
        matched = set(resume.skills) & set(job.required_skills)
        match_rate = len(matched) / max(len(job.required_skills), 1)
        job_score = round(match_rate * 20)
        score += job_score
        breakdown.append(f"岗位匹配：{job_score}/20")
        missing = sorted(set(job.required_skills) - set(resume.skills))
        if missing:
            suggestions.append(f"目标岗位仍缺少这些关键词：{', '.join(missing)}。")
    else:
        breakdown.append("岗位匹配：未选择目标岗位")

    return {
        "score": min(score, 100),
        "skills": resume.skills,
        "projects": resume.projects,
        "breakdown": breakdown,
        "suggestions": suggestions or ["简历结构较完整，可继续针对目标岗位强化成果表达。"],
    }


def match_jobs(resume: ResumeProfile, jobs: Iterable[Job]) -> list[dict[str, Any]]:
    results = []
    resume_skills = set(resume.skills)
    for job in jobs:
        required = set(job.required_skills)
        matched = sorted(resume_skills & required)
        missing = sorted(required - resume_skills)
        score = round(len(matched) / max(len(required), 1) * 100)
        results.append(
            {
                "job_id": f"{job.title}::{job.company}",
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "match_score": score,
                "matched_skills": matched,
                "missing_skills": missing,
            }
        )
    return sorted(results, key=lambda item: item["match_score"], reverse=True)


def generate_interview_questions(job: Job, resume: ResumeProfile) -> list[str]:
    primary_skill = job.required_skills[0] if job.required_skills else "核心技能"
    questions = [
        f"请用 1 分钟介绍你自己，并说明你为什么适合 {job.title} 岗位。",
        f"你做过的项目中，哪个最能体现你对 {primary_skill} 的掌握？",
        "请讲述一个你遇到技术困难并最终解决的经历。",
        f"如果让你负责“{job.description.rstrip('。')}”，你会如何拆解任务？",
    ]
    for focus in job.interview_focus[:3]:
        questions.append(f'围绕“{focus}”，请说明你的理解和实践经验。')
    if resume.projects:
        questions.append(f"请详细介绍这段经历，并说明你的个人贡献：{resume.projects[0]}")
    return questions


def review_answer(answer: str, job: Job) -> dict[str, Any]:
    text = answer.strip()
    score = 50
    feedback: list[str] = []

    if len(text) >= 120:
        score += 15
    else:
        feedback.append('回答偏短，建议用“背景-行动-结果”结构展开。')

    if any(skill in text for skill in job.required_skills):
        score += 15
    else:
        feedback.append("回答中没有明显体现岗位关键词，需要主动贴合 JD。")

    if any(char.isdigit() for char in text):
        score += 10
    else:
        feedback.append("缺少量化结果，建议补充准确率、耗时、规模、排名等数字。")

    if any(word in text for word in ACTION_WORDS):
        score += 10
    else:
        feedback.append("建议突出个人动作，例如负责了什么、实现了什么、优化了什么。")

    return {
        "score": min(score, 100),
        "feedback": feedback or ["回答结构较完整，建议继续增加真实项目细节。"],
    }


def read_uploaded_document(file_storage) -> str:
    filename = (file_storage.filename or "").lower()
    suffix = Path(filename).suffix

    if suffix == ".txt":
        return file_storage.read().decode("utf-8", errors="replace")
    if suffix == ".pdf":
        return read_pdf_bytes(file_storage.read())
    if suffix == ".docx":
        return read_docx_bytes(file_storage.read())

    raise ValueError("仅支持 .txt、.pdf、.docx 文件。")


def read_pdf_bytes(raw: bytes) -> str:
    errors: list[str] = []

    try:
        from io import BytesIO
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if text:
            return text
        errors.append("PyPDF2 未提取到文本，可能是扫描版 PDF。")
    except ImportError:
        errors.append("未安装 PyPDF2。")
    except Exception as exc:
        errors.append(f"PyPDF2 解析失败: {exc}")

    try:
        from io import BytesIO
        import pdfplumber

        with pdfplumber.open(BytesIO(raw)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if text:
            return text
        errors.append("pdfplumber 未提取到文本，可能需要 OCR。")
    except ImportError as exc:
        raise ImportError("解析 PDF 需要安装 PyPDF2 或 pdfplumber。") from exc
    except Exception as exc:
        raise RuntimeError(f"PDF 解析失败: {exc}") from exc

    raise RuntimeError("PDF 未提取到可用文本。 " + " ".join(errors))


def read_docx_bytes(raw: bytes) -> str:
    try:
        from io import BytesIO
        from docx import Document

        doc = Document(BytesIO(raw))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return "\n".join(paragraphs)
    except ImportError as exc:
        raise ImportError("解析 Word 需要安装 python-docx。") from exc
    except Exception as exc:
        raise RuntimeError(f"Word 解析失败: {exc}") from exc


def extract_json_block(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("模型返回中未找到 JSON。")
    return json.loads(match.group(0))


def call_deepseek(messages: list[dict[str, str]], temperature: float = 0.3) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DeepSeek API Key。")

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def build_ai_diagnosis(resume_text: str, resume: ResumeProfile, current_job: Job, fallback: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
你是中文求职教练。请基于简历和目标岗位，输出一个 JSON 对象，不要输出 markdown。

JSON 格式：
{{
  "summary": "1-2句总体判断",
  "highlights": ["亮点1", "亮点2", "亮点3"],
  "risks": ["风险1", "风险2", "风险3"],
  "rewrite_suggestions": ["建议1", "建议2", "建议3"]
}}

简历信息：
姓名：{resume.name}
专业：{resume.major}
识别技能：{", ".join(resume.skills) or "无"}
识别项目：{" | ".join(resume.projects) or "无"}

目标岗位：
岗位：{current_job.title}
公司：{current_job.company}
描述：{current_job.description}
技能要求：{", ".join(current_job.required_skills)}

规则分析结果：
评分：{fallback["score"]}
建议：{" | ".join(fallback["suggestions"])}

原始简历：
{resume_text}
""".strip()

    raw = call_deepseek(
        [
            {"role": "system", "content": "你是一个严格、专业、简洁的中文求职顾问。"},
            {"role": "user", "content": prompt},
        ]
    )
    return extract_json_block(raw)


def build_ai_interview_questions(resume: ResumeProfile, current_job: Job, fallback_questions: list[str]) -> list[str]:
    prompt = f"""
你是中文面试官。请基于简历和岗位，输出一个 JSON 对象，不要输出 markdown。

JSON 格式：
{{
  "questions": ["问题1", "问题2", "问题3", "问题4", "问题5", "问题6"]
}}

候选人技能：{", ".join(resume.skills) or "无"}
候选人项目：{" | ".join(resume.projects) or "无"}
岗位：{current_job.title}
岗位描述：{current_job.description}
岗位要求：{", ".join(current_job.required_skills)}
面试重点：{", ".join(current_job.interview_focus)}
规则版问题参考：{" | ".join(fallback_questions)}
""".strip()

    raw = call_deepseek(
        [
            {"role": "system", "content": "你是一个严格、专业、简洁的中文技术面试官。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
    )
    data = extract_json_block(raw)
    questions = data.get("questions") or []
    return [str(item).strip() for item in questions if str(item).strip()][:8]


def build_ai_review(answer: str, current_job: Job, fallback: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
你是中文面试复盘教练。请基于岗位和候选人回答，输出一个 JSON 对象，不要输出 markdown。

JSON 格式：
{{
  "score": 0,
  "summary": "一句话总结",
  "feedback": ["反馈1", "反馈2", "反馈3"],
  "improved_answer": "一段更好的示范回答"
}}

岗位：{current_job.title}
岗位描述：{current_job.description}
岗位要求：{", ".join(current_job.required_skills)}
规则版评分：{fallback["score"]}
规则版反馈：{" | ".join(fallback["feedback"])}

候选人回答：
{answer}
""".strip()

    raw = call_deepseek(
        [
            {"role": "system", "content": "你是一个严格、专业、简洁的中文面试复盘教练。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    data = extract_json_block(raw)
    score = int(data.get("score", fallback["score"]))
    feedback = [str(item).strip() for item in data.get("feedback", []) if str(item).strip()]
    return {
        "score": max(0, min(score, 100)),
        "summary": str(data.get("summary", "")).strip(),
        "feedback": feedback or fallback["feedback"],
        "improved_answer": str(data.get("improved_answer", "")).strip(),
    }


def build_analysis_payload(text: str, selected_job_id: str | None = None) -> dict[str, Any]:
    resume = parse_resume(text)
    matches = match_jobs(resume, JOBS)
    if not matches:
        raise ValueError("未找到可匹配的岗位。")

    job_lookup = {f"{job.title}::{job.company}": job for job in JOBS}
    chosen_job_id = selected_job_id if selected_job_id in job_lookup else matches[0]["job_id"]
    current_job = job_lookup[chosen_job_id]
    diagnosis = score_resume(resume, current_job)
    interview_questions = generate_interview_questions(current_job, resume)
    ai_enabled = False
    ai_error = ""
    ai_diagnosis: dict[str, Any] | None = None

    try:
        ai_diagnosis = build_ai_diagnosis(text, resume, current_job, diagnosis)
        ai_questions = build_ai_interview_questions(resume, current_job, interview_questions)
        if ai_questions:
            interview_questions = ai_questions
        ai_enabled = True
    except Exception as exc:
        ai_error = str(exc)

    return {
        "resume": asdict(resume),
        "diagnosis": diagnosis,
        "jobs": matches,
        "current_job_id": chosen_job_id,
        "current_job": asdict(current_job),
        "interview_questions": interview_questions,
        "ai_enabled": ai_enabled,
        "ai_error": ai_error,
        "ai_diagnosis": ai_diagnosis,
    }


app = Flask(__name__)
JOBS = load_jobs(DATA_DIR / "jobs.json")
SAMPLE_RESUME = (DATA_DIR / "sample_resume.txt").read_text(encoding="utf-8")
SAMPLE_ANSWER = (
    "我在课程项目中负责实现一个基于 Python 和 PyTorch 的文本分类模型，"
    "主要完成数据清洗、模型训练和结果分析。通过调整学习率和样本均衡策略，"
    "模型准确率从 82% 提升到 89%，并将实验过程整理成报告。"
)


@app.get("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(ASSETS_DIR, filename)


@app.get("/")
def index():
    return render_template(
        "index.html",
        sample_resume=SAMPLE_RESUME,
        sample_answer=SAMPLE_ANSWER,
        jobs=[asdict(job) for job in JOBS],
        ai_configured=bool(DEEPSEEK_API_KEY),
    )


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "ai_configured": bool(DEEPSEEK_API_KEY)})


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("resume_text") or "").strip()
    selected_job_id = payload.get("job_id")

    if not text:
        return jsonify({"error": "请先输入简历内容。"}), 400

    try:
        return jsonify(build_analysis_payload(text, selected_job_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/review")
def review():
    payload = request.get_json(silent=True) or {}
    answer = (payload.get("answer") or "").strip()
    job_id = payload.get("job_id")

    if not answer:
        return jsonify({"error": "请先输入面试回答。"}), 400
    if not job_id:
        return jsonify({"error": "请先完成简历分析并选择目标岗位。"}), 400

    job_lookup = {f"{job.title}::{job.company}": job for job in JOBS}
    current_job = job_lookup.get(job_id)
    if current_job is None:
        return jsonify({"error": "岗位信息无效，请重新分析。"}), 400

    fallback = review_answer(answer, current_job)
    result: dict[str, Any] = {
        **fallback,
        "summary": "",
        "improved_answer": "",
        "ai_enabled": False,
        "ai_error": "",
    }

    try:
        ai_review = build_ai_review(answer, current_job, fallback)
        result.update(ai_review)
        result["ai_enabled"] = True
    except Exception as exc:
        result["ai_error"] = str(exc)

    return jsonify(result)


@app.post("/api/import")
def import_resume():
    uploaded = request.files.get("resume_file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "请选择需要导入的简历文件。"}), 400

    try:
        text = read_uploaded_document(uploaded)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    if not text.strip():
        return jsonify({"error": "文件中未提取到文本内容。"}), 400

    return jsonify({"text": text})


def main() -> None:
    url = f"http://{HOST}:{PORT}"
    if HOST in {"127.0.0.1", "localhost"}:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
