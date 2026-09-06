/**
 * TECHBLITZ Dual Timer Manager
 * 1. Main Examination Server-Synced Countdown
 * 2. 20-Second Violation Acknowledgement Countdown
 */

let examRemainingSeconds = 0;
let examTimerInterval = null;

let warningRemainingSeconds = 20;
let warningTimerInterval = null;

function initExamTimer(initialSeconds) {
  examRemainingSeconds = initialSeconds;
  updateExamTimerDisplay();
  
  if (examTimerInterval) clearInterval(examTimerInterval);
  
  examTimerInterval = setInterval(() => {
    if (examRemainingSeconds > 0) {
      examRemainingSeconds--;
      updateExamTimerDisplay();
    } else {
      clearInterval(examTimerInterval);
      onExamTimerZero();
    }
  }, 1000);
}

function updateExamTimerDisplay() {
  const display = document.getElementById('timeRemainingDisplay');
  const box = document.getElementById('timerBox');
  if (!display) return;

  const minutes = Math.floor(examRemainingSeconds / 60);
  const seconds = examRemainingSeconds % 60;
  const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  display.textContent = formatted;

  // Visual urgency alert when under 3 minutes
  if (examRemainingSeconds <= 180 && box) {
    box.classList.add('timer-danger');
  }
}

function syncExamTimer(serverSeconds) {
  // Resync with server if clock drifted by > 3 seconds
  if (Math.abs(examRemainingSeconds - serverSeconds) > 3) {
    examRemainingSeconds = serverSeconds;
    updateExamTimerDisplay();
  }
}

function onExamTimerZero() {
  showToast('Time expired! Automatically submitting assessment...', 'danger');
  if (window.submitExamFinal) {
    window.submitExamFinal(true); // true = auto submit
  }
}

// ---------------------------------------------------------
// 20-SECOND VIOLATION TIMER
// ---------------------------------------------------------

function start20SecWarningCountdown(onExpiredCallback) {
  warningRemainingSeconds = 20;
  updateWarningDisplay();

  if (warningTimerInterval) clearInterval(warningTimerInterval);

  warningTimerInterval = setInterval(() => {
    warningRemainingSeconds--;
    updateWarningDisplay();

    if (warningRemainingSeconds <= 0) {
      clearInterval(warningTimerInterval);
      if (onExpiredCallback) onExpiredCallback();
    }
  }, 1000);
}

function stop20SecWarningCountdown() {
  if (warningTimerInterval) {
    clearInterval(warningTimerInterval);
    warningTimerInterval = null;
  }
}

function updateWarningDisplay() {
  const display = document.getElementById('warningCountdownDisplay');
  if (display) {
    display.textContent = warningRemainingSeconds;
  }
}
