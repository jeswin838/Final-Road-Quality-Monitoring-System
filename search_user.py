import os
import re

for root, dirs, files in os.walk('.'):
    if 'node_modules' in root or '.git' in root or 'venv' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.html') or file.endswith('.js'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # We also want to find 'USER' in addEventListener or innerHTML
                # Let's just find the string USER not in quotes
                matches = re.finditer(r'\bUSER\b', content)
                for m in matches:
                    start = max(0, m.start() - 30)
                    end = min(len(content), m.end() + 30)
                    print(f"{filepath}: {content[start:end]}")
