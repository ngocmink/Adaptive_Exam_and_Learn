(() => {
  const tokenElement = document.querySelector('meta[name="csrf-token"]');
  const form = document.querySelector("#login-form, #register-form");
  const notice = document.querySelector("#notice");
  if (!form || !notice) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    notice.textContent = "";

    const values = Object.fromEntries(new FormData(form).entries());
    let endpoint;
    let payload;

    if (form.id === "login-form") {
      endpoint = "/api/auth/login";
      payload = { email: values.email, password: values.password };
    } else {
      if (values.password !== values.confirm_password) {
        notice.textContent = "Hai mật khẩu chưa khớp.";
        return;
      }
      endpoint = "/api/auth/register";
      payload = {
        email: values.email,
        password: values.password,
        full_name: values.rname,
        phone: values.phone,
        study_type: values.study_type || "",
      };
    }

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": tokenElement?.content || "",
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        notice.textContent = result.message || "Không thể xử lý yêu cầu.";
        return;
      }

      if (form.id === "login-form") {
        window.location.assign(result.data.redirect_url);
      } else {
        notice.textContent = "Đăng ký thành công. Đang chuyển đến trang đăng nhập…";
        window.location.assign("/login");
      }
    } catch {
      notice.textContent = "Không kết nối được máy chủ. Hãy thử lại.";
    }
  });
})();
