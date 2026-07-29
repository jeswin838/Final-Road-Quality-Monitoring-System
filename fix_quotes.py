import re

with open('static/js/map.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix showReports(${r.id}) -> showReports('${r.id}')
content = content.replace('onclick="showReports(${r.id})"', r'onclick="showReports(\'${r.id}\')"')

# Fix openAssignModal(${r.id}, ...)
content = content.replace('openAssignModal(${r.id},', r'openAssignModal(\'${r.id}\',')

with open('static/js/map.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed unquoted ${r.id} in map.js')
