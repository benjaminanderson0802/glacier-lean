const byId = (id) => document.getElementById(id);
const resultBox = byId("result");

function infer(text, title) {
  const content = `${title}\n${text}`.slice(0, 12000);
  const barcode = content.match(/\b(?:UPC|EAN|GTIN|barcode)\s*[:#-]?\s*(\d{8,14})\b/i)?.[1]
    || content.match(/\b(\d{12})\b/)?.[1] || "";
  const brand = content.match(/\bbrand\s*[:#-]\s*([^\n,;]{2,60})/i)?.[1]?.trim() || "";
  const model = content.match(/\b(?:model|model\s*(?:number|no\.?))\s*[:#-]\s*([A-Z0-9][A-Z0-9._/-]{2,30})/i)?.[1]?.trim() || "";
  return { barcode, brand, model };
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
    resultBox.textContent = Object.values(values).some(Boolean)
      ? "Found some item details. Review them, then check item."
      : "No clear barcode, brand or model found. Enter the details and check item.";
  } catch (error) {
    resultBox.textContent = error.message || "Could not read this tab.";
  }
});

byId("check").addEventListener("click", async () => {
  resultBox.hidden = false;
  resultBox.textContent = "Checking local recall data…";
  try {
    const response = await fetch("http://127.0.0.1:8765/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item: { barcode: byId("barcode").value.trim(), brand: byId("brand").value.trim(), model: byId("model").value.trim() } })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Local API request failed.");
    resultBox.replaceChildren();
    const verdict = document.createElement("strong");
    verdict.textContent = payload.result;
    resultBox.append(verdict);
    const date = document.createElement("p");
    date.textContent = `checked ${payload.checked_at || ""}`;
    resultBox.append(date);
    for (const recall of payload.recalls || []) {
      const link = document.createElement("a");
      link.href = recall.official_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = `official notice: ${recall.recall_number} — ${recall.title}`;
      resultBox.append(link);
    }
    if (payload.detail) {
      const detail = document.createElement("p");
      detail.textContent = payload.detail;
      resultBox.append(detail);
    }
  } catch (error) {
    resultBox.textContent = `${error.message || "Could not reach the recall API."} Start Glacier's local recall API and try again.`;
  }
});
