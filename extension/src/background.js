chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    backendUrl: "ws://localhost:8000/ws/summarize",
    summaryMode: "short"
  });
});
