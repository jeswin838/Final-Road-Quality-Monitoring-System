// ═══════════════════════════════════════════════════════════════════════════
// main.js — Common utilities shared across all pages
// ═══════════════════════════════════════════════════════════════════════════

// ── Sidebar toggle ──────────────────────────────────────────────────────────
const toggle = document.getElementById('sidebarToggle');
const overlay = document.getElementById('sidebarOverlay');

if (toggle) {
  toggle.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      document.body.classList.toggle('sidebar-open');
    } else {
      document.body.classList.toggle('sidebar-collapsed');
    }
  });
}

if (overlay) {
  overlay.addEventListener('click', () => {
    document.body.classList.remove('sidebar-open');
  });
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768
    && !e.target.closest('.sidebar')
    && !e.target.closest('#sidebarToggle')) {
    document.body.classList.remove('sidebar-open');
  }
});

// ── Toast notification ──────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 5000) {
  const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', info: 'fa-circle-info', warning: 'fa-triangle-exclamation' };
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }
  
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <i class="fa-solid ${icons[type] || icons.info}"></i>
    <div class="toast-content">${message}</div>
    <button class="toast-close">&times;</button>
    <div class="toast-progress"></div>
  `;
  container.appendChild(toast);
  
  // Reflow to ensure animation triggers
  toast.offsetHeight;
  toast.classList.add('show');
  
  const progress = toast.querySelector('.toast-progress');
  if(progress) {
    progress.style.transition = `width ${duration}ms linear`;
    progress.style.width = '0%';
  }
  
  let timeoutId;
  const closeToast = () => {
    toast.classList.remove('show');
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 300);
  };
  
  toast.querySelector('.toast-close').addEventListener('click', () => {
    clearTimeout(timeoutId);
    closeToast();
  });
  
  timeoutId = setTimeout(closeToast, duration);
}

// ── Custom Modals (Replacements for alert, confirm, prompt) ─────────────────

function createCustomModalContainer() {
  let container = document.getElementById('customModalContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'customModalContainer';
    container.className = 'custom-modal-overlay';
    document.body.appendChild(container);
  }
  return container;
}

function customAlert(message, type = 'info') {
  return new Promise((resolve) => {
    const container = createCustomModalContainer();
    const modal = document.createElement('div');
    modal.className = `custom-modal-box type-${type}`;
    const icon = type === 'error' ? 'fa-circle-xmark' : type === 'success' ? 'fa-circle-check' : 'fa-circle-info';
    modal.innerHTML = `
      <div class="custom-modal-icon"><i class="fa-solid ${icon}"></i></div>
      <div class="custom-modal-message">${message}</div>
      <div class="custom-modal-actions">
        <button class="btn btn-primary custom-modal-ok">OK</button>
      </div>
    `;
    container.appendChild(modal);
    container.style.display = 'flex';
    
    const cleanup = () => {
      modal.remove();
      if (container.childNodes.length === 0) container.style.display = 'none';
      resolve();
    };
    
    modal.querySelector('.custom-modal-ok').addEventListener('click', cleanup);
  });
}

function customConfirm(message) {
  return new Promise((resolve) => {
    const container = createCustomModalContainer();
    const modal = document.createElement('div');
    modal.className = `custom-modal-box type-warning`;
    modal.innerHTML = `
      <div class="custom-modal-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
      <div class="custom-modal-message">${message}</div>
      <div class="custom-modal-actions">
        <button class="btn btn-secondary custom-modal-cancel">Cancel</button>
        <button class="btn btn-primary custom-modal-ok">Confirm</button>
      </div>
    `;
    container.appendChild(modal);
    container.style.display = 'flex';
    
    const cleanup = (result) => {
      modal.remove();
      if (container.childNodes.length === 0) container.style.display = 'none';
      resolve(result);
    };
    
    modal.querySelector('.custom-modal-ok').addEventListener('click', () => cleanup(true));
    modal.querySelector('.custom-modal-cancel').addEventListener('click', () => cleanup(false));
  });
}

function customPrompt(message, defaultValue = '') {
  return new Promise((resolve) => {
    const container = createCustomModalContainer();
    const modal = document.createElement('div');
    modal.className = `custom-modal-box type-info`;
    modal.innerHTML = `
      <div class="custom-modal-message" style="text-align: left; margin-bottom: 10px;">${message}</div>
      <input type="text" class="form-input custom-modal-input" value="${defaultValue}" />
      <div class="custom-modal-actions" style="margin-top: 15px;">
        <button class="btn btn-secondary custom-modal-cancel">Cancel</button>
        <button class="btn btn-primary custom-modal-ok">OK</button>
      </div>
    `;
    container.appendChild(modal);
    container.style.display = 'flex';
    
    const input = modal.querySelector('.custom-modal-input');
    input.focus();
    
    const cleanup = (isOk) => {
      const val = isOk ? input.value : null;
      modal.remove();
      if (container.childNodes.length === 0) container.style.display = 'none';
      resolve(val);
    };
    
    modal.querySelector('.custom-modal-ok').addEventListener('click', () => cleanup(true));
    modal.querySelector('.custom-modal-cancel').addEventListener('click', () => cleanup(false));
  });
}

// ── Assign Modal ────────────────────────────────────────────────────────────
const assignModal = document.getElementById('assignModal');
const deleteModal = document.getElementById('deleteModal');

function openAssignModal(potholeId, currentStatus = 'Pending Repair') {
  document.getElementById('assignPotholeId').value = potholeId;
  document.getElementById('assignWorkerName').value = '';
  document.getElementById('assignNotes').value = '';
  
  const workerGroup = document.getElementById('workerNameGroup');
  const statusGroup = document.getElementById('statusGroup');
  const notesGroup = document.getElementById('notesGroup');
  
  if (currentStatus === 'Pending Repair' || currentStatus === 'Pending') {
      workerGroup.style.display = 'block';
      notesGroup.style.display = 'block';
      statusGroup.style.display = 'none';
      document.getElementById('assignModal').dataset.mode = 'assign';
  } else {
      workerGroup.style.display = 'none';
      notesGroup.style.display = 'none';
      statusGroup.style.display = 'block';
      document.getElementById('assignStatus').value = currentStatus;
      document.getElementById('assignModal').dataset.mode = 'update';
  }
  
  if (assignModal) assignModal.style.display = 'flex';
}

function openDeleteModal(targetId, type = 'pothole') {
  document.getElementById('deleteTargetId').value = targetId;
  document.getElementById('deleteModal').dataset.type = type;
  if (deleteModal) deleteModal.style.display = 'flex';
}

function closeDeleteModal() {
  if (deleteModal) deleteModal.style.display = 'none';
}

async function confirmGlobalDelete() {
  const modal = document.getElementById('deleteModal');
  const type = modal.dataset.type || 'pothole';
  const tid = document.getElementById('deleteTargetId').value;

  const endpoint = type === 'pothole' ? `/api/pothole/${tid}` : `/api/assignments/${tid}`;

  try {
    const res = await fetch(endpoint, { method: 'DELETE' });
    if (res.ok) {
      showToast(`${type.charAt(0).toUpperCase() + type.slice(1)} removed ✓`, 'info');
      closeDeleteModal();
      if (typeof loadTable === 'function') loadTable();
      if (typeof loadAssignments === 'function') loadAssignments();
    } else {
      showToast('Action failed', 'error');
    }
  } catch (e) {
    showToast('Connection error', 'error');
  }
}

['closeAssignModal', 'closeAssignModal2'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('click', () => assignModal.style.display = 'none');
});

const confirmAssignBtn = document.getElementById('confirmAssign');
if (confirmAssignBtn) {
  confirmAssignBtn.addEventListener('click', async () => {
    const pid = document.getElementById('assignPotholeId').value;
    const mode = document.getElementById('assignModal').dataset.mode || 'assign';
    
    let res, d;
    if (mode === 'assign') {
        const name = document.getElementById('assignWorkerName').value.trim();
        const notes = document.getElementById('assignNotes').value;
        if (!name) { showToast('Enter worker name', 'error'); return; }
        res = await fetch('/api/assignments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hazard_id: pid, worker_name: name, notes })
        });
    } else {
        const status = document.getElementById('assignStatus').value;
        res = await fetch(`/api/assignments/pothole/${pid}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status })
        });
    }
    
    d = await res.json();
    if (res.ok) {
      showToast('Maintenance status updated ✓', 'success');
      assignModal.style.display = 'none';
      if (typeof fetchDashboardData === 'function') fetchDashboardData();
    } else {
      showToast(d.error || 'Error', 'error');
    }
  });
}

// ── Formatting helpers ──────────────────────────────────────────────────────
function formatDate(s) {
  if (!s) return '—';
  const d = new Date(s);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function severityBadge(s) {
  const cls = s === 'High' ? 'badge-danger' : s === 'Medium' ? 'badge-warning' : 'badge-success';
  return `<span class="badge ${cls}">${s || '—'}</span>`;
}

function statusBadge(s) {
  const cls = s === 'Fixed' ? 'badge-success' : s === 'In Progress' ? 'badge-info' : s === 'Assigned' ? 'badge-primary' : 'badge-warning';
  return `<span class="badge ${cls}">${s || 'Pending Repair'}</span>`;
}

// ── Sidebar active state ────────────────────────────────────────────────────
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.getAttribute('href') === currentPath) {
    link.classList.add('active');
  }
});

// ── Load user info ──────────────────────────────────────────────────────────
(async () => {
  try {
    const res = await fetch('/api/me');
    if (res.ok) {
      const u = await res.json();
      const el = document.getElementById('sidebar-user');
      if (el) el.textContent = u.name || 'User';
    }
  } catch (_) { }
})();
