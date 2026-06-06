/* main.js — shared across all pages */

// Auto-dismiss flash messages after 4 s
document.querySelectorAll('.flash').forEach(function (el) {
  setTimeout(function () {
    el.style.transition = 'opacity .4s ease';
    el.style.opacity = '0';
    setTimeout(function () { el.remove(); }, 400);
  }, 4000);
});

// Delete confirmation dialog
function confirmDelete(title) {
  return window.confirm('Remove "' + title + '" from your shelf?');
}
