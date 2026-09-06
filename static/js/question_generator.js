/**
 * TECHBLITZ Question Generator & Review Controller
 */

let currentGeneratedBatch = [];

function checkCustomTopic(val) {
  const customGroup = document.getElementById('customTopicGroup');
  if (val === '__custom__') {
    customGroup.style.display = 'block';
    document.getElementById('customTopicInput').required = true;
  } else {
    customGroup.style.display = 'none';
    document.getElementById('customTopicInput').required = false;
  }
}

async function handleGenerateQuestions(e) {
  e.preventDefault();
  const btn = document.getElementById('generateSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Generating Questions...';

  let topic = document.getElementById('topicSelect').value;
  if (topic === '__custom__') {
    topic = document.getElementById('customTopicInput').value.trim() || 'General';
  }

  const payload = {
    topic,
    difficulty: document.getElementById('difficultySelect').value,
    count: document.getElementById('questionCount').value,
    marks: document.getElementById('marksPerQuestion').value,
    instructions: document.getElementById('generatorInstructions').value.trim()
  };

  try {
    const res = await fetch('/api/admin/questions/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.error || 'Failed to generate questions');
      btn.disabled = false;
      btn.textContent = '⚡ GENERATE QUESTIONS';
      return;
    }

    currentGeneratedBatch = data.questions;
    renderReviewCards();

    btn.disabled = false;
    btn.textContent = '⚡ GENERATE QUESTIONS';

    const reviewSection = document.getElementById('reviewContainer');
    reviewSection.style.display = 'block';
    reviewSection.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert('Generation error: ' + err.message);
    btn.disabled = false;
    btn.textContent = '⚡ GENERATE QUESTIONS';
  }
}

function renderReviewCards() {
  const list = document.getElementById('reviewCardsList');
  if (!list) return;

  if (currentGeneratedBatch.length === 0) {
    list.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">All questions removed from this batch.</div>`;
    return;
  }

  list.innerHTML = currentGeneratedBatch.map((q, idx) => `
    <div class="card" id="reviewCard_${idx}" style="border-left: 4px solid var(--primary); padding: 1.5rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <span style="font-weight: 800; color: var(--accent-cyan); font-size: 1rem;">
          Question #${idx + 1}
        </span>
        <button type="button" onclick="removeReviewedQuestion(${idx})" class="btn btn-danger btn-sm">
          Remove
        </button>
      </div>

      <div class="form-group">
        <label class="form-label">Question Text *</label>
        <textarea class="form-control" id="revQText_${idx}" required>${escapeHtml(q.question_text)}</textarea>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label class="form-label">Option A *</label>
          <input type="text" class="form-control" id="revOptA_${idx}" value="${escapeHtml(q.option_a)}" required>
        </div>
        <div class="form-group">
          <label class="form-label">Option B *</label>
          <input type="text" class="form-control" id="revOptB_${idx}" value="${escapeHtml(q.option_b)}" required>
        </div>
        <div class="form-group">
          <label class="form-label">Option C *</label>
          <input type="text" class="form-control" id="revOptC_${idx}" value="${escapeHtml(q.option_c)}" required>
        </div>
        <div class="form-group">
          <label class="form-label">Option D *</label>
          <input type="text" class="form-control" id="revOptD_${idx}" value="${escapeHtml(q.option_d)}" required>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label class="form-label">Correct Answer *</label>
          <select class="form-control" id="revCorrect_${idx}">
            <option value="A" ${q.correct_answer === 'A' ? 'selected' : ''}>Option A</option>
            <option value="B" ${q.correct_answer === 'B' ? 'selected' : ''}>Option B</option>
            <option value="C" ${q.correct_answer === 'C' ? 'selected' : ''}>Option C</option>
            <option value="D" ${q.correct_answer === 'D' ? 'selected' : ''}>Option D</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Marks *</label>
          <input type="number" class="form-control" id="revMarks_${idx}" step="0.5" min="0.5" value="${q.marks}">
        </div>

        <div class="form-group">
          <label class="form-label">Topic</label>
          <input type="text" class="form-control" id="revTopic_${idx}" value="${escapeHtml(q.topic)}">
        </div>

        <div class="form-group">
          <label class="form-label">Difficulty</label>
          <select class="form-control" id="revDiff_${idx}">
            <option value="Easy" ${q.difficulty === 'Easy' ? 'selected' : ''}>Easy</option>
            <option value="Medium" ${q.difficulty === 'Medium' ? 'selected' : ''}>Medium</option>
            <option value="Hard" ${q.difficulty === 'Hard' ? 'selected' : ''}>Hard</option>
          </select>
        </div>
      </div>

      <div class="form-group" style="margin-bottom: 0;">
        <label class="form-label">Explanation (Optional)</label>
        <textarea class="form-control" id="revExpl_${idx}" style="min-height: 60px;">${escapeHtml(q.explanation || '')}</textarea>
      </div>
    </div>
  `).join('');
}

function removeReviewedQuestion(index) {
  currentGeneratedBatch.splice(index, 1);
  renderReviewCards();
}

async function saveReviewedQuestions() {
  if (!currentGeneratedBatch || currentGeneratedBatch.length === 0) {
    alert('No questions in batch to save.');
    return;
  }

  const testId = document.getElementById('targetTestSelect').value;
  if (!testId) {
    alert('Please select a target test.');
    return;
  }

  // Harvest edited values from review cards
  const finalQuestions = [];
  for (let i = 0; i < currentGeneratedBatch.length; i++) {
    const qText = document.getElementById(`revQText_${i}`)?.value.trim();
    const optA = document.getElementById(`revOptA_${i}`)?.value.trim();
    const optB = document.getElementById(`revOptB_${i}`)?.value.trim();
    const optC = document.getElementById(`revOptC_${i}`)?.value.trim();
    const optD = document.getElementById(`revOptD_${i}`)?.value.trim();
    const correct = document.getElementById(`revCorrect_${i}`)?.value;
    const marks = document.getElementById(`revMarks_${i}`)?.value;
    const topic = document.getElementById(`revTopic_${i}`)?.value.trim();
    const diff = document.getElementById(`revDiff_${i}`)?.value;
    const expl = document.getElementById(`revExpl_${i}`)?.value.trim();

    if (!qText || !optA || !optB || !optC || !optD) {
      alert(`Question #${i + 1} has incomplete fields.`);
      return;
    }

    finalQuestions.push({
      question_text: qText,
      option_a: optA,
      option_b: optB,
      option_c: optC,
      option_d: optD,
      correct_answer: correct,
      marks: parseFloat(marks) || 1.0,
      topic: topic || 'General',
      difficulty: diff || 'Medium',
      explanation: expl || ''
    });
  }

  const btn = document.getElementById('saveBatchBtn');
  btn.disabled = true;
  btn.textContent = 'Saving to test...';

  try {
    const res = await fetch('/api/admin/questions/batch-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        test_id: testId,
        questions: finalQuestions
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.error || 'Failed to save questions');
      btn.disabled = false;
      btn.textContent = '💾 SAVE QUESTIONS TO TEST';
      return;
    }

    alert(data.message || 'Questions saved to test successfully!');
    window.location.href = `/admin/questions?test_id=${testId}`;

  } catch (err) {
    alert('Error saving questions: ' + err.message);
    btn.disabled = false;
    btn.textContent = '💾 SAVE QUESTIONS TO TEST';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
