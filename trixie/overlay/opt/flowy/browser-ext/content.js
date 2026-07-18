// Auto show/hide the wvkbd on-screen keyboard based on text-field focus.
// The browser's own address bar is out of reach for extensions; the
// companion's toggle button covers that case.
let last = null;

function isEditable(el) {
  if (!el) return false;
  if (el.isContentEditable) return true;
  if (el.tagName === 'TEXTAREA') return true;
  if (el.tagName === 'INPUT') {
    const t = (el.type || 'text').toLowerCase();
    return !['checkbox', 'radio', 'button', 'submit', 'reset', 'range', 'color', 'file', 'image', 'hidden'].includes(t);
  }
  return false;
}

function send(action) {
  if (action === last) return;
  last = action;
  try { chrome.runtime.sendMessage({ action }); } catch { /* extension reloading */ }
}

document.addEventListener('focusin', (e) => { if (isEditable(e.target)) send('show'); }, true);
document.addEventListener('focusout', () => {
  // Small delay: focus often hops between fields; only hide when nothing
  // editable ends up focused.
  setTimeout(() => { if (!isEditable(document.activeElement)) send('hide'); }, 200);
}, true);
