(() => {
  const config = window.accountDashboardConfig;
  const subjectFilter = document.querySelector("#subject-filter");
  const subjectMessage = document.querySelector("#subject-message");
  const cards = document.querySelector("#account-cards");
  const message = document.querySelector("#account-message");
  const tabs = Array.from(document.querySelectorAll(".learner-tab"));
  const logoutButton = document.querySelector("#logout-button");
  if (!config || !subjectFilter || !cards || !message) return;

  let kind = "materials";
  let recordsRequestId = 0;

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
    const facts = [record.subject_name];
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
    }

    return card;
  }

  async function loadSubjects() {
    try {
      const subjects = await getAllPages(config.subjectsUrl);
      subjects.forEach((subject) => {
        const option = document.createElement("option");
        option.value = String(subject.id);
        option.textContent = subject.name;
        subjectFilter.append(option);
      });
      if (subjectMessage) subjectMessage.textContent = "";
    } catch (error) {
      subjectFilter.disabled = true;
      if (subjectMessage) subjectMessage.textContent = "Không tải được danh sách môn học. " + error.message;
    }
  }

  async function loadRecords() {
    const requestId = ++recordsRequestId;
    const requestedKind = kind;
    const requestedSubject = subjectFilter.value;
    message.textContent = "Đang tải nội dung học tập…";
    cards.replaceChildren();
    const endpoint = requestedKind === "materials" ? config.materialsUrl : config.assessmentsUrl;
    const filters = requestedSubject ? { subject_id: requestedSubject } : {};

    try {
      const records = await getAllPages(endpoint, filters);
      if (requestId !== recordsRequestId) return;
      if (!records.length) {
        message.textContent = requestedKind === "materials"
          ? "Môn học này chưa có tài liệu phù hợp."
          : "Môn học này chưa có đề ôn tập phù hợp.";
        return;
      }
      records.forEach((record) => cards.append(createCard(record, requestedKind)));
      message.textContent = "";
    } catch (error) {
      if (requestId !== recordsRequestId) return;
      message.textContent = error.message || "Không thể tải nội dung lúc này.";
    }
  }

  subjectFilter.addEventListener("change", loadRecords);
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      kind = tab.dataset.kind === "assessments" ? "assessments" : "materials";
      tabs.forEach((item) => {
        const active = item === tab;
        item.classList.toggle("active", active);
        item.setAttribute("aria-selected", String(active));
      });
      loadRecords();
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

  loadSubjects();
  loadRecords();
})();
