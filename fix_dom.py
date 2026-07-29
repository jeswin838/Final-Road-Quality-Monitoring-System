import re

with open('templates/navigation.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Strip the exact upcomingHazardsList block from wherever it is.
pattern_haz = re.compile(r'<!-- Upcoming Hazards List -->\s*<div id="upcomingHazardsList"></div>')
content = pattern_haz.sub('', content)

# 2. Extract the .nav-bottom-right block and rebuild it.
pattern_br = re.compile(r'(<div class="nav-bottom-right">.*?</div>\s*</div>)', re.DOTALL)

new_bottom_right = '''  <div class="nav-bottom-right">

    <div class="floating-panel legend-panel">
      <div class="legend-item"><div class="leg-line" style="background: #22c55e;"></div> 🟢 Safe Road</div>
      <div class="legend-item"><div class="leg-line" style="background: #eab308;"></div> 🟡 Medium Risk</div>
      <div class="legend-item"><div class="leg-line" style="background: #ef4444;"></div> 🔴 High Risk</div>
      <div class="legend-item"><div class="leg-color" style="background: #3b82f6;"></div> 🚶 Worker</div>
      <div class="legend-item"><i class="fa-solid fa-bullseye" style="color: #ef4444;"></i> 🎯 Destination</div>
    </div>

    <!-- Upcoming Hazards List -->
    <div id="upcomingHazardsList"></div>
    
    <div class="map-controls">
      <button class="map-ctrl-btn" onclick="recenterMap()" title="Recenter"><i class="fa-solid fa-crosshairs"></i></button>
      <button class="map-ctrl-btn" onclick="zoomInMap()" title="Zoom In"><i class="fa-solid fa-plus"></i></button>
      <button class="map-ctrl-btn" onclick="zoomOutMap()" title="Zoom Out"><i class="fa-solid fa-minus"></i></button>
      <button class="map-ctrl-btn" onclick="toggleFullScreen()" title="Full Screen"><i class="fa-solid fa-expand"></i></button>
    </div>

  </div>'''

content = pattern_br.sub(new_bottom_right, content)

with open('templates/navigation.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated DOM structure for UpcomingHazardsList')
