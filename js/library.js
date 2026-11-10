(() => {
  const cards = document.querySelector("#cards");
  if (!cards) return;

  const search = document.querySelector("#search");
  const subjectFilter = document.querySelector("#subject-filter");
  const difficultyFilter = document.querySelector("#difficulty-filter");
  const message = document.querySelector("#message");
  const pages = document.querySelector("#pages");
  const token = document.querySelector('meta[name="csrf-token"]')?.content || "";
  let kind = "materials";
  let page = 1;
  let debounceTimer;

  async function getJson(url, options = {}) {
    const response = await fetch(url, options);
    const body = await response.json();
    if (!response.ok || !body.success) throw new Error(body.message || "Yêu cầu thất bại.");
    return body;
  }

  function makeCard(record) {
    const article = document.createElement("article");
    const title = document.createElement("h2");
    title.textContent = record.title;
    article.append(title);

    const details = document.createElement("p");
    if (kind === "materials") {
      details.textContent = [record.subject_name, record.difficulty].filter(Boolean).join(" · ");
    } else {
      details.textContent = [
        record.subject_name,
        record.type,
        String(record.question_count) + " câu",
        String(record.duration_minutes) + " phút",
      ].filter(Boolean).join(" · ");
    }
    article.append(details);

    if (record.description) {
      const description = document.createElement("p");
      description.textContent = record.description;
      article.append(description);
    }

    const link = document.createElement("a");
    link.href = kind === "materials" ? "/reading?id=" + record.id : "/api/assessments/" + record.id;
    link.textContent = kind === "materials" ? "Đọc tài liệu" : "Xem thông tin đề";
    article.append(link);
    return article;
  }

  function showPages(pagination) {
    pages.replaceChildren();
    if (!pagination || pagination.total_pages < 2) return;
    for (let number = 1; number <= pagination.total_pages; number += 1) {
      const button = document.createElement("button");
      button.textContent = String(number);
      button.disabled = number === pagination.page;
      button.addEventListener("click", () => {
        page = number;
        loadRecords();
      });
      pages.append(button);
    }
  }

  async function loadRecords() {
    message.textContent = "Đang tải…";
    cards.replaceChildren();
    const params = new URLSearchParams({ page: String(page), limit: "9" });
    if (search.value.trim()) params.set("search", search.value.trim());
    if (subjectFilter.value) params.set("subject_id", subjectFilter.value);
    if (kind === "materials" && difficultyFilter.value) {
      params.set("difficulty", difficultyFilter.value);
    }
    try {
      const result = await getJson("/api/" + kind + "?" + params);
      result.data.forEach((record) => cards.append(makeCard(record)));
      message.textContent = result.data.length ? "" : "Chưa có nội dung phù hợp.";
      showPages(result.pagination);
    } catch (error) {
      message.textContent = error.message;
      pages.replaceChildren();
    }
  }

  async function loadSubjects() {
    try {
      const result = await getJson("/api/subjects");
      result.data.forEach((subject) => {
        const option = document.createElement("option");
        option.value = subject.id;
        option.textContent = subject.name;
        subjectFilter.append(option);
      });
    } catch (error) {
      message.textContent = error.message;
    }
  }

  search.addEventListener("input", () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      page = 1;
      loadRecords();
    }, 300);
  });
  subjectFilter.addEventListener("change", () => { page = 1; loadRecords(); });
  difficultyFilter.addEventListener("change", () => { page = 1; loadRecords(); });
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      kind = button.dataset.kind;
      page = 1;
      difficultyFilter.hidden = kind !== "materials";
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab === button));
      loadRecords();
    });
  });
  document.querySelector("#logout-button").addEventListener("click", async () => {
    try {
      await getJson("/api/auth/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": token },
      });
      window.location.assign("/login");
    } catch (error) {
      message.textContent = error.message;
    }
  });

  loadSubjects();
  loadRecords();
})();
