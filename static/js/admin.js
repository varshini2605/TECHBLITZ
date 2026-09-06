/**
 * TECHBLITZ Admin Dashboard Live Poller & Monitor
 */

document.addEventListener('DOMContentLoaded', () => {
  pollLiveDashboard();
  setInterval(pollLiveDashboard, 2500);
});

async function pollLiveDashboard() {
  try {
    const res = await fetch('/api/admin/live');
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success) return;

    // 1. Update Stat Counters
    const c = data.counters;
    document.getElementById('statRegistered').textContent = c.total_registered;
    document.getElementById('statTotal').textContent = c.total_candidates;
    document.getElementById('statActive').textContent = c.active;
    document.getElementById('statCompleted').textContent = c.completed;
    document.getElementById('statBlocked').textContent = c.blocked;
    document.getElementById('statFlagged').textContent = c.flagged;
    document.getElementById('statTerminated').textContent = c.terminated;

    // 2. Render Live Candidates Table
    renderCandidatesTable(data.candidates);

    // 3. Render Violation Alert Feed
    renderViolationFeed(data.violations_feed);

    // 4. Render Live Rankings
    renderRankingsTable(data.results);

  } catch (err) {
    console.error('Live polling error:', err);
  }
}

function renderCandidatesTable(candidates) {
  const tbody = document.getElementById('candidatesTableBody');
  if (!tbody) return;

  if (!candidates || candidates.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          No candidates have initiated an exam session yet.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = candidates.map(c => {
    const timeMins = Math.floor(c.remaining_seconds / 60);
    const timeSecs = c.remaining_seconds % 60;
    const timeFormatted = `${String(timeMins).padStart(2, '0')}:${String(timeSecs).padStart(2, '0')}`;

    let statusBadgeClass = 'badge-neutral';
    if (c.status === 'ACTIVE' || c.status === 'ACTIVE_AFTER_APPROVAL') statusBadgeClass = 'badge-active';
    else if (c.status === 'WARNING') statusBadgeClass = 'badge-warning';
    else if (c.status === 'BLOCKED' || c.status === 'TERMINATED') statusBadgeClass = 'badge-danger';
    else if (c.status === 'COMPLETED' || c.status === 'AUTO_SUBMITTED') statusBadgeClass = 'badge-completed';

    return `
      <tr>
        <td>
          <strong style="color: #ffffff;">${escapeHtml(c.name)}</strong>
        </td>
        <td style="font-family: var(--font-mono); font-size: 0.85rem;">
          ${escapeHtml(c.hall_ticket_number)}
        </td>
        <td>${escapeHtml(c.team_id)}</td>
        <td>
          <span style="font-weight: 600;">${c.answered_count}</span> / ${c.total_questions}
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700; color: ${c.remaining_seconds < 180 ? 'var(--danger)' : '#ffffff'};">
          ${timeFormatted}
        </td>
        <td>
          <span class="badge ${c.violations_count > 0 ? 'badge-danger' : 'badge-neutral'}">
            ${c.violations_count}
          </span>
        </td>
        <td>
          <span class="badge ${statusBadgeClass}">
            ${c.status}
          </span>
        </td>
        <td>
          <a href="/admin/candidate/${c.id}" class="btn btn-secondary btn-sm" style="font-size: 0.78rem;">
            Inspect
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

function renderViolationFeed(violations) {
  const container = document.getElementById('violationFeedContainer');
  if (!container) return;

  if (!violations || violations.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 2rem; font-size: 0.85rem;">
        No violations detected yet.
      </div>
    `;
    return;
  }

  container.innerHTML = violations.map(v => {
    return `
      <div style="background: var(--bg-input); border: 1px solid var(--border); border-left: 3px solid var(--danger); border-radius: var(--radius-sm); padding: 0.75rem; font-size: 0.82rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
          <strong style="color: var(--danger);">${escapeHtml(v.type)}</strong>
          <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">${v.timestamp ? v.timestamp.split(' ')[1] : ''}</span>
        </div>
        <div style="color: #ffffff; font-weight: 600;">
          ${escapeHtml(v.candidate_name)} (${escapeHtml(v.hall_ticket_number)})
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.4rem;">
          <span style="font-size: 0.75rem; color: var(--text-secondary);">
            Strike #${v.violation_number} • Team: ${escapeHtml(v.team_id)}
          </span>
          <a href="/admin/candidate/${v.candidate_id}" style="font-size: 0.75rem; color: var(--primary); text-decoration: none; font-weight: 700;">
            Action →
          </a>
        </div>
      </div>
    `;
  }).join('');
}

function renderRankingsTable(results) {
  const tbody = document.getElementById('rankingsTableBody');
  if (!tbody || !results) return;

  if (results.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          No completed assessments yet.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = results.slice(0, 15).map(r => `
    <tr>
      <td><strong>#${r.rank}</strong></td>
      <td><strong>${escapeHtml(r.name)}</strong></td>
      <td style="font-family: var(--font-mono);">${escapeHtml(r.hall_ticket_number)}</td>
      <td>${escapeHtml(r.team_id)}</td>
      <td><strong style="color: var(--success); font-family: var(--font-mono); font-size: 1rem;">${r.score}</strong></td>
      <td>${r.total_marks}</td>
      <td>${r.percentage}%</td>
      <td>${r.time_taken}</td>
      <td><span class="badge ${r.violations_count > 0 ? 'badge-warning' : 'badge-neutral'}">${r.violations_count}</span></td>
      <td><span class="badge badge-completed">${r.status}</span></td>
    </tr>
  `).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
