/**
 * TECHBLITZ Registration Drag-and-Drop, Preview, and Access Control
 */

let currentPreviewData = null;
let currentTempFilePath = null;
let currentOriginalFilename = null;
let searchDebounceTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
  setupDragAndDrop();
  loadRegistrations();
});

// ---------------------------------------------------------
// DRAG AND DROP HANDLING
// ---------------------------------------------------------

function setupDragAndDrop() {
  const zone = document.getElementById('regDropZone');
  if (!zone) return;

  ['dragenter', 'dragover'].forEach(eventName => {
    zone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    zone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove('dragover');
    });
  });

  zone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      uploadRegistrationFile(files[0]);
    }
  });
}

function handleFileSelected(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    uploadRegistrationFile(files[0]);
  }
}

async function uploadRegistrationFile(file, customColumnMap = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (customColumnMap) {
    formData.append('column_map', JSON.stringify(customColumnMap));
  }

  showToast('Processing uploaded registration file...', 'info');

  try {
    const res = await fetch('/api/admin/registrations/upload-preview', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      alert(data.error || 'Failed to process file');
      return;
    }

    currentTempFilePath = data.temp_file_path;
    currentOriginalFilename = data.original_filename;

    if (data.needs_mapping) {
      openMappingModal(data.headers, data.detected_map, file);
      return;
    }

    showImportPreview(data);

  } catch (err) {
    alert('Error uploading registration file: ' + err.message);
  }
}

function showImportPreview(data) {
  currentPreviewData = data;

  const card = document.getElementById('importPreviewCard');
  card.style.display = 'block';

  document.getElementById('prevTotalCount').textContent = data.total_rows;
  document.getElementById('prevValidCount').textContent = data.valid_count;
  document.getElementById('prevInvalidCount').textContent = data.invalid_count;
  document.getElementById('prevDupCount').textContent = data.duplicate_count;

  // Show duplicate options if duplicates exist
  const dupBox = document.getElementById('duplicateHandlingBox');
  if (data.duplicate_count > 0) {
    dupBox.style.display = 'block';
  } else {
    dupBox.style.display = 'none';
  }

  // Populate preview rows
  const tbody = document.getElementById('previewTableBody');
  const previewRows = [...data.valid_records, ...data.invalid_records].slice(0, 50);

  tbody.innerHTML = previewRows.map(r => `
    <tr style="${!r.is_valid ? 'background: rgba(239, 68, 68, 0.1);' : ''}">
      <td>#${r.row_number}</td>
      <td style="font-family: var(--font-mono);">${escapeHtml(r.hall_ticket_number || '--')}</td>
      <td><strong>${escapeHtml(r.name || '--')}</strong></td>
      <td>${escapeHtml(r.team_id || '--')}</td>
      <td>${escapeHtml(r.email || '--')}</td>
      <td>
        ${r.is_valid 
          ? `<span class="badge badge-active">✓ Valid ${r.is_db_duplicate ? '(DB Duplicate)' : ''}</span>`
          : `<span class="badge badge-danger">✗ ${escapeHtml(r.errors.join(', '))}</span>`
        }
      </td>
    </tr>
  `).join('');

  card.scrollIntoView({ behavior: 'smooth' });
}

function cancelImportPreview() {
  currentPreviewData = null;
  document.getElementById('importPreviewCard').style.display = 'none';
  document.getElementById('regFileInput').value = '';
}

async function confirmImport() {
  if (!currentPreviewData) return;

  const dupMode = document.querySelector('input[name="dupMode"]:checked')?.value || 'skip';
  const btn = document.getElementById('confirmImportBtn');
  btn.disabled = true;
  btn.textContent = 'Importing records...';

  try {
    const res = await fetch('/api/admin/registrations/confirm-import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        records: currentPreviewData.all_valid_records,
        temp_file_path: currentTempFilePath,
        original_filename: currentOriginalFilename,
        duplicate_mode: dupMode
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.error || 'Import failed');
      btn.disabled = false;
      btn.textContent = '[ CONFIRM IMPORT ]';
      return;
    }

    showToast(`Successfully imported: ${data.imported} added, ${data.updated} updated, ${data.skipped} skipped.`, 'success');
    cancelImportPreview();
    loadRegistrations();

  } catch (e) {
    alert('Import failed: ' + e.message);
    btn.disabled = false;
    btn.textContent = '[ CONFIRM IMPORT ]';
  }
}

