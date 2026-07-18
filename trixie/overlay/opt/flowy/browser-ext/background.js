// Relay show/hide to the Flowy API, which signals wvkbd (USR1/USR2).
// Service-worker fetch with host_permissions bypasses page CORS.
chrome.runtime.onMessage.addListener((msg) => {
  if (!msg || !['show', 'hide'].includes(msg.action)) return;
  fetch('http://localhost:10000/display/browser-keyboard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: msg.action }),
  }).catch(() => {});
});
