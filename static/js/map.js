// ═══════════════════════════════════════════════════════════════════════════
// map.js — Leaflet map with clustering, heatmap, severity markers, auto-refresh
// ═══════════════════════════════════════════════════════════════════════════

/* MAP_SETTINGS is injected by dashboard.html */
const defaultSettings = window.MAP_SETTINGS || { lat: 20.5937, lon: 78.9629, zoom: 13, refresh: 5 };

// ── Init map ────────────────────────────────────────────────────────────────
const map = L.map('map', {
  center:          [defaultSettings.lat, defaultSettings.lon],
  zoom:            defaultSettings.zoom,
  zoomControl:     true,
  attributionControl: true,
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19,
}).addTo(map);

// ── State ───────────────────────────────────────────────────────────────────
let markerClusterGroup = L.markerClusterGroup({ maxClusterRadius: 50, disableClusteringAtZoom: 17 });
let allData            = [];
let userReports        = [];
let showClusters       = true;
let refreshTimer       = null;
let autoRefreshInterval= null;
let isLoadingMarkers   = false;
let activeFilters      = { severity: '', status: '', confidence: 0 };
let userMarker         = null;
let firstLoad           = true;

map.addLayer(markerClusterGroup);

// ── Geolocation ─────────────────────────────────────────────────────────────
function initGeolocation() {
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        
        // Basic sanity check
        if (Math.abs(lat) < 0.1 && Math.abs(lon) < 0.1) return;

        map.setView([lat, lon], 14);
        userMarker = L.circleMarker([lat, lon], { radius: 10, color: '#6366f1', fillOpacity: 0.7 })
          .addTo(map).bindPopup('My Location').openPopup();
      }, 
      (err) => {
        console.warn("GPS unavailable on init", err);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }
}

function locateMe() {
  if ('geolocation' in navigator) {
    if (typeof showToast === 'function') showToast('Getting your location...', 'info', 2000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        
        if (Math.abs(lat) < 0.1 && Math.abs(lon) < 0.1) {
          if (typeof showToast === 'function') showToast('Low accuracy GPS data. Please try again.', 'warning');
          return;
        }

        map.setView([lat, lon], 16);
        if (userMarker) {
          userMarker.setLatLng([lat, lon]);
          userMarker.openPopup();
        } else {
          userMarker = L.circleMarker([lat, lon], { radius: 10, color: '#6366f1', fillOpacity: 0.7 })
            .addTo(map).bindPopup('My Location').openPopup();
        }
        if (typeof showToast === 'function') showToast('Located ✓', 'success');
      },
      (err) => {
        let msg = "Geolocation failed: " + err.message;
        if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
           msg = "Secure connection (HTTPS) required for GPS.";
        }
        if (typeof showToast === 'function') showToast(msg, 'error');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  } else {
    if (typeof showToast === 'function') showToast('Location not supported', 'warning');
  }
}

