const byId = (id) => document.getElementById(id);
const resultBox = byId("result");
const settingIds = ["check-mode", "actor-id", "api-token"];

async function loadSettings() {
  const settings = await chrome.storage.local.get({ "check-mode": "local", "actor-id": "", "api-token": "" });
  for (const id of settingIds) byId(id).value = settings[id] || "";
  byId("hosted-settings").hidden = settings["check-mode"] !== "hosted";
}

for (const id of settingIds) {
  byId(id).addEventListener("change", async () => {
    await chrome.storage.local.set({ [id]: byId(id).value });
    byId("hosted-settings").hidden = byId("check-mode").value !== "hosted";
  });
}
loadSettings();

function infer(text, title) {
  const content = `${title}\n${text}`.slice(0, 12000);
  const barcode = content.match(/\b(?:UPC|EAN|GTIN|barcode)\s*[:#-]?\s*(\d{8,14})\b/i)?.[1]
    || content.match(/\b(\d{12})\b/)?.[1] || "";
  const brand = content.match(/\bbrand\s*[:#-]\s*([^\n,;]{2,60})/i)?.[1]?.trim() || "";
  const model = content.match(/\b(?:model|model\s*(?:number|no\.?))\s*[:#-]\s*([A-Z0-9][A-Z0-9._/-]{2,30})/i)?.[1]?.trim() || "";
  const product_name = title.trim().slice(0, 200);
  return { barcode, brand, model, product_name };
}

byId("read-page").addEventListener("click", async () => {
  resultBox.hidden = false;
  resultBox.textContent = "Reading the current tab…";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !/^https?:/.test(tab.url || "")) throw new Error("Open a product page in this tab first.");
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({ title: document.title, text: document.body?.innerText?.slice(0, 12000) || "" })
    });
    const values = infer(result.text, result.title);
    for (const key of ["barcode", "brand", "model"]) if (values[key]) byId(key).value = values[key];
    if (values.product_name && !byId("product-name").value) byId("product-name").value = values.product_name;
    resultBox.textContent = Object.values(values).some(Boolean)
      ? "Found some item details. Review them, then check item."
      : "No clear barcode, brand or model found. Enter the details and check item.";
  } catch (error) {
    resultBox.textContent = error.message || "Could not read this tab.";
  }
});

function itemInput() {
  const item = {
    barcode: byId("barcode").value.trim(),
    brand: byId("brand").value.trim(),
    model: byId("model").value.trim(),
    product_name: byId("product-name").value.trim()
  };
  const yearText = byId("year").value.trim();
  if (yearText) item.year = Number(yearText);
  return item;
}

function renderResult(payload) {
  resultBox.replaceChildren();
  const verdict = document.createElement("strong");
  verdict.textContent = payload.message || payload.outcome || payload.result || "uncertain — please check";
  resultBox.append(verdict);
  const date = document.createElement("p");
  date.textContent = `checked ${payload.checked_at || ""}`;
  resultBox.append(date);
  const matches = payload.matches || payload.recalls || [];
  for (const recall of matches) {
    const link = document.createElement("a");
    link.href = recall.url || recall.official_url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = `official notice: ${recall.recall_id || recall.recall_number || "recall"} — ${recall.title || ""}`;
    resultBox.append(link);
  }
  if (payload.detail) {
    const detail = document.createElement("p");
    detail.textContent = payload.detail;
    resultBox.append(detail);
  }
  if (payload.sources_checked) {
    const status = document.createElement("p");
    status.textContent = Object.entries(payload.sources_checked)
      .map(([name, value]) => `${name}: ${value.status}${value.message ? ` (${value.message})` : ""}`)
      .join(" · ");
    resultBox.append(status);
  }
}

byId("check").addEventListener("click", async () => {
  resultBox.hidden = false;
  const hosted = byId("check-mode").value === "hosted";
  resultBox.textContent = hosted ? "Checking public recall sources with Apify…" : "Checking local recall data…";
  try {
    const item = itemInput();
    let response;
    if (hosted) {
      const actorId = byId("actor-id").value.trim();
      const token = byId("api-token").value.trim();
      if (!actorId || !token) throw new Error("Enter your Apify Actor ID and API token in hosted Actor settings.");
      response = await fetch(`https://api.apify.com/v2/acts/${encodeURIComponent(actorId)}/run-sync-dataset?timeout=300`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(item)
      });
    } else {
      response = await fetch("http://127.0.0.1:8765/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item })
      });
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || payload.message || (hosted ? "Apify Actor request failed." : "Local API request failed."));
    renderResult(hosted ? (Array.isArray(payload) ? payload[0] || {} : payload) : payload);
  } catch (error) {
    resultBox.textContent = hosted
      ? (error.message || "Could not reach the Apify Actor.")
      : `${error.message || "Could not reach the recall API."} Start Glacier's local recall API and try again.`;
  }
});
