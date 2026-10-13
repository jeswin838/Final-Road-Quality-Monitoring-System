import os
import re

normalize_fn = """
// --- ID Normalization Layer ---
function normalizeHazardId(id, source = null) {
    if (!id) return id;
    let strId = String(id);
    if (strId.startsWith('AI-') || strId.startsWith('USER-')) return strId;
    if (!isNaN(strId)) {
        if (source && (source.toLowerCase() === 'user_reports' || source.toLowerCase() === 'user' || source.toLowerCase() === 'citizen')) {
            return `USER-${strId}`;
        }
        return `AI-${strId}`;
    }
    return strId;
}
// ------------------------------
"""

base_dir = r"c:\New folder\project Copies\Road-Quality-Monitoring-System-main"
map_js_path = os.path.join(base_dir, "static", "js", "map.js")
alerts_html_path = os.path.join(base_dir, "templates", "alerts.html")

# Fix map.js
with open(map_js_path, "r", encoding="utf-8") as f:
    map_content = f.read()

if "function normalizeHazardId" not in map_content:
    map_content = map_content.replace("// ── State ───────────────────────────────────────────────────────────────────", normalize_fn + "\n// ── State ───────────────────────────────────────────────────────────────────")

# 1. targetHazardId match
map_content = map_content.replace(
    "if (targetHazardId && String(group.id) === String(targetHazardId)) {",
    "if (targetHazardId && (String(group.id) === String(targetHazardId) || String(group.id) === normalizeHazardId(targetHazardId, group.source))) {"
)

# 2. reports some match
map_content = map_content.replace(
    "if (group.reports.some(r => String(r.id) === String(searchId) || String(r.hazard_id) === String(searchId))) {",
    "if (group.reports.some(r => String(r.id) === String(searchId) || String(r.hazard_id) === String(searchId) || String(r.id) === normalizeHazardId(searchId, group.source))) {"
)

# 3. r.id search
map_content = map_content.replace(
    "if (r.id && String(r.id) === search_id) {",
    "if (r.id && (String(r.id) === search_id || String(r.id) === normalizeHazardId(search_id, r.source))) {"
)

# 4. r.hazard_id search
map_content = map_content.replace(
    "if (r.hazard_id && String(r.hazard_id) === search_id) {",
    "if (r.hazard_id && (String(r.hazard_id) === search_id || String(r.hazard_id) === normalizeHazardId(search_id, r.source))) {"
)

# 5. sub_r.id search
map_content = map_content.replace(
    "if (String(sub_r.id) === search_id || String(sub_r.hazard_id) === search_id) {",
    "if (String(sub_r.id) === search_id || String(sub_r.hazard_id) === search_id || String(sub_r.id) === normalizeHazardId(search_id, r.source)) {"
)

with open(map_js_path, "w", encoding="utf-8") as f:
    f.write(map_content)


# Fix alerts.html
with open(alerts_html_path, "r", encoding="utf-8") as f:
    alerts_content = f.read()

if "function normalizeHazardId" not in alerts_content:
    alerts_content = alerts_content.replace("<script>", "<script>\n" + normalize_fn)

alerts_content = alerts_content.replace(
    "if (selectedHazardId && !allHazards.find(h => (h.hazard_id || h.id) == selectedHazardId)) {",
    "if (selectedHazardId && !allHazards.find(h => (h.hazard_id || h.id) == selectedHazardId || String(h.hazard_id || h.id) === normalizeHazardId(selectedHazardId, h.source))) {"
)

alerts_content = alerts_content.replace(
    "const hz = allHazards.find(h => (h.hazard_id || h.id) == selectedHazardId);",
    "const hz = allHazards.find(h => (h.hazard_id || h.id) == selectedHazardId || String(h.hazard_id || h.id) === normalizeHazardId(selectedHazardId, h.source));"
)

alerts_content = alerts_content.replace(
    "const h = allHazards.find(x => (x.hazard_id || x.id) == id);",
    "const h = allHazards.find(x => (x.hazard_id || x.id) == id || String(x.hazard_id || x.id) === normalizeHazardId(id, x.source));"
)

alerts_content = alerts_content.replace(
    "if (selectedHazardId && (selectedHazardId == updated.id || selectedHazardId == updated.hazard_id)) {",
    "if (selectedHazardId && (selectedHazardId == updated.id || selectedHazardId == updated.hazard_id || normalizeHazardId(selectedHazardId, updated.source) === String(updated.id))) {"
)

with open(alerts_html_path, "w", encoding="utf-8") as f:
    f.write(alerts_content)

print("ID normalizations applied.")
