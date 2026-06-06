/* form.js — client-side validation + live star rating preview */

(function () {
  var form       = document.getElementById('bookForm');
  var submitBtn  = document.getElementById('submitBtn');
  if (!form) return;

  // ── Field references ──────────────────────────────────────
  var titleInput  = document.getElementById('title');
  var authorInput = document.getElementById('author');
  var yearInput   = document.getElementById('year');
  var ratingInput = document.getElementById('rating');
  var starFill    = document.getElementById('starFill');
  var cntTitle    = document.getElementById('cnt-title');

  var currentYear = new Date().getFullYear();

  // ── Helpers ───────────────────────────────────────────────
  function fieldEl(id)   { return document.getElementById('field-' + id); }
  function feedbackEl(id){ return document.getElementById('fb-' + id); }

  function setValid(id, msg) {
    var field = fieldEl(id);
    var fb    = feedbackEl(id);
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    fb.textContent = msg || '✓ Looks good';
  }

  function setInvalid(id, msg) {
    var field = fieldEl(id);
    var fb    = feedbackEl(id);
    field.classList.remove('is-valid');
    field.classList.add('is-invalid');
    fb.textContent = msg;
  }

  function clearState(id) {
    var field = fieldEl(id);
    var fb    = feedbackEl(id);
    field.classList.remove('is-valid', 'is-invalid');
    fb.textContent = '';
  }

  // ── Validators ────────────────────────────────────────────
  function validateTitle() {
    var val = titleInput.value.trim();
    cntTitle.textContent = val.length;
    if (!val) { setInvalid('title', 'Title is required.'); return false; }
    if (val.length < 1) { setInvalid('title', 'Title is too short.'); return false; }
    setValid('title', '✓ Title looks good');
    return true;
  }

  function validateAuthor() {
    var val = authorInput.value.trim();
    if (!val) { setInvalid('author', 'Author is required.'); return false; }
    setValid('author', '✓ Author looks good');
    return true;
  }

  function validateYear() {
    var val = yearInput.value.trim();
    if (!val) { setInvalid('year', 'Publication year is required.'); return false; }
    var n = parseInt(val, 10);
    if (isNaN(n) || n < 1 || n > 2100) {
      setInvalid('year', 'Enter a year between 1 and 2100.');
      return false;
    }
    if (n > currentYear + 5) {
      setInvalid('year', 'That year seems far in the future.');
      return false;
    }
    setValid('year', '✓ Year is valid');
    return true;
  }

  function validateRating() {
    var val = ratingInput.value.trim();
    if (val === '') {
      clearState('rating');
      updateStars(0);
      return true; // optional field
    }
    var n = parseFloat(val);
    if (isNaN(n) || n < 0 || n > 5) {
      setInvalid('rating', 'Rating must be between 0.0 and 5.0.');
      updateStars(0);
      return false;
    }
    // Round to 1 decimal for display
    var rounded = Math.round(n * 10) / 10;
    setValid('rating', '✓ ' + rounded.toFixed(1) + ' / 5.0');
    updateStars(n);
    return true;
  }

  // ── Live star preview ─────────────────────────────────────
  function updateStars(value) {
    if (!starFill) return;
    var pct = Math.min(Math.max(value / 5 * 100, 0), 100);
    starFill.style.setProperty('--pct', pct.toFixed(1) + '%');
  }

  // Initialise stars from pre-filled value (edit page)
  if (ratingInput.value) updateStars(parseFloat(ratingInput.value));

  // ── Live listeners (validate on input, not just submit) ───
  titleInput.addEventListener('input', function () {
    cntTitle.textContent = titleInput.value.trim().length;
    if (titleInput.value.trim()) validateTitle();
    else clearState('title');
  });
  titleInput.addEventListener('blur', validateTitle);

  authorInput.addEventListener('input', function () {
    if (authorInput.value.trim()) validateAuthor();
    else clearState('author');
  });
  authorInput.addEventListener('blur', validateAuthor);

  yearInput.addEventListener('input', function () {
    if (yearInput.value.trim()) validateYear();
    else clearState('year');
  });
  yearInput.addEventListener('blur', validateYear);

  ratingInput.addEventListener('input', validateRating);
  ratingInput.addEventListener('blur', validateRating);

  // ── Submit — full validation pass ────────────────────────
  form.addEventListener('submit', function (e) {
    var ok = validateTitle() & validateAuthor() & validateYear() & validateRating();
    // using & (not &&) so ALL validators run and all errors are shown at once
    if (!ok) {
      e.preventDefault();
      // Scroll to first invalid field
      var firstInvalid = form.querySelector('.is-invalid .field-input');
      if (firstInvalid) {
        firstInvalid.focus();
        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    // Prevent double-submit
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving…';
  });
}());
