/**
 * TECHBLITZ Candidate Examination Controller
 */

let examQuestions = [];
let currentQuestionIndex = 0;
let candidateStatusPollInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
  setupProctoringMonitoring();
  await loadExamSession();
  
  // Background polling every 2.5 seconds to sync status and timer
  candidateStatusPollInterval = setInterval(pollCandidateStatus, 2500);
});

async function loadExamSession() {
  try {
    // 1. Fetch Candidate Status and Server Timer
    const statusRes = await fetch('/api/candidate/status');
    if (!statusRes.ok) {
      window.location.href = '/';
      return;
    }
    const statusData = await statusRes.json();

    if (statusData.status === 'BLOCKED') {
      window.location.href = '/blocked';
      return;
    } else if (statusData.status === 'COMPLETED' || statusData.status === 'AUTO_SUBMITTED') {
      window.location.href = '/result';
      return;
    }

    // Initialize countdown timer
    initExamTimer(statusData.remaining_seconds);

    // Update violation badge
    const vBadge = document.getElementById('violationCountDisplay');
    if (vBadge) vBadge.textContent = statusData.violations_count;

    // 2. Fetch Questions (Without correct answers)
    const qRes = await fetch('/api/candidate/questions');
    const qData = await qRes.json();

    if (!qData.success || !qData.questions || qData.questions.length === 0) {
      alert('No questions loaded for this examination. Please contact the administrator.');
      return;
    }

    examQuestions = qData.questions;
    currentQuestionIndex = qData.current_index || 0;

    renderPalette();
    renderCurrentQuestion();

  } catch (err) {
    console.error('Failed to initialize exam:', err);
  }
}

function renderCurrentQuestion() {
  if (!examQuestions || examQuestions.length === 0) return;
  const q = examQuestions[currentQuestionIndex];
  if (!q) return;

  // Question Meta
  document.getElementById('questionNumberLabel').textContent = `Question ${currentQuestionIndex + 1} of ${examQuestions.length}`;
  document.getElementById('questionTopicBadge').textContent = q.topic || 'General';
  document.getElementById('questionDifficultyBadge').textContent = q.difficulty || 'Medium';
  document.getElementById('questionMarksLabel').textContent = q.marks;

  // Question Text
  document.getElementById('questionTextDisplay').textContent = q.question_text;

  // Render Options
  const container = document.getElementById('optionsContainer');
  container.innerHTML = '';

  const options = [
    { letter: 'A', text: q.option_a },
    { letter: 'B', text: q.option_b },
    { letter: 'C', text: q.option_c },
    { letter: 'D', text: q.option_d }
  ];

  options.forEach(opt => {
    const item = document.createElement('div');
    const isSelected = q.selected_answer === opt.letter;
    item.className = `option-item ${isSelected ? 'selected' : ''}`;
    item.onclick = () => selectOption(opt.letter);

    item.innerHTML = `
      <div class="option-letter">${opt.letter}</div>
      <div class="option-text">${escapeHtml(opt.text)}</div>
    `;
    container.appendChild(item);
  });

  // Update Nav Buttons
  document.getElementById('prevBtn').disabled = currentQuestionIndex === 0;
  const nextBtn = document.getElementById('nextBtn');
  if (currentQuestionIndex === examQuestions.length - 1) {
    nextBtn.textContent = 'Review / Finish';
    nextBtn.className = 'btn btn-secondary';
  } else {
    nextBtn.textContent = 'Next →';
    nextBtn.className = 'btn btn-primary';
  }

  updatePaletteHighlight();
}

async function selectOption(letter) {
  const q = examQuestions[currentQuestionIndex];
  if (!q) return;

  // Toggle if clicked already selected
  q.selected_answer = letter;

  // Update UI immediately
  const items = document.querySelectorAll('.option-item');
  items.forEach(el => {
    const l = el.querySelector('.option-letter').textContent;
    el.classList.toggle('selected', l === letter);
  });

  updatePaletteHighlight();

  // Save to server
  try {
    await fetch('/api/candidate/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: q.id,
        selected_answer: letter,
        current_question_index: currentQuestionIndex
      })
    });
  } catch (err) {}
}

function navigateQuestion(direction) {
  const target = currentQuestionIndex + direction;
  if (target >= 0 && target < examQuestions.length) {
    currentQuestionIndex = target;
    renderCurrentQuestion();
  }
}

function jumpToQuestion(index) {
  if (index >= 0 && index < examQuestions.length) {
    currentQuestionIndex = index;
    renderCurrentQuestion();
  }
}

function renderPalette() {
  const grid = document.getElementById('paletteGrid');
  if (!grid) return;
  grid.innerHTML = '';

  examQuestions.forEach((q, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = `paletteBtn_${idx}`;
    btn.className = 'palette-btn';
    btn.textContent = idx + 1;
    btn.onclick = () => jumpToQuestion(idx);

    if (q.selected_answer) {
      btn.classList.add('answered');
    }
    grid.appendChild(btn);
  });
}

function updatePaletteHighlight() {
  examQuestions.forEach((q, idx) => {
    const btn = document.getElementById(`paletteBtn_${idx}`);
    if (!btn) return;

    btn.className = 'palette-btn';
    if (idx === currentQuestionIndex) {
      btn.classList.add('current');
    }
    if (q.selected_answer) {
      btn.classList.add('answered');
    }
  });
}

async function confirmSubmitTest() {
  const answered = examQuestions.filter(q => q.selected_answer).length;
  const unanswered = examQuestions.length - answered;

  const msg = unanswered > 0 
    ? `You have answered ${answered} of ${examQuestions.length} questions (${unanswered} unanswered).\n\nAre you sure you want to submit your assessment?`
    : `You have answered all ${examQuestions.length} questions.\n\nSubmit your assessment now?`;

  if (confirm(msg)) {
    submitExamFinal(false);
  }
}

async function submitExamFinal(isAutoSubmit = false) {
  isExamSubmitting = true;
  if (candidateStatusPollInterval) clearInterval(candidateStatusPollInterval);

  try {
    const res = await fetch('/api/candidate/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    window.location.href = data.redirect || '/result';
  } catch (err) {
    window.location.href = '/result';
  }
}

window.submitExamFinal = submitExamFinal;

async function pollCandidateStatus() {
  if (isExamSubmitting) return;

  try {
    const res = await fetch('/api/candidate/status');
    if (!res.ok) return;
    const data = await res.json();

    if (data.status === 'BLOCKED') {
      window.location.href = '/blocked';
      return;
    } else if (data.status === 'TERMINATED' || data.status === 'COMPLETED' || data.status === 'AUTO_SUBMITTED') {
      window.location.href = '/result';
      return;
    }

    // Sync timer
    syncExamTimer(data.remaining_seconds);

    // Update violations count
    const vBadge = document.getElementById('violationCountDisplay');
    if (vBadge) vBadge.textContent = data.violations_count;

    // Check if server-side warning was activated
    if (data.warning_active && !isWarningActive) {
      showViolationWarningModal(data.latest_violation_type || 'PROCTORING_ALERT');
    }
  } catch (e) {}
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