// ── Marker icons ─────────────────────────────────────────────────────────────
function makeIcon(severity, isUserReport = false) {
  const sev = (severity || '').toLowerCase();
  const colors = { critical: '#DC2626', high: '#ef4444', medium: '#f97316', low: '#22c55e' };
  const color  = isUserReport ? '#3b82f6' : (colors[sev] || '#6366f1');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="24" height="32">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 8 12 20 12 20S24 20 24 12C24 5.4 18.6 0 12 0z" fill="${color}" stroke="#fff" stroke-width="1.5"/>
    <circle cx="12" cy="12" r="5" fill="#fff" opacity="0.9"/>
  </svg>`;
  return L.divIcon({
    html: svg,
    className: '',
    iconSize:   [24, 32],
    iconAnchor: [12, 32],
    popupAnchor:[0, -32],
  });
}

// ── Build popup ──────────────────────────────────────────────────────────────
function buildPopup(r) {
  const img = r.image_url
    ? `<img src="${r.image_url}" onerror="this.onerror=null;this.outerHTML='<div style=\\'width:100%;height:80px;background:#1c2128;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#ef4444;margin-bottom:10px\\'><i class=\\'fa-solid fa-image-slash fa-2x\\'></i></div>';" style="width:100%;height:140px;object-fit:cover;border-radius:8px;margin-bottom:10px;cursor:pointer"
            onclick="window.open('${r.image_url}','_blank')"/>`
    : `<div style="width:100%;height:80px;background:#1c2128;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#7d8590;margin-bottom:10px"><i class="fa-solid fa-image fa-2x"></i></div>`;
  const sevLower = (r.severity || '').toLowerCase();
  const sevColor = sevLower === 'critical' ? '#DC2626' : sevLower === 'high' ? '#ef4444' : sevLower === 'medium' ? '#f97316' : '#22c55e';
  const stsColor = r.status   === 'Fixed'? '#22c55e' : r.status === 'In Progress' ? '#3b82f6' : '#f59e0b';
  const conf     = Math.round((r.confidence || 0) * 100);
  return `
  <div style="min-width:220px;font-family:Inter,sans-serif;font-size:13px;color:#e6edf3">
    ${img}
    <div style="display:grid;gap:5px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <strong style="font-size:14px">Pothole #${r.id}</strong>
        <span style="background:${sevColor}22;color:${sevColor};padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">${r.severity || '—'}</span>
      </div>
      <div style="color:#7d8590;font-size:11px"><i class="fa-solid fa-map-pin"></i> ${parseFloat(r.latitude).toFixed(5)}, ${parseFloat(r.longitude).toFixed(5)}</div>
      <div style="color:#7d8590;font-size:11px"><i class="fa-solid fa-clock"></i> ${r.created_at ? new Date(r.created_at).toLocaleString() : '—'}</div>
      <div style="display:flex;gap:8px;align-items:center;margin-top:2px">
        <span style="background:${stsColor}22;color:${stsColor};padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">${r.status || 'Pending'}</span>
        <span style="font-size:11px;color:#7d8590">Type: ${r.type || '—'}</span>
        ${r.report_count > 1 ? `<span style="font-size:11px;color:var(--accent);font-weight:600"><i class="fa-solid fa-users"></i> ${r.report_count} reports</span>` : ''}
      </div>
      <div>
        <div style="background:#161b22;border-radius:4px;height:5px;overflow:hidden;margin:4px 0">
          <div style="height:100%;width:${conf}%;background:${conf>=75?'#22c55e':conf>=50?'#f59e0b':'#ef4444'};border-radius:4px"></div>
        </div>
        <span style="font-size:11px;color:#7d8590">Confidence: ${conf}%</span>
      </div>
      <div style="display:flex;gap:6px;margin-top:6px">
        <button onclick="markFixedFromMap(${r.id})"
          style="flex:1;padding:5px;background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.3);border-radius:6px;cursor:pointer;font-size:11px">
          ✓ Mark Fixed
        </button>
        <button onclick="openAssignModal(${r.id})"
          style="flex:1;padding:5px;background:rgba(99,102,241,.15);color:#6366f1;border:1px solid rgba(99,102,241,.3);border-radius:6px;cursor:pointer;font-size:11px">
          + Assign
        </button>
      </div>
    </div>
  </div>`;
}

function buildUserReportPopup(r) {
  const media = r.type === 'video'
    ? `<video src="${r.media_url}" controls style="width:100%;border-radius:8px;margin-bottom:10px"></video>`
    : `<img src="${r.media_url}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;margin-bottom:10px;cursor:pointer" onclick="window.open('${r.media_url}','_blank')"/>`;
  
  return `
  <div style="min-width:220px;font-family:Inter,sans-serif;font-size:13px;color:#e6edf3">
    ${media}
    <div style="display:grid;gap:5px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <strong style="font-size:14px">User Report</strong>
        <span style="background:#3b82f622;color:#3b82f6;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">PENDING</span>
      </div>
      <div style="color:#7d8590;font-size:11px"><i class="fa-solid fa-map-pin"></i> ${parseFloat(r.latitude).toFixed(5)}, ${parseFloat(r.longitude).toFixed(5)}</div>
      <div style="color:#7d8590;font-size:11px"><i class="fa-solid fa-clock"></i> ${new Date(r.created_at).toLocaleString()}</div>
      <div style="margin-top:5px; padding:8px; background:#161b22; border-radius:6px; font-style:italic">
        "${r.description || 'No description provided'}"
      </div>
    </div>
  </div>`;
}

// ── Build premium popup (redesigned) ─────────────────────────────────────
function buildPremiumPopup(r, lat, lon, isUserReport) {
  // Image Carousel
  const images = (r.all_images && r.all_images.length > 0) ? r.all_images : (r.image ? [r.image] : []);
  
  let heroMedia = '';
  if (images.length === 0) {
    heroMedia = `<div class="popup-hero-placeholder"><i class="fa-solid fa-road-circle-exclamation"></i></div>`;
  } else if (images.length === 1) {
    heroMedia = `<img class="popup-hero-img" src="${images[0]}" alt="Pothole detection"
                     onclick="window.open('${images[0]}','_blank')"
                     onerror="this.onerror=null;this.outerHTML='<div class=\\'popup-hero-placeholder\\'><i class=\\'fa-solid fa-image-slash\\'></i></div>'"/>`;
  } else {
    // Basic CSS carousel (horizontal scroll)
    const slides = images.map(img => `
      <img src="${img}" style="width:100%; height:140px; object-fit:cover; flex-shrink:0; cursor:pointer;" onclick="window.open('${img}','_blank')"/>
    `).join('');
    heroMedia = `
      <div style="display:flex; overflow-x:auto; width:100%; height:140px; scroll-snap-type: x mandatory;">
        ${slides.replace(/<img/g, '<img style="scroll-snap-align: start; width:100%; height:140px; object-fit:cover; flex-shrink:0; cursor:pointer;"')}
      </div>
      <div style="text-align:center; font-size:10px; color:#aaa; margin-top:4px;">Swipe to see ${images.length} images</div>
    `;
  }

  // Severity badge class
  const sevLower = (r.severity || 'medium').toLowerCase();
  const sevClass = {
    critical: 'popup-sev-critical',
    high:     'popup-sev-high',
    medium:   'popup-sev-medium',
    low:      'popup-sev-low'
  }[sevLower] || 'popup-sev-medium';

  // Status chip class
  const statusRaw = (r.status || 'Pending');
  const statusLower = statusRaw.toLowerCase().replace(/\s+/g, '');
  const statusClass = {
    pending:    'popup-status-pending',
    inprogress: 'popup-status-inprogress',
    fixed:      'popup-status-fixed'
  }[statusLower] || 'popup-status-pending';

  // Info rows
  const lastSeen = r.last_reported_at || r.created_at ? new Date(r.last_reported_at || r.created_at).toLocaleString() : '—';
  
  const descRow = isUserReport && r.description
    ? `<div class="popup-info-row">
        <span class="info-label"><i class="fa-solid fa-comment"></i> Note</span>
        <span class="info-value" style="max-width:160px;text-overflow:ellipsis;overflow:hidden;white-space:nowrap" title="${r.description}">${r.description}</span>
      </div>`
    : '';

  const verifiedBadge = r.status !== 'pending' && r.status !== 'rejected' 
    ? `<span style="background:rgba(34,197,94,0.1); color:#22c55e; padding:4px 8px; border-radius:12px; font-size:10px; font-weight:600;"><i class="fa-solid fa-shield-check"></i> Verified by Admin</span>`
    : '';

  // Action buttons
  const markFixedBtn = !isUserReport
    ? `<button class="popup-btn popup-btn-success" onclick="markFixedFromMap(${r.id})">
        <i class="fa-solid fa-circle-check"></i> Mark as Fixed
      </button>`
    : '';

  return `
    ${heroMedia}
    <div class="popup-body">
      <div class="popup-header-row" style="margin-bottom:8px;">
        <span class="popup-title">${isUserReport ? 'User Report' : `Pothole #${r.id}`}</span>
        <span class="popup-sev-badge ${sevClass}">${(r.severity || 'Medium').toUpperCase()}</span>
      </div>
      
      <div style="margin-bottom:12px;">${verifiedBadge}</div>

      <div class="popup-info-section">
        <div class="popup-info-row">
          <span class="info-label"><i class="fa-solid fa-clock"></i> Last Seen</span>
          <span class="info-value">${lastSeen}</span>
        </div>
        <div class="popup-info-row">
          <span class="info-label"><i class="fa-solid fa-bullseye"></i> Status</span>
          <span class="popup-status-chip ${statusClass}">${statusRaw}</span>
        </div>
        <div class="popup-info-row">
          <span class="info-label"><i class="fa-solid fa-satellite-dish"></i> Source</span>
          <span class="info-value">${r.source || (isUserReport ? 'Citizen' : 'AI Detection')}</span>
        </div>
        ${descRow}
      </div>

      <div class="popup-actions">
        <button class="popup-btn popup-btn-primary" onclick="showReports('${r.marker_id}')">
          <i class="fa-solid fa-images"></i> View Reports
        </button>
        ${markFixedBtn}
      </div>
    </div>`;
}

// ── Load & render markers ────────────────────────────────────────────────
async function loadMarkers() {
  if (isLoadingMarkers) return;
  isLoadingMarkers = true;

  try {
    const container = map.getContainer();
    let spinner = document.getElementById('map-spinner');
    if(!spinner && container) {
      spinner = document.createElement('div');
      spinner.id = 'map-spinner';
      spinner.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size:24px;color:#6366f1"></i>';
      spinner.style.cssText = 'position:absolute;top:15px;right:15px;z-index:9999;background:var(--card-bg);padding:10px;border-radius:50%;box-shadow:0 4px 12px rgba(0,0,0,0.5);display:none;';
      container.appendChild(spinner);
    }
    if (spinner) spinner.style.display = 'block';

    try {
      const res = await fetch('/api/alerts');
      allData = await res.json();
      userReports = []; // No longer needed separately
    } catch (e) {
      console.error('Map fetch error', e);
      if (spinner) spinner.style.display = 'none';
      return;
    }
    
    if (spinner) spinner.style.display = 'none';
    renderMarkers();
    updateStats();
    
    // Update alerts panel using the same data to save API calls
    if (typeof pollAlerts === 'function') {
      pollAlerts(allData);
    }

    if (firstLoad) {
      focusTargetReport();
      firstLoad = false;
    }
  } finally {
    isLoadingMarkers = false;
  }
}

function focusTargetReport() {
  const urlParams = new URLSearchParams(window.location.search);
  const targetReportId = urlParams.get('report_id');
  const targetMarkerId = urlParams.get('marker_id');
  
  if (!targetReportId && !targetMarkerId) return;
  if (!allData || allData.length === 0) return;

  let targetGroup = null;

  for (let group of allData) {
     if (targetMarkerId && group.marker_id === targetMarkerId) {
         targetGroup = group;
         break;
     }
     if (targetReportId && group.reports) {
         if (group.reports.some(r => String(r.id) === String(targetReportId))) {
             targetGroup = group;
             break;
         }
     }
  }

  if (targetGroup) {
      const lat = parseFloat(targetGroup.latitude);
      const lon = parseFloat(targetGroup.longitude);
      
      map.flyTo([lat, lon], 18, { animate: true, duration: 1.5 });
      
      setTimeout(() => {
          let foundLayer = null;
          markerClusterGroup.eachLayer(layer => {
              if (layer.options && layer.options.marker_id === targetGroup.marker_id) {
                  foundLayer = layer;
              }
          });
          
          if (foundLayer) {
              markerClusterGroup.zoomToShowLayer(foundLayer, () => {
                  foundLayer.openPopup();
                  setTimeout(() => {
                      if (typeof showReports === 'function') {
                          showReports(targetGroup.marker_id, targetReportId);
                      }
                  }, 500);
              });
          }
      }, 1600);
  } else {
      if (typeof showToast === 'function') {
          showToast('Report location not found.', 'error');
      } else {
          alert('Report location not found.');
      }
  }
}

function renderMarkers() {
  markerClusterGroup.clearLayers();

    allData.forEach(r => {
    const lat = parseFloat(r.latitude);
    const lon = parseFloat(r.longitude);
    if (isNaN(lat) || isNaN(lon)) return;
    
    if (showClusters) {
      const isUserReport = r.type === 'user_report';
      const color = isUserReport ? '#3b82f6' : (r.severity === 'critical' ? '#DC2626' : r.severity === 'high' ? '#ef4444' : r.severity === 'medium' ? '#f97316' : '#22c55e');
      const marker = L.marker([lat, lon], { icon: makeIcon(r.severity, isUserReport) });
      marker.options.marker_id = r.marker_id;
      
      const popupHtml = buildPremiumPopup(r, lat, lon, isUserReport);
      
      marker.bindPopup(popupHtml, { maxWidth: 290, minWidth: 270, className: 'pothole-popup' });
      markerClusterGroup.addLayer(marker);
    }
  });

}

// ── Stats cards ──────────────────────────────────────────────────────────────
async function updateStats() {
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl('stat-total',   data.total   ?? '—');
    setEl('stat-today',   data.today   ?? '—');
    setEl('stat-fixed',   data.fixed   ?? '—');
    setEl('stat-pending', data.pending ?? '—');
  } catch (_) {}
}

// ── Toggling ─────────────────────────────────────────────────────────────────
function toggleClusters() {
  showClusters = !showClusters;
  document.getElementById('btnClusters').classList.toggle('active', showClusters);
  renderMarkers();
}


// ── Filter chips ─────────────────────────────────────────────────────────────
document.querySelectorAll('#severityFilters .filter-chip').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#severityFilters .filter-chip').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilters.severity = btn.dataset.val;
    scheduleRefresh();
  });
});

document.querySelectorAll('#statusFilters .filter-chip').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#statusFilters .filter-chip').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilters.status = btn.dataset.val;
    scheduleRefresh();
  });
});

const confSlider = document.getElementById('confSlider');
if (confSlider) {
  confSlider.addEventListener('change', () => {
    activeFilters.confidence = confSlider.value;
    scheduleRefresh();
  });
}

// ── Auto refresh ─────────────────────────────────────────────────────────────
function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(loadMarkers, 400);
}

function startAutoRefresh() {
  if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  loadMarkers();
  autoRefreshInterval = setInterval(loadMarkers, (defaultSettings.refresh || 5) * 1000);
}

// ── Mark fixed from popup ────────────────────────────────────────────────────
window.markFixedFromMap = async function(id) {
  await fetch(`/api/pothole/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'Fixed' }),
  });
  map.closePopup();
  loadMarkers();
  if (typeof showToast === 'function') showToast('Marked as Fixed ✓', 'success');
};

