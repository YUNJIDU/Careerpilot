const API = "http://127.0.0.1:9998/api/v1";
const sessionInput = document.querySelector("#session");
const previewButton = document.querySelector("#preview");
const fillButton = document.querySelector("#fill");
const message = document.querySelector("#message");
const result = document.querySelector("#result");
const diffBox = document.querySelector("#diff");
let currentSession = null;
let currentDiff = [];

function setMessage(value, error = false) {
  message.textContent = value;
  message.classList.toggle("error", error);
}

async function request(path, init) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `本地 API 请求失败 (${response.status})`);
  }
  return response.json();
}

function inspectForm(fields, fill) {
  const captcha = Boolean(document.querySelector([
    'iframe[src*="recaptcha" i]',
    'iframe[src*="hcaptcha" i]',
    '[class*="captcha" i]',
    '[id*="captcha" i]',
    'input[name*="captcha" i]',
  ].join(",")));
  const patterns = {
    full_name: /full.?name|姓名|名字|真实姓名|candidate.?name/i,
    email: /e.?mail|邮箱|电子邮件/i,
    phone: /phone|mobile|tel|电话|手机/i,
    location: /location|city|address|所在地|城市|地址/i,
    website: /website|portfolio|个人网站|作品集/i,
    linkedin: /linkedin/i,
  };
  const controls = [...document.querySelectorAll("input, textarea")].filter((element) => {
    const type = (element.getAttribute("type") || "text").toLowerCase();
    return !element.disabled && !element.readOnly && !["hidden", "password", "file", "submit", "button", "reset", "checkbox", "radio"].includes(type);
  });
  const used = new Set();
  const mappings = [];
  for (const [fieldKey, nextValue] of Object.entries(fields)) {
    if (!patterns[fieldKey] || !nextValue) continue;
    const match = controls.find((element) => {
      if (used.has(element)) return false;
      const label = [...(element.labels || [])].map((item) => item.textContent || "").join(" ");
      const descriptor = [
        element.getAttribute("name"), element.id, element.getAttribute("autocomplete"),
        element.getAttribute("aria-label"), element.getAttribute("placeholder"), label,
        element.getAttribute("type"),
      ].filter(Boolean).join(" ");
      return patterns[fieldKey].test(descriptor);
    });
    if (!match) continue;
    used.add(match);
    const label = [...(match.labels || [])].map((item) => item.textContent || "").join(" ")
      || match.getAttribute("aria-label") || match.getAttribute("placeholder") || match.getAttribute("name") || fieldKey;
    mappings.push({ field_key: fieldKey, label: label.slice(0, 300), current_value: match.value.slice(0, 500), next_value: nextValue });
    if (fill && !captcha) {
      const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(match), "value")?.set;
      if (setter) setter.call(match, nextValue); else match.value = nextValue;
      match.dispatchEvent(new Event("input", { bubbles: true }));
      match.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }
  return { captcha, mappings };
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url) throw new Error("无法读取当前标签页。");
  return tab;
}

async function runInspection(fill) {
  const tab = await activeTab();
  if (new URL(tab.url).origin !== currentSession.target_origin) {
    throw new Error(`当前网站与会话不匹配，应为 ${currentSession.target_origin}`);
  }
  const [{ result: inspected }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: inspectForm,
    args: [currentSession.field_values, fill],
  });
  return inspected;
}

previewButton.addEventListener("click", async () => {
  setMessage("正在本地读取会话并检查当前表单…");
  result.hidden = true;
  try {
    const id = sessionInput.value.trim();
    if (!/^[0-9a-f-]{36}$/i.test(id)) throw new Error("请输入有效的会话 ID。");
    currentSession = await request(`/prefill-sessions/${encodeURIComponent(id)}`);
    const inspected = await runInspection(false);
    currentDiff = inspected.mappings;
    diffBox.replaceChildren(...currentDiff.map((item) => {
      const article = document.createElement("article");
      const title = document.createElement("b");
      const change = document.createElement("span");
      title.textContent = item.label;
      change.textContent = `${item.current_value || "（空）"} → ${item.next_value}`;
      article.append(title, change);
      return article;
    }));
    result.hidden = false;
    fillButton.disabled = inspected.captcha || currentDiff.length === 0;
    if (inspected.captcha) {
      await request(`/prefill-sessions/${currentSession.session_id}/handoff`, {
        method: "POST",
        body: JSON.stringify({ diff: currentDiff, captcha_required: true }),
      });
      setMessage("检测到验证码。请先手工完成验证码，再重新预览；扩展没有填值。", true);
    } else {
      setMessage(currentDiff.length ? "请核对以下差异，再确认预填。" : "没有识别到可安全预填的字段。", !currentDiff.length);
    }
  } catch (error) { setMessage(String(error), true); }
});

fillButton.addEventListener("click", async () => {
  fillButton.disabled = true;
  try {
    const inspected = await runInspection(true);
    if (inspected.captcha) throw new Error("检测到验证码，已停止预填。");
    currentDiff = inspected.mappings;
    await request(`/prefill-sessions/${currentSession.session_id}/handoff`, {
      method: "POST",
      body: JSON.stringify({ diff: currentDiff, captcha_required: false }),
    });
    setMessage("字段已预填。请逐项检查，并由你手工完成最终提交。");
  } catch (error) { setMessage(String(error), true); fillButton.disabled = false; }
});
