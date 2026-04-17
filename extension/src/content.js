function extractPageText() {
  const article = document.querySelector("article");
  const source = article || document.body;
  const text = (source?.innerText || "").replace(/\s+/g, " ").trim();
  return text.slice(0, 120000);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "GET_PAGE_CONTENT") {
    sendResponse({
      ok: true,
      payload: {
        url: window.location.href,
        title: document.title || "",
        content: extractPageText()
      }
    });
    return true;
  }
  return false;
});
