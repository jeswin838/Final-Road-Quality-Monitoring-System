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
let currentOpenMarkerId = null;

map.addLayer(markerClusterGroup);

map.on('popupopen', function(e) {
  if (e.popup && e.popup._source && e.popup._source.options) {
    currentOpenMarkerId = e.popup._source.options.marker_id || e.popup._source.options.hazard_id;
  }
});

map.on('popupclose', function(e) {
  currentOpenMarkerId = null;
});

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
  const color  = colors[sev] || '#6366f1';
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
        <button onclick="openAssignModal(\'${r.id}\', '${r.status || 'Pending Repair'}')"
          style="flex:1;padding:5px;background:rgba(99,102,241,.15);color:#6366f1;border:1px solid rgba(99,102,241,.3);border-radius:6px;cursor:pointer;font-size:11px">
          + Manage
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
  const assignText = (statusRaw === 'Pending Repair' || statusRaw === 'Pending') ? 'Assign Worker' : 'Update Status';
  const markFixedBtn = !isUserReport
    ? `<button class="popup-btn popup-btn-success" onclick="openAssignModal(\'${r.id}\', '${statusRaw}')">
        <i class="fa-solid fa-clipboard-user"></i> ${assignText}
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
        <button class="popup-btn popup-btn-primary" onclick="showReports(\'${r.marker_id || r.id}\')">
          <i class="fa-solid fa-images"></i> View Report
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
    const targetHazardId = urlParams.get('hazard');
    
    if (!targetReportId && !targetMarkerId && !targetHazardId) return;
    if (!allData || allData.length === 0) return;
  
    let targetGroup = null;
  
    for (let group of allData) {
       if (targetMarkerId && group.marker_id === targetMarkerId) {
           targetGroup = group;
           break;
       }
       if (targetHazardId && String(group.id) === String(targetHazardId)) {
           targetGroup = group;
           break;
       }
       if ((targetReportId || targetHazardId) && group.reports) {
           const searchId = targetReportId || targetHazardId;
           if (group.reports.some(r => String(r.id) === String(searchId) || String(r.hazard_id) === String(searchId))) {
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
                    window.history.replaceState({}, document.title, window.location.pathname);
                    
                    if (foundLayer._icon) {
                        foundLayer._icon.classList.add('marker-pulse-highlight');
                        setTimeout(() => {
                            if (foundLayer._icon) {
                                foundLayer._icon.classList.remove('marker-pulse-highlight');
                            }
                        }, 5000);
                    }
                    
                    setTimeout(() => {
                        if (typeof showReports === 'function') {
                            showReports(targetGroup.marker_id, targetReportId || targetHazardId);
                        }
                    }, 500);
                });
            }
        }, 1600);
    } else {
        if (typeof showToast === 'function') {
            showToast('Report location not found.', 'error');
        } else {
            showToast('Report location not found.', 'error');
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
      const marker = L.marker([lat, lon], { icon: makeIcon(r.severity) });
      marker.options.marker_id = r.marker_id;
      marker.options.hazard_id = r.id;
      
      const popupHtml = buildPremiumPopup(r, lat, lon, isUserReport);
      
      marker.bindPopup(popupHtml, { maxWidth: 290, minWidth: 270, className: 'pothole-popup' });
      markerClusterGroup.addLayer(marker);
    }
  });
  
  if (currentOpenMarkerId) {
      markerClusterGroup.eachLayer(layer => {
          if (layer.options && (layer.options.marker_id === currentOpenMarkerId || layer.options.hazard_id === currentOpenMarkerId)) {
              // Wait slightly for cluster to finish updating
              setTimeout(() => { layer.openPopup(); }, 100);
          }
      });
  }

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
window.showReports = async function(report_id) {
    const modal = document.getElementById('reportsModal');
    const inner = document.querySelector('.reports-modal-inner');
    if (!modal || !inner) return;
  
    modal.style.display = 'flex';
    
    // Give it fixed dimensions for the new layout
    inner.style.width = '90vw';
    inner.style.maxWidth = '1200px';
    inner.style.height = '85vh';
    inner.style.padding = '0'; // Remove any default padding
  
    // Show loading state
    inner.innerHTML = `
      <div style="flex:1; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#6366f1; height:100%;">
        <i class="fa-solid fa-spinner fa-spin fa-3x"></i>
        <div style="margin-top:20px; color:#cbd5e1; font-weight:600; letter-spacing:1px; text-transform:uppercase;">Locating Report History...</div>
      </div>
    `;

    try {
      // 1. Resolve coordinates from allData
      let lat = null, lon = null;
      let fallbackData = null;
      let lookupStrategy = 'None';
      
      const search_id = String(report_id);
      
      console.log("-----------------------------------------");
      console.log("History Lookup Initiated");
      console.log("Clicked ID (Passed to function):", search_id);

      if (typeof allData !== 'undefined' && allData && allData.length > 0) {
          for (let r of allData) {
              // Priority 1: marker_id
              if (r.marker_id && String(r.marker_id) === search_id) {
                  fallbackData = r;
                  lookupStrategy = "marker_id";
                  break;
              }
              // Priority 2: hazard_id
              if (r.hazard_id && String(r.hazard_id) === search_id) {
                  fallbackData = r;
                  lookupStrategy = "hazard_id";
                  break;
              }
              // Priority 3: id
              if (r.id && (String(r.id) === search_id || String(r.id) === search_id.replace('AI-', ''))) {
                  fallbackData = r;
                  lookupStrategy = "id";
                  break;
              }
              // Priority 4: reports[].id
              if (r.reports && Array.isArray(r.reports)) {
                  let foundInReports = false;
                  for (let sub_r of r.reports) {
                      if (String(sub_r.id) === search_id || String(sub_r.hazard_id) === search_id) {
                          foundInReports = true;
                          break;
                      }
                  }
                  if (foundInReports) {
                      fallbackData = r;
                      lookupStrategy = "reports[].id";
                      break;
                  }
              }
          }
      }
      
      if (fallbackData) {
          lat = fallbackData.latitude !== undefined ? fallbackData.latitude : (fallbackData.lat !== undefined ? fallbackData.lat : (fallbackData.location ? (fallbackData.location.lat !== undefined ? fallbackData.location.lat : fallbackData.location.latitude) : null));
          lon = fallbackData.longitude !== undefined ? fallbackData.longitude : (fallbackData.lng !== undefined ? fallbackData.lng : (fallbackData.lon !== undefined ? fallbackData.lon : (fallbackData.location ? (fallbackData.location.lon !== undefined ? fallbackData.location.lon : fallbackData.location.longitude) : null)));
          
          console.log("Lookup Strategy Used:", lookupStrategy);
          console.log("Matched Object:", fallbackData);
          console.log("Extracted Latitude:", lat);
          console.log("Extracted Longitude:", lon);
          console.log("Grouped Marker ID:", fallbackData.marker_id);
          console.log("Grouped Report Count:", fallbackData.reports ? fallbackData.reports.length : 0);
          console.log("History API URL:", `/api/location-reports?lat=${lat}&lon=${lon}`);
      } else {
          console.error("Lookup failed. Could not find ID:", search_id, "in allData.");
      }
      
      console.log("----- DEBUG LOGS -----");
      console.log("Clicked report id:", report_id);
      console.log("Resolved report:", fallbackData);
      console.log("Latitude:", lat);
      console.log("Longitude:", lon);
      console.log("API URL:", `/api/location-reports?lat=${lat}&lon=${lon}`);
      console.log("Current allData length:", allData ? allData.length : 0);
      
      let markerObj = null;
      let popupObj = null;
      if (typeof markerClusterGroup !== 'undefined') {
          markerClusterGroup.eachLayer(layer => {
              if (layer.options && fallbackData && layer.options.marker_id === fallbackData.marker_id) {
                  markerObj = layer;
                  if (typeof layer.getPopup === 'function') popupObj = layer.getPopup();
              }
          });
      }
      console.log("Marker object:", markerObj);
      console.log("Popup object:", popupObj);
      console.log("Current selected marker:", typeof selectedMarker !== 'undefined' ? selectedMarker : null);

      if (!lat || !lon) {
          throw new Error("Location coordinates not found in active map data.");
      }

      // 2. Fetch all reports at this location
      const res = await fetch(`/api/location-reports?lat=${lat}&lon=${lon}`);
      console.log("API response status:", res.status, res.statusText);
      if (!res.ok) throw new Error("Failed to fetch data"); // Match exact error text
      const reports = await res.json();
      console.log("API response (JSON):", reports);
      console.log("Number of reports returned:", reports ? reports.length : 0);
      
      if (!reports || reports.length === 0) {
          throw new Error("No reports found for this location");
      }

      // Sort newest to oldest
      reports.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      // Formatting helper
      function fmtDate(d) {
        if (!d) return 'N/A';
        const dt = new Date(d);
        return dt.toLocaleString(undefined, {
          month: 'short', day: 'numeric', year: 'numeric',
          hour: '2-digit', minute: '2-digit'
        });
      }

      // 3. Extract all images for the gallery
      let allImages = [];
      let total_images_extracted = 0;
      reports.forEach(r => {
          let imgArr = [];
          if (r.image_url) imgArr.push(r.image_url);
          if (r.media_url && r.media_url !== r.image_url) imgArr.push(r.media_url);
          if (r.all_images && Array.isArray(r.all_images)) {
              r.all_images.forEach(i => { if (!imgArr.includes(i)) imgArr.push(i); });
          }
          
          total_images_extracted += imgArr.length;
          
          if (imgArr.length === 0) {
              // Add fallback placeholder for reports with no image so it still shows in gallery
              imgArr.push('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIHZpZXdCb3g9IjAgMCA0MDAgMzAwIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0Ij48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUyOTNiIi8+PHBhdGggZD0iTTIwMCAxMTRMMTUwIDE4NEgyNTBMMjAwIDExNFoiIGZpbGw9IiM0NzU1NjkiLz48Y2lyY2xlIGN4PSIxNjAiIGN5PSIxMjAiIHI9IjE1IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iMjAwIiB5PSIyMTAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE2IiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5JbWFnZSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==');
          }
          
          imgArr.forEach(img => {
              if (!allImages.find(x => x.src === img)) {
                  allImages.push({ src: img, report: r });
              }
          });
      });

      console.log("Gallery Debug:");
      console.log("- Total Reports Fetched:", reports.length);
      console.log("- Total Images Extracted:", total_images_extracted);
      console.log("- Gallery Item Count:", allImages.length);

      window.galleryImages = allImages;
      window.currentGalleryIndex = 0;
      
      window.setGalleryImage = function(index) {
          if (index < 0 || index >= window.galleryImages.length) return;
          window.currentGalleryIndex = index;
          const item = window.galleryImages[index];
          
          const mainImg = document.getElementById('galleryMainImage');
          const errDiv = document.getElementById('galleryImageError');
          const errUrl = document.getElementById('galleryImageErrorUrl');
          
          console.log("=========================================");
          console.log("[IMAGE VIEWER] Selected Image Index:", index);
          console.log("[IMAGE VIEWER] Database ID:", item.report.id);
          console.log("[IMAGE VIEWER] Source Table:", item.report.pothole ? "User Report / Pothole" : "Unknown");
          console.log("[IMAGE VIEWER] Image URL:", item.src);
          console.log("=========================================");

          if (mainImg) {
              mainImg.style.opacity = '0';
              if (errDiv) errDiv.style.display = 'none';
              
              if (!item.src || item.src.trim() === '' || item.src === 'null' || item.src === 'undefined') {
                  console.error("[IMAGE VIEWER] LOAD FAILURE! URL is null, empty, or undefined.");
                  if (errDiv) {
                      errDiv.style.display = 'block';
                      errUrl.textContent = "URL is missing or undefined";
                  }
              } else {
                  // Explicit Pre-loading
                  const imgLoader = new Image();
                  
                  imgLoader.onload = function() {
                      console.log(`[IMAGE VIEWER] LOAD SUCCESS: ${item.src}`);
                      console.log(`[IMAGE VIEWER] Natural Width: ${imgLoader.naturalWidth}px`);
                      console.log(`[IMAGE VIEWER] Natural Height: ${imgLoader.naturalHeight}px`);
                      console.log(`[IMAGE VIEWER] HTTP Status: (Assumed 200 OK since onload fired)`);
                      
                      mainImg.src = item.src;
                      mainImg.style.opacity = '1';
                      if (errDiv) errDiv.style.display = 'none';
                  };
                  
                  imgLoader.onerror = function() {
                      console.error(`[IMAGE VIEWER] LOAD FAILURE! Image threw onerror during fetch.`);
                      console.error(`[IMAGE VIEWER] Broken URL: ${item.src}`);
                      console.error(`[IMAGE VIEWER] Possible Reasons: 404 Not Found, 403 Forbidden, CORS error, or invalid format.`);
                      
                      if (errDiv) {
                          errDiv.style.display = 'block';
                          errUrl.textContent = item.src;
                      }
                      // Keep mainImg opacity at 0 so it doesn't show broken icon
                      mainImg.style.opacity = '0';
                  };
                  
                  // Trigger load
                  imgLoader.src = item.src;
              }
          }
          
          document.querySelectorAll('.gallery-thumb').forEach((th, i) => {
              th.style.borderColor = (i === index) ? '#6366f1' : 'transparent';
              th.style.opacity = (i === index) ? '1' : '0.5';
          });
          
          const r = item.report;

          
          document.getElementById('meta-date').textContent = fmtDate(r.created_at);
          
          let sourceHtml = '';
          if (r.source === 'Citizen Report' || r.source === 'Citizen') {
              sourceHtml = '<i class="fa-solid fa-user" style="color:#60a5fa;margin-right:6px;"></i>Citizen Report';
          } else {
              sourceHtml = '<i class="fa-solid fa-robot" style="color:#a78bfa;margin-right:6px;"></i>AI Detection';
          }
          document.getElementById('meta-source').innerHTML = sourceHtml;
          
          if (r.confidence === null || r.confidence === undefined) {
              document.getElementById('meta-conf').innerHTML = `<i class="fa-solid fa-percent" style="opacity:0.6;margin-right:6px;"></i>N/A`;
          } else {
              document.getElementById('meta-conf').innerHTML = `<i class="fa-solid fa-percent" style="opacity:0.6;margin-right:6px;"></i>${Math.round(r.confidence)}%`;
          }
          
          document.getElementById('meta-sev').innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="opacity:0.6;margin-right:6px;"></i>${r.severity || 'Unknown'}`;
          
          document.getElementById('meta-road').textContent = r.road_name || 'Unknown';
          document.getElementById('meta-landmark').textContent = r.landmark || r.village || r.town || 'Unknown';
          document.getElementById('meta-desc').textContent = r.description || 'No description provided.';
          
          document.getElementById('meta-counter').textContent = `Image ${index + 1} of ${window.galleryImages.length}`;
          
          console.log("Viewing Image Index:", index);
          console.log("- Source:", r.source);
          console.log("- Confidence:", r.confidence);
          console.log("- Severity:", r.severity);
          console.log("- Road:", r.road_name);
          console.log("- Image URL:", item.src);
      };

      let thumbsHtml = '';
      if (allImages.length > 1) {
          thumbsHtml = `
          <div style="display:flex; gap:12px; overflow-x:auto; padding:15px; background:rgba(0,0,0,0.5); border-top:1px solid rgba(255,255,255,0.1);">
              ${allImages.map((img, i) => `
                  <img src="${img.src}" class="gallery-thumb" onclick="setGalleryImage(${i})" style="width:100px; height:70px; object-fit:cover; border-radius:8px; cursor:pointer; border:2px solid transparent; opacity:0.5; transition:all 0.2s; flex-shrink:0;" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIHZpZXdCb3g9IjAgMCA0MDAgMzAwIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0Ij48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUyOTNiIi8+PHBhdGggZD0iTTIwMCAxMTRMMTUwIDE4NEgyNTBMMjAwIDExNFoiIGZpbGw9IiM0NzU1NjkiLz48Y2lyY2xlIGN4PSIxNjAiIGN5PSIxMjAiIHI9IjE1IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iMjAwIiB5PSIyMTAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE2IiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5JbWFnZSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';">
              `).join('')}
          </div>`;
      } else {
          thumbsHtml = `<div style="padding:15px; text-align:center; color:#94a3b8; background:rgba(0,0,0,0.5); border-top:1px solid rgba(255,255,255,0.1);">No additional images available.</div>`;
      }

      inner.innerHTML = `
      <div style="display: flex; flex-direction: column; width: 100%; height: 100%; background: #0f172a; border-radius:inherit; overflow:hidden;">
          
          <!-- Header -->
          <div style="display:flex; justify-content:space-between; align-items:center; padding:20px 25px; background:rgba(255,255,255,0.03); border-bottom:1px solid rgba(255,255,255,0.1);">
              <h3 style="margin:0; font-size:1.2rem; color:#fff; font-weight:800; display:flex; align-items:center; gap:10px;">
                  <i class="fa-solid fa-images" style="color:#6366f1;"></i> Location Gallery
              </h3>
              <div style="display:flex; align-items:center; gap:20px;">
                  <span id="meta-counter" style="color:#94a3b8; font-weight:600; font-size:0.9rem;"></span>
                  <button onclick="closeReportsModal()" style="background:transparent; border:none; color:#cbd5e1; font-size:1.5rem; cursor:pointer; padding:0;">&times;</button>
              </div>
          </div>

          <!-- Main Content -->
          <div style="flex:1; display:flex; overflow:hidden;">
              
              <!-- Left: Main Image Viewer -->
              <div style="flex: 3; display:flex; flex-direction:column; background:#000; position:relative;">
                  <div style="flex:1; display:flex; align-items:center; justify-content:center; overflow:hidden; position:relative; cursor:zoom-in;" onclick="openFullscreenGallery()">
                      <img id="galleryMainImage" src="" style="max-width:100%; max-height:100%; object-fit:contain; transition:opacity 0.2s; opacity:0;" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIHZpZXdCb3g9IjAgMCA0MDAgMzAwIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0Ij48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUyOTNiIi8+PHBhdGggZD0iTTIwMCAxMTRMMTUwIDE4NEgyNTBMMjAwIDExNFoiIGZpbGw9IiM0NzU1NjkiLz48Y2lyY2xlIGN4PSIxNjAiIGN5PSIxMjAiIHI9IjE1IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iMjAwIiB5PSIyMTAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE2IiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5JbWFnZSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';">
                  </div>
                  ${thumbsHtml}
              </div>

              <!-- Right: Metadata Panel -->
              <div style="flex: 1; min-width:300px; background:rgba(255,255,255,0.02); border-left:1px solid rgba(255,255,255,0.1); padding:25px; display:flex; flex-direction:column; gap:20px; overflow-y:auto;">
                  
                  <div style="display:flex; gap:20px;">
                      <div style="flex:1;">
                          <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Capture Date</div>
                          <div id="meta-date" style="font-size:1.1rem; color:#fff; font-weight:600;"></div>
                      </div>
                      <div style="flex:1;">
                          <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Source</div>
                          <div id="meta-source" style="font-size:1.1rem; color:#fff; font-weight:600; display:flex; align-items:center;"></div>
                      </div>
                  </div>
                  
                  <div style="display:flex; gap:20px;">
                      <div style="flex:1;">
                          <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Average AI Confidence</div>
                          <div id="meta-conf" style="font-size:1.1rem; color:#fff; font-weight:600;"></div>
                            <div id="meta-conf-details" style="font-size:0.75rem; color:#94a3b8; margin-top:6px; line-height:1.4;"></div>
                      </div>
                      <div style="flex:1;">
                          <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Severity</div>
                          <div id="meta-sev" style="font-size:1.1rem; color:#fff; font-weight:600;"></div>
                      </div>
                  </div>
                  
                  <hr style="border-color:rgba(255,255,255,0.1); border-top:none; margin:0;">
                  
                  <div>
                      <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Road Name</div>
                      <div id="meta-road" style="font-size:1rem; color:#fff; font-weight:600;"></div>
                  </div>
                  
                  <div>
                      <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Landmark / Area</div>
                      <div id="meta-landmark" style="font-size:1rem; color:#fff; font-weight:600;"></div>
                  </div>
                  
                  <div>
                      <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px;">Description</div>
                      <div id="meta-desc" style="font-size:0.9rem; color:#cbd5e1; font-weight:500; font-style:italic; padding:10px; background:rgba(0,0,0,0.2); border-radius:6px;"></div>
                  </div>
                  
                  <hr style="border-color:rgba(255,255,255,0.1); border-top:none; margin:10px 0;">
                  
                  <div>
                      <button onclick="openFullscreenGallery()" class="roc-btn" style="width:100%; background:rgba(99,102,241,0.15); color:#818cf8; border:1px solid rgba(99,102,241,0.3); padding:12px; border-radius:8px; cursor:pointer; font-weight:700; transition:all 0.2s;" onmouseover="this.style.background='rgba(99,102,241,0.25)'" onmouseout="this.style.background='rgba(99,102,241,0.15)'">
                          <i class="fa-solid fa-expand" style="margin-right:8px;"></i> Open Fullscreen
                      </button>
                  </div>
              </div>
          </div>
      </div>`;

      // Init first image
      setTimeout(() => { 
          console.log("Gallery images count:", document.querySelectorAll('#reportsContainer .gallery-item').length);
          setGalleryImage(0); 
      }, 50);

    } catch (err) {
      console.error("DEBUG ERROR TRACE:", err);
      inner.innerHTML = `
      <div style="display: flex; width: 100%; height: 100%; align-items:center; justify-content:center; flex-direction:column; padding:40px; text-align:center;">
        <i class="fa-solid fa-circle-exclamation fa-4x" style="color:#ef4444; margin-bottom:25px;"></i>
        <div style="font-size:1.5rem; color:#fff; font-weight:800; margin-bottom:12px;">Failed to Load Gallery</div>
        <div style="font-size:1.05rem; color:#94a3b8; margin-bottom:30px;">${err.message}</div>
        <button class="roc-btn" style="background:rgba(255,255,255,0.1); color:#fff; border:1px solid rgba(255,255,255,0.2); padding:12px 35px; border-radius:8px; cursor:pointer; font-weight:600; font-size:1.1rem;" onclick="closeReportsModal()">Close</button>
      </div>`;
    }
}
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


