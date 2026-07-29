import re

with open('static/js/navigation.js', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'function updateUpcomingHazards\(remainingCoords, speed\) \{.*?(?=function handleArrival\(\) \{)', re.DOTALL)

new_code = '''function updateUpcomingHazards(remainingCoords, speed) {
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

'''

content = pattern.sub(new_code, content)

with open('static/js/navigation.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed updateUpcomingHazards logic')
