import re
with open('static/js/navigation.js', 'r', encoding='utf-8') as f:
    content = f.read()

bad_string = '''  // 4. Calculate Distance Travelled & Remaining
  let distTravelled = 0;
  for(let i=0; i<completedCoords.length-1; i++) {
    distTravelled += L.latLng(cofunction highlightHazardMarker(id) {'''

good_string = '''  // 4. Calculate Distance Travelled & Remaining
  let distTravelled = 0;
  for(let i=0; i<completedCoords.length-1; i++) {
    distTravelled += L.latLng(completedCoords[i]).distanceTo(L.latLng(completedCoords[i+1]));
  }
  let distRemaining = 0;
  for(let i=0; i<remainingCoords.length-1; i++) {
    distRemaining += L.latLng(remainingCoords[i]).distanceTo(L.latLng(remainingCoords[i+1]));
  }

  const total = distTravelled + distRemaining;
  const pct = total > 0 ? Math.min(100, Math.round((distTravelled / total) * 100)) : 0;

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

  document.getElementById('navProgressFill').style.width = pct + '%';
  document.getElementById('navProgressPct').textContent = pct + '%';
  document.getElementById('navProgressTravelled').textContent = (distTravelled / 1000).toFixed(1) + ' km';
  document.getElementById('navProgressRemaining').textContent = (distRemaining / 1000).toFixed(1) + ' km left';
  
  // 7. Update Hazard List
  updateUpcomingHazards(remainingCoords, currentSpeed > 1 ? currentSpeed : (currentRouteTotalDist / initialRouteDuration));
}

function highlightHazardMarker(id) {'''

content = content.replace(bad_string, good_string)

with open('static/js/navigation.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed navigation progress logic')