// ── FULLSCREEN GALLERY LOGIC ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const fsHtml = `
    <div id="fsGalleryModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.95); z-index:99999; backdrop-filter:blur(10px); opacity:0; transition:opacity 0.25s;">
        <!-- Header -->
        <div style="position:absolute; top:0; left:0; right:0; padding:20px 30px; display:flex; justify-content:space-between; align-items:center; z-index:100000; background:linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);">
            <div style="color:#fff; font-size:1.2rem; font-weight:800; font-family:'Inter', sans-serif;" id="fsCounter"></div>
            <div style="display:flex; gap:15px;">
                <a id="fsDownload" href="#" download class="roc-btn" style="background:rgba(255,255,255,0.1); color:#fff; padding:10px 20px; border-radius:8px; text-decoration:none;"><i class="fa-solid fa-download"></i></a>
                <button onclick="closeFullscreenGallery()" class="roc-btn" style="background:rgba(239,68,68,0.2); color:#f87171; border:none; padding:10px 20px; border-radius:8px; cursor:pointer;"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>

        <!-- Controls -->
        <button onclick="fsPrev(event)" style="position:absolute; left:30px; top:50%; transform:translateY(-50%); background:rgba(255,255,255,0.1); border:none; color:#fff; width:60px; height:60px; border-radius:50%; cursor:pointer; z-index:100000; font-size:1.5rem; transition:background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'"><i class="fa-solid fa-chevron-left"></i></button>
        
        <button onclick="fsNext(event)" style="position:absolute; right:30px; top:50%; transform:translateY(-50%); background:rgba(255,255,255,0.1); border:none; color:#fff; width:60px; height:60px; border-radius:50%; cursor:pointer; z-index:100000; font-size:1.5rem; transition:background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'"><i class="fa-solid fa-chevron-right"></i></button>

        <!-- Image Container -->
        <div id="fsImgContainer" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; overflow:hidden; cursor:grab;" onmousedown="fsPanStart(event)">
            <img id="fsMainImg" src="" style="max-width:90%; max-height:90%; object-fit:contain; transition:transform 0.1s ease-out, opacity 0.2s;" draggable="false">
        </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', fsHtml);
    
    // Mouse wheel zoom
    document.getElementById('fsImgContainer').addEventListener('wheel', (e) => {
        e.preventDefault();
        window.fsZoom += e.deltaY * -0.002;
        window.fsZoom = Math.min(Math.max(1, window.fsZoom), 5); // clamped 1x - 5x
        updateFsTransform();
    }, {passive: false});
});

