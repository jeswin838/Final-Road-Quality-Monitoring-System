// ═══════════════════════════════════════════════════════════════════════════
// report.js — User Reporting Module logic
// ═══════════════════════════════════════════════════════════════════════════

let stream = null;
let capturedBlob = null;
let currentCoords = null;
let gpsAccuracy = null;
let useFacingMode = 'environment';
let analysisResult = null;
let captureSource = 'live_camera';
const strictLiveCaptureOnly = !!(window.REPORT_SECURITY && window.REPORT_SECURITY.strictLiveCaptureOnly);

const video = document.getElementById('cameraStream');
const canvas = document.createElement('canvas');
const preview = document.getElementById('capturedPreview');
const captureBtn = document.getElementById('captureBtn');
const retakeBtn = document.getElementById('retakeBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const submitBtn = document.getElementById('submitBtn');
const gpsStatus = document.getElementById('gpsStatus');
const resultCard = document.getElementById('analyzeResultCard');
const resultImg = document.getElementById('resultPreviewImage');
const resultMeta = document.getElementById('resultMeta');
const resultBadge = document.getElementById('resultStatusBadge');

/* ── Camera Logic ────────────────────────────────────────────────────────── */
async function startCamera() {
  try {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: useFacingMode },
      audio: false
    });
    video.srcObject = stream;
    video.style.display = 'block';
    preview.style.display = 'none';
  } catch (err) {
    console.error("Camera error:", err);
    showToast("Could not access camera. Please use file upload.", "error");
  }
}

function captureImage() {
  const track = stream && stream.getVideoTracks ? stream.getVideoTracks()[0] : null;

  // Prefer ImageCapture to keep original camera quality.
  if (track && 'ImageCapture' in window) {
    const imageCapture = new ImageCapture(track);
    imageCapture.takePhoto()
      .then((blob) => {
        capturedBlob = blob; // original-quality capture blob
        captureSource = 'live_camera';
        const url = URL.createObjectURL(blob);
        preview.src = url;
        preview.style.display = 'block';
        video.style.display = 'none';
        captureBtn.style.display = 'none';
        retakeBtn.style.display = 'flex';
        checkSubmitReady();
      })
      .catch(() => {
        // Fallback only if ImageCapture fails.
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        canvas.toBlob((blob) => {
          capturedBlob = blob;
          captureSource = 'live_camera';
          const url = URL.createObjectURL(blob);
          preview.src = url;
          preview.style.display = 'block';
          video.style.display = 'none';
          captureBtn.style.display = 'none';
          retakeBtn.style.display = 'flex';
          checkSubmitReady();
        }, 'image/png');
      });
    return;
  }

  // Legacy fallback (avoid lossy JPEG recompression).
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob((blob) => {
    capturedBlob = blob;
    captureSource = 'live_camera';
    const url = URL.createObjectURL(blob);
    preview.src = url;
    preview.style.display = 'block';
    video.style.display = 'none';
    captureBtn.style.display = 'none';
    retakeBtn.style.display = 'flex';
    checkSubmitReady();
  }, 'image/png');
}

function retake() {
  capturedBlob = null;
  analysisResult = null;
  preview.style.display = 'none';
  video.style.display = 'block';
  captureBtn.style.display = 'flex';
  retakeBtn.style.display = 'none';
  if (resultCard) resultCard.style.display = 'none';
  checkSubmitReady();
}

function setCaptureMode(mode) {
  captureSource = mode;
}

/* ── GPS Logic ───────────────────────────────────────────────────────────── */
function initGPS() {
  if (!navigator.geolocation) {
    gpsStatus.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> GPS not supported';
    gpsStatus.className = 'gps-status searching';
    return;
  }

  navigator.geolocation.watchPosition(
    (pos) => {
      currentCoords = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude
      };
      gpsAccuracy = pos.coords.accuracy ?? null;
      document.getElementById('latInput').value = currentCoords.lat.toFixed(6);
      document.getElementById('lonInput').value = currentCoords.lon.toFixed(6);
      
      gpsStatus.innerHTML = '<i class="fa-solid fa-circle-check"></i> GPS Location Ready';
      gpsStatus.className = 'gps-status ready';
      checkSubmitReady();
    },
    (err) => {
      console.warn("GPS Error:", err);
      gpsStatus.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> GPS Error: ' + err.message;
      gpsStatus.className = 'gps-status searching';
    },
    { enableHighAccuracy: true }
  );
}

/* ── Submission Logic ────────────────────────────────────────────────────── */
function checkSubmitReady() {
  analyzeBtn.disabled = !(capturedBlob && currentCoords);
  submitBtn.disabled = !analysisResult;
}

