const state = {
  currentJobId: "",
  jobs: window.__APP_DATA__.jobs || [],
  sampleResume: window.__APP_DATA__.sampleResume || "",
  sampleAnswer: window.__APP_DATA__.sampleAnswer || "",
  aiConfigured: Boolean(window.__APP_DATA__.aiConfigured),
};

const elements = {
  resumeText: document.querySelector("#resume-text"),
  answerText: document.querySelector("#answer-text"),
  resumeFile: document.querySelector("#resume-file"),
  analyzeButton: document.querySelector("#analyze-button"),
  reviewButton: document.querySelector("#review-button"),
  resetButton: document.querySelector("#reset-button"),
  importStatus: document.querySelector("#import-status"),
  diagnosisOutput: document.querySelector("#diagnosis-output"),
  jobsOutput: document.querySelector("#jobs-output"),
  interviewOutput: document.querySelector("#interview-output"),
  reviewOutput: document.querySelector("#review-output"),
  jobSelect: document.querySelector("#job-select"),
  searchKeyword: document.querySelector("#search-keyword"),
  quickTags: document.querySelectorAll(".tag-button"),
  platformLinks: document.querySelectorAll(".platform-link"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setEmptyOutput(node, text) {
  node.classList.add("empty-state");
  node.innerHTML = escapeHtml(text);
}

function renderAiBadge(enabled, error) {
  if (enabled) {
    return '<p class="ai-badge success">AI 增强已启用</p>';
  }
  if (error) {
    return `<p class="ai-badge warning">AI 回退到规则模式：${escapeHtml(error)}</p>`;
  }
  return '<p class="ai-badge muted">当前使用规则模式</p>';
}

function fillJobSelect(matches, currentJobId) {
  elements.jobSelect.innerHTML = "";
  matches.forEach((job) => {
    const option = document.createElement("option");
    option.value = job.job_id;
    option.textContent = `${job.title} @ ${job.company}`;
    if (job.job_id === currentJobId) {
      option.selected = true;
    }
    elements.jobSelect.appendChild(option);
  });
}

function renderDiagnosis(data) {
  const diagnosis = data.diagnosis;
  const resume = data.resume;
  const skills = diagnosis.skills.length ? diagnosis.skills.join("、") : "未识别到";
  const projects = diagnosis.projects.length
    ? `<ul>${diagnosis.projects.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "<p>未识别到项目经历。</p>";
  const breakdown = `<ul>${diagnosis.breakdown.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  const suggestions = `<ul>${diagnosis.suggestions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;

  let aiBlock = "";
  if (data.ai_diagnosis) {
    const highlights = (data.ai_diagnosis.highlights || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const risks = (data.ai_diagnosis.risks || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const rewriteSuggestions = (data.ai_diagnosis.rewrite_suggestions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    aiBlock = `
      <p><strong>AI 总结：</strong>${escapeHtml(data.ai_diagnosis.summary || "无")}</p>
      <p><strong>AI 亮点：</strong></p>
      <ul>${highlights}</ul>
      <p><strong>AI 风险：</strong></p>
      <ul>${risks}</ul>
      <p><strong>AI 改写建议：</strong></p>
      <ul>${rewriteSuggestions}</ul>
    `;
  }

  elements.diagnosisOutput.classList.remove("empty-state");
  elements.diagnosisOutput.innerHTML = `
    ${renderAiBadge(data.ai_enabled, data.ai_error)}
    <h3>${escapeHtml(resume.name)} / ${escapeHtml(resume.major)}</h3>
    <p><strong>识别技能：</strong>${escapeHtml(skills)}</p>
    <p><strong>综合评分：</strong>${diagnosis.score} / 100</p>
    <p><strong>评分构成：</strong></p>
    ${breakdown}
    <p><strong>项目经历：</strong></p>
    ${projects}
    <p><strong>规则建议：</strong></p>
    ${suggestions}
    ${aiBlock}
  `;
}

function renderJobs(data) {
  const html = data.jobs.map((job, index) => {
    const badge = index === 0 ? "Top 1" : `Top ${index + 1}`;
    const matched = job.matched_skills.length ? job.matched_skills.join("、") : "暂无";
    const missing = job.missing_skills.length ? job.missing_skills.join("、") : "暂无";
    return `
      <div class="job-item">
        <p><strong>${badge} · ${escapeHtml(job.title)} @ ${escapeHtml(job.company)}</strong></p>
        <p>匹配度：${job.match_score}%</p>
        <p>已具备：${escapeHtml(matched)}</p>
        <p>仍缺少：${escapeHtml(missing)}</p>
      </div>
    `;
  }).join("");

  elements.jobsOutput.classList.remove("empty-state");
  elements.jobsOutput.innerHTML = html;
}

function renderInterview(data) {
  const job = data.current_job;
  const questions = data.interview_questions.map((question) => `<li>${escapeHtml(question)}</li>`).join("");
  elements.interviewOutput.classList.remove("empty-state");
  elements.interviewOutput.innerHTML = `
    ${renderAiBadge(data.ai_enabled, data.ai_error)}
    <h3>${escapeHtml(job.title)} @ ${escapeHtml(job.company)}</h3>
    <p><strong>岗位描述：</strong>${escapeHtml(job.description)}</p>
    <ol>${questions}</ol>
  `;
}

function renderReview(result) {
  const feedback = result.feedback.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const improved = result.improved_answer
    ? `<p><strong>示范回答：</strong></p><div class="answer-demo">${escapeHtml(result.improved_answer)}</div>`
    : "";
  const summary = result.summary ? `<p><strong>总结：</strong>${escapeHtml(result.summary)}</p>` : "";

  elements.reviewOutput.classList.remove("empty-state");
  elements.reviewOutput.innerHTML = `
    ${renderAiBadge(result.ai_enabled, result.ai_error)}
    <h3>回答评分：${result.score} / 100</h3>
    ${summary}
    <ul>${feedback}</ul>
    ${improved}
  `;
}

function updateSearchKeyword(keyword) {
  elements.searchKeyword.value = keyword || "";
  elements.platformLinks.forEach((link) => {
    const base = link.dataset.base;
    const query = encodeURIComponent(keyword || "Python");
    link.href = `${base}${query}`;
  });
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

async function analyze(jobId = "") {
  const resumeText = elements.resumeText.value.trim();
  if (!resumeText) {
    setEmptyOutput(elements.diagnosisOutput, "请先输入简历内容。");
    return;
  }

  elements.analyzeButton.disabled = true;
  elements.analyzeButton.textContent = "分析中...";

  try {
    const data = await postJson("/api/analyze", {
      resume_text: resumeText,
      job_id: jobId || state.currentJobId,
    });
    state.currentJobId = data.current_job_id;
    renderDiagnosis(data);
    renderJobs(data);
    renderInterview(data);
    fillJobSelect(data.jobs, data.current_job_id);
    updateSearchKeyword(data.current_job.title);
    setEmptyOutput(elements.reviewOutput, "已生成岗位与面试题，输入回答后可继续复盘。");
  } catch (error) {
    setEmptyOutput(elements.diagnosisOutput, error.message);
  } finally {
    elements.analyzeButton.disabled = false;
    elements.analyzeButton.textContent = "一键分析";
  }
}

async function review() {
  const answer = elements.answerText.value.trim();
  if (!answer) {
    setEmptyOutput(elements.reviewOutput, "请先输入面试回答。");
    return;
  }
  if (!state.currentJobId) {
    setEmptyOutput(elements.reviewOutput, "请先完成简历分析。");
    return;
  }

  elements.reviewButton.disabled = true;
  elements.reviewButton.textContent = "复盘中...";

  try {
    const result = await postJson("/api/review", {
      answer,
      job_id: state.currentJobId,
    });
    renderReview(result);
  } catch (error) {
    setEmptyOutput(elements.reviewOutput, error.message);
  } finally {
    elements.reviewButton.disabled = false;
    elements.reviewButton.textContent = "复盘回答";
  }
}

async function importFile(file) {
  const formData = new FormData();
  formData.append("resume_file", file);
  elements.importStatus.textContent = "正在导入文件...";

  try {
    const response = await fetch("/api/import", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "导入失败");
    }
    elements.resumeText.value = data.text;
    elements.importStatus.textContent = `已导入：${file.name}`;
  } catch (error) {
    elements.importStatus.textContent = `导入失败：${error.message}`;
  }
}

elements.analyzeButton.addEventListener("click", () => analyze());
elements.reviewButton.addEventListener("click", review);
elements.resetButton.addEventListener("click", () => {
  elements.resumeText.value = state.sampleResume;
  elements.answerText.value = state.sampleAnswer;
  elements.importStatus.textContent = "已恢复示例内容。";
  state.currentJobId = "";
  elements.jobSelect.innerHTML = '<option value="">分析后选择岗位</option>';
  setEmptyOutput(elements.diagnosisOutput, "分析结果会显示在这里。");
  setEmptyOutput(elements.jobsOutput, "岗位匹配结果会显示在这里。");
  setEmptyOutput(elements.interviewOutput, "面试题会显示在这里。");
  setEmptyOutput(elements.reviewOutput, "复盘结果会显示在这里。");
  updateSearchKeyword("");
});

elements.resumeFile.addEventListener("change", (event) => {
  const [file] = event.target.files || [];
  if (file) {
    importFile(file);
  }
});

elements.jobSelect.addEventListener("change", (event) => {
  state.currentJobId = event.target.value;
  if (state.currentJobId) {
    analyze(state.currentJobId);
  }
});

elements.quickTags.forEach((button) => {
  button.addEventListener("click", () => updateSearchKeyword(button.dataset.keyword));
});

elements.searchKeyword.addEventListener("input", (event) => {
  updateSearchKeyword(event.target.value.trim());
});

setEmptyOutput(elements.diagnosisOutput, "分析结果会显示在这里。");
setEmptyOutput(elements.jobsOutput, "岗位匹配结果会显示在这里。");
setEmptyOutput(elements.interviewOutput, "面试题会显示在这里。");
setEmptyOutput(elements.reviewOutput, "复盘结果会显示在这里。");
updateSearchKeyword("");
