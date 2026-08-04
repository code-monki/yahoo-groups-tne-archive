(function () {
  var modal = document.getElementById('attachment-modal');
  if (!modal) return;
  // Any element on the page can trigger the modal by carrying this data
  // attribute -- FR-27's per-attachment "not available" buttons (Phase 7)
  // just need to add it, no per-button wiring required here.
  document.querySelectorAll('[data-open-attachment-modal]').forEach(function (btn) {
    btn.addEventListener('click', function () { modal.showModal(); });
  });
  var closeBtn = document.getElementById('close-modal-btn');
  if (closeBtn) closeBtn.addEventListener('click', function () { modal.close(); });
})();
