const summarizeBtn = document.getElementById("summarizeBtn");
const outputEl = document.getElementById("output");
const statusEl = document.getElementById("status");
const modeEl = document.getElementById("mode");

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

function setStatus(text) {
  statusEl.textContent = text;
}

function appendOutput(text) {
  outputEl.textContent += `${text}\n\n`;
}

function clearOutput() {
  outputEl.textContent = "";
}

async function getPagePayload(tabId) {
  const response = await chrome.tabs.sendMessage(tabId, { type: "GET_PAGE_CONTENT" });
  if (!response?.ok || !response?.payload) {
    throw new Error("Could not extract page content.");
  }
  return response.payload;
}

function isRestrictedUrl(url) {
  if (!url) return true;
  return (
    url.startsWith("edge://") ||
    url.startsWith("chrome://") ||
    url.startsWith("about:") ||
    url.startsWith("file://")
  );
}

async function getPagePayloadWithInjection(tab) {
  if (!tab?.id) {
    throw new Error("No active tab found.");
  }
  if (isRestrictedUrl(tab.url)) {
    throw new Error("Open a normal website page (http/https), not browser internal pages.");
  }

  try {
    return await getPagePayload(tab.id);
  } catch (error) {
    if (!String(error?.message || "").includes("Receiving end does not exist")) {
      throw error;
    }

    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["src/content.js"]
    });
    return getPagePayload(tab.id);
  }
}

async function getBackendConfig() {
  const data = await chrome.storage.local.get(["backendUrl", "summaryMode"]);
  return {
    backendUrl: data.backendUrl || "ws://localhost:8000/ws/summarize",
    summaryMode: data.summaryMode || "short"
  };
}

async function saveMode(mode) {
  await chrome.storage.local.set({ summaryMode: mode });
}

async function runSummarization() {
  summarizeBtn.disabled = true;
  clearOutput();
  setStatus("Collecting page content...");

  try {
    const tab = await getActiveTab();
    const page = await getPagePayloadWithInjection(tab);
    if (!page.content || page.content.length < 200) {
      throw new Error("Page content is too short to summarize.");
    }

    const { backendUrl } = await getBackendConfig();
    const ws = new WebSocket(backendUrl);

    ws.onopen = () => {
      setStatus("Connected. Summarizing...");
      ws.send(
        JSON.stringify({
          ...page,
          mode: modeEl.value
        })
      );
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.event === "progress") {
        setStatus(msg.message);
      } else if (msg.event === "partial") {
        appendOutput(`Partial: ${msg.data?.text || ""}`);
      } else if (msg.event === "done") {
        setStatus("Done");
        clearOutput();
        appendOutput(msg.data?.summary || "");
      } else if (msg.event === "error") {
        setStatus("Failed");
        appendOutput(`Error: ${msg.data?.reason || "Unknown error"}`);
      }
    };

    ws.onerror = () => {
      setStatus("Connection error");
      appendOutput("WebSocket connection failed. Is backend running on localhost:8000?");
    };

    ws.onclose = () => {
      summarizeBtn.disabled = false;
    };
  } catch (error) {
    summarizeBtn.disabled = false;
    setStatus("Failed");
    appendOutput(`Error: ${error.message}`);
  }
}

modeEl.addEventListener("change", async () => {
  await saveMode(modeEl.value);
});

document.addEventListener("DOMContentLoaded", async () => {
  const { summaryMode } = await getBackendConfig();
  modeEl.value = summaryMode;
});

summarizeBtn.addEventListener("click", runSummarization);
