(() => {
  const message = document.querySelector("#message");
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  if (!message) return;

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        "X-CSRF-Token": csrf,
        ...options.headers,
      },
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.message || "Yêu cầu thất bại.");
    return result;
  }

  function formObject(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  async function loadSubjects() {
    try {
      const result = await requestJson("/api/subjects?limit=100");
      const list = document.querySelector("#subject-list");
      result.data.forEach((subject) => {
        const optionText = subject.code + " — " + subject.name;
        const item = document.createElement("li");
        item.textContent = optionText;
        list.append(item);
        ["#material-subject", "#question-subject", "#assessment-subject"].forEach((selector) => {
          const option = document.createElement("option");
          option.value = subject.id;
          option.textContent = optionText;
          document.querySelector(selector).append(option);
        });
      });
    } catch (error) {
      message.textContent = error.message;
    }
  }

  function addAction(container, label, callback) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.style.width = "auto";
    button.style.marginRight = ".4rem";
    button.addEventListener("click", callback);
    container.append(button);
  }

  function renderRows(containerSelector, records, columns, actions) {
    const container = document.querySelector(containerSelector);
    container.replaceChildren();
    if (!records.length) {
      container.textContent = "Chưa có dữ liệu.";
      return;
    }
    const table = document.createElement("table");
    table.style.width = "100%";
    table.style.borderCollapse = "collapse";
    const head = document.createElement("tr");
    columns.forEach((column) => {
      const cell = document.createElement("th");
      cell.textContent = column.label;
      head.append(cell);
    });
    const actionHead = document.createElement("th");
    actionHead.textContent = "Thao tác";
    head.append(actionHead);
    table.append(head);

    records.forEach((record) => {
      const row = document.createElement("tr");
      columns.forEach((column) => {
        const cell = document.createElement("td");
        cell.textContent = String(column.value(record) ?? "");
        cell.style.padding = ".5rem";
        cell.style.borderTop = "1px solid #ddd";
        row.append(cell);
      });
      const actionCell = document.createElement("td");
      actionCell.style.padding = ".5rem";
      actionCell.style.borderTop = "1px solid #ddd";
      actions(record, actionCell);
      row.append(actionCell);
      table.append(row);
    });
    container.append(table);
  }

  async function loadManagedRecords() {
    try {
      const [materials, questions, assessments] = await Promise.all([
        requestJson("/api/admin/materials?limit=100&include_inactive=true"),
        requestJson("/api/admin/questions?limit=100&include_inactive=true"),
        requestJson("/api/admin/assessments?limit=100&include_inactive=true"),
      ]);

      renderRows("#materials-list", materials.data, [
        { label: "ID", value: (item) => item.id },
        { label: "Tiêu đề", value: (item) => item.title },
        { label: "Độ khó", value: (item) => item.difficulty },
        { label: "Trạng thái", value: (item) => item.is_active ? "Đang hiện" : "Đã ẩn" },
      ], (item, cell) => {
        addAction(cell, "Sửa", async () => {
          const title = window.prompt("Tiêu đề", item.title);
          if (title === null) return;
          const description = window.prompt("Mô tả", item.description || "");
          if (description === null) return;
          const file_url = window.prompt("URL tài liệu", item.file_url || "");
          if (file_url === null) return;
          try {
            await requestJson("/api/admin/materials/" + item.id, {
              method: "PUT",
              body: JSON.stringify({ title, description, file_url }),
            });
            await loadManagedRecords();
            message.textContent = "Đã cập nhật tài liệu.";
          } catch (error) { message.textContent = error.message; }
        });
        addAction(cell, item.is_active ? "Ẩn" : "Đã ẩn", async () => {
          if (!item.is_active) return;
          try {
            await requestJson("/api/admin/materials/" + item.id, { method: "DELETE" });
            await loadManagedRecords();
            message.textContent = "Đã ẩn tài liệu.";
          } catch (error) { message.textContent = error.message; }
        });
      });

      renderRows("#questions-list", questions.data, [
        { label: "ID", value: (item) => item.id },
        { label: "Câu hỏi", value: (item) => item.content },
        { label: "Độ khó", value: (item) => item.difficulty },
        { label: "Trạng thái", value: (item) => item.is_active ? "Đang dùng" : "Đã ẩn" },
      ], (item, cell) => {
        addAction(cell, "Sửa nội dung", async () => {
          const content = window.prompt("Nội dung câu hỏi", item.content);
          if (content === null) return;
          try {
            await requestJson("/api/admin/questions/" + item.id, {
              method: "PUT",
              body: JSON.stringify({ content }),
            });
            await loadManagedRecords();
            message.textContent = "Đã cập nhật câu hỏi.";
          } catch (error) { message.textContent = error.message; }
        });
        addAction(cell, item.is_active ? "Ẩn" : "Đã ẩn", async () => {
          if (!item.is_active) return;
          try {
            await requestJson("/api/admin/questions/" + item.id, { method: "DELETE" });
            await loadManagedRecords();
            message.textContent = "Đã ẩn câu hỏi.";
          } catch (error) { message.textContent = error.message; }
        });
      });

      renderRows("#assessments-list", assessments.data, [
        { label: "ID", value: (item) => item.id },
        { label: "Tên đề", value: (item) => item.title },
        { label: "Số câu", value: (item) => item.question_count },
        { label: "Trạng thái", value: (item) => item.is_active ? "Đang hiện" : "Đã ẩn" },
      ], (item, cell) => {
        addAction(cell, "Sửa tên", async () => {
          const title = window.prompt("Tên đề", item.title);
          if (title === null) return;
          try {
            await requestJson("/api/admin/assessments/" + item.id, {
              method: "PUT",
              body: JSON.stringify({ title }),
            });
            await loadManagedRecords();
            message.textContent = "Đã cập nhật đề thi.";
          } catch (error) { message.textContent = error.message; }
        });
        addAction(cell, item.is_active ? "Ẩn/hiện" : "Ẩn/hiện", async () => {
          try {
            await requestJson("/api/admin/assessments/" + item.id + "/toggle-status", { method: "PATCH" });
            await loadManagedRecords();
            message.textContent = "Đã đổi trạng thái đề thi.";
          } catch (error) { message.textContent = error.message; }
        });
      });
    } catch (error) {
      message.textContent = error.message;
    }
  }

  document.querySelector("#material-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = formObject(form);
    values.subject_id = Number(values.subject_id);
    values.difficulty = Number(values.difficulty);
    try {
      await requestJson("/api/admin/materials", { method: "POST", body: JSON.stringify(values) });
      message.textContent = "Đã tạo tài liệu.";
      form.reset();
      await loadManagedRecords();
    } catch (error) { message.textContent = error.message; }
  });

  document.querySelector("#question-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = formObject(form);
    values.subject_id = Number(values.subject_id);
    values.difficulty = Number(values.difficulty);
    const correct = Number(values.correct_option);
    values.options = [0, 1, 2, 3].map((index) => ({
      content: values["option_" + index],
      is_correct: index === correct,
    }));
    delete values.correct_option;
    [0, 1, 2, 3].forEach((index) => delete values["option_" + index]);
    try {
      await requestJson("/api/admin/questions", { method: "POST", body: JSON.stringify(values) });
      message.textContent = "Đã tạo câu hỏi.";
      form.reset();
      await loadManagedRecords();
    } catch (error) { message.textContent = error.message; }
  });

  document.querySelector("#assessment-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = formObject(form);
    values.subject_id = Number(values.subject_id);
    values.duration_minutes = Number(values.duration_minutes);
    values.pass_score = Number(values.pass_score);
    values.question_ids = values.question_ids
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map(Number);
    try {
      await requestJson("/api/admin/assessments", { method: "POST", body: JSON.stringify(values) });
      message.textContent = "Đã tạo đề thi.";
      form.reset();
      await loadManagedRecords();
    } catch (error) { message.textContent = error.message; }
  });

  document.querySelector("#logout-button").addEventListener("click", async () => {
    try {
      await requestJson("/api/auth/logout", { method: "POST" });
      window.location.assign("/login");
    } catch (error) { message.textContent = error.message; }
  });

  loadSubjects();
  loadManagedRecords();
})();
