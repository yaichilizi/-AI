from __future__ import annotations

import json
import re
import tkinter as tk
import urllib.parse
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

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


def score_resume(resume: ResumeProfile, job: Job | None = None) -> dict:
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


def match_jobs(resume: ResumeProfile, jobs: Iterable[Job]) -> list[dict]:
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


def review_answer(answer: str, job: Job) -> dict:
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


class CareerCoachApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("职启AI · 职业规划教练")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)
        self.root.configure(bg="#f0f4f8")

        self.jobs = load_jobs(DATA_DIR / "jobs.json")
        self.resume: ResumeProfile | None = None
        self.current_job: Job | None = None
        self.job_lookup: dict[str, Job] = {}
        self.combo_job_ids: list[str] = []

        self._build_ui()
        self._load_sample()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#1a73e8", height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="职启AI · 职业规划教练",
            font=("Microsoft YaHei", 18, "bold"),
            fg="white",
            bg="#1a73e8",
        ).pack(side=tk.LEFT, padx=20, pady=10)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=2)
        paned.add(right, weight=3)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_left_panel(self, parent: ttk.Frame):
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(title_frame, text="简历内容", font=("Microsoft YaHei", 13, "bold")).pack(side=tk.LEFT)

        self.resume_text = scrolledtext.ScrolledText(
            parent,
            height=14,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.resume_text.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)

        self.import_btn = tk.Button(
            btn_frame,
            text="导入文件",
            font=("Microsoft YaHei", 10),
            fg="white",
            bg="#1a73e8",
            activebackground="#1557b0",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=4,
            command=self._on_import,
        )
        self.import_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.analyze_btn = ttk.Button(btn_frame, text="一键分析", command=self._on_analyze)
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.reset_btn = ttk.Button(btn_frame, text="恢复示例", command=self._load_sample)
        self.reset_btn.pack(side=tk.LEFT)

        self.import_status = ttk.Label(
            parent,
            text="支持导入 .txt / .pdf / .docx 简历文件",
            font=("Microsoft YaHei", 8),
            foreground="#999",
        )
        self.import_status.pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(parent, text="面试回答复盘", font=("Microsoft YaHei", 13, "bold")).pack(anchor=tk.W, pady=(15, 5))
        self.answer_text = scrolledtext.ScrolledText(
            parent,
            height=6,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.answer_text.pack(fill=tk.BOTH, expand=False)
        self.answer_text.insert("1.0", "请在这里输入你的面试回答……")
        self.answer_text.bind("<FocusIn>", self._clear_answer_placeholder)

        self.review_btn = ttk.Button(parent, text="复盘回答", command=self._on_review)
        self.review_btn.pack(pady=(8, 0))

    def _build_right_panel(self, parent: ttk.Frame):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_resume = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_resume, text="简历诊断")
        self._build_diagnosis_tab(self.tab_resume)

        self.tab_jobs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_jobs, text="岗位匹配")
        self._build_jobs_tab(self.tab_jobs)

        self.tab_interview = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_interview, text="模拟面试")
        self._build_interview_tab(self.tab_interview)

        self.tab_review = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_review, text="回答复盘")
        self._build_review_tab(self.tab_review)

        self.tab_web = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_web, text="招聘网站")
        self._build_web_tab(self.tab_web)

    def _build_diagnosis_tab(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.diagnosis_output = scrolledtext.ScrolledText(
            frame,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.diagnosis_output.pack(fill=tk.BOTH, expand=True)

    def _build_jobs_tab(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sel_frame = ttk.Frame(frame)
        sel_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(sel_frame, text="选择岗位：", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.job_combo = ttk.Combobox(sel_frame, state="readonly", font=("Microsoft YaHei", 10))
        self.job_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.job_combo.bind("<<ComboboxSelected>>", self._on_job_selected)

        self.jobs_output = scrolledtext.ScrolledText(
            frame,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.jobs_output.pack(fill=tk.BOTH, expand=True)

    def _build_interview_tab(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.interview_output = scrolledtext.ScrolledText(
            frame,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.interview_output.pack(fill=tk.BOTH, expand=True)

    def _build_review_tab(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.review_output = scrolledtext.ScrolledText(
            frame,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.review_output.pack(fill=tk.BOTH, expand=True)

    def _build_web_tab(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="输入岗位关键词，点击平台按钮即可跳转到对应招聘网站搜索页。",
            font=("Microsoft YaHei", 10),
            wraplength=400,
        ).pack(anchor=tk.W, pady=(0, 12))

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(search_frame, text="搜索岗位：", font=("Microsoft YaHei", 11, "bold")).pack(side=tk.LEFT)
        self.search_entry = ttk.Entry(search_frame, font=("Microsoft YaHei", 11), width=20)
        self.search_entry.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        quick_frame = ttk.Frame(frame)
        quick_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(quick_frame, text="快捷填入：", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        ttk.Button(quick_frame, text="AI算法实习生", command=lambda: self._fill_search("AI算法实习生")).pack(side=tk.LEFT, padx=4)
        ttk.Button(quick_frame, text="大模型应用开发", command=lambda: self._fill_search("大模型应用开发")).pack(side=tk.LEFT, padx=4)
        ttk.Button(quick_frame, text="数据分析", command=lambda: self._fill_search("数据分析")).pack(side=tk.LEFT, padx=4)
        ttk.Button(quick_frame, text="Python开发", command=lambda: self._fill_search("Python开发")).pack(side=tk.LEFT, padx=4)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(frame, text="选择招聘平台：", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))

        platforms = [
            ("BOSS直聘", "#5cadff", self._open_boss),
            ("拉勾", "#00b33b", self._open_lagou),
            ("智联招聘", "#ff6a00", self._open_zhilian),
            ("猎聘", "#7b2cbf", self._open_liepin),
            ("前程无忧", "#e60012", self._open_51job),
            ("实习僧", "#00a6a0", self._open_shixiseng),
        ]

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        for i, (name, color, cmd) in enumerate(platforms):
            row = i // 2
            col = i % 2
            wrapper = tk.Frame(btn_frame, bg=color, padx=1, pady=1)
            wrapper.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            btn = tk.Button(
                wrapper,
                text=name,
                font=("Microsoft YaHei", 11, "bold"),
                fg="white",
                bg=color,
                activebackground=color,
                activeforeground="white",
                relief=tk.FLAT,
                cursor="hand2",
                padx=20,
                pady=10,
                command=cmd,
            )
            btn.pack(fill=tk.BOTH, expand=True)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

    def _on_import(self):
        file_path = filedialog.askopenfilename(
            title="选择简历文件",
            filetypes=[
                ("所有支持格式", "*.txt *.pdf *.docx"),
                ("文本文件", "*.txt"),
                ("PDF文件", "*.pdf"),
                ("Word文档", "*.docx"),
            ],
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            text = self._read_document(path)
        except Exception as exc:
            messagebox.showerror("导入失败", f"无法读取文件：\n{exc}")
            self.import_status.config(text=f"导入失败：{exc}", foreground="#e74c3c")
            return

        if not text.strip():
            messagebox.showwarning("内容为空", "文件中未提取到文本内容。")
            self.import_status.config(text="文件中未提取到文本内容", foreground="#e67e22")
            return

        self.resume_text.delete("1.0", tk.END)
        self.resume_text.insert("1.0", text)
        self.import_status.config(text=f"已导入：{path.name}", foreground="#27ae60")

    def _read_document(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="replace")
        if suffix == ".pdf":
            return self._read_pdf(path)
        if suffix == ".docx":
            return self._read_docx(path)
        raise ValueError(f"不支持的文件格式：{suffix}")

    def _read_pdf(self, path: Path) -> str:
        errors = []
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
            if text:
                return text
            errors.append("PyPDF2 未提取到文本，可能是扫描版 PDF。")
        except ImportError:
            errors.append("未安装 PyPDF2。")
        except Exception as exc:
            errors.append(f"PyPDF2 解析失败：{exc}")

        try:
            import pdfplumber

            with pdfplumber.open(str(path)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages).strip()
            if text:
                return text
            errors.append("pdfplumber 未提取到文本，可能需要 OCR。")
        except ImportError as exc:
            raise ImportError("解析 PDF 需要安装 PyPDF2 或 pdfplumber。") from exc
        except Exception as exc:
            raise RuntimeError(f"PDF 解析失败：{exc}") from exc

        raise RuntimeError("PDF 未提取到可用文本。 " + " ".join(errors))

    def _read_docx(self, path: Path) -> str:
        try:
            from docx import Document

            doc = Document(str(path))
            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            return "\n".join(paragraphs)
        except ImportError as exc:
            raise ImportError("解析 Word 需要安装 python-docx。") from exc
        except Exception as exc:
            raise RuntimeError(f"Word 解析失败：{exc}") from exc

    def _load_sample(self):
        path = DATA_DIR / "sample_resume.txt"
        if path.exists():
            self.resume_text.delete("1.0", tk.END)
            self.resume_text.insert("1.0", path.read_text(encoding="utf-8"))
        self.answer_text.delete("1.0", tk.END)
        self.answer_text.insert(
            "1.0",
            "我在课程项目中负责实现一个基于 Python 和 PyTorch 的文本分类模型，"
            "主要完成数据清洗、模型训练和结果分析。通过调整学习率和样本均衡策略，"
            "模型准确率从 82% 提升到 89%，并将实验过程整理成报告。",
        )

    def _on_analyze(self):
        text = self.resume_text.get("1.0", tk.END).strip()
        if not text:
            self._set_text(self.diagnosis_output, "请先输入简历内容。")
            return

        self.resume = parse_resume(text)
        matches = match_jobs(self.resume, self.jobs)
        if not matches:
            self._set_text(self.diagnosis_output, "未找到可匹配的岗位。")
            return

        best_match = matches[0]
        self.current_job = next(job for job in self.jobs if job.title == best_match["title"])
        report = score_resume(self.resume, self.current_job)

        diag = (
            f"姓名：{self.resume.name}\n"
            f"专业：{self.resume.major}\n"
            f"识别技能：{', '.join(self.resume.skills) or '未识别到'}\n\n"
            f"综合评分：{report['score']} / 100\n\n"
            "评分构成：\n"
        )
        for item in report["breakdown"]:
            diag += f"  - {item}\n"
        diag += "\n项目经历：\n"
        for item in report["projects"]:
            diag += f"  - {item}\n"
        diag += "\n优化建议：\n"
        for item in report["suggestions"]:
            diag += f"  - {item}\n"
        self._set_text(self.diagnosis_output, diag)

        job_lines = []
        for match in matches:
            job_lines.append(
                f"{match['title']} @ {match['company']}\n"
                f"  匹配度：{match['match_score']}%\n"
                f"  已具备：{', '.join(match['matched_skills']) or '暂无'}\n"
                f"  仍缺少：{', '.join(match['missing_skills']) or '暂无'}\n"
            )
        self._set_text(self.jobs_output, "\n".join(job_lines))
        self.job_lookup = {f"{job.title}::{job.company}": job for job in self.jobs}
        self.combo_job_ids = [match["job_id"] for match in matches]
        self.job_combo["values"] = [f"{match['title']} @ {match['company']}" for match in matches]
        self.job_combo.current(0)

        self._refresh_interview(self.current_job)
        self._fill_search(self.current_job.title)
        self.notebook.select(0)

    def _refresh_interview(self, job: Job):
        questions = generate_interview_questions(job, self.resume or parse_resume(""))
        out = f"目标岗位：{job.title} @ {job.company}\n\n岗位描述：{job.description}\n\n模拟面试题：\n\n"
        for index, question in enumerate(questions, 1):
            out += f"{index}. {question}\n\n"
        self._set_text(self.interview_output, out)

    def _on_job_selected(self, _event=None):
        if self.resume is None:
            return
        index = self.job_combo.current()
        if index < 0 or index >= len(self.combo_job_ids):
            return
        self.current_job = self.job_lookup[self.combo_job_ids[index]]
        self._refresh_interview(self.current_job)
        self._fill_search(self.current_job.title)

    def _on_review(self):
        answer = self.answer_text.get("1.0", tk.END).strip()
        if not answer or answer == "请在这里输入你的面试回答……":
            self._set_text(self.review_output, "请先输入你的面试回答。")
            return
        if self.current_job is None:
            self._set_text(self.review_output, "请先点击“一键分析”加载岗位信息。")
            return

        result = review_answer(answer, self.current_job)
        out = f"回答评分：{result['score']} / 100\n\n反馈意见：\n"
        for item in result["feedback"]:
            out += f"  - {item}\n"
        self._set_text(self.review_output, out)
        self.notebook.select(3)

    def _clear_answer_placeholder(self, _event=None):
        if self.answer_text.get("1.0", tk.END).strip() == "请在这里输入你的面试回答……":
            self.answer_text.delete("1.0", tk.END)

    def _fill_search(self, keyword: str):
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, keyword)

    def _get_search_keyword(self) -> str:
        keyword = self.search_entry.get().strip() or "Python"
        return urllib.parse.quote(keyword)

    def _open_boss(self):
        webbrowser.open(f"https://www.zhipin.com/web/geek/job?query={self._get_search_keyword()}&city=100010000")

    def _open_lagou(self):
        webbrowser.open(f"https://www.lagou.com/wn/jobs?kd={self._get_search_keyword()}")

    def _open_zhilian(self):
        webbrowser.open(f"https://sou.zhaopin.com/?jl=530&kw={self._get_search_keyword()}")

    def _open_liepin(self):
        webbrowser.open(f"https://www.liepin.com/zhaopin/?key={self._get_search_keyword()}")

    def _open_51job(self):
        webbrowser.open(f"https://we.51job.com/pc/search?keyword={self._get_search_keyword()}")

    def _open_shixiseng(self):
        webbrowser.open(f"https://www.shixiseng.com/interns?keyword={self._get_search_keyword()}")

    @staticmethod
    def _set_text(widget: scrolledtext.ScrolledText, content: str):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state=tk.DISABLED)


def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton", font=("Microsoft YaHei", 10), padding=6)
    style.configure("TLabel", font=("Microsoft YaHei", 10), background="#f0f4f8")
    style.configure("TFrame", background="#f0f4f8")
    style.configure("TNotebook", background="#f0f4f8")
    style.configure("TNotebook.Tab", font=("Microsoft YaHei", 10), padding=[15, 6])

    CareerCoachApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
