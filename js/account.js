(() => {
  const config = window.accountDashboardConfig;
  const subjectFilter = document.querySelector("#subject-filter");
  const subjectMessage = document.querySelector("#subject-message");
  const searchInput = document.querySelector("#content-search");
  const paginationNav = document.querySelector("#account-pagination");
  const cards = document.querySelector("#account-cards");
  const message = document.querySelector("#account-message");
  const tabs = Array.from(document.querySelectorAll(".learner-tab"));
  const logoutButton = document.querySelector("#logout-button");
  if (!config || !subjectFilter || !cards || !message) return;

  const PAGE_SIZE = 8;
  let kind = "materials";
  let recordsRequestId = 0;
  let currentPage = 1;
  let searchQuery = "";
  let searchDebounceTimer = null;

  async function getJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error("Máy chủ trả về dữ liệu không hợp lệ.");
    }
    if (!response.ok || !body?.success) {
      throw new Error(body?.message || "Không thể tải nội dung lúc này.");
    }
    return body;
  }

  async function getAllPages(endpoint, filters = {}) {
    const records = [];
    let page = 1;
    let totalPages = 1;

    while (page <= totalPages) {
      const url = new URL(endpoint, window.location.origin);
      url.searchParams.set("page", String(page));
      url.searchParams.set("limit", "100");
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== "" && value !== null && value !== undefined) {
          url.searchParams.set(key, String(value));
        }
      });

      const body = await getJson(url);
      if (!Array.isArray(body.data)) {
        throw new Error("Dữ liệu trả về không đúng định dạng.");
      }
      records.push(...body.data);

      const receivedPages = Number(body.pagination?.total_pages ?? 1);
      if (!Number.isInteger(receivedPages) || receivedPages < 0) {
        throw new Error("Thông tin phân trang không hợp lệ.");
      }
      totalPages = receivedPages;
      page += 1;
    }

    return records;
  }

  async function fetchPage(endpoint, filters = {}, page = 1, limit = PAGE_SIZE) {
    const url = new URL(endpoint, window.location.origin);
    url.searchParams.set("page", String(page));
    url.searchParams.set("limit", String(limit));
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });

    const body = await getJson(url);
    if (!Array.isArray(body.data)) {
      throw new Error("Dữ liệu trả về không đúng định dạng.");
    }
    return {
      records: body.data,
      pagination: body.pagination || { page: 1, limit, total_records: body.data.length, total_pages: 1 }
    };
  }

  function appendText(parent, tagName, text, className) {
    const element = document.createElement(tagName);
    element.textContent = text;
    if (className) element.className = className;
    parent.append(element);
    return element;
  }

  function createCard(record, recordKind) {
    const card = document.createElement("article");
    card.className = "learner-card";
    appendText(card, "h2", record.title || "Nội dung chưa có tiêu đề", "learner-card-title");

    const metadata = document.createElement("p");
    metadata.className = "learner-card-meta";
    const facts = [];
    if (record.lesson_code) facts.push(record.lesson_code);
    if (record.subject_name) facts.push(record.subject_name);
    if (recordKind === "materials") {
      if (record.difficulty !== null && record.difficulty !== undefined) {
        facts.push("Độ khó " + record.difficulty + "/10");
      }
    } else {
      if (record.type) facts.push(record.type);
      if (record.question_count !== null && record.question_count !== undefined) {
        facts.push(String(record.question_count) + " câu hỏi");
      }
      if (record.duration_minutes !== null && record.duration_minutes !== undefined) {
        facts.push(String(record.duration_minutes) + " phút");
      }
      if (record.pass_score !== null && record.pass_score !== undefined) {
        facts.push("Điểm đạt " + record.pass_score);
      }
    }
    metadata.textContent = facts.filter(Boolean).join(" · ");
    card.append(metadata);

    if (record.description) {
      appendText(card, "p", record.description, "learner-card-description");
    }

    if (kind === "materials") {
      const link = document.createElement("a");
      const readerUrl = new URL(config.readingUrl, window.location.origin);
      readerUrl.searchParams.set("id", String(record.id));
      link.href = readerUrl.pathname + readerUrl.search;
      link.className = "learner-card-link";
      link.textContent = "Mở tài liệu";
      card.append(link);
    } else {
      const link = document.createElement("a");
      const quizUrl = new URL(config.quizUrl, window.location.origin);
      quizUrl.searchParams.set("id", String(record.id));
      link.href = quizUrl.pathname + quizUrl.search;
      link.className = "learner-card-link learner-card-btn-quiz";
      link.textContent = "Làm bài";
      card.append(link);
    }

    return card;
  }

  function renderPagination(pagination) {
    if (!paginationNav) return;
    paginationNav.replaceChildren();

    const totalPages = Number(pagination.total_pages) || 1;
    if (totalPages <= 1) return;

    const page = Number(pagination.page) || 1;

    function createButton(text, targetPage, disabled = false, isActive = false, ariaLabel = "") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "learner-page-btn" + (isActive ? " active" : "");
      btn.textContent = text;
      if (ariaLabel) btn.setAttribute("aria-label", ariaLabel);
      if (isActive) btn.setAttribute("aria-current", "page");
      if (disabled) {
        btn.disabled = true;
      } else if (!isActive) {
        btn.addEventListener("click", () => {
          document.querySelector("#courses")?.scrollIntoView({ behavior: "smooth", block: "start" });
          loadRecords(targetPage);
        });
      }
      return btn;
    }

    paginationNav.append(createButton("« Trước", page - 1, page <= 1, false, "Trang trước"));

    const maxVisible = 5;
    let startPage = Math.max(1, page - 2);
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
      paginationNav.append(createButton("1", 1, false, page === 1, "Trang 1"));
      if (startPage > 2) {
        const dots = document.createElement("span");
        dots.className = "learner-page-dots";
        dots.textContent = "…";
        paginationNav.append(dots);
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      paginationNav.append(createButton(String(i), i, false, page === i, "Trang " + i));
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        const dots = document.createElement("span");
        dots.className = "learner-page-dots";
        dots.textContent = "…";
        paginationNav.append(dots);
      }
      paginationNav.append(createButton(String(totalPages), totalPages, false, page === totalPages, "Trang " + totalPages));
    }

    paginationNav.append(createButton("Sau »", page + 1, page >= totalPages, false, "Trang sau"));
  }

  async function loadLessons() {
    try {
      const endpoint = config.lessonsUrl || config.subjectsUrl;
      const items = await getAllPages(endpoint);
      const optgroups = {};
      items.forEach((item) => {
        if (item.code && item.title) {
          const groupName = item.subject_name || "Môn học";
          if (!optgroups[groupName]) {
            const optgroup = document.createElement("optgroup");
            optgroup.label = groupName;
            subjectFilter.append(optgroup);
            optgroups[groupName] = optgroup;
          }
          const option = document.createElement("option");
          option.value = String(item.id);
          option.textContent = `${item.code} - ${item.title}`;
          optgroups[groupName].append(option);
        } else {
          const option = document.createElement("option");
          option.value = String(item.id);
          option.textContent = item.name || item.title;
          subjectFilter.append(option);
        }
      });
      if (subjectMessage) subjectMessage.textContent = "";
    } catch (error) {
      subjectFilter.disabled = true;
      if (subjectMessage) subjectMessage.textContent = "Không tải được danh sách chủ đề bài học. " + error.message;
    }
  }

  async function loadRecords(targetPage = 1) {
    currentPage = targetPage;
    const requestId = ++recordsRequestId;
    const requestedKind = kind;
    const requestedLesson = subjectFilter.value;
    const requestedSearch = searchQuery;
    message.textContent = "Đang tải nội dung học tập…";
    cards.replaceChildren();
    if (paginationNav) paginationNav.replaceChildren();

    const endpoint = requestedKind === "materials" ? config.materialsUrl : config.assessmentsUrl;
    const filters = {};
    if (requestedLesson) filters.lesson_id = requestedLesson;
    if (requestedSearch) filters.search = requestedSearch;

    try {
      const { records, pagination } = await fetchPage(endpoint, filters, currentPage, PAGE_SIZE);
      if (requestId !== recordsRequestId) return;
      if (!records.length) {
        if (requestedSearch) {
          message.textContent = `Không tìm thấy nội dung phù hợp với "${requestedSearch}".`;
        } else {
          message.textContent = requestedKind === "materials"
            ? "Chủ đề này chưa có tài liệu phù hợp."
            : "Chủ đề này chưa có đề ôn tập phù hợp.";
        }
        return;
      }
      records.forEach((record) => cards.append(createCard(record, requestedKind)));
      message.textContent = "";
      renderPagination(pagination);
    } catch (error) {
      if (requestId !== recordsRequestId) return;
      message.textContent = error.message || "Không thể tải nội dung lúc này.";
    }
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        searchQuery = searchInput.value.trim();
        loadRecords(1);
      }, 350);
    });

    searchInput.addEventListener("search", () => {
      searchQuery = searchInput.value.trim();
      loadRecords(1);
    });

    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        clearTimeout(searchDebounceTimer);
        searchQuery = searchInput.value.trim();
        loadRecords(1);
      }
    });
  }

  subjectFilter.addEventListener("change", () => loadRecords(1));

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      kind = tab.dataset.kind === "assessments" ? "assessments" : "materials";
      tabs.forEach((item) => {
        const active = item === tab;
        item.classList.toggle("active", active);
        item.setAttribute("aria-selected", String(active));
      });
      loadRecords(1);
    });
  });

  if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
      logoutButton.disabled = true;
      message.textContent = "Đang đăng xuất…";
      try {
        const response = await fetch(config.logoutUrl, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content || "",
          },
        });
        const body = await response.json();
        if (!response.ok || !body?.success) {
          throw new Error(body?.message || "Không thể đăng xuất lúc này.");
        }
        window.location.assign(config.loginUrl);
      } catch (error) {
        message.textContent = error.message || "Không thể kết nối với máy chủ.";
        logoutButton.disabled = false;
      }
    });
  }

  loadLessons();
  loadRecords(1);
})();
