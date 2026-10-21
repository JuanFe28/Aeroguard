// Escape values at HTML sinks, including quoted attributes. Do not alter API data.
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

export function safeColor(value) {
  return /^#[0-9a-f]{6}$/i.test(value || '') ? value : '#ef4444';
}