window.fsZoom = 1;
window.fsPanX = 0;
window.fsPanY = 0;
window.fsDragging = false;
window.fsStartX = 0;
window.fsStartY = 0;

function updateFsTransform() {
    const img = document.getElementById('fsMainImg');
    if(img) {
        img.style.transform = `translate(${window.fsPanX}px, ${window.fsPanY}px) scale(${window.fsZoom})`;
    }
}

function resetFsTransform() {
    window.fsZoom = 1;
    window.fsPanX = 0;
    window.fsPanY = 0;
    updateFsTransform();
}

window.fsPanStart = function(e) {
    if (window.fsZoom <= 1) return;
    window.fsDragging = true;
    window.fsStartX = e.clientX - window.fsPanX;
    window.fsStartY = e.clientY - window.fsPanY;
    document.getElementById('fsImgContainer').style.cursor = 'grabbing';
};

window.addEventListener('mousemove', (e) => {
    if(!window.fsDragging) return;
    window.fsPanX = e.clientX - window.fsStartX;
    window.fsPanY = e.clientY - window.fsStartY;
    updateFsTransform();
});

window.addEventListener('mouseup', () => {
    window.fsDragging = false;
    const c = document.getElementById('fsImgContainer');
    if(c) c.style.cursor = 'grab';
});

