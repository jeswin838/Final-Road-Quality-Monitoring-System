// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// navigation.js  â€”  Safe Route Navigation (Leaflet + ORS backend)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

/* â”€â”€ Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const NAV_CFG = {
  defaultLat:     12.1326,
  defaultLon:     78.1944,
  defaultZoom:    13,
  refreshMs:      12000,    // pothole refresh interval
  recalcDist:     50,       // deviation distance to trigger recalc (meters)
  arrivalDist:    30,       // distance to trigger arrival (meters)
};

/* â”€â”€ State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
let navMap            = null;
let clickMode         = 'start';   // 'start' | 'end'
let startLatLon       = null;
let endLatLon         = null;
let startMarker       = null;
let endMarker         = null;
let userMarker        = null;      // Current GPS location
let userLatLon        = null;
let safeRouteLayer    = null;
let completedRouteLayer = null;
let dynamicRouteLayers = null;
let altRouteLayers    = [];
let routeHazardMarkers = [];
let allHazardsData    = [];      // Cache of fetched hazards
let currentUpcomingHazardId = null;
let navWatchId        = null;
let currentHazardFilter = 'all'; // all, high, medium, low, destination
let potholeLayerGroup = null;
let refreshTimer      = null;

// Navigation State
let isNavigating = false;
let currentRouteCoords = [];
let originalRouteCoords = [];
let currentRouteTotalDist = 0;
let initialRouteDuration = 0;
let lastLocationTime = 0;
let currentSpeed = 0; // m/s
let speedBuffer = [];
let lastRecalcTime = 0;
let isRecalculating = false;

/* â”€â”€ Icons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function makeIcon(color, label) {
  return L.divIcon({
    className: '',
    iconSize:  [30, 42],
    iconAnchor:[15, 42],
    popupAnchor:[0, -40],
    html: `
      <svg xmlns="http://www.w3.org/2000/svg" width="30" height="42" viewBox="0 0 30 42">
        <path d="M15 0 C6.7 0 0 6.7 0 15 C0 26 15 42 15 42 C15 42 30 26 30 15 C30 6.7 23.3 0 15 0Z"
              fill="${color}" stroke="rgba(0,0,0,.35)" stroke-width="1.5"/>
        <text x="15" y="20" text-anchor="middle" font-size="13" font-weight="bold"
              font-family="Inter,sans-serif" fill="#fff">${label}</text>
      </svg>`,
  });
}

const startIcon = makeIcon('#22c55e', 'S');

const destTargetIcon = L.divIcon({
  className: '',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16],
  html: `<div class="dest-marker-pulse"><i class="fa-solid fa-bullseye"></i></div>`
});

/* â”€â”€ Map initialisation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function initNavMap() {
  navMap = L.map('navMap', { zoomControl: false }).setView(
    [NAV_CFG.defaultLat, NAV_CFG.defaultLon], NAV_CFG.defaultZoom
  );

  // OpenStreetMap tiles with dark-ish overlay
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'Â© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(navMap);

  // Enforce Z-Index hierarchy
  navMap.createPane('hazardPane'); navMap.getPane('hazardPane').style.zIndex = 400;
  navMap.createPane('workerPane'); navMap.getPane('workerPane').style.zIndex = 410;
  navMap.createPane('destPane');   navMap.getPane('destPane').style.zIndex = 420;
  navMap.createPane('routePane');  navMap.getPane('routePane').style.zIndex = 430;

  potholeLayerGroup = L.layerGroup().addTo(navMap);

  navMap.on('click', onMapClick);

  // Load potholes immediately then schedule refresh
  loadPotholes();
  refreshTimer = setInterval(loadPotholes, NAV_CFG.refreshMs);
}

/* â”€â”€ Map click handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function onMapClick(e) {
  const { lat, lng } = e.latlng;
  if (clickMode === 'start') {
    placeMarker('start', lat, lng);
  } else {
    placeMarker('end', lat, lng);
  }
}

function placeMarker(type, lat, lng) {
  if (type === 'start') {
    if (startMarker) navMap.removeLayer(startMarker);
    startLatLon = [lat, lng];
    startMarker = L.marker([lat, lng], { icon: startIcon, pane: 'workerPane', draggable: true }).addTo(navMap);
    startMarker.on('dragend', function(e) {
      const p = e.target.getLatLng();
      startLatLon = [p.lat, p.lng];
      document.getElementById('startInput').value = `${p.lat.toFixed(5)}, ${p.lng.toFixed(5)}`;
    });
    document.getElementById('startInput').value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  } else {
    if (endMarker) navMap.removeLayer(endMarker);
    endLatLon = [lat, lng];
    
    // Popup mimicking assigned work
    const destPopup = `
      <div class="custom-popup">
        <h4>Assigned Work</h4>
        <div><b>Coordinates:</b> ${lat.toFixed(4)}, ${lng.toFixed(4)}</div>
        <div><b>Status:</b> <span>Pending</span></div>
      </div>
    `;
    endMarker = L.marker([lat, lng], { icon: destTargetIcon, pane: 'destPane', draggable: true })
      .bindPopup(destPopup)
      .addTo(navMap);
    endMarker.on('dragend', function(e) {
      const p = e.target.getLatLng();
      endLatLon = [p.lat, p.lng];
      document.getElementById('endInput').value = `${p.lat.toFixed(5)}, ${p.lng.toFixed(5)}`;
    });
    
    document.getElementById('endInput').value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  }
}

/* â”€â”€ Click mode toggle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function setClickMode(mode) {
  clickMode = mode;
  document.getElementById('modeStart').style.opacity = mode === 'start' ? '1' : '.5';
  document.getElementById('modeEnd').style.opacity   = mode === 'end'   ? '1' : '.5';
  navMap.getContainer().style.cursor = 'crosshair';
}

/* â”€â”€ Clear a point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function clearPoint(type) {
  if (type === 'start') {
    if (startMarker) navMap.removeLayer(startMarker);
    startMarker = null; startLatLon = null;
    document.getElementById('startInput').value = '';
  } else {
    if (endMarker) navMap.removeLayer(endMarker);
    endMarker = null; endLatLon = null;
    document.getElementById('endInput').value = '';
  }
  stopNavigation();
}

/* â”€â”€ Filter Hazards â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
window.setHazardFilter = function(filter) {
  currentHazardFilter = filter;
  document.getElementById('hazardFilterDropdown').classList.remove('show');
  
  // Update active state in dropdown
  const opts = document.querySelectorAll('.filter-option');
  opts.forEach(o => o.classList.remove('active'));
  event.currentTarget.classList.add('active');

  renderPotholes();
}

/* â”€â”€ GPS & Location Tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function useMyLocation() {
  if (!navigator.geolocation) {
    alert('Geolocation not supported by your browser.');
    return;
  }
  
  const startBtn = document.getElementById('modeStart');
  const oldText = startBtn ? startBtn.innerHTML : '';
  if (startBtn) startBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Locating...';

  navigator.geolocation.getCurrentPosition(
    pos => {
      if (startBtn) startBtn.innerHTML = oldText;
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      
      userLatLon = [lat, lng];
      placeMarker('start', lat, lng);
      updateUserMarker(lat, lng, pos.coords.heading, pos.coords.accuracy);
      navMap.setView([lat, lng], 17);
      
      trackUserLocation();
    },
    err => {
      if (startBtn) startBtn.innerHTML = oldText;
      console.error(err);
      if (err.code === 1) {
        alert('Location permission denied. Please allow location access to use live tracking.');
      } else {
        alert('Waiting for GPS... Unable to retrieve location.');
      }
    },
    { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }
  );
}

let targetMarkerLat = 0, targetMarkerLng = 0;
let currentMarkerLat = 0, currentMarkerLng = 0;
let animationFrameId = null;

function trackUserLocation() {
  if (navWatchId !== null) {
    navigator.geolocation.clearWatch(navWatchId);
  }

  navWatchId = navigator.geolocation.watchPosition(
    pos => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      const heading = pos.coords.heading;
      const accuracy = pos.coords.accuracy;
      const now = Date.now();

      if (lastLocationTime > 0) {
        const dt = (now - lastLocationTime) / 1000;
        const dist = haversineDist(userLatLon[0], userLatLon[1], lat, lng);
        if (dt > 0) {
          const spd = dist / dt;
          speedBuffer.push(spd);
          if (speedBuffer.length > 5) speedBuffer.shift();
          currentSpeed = speedBuffer.reduce((a, b) => a + b, 0) / speedBuffer.length;
        }
      }

      userLatLon = [lat, lng];
      lastLocationTime = now;
      
      // Smooth movement via interpolation target
      targetMarkerLat = lat;
      targetMarkerLng = lng;
      
      if (!userMarker) {
        currentMarkerLat = lat;
        currentMarkerLng = lng;
        createUserMarker(lat, lng, heading, accuracy);
        animateMarker(); // start loop
      } else {
        if (userMarker._accuracyCircle) {
           userMarker._accuracyCircle.setLatLng([lat, lng]);
           userMarker._accuracyCircle.setRadius(accuracy || 10);
        }
      }
      
      if (isNavigating) {
        updateNavigationProgress(lat, lng);
        autoFitMap();
        renderPotholes(); // dynamically filter based on new location
      }
    },
    err => console.warn(err),
    { enableHighAccuracy: true, maximumAge: 1000 }
  );
}

function createUserMarker(lat, lng, heading, accuracy) {
  const iconHtml = `
    <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
      <div style="position: absolute; width: 24px; height: 24px; background: #3b82f6; border: 3px solid #fff; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 2;"></div>
      <div style="position: absolute; top: -6px; width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-bottom: 12px solid #3b82f6; z-index: 1; transform: rotate(${heading || 0}deg);"></div>
    </div>
  `;
  
  userMarker = L.marker([lat, lng], {
    icon: L.divIcon({ className: 'worker-marker', html: iconHtml, iconSize: [32, 32], iconAnchor: [16, 16] }),
    pane: 'workerPane'
  }).addTo(navMap);
  
  userMarker._accuracyCircle = L.circle([lat, lng], {
    radius: accuracy || 10, color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.15, weight: 1, pane: 'workerPane'
  }).addTo(navMap);
}

function animateMarker() {
  if (userMarker) {
    const latDiff = targetMarkerLat - currentMarkerLat;
    const lngDiff = targetMarkerLng - currentMarkerLng;
    
    currentMarkerLat += latDiff * 0.1;
    currentMarkerLng += lngDiff * 0.1;
    
    userMarker.setLatLng([currentMarkerLat, currentMarkerLng]);
  }
  animationFrameId = requestAnimationFrame(animateMarker);
}

function autoFitMap() {
  if (userLatLon && endLatLon) {
    const bounds = L.latLngBounds([userLatLon, endLatLon]);
    // Padding protects UI panels from overlapping the markers
    navMap.fitBounds(bounds, { padding: [80, 80], animate: true, duration: 1.5 });
  }
}

/* â”€â”€ Load & render potholes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
async function loadPotholes() {
  try {
    const res = await fetch('/api/alerts');
    if (!res.ok) throw new Error('API error');
    allHazardsData = await res.json();
    renderPotholes();
  } catch (e) {
    console.warn('Could not fetch real-time potholes:', e);
  }
}

function renderPotholes() {
  potholeLayerGroup.clearLayers();

  if (currentHazardFilter === 'destination') {
    // Only destination is shown, no hazards
    return;
  }

  allHazardsData.forEach(p => {
    const lat = parseFloat(p.latitude);
    const lon = parseFloat(p.longitude);
    if (isNaN(lat) || isNaN(lon)) return;

    const sev = (p.severity || 'low').toLowerCase();

    // Filtering by type
    if (currentHazardFilter === 'high' && sev !== 'critical' && sev !== 'high') return;
    if (currentHazardFilter === 'medium' && sev !== 'medium') return;
    if (currentHazardFilter === 'low' && sev !== 'low') return;

    // Smart Distance Filtering
    let distToWorker = Infinity;
    if (userLatLon) {
      distToWorker = haversineDist(userLatLon[0], userLatLon[1], lat, lon);
    }
    
    let distToRoute = Infinity;
    if (safeRouteLayer && currentRouteCoords.length > 0) {
      const pLatLng = L.latLng(lat, lon);
      let closestPoint = null;
      if (typeof L.GeometryUtil !== 'undefined') {
         closestPoint = L.GeometryUtil.closest(navMap, safeRouteLayer, pLatLng);
         if (closestPoint) distToRoute = pLatLng.distanceTo(closestPoint);
      } else {
         // rough fallback
         distToRoute = Math.min(...currentRouteCoords.map(c => haversineDist(c[0], c[1], lat, lon)));
      }
    }

    // Only show if < 1km from worker or < 2km from active route
    if (isNavigating) {
      if (distToWorker > 1000 && distToRoute > 2000) return;
    }

    // Marker styling
    let hClass = 'hazard-low';
    let iconClass = 'fa-triangle-exclamation';
    if (sev === 'medium') { hClass = 'hazard-medium'; iconClass = 'fa-exclamation'; }
    if (sev === 'high' || sev === 'critical') { hClass = 'hazard-high'; iconClass = 'fa-skull-crossbones'; }

    const iconHtml = `<div class="hazard-marker ${hClass}"><i class="fa-solid ${iconClass}"></i></div>`;
    const m = L.marker([lat, lon], {
      icon: L.divIcon({ className: '', html: iconHtml, iconSize: [24, 24], iconAnchor: [12, 12] }),
      pane: 'hazardPane'
    });

    const reportedTime = new Date(p.created_at || Date.now()).toLocaleString();
    const distText = distToRoute < Infinity ? `${Math.round(distToRoute)}m from route` : 'Unknown';
    const reportIdStr = p.id ? `#${p.id}` : 'N/A';
    const displayImg = p.image_url || p.media_url || p.annotated_image_url || '';
    const imgHtml = displayImg 
      ? `<div style="margin-top:8px;"><img src="${displayImg}" style="width:100%;height:120px;object-fit:cover;border-radius:6px;cursor:pointer" onclick="window.open('${displayImg}','_blank')"></div>` 
      : `<div style="margin-top:8px;background:rgba(0,0,0,0.3);text-align:center;padding:20px;border-radius:6px;color:#94a3b8;"><i class="fa-solid fa-image-slash"></i> No image</div>`;

    m.bindPopup(`
      <div class="custom-popup" style="width:200px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <h4 style="margin:0; border:none; padding:0;">Report ${reportIdStr}</h4>
          <span class="${hClass}" style="background:transparent; color:inherit; font-weight:800; font-size:11px;">${sev.toUpperCase()}</span>
        </div>
        <div><b>Risk Score:</b> <span>${p.risk_score || p.raw_risk || 'N/A'}</span></div>
        <div><b>Distance:</b> <span>${distText}</span></div>
        ${imgHtml}
      </div>
    `);

    potholeLayerGroup.addLayer(m);
  });
}

function haversineDist(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2-lat1)*Math.PI/180;
  const dLon = (lon2-lon1)*Math.PI/180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

/* â”€â”€ Find Safe Route â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
async function findSafeRoute(isRecalc = false) {
  if (!startLatLon || !endLatLon) return;

  if (isRecalc) {
    document.getElementById('recalcAlert').style.display = 'flex';
    isRecalculating = true;
  } else {
    const btn = document.getElementById('findRouteBtn');
    if (btn) btn.innerHTML = '<span class="spinner"></span> Calculatingâ€¦';
    const btnR = document.getElementById('recalcRouteBtn');
    if (btnR) btnR.innerHTML = '<span class="spinner"></span> Calculatingâ€¦';
  }

  try {
    const reqBody = { 
      start: isRecalc && userLatLon ? userLatLon : startLatLon, 
      end: endLatLon 
    };

    const res = await fetch('/api/safe-route', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(reqBody),
    });

    const data = await res.json();
    if (!res.ok) throw new Error('Routing error');

    drawRoute(data);
    startNavigation(data);

  } catch (e) {
    console.error(e);
  } finally {
    if (isRecalc) {
      setTimeout(() => document.getElementById('recalcAlert').style.display = 'none', 3000);
      isRecalculating = false;
    }
    const btn = document.getElementById('findRouteBtn');
    if (btn) btn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Start Navigation';
    const btnR = document.getElementById('recalcRouteBtn');
    if (btnR) btnR.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Recalculate';
  }
}

function stopNavigation() {
  isNavigating = false;
  currentRouteCoords = [];
  if (safeRouteLayer) navMap.removeLayer(safeRouteLayer);
  if (completedRouteLayer) navMap.removeLayer(completedRouteLayer);
  if (dynamicRouteLayers) dynamicRouteLayers.clearLayers();
  altRouteLayers.forEach(l => navMap.removeLayer(l));
  
  safeRouteLayer = null; completedRouteLayer = null; altRouteLayers = [];
  
  document.getElementById('navActiveCard').style.display = 'none';
  document.getElementById('arrivalOverlay').style.display = 'none';
  const uhList = document.getElementById('upcomingHazardsList');
  if (uhList) uhList.style.display = 'none';
  
  document.getElementById('findRouteBtn').style.display = 'flex';
  document.getElementById('recalcRouteBtn').style.display = 'none';
  document.getElementById('clearRouteBtn').style.display = 'none';
}

function createSafetySegments(coords) {
  if (!dynamicRouteLayers) {
    dynamicRouteLayers = L.layerGroup().addTo(navMap);
  } else {
    dynamicRouteLayers.clearLayers();
  }
  
  // 1. Split route into ~30m segments
  let segmentedPoints = [coords[0]];
  for (let i = 0; i < coords.length - 1; i++) {
    let p1 = coords[i];
    let p2 = coords[i+1];
    let dist = haversineDist(p1[0], p1[1], p2[0], p2[1]);
    if (dist > 30) {
      let segmentsCount = Math.ceil(dist / 30);
      for (let j = 1; j <= segmentsCount; j++) {
        let lat = p1[0] + (p2[0] - p1[0]) * (j / segmentsCount);
        let lng = p1[1] + (p2[1] - p1[1]) * (j / segmentsCount);
        segmentedPoints.push([lat, lng]);
      }
    } else {
      segmentedPoints.push(p2);
    }
  }

  // 2. Evaluate colors
  const RADIUS = 50;
  let coloredSegments = [];
  for (let i = 0; i < segmentedPoints.length - 1; i++) {
    let p1 = segmentedPoints[i];
    let p2 = segmentedPoints[i+1];
    let midLat = (p1[0] + p2[0]) / 2;
    let midLng = (p1[1] + p2[1]) / 2;
    
    let color = '#22c55e'; // Green
    let hasMedium = false;
    let hasHigh = false;
    
    for (let h of allHazardsData) {
      let hLat = parseFloat(h.latitude);
      let hLng = parseFloat(h.longitude);
      if (isNaN(hLat) || isNaN(hLng)) continue;
      
      let d = haversineDist(midLat, midLng, hLat, hLng);
      if (d <= RADIUS) {
        let sev = (h.severity || 'low').toLowerCase();
        if (sev === 'critical' || sev === 'high') hasHigh = true;
        if (sev === 'medium') hasMedium = true;
      }
    }
    
    if (hasHigh) color = '#ef4444'; // Red
    else if (hasMedium) color = '#eab308'; // Yellow
    
    coloredSegments.push({ p1, p2, color });
  }

  // 3. Merge consecutive same colors
  let mergedLines = [];
  if (coloredSegments.length > 0) {
    let currentLine = [coloredSegments[0].p1, coloredSegments[0].p2];
    let currentColor = coloredSegments[0].color;
    
    for (let i = 1; i < coloredSegments.length; i++) {
      if (coloredSegments[i].color === currentColor) {
        currentLine.push(coloredSegments[i].p2);
      } else {
        mergedLines.push({ coords: currentLine, color: currentColor });
        currentLine = [coloredSegments[i].p1, coloredSegments[i].p2];
        currentColor = coloredSegments[i].color;
      }
    }
    mergedLines.push({ coords: currentLine, color: currentColor });
  }

  // 4. Draw
  mergedLines.forEach(line => {
    L.polyline(line.coords, {
      color: line.color,
      weight: 8,
      opacity: 0.9,
      lineJoin: 'round',
      lineCap: 'round',
      pane: 'routePane'
    }).addTo(dynamicRouteLayers);
  });

  // 5. Update Progress Bar Background Gradient
  let totalSegDist = 0;
  mergedLines.forEach(line => {
    let d = 0;
    for(let i=0; i<line.coords.length-1; i++){
      d += haversineDist(line.coords[i][0], line.coords[i][1], line.coords[i+1][0], line.coords[i+1][1]);
    }
    line.dist = d;
    totalSegDist += d;
  });

  let gradientStops = [];
  let currentPct = 0;
  mergedLines.forEach(line => {
    let pctSpan = (line.dist / totalSegDist) * 100;
    gradientStops.push(`${line.color} ${currentPct}%`);
    currentPct += pctSpan;
    gradientStops.push(`${line.color} ${currentPct}%`);
  });

  const bgEl = document.getElementById('navProgressBg');
  if (bgEl) {
    if (gradientStops.length > 0) {
      bgEl.style.background = `linear-gradient(to right, ${gradientStops.join(', ')})`;
    } else {
      bgEl.style.background = '#334155';
    }
  }
}

function drawRoute(data) {
  const { recommended_route, route, distance, duration, safety_score, alternatives } = data;
  const finalRoute = recommended_route || route;
  
  if (!finalRoute || finalRoute.length < 2) return;
  
  originalRouteCoords = [...finalRoute];
  currentRouteCoords = [...finalRoute];
  // Calculate total route distance dynamically from geometry to ensure accuracy in meters
  currentRouteTotalDist = 0;
  for (let i = 0; i < finalRoute.length - 1; i++) {
    currentRouteTotalDist += L.latLng(finalRoute[i]).distanceTo(L.latLng(finalRoute[i+1]));
  }
  initialRouteDuration = duration;

  // Clear old
  if (safeRouteLayer) navMap.removeLayer(safeRouteLayer);
  if (completedRouteLayer) navMap.removeLayer(completedRouteLayer);
  if (dynamicRouteLayers) dynamicRouteLayers.clearLayers();
  altRouteLayers.forEach(l => navMap.removeLayer(l));
  altRouteLayers = [];

  // Draw Alternatives
  if (alternatives && alternatives.length > 0) {
      alternatives.forEach((alt) => {
          let poly = L.polyline(alt.route_latlon, { color: '#9ca3af', weight: 6, opacity: 0.6, lineJoin: 'round', lineCap: 'round', pane: 'routePane' }).addTo(navMap);
          altRouteLayers.push(poly);
      });
  }

  // Draw Dynamic Safety Segments
  createSafetySegments(finalRoute);

  // Invisible layer for logic/math
  safeRouteLayer = L.polyline(finalRoute, { color: 'transparent', weight: 8, opacity: 0, pane: 'routePane' }).addTo(navMap);
  
  // Completed layer drawn OVER dynamic routes (darker color to mask it)
  completedRouteLayer = L.polyline([], { color: '#1a1f27', weight: 10, opacity: 0.85, lineJoin: 'round', lineCap: 'round', pane: 'routePane' }).addTo(navMap);

  autoFitMap(); // zoom to worker + dest

  // Stats init
  document.getElementById('statEtaTime').textContent = Math.round(duration / 60) || 1;
  document.getElementById('statDistLeft').textContent = (currentRouteTotalDist / 1000).toFixed(1);
  document.getElementById('statSafety').textContent = safety_score || 100;
  
  let arrival = new Date(Date.now() + duration * 1000);
  document.getElementById('statArrivalTime').textContent = arrival.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

  // Show UI
  document.getElementById('navActiveCard').style.display = 'block';
  const uhList = document.getElementById('upcomingHazardsList');
  if (uhList) uhList.style.display = 'block';
  
  document.getElementById('findRouteBtn').style.display = 'none';
  document.getElementById('recalcRouteBtn').style.display = 'flex';
  document.getElementById('clearRouteBtn').style.display = 'flex';

  document.getElementById('navProgressFill').style.width = '0%';
  document.getElementById('navProgressPct').textContent = '0%';
  document.getElementById('navProgressTravelled').textContent = '0 km';
  document.getElementById('navProgressRemaining').textContent = (currentRouteTotalDist / 1000).toFixed(1) + ' km left';

  // Trigger smart render of potholes based on new route geometry
  renderPotholes();
}

function startNavigation(data) {
  isNavigating = true;
}

/* â”€â”€ Live Route Progress â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function updateNavigationProgress(lat, lng) {
  if (!safeRouteLayer || !isNavigating || currentRouteCoords.length < 2) return;

  // Find closest point on route
  const currentLatLng = L.latLng(lat, lng);
  
  // Use leaflet.geometryutil if loaded, otherwise fallback
  let closestPoint;
  if (typeof L.GeometryUtil !== 'undefined') {
    closestPoint = L.GeometryUtil.closest(navMap, safeRouteLayer, currentLatLng);
  } else {
    closestPoint = L.latLng(currentRouteCoords[0]); 
  }

  if (!closestPoint) return;

  // 1. Check deviation distance
  const deviation = currentLatLng.distanceTo(closestPoint);
  if (deviation > NAV_CFG.recalcDist) {
    const now = Date.now();
    if (now - lastRecalcTime > 10000 && !isRecalculating) { // 10s cooldown
      lastRecalcTime = now;
      findSafeRoute(true); // Trigger Recalc
      return;
    }
  }

  // 2. Check Arrival
  const destLatLng = L.latLng(currentRouteCoords[currentRouteCoords.length - 1]);
  if (currentLatLng.distanceTo(destLatLng) < NAV_CFG.arrivalDist) {
    handleArrival();
    return;
  }

  // 3. Split Route (Green completed, Blue remaining)
  let splitIndex = 0;
  let minDist = Infinity;
  currentRouteCoords.forEach((coord, idx) => {
    let d = L.latLng(coord).distanceTo(closestPoint);
    if (d < minDist) { minDist = d; splitIndex = idx; }
  });

  const completedCoords = currentRouteCoords.slice(0, splitIndex + 1);
  completedCoords.push([closestPoint.lat, closestPoint.lng]);
  
  const remainingCoords = [[closestPoint.lat, closestPoint.lng], ...currentRouteCoords.slice(splitIndex + 1)];

  completedRouteLayer.setLatLngs(completedCoords);

  // Keep the visible remaining route updated,
  // but never modify the original route coordinates.
  safeRouteLayer.setLatLngs(remainingCoords);

  // 4. Calculate Distance Travelled & Remaining
  // Calculate travelled distance from the original full route
  let distTravelled = 0;

  // Distance up to the split point
  for (let i = 0; i < splitIndex; i++) {
      distTravelled += L.latLng(originalRouteCoords[i]).distanceTo(
          L.latLng(originalRouteCoords[i + 1])
      );
  }

  // Distance from split vertex to current GPS position
  distTravelled += L.latLng(originalRouteCoords[splitIndex]).distanceTo(closestPoint);

  // Remaining distance
  let displayRemaining = Math.max(0, currentRouteTotalDist - distTravelled);
  
  // Clamp values
  if (distTravelled < 0) distTravelled = 0;
  if (displayRemaining < 0) displayRemaining = 0;
  
  // Progress = (Travelled Distance / Total Route Distance) * 100
  let pct = 0;
  if (currentRouteTotalDist > 0) {
      pct = (distTravelled / currentRouteTotalDist) * 100;
  }
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  pct = Math.round(pct);

  // Preserve the old distRemaining strictly for ETA and Distance Left calculations to avoid regressions
  let distRemaining = 0;
  for(let i = 0; i < remainingCoords.length - 1; i++) {
    distRemaining += L.latLng(remainingCoords[i]).distanceTo(L.latLng(remainingCoords[i+1]));
  }

  // 5. Update ETA
  let etaSeconds = 0;
  if (currentSpeed > 1) { // > 1 m/s (~3.6 km/h)
    etaSeconds = distRemaining / currentSpeed;
  } else {
    // use initial average speed
    const avgSpeed = currentRouteTotalDist / initialRouteDuration;
    etaSeconds = distRemaining / avgSpeed;
  }

  if (isNaN(etaSeconds) || !isFinite(etaSeconds)) etaSeconds = initialRouteDuration;

  const etaMinutes = Math.max(1, Math.round(etaSeconds / 60));
  const arrivalDate = new Date(Date.now() + etaSeconds * 1000);

  // 6. Update DOM
  document.getElementById('statEtaTime').textContent = etaMinutes;
  document.getElementById('statDistLeft').textContent = (distRemaining / 1000).toFixed(1);
  document.getElementById('statArrivalTime').textContent = arrivalDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

  // Update Visual Progress Bar
  const vehicleMarker = document.getElementById('navVehicleMarker');
  if (vehicleMarker) vehicleMarker.style.left = pct + '%';
  const progressFill = document.getElementById('navProgressFill');
  if (progressFill) progressFill.style.width = pct + '%';

  // Update Text Labels
  document.getElementById('navProgressPct').textContent = pct + '%';
  document.getElementById('navProgressTravelled').textContent = (distTravelled / 1000).toFixed(1) + ' km';
  document.getElementById("navProgressRemaining").textContent = Math.max(0, displayRemaining / 1000).toFixed(1) + " km";
  
  // 7. Update Hazard List
  updateUpcomingHazards(remainingCoords, currentSpeed > 1 ? currentSpeed : (currentRouteTotalDist / initialRouteDuration));
}

function highlightHazardMarker(id) {
  const targetLayer = Object.values(navMap._layers).find(l => 
    l.options && l.options.pane === 'hazardPane' && l._popup && l._popup._content.includes(`Report #${id}`)
  );
  if (targetLayer && targetLayer._icon) {
    targetLayer._icon.style.filter = 'brightness(1.5) drop-shadow(0 0 10px rgba(255,255,255,0.8))';
    targetLayer._icon.style.transform = 'scale(1.2)';
    targetLayer._icon.style.transition = 'all 0.2s';
    targetLayer.setZIndexOffset(1000);
  }
}

function unhighlightHazardMarker(id) {
  const targetLayer = Object.values(navMap._layers).find(l => 
    l.options && l.options.pane === 'hazardPane' && l._popup && l._popup._content.includes(`Report #${id}`)
  );
  if (targetLayer && targetLayer._icon) {
    targetLayer._icon.style.filter = '';
    targetLayer._icon.style.transform = '';
    targetLayer.setZIndexOffset(0);
  }
}

function focusUpcomingHazard(id) {
  const targetLayer = Object.values(navMap._layers).find(l => 
    l.options && l.options.pane === 'hazardPane' && l._popup && l._popup._content.includes(`Report #${id}`)
  );
  if (targetLayer) {
    navMap.flyTo(targetLayer.getLatLng(), 18, { animate: true, duration: 1 });
    setTimeout(() => {
      targetLayer.openPopup();
      if (targetLayer._icon) {
        targetLayer._icon.classList.add('marker-pulse');
        setTimeout(() => targetLayer._icon.classList.remove('marker-pulse'), 2000);
      }
    }, 1000);
  }
}

function updateUpcomingHazards(remainingCoords, speed) {
  const listContainer = document.getElementById('upcomingHazardsList');
  if (!listContainer) return;

  if (remainingCoords.length < 2) {
    listContainer.style.display = 'none';
    return;
  }

  const RADIUS = 50; // meters
  let upcoming = [];
  let distToHazardPath = 0;
  let seenIds = new Set();

  for (let i = 0; i < remainingCoords.length - 1; i++) {
    let p1 = remainingCoords[i];
    let p2 = remainingCoords[i+1];
    let segmentDist = haversineDist(p1[0], p1[1], p2[0], p2[1]);
    
    for (let h of allHazardsData) {
      if (seenIds.has(h.id)) continue;
      
      let hLat = parseFloat(h.latitude);
      let hLng = parseFloat(h.longitude);
      if (isNaN(hLat) || isNaN(hLng)) continue;
      
      let d = haversineDist(p2[0], p2[1], hLat, hLng);
      if (d <= RADIUS) {
        upcoming.push({ hazard: h, dist: distToHazardPath + segmentDist });
        seenIds.add(h.id);
      }
    }
    distToHazardPath += segmentDist;
  }

  if (upcoming.length === 0) {
    listContainer.style.display = 'block';
    listContainer.innerHTML = `
      <div class="hazard-clear">
        <i class="fa-solid fa-circle-check"></i>
        <div style="font-size:1.1rem; font-weight:800; color:#fff;">Route Clear</div>
        <div style="font-size:0.85rem; margin-top:4px;">No upcoming hazards detected.<br>You are travelling on the safest available route.</div>
      </div>
    `;
    return;
  }

  upcoming.sort((a, b) => a.dist - b.dist);

  let html = '';
  upcoming.forEach((item, index) => {
    const h = item.hazard;
    const dPath = item.dist;
    const sev = (h.severity || 'low').toLowerCase();
    
    let hColor = '#22c55e'; let riskText = 'Low Risk';
    if (sev === 'medium') { hColor = '#eab308'; riskText = 'Medium Risk'; }
    if (sev === 'high' || sev === 'critical') { hColor = '#ef4444'; riskText = 'High Risk'; }

    const typeLabel = h.type === 'user_report' ? 'Citizen Report' : 'Pothole';
    const displayImg = h.image_url || h.media_url || h.annotated_image_url || '';
    const imgHtml = displayImg 
      ? `<img src="${displayImg}" class="hazard-thumb" onclick="event.stopPropagation(); window.open('${displayImg}','_blank')">` 
      : `<div class="hazard-thumb" style="display:flex;align-items:center;justify-content:center;color:#94a3b8;"><i class="fa-solid fa-image-slash"></i></div>`;

    let distText = dPath < 1000 ? `${Math.round(dPath)} m` : `${(dPath/1000).toFixed(1)} km`;
    let etaSec = speed > 0 ? dPath / speed : 0;
    let etaText = '--';
    if (etaSec > 0) {
      if (etaSec < 60) etaText = `${Math.round(etaSec)} sec`;
      else etaText = `${Math.round(etaSec/60)} min`;
    }

    const roadNameStr = h.road_name ? `<div class="hazard-metric">Road <strong>${h.road_name}</strong></div>` : '';
    const isHighRiskClose = index === 0 && (sev === 'high' || sev === 'critical') && dPath <= 100;
    const confText = h.confidence ? `${Math.round(h.confidence)}%` : (h.ai_confidence ? `${Math.round(h.ai_confidence)}%` : 'N/A');
    const reportCount = h.report_count || 1;
    const reportStr = h.type === 'user_report' ? `${reportCount} Citizen(s)` : `${reportCount} Detection(s)`;
    const idStr = h.id ? `#${h.id}` : 'N/A';

    html += `
      <div class="hazard-card" style="border-left-color:${hColor};" 
           onmouseenter="highlightHazardMarker('${h.id}')" 
           onmouseleave="unhighlightHazardMarker('${h.id}')" 
           onclick="focusUpcomingHazard('${h.id}')">
        <div class="hazard-header">
          <div class="hazard-title"><i class="fa-solid fa-triangle-exclamation" style="color:${hColor}"></i> ${typeLabel}</div>
          <div style="font-size:12px; background:rgba(255,255,255,0.1); padding:2px 8px; border-radius:12px; font-weight:700; color:${hColor}">${riskText}</div>
        </div>
        <div class="hazard-body">
          ${imgHtml}
          <div class="hazard-details">
            <div class="hazard-metric">ID <strong>${idStr}</strong></div>
            ${roadNameStr}
            <div class="hazard-metric">Distance <strong>${distText} Ahead</strong></div>
            <div class="hazard-metric">ETA <strong>${etaText}</strong></div>
            <div class="hazard-metric">Confidence <strong>${confText}</strong></div>
            <div class="hazard-metric">Reports <strong>${reportStr}</strong></div>
          </div>
        </div>
        ${isHighRiskClose ? `<div class="hazard-alert">⚠ HIGH RISK AHEAD - Reduce Speed!</div>` : ''}
      </div>
    `;
  });

  listContainer.style.display = 'block';
  listContainer.innerHTML = html;
}

function handleArrival() {
  if (!isNavigating) return;
  isNavigating = false;
  document.getElementById('arrivalOverlay').style.display = 'flex';
}

function markAsReached() {
  alert('Worker status updated: Reached Site.');
  window.location.reload();
}

/* â”€â”€ UI Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function recenterMap() {
  if (isNavigating) {
    autoFitMap();
  } else if (userLatLon) {
    navMap.setView(userLatLon, 17);
  } else if (safeRouteLayer) {
    navMap.fitBounds(safeRouteLayer.getBounds());
  }
}
function zoomInMap() { navMap.zoomIn(); }
function zoomOutMap() { navMap.zoomOut(); }
function toggleFullScreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(e => console.error(e));
  } else {
    if (document.exitFullscreen) document.exitFullscreen();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initNavMap();
  setClickMode('start');
});

