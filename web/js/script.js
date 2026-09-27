const API_BASE = (typeof window !== 'undefined' && window.location) ? window.location.origin : '';
const LAST_EMAIL_KEY = 'aqoneLastEmail';

function showMessage(message, isError = false) {
  if (isError) {
    console.error(message);
  }
  if (typeof alert === 'function') {
    alert(message);
  }
}

async function postJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || 'Request failed');
  }

  return data;
}

function fillSavedEmail() {
  const savedEmail = sessionStorage.getItem(LAST_EMAIL_KEY);
  const emailField = document.getElementById('email');

  if (emailField && savedEmail) {
    emailField.value = savedEmail;
  }
}

async function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById('email')?.value.trim() || '';
  const password = document.getElementById('password')?.value || '';

  if (!email || !password) {
    showMessage('Please enter your email and password.');
    return;
  }

  try {
    const result = await postJson('/api/login', { email, password });
    sessionStorage.setItem(LAST_EMAIL_KEY, email);
    sessionStorage.removeItem('aqoneDemoBypassActive');
    sessionStorage.removeItem('aqoneDashboardMode');
    sessionStorage.removeItem('aqoneTutorialLesson');
    if (result.token) {
      sessionStorage.setItem('aqoneToken', result.token);
    }
    // The dashboard attributes sea-condition entries to the signed-in account
    // rather than a hardcoded operator name.
    if (result.user) {
      sessionStorage.setItem('aqoneUser', JSON.stringify(result.user));
    }
    window.location.href = 'dashboard.html';
  } catch (error) {
    showMessage(error.message, true);
  }
}

// No account needed: the tutorial (docs/72) replays practice data and never
// calls the API, so it works at a venue without a login or a signal.
function startTutorial(event) {
  event.preventDefault();
  sessionStorage.setItem('aqoneDashboardMode', 'tutorial');
  sessionStorage.setItem('aqoneTutorialLesson', 'console');
  window.location.href = 'dashboard.html';
}

// There is no public sign-up. Dashboard accounts are created by an
// administrator through html/admin-signup.html, which requires a server-side
// setup key and is handled by js/admin-signup.js.

function initAuthForms() {
  fillSavedEmail();

  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }

  const tutorialBtn = document.getElementById('tutorial-btn');
  if (tutorialBtn) {
    tutorialBtn.addEventListener('click', startTutorial);
  }
}

if (typeof window !== 'undefined' && window.addEventListener) {
  window.addEventListener('DOMContentLoaded', initAuthForms);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    handleLogin: handleLogin,
    startTutorial: startTutorial,
    postJson: postJson
  };
}