// ---------------------------------------------------------
// COLUMN MAPPING MODAL
// ---------------------------------------------------------

let pendingUploadFile = null;

function openMappingModal(headers, detected, file) {
  pendingUploadFile = file;
  const modal = document.getElementById('mappingModal');

  ['mapHallTicket', 'mapName', 'mapTeamId', 'mapEmail'].forEach(id => {
    const select = document.getElementById(id);
    select.innerHTML = '<option value="">-- Select Column --</option>' + 
      headers.map((h, idx) => `<option value="${idx}">${escapeHtml(h)} (Col ${idx + 1})</option>`).join('');
  });

  if (detected.hall_ticket !== null) document.getElementById('mapHallTicket').value = detected.hall_ticket;
  if (detected.name !== null) document.getElementById('mapName').value = detected.name;
  if (detected.team_id !== null) document.getElementById('mapTeamId').value = detected.team_id;
  if (detected.email !== null) document.getElementById('mapEmail').value = detected.email;

  modal.style.display = 'flex';
}

function closeMappingModal() {
  document.getElementById('mappingModal').style.display = 'none';
  pendingUploadFile = null;
}

function applyColumnMapping() {
  const ht = document.getElementById('mapHallTicket').value;
  const name = document.getElementById('mapName').value;
  const team = document.getElementById('mapTeamId').value;
  const email = document.getElementById('mapEmail').value;

  if (ht === '' || name === '' || team === '') {
    alert('Please assign Hall Ticket Number, Name, and Team ID columns.');
    return;
  }

  const columnMap = {
    hall_ticket: parseInt(ht),
    name: parseInt(name),
    team_id: parseInt(team),
    email: email !== '' ? parseInt(email) : null
  };

  const fileToUpload = pendingUploadFile;
  closeMappingModal();
  if (fileToUpload) {
    uploadRegistrationFile(fileToUpload, columnMap);
  }
}

// ---------------------------------------------------------
// REGISTRATION DATABASE CRUD
// ---------------------------------------------------------

async function loadRegistrations() {
  const search = document.getElementById('searchRegInput').value.trim();
  const team = document.getElementById('teamFilterSelect').value;
  const status = document.getElementById('statusFilterSelect').value;

  let url = `/api/admin/registrations?search=${encodeURIComponent(search)}&team=${encodeURIComponent(team)}&status=${encodeURIComponent(status)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    if (!data.success) return;

    // Update Team Filter Dropdown
    const teamSelect = document.getElementById('teamFilterSelect');
    const curTeam = teamSelect.value;
    teamSelect.innerHTML = '<option value="">All Teams</option>' + 
      data.teams.map(t => `<option value="${escapeHtml(t)}" ${t === curTeam ? 'selected' : ''}>${escapeHtml(t)}</option>`).join('');

    renderRegistrationsTable(data.registrations);

  } catch (err) {
    console.error('Error loading registrations:', err);
  }
}

function renderRegistrationsTable(records) {
  const tbody = document.getElementById('registrationTableBody');
  if (!tbody) return;

  if (!records || records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          No registration records found. Drag and drop a spreadsheet above to import.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = records.map(r => `
    <tr id="regRow_${r.id}">
      <td style="font-family: var(--font-mono); font-weight: 700; color: #ffffff;">
        ${escapeHtml(r.hall_ticket_number)}
      </td>
      <td><strong>${escapeHtml(r.name)}</strong></td>
      <td>
        <span class="badge badge-neutral">${escapeHtml(r.team_id)}</span>
      </td>
      <td style="font-size: 0.82rem; color: var(--text-secondary);">${escapeHtml(r.email || '--')}</td>
      <td>
        <button type="button" onclick="toggleStatus(${r.id}, '${r.status}')" class="badge ${r.status === 'ACTIVE' ? 'badge-active' : 'badge-blocked'}" style="cursor: pointer; border: none;">
          ${r.status}
        </button>
      </td>
      <td style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(r.source_file)}</td>
      <td style="font-size: 0.78rem; font-family: var(--font-mono);">${r.imported_at || '--'}</td>
      <td>
        <div style="display: flex; gap: 0.4rem;">
          <button type="button" onclick="openEditModal(${r.id}, '${escapeHtml(r.hall_ticket_number)}', '${escapeHtml(r.name)}', '${escapeHtml(r.team_id)}', '${escapeHtml(r.email || '')}', '${r.status}')" class="btn btn-secondary btn-sm">Edit</button>
          <button type="button" onclick="deleteRegistration(${r.id})" class="btn btn-danger btn-sm">Del</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function debounceSearch() {
  clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(loadRegistrations, 350);
}

