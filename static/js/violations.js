/**
 * TECHBLITZ Browser Proctoring & 20-Second Warning Protocol
 */

let lastViolationType = null;
let lastViolationTime = 0;
let isWarningActive = false;
let isExamSubmitting = false;

function setupProctoringMonitoring() {
  // 1. Page Visibility (Tab Switch Detection)
  document.addEventListener('visibilitychange', () => {
    if (isExamSubmitting) return;
    if (document.hidden) {
      triggerBrowserViolation('TAB_SWITCH', 'User navigated away or switched browser tabs');
    }
  });

  // 2. Window Blur (Leaving exam window / switching applications)
  window.addEventListener('blur', () => {
    if (isExamSubmitting) return;
    triggerBrowserViolation('WINDOW_BLUR', 'Test window lost focus');
  });

  // 3. Fullscreen Exit Detection
  document.addEventListener('fullscreenchange', () => {
    if (isExamSubmitting) return;
    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
      triggerBrowserViolation('FULLSCREEN_EXIT', 'Candidate exited fullscreen mode');
    }
  });

  // 4. Copy, Cut, Paste Prevention
  document.addEventListener('copy', (e) => {
    e.preventDefault();
    triggerBrowserViolation('COPY_ATTEMPT', 'Candidate attempted to copy test content');
  });

  document.addEventListener('cut', (e) => {
    e.preventDefault();
    triggerBrowserViolation('CUT_ATTEMPT', 'Candidate attempted to cut test content');
  });

  document.addEventListener('paste', (e) => {
    e.preventDefault();
    triggerBrowserViolation('PASTE_ATTEMPT', 'Candidate attempted to paste content');
  });

  // 5. Right Click Context Menu Prevention
  document.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    triggerBrowserViolation('RIGHT_CLICK', 'Context menu / right-click attempted');
  });

  // 6. Keyboard Shortcuts Prevention (Ctrl/Cmd + C, V, X, A, F12)
  document.addEventListener('keydown', (e) => {
    const isModifier = e.ctrlKey || e.metaKey;
    const key = e.key ? e.key.toLowerCase() : '';

    if (isModifier && ['c', 'v', 'x', 'u', 's'].includes(key)) {
      e.preventDefault();
      triggerBrowserViolation('KEYBOARD_SHORTCUT', `Shortcut Ctrl/Cmd+${key.toUpperCase()} blocked`);
    }

    if (e.key === 'F12' || (isModifier && e.shiftKey && ['i', 'j', 'c'].includes(key))) {
      e.preventDefault();
      triggerBrowserViolation('DEVTOOLS_ATTEMPT', 'Developer tools inspection attempt');
    }
  });
}

function triggerBrowserViolation(type, message) {
  if (isExamSubmitting || isWarningActive) return;

  const now = Date.now();
  // 1.5-second debounce for duplicate event spam
  if (type === lastViolationType && (now - lastViolationTime) < 1500) {
    return;
  }

  lastViolationType = type;
  lastViolationTime = now;

  // Log to server immediately
  fetch('/api/candidate/violations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, metadata: { reason: message } })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      // Update badge display
      const counterEl = document.getElementById('violationCountDisplay');
      if (counterEl) {
        counterEl.textContent = data.violation_count;
      }

      // Check if server set status to BLOCKED immediately (e.g. 3rd strike)
      if (data.status === 'BLOCKED') {
        window.location.href = '/blocked';
        return;
      }

      // Show 20-Second Warning Modal
      showViolationWarningModal(type);
    }
  })
  .catch(() => {});
}

function showViolationWarningModal(type) {
  isWarningActive = true;
  
  const modal = document.getElementById('violationWarningModal');
  const label = document.getElementById('warningViolationLabel');
  if (modal) {
    if (label) label.textContent = formatViolationTitle(type);
    modal.style.display = 'flex';
  }

  // Start 20-second countdown
  start20SecWarningCountdown(() => {
    // 20 Seconds Expired without acknowledgement!
    onWarningTimeoutExpired();
  });
}

function formatViolationTitle(type) {
  switch (type) {
    case 'TAB_SWITCH': return 'TAB SWITCH DETECTED';
    case 'WINDOW_BLUR': return 'WINDOW FOCUS LOST';
    case 'FULLSCREEN_EXIT': return 'FULLSCREEN EXITED';
    case 'COPY_ATTEMPT': return 'COPY ATTEMPT BLOCKED';
    case 'PASTE_ATTEMPT': return 'PASTE ATTEMPT BLOCKED';
    case 'CUT_ATTEMPT': return 'CUT ATTEMPT BLOCKED';
    case 'RIGHT_CLICK': return 'RIGHT CLICK RESTRICTED';
    default: return `${type.replace('_', ' ')} DETECTED`;
  }
}

async function handleAcknowledgeWarning() {
  stop20SecWarningCountdown();

  try {
    const res = await fetch('/api/candidate/acknowledge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();

    if (!data.success || data.status === 'BLOCKED') {
      // Exceeded 20 seconds or blocked
      window.location.href = '/blocked';
      return;
    }

    // Successfully acknowledged within 20s
    closeViolationModal();
  } catch (e) {
    closeViolationModal();
  }
}

function closeViolationModal() {
  isWarningActive = false;
  const modal = document.getElementById('violationWarningModal');
  if (modal) modal.style.display = 'none';

  // Request fullscreen again if exited
  try {
    const elem = document.documentElement;
    if (!document.fullscreenElement && elem.requestFullscreen) {
      elem.requestFullscreen().catch(() => {});
    }
  } catch (e) {}
}

async function onWarningTimeoutExpired() {
  // 20 seconds elapsed without clicking OK
  showToast('Violation warning not acknowledged within 20 seconds! Test blocked.', 'danger');
  
  try {
    await fetch('/api/candidate/status'); // Triggers server-side auto-block check
  } catch (e) {}

  setTimeout(() => {
    window.location.href = '/blocked';
  }, 500);
}