async function handleAnalyze() {
  if (!capturedBlob || !currentCoords) return;

  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
  submitBtn.disabled = true;
  analysisResult = null;

  const formData = new FormData();
  formData.append('image', capturedBlob, 'capture.jpg');
  formData.append('lat', currentCoords.lat);
  formData.append('lon', currentCoords.lon);
  formData.append('description', document.getElementById('descInput').value);
  formData.append('capture_source', captureSource === 'gallery_upload' ? 'upload' : 'live');
  if (gpsAccuracy !== null) formData.append('gps_accuracy', gpsAccuracy);

  try {
    const res = await fetch('/user-report', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (res.ok) {
      analysisResult = data;
      renderAnalyzeResult(data);
      showToast(`Analysis complete: ${formatStatus(data.status)}`, data.status === 'approved' ? 'success' : data.status === 'rejected' ? 'error' : 'warning');
      
      // Auto-submit only for >= 50% confidence (high/medium). 30-49% requires manual click.
      if (data.status === 'approved' || (data.status === 'pending' && data.confidence >= 0.50)) {
        setTimeout(() => {
            handleSubmit();
        }, 1500);
      }
    } else {
      showToast(data.error || "Inference failed", "error");
    }
  } catch (err) {
    showToast("Network error occurred", "error");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Analyze';
    checkSubmitReady();
  }
}

function formatStatus(status) {
  if (!status) return 'Pending';
  if (status === 'approved') return 'Auto Approved';
  if (status === 'pending') return 'Pending Admin Review';
  if (status === 'rejected') return 'Rejected';
  return status;
}

function renderAnalyzeResult(data) {
  if (!resultCard) return;
  resultCard.style.display = 'block';

  const status = data.status || 'pending';
  const badgeColor = status === 'approved' ? 'var(--success)' : status === 'rejected' ? 'var(--danger)' : 'var(--warning)';
  const confidence = typeof data.confidence === 'number' ? `${Math.round(data.confidence * 100)}%` : '0%';
  const isPothole = data.pothole_detected || data.detections?.length > 0;

  resultBadge.textContent = formatStatus(status);
  resultBadge.style.background = badgeColor;
  resultBadge.style.color = '#fff';
  resultBadge.style.border = '1px solid rgba(255,255,255,0.2)';

  if (data.annotated_image_url) {
    resultImg.src = data.annotated_image_url;
    resultImg.style.display = 'block';
  }

  // Build a status-specific guidance note
  let statusNote = '';
  if (status === 'approved') {
    statusNote = `<div style="margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.25);font-size:0.78rem;color:#4ade80">
      <i class="fa-solid fa-circle-check"></i> <b>Auto-Approved:</b> High confidence detection. <i class="fa-solid fa-spinner fa-spin"></i> Auto-submitting to publish live...
    </div>`;
  } else if (status === 'pending') {
    if (data.confidence >= 0.50) {
      statusNote = `<div style="margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.25);font-size:0.78rem;color:#fbbf24">
        <i class="fa-solid fa-clock"></i> <b>Pending Review:</b> Medium confidence. <i class="fa-solid fa-spinner fa-spin"></i> Auto-submitting for admin verification...
      </div>`;
    } else {
      statusNote = `<div style="margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.25);font-size:0.78rem;color:#fbbf24">
        <i class="fa-solid fa-clock"></i> <b>Pending Review (Low Confidence):</b> This detection requires admin review. Click <b>Submit Report</b> below to send it to the admin queue.
      </div>`;
    }
  } else if (status === 'rejected') {
    statusNote = `<div style="margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.25);font-size:0.78rem;color:#f87171">
      <i class="fa-solid fa-circle-xmark"></i> <b>Rejected:</b> No pothole detected with sufficient confidence. This report will not be submitted.
    </div>`;
  }

  resultMeta.innerHTML = `
    <div><i class="fa-solid fa-check-circle" style="color:var(--success)"></i> AI Detection: <b>${isPothole ? '✔ Pothole Detected' : 'No Pothole Detected'}</b></div>
    <div><i class="fa-solid fa-chart-line"></i> Confidence: <b>${confidence}</b></div>
    <div><i class="fa-solid fa-gauge-high"></i> Severity: <b>${(data.severity && data.severity.toLowerCase() !== 'null' && data.severity.toLowerCase() !== 'none') ? data.severity.toUpperCase() : 'N/A'}</b></div>
    <div><i class="fa-solid fa-info-circle"></i> Status: <b>${formatStatus(status)}</b></div>
    <div><i class="fa-solid fa-clipboard-check"></i> Review Required: <b>${data.review_required ? 'YES' : 'NO'}</b></div>
    ${statusNote}
  `;

  // Hide submit button for rejected reports — nothing to submit
  if (submitBtn) {
    submitBtn.style.display = status === 'rejected' ? 'none' : 'flex';
  }
}

async function handleSubmit() {
  if (!analysisResult) return;

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

  try {
    const res = await fetch('/user-report/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(analysisResult)
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = data.detail ? ` (${data.detail})` : '';
      showToast((data.error || 'Save failed') + detail, 'error');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Report';
      return;
    }

    // Show status-appropriate message and redirect
    const savedStatus = data.status || analysisResult.status || 'pending';
    if (savedStatus === 'approved') {
      showToast('✔ Auto-Approved! Your report is now live on the map.', 'success', 4000);
    } else if (savedStatus === 'pending') {
      showToast('✔ Report Submitted — Awaiting Admin Verification', 'warning', 4000);
    } else if (savedStatus === 'rejected') {
      showToast('Report was rejected (no pothole detected with sufficient confidence).', 'error', 5000);
    } else {
      showToast('✔ Report Submitted Successfully', 'success');
    }
    setTimeout(() => window.location.href = '/', 2000);
  } catch (err) {
    showToast('Network error occurred', 'error');
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Report';
  }
}

/* ── File Upload Fallback Removed ─────────────────────────────────────── */

/* ── Boot ────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  startCamera();
  initGPS();
  setCaptureMode('live_camera');

  captureBtn.onclick = captureImage;
  retakeBtn.onclick = retake;
  analyzeBtn.onclick = handleAnalyze;
  submitBtn.onclick = handleSubmit;
  document.getElementById('switchCameraBtn').onclick = () => {
    useFacingMode = useFacingMode === 'user' ? 'environment' : 'user';
    startCamera();
  };
});