// ---------------------------------------------------------
// MANUAL ADD / EDIT MODAL
// ---------------------------------------------------------

function openManualAddModal() {
  document.getElementById('regModalTitle').textContent = 'Add Registration';
  document.getElementById('editRegId').value = '';
  document.getElementById('mHallTicket').value = '';
  document.getElementById('mHallTicket').disabled = false;
  document.getElementById('mName').value = '';
  document.getElementById('mTeamId').value = '';
  document.getElementById('mEmail').value = '';
  document.getElementById('mStatus').value = 'ACTIVE';
  document.getElementById('registrationModal').style.display = 'flex';
}

function openEditModal(id, ht, name, team, email, status) {
  document.getElementById('regModalTitle').textContent = 'Edit Registration';
  document.getElementById('editRegId').value = id;
  document.getElementById('mHallTicket').value = ht;
  document.getElementById('mHallTicket').disabled = true; // Hall ticket cannot be changed once created
  document.getElementById('mName').value = name;
  document.getElementById('mTeamId').value = team;
  document.getElementById('mEmail').value = email;
  document.getElementById('mStatus').value = status;
  document.getElementById('registrationModal').style.display = 'flex';
}

function closeRegistrationModal() {
  document.getElementById('registrationModal').style.display = 'none';
}

async function saveRegistration() {
  const regId = document.getElementById('editRegId').value;
  const payload = {
    hall_ticket_number: document.getElementById('mHallTicket').value.trim(),
    name: document.getElementById('mName').value.trim(),
    team_id: document.getElementById('mTeamId').value.trim(),
    email: document.getElementById('mEmail').value.trim(),
    status: document.getElementById('mStatus').value
  };

  if (!payload.hall_ticket_number || !payload.name || !payload.team_id) {
    alert('Hall Ticket Number, Name, and Team ID are all required.');
    return;
  }

  const url = regId ? `/api/admin/registrations/${regId}` : '/api/admin/registrations';
  const method = regId ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.error || 'Failed to save registration');
      return;
    }
    showToast('Registration saved successfully', 'success');
    closeRegistrationModal();
    loadRegistrations();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function toggleStatus(id, currentStatus) {
  const newStatus = currentStatus === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  try {
    const res = await fetch(`/api/admin/registrations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    const data = await res.json();
    if (!data.success) {
      alert(data.error || 'Failed to toggle status');
      return;
    }
    showToast(`Status changed to ${newStatus}`, 'info');
    loadRegistrations();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function deleteRegistration(id) {
  if (!confirm('Are you sure you want to delete this candidate registration?')) return;
  try {
    const res = await fetch(`/api/admin/registrations/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!data.success) {
      alert(data.error || 'Failed to delete');
      return;
    }
    showToast('Registration deleted', 'success');
    document.getElementById(`regRow_${id}`)?.remove();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
