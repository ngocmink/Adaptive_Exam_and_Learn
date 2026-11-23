(() => {
  const config = window.quizConfig;
  const form = document.querySelector("#quiz-form");
  if (!config || !form || !config.totalQuestions) return;

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const cards = Array.from(document.querySelectorAll(".question-card[data-index]"));
  const navPills = Array.from(document.querySelectorAll("#question-nav-grid .nav-pill"));
  const timerDisplay = document.querySelector("#time-left");
  const timerBadge = document.querySelector("#quiz-timer");
  const autosaveStatus = document.querySelector("#autosave-status");
  const progressText = document.querySelector("#answered-progress-text");
  const progressBar = document.querySelector("#answered-progress-bar");
  const modeButtons = Array.from(document.querySelectorAll("[data-view-mode]"));
  const submitModal = document.querySelector("#submit-modal");
  const timeoutOverlay = document.querySelector("#timeout-overlay");

  let currentIndex = 0;
  let viewMode = "single"; // 'single' | 'all'
  let remainingSeconds = Math.max(0, Number(config.remainingSeconds) || 0);
  let isSubmitting = false;
  let timerInterval = null;
  const flaggedSet = new Set();
  const localAnswers = { ...(config.savedAnswers || {}) };
  const localBackupKey = config.attemptId ? `vise_attempt_${config.attemptId}` : null;

  function setAutosaveState(state, text) {
    if (!autosaveStatus) return;
    autosaveStatus.className = `autosave-pill ${state}`;
    autosaveStatus.textContent = text;
  }

  function backupToLocalStorage() {
    if (!localBackupKey) return;
    try {
      window.localStorage.setItem(localBackupKey, JSON.stringify(localAnswers));
    } catch {}
  }

  function getSelectedOptionForQuestion(qid) {
    const checked = form.querySelector(`input[name="question_${qid}"]:checked`);
    return checked ? Number(checked.value) : null;
  }

  function collectAllAnswers() {
    const result = {};
    cards.forEach((card) => {
      const qid = Number(card.dataset.questionId);
      const val = getSelectedOptionForQuestion(qid);
      if (val !== null) result[qid] = val;
    });
    return result;
  }

  function syncCardSelectionStyles(qid) {
    document.querySelectorAll(`.option-label[data-question-id="${qid}"]`).forEach((lbl) => {
      const radio = lbl.querySelector('input[type="radio"]');
      lbl.classList.toggle("selected", Boolean(radio && radio.checked));
    });
  }

  function updateProgressAndNavigator() {
    let answeredCount = 0;
    cards.forEach((card, idx) => {
      const qid = Number(card.dataset.questionId);
      const isAnswered = getSelectedOptionForQuestion(qid) !== null;
      if (isAnswered) answeredCount += 1;
      const pill = navPills[idx];
      if (pill) {
        pill.classList.toggle("answered", isAnswered);
        pill.classList.toggle("current", idx === currentIndex);
        pill.classList.toggle("flagged", flaggedSet.has(idx));
      }
    });
    if (progressText) {
      progressText.textContent = `${answeredCount} / ${config.totalQuestions}`;
    }
    if (progressBar) {
      const pct = config.totalQuestions > 0 ? Math.round((answeredCount / config.totalQuestions) * 100) : 0;
      progressBar.style.width = `${pct}%`;
    }
  }

  function showQuestion(index) {
    if (index < 0 || index >= cards.length) return;
    currentIndex = index;

    if (viewMode === "single") {
      cards.forEach((card, idx) => {
        card.classList.toggle("hidden", idx !== currentIndex);
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      cards.forEach((card) => card.classList.remove("hidden"));
      cards[currentIndex]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    updateProgressAndNavigator();
  }

  function setViewMode(mode) {
    viewMode = mode === "all" ? "all" : "single";
    modeButtons.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.viewMode === viewMode);
    });
    if (viewMode === "all") {
      cards.forEach((card) => card.classList.remove("hidden"));
    } else {
      showQuestion(currentIndex);
    }
  }

  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => setViewMode(btn.dataset.viewMode));
  });

  // Restore any localStorage answers not yet reflected if network previously dropped
  if (localBackupKey) {
    try {
      const raw = window.localStorage.getItem(localBackupKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        Object.entries(parsed).forEach(([qid, optId]) => {
          if (localAnswers[qid] === undefined && optId !== null) {
            const radio = form.querySelector(`input[name="question_${qid}"][value="${optId}"]`);
            if (radio) {
              radio.checked = true;
              localAnswers[qid] = Number(optId);
              syncCardSelectionStyles(qid);
            }
          }
        });
      }
    } catch {}
  }

  // Auto-save to server
  async function saveAnswerToServer(questionId, selectedOptionId) {
    if (!config.saveUrl || isSubmitting) return;
    setAutosaveState("saving", "↻ Đang lưu...");
    try {
      const response = await fetch(config.saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          question_id: Number(questionId),
          selected_option_id: selectedOptionId !== null ? Number(selectedOptionId) : null,
        }),
      });
      const body = await response.json();
      if (body?.data?.expired && body?.data?.redirect_url) {
        isSubmitting = true;
        clearInterval(timerInterval);
        window.location.assign(body.data.redirect_url);
        return;
      }
      if (!response.ok || !body?.success) {
        if (response.status === 409 && body?.data?.redirect_url) {
          window.location.assign(body.data.redirect_url);
          return;
        }
        throw new Error(body?.message || "Lỗi lưu tạm.");
      }
      const nowTime = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setAutosaveState("saved", `✓ Đã lưu lúc ${nowTime}`);
    } catch {
      setAutosaveState("error", "⚠ Đã lưu tạm trên máy");
    }
  }

  // Option selection listener
  document.querySelectorAll(".option-label").forEach((label) => {
    const input = label.querySelector('input[type="radio"]');
    if (!input) return;
    input.addEventListener("change", () => {
      const qid = Number(label.dataset.questionId);
      const optId = Number(input.value);
      localAnswers[qid] = optId;
      backupToLocalStorage();
      syncCardSelectionStyles(qid);
      updateProgressAndNavigator();
      saveAnswerToServer(qid, optId);
    });
  });

  // Clear selection button
  document.querySelectorAll(".btn-clear-choice").forEach((btn) => {
    btn.addEventListener("click", () => {
      const qid = Number(btn.dataset.questionId);
      const radios = form.querySelectorAll(`input[name="question_${qid}"]`);
      const hadSelection = Array.from(radios).some((r) => r.checked);
      if (!hadSelection) return;
      radios.forEach((r) => (r.checked = false));
      delete localAnswers[qid];
      backupToLocalStorage();
      syncCardSelectionStyles(qid);
      updateProgressAndNavigator();
      saveAnswerToServer(qid, null);
    });
  });

  // Prev / Next buttons & Navigator pills
  document.querySelectorAll(".btn-prev-q").forEach((btn) => {
    btn.addEventListener("click", () => showQuestion(currentIndex - 1));
  });
  document.querySelectorAll(".btn-next-q").forEach((btn) => {
    btn.addEventListener("click", () => showQuestion(currentIndex + 1));
  });
  navPills.forEach((pill) => {
    pill.addEventListener("click", () => showQuestion(Number(pill.dataset.navIndex)));
  });

  // Flag for review buttons
  document.querySelectorAll(".flag-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.dataset.flagIndex);
      if (flaggedSet.has(idx)) {
        flaggedSet.delete(idx);
        btn.classList.remove("flagged");
        btn.textContent = "🚩 Đánh dấu";
      } else {
        flaggedSet.add(idx);
        btn.classList.add("flagged");
        btn.textContent = "🚩 Đã đánh dấu";
      }
      updateProgressAndNavigator();
    });
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (submitModal?.classList.contains("open") || isSubmitting) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      showQuestion(currentIndex - 1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      showQuestion(currentIndex + 1);
    } else if (["1", "2", "3", "4"].includes(e.key)) {
      const activeCard = cards[currentIndex];
      const radios = activeCard?.querySelectorAll('input[type="radio"]');
      const target = radios?.[Number(e.key) - 1];
      if (target) {
        target.checked = true;
        target.dispatchEvent(new Event("change"));
      }
    }
  });

  // Submit logic
  async function performSubmit(autoSubmitted = false) {
    if (isSubmitting) return;
    isSubmitting = true;
    clearInterval(timerInterval);
    if (submitModal) submitModal.classList.remove("open");

    const confirmBtn = document.querySelector("#confirm-submit-btn");
    if (confirmBtn) {
      confirmBtn.disabled = true;
      confirmBtn.textContent = "Đang chấm điểm...";
    }

    const answersPayload = collectAllAnswers();
    if (config.submitUrl) {
      try {
        const res = await fetch(config.submitUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({
            answers: answersPayload,
            auto_submitted: autoSubmitted,
          }),
        });
        const body = await res.json();
        if (res.ok && body?.success && body?.data?.redirect_url) {
          if (localBackupKey) {
            try { window.localStorage.removeItem(localBackupKey); } catch {}
          }
          window.location.assign(body.data.redirect_url);
          return;
        }
      } catch {}
    }
    // Fallback to standard HTML form POST
    if (localBackupKey) {
      try { window.localStorage.removeItem(localBackupKey); } catch {}
    }
    form.submit();
  }

  // Pre-submit verification modal
  function openSubmitModal() {
    const unansweredIndices = [];
    let answeredCount = 0;
    cards.forEach((card, idx) => {
      const qid = Number(card.dataset.questionId);
      if (getSelectedOptionForQuestion(qid) !== null) {
        answeredCount += 1;
      } else {
        unansweredIndices.push(idx);
      }
    });

    document.querySelector("#modal-answered-count").textContent = String(answeredCount);
    document.querySelector("#modal-unanswered-count").textContent = String(unansweredIndices.length);
    document.querySelector("#modal-flagged-count").textContent = String(flaggedSet.size);

    const unWrap = document.querySelector("#modal-unanswered-wrap");
    const unChips = document.querySelector("#modal-unanswered-chips");
    unChips.replaceChildren();
    if (unansweredIndices.length) {
      unWrap.style.display = "block";
      unansweredIndices.forEach((idx) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "jump-chip";
        chip.textContent = `Câu ${idx + 1}`;
        chip.addEventListener("click", () => {
          submitModal.classList.remove("open");
          showQuestion(idx);
        });
        unChips.append(chip);
      });
    } else {
      unWrap.style.display = "none";
    }

    const flagWrap = document.querySelector("#modal-flagged-wrap");
    const flagChips = document.querySelector("#modal-flagged-chips");
    flagChips.replaceChildren();
    if (flaggedSet.size) {
      flagWrap.style.display = "block";
      Array.from(flaggedSet)
        .sort((a, b) => a - b)
        .forEach((idx) => {
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "jump-chip";
          chip.textContent = `Câu ${idx + 1}`;
          chip.addEventListener("click", () => {
            submitModal.classList.remove("open");
            showQuestion(idx);
          });
          flagChips.append(chip);
        });
    } else {
      flagWrap.style.display = "none";
    }

    submitModal.classList.add("open");
  }

  document.querySelector("#open-submit-modal-btn")?.addEventListener("click", openSubmitModal);
  document.querySelector("#cancel-submit-btn")?.addEventListener("click", () => {
    submitModal.classList.remove("open");
  });
  submitModal?.addEventListener("click", (e) => {
    if (e.target === submitModal) submitModal.classList.remove("open");
  });
  document.querySelector("#confirm-submit-btn")?.addEventListener("click", () => performSubmit(false));

  // Countdown Timer
  function formatTime(secs) {
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return `${String(mins).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
  }

  function updateTimerDisplay() {
    if (!timerDisplay) return;
    timerDisplay.textContent = formatTime(remainingSeconds);
    if (remainingSeconds <= 60) {
      timerBadge?.classList.remove("warning");
      timerBadge?.classList.add("danger");
    } else if (remainingSeconds <= 300) {
      timerBadge?.classList.add("warning");
    }
  }

  updateTimerDisplay();
  if (remainingSeconds <= 0) {
    timeoutOverlay?.classList.add("open");
    performSubmit(true);
  } else {
    timerInterval = setInterval(() => {
      remainingSeconds -= 1;
      if (remainingSeconds <= 0) {
        remainingSeconds = 0;
        updateTimerDisplay();
        timeoutOverlay?.classList.add("open");
        performSubmit(true);
        return;
      }
      updateTimerDisplay();
    }, 1000);
  }

  updateProgressAndNavigator();
})();
