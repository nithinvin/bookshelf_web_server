/* auth.js  —  login + signup client-side validation */

(function () {

  // ── Shared helpers ──────────────────────────────────────────────────────────
  function fieldEl(id)    { return document.getElementById('field-' + id); }
  function feedbackEl(id) { return document.getElementById('fb-'    + id); }

  function setValid(id, msg) {
    var f = fieldEl(id), fb = feedbackEl(id);
    if (!f) return;
    f.classList.remove('is-invalid'); f.classList.add('is-valid');
    if (fb) fb.textContent = msg || '✓';
  }

  function setInvalid(id, msg) {
    var f = fieldEl(id), fb = feedbackEl(id);
    if (!f) return;
    f.classList.remove('is-valid'); f.classList.add('is-invalid');
    if (fb) fb.textContent = msg;
  }

  function clearState(id) {
    var f = fieldEl(id), fb = feedbackEl(id);
    if (!f) return;
    f.classList.remove('is-valid', 'is-invalid');
    if (fb) fb.textContent = '';
  }

  // Show/hide password toggle (shared by both pages)
  document.querySelectorAll('.toggle-pw').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = document.getElementById(btn.dataset.target);
      if (!target) return;
      var show = target.type === 'password';
      target.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
    });
  });


  // ── LOGIN form ──────────────────────────────────────────────────────────────
  var loginForm = document.getElementById('loginForm');
  if (loginForm) {
    var luInput = document.getElementById('username');
    var lpInput = document.getElementById('password');

    function validateLoginUsername() {
      var v = luInput.value.trim();
      if (!v) { setInvalid('username', 'Username is required.'); return false; }
      setValid('username', '✓');
      return true;
    }

    function validateLoginPassword() {
      var v = lpInput.value;
      if (!v) { setInvalid('password', 'Password is required.'); return false; }
      setValid('password', '✓');
      return true;
    }

    luInput.addEventListener('blur',  validateLoginUsername);
    lpInput.addEventListener('blur',  validateLoginPassword);
    luInput.addEventListener('input', function () { if (luInput.value.trim()) validateLoginUsername(); else clearState('username'); });
    lpInput.addEventListener('input', function () { if (lpInput.value)        validateLoginPassword(); else clearState('password'); });

    loginForm.addEventListener('submit', function (e) {
      var ok = (validateLoginUsername() & validateLoginPassword());
      if (!ok) {
        e.preventDefault();
        var first = loginForm.querySelector('.is-invalid .field-input');
        if (first) first.focus();
      }
    });
  }


  // ── SIGNUP form ─────────────────────────────────────────────────────────────
  var signupForm = document.getElementById('signupForm');
  if (signupForm) {
    var suInput  = document.getElementById('username');
    var pwInput  = document.getElementById('password');
    var cfInput  = document.getElementById('confirm');
    var pwFill   = document.getElementById('pwFill');
    var pwLabel  = document.getElementById('pwLabel');

    // Username
    function validateSUUsername() {
      var v = suInput.value.trim();
      if (!v)         { setInvalid('username', 'Username is required.');                       return false; }
      if (v.length < 3) { setInvalid('username', 'Must be at least 3 characters.');            return false; }
      if (v.length > 50) { setInvalid('username', 'Must be 50 characters or fewer.');          return false; }
      if (!/^[a-zA-Z0-9]+$/.test(v)) { setInvalid('username', 'Letters and numbers only.');   return false; }
      setValid('username', '✓ Looks good');
      return true;
    }

    // Password strength scoring (0–4)
    function scorePassword(pw) {
      var score = 0;
      if (pw.length >= 8)  score++;
      if (pw.length >= 12) score++;
      if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
      if (/[0-9]/.test(pw))  score++;
      if (/[^A-Za-z0-9]/.test(pw)) score++;
      return Math.min(score, 4);
    }

    var strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong'];

    function updateStrength(pw) {
      if (!pwFill || !pwLabel) return;
      if (!pw) {
        pwFill.className = 'pw-strength-fill s0';
        pwFill.style.width = '0%';
        pwLabel.textContent = '';
        return;
      }
      var s = scorePassword(pw);
      pwFill.className = 'pw-strength-fill s' + s;
      pwLabel.textContent = strengthLabels[s] || '';
    }

    function validatePassword() {
      var v = pwInput.value;
      updateStrength(v);
      if (!v)         { setInvalid('password', 'Password is required.');           return false; }
      if (v.length < 8) { setInvalid('password', 'Must be at least 8 characters.'); return false; }
      setValid('password', '✓ Looks good');
      if (cfInput.value) validateConfirm(); // re-check confirm when password changes
      return true;
    }

    function validateConfirm() {
      var v = cfInput.value;
      if (!v)                      { setInvalid('confirm', 'Please confirm your password.'); return false; }
      if (v !== pwInput.value)     { setInvalid('confirm', 'Passwords do not match.');       return false; }
      setValid('confirm', '✓ Passwords match');
      return true;
    }

    suInput.addEventListener('input', function () { if (suInput.value.trim()) validateSUUsername(); else clearState('username'); });
    suInput.addEventListener('blur',  validateSUUsername);

    pwInput.addEventListener('input', function () { updateStrength(pwInput.value); if (pwInput.value) validatePassword(); else clearState('password'); });
    pwInput.addEventListener('blur',  validatePassword);

    cfInput.addEventListener('input', function () { if (cfInput.value) validateConfirm(); else clearState('confirm'); });
    cfInput.addEventListener('blur',  validateConfirm);

    signupForm.addEventListener('submit', function (e) {
      var ok = (validateSUUsername() & validatePassword() & validateConfirm());
      if (!ok) {
        e.preventDefault();
        var first = signupForm.querySelector('.is-invalid .field-input');
        if (first) first.focus();
      } else {
        var btn = document.getElementById('submitBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Creating account…'; }
      }
    });
  }

}());