window.openFullscreenGallery = function() {
    if(!window.galleryImages || window.galleryImages.length === 0) return;
    const m = document.getElementById('fsGalleryModal');
    if(m) {
        m.style.display = 'block';
        setTimeout(() => m.style.opacity = '1', 10);
        updateFsImage();
    }
};

window.closeFullscreenGallery = function() {
    const m = document.getElementById('fsGalleryModal');
    if(m) {
        m.style.opacity = '0';
        setTimeout(() => m.style.display = 'none', 250);
    }
};

function updateFsImage() {
    const item = window.galleryImages[window.currentGalleryIndex];
    if(!item) return;
    const img = document.getElementById('fsMainImg');
    img.style.opacity = '0';
    setTimeout(() => {
        resetFsTransform();
        img.src = item.src;
        img.style.opacity = '1';
    }, 150);
    
    document.getElementById('fsCounter').textContent = `Image ${window.currentGalleryIndex + 1} of ${window.galleryImages.length}`;
    document.getElementById('fsDownload').href = item.src;
}

window.fsNext = function(e) {
    if(e) e.stopPropagation();
    if(window.currentGalleryIndex < window.galleryImages.length - 1) {
        window.currentGalleryIndex++;
    } else {
        window.currentGalleryIndex = 0; // wrap around
    }
    updateFsImage();
    
    // Sync thumbnail in modal behind
    if(window.setGalleryImage) window.setGalleryImage(window.currentGalleryIndex);
};

window.fsPrev = function(e) {
    if(e) e.stopPropagation();
    if(window.currentGalleryIndex > 0) {
        window.currentGalleryIndex--;
    } else {
        window.currentGalleryIndex = window.galleryImages.length - 1; // wrap around
    }
    updateFsImage();
    
    // Sync thumbnail
    if(window.setGalleryImage) window.setGalleryImage(window.currentGalleryIndex);
};

// Keyboard navigation
window.addEventListener('keydown', (e) => {
    const m = document.getElementById('fsGalleryModal');
    if(m && m.style.display === 'block') {
        if(e.key === 'ArrowRight') window.fsNext();
        if(e.key === 'ArrowLeft') window.fsPrev();
        if(e.key === 'Escape') window.closeFullscreenGallery();
    }
});