// ── Reports Modal Logic ──────────────────────────────────────────────────────
window.showReports = async function(marker_id, highlightReportId = null) {
  const modal = document.getElementById('reportsModal');
  const container = document.getElementById('reportsContainer');
  const countBadge = document.getElementById('reportsCountBadge');
  if (!modal || !container) return;

  modal.style.display = 'flex';
  if (countBadge) countBadge.style.display = 'none';

  try {
    const group = allData.find(g => g.marker_id === marker_id);
    if (!group) throw new Error("Marker not found in cache");
    const reports = group.reports || [];
    console.log(`[Reports] Found ${reports?.length || 0} reports.`);

    if (!Array.isArray(reports) || reports.length === 0) {
      container.innerHTML = `
        <div class="reports-gallery-empty">
          <i class="fa-solid fa-image-slash"></i>
          No verified pothole images available.
        </div>`;
      return;
    }

    // Update count badge
    if (countBadge) {
      countBadge.textContent = reports.length;
      countBadge.style.display = 'inline-block';
    }

    // Helper: format date
    function fmtDate(d) {
      if (!d) return '—';
      const dt = new Date(d);
      return dt.toLocaleString(undefined, {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    }

    container.innerHTML = reports.map((r, idx) => {
      const isVideo = r.type === 'video' || (r.image_url && r.image_url.toLowerCase().endsWith('.mp4'));
      const displayMedia = r.image || r.media_url || r.image_url || '';
      const sev = (r.severity || 'unknown').toLowerCase();
      const sevColors = {
        low:      { bg: 'rgba(34,197,94,.18)',  color: '#4ade80' },
        medium:   { bg: 'rgba(245,158,11,.18)', color: '#fbbf24' },
        high:     { bg: 'rgba(239,68,68,.18)',  color: '#f87171' },
        critical: { bg: 'rgba(239,68,68,.28)',  color: '#fca5a5' }
      };
      const chip = sevColors[sev] || { bg: 'rgba(255,255,255,.1)', color: 'var(--muted)' };

      const mediaTag = isVideo
        ? `<video src="${displayMedia}" controls style="width:100%;height:100%;object-fit:contain"></video>`
        : `<img
            src="${displayMedia}"
            alt="Report ${idx + 1}"
            style="width:100%;height:100%;object-fit:contain;cursor:zoom-in"
            onclick="window.open('${displayMedia}','_blank')"
            onerror="this.onerror=null;this.outerHTML='<div style=\\'width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.35);color:#7d8590;\\'><i class=\\'fa-solid fa-image-slash fa-3x\\'></i></div>';"
          >`;

      const confPct = r.confidence ? Math.round(r.confidence * 100) : 0;
      const formattedTime = fmtDate(r.created_at);

      const srcRaw = (r.source || 'Unknown').toLowerCase();
      let srcIcon = '❓';
      let srcText = 'Unknown Report';
      if (srcRaw.includes('citizen')) { srcIcon = '👤'; srcText = 'Citizen Report'; }
      else if (srcRaw.includes('sensor')) { srcIcon = '📡'; srcText = 'Sensor Report'; }
      else if (srcRaw.includes('ai')) { srcIcon = '🤖'; srcText = 'AI Report'; }
      else if (srcRaw.includes('live')) { srcIcon = '📹'; srcText = 'Live Report'; }
      else { srcIcon = '📄'; srcText = 'System Report'; }

      const statLower = (r.status || 'Pending').toLowerCase();
      const statColor = statLower === 'approved' ? '#4ade80' : 
                        statLower === 'rejected' ? '#f87171' : '#fbbf24';

      return `
        <div class="report-gallery-card" id="reportCard_${r.id || ''}">
          <div class="report-gallery-img-wrap">
            ${displayMedia ? mediaTag : `<div class="reports-gallery-empty" style="padding:40px"><i class="fa-solid fa-image" style="opacity:.3"></i></div>`}
          </div>
          <div style="padding: 18px; display: flex; flex-direction: column; gap: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:1.1rem; font-weight:800; color:#fff;">#${r.id || 'N/A'}</span>
              <span style="font-size:0.9rem; font-weight:600; color:var(--muted);">${srcIcon} ${srcText}</span>
            </div>
            
            <div style="font-size:0.85rem; color:var(--muted); border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:14px; margin-bottom:2px;">
              📅 ${formattedTime}
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; align-items:center;">
              <div style="display:flex; flex-direction:column; gap:6px;">
                <span style="font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px;">Confidence</span>
                <span style="font-size:0.9rem; font-weight:700; color:#fff;">${confPct}%</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:6px;">
                <span style="font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px;">Severity</span>
                <span style="background:${chip.bg}; color:${chip.color}; border-radius:12px; font-size:0.75rem; font-weight:800; padding:4px 8px; text-transform:uppercase; display:inline-flex; justify-content:center; align-items:center;">${r.severity || 'UNKNOWN'}</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:6px;">
                <span style="font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px;">Status</span>
                <span style="background:${statColor}22; color:${statColor}; border-radius:12px; font-size:0.75rem; font-weight:800; padding:4px 8px; display:inline-flex; justify-content:center; align-items:center;">${r.status || 'Pending'}</span>
              </div>
            </div>

            <button class="popup-btn popup-btn-primary" style="margin-top:8px; width:100%; justify-content:center;" onclick="window.open('${displayMedia}','_blank')">
              View
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (highlightReportId) {
      setTimeout(() => {
        const el = document.getElementById(`reportCard_${highlightReportId}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.style.border = '2px solid var(--accent)';
          el.style.boxShadow = '0 0 20px rgba(99,102,241,0.5)';
        }
      }, 300);
    }

  } catch (err) {
    console.error('[Reports] Modal Error:', err);
    container.innerHTML = `
      <div class="reports-gallery-empty">
        <i class="fa-solid fa-circle-exclamation" style="color:var(--danger)"></i>
        <div>Failed to load reports.<br><small>${err.message}</small></div>
      </div>`;
  }
};

window.closeReportsModal = function() {
  const modal = document.getElementById('reportsModal');
  if (modal) {
    modal.style.display = 'none';
    const container = document.getElementById('reportsContainer');
    if (container) container.innerHTML = ''; // stop any playing videos
    const badge = document.getElementById('reportsCountBadge');
    if (badge) badge.style.display = 'none';
  }
};

// Haversine for JS
function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

initGeolocation();
startAutoRefresh();
