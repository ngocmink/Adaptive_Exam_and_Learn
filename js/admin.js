(() => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const config = window.adminConfig || { userId: null, userRole: "teacher", userName: "" };
  const toastStack = document.querySelector("#toast-stack");

  const state = {
    activeTab: "dashboard",
    subjectsSubtab: "subjects",
    subjectsCache: [],
    lessonsCache: [],
    pages: {
      subjects: 1,
      lessons: 1,
      materials: 1,
      questions: 1,
      assessments: 1,
      attempts: 1,
      users: 1,
    },
    charts: {
      line: null,
      donut: null,
    },
    assessmentPicker: {
      available: [],
      selected: [], // [{ question_id, content, topic, difficulty, points }]
    },
    latestOverview: null,
  };

  // ---------------- HELPERS ----------------

  function toast(message, type = "info") {
    if (!toastStack) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    const text = document.createElement("span");
    text.textContent = message;
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.textContent = "×";
    closeBtn.style.cssText = "border:0;background:transparent;font-size:1.1rem;cursor:pointer;color:inherit;";
    closeBtn.addEventListener("click", () => el.remove());
    el.append(text, closeBtn);
    toastStack.append(el);
    setTimeout(() => {
      if (el.isConnected) el.remove();
    }, 4200);
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        "X-CSRF-Token": csrfToken,
        ...options.headers,
      },
    });
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error("Máy chủ trả về phản hồi không hợp lệ.");
    }
    if (!response.ok || !body?.success) {
      throw new Error(body?.message || "Yêu cầu thất bại.");
    }
    return body;
  }

  function typesetMath(rootEl) {
    if (window.MathJax && typeof window.MathJax.typesetPromise === "function" && rootEl) {
      window.MathJax.typesetPromise([rootEl]).catch(() => {});
    }
  }

  function debounce(fn, delay = 320) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  function el(tag, className, textContent) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (textContent !== undefined && textContent !== null) {
      node.textContent = String(textContent);
    }
    return node;
  }

  function badge(text, variant = "secondary") {
    return el("span", `badge badge-${variant}`, text);
  }

  function actionBtn(label, variantClass, onClick) {
    const btn = el("button", `btn btn-sm ${variantClass}`, label);
    btn.type = "button";
    btn.addEventListener("click", onClick);
    return btn;
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return "—";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}p ${String(secs).padStart(2, "0")}s`;
  }

  function truncate(str, maxLen = 110) {
    if (!str) return "";
    return str.length > maxLen ? str.slice(0, maxLen) + "…" : str;
  }

  function renderTable(wrapSelector, columns, rows, emptyText = "Chưa có dữ liệu.") {
    const wrap = document.querySelector(wrapSelector);
    if (!wrap) return;
    wrap.replaceChildren();
    if (!rows.length) {
      wrap.append(el("p", "text-muted", emptyText));
      return;
    }
    const table = el("table", "admin-table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columns.forEach((col) => {
      headRow.append(el("th", "", col.label));
    });
    thead.append(headRow);
    table.append(thead);

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      columns.forEach((col) => {
        const td = document.createElement("td");
        const rendered = col.render(row);
        if (rendered instanceof Node) {
          td.append(rendered);
        } else {
          td.textContent = rendered !== undefined && rendered !== null ? String(rendered) : "";
        }
        tr.append(td);
      });
      tbody.append(tr);
    });
    table.append(tbody);
    wrap.append(table);
    typesetMath(wrap);
  }

  function renderPagination(barSelector, pagination, onPageChange) {
    const bar = document.querySelector(barSelector);
    if (!bar) return;
    bar.replaceChildren();
    if (!pagination) return;

    const totalPages = Number(pagination.total_pages) || 1;
    const current = Number(pagination.page) || 1;
    const totalRecords = Number(pagination.total_records) || 0;

    bar.append(el("span", "", `Trang ${current} / ${Math.max(1, totalPages)} · Tổng ${totalRecords} bản ghi`));
    if (totalPages <= 1) return;

    const btnGroup = el("div", "pagination-buttons");
    const makeBtn = (label, page, disabled = false, active = false) => {
      const b = el("button", "page-btn" + (active ? " active" : ""), label);
      b.type = "button";
      b.disabled = disabled;
      if (!disabled && !active) {
        b.addEventListener("click", () => onPageChange(page));
      }
      return b;
    };

    btnGroup.append(makeBtn("«", current - 1, current <= 1));
    const start = Math.max(1, current - 2);
    const end = Math.min(totalPages, start + 4);
    for (let p = start; p <= end; p++) {
      btnGroup.append(makeBtn(String(p), p, false, p === current));
    }
    btnGroup.append(makeBtn("»", current + 1, current >= totalPages));
    bar.append(btnGroup);
  }

  // ---------------- MODALS ----------------

  function openModal(id) {
    const modal = document.querySelector(id);
    if (modal) {
      modal.classList.add("open");
      typesetMath(modal);
    }
  }

  function closeModal(modalEl) {
    modalEl?.classList.remove("open");
  }

  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(btn.closest(".modal-backdrop")));
  });
  document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeModal(backdrop);
    });
  });

  // ---------------- NAVIGATION & SIDEBAR ----------------

  function switchTab(tabName) {
    const valid = ["dashboard", "subjects", "materials", "questions", "assessments", "attempts", "users"];
    if (!valid.includes(tabName)) tabName = "dashboard";
    state.activeTab = tabName;

    document.querySelectorAll(".sidebar-link[data-tab]").forEach((link) => {
      link.classList.toggle("active", link.dataset.tab === tabName);
    });
    document.querySelectorAll(".view-section").forEach((sec) => {
      sec.classList.toggle("active", sec.id === `view-${tabName}`);
    });
    document.body.classList.remove("mobile-sidebar-open");

    if (window.location.hash !== `#${tabName}`) {
      history.replaceState(null, "", `#${tabName}`);
    }

    if (tabName === "dashboard") loadOverview();
    if (tabName === "subjects") {
      loadSubjectsTable();
      loadLessonsTable();
    }
    if (tabName === "materials") loadMaterials();
    if (tabName === "questions") loadQuestions();
    if (tabName === "assessments") loadAssessments();
    if (tabName === "attempts") loadAttempts();
    if (tabName === "users") loadUsers();
  }

  document.querySelectorAll(".sidebar-link[data-tab], [data-nav]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      switchTab(btn.dataset.tab || btn.dataset.nav);
    });
  });

  document.querySelectorAll("[data-jump]").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.jump));
  });

  document.querySelector("#sidebar-collapse-btn")?.addEventListener("click", () => {
    document.body.classList.toggle("sidebar-collapsed");
  });
  document.querySelector("#mobile-menu-btn")?.addEventListener("click", () => {
    document.body.classList.toggle("mobile-sidebar-open");
  });
  document.querySelector("#mobile-backdrop")?.addEventListener("click", () => {
    document.body.classList.remove("mobile-sidebar-open");
  });

  // Topbar quick search delegates into active tab search box
  document.querySelector("#topbar-search-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = document.querySelector("#topbar-search-input")?.value.trim() || "";
    const targetMap = {
      subjects: state.subjectsSubtab === "lessons" ? "#filter-lessons-search" : "#filter-subjects-search",
      materials: "#filter-materials-search",
      questions: "#filter-questions-search",
      assessments: "#filter-assessments-search",
      attempts: "#filter-attempts-search",
      users: "#filter-users-search",
    };
    let targetTab = state.activeTab;
    if (targetTab === "dashboard") {
      targetTab = "questions";
      switchTab("questions");
    }
    const input = document.querySelector(targetMap[targetTab]);
    if (input) {
      input.value = q;
      input.dispatchEvent(new Event("input"));
    }
  });

  // ---------------- SHARED SUBJECT & LESSON CACHES ----------------

  async function refreshSubjectsAndLessonsCache() {
    try {
      const [subjRes, lessonRes] = await Promise.all([
        requestJson("/api/admin/subjects?limit=100&include_inactive=true"),
        requestJson("/api/admin/lessons?limit=100"),
      ]);
      state.subjectsCache = subjRes.data || [];
      state.lessonsCache = lessonRes.data || [];
      populateSubjectDropdowns();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function populateSubjectDropdowns() {
    const filterSelectors = [
      "#filter-lessons-subject",
      "#filter-materials-subject",
      "#filter-questions-subject",
      "#filter-assessments-subject",
      "#filter-attempts-subject",
      "#picker-subject-filter",
    ];
    filterSelectors.forEach((sel) => {
      const select = document.querySelector(sel);
      if (!select) return;
      const prev = select.value;
      const firstLabel = sel === "#picker-subject-filter" ? "Tất cả môn" : "Tất cả môn học";
      select.replaceChildren(new Option(firstLabel, ""));
      state.subjectsCache.forEach((s) => {
        select.append(new Option(`${s.code} — ${s.name}`, String(s.id)));
      });
      if (prev) select.value = prev;
    });

    const formSelectors = ["#lesson-subject", "#mat-subject", "#q-subject", "#assess-subject"];
    formSelectors.forEach((sel) => {
      const select = document.querySelector(sel);
      if (!select) return;
      const prev = select.value;
      select.replaceChildren();
      state.subjectsCache.forEach((s) => {
        select.append(new Option(`${s.code} — ${s.name}`, String(s.id)));
      });
      if (prev && [...select.options].some((o) => o.value === prev)) {
        select.value = prev;
      }
    });
  }

  function renderLessonChecklist(containerSelector, subjectId, selectedIds = []) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    container.replaceChildren();
    const sid = Number(subjectId);
    const matching = state.lessonsCache.filter((l) => l.subject_id === sid);
    if (!matching.length) {
      container.append(el("span", "text-muted", "Môn học này chưa có bài học nào."));
      return;
    }
    const selectedSet = new Set((selectedIds || []).map(Number));
    matching.forEach((l) => {
      const label = el("label", "lesson-check-item");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = String(l.id);
      cb.checked = selectedSet.has(l.id);
      label.append(cb, el("span", "", `${l.code}: ${l.title}`));
      container.append(label);
    });
  }

  function getCheckedIds(containerSelector) {
    return [...document.querySelectorAll(`${containerSelector} input[type="checkbox"]:checked`)].map((cb) =>
      Number(cb.value)
    );
  }

  // ---------------- VIEW 1: DASHBOARD OVERVIEW & CHARTS ----------------

  async function loadOverview() {
    try {
      const res = await requestJson("/api/admin/overview");
      const data = res.data;
      state.latestOverview = data;
      const k = data.kpis;

      document.querySelector("#kpi-materials").textContent = `${k.materials_active} / ${k.materials_total}`;
      document.querySelector("#kpi-materials-sub").textContent = `${k.lessons_published} bài học xuất bản · ${k.subjects_active} môn`;

      document.querySelector("#kpi-questions").textContent = `${k.questions_active} / ${k.questions_total}`;
      document.querySelector("#kpi-questions-sub").textContent = `${k.assessments_active} đề đang mở · ${k.students_total} học viên`;

      document.querySelector("#kpi-pass-rate").textContent = `${k.pass_rate}%`;
      document.querySelector("#kpi-pass-bar").style.width = `${Math.min(100, Math.max(0, k.pass_rate))}%`;
      document.querySelector("#kpi-pass-sub").textContent = `Điểm trung bình: ${k.average_score}/100 (${k.completed_attempts} bài nộp)`;

      document.querySelector("#kpi-attempts").textContent = String(k.attempts_total);
      document.querySelector("#kpi-attempts-sub").textContent = `${k.completed_attempts} đã nộp · ${k.in_progress_attempts} đang làm`;

      renderOverviewCharts(data);

      renderTable(
        "#overview-subject-breakdown",
        [
          { label: "Môn học", render: (r) => `${r.code} — ${r.name}` },
          { label: "Bài", render: (r) => r.lessons },
          { label: "Tài liệu", render: (r) => r.materials },
          { label: "Câu hỏi", render: (r) => r.questions },
          { label: "Đề thi", render: (r) => r.assessments },
        ],
        data.subject_breakdown || [],
        "Chưa có môn học đang hoạt động."
      );

      renderTable(
        "#overview-recent-attempts",
        [
          {
            label: "Học viên",
            render: (r) => {
              const box = el("div");
              box.append(el("div", "", r.user_name));
              box.append(el("small", "text-muted", r.assessment_title));
              return box;
            },
          },
          {
            label: "Điểm",
            render: (r) => {
              if (r.status !== "completed") return badge("Đang làm", "info");
              return badge(`${r.score}%`, r.is_passed ? "success" : "danger");
            },
          },
          {
            label: "Chi tiết",
            render: (r) => {
              const a = el("a", "btn btn-sm btn-outline-primary", "Xem");
              a.href = `/quiz/results?attempt_id=${r.id}`;
              return a;
            },
          },
        ],
        data.recent_attempts || [],
        "Chưa có lượt làm bài nào."
      );
    } catch (err) {
      toast("Không tải được thống kê tổng quan: " + err.message, "error");
    }
  }

  function renderOverviewCharts(data) {
    if (typeof window.Chart === "undefined") return;

    const lineCanvas = document.querySelector("#chart-attempts-line");
    if (lineCanvas) {
      if (state.charts.line) state.charts.line.destroy();
      const days = data.attempts_by_day || [];
      state.charts.line = new window.Chart(lineCanvas, {
        type: "line",
        data: {
          labels: days.map((d) => d.label),
          datasets: [
            {
              label: "Số lượt làm bài",
              data: days.map((d) => d.count),
              borderColor: "#4e73df",
              backgroundColor: "rgba(78, 115, 223, 0.12)",
              fill: true,
              tension: 0.35,
              pointRadius: 4,
              pointBackgroundColor: "#4e73df",
              pointBorderColor: "#fff",
              pointBorderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, ticks: { precision: 0 } },
          },
        },
      });
    }

    const donutCanvas = document.querySelector("#chart-results-donut");
    if (donutCanvas) {
      if (state.charts.donut) state.charts.donut.destroy();
      const dist = data.result_distribution || { passed: 0, failed: 0, in_progress: 0 };
      const hasData = dist.passed + dist.failed + dist.in_progress > 0;
      state.charts.donut = new window.Chart(donutCanvas, {
        type: "doughnut",
        data: {
          labels: hasData ? ["Đạt yêu cầu", "Chưa đạt", "Đang làm"] : ["Chưa có dữ liệu"],
          datasets: [
            {
              data: hasData ? [dist.passed, dist.failed, dist.in_progress] : [1],
              backgroundColor: hasData ? ["#1cc88a", "#e74a3b", "#36b9cc"] : ["#e3e6f0"],
              hoverBorderColor: "#fff",
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "68%",
          plugins: {
            legend: { position: "bottom" },
          },
        },
      });
    }
  }

  function downloadCsv(filename, headers, rows) {
    const escapeCell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [headers.map(escapeCell).join(","), ...rows.map((r) => r.map(escapeCell).join(","))].join("\r\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  document.querySelector("#btn-refresh-overview")?.addEventListener("click", loadOverview);
  document.querySelector("#btn-export-report")?.addEventListener("click", async () => {
    try {
      const res = await requestJson("/api/admin/attempts?limit=100");
      const rows = (res.data || []).map((a) => [
        a.id,
        a.user_name,
        a.user_email,
        a.subject_name,
        a.assessment_title,
        a.score ?? "",
        a.correct_answers,
        a.total_questions,
        a.status,
        formatDateTime(a.start_time),
        formatDateTime(a.submit_time),
      ]);
      downloadCsv(
        `vise-bao-cao-ket-qua-${new Date().toISOString().slice(0, 10)}.csv`,
        ["ID", "Học viên", "Email", "Môn học", "Đề thi", "Điểm (%)", "Số câu đúng", "Tổng câu", "Trạng thái", "Bắt đầu", "Nộp bài"],
        rows
      );
      toast("Đã xuất báo cáo CSV.", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });
  document.querySelector("#btn-export-attempts")?.addEventListener("click", () => {
    document.querySelector("#btn-export-report")?.click();
  });

  // ---------------- VIEW 2: SUBJECTS & LESSONS ----------------

  document.querySelectorAll("[data-subtab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      state.subjectsSubtab = tab.dataset.subtab;
      document.querySelectorAll("[data-subtab]").forEach((t) => t.classList.toggle("active", t === tab));
      document.querySelector("#subpanel-subjects").classList.toggle("hidden", state.subjectsSubtab !== "subjects");
      document.querySelector("#subpanel-lessons").classList.toggle("hidden", state.subjectsSubtab !== "lessons");
      document.querySelector("#btn-add-subject").classList.toggle("hidden", state.subjectsSubtab !== "subjects");
      document.querySelector("#btn-add-lesson").classList.toggle("hidden", state.subjectsSubtab !== "lessons");
    });
  });

  async function loadSubjectsTable(page = state.pages.subjects) {
    state.pages.subjects = page;
    const params = new URLSearchParams({
      page: String(page),
      limit: "15",
      include_inactive: String(document.querySelector("#filter-subjects-inactive")?.checked ?? true),
    });
    const search = document.querySelector("#filter-subjects-search")?.value.trim();
    if (search) params.set("search", search);

    try {
      const res = await requestJson(`/api/admin/subjects?${params}`);
      renderTable(
        "#subjects-table-wrap",
        [
          { label: "ID", render: (s) => s.id },
          { label: "Mã môn", render: (s) => el("strong", "", s.code) },
          { label: "Tên môn học", render: (s) => s.name },
          { label: "Bài học", render: (s) => s.lesson_count },
          { label: "Tài liệu", render: (s) => s.material_count },
          { label: "Câu hỏi", render: (s) => s.question_count },
          { label: "Đề thi", render: (s) => s.assessment_count },
          { label: "Trạng thái", render: (s) => (s.is_active ? badge("Đang hiện", "success") : badge("Đã ẩn", "secondary")) },
          {
            label: "Thao tác",
            render: (s) => {
              const box = el("div", "table-actions");
              box.append(
                actionBtn("Sửa", "btn-outline-primary", () => openSubjectModal(s)),
                actionBtn(s.is_active ? "Ẩn" : "Hiện", s.is_active ? "btn-outline" : "btn-success", async () => {
                  try {
                    await requestJson(`/api/admin/subjects/${s.id}/toggle-status`, { method: "PATCH" });
                    toast("Đã cập nhật trạng thái môn học.", "success");
                    await refreshSubjectsAndLessonsCache();
                    loadSubjectsTable();
                  } catch (err) {
                    toast(err.message, "error");
                  }
                })
              );
              return box;
            },
          },
        ],
        res.data || []
      );
      renderPagination("#subjects-pagination", res.pagination, loadSubjectsTable);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function openSubjectModal(subj = null) {
    const form = document.querySelector("#form-subject");
    form.reset();
    form.elements.id.value = subj ? subj.id : "";
    form.elements.code.value = subj ? subj.code : "";
    form.elements.name.value = subj ? subj.name : "";
    form.elements.description.value = subj?.description || "";
    form.elements.is_active.checked = subj ? Boolean(subj.is_active) : true;
    document.querySelector("#modal-subject-title").textContent = subj ? `Sửa môn học #${subj.id}` : "Thêm môn học mới";
    openModal("#modal-subject");
  }

  document.querySelector("#btn-add-subject")?.addEventListener("click", () => openSubjectModal());
  document.querySelector("#form-subject")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const id = f.elements.id.value;
    const payload = {
      code: f.elements.code.value.trim(),
      name: f.elements.name.value.trim(),
      description: f.elements.description.value.trim() || null,
      is_active: f.elements.is_active.checked,
    };
    try {
      await requestJson(id ? `/api/admin/subjects/${id}` : "/api/admin/subjects", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      closeModal(f.closest(".modal-backdrop"));
      toast(id ? "Đã cập nhật môn học." : "Đã tạo môn học mới.", "success");
      await refreshSubjectsAndLessonsCache();
      loadSubjectsTable();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  async function loadLessonsTable(page = state.pages.lessons) {
    state.pages.lessons = page;
    const params = new URLSearchParams({ page: String(page), limit: "15" });
    const search = document.querySelector("#filter-lessons-search")?.value.trim();
    const sid = document.querySelector("#filter-lessons-subject")?.value;
    const status = document.querySelector("#filter-lessons-status")?.value;
    if (search) params.set("search", search);
    if (sid) params.set("subject_id", sid);
    if (status) params.set("status", status);

    const statusBadge = {
      published: ["Đã xuất bản", "success"],
      draft: ["Bản nháp", "warning"],
      archived: ["Lưu trữ", "secondary"],
    };

    try {
      const res = await requestJson(`/api/admin/lessons?${params}`);
      renderTable(
        "#lessons-table-wrap",
        [
          { label: "STT", render: (l) => l.order_num },
          { label: "Mã bài", render: (l) => el("strong", "", l.code) },
          { label: "Tiêu đề bài học", render: (l) => l.title },
          { label: "Môn học", render: (l) => l.subject_name || l.subject_id },
          { label: "Tài liệu", render: (l) => l.material_count },
          { label: "Câu hỏi", render: (l) => l.question_count },
          {
            label: "Trạng thái",
            render: (l) => {
              const [lbl, v] = statusBadge[l.status] || [l.status, "secondary"];
              return badge(lbl, v);
            },
          },
          {
            label: "Thao tác",
            render: (l) => {
              const box = el("div", "table-actions");
              box.append(
                actionBtn("Sửa", "btn-outline-primary", () => openLessonModal(l)),
                actionBtn("Xóa / Lưu trữ", "btn-danger", async () => {
                  if (!window.confirm(`Xóa hoặc lưu trữ bài học "${l.code}: ${l.title}"?`)) return;
                  try {
                    const out = await requestJson(`/api/admin/lessons/${l.id}`, { method: "DELETE" });
                    toast(out.message, "success");
                    await refreshSubjectsAndLessonsCache();
                    loadLessonsTable();
                  } catch (err) {
                    toast(err.message, "error");
                  }
                })
              );
              return box;
            },
          },
        ],
        res.data || []
      );
      renderPagination("#lessons-pagination", res.pagination, loadLessonsTable);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function openLessonModal(lesson = null) {
    const f = document.querySelector("#form-lesson");
    f.reset();
    f.elements.id.value = lesson ? lesson.id : "";
    if (lesson) f.elements.subject_id.value = String(lesson.subject_id);
    f.elements.order_num.value = lesson ? lesson.order_num : 1;
    f.elements.code.value = lesson ? lesson.code : "";
    f.elements.title.value = lesson ? lesson.title : "";
    f.elements.status.value = lesson ? lesson.status : "published";
    f.elements.objectives.value = lesson?.objectives || "";
    f.elements.content.value = lesson?.content || "";
    document.querySelector("#modal-lesson-title").textContent = lesson ? `Sửa bài học #${lesson.id}` : "Thêm bài học mới";
    openModal("#modal-lesson");
  }

  document.querySelector("#btn-add-lesson")?.addEventListener("click", () => openLessonModal());
  document.querySelector("#form-lesson")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const id = f.elements.id.value;
    const payload = {
      subject_id: Number(f.elements.subject_id.value),
      order_num: Number(f.elements.order_num.value),
      code: f.elements.code.value.trim(),
      title: f.elements.title.value.trim(),
      status: f.elements.status.value,
      objectives: f.elements.objectives.value.trim() || null,
      content: f.elements.content.value.trim() || null,
    };
    try {
      await requestJson(id ? `/api/admin/lessons/${id}` : "/api/admin/lessons", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      closeModal(f.closest(".modal-backdrop"));
      toast(id ? "Đã cập nhật bài học." : "Đã tạo bài học mới.", "success");
      await refreshSubjectsAndLessonsCache();
      loadLessonsTable();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // ---------------- VIEW 3: MATERIALS ----------------

  let materialSourceMode = "storage";
  function setMaterialSourceMode(mode) {
    materialSourceMode = mode === "url" ? "url" : "storage";
    document.querySelectorAll("[data-mat-source]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.matSource === materialSourceMode);
    });
    document.querySelector("#mat-source-storage").classList.toggle("hidden", materialSourceMode !== "storage");
    document.querySelector("#mat-source-url").classList.toggle("hidden", materialSourceMode !== "url");
  }
  document.querySelectorAll("[data-mat-source]").forEach((btn) => {
    btn.addEventListener("click", () => setMaterialSourceMode(btn.dataset.matSource));
  });

  async function loadMaterials(page = state.pages.materials) {
    state.pages.materials = page;
    const params = new URLSearchParams({
      page: String(page),
      limit: "10",
      include_inactive: String(document.querySelector("#filter-materials-inactive")?.checked ?? true),
    });
    const search = document.querySelector("#filter-materials-search")?.value.trim();
    const sid = document.querySelector("#filter-materials-subject")?.value;
    if (search) params.set("search", search);
    if (sid) params.set("subject_id", sid);

    try {
      const res = await requestJson(`/api/admin/materials?${params}`);
      renderTable(
        "#materials-table-wrap",
        [
          { label: "ID", render: (m) => m.id },
          {
            label: "Tài liệu",
            render: (m) => {
              const box = el("div");
              box.append(el("strong", "", m.title));
              if (m.description) box.append(el("div", "text-muted", truncate(m.description, 80)));
              return box;
            },
          },
          { label: "Môn học", render: (m) => m.subject_name },
          {
            label: "Bài học",
            render: (m) => {
              const wrap = el("div", "chip-list");
              if (!m.lesson_codes || !m.lesson_codes.length) return el("span", "text-muted", "Chưa gán");
              m.lesson_codes.forEach((code) => wrap.append(badge(code, "primary")));
              return wrap;
            },
          },
          {
            label: "Nguồn PDF",
            render: (m) => (m.storage_path ? badge("Supabase", "info") : badge("URL", "secondary")),
          },
          { label: "Độ khó", render: (m) => `${m.difficulty}/10` },
          { label: "Trạng thái", render: (m) => (m.is_active ? badge("Đang hiện", "success") : badge("Đã ẩn", "secondary")) },
          {
            label: "Thao tác",
            render: (m) => {
              const box = el("div", "table-actions");
              if (m.is_active) {
                const viewLink = el("a", "btn btn-sm btn-outline", "Xem PDF");
                viewLink.href = `/reading?id=${m.id}`;
                viewLink.target = "_blank";
                box.append(viewLink);
              }
              box.append(
                actionBtn("Sửa", "btn-outline-primary", () => openMaterialModal(m)),
                actionBtn(m.is_active ? "Ẩn" : "Hiện", m.is_active ? "btn-outline" : "btn-success", async () => {
                  try {
                    await requestJson(`/api/admin/materials/${m.id}/toggle-status`, { method: "PATCH" });
                    toast("Đã cập nhật trạng thái tài liệu.", "success");
                    loadMaterials();
                  } catch (err) {
                    toast(err.message, "error");
                  }
                })
              );
              return box;
            },
          },
        ],
        res.data || []
      );
      renderPagination("#materials-pagination", res.pagination, loadMaterials);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function openMaterialModal(mat = null) {
    const f = document.querySelector("#form-material");
    f.reset();
    f.elements.id.value = mat ? mat.id : "";
    if (mat) f.elements.subject_id.value = String(mat.subject_id);
    f.elements.title.value = mat ? mat.title : "";
    f.elements.description.value = mat?.description || "";
    f.elements.difficulty.value = mat ? mat.difficulty : 5.5;
    f.elements.is_active.checked = mat ? Boolean(mat.is_active) : true;
    f.elements.storage_path.value = mat?.storage_path || "";
    f.elements.file_url.value = mat?.file_url || "";
    setMaterialSourceMode(mat && !mat.storage_path && mat.file_url ? "url" : "storage");
    renderLessonChecklist("#mat-lessons-checklist", f.elements.subject_id.value, mat?.lesson_ids || []);
    document.querySelector("#modal-material-title").textContent = mat ? `Sửa tài liệu #${mat.id}` : "Thêm tài liệu mới";
    openModal("#modal-material");
  }

  document.querySelector("#mat-subject")?.addEventListener("change", (e) => {
    renderLessonChecklist("#mat-lessons-checklist", e.currentTarget.value, []);
  });
  document.querySelector("#btn-add-material")?.addEventListener("click", () => openMaterialModal());
  document.querySelector("#form-material")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const id = f.elements.id.value;
    const payload = {
      subject_id: Number(f.elements.subject_id.value),
      title: f.elements.title.value.trim(),
      description: f.elements.description.value.trim() || null,
      difficulty: Number(f.elements.difficulty.value),
      is_active: f.elements.is_active.checked,
      lesson_ids: getCheckedIds("#mat-lessons-checklist"),
    };
    if (materialSourceMode === "storage") {
      payload.storage_path = f.elements.storage_path.value.trim();
      payload.file_url = "";
    } else {
      payload.file_url = f.elements.file_url.value.trim();
      payload.storage_path = "";
    }
    try {
      await requestJson(id ? `/api/admin/materials/${id}` : "/api/admin/materials", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      closeModal(f.closest(".modal-backdrop"));
      toast(id ? "Đã cập nhật tài liệu." : "Đã tạo tài liệu mới.", "success");
      loadMaterials();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // ---------------- VIEW 4: QUESTIONS ----------------

  const qContentInput = document.querySelector("#q-content");
  const qPreviewBox = document.querySelector("#q-math-preview");
  qContentInput?.addEventListener("input", () => {
    if (!qPreviewBox) return;
    qPreviewBox.textContent = qContentInput.value.trim() || "Xem trước công thức toán học...";
    typesetMath(qPreviewBox);
  });

  async function loadQuestions(page = state.pages.questions) {
    state.pages.questions = page;
    const params = new URLSearchParams({
      page: String(page),
      limit: "10",
      include_inactive: String(document.querySelector("#filter-questions-inactive")?.checked ?? true),
    });
    const search = document.querySelector("#filter-questions-search")?.value.trim();
    const sid = document.querySelector("#filter-questions-subject")?.value;
    const diff = document.querySelector("#filter-questions-difficulty")?.value.trim();
    if (search) params.set("search", search);
    if (sid) params.set("subject_id", sid);
    if (diff) params.set("difficulty", diff);

    try {
      const res = await requestJson(`/api/admin/questions?${params}`);
      renderTable(
        "#questions-table-wrap",
        [
          { label: "ID", render: (q) => q.id },
          {
            label: "Nội dung câu hỏi",
            render: (q) => {
              const box = el("div");
              box.append(el("div", "", truncate(q.content, 130)));
              const correct = (q.options || []).find((o) => o.is_correct);
              if (correct) {
                const ans = el("small", "text-success", "✓ Đáp án: " + truncate(correct.content, 60));
                ans.style.display = "block";
                box.append(ans);
              }
              return box;
            },
          },
          {
            label: "Môn / Chủ đề",
            render: (q) => {
              const box = el("div");
              box.append(el("div", "", q.subject_name || q.subject_id));
              if (q.topic) box.append(el("small", "text-muted", q.topic));
              return box;
            },
          },
          { label: "Độ khó", render: (q) => `${q.difficulty}/10` },
          { label: "Trạng thái", render: (q) => (q.is_active ? badge("Đang dùng", "success") : badge("Đã ẩn", "secondary")) },
          {
            label: "Thao tác",
            render: (q) => {
              const box = el("div", "table-actions");
              box.append(
                actionBtn("Sửa", "btn-outline-primary", () => openQuestionModal(q)),
                actionBtn(q.is_active ? "Ẩn" : "Hiện", q.is_active ? "btn-outline" : "btn-success", async () => {
                  try {
                    await requestJson(`/api/admin/questions/${q.id}/toggle-status`, { method: "PATCH" });
                    toast("Đã cập nhật trạng thái câu hỏi.", "success");
                    loadQuestions();
                  } catch (err) {
                    toast(err.message, "error");
                  }
                })
              );
              return box;
            },
          },
        ],
        res.data || []
      );
      renderPagination("#questions-pagination", res.pagination, loadQuestions);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function openQuestionModal(q = null) {
    const f = document.querySelector("#form-question");
    f.reset();
    f.elements.id.value = q ? q.id : "";
    if (q) f.elements.subject_id.value = String(q.subject_id);
    f.elements.topic.value = q?.topic || "";
    f.elements.difficulty.value = q ? q.difficulty : 5.5;
    f.elements.content.value = q ? q.content : "";
    f.elements.explanation.value = q?.explanation || "";
    f.elements.is_active.checked = q ? Boolean(q.is_active) : true;

    const opts = q?.options || [];
    let correctIdx = 0;
    [0, 1, 2, 3].forEach((i) => {
      f.elements[`option_${i}`].value = opts[i]?.content || "";
      if (opts[i]?.is_correct) correctIdx = i;
    });
    const radios = f.querySelectorAll('input[name="correct_option"]');
    if (radios[correctIdx]) radios[correctIdx].checked = true;

    if (qPreviewBox) {
      qPreviewBox.textContent = f.elements.content.value.trim() || "Xem trước công thức toán học...";
    }
    renderLessonChecklist("#q-lessons-checklist", f.elements.subject_id.value, q?.lesson_ids || []);
    document.querySelector("#modal-question-title").textContent = q ? `Sửa câu hỏi #${q.id}` : "Thêm câu hỏi trắc nghiệm";
    openModal("#modal-question");
  }

  document.querySelector("#q-subject")?.addEventListener("change", (e) => {
    renderLessonChecklist("#q-lessons-checklist", e.currentTarget.value, []);
  });
  document.querySelector("#btn-add-question")?.addEventListener("click", () => openQuestionModal());
  document.querySelector("#form-question")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const id = f.elements.id.value;
    const correct = Number(f.elements.correct_option.value);
    const payload = {
      subject_id: Number(f.elements.subject_id.value),
      topic: f.elements.topic.value.trim() || null,
      difficulty: Number(f.elements.difficulty.value),
      content: f.elements.content.value.trim(),
      explanation: f.elements.explanation.value.trim() || null,
      is_active: f.elements.is_active.checked,
      lesson_ids: getCheckedIds("#q-lessons-checklist"),
      options: [0, 1, 2, 3].map((idx) => ({
        content: f.elements[`option_${idx}`].value.trim(),
        is_correct: idx === correct,
      })),
    };
    try {
      await requestJson(id ? `/api/admin/questions/${id}` : "/api/admin/questions", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      closeModal(f.closest(".modal-backdrop"));
      toast(id ? "Đã cập nhật câu hỏi." : "Đã tạo câu hỏi mới.", "success");
      loadQuestions();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // ---------------- VIEW 5: ASSESSMENTS & QUESTION PICKER ----------------

  async function loadAssessments(page = state.pages.assessments) {
    state.pages.assessments = page;
    const params = new URLSearchParams({
      page: String(page),
      limit: "10",
      include_inactive: String(document.querySelector("#filter-assessments-inactive")?.checked ?? true),
    });
    const search = document.querySelector("#filter-assessments-search")?.value.trim();
    const sid = document.querySelector("#filter-assessments-subject")?.value;
    const type = document.querySelector("#filter-assessments-type")?.value;
    if (search) params.set("search", search);
    if (sid) params.set("subject_id", sid);
    if (type) params.set("type", type);

    const typeLabels = {
      quiz: ["Quiz", "primary"],
      exam: ["Exam", "danger"],
      practice: ["Practice", "info"],
    };

    try {
      const res = await requestJson(`/api/admin/assessments?${params}`);
      renderTable(
        "#assessments-table-wrap",
        [
          { label: "ID", render: (a) => a.id },
          {
            label: "Tên đề thi",
            render: (a) => {
              const box = el("div");
              box.append(el("strong", "", a.title));
              if (a.description) box.append(el("div", "text-muted", truncate(a.description, 75)));
              return box;
            },
          },
          { label: "Môn học", render: (a) => a.subject_name },
          {
            label: "Loại",
            render: (a) => {
              const [lbl, v] = typeLabels[a.type] || [a.type, "secondary"];
              return badge(lbl, v);
            },
          },
          { label: "Cấu hình", render: (a) => `${a.question_count} câu · ${a.duration_minutes}p · Đạt ${a.pass_score}%` },
          { label: "Lượt thi", render: (a) => a.attempt_count ?? 0 },
          { label: "Trạng thái", render: (a) => (a.is_active ? badge("Đang mở", "success") : badge("Đã ẩn", "secondary")) },
          {
            label: "Thao tác",
            render: (a) => {
              const box = el("div", "table-actions");
              if (a.is_active) {
                const tryLink = el("a", "btn btn-sm btn-outline", "Xem / Làm thử");
                tryLink.href = `/quiz?id=${a.id}`;
                box.append(tryLink);
              }
              box.append(
                actionBtn("Sửa & Chọn câu", "btn-outline-primary", () => openAssessmentModal(a.id)),
                actionBtn(a.is_active ? "Ẩn" : "Mở", a.is_active ? "btn-outline" : "btn-success", async () => {
                  try {
                    await requestJson(`/api/admin/assessments/${a.id}/toggle-status`, { method: "PATCH" });
                    toast("Đã đổi trạng thái đề thi.", "success");
                    loadAssessments();
                  } catch (err) {
                    toast(err.message, "error");
                  }
                })
              );
              return box;
            },
          },
        ],
        res.data || []
      );
      renderPagination("#assessments-pagination", res.pagination, loadAssessments);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function loadPickerAvailableQuestions() {
    const params = new URLSearchParams({ page: "1", limit: "60" });
    const search = document.querySelector("#picker-search")?.value.trim();
    const sid = document.querySelector("#picker-subject-filter")?.value;
    if (search) params.set("search", search);
    if (sid) params.set("subject_id", sid);
    try {
      const res = await requestJson(`/api/admin/questions?${params}`);
      state.assessmentPicker.available = res.data || [];
      renderAssessmentPicker();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function renderAssessmentPicker() {
    const availBox = document.querySelector("#picker-available-list");
    const selBox = document.querySelector("#picker-selected-list");
    const countEl = document.querySelector("#picker-selected-count");
    if (!availBox || !selBox) return;

    const selectedMap = new Map(state.assessmentPicker.selected.map((item) => [item.question_id, item]));
    if (countEl) countEl.textContent = String(state.assessmentPicker.selected.length);

    availBox.replaceChildren();
    if (!state.assessmentPicker.available.length) {
      availBox.append(el("p", "text-muted", "Không có câu hỏi phù hợp."));
    } else {
      state.assessmentPicker.available.forEach((q) => {
        const isAdded = selectedMap.has(q.id);
        const item = el("div", "picker-item");
        const contentWrap = el("div", "picker-item-content");
        contentWrap.append(el("div", "", `#${q.id}: ${truncate(q.content, 110)}`));
        contentWrap.append(
          el("div", "picker-item-meta", `${q.subject_name || ""} · Độ khó ${q.difficulty}/10${q.topic ? " · " + q.topic : ""}`)
        );
        const btn = actionBtn(isAdded ? "Đã chọn" : "+ Thêm", isAdded ? "btn-outline" : "btn-outline-primary", () => {
          if (isAdded) return;
          state.assessmentPicker.selected.push({
            question_id: q.id,
            content: q.content,
            topic: q.topic,
            difficulty: q.difficulty,
            points: 1,
          });
          renderAssessmentPicker();
        });
        btn.disabled = isAdded;
        item.append(contentWrap, btn);
        availBox.append(item);
      });
    }

    selBox.replaceChildren();
    if (!state.assessmentPicker.selected.length) {
      selBox.append(el("p", "text-muted", "Chưa chọn câu hỏi nào. Hãy bấm '+ Thêm' ở cột bên trái."));
    } else {
      state.assessmentPicker.selected.forEach((itemObj, idx) => {
        const row = el("div", "picker-item");
        const contentWrap = el("div", "picker-item-content");
        contentWrap.append(el("div", "", `Câu ${idx + 1} (#${itemObj.question_id}): ${truncate(itemObj.content, 90)}`));
        contentWrap.append(el("div", "picker-item-meta", `Độ khó ${itemObj.difficulty}/10`));

        const controls = el("div", "picker-item-controls");
        const ptsInput = document.createElement("input");
        ptsInput.type = "number";
        ptsInput.min = "0.5";
        ptsInput.step = "0.5";
        ptsInput.value = String(itemObj.points || 1);
        ptsInput.className = "points-input";
        ptsInput.title = "Điểm câu hỏi";
        ptsInput.addEventListener("change", () => {
          const v = parseFloat(ptsInput.value);
          itemObj.points = v > 0 ? v : 1;
        });

        const upBtn = actionBtn("↑", "btn-outline", () => {
          if (idx === 0) return;
          const arr = state.assessmentPicker.selected;
          [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
          renderAssessmentPicker();
        });
        upBtn.disabled = idx === 0;

        const downBtn = actionBtn("↓", "btn-outline", () => {
          const arr = state.assessmentPicker.selected;
          if (idx >= arr.length - 1) return;
          [arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]];
          renderAssessmentPicker();
        });
        downBtn.disabled = idx === state.assessmentPicker.selected.length - 1;

        const rmBtn = actionBtn("×", "btn-danger", () => {
          state.assessmentPicker.selected.splice(idx, 1);
          renderAssessmentPicker();
        });

        controls.append(ptsInput, upBtn, downBtn, rmBtn);
        row.append(contentWrap, controls);
        selBox.append(row);
      });
    }

    typesetMath(availBox);
    typesetMath(selBox);
  }

  async function openAssessmentModal(assessmentId = null) {
    const f = document.querySelector("#form-assessment");
    f.reset();
    f.elements.id.value = assessmentId ? String(assessmentId) : "";
    state.assessmentPicker.selected = [];

    if (assessmentId) {
      try {
        const res = await requestJson(`/api/admin/assessments/${assessmentId}`);
        const a = res.data;
        f.elements.subject_id.value = String(a.subject_id);
        f.elements.type.value = a.type;
        f.elements.title.value = a.title;
        f.elements.duration_minutes.value = a.duration_minutes;
        f.elements.pass_score.value = a.pass_score;
        f.elements.description.value = a.description || "";
        f.elements.is_active.checked = Boolean(a.is_active);
        state.assessmentPicker.selected = (a.questions || []).map((q) => ({
          question_id: q.id,
          content: q.content,
          topic: q.topic,
          difficulty: q.difficulty,
          points: q.points || 1,
        }));
        document.querySelector("#modal-assessment-title").textContent = `Chỉnh sửa đề thi #${a.id}`;
      } catch (err) {
        toast(err.message, "error");
        return;
      }
    } else {
      f.elements.duration_minutes.value = 30;
      f.elements.pass_score.value = 50;
      f.elements.is_active.checked = true;
      document.querySelector("#modal-assessment-title").textContent = "Tạo đề thi / bài tập mới";
    }

    const pickerSubject = document.querySelector("#picker-subject-filter");
    if (pickerSubject && f.elements.subject_id.value) {
      pickerSubject.value = f.elements.subject_id.value;
    }
    openModal("#modal-assessment");
    await loadPickerAvailableQuestions();
  }

  document.querySelector("#btn-add-assessment")?.addEventListener("click", () => openAssessmentModal());
  document.querySelector("#picker-load-btn")?.addEventListener("click", loadPickerAvailableQuestions);
  document.querySelector("#picker-subject-filter")?.addEventListener("change", loadPickerAvailableQuestions);
  document.querySelector("#picker-search")?.addEventListener("input", debounce(loadPickerAvailableQuestions, 300));
  document.querySelector("#picker-clear-btn")?.addEventListener("click", () => {
    state.assessmentPicker.selected = [];
    renderAssessmentPicker();
  });

  document.querySelector("#form-assessment")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const id = f.elements.id.value;
    const payload = {
      subject_id: Number(f.elements.subject_id.value),
      type: f.elements.type.value,
      title: f.elements.title.value.trim(),
      duration_minutes: Number(f.elements.duration_minutes.value),
      pass_score: Number(f.elements.pass_score.value),
      description: f.elements.description.value.trim() || null,
      is_active: f.elements.is_active.checked,
      question_items: state.assessmentPicker.selected.map((q) => ({
        question_id: q.question_id,
        points: Number(q.points) > 0 ? Number(q.points) : 1,
      })),
    };
    try {
      await requestJson(id ? `/api/admin/assessments/${id}` : "/api/admin/assessments", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      closeModal(f.closest(".modal-backdrop"));
      toast(id ? "Đã cập nhật đề thi." : "Đã tạo đề thi mới.", "success");
      loadAssessments();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // ---------------- VIEW 6: ATTEMPTS ----------------

  async function loadAttempts(page = state.pages.attempts) {
    state.pages.attempts = page;
    const params = new URLSearchParams({ page: String(page), limit: "15" });
    const search = document.querySelector("#filter-attempts-search")?.value.trim();
    const sid = document.querySelector("#filter-attempts-subject")?.value;
    const status = document.querySelector("#filter-attempts-status")?.value;
    if (search) params.set("search", search);
    if (sid) params.set("subject_id", sid);
    if (status) params.set("status", status);

    try {
      const res = await requestJson(`/api/admin/attempts?${params}`);
      renderTable(
        "#attempts-table-wrap",
        [
          { label: "ID", render: (a) => a.id },
          {
            label: "Học viên",
            render: (a) => {
              const box = el("div");
              box.append(el("strong", "", a.user_name));
              box.append(el("div", "text-muted", a.user_email));
              return box;
            },
          },
          {
            label: "Đề thi",
            render: (a) => {
              const box = el("div");
              box.append(el("div", "", a.assessment_title));
              box.append(el("small", "text-muted", a.subject_name));
              return box;
            },
          },
          {
            label: "Điểm số",
            render: (a) => {
              if (a.status !== "completed" || a.score === null) return "—";
              return badge(`${a.score}% (${a.is_passed ? "Đạt" : "Chưa đạt"})`, a.is_passed ? "success" : "danger");
            },
          },
          { label: "Số câu đúng", render: (a) => `${a.correct_answers} / ${a.total_questions}` },
          {
            label: "Trạng thái",
            render: (a) => {
              if (a.status === "completed") return badge("Đã nộp", "success");
              if (a.status === "in_progress") return badge("Đang làm", "info");
              return badge("Đã hủy", "secondary");
            },
          },
          {
            label: "Thời gian",
            render: (a) => {
              const box = el("div");
              box.append(el("div", "", formatDateTime(a.start_time)));
              box.append(el("small", "text-muted", "Thời lượng: " + formatDuration(a.duration_seconds)));
              return box;
            },
          },
          {
            label: "Chi tiết",
            render: (a) => {
              const link = el("a", "btn btn-sm btn-outline-primary", "Xem bài làm");
              link.href = `/quiz/results?attempt_id=${a.id}`;
              return link;
            },
          },
        ],
        res.data || []
      );
      renderPagination("#attempts-pagination", res.pagination, loadAttempts);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  // ---------------- VIEW 7: USERS ----------------

  async function loadUsers(page = state.pages.users) {
    state.pages.users = page;
    const params = new URLSearchParams({ page: String(page), limit: "15" });
    const search = document.querySelector("#filter-users-search")?.value.trim();
    const role = document.querySelector("#filter-users-role")?.value;
    if (search) params.set("search", search);
    if (role) params.set("role", role);

    const roleVariant = { admin: "danger", teacher: "primary", student: "info" };

    try {
      const res = await requestJson(`/api/admin/users?${params}`);
      renderTable(
        "#users-table-wrap",
        [
          { label: "ID", render: (u) => u.id },
          { label: "Họ và tên", render: (u) => el("strong", "", u.full_name) },
          { label: "Email", render: (u) => u.email },
          { label: "SĐT", render: (u) => u.phone || "—" },
          { label: "Phong cách", render: (u) => u.study_type || "—" },
          { label: "Lượt thi", render: (u) => u.attempt_count },
          {
            label: "Vai trò",
            render: (u) => {
              if (config.userRole !== "admin" || u.id === config.userId) {
                return badge(u.role, roleVariant[u.role] || "secondary");
              }
              const box = el("div", "table-actions");
              const sel = document.createElement("select");
              sel.className = "form-control";
              sel.style.cssText = "width:auto;padding:0.2rem 0.5rem;font-size:0.8rem;";
              ["student", "teacher", "admin"].forEach((r) => {
                sel.append(new Option(r, r, r === u.role, r === u.role));
              });
              const saveBtn = actionBtn("Lưu", "btn-outline-primary", async () => {
                try {
                  await requestJson(`/api/admin/users/${u.id}/role`, {
                    method: "PATCH",
                    body: JSON.stringify({ role: sel.value }),
                  });
                  toast(`Đã đổi vai trò của ${u.full_name} thành ${sel.value}.`, "success");
                  loadUsers();
                } catch (err) {
                  toast(err.message, "error");
                }
              });
              box.append(sel, saveBtn);
              return box;
            },
          },
          { label: "Ngày tạo", render: (u) => formatDateTime(u.created_at) },
        ],
        res.data || []
      );
      renderPagination("#users-pagination", res.pagination, loadUsers);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  // ---------------- FILTER BINDINGS ----------------

  document.querySelector("#filter-subjects-search")?.addEventListener("input", debounce(() => loadSubjectsTable(1)));
  document.querySelector("#filter-subjects-inactive")?.addEventListener("change", () => loadSubjectsTable(1));

  document.querySelector("#filter-lessons-search")?.addEventListener("input", debounce(() => loadLessonsTable(1)));
  document.querySelector("#filter-lessons-subject")?.addEventListener("change", () => loadLessonsTable(1));
  document.querySelector("#filter-lessons-status")?.addEventListener("change", () => loadLessonsTable(1));

  document.querySelector("#filter-materials-search")?.addEventListener("input", debounce(() => loadMaterials(1)));
  document.querySelector("#filter-materials-subject")?.addEventListener("change", () => loadMaterials(1));
  document.querySelector("#filter-materials-inactive")?.addEventListener("change", () => loadMaterials(1));

  document.querySelector("#filter-questions-search")?.addEventListener("input", debounce(() => loadQuestions(1)));
  document.querySelector("#filter-questions-subject")?.addEventListener("change", () => loadQuestions(1));
  document.querySelector("#filter-questions-difficulty")?.addEventListener("input", debounce(() => loadQuestions(1)));
  document.querySelector("#filter-questions-inactive")?.addEventListener("change", () => loadQuestions(1));

  document.querySelector("#filter-assessments-search")?.addEventListener("input", debounce(() => loadAssessments(1)));
  document.querySelector("#filter-assessments-subject")?.addEventListener("change", () => loadAssessments(1));
  document.querySelector("#filter-assessments-type")?.addEventListener("change", () => loadAssessments(1));
  document.querySelector("#filter-assessments-inactive")?.addEventListener("change", () => loadAssessments(1));

  document.querySelector("#filter-attempts-search")?.addEventListener("input", debounce(() => loadAttempts(1)));
  document.querySelector("#filter-attempts-subject")?.addEventListener("change", () => loadAttempts(1));
  document.querySelector("#filter-attempts-status")?.addEventListener("change", () => loadAttempts(1));

  document.querySelector("#filter-users-search")?.addEventListener("input", debounce(() => loadUsers(1)));
  document.querySelector("#filter-users-role")?.addEventListener("change", () => loadUsers(1));

  // ---------------- USER DROPDOWN, LOGOUT & INIT ----------------

  const userMenuBtn = document.querySelector("#user-menu-btn");
  const userDropdownMenu = document.querySelector("#user-dropdown-menu");

  function setUserDropdownOpen(isOpen) {
    if (!userDropdownMenu || !userMenuBtn) return;
    userDropdownMenu.classList.toggle("open", isOpen);
    userMenuBtn.setAttribute("aria-expanded", String(isOpen));
  }

  userMenuBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = userDropdownMenu?.classList.contains("open");
    setUserDropdownOpen(!isOpen);
  });

  document.addEventListener("click", (e) => {
    if (userDropdownMenu?.classList.contains("open") && !e.target.closest(".user-dropdown")) {
      setUserDropdownOpen(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setUserDropdownOpen(false);
  });

  document.querySelector("#open-profile-btn")?.addEventListener("click", () => {
    setUserDropdownOpen(false);
    openModal("#modal-profile");
  });

  document.querySelector("#logout-button")?.addEventListener("click", async () => {
    try {
      await requestJson("/api/auth/logout", { method: "POST" });
      window.location.assign("/login");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  (async () => {
    await refreshSubjectsAndLessonsCache();
    const initialHash = window.location.hash.replace("#", "") || "dashboard";
    switchTab(initialHash);
  })();
})();
