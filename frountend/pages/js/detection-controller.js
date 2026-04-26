import { detectDefects } from './api.js';
import { rgbaFromClass } from './mask-utils.js';

document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('fileInput');
  const startBtn = document.getElementById('btnStartInspection');
  const previewImg = document.getElementById('originalImage');
  const resultImg = document.getElementById('detectionResult');
  const progressBar = document.getElementById('uploadProgress');
  const statsTotal = document.querySelector('[data-stat="total-damages"]');
  const statsConfidence = document.querySelector('[data-stat="highest-confidence"]');
  const confidenceRange = document.getElementById('confidenceRange');
  const confidenceValue = document.getElementById('confidenceValue');
  const workflowUploadDetail = document.getElementById('workflowUploadDetail');
  const workflowImageDetail = document.getElementById('workflowImageDetail');
  const workflowAiDetail = document.getElementById('workflowAiDetail');
  const resetBtn = document.getElementById('btnResetSystem');

  let currentFile = null;

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      currentFile = f;
      const url = URL.createObjectURL(f);
      if (previewImg) previewImg.src = url;
      if (workflowUploadDetail) workflowUploadDetail.textContent = `Ready • ${(f.size/1024/1024).toFixed(2)} MB`;
    });
  }

  // Save default src to restore on reset
  const defaultOriginalSrc = previewImg ? previewImg.src : '';
  const defaultResultSrc = resultImg ? resultImg.src : '';

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      // Clear selected file
      if (fileInput) fileInput.value = '';
      currentFile = null;

      // Restore images
      if (previewImg) previewImg.src = defaultOriginalSrc;
      if (resultImg) resultImg.src = defaultResultSrc;

      // Reset stats
      if (statsTotal) statsTotal.textContent = '0';
      if (statsConfidence) statsConfidence.textContent = '0';

      // Reset progress and workflow
      if (progressBar) progressBar.value = 0;
      const label = document.getElementById('uploadProgressLabel');
      if (label) label.textContent = '0%';
      if (workflowUploadDetail) workflowUploadDetail.textContent = 'Not uploaded';
      if (workflowImageDetail) workflowImageDetail.textContent = 'Not processed';
      if (workflowAiDetail) workflowAiDetail.textContent = 'Idle';

      showToast('System reset');
    });
  }

  if (confidenceRange && confidenceValue) {
    confidenceValue.textContent = (parseInt(confidenceRange.value)/100).toFixed(2);
    confidenceRange.addEventListener('input', () => {
      confidenceValue.textContent = (parseInt(confidenceRange.value)/100).toFixed(2);
    });
  }

  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      if (!currentFile) {
        showToast('Please select an image first');
        return;
      }

      const threshold = confidenceRange ? (parseInt(confidenceRange.value) / 100) : 0.25;

      startBtn.disabled = true;
      setProgress(0);
      if (workflowUploadDetail) workflowUploadDetail.textContent = `Uploading • ${(currentFile.size/1024/1024).toFixed(2)} MB`;
      if (workflowAiDetail) workflowAiDetail.textContent = 'Analyzing...';

      try {
        const result = await detectDefects(currentFile, threshold, null, (p) => setProgress(p));
        // Upload complete
        if (workflowUploadDetail) workflowUploadDetail.textContent = `Upload complete • ${(currentFile.size/1024/1024).toFixed(2)} MB`;
        // Image processed info
        if (workflowImageDetail) workflowImageDetail.textContent = result?.image_width && result?.image_height ? `Processed • ${result.image_width}x${result.image_height}` : 'Processed';
        // AI details
        if (workflowAiDetail) workflowAiDetail.textContent = result?.processing_time_ms ? `Analysis ${Math.round(result.processing_time_ms)} ms` : 'Analysis complete';

        renderDetections(result, resultImg);
        updateStats(result.detections, statsTotal, statsConfidence);
      } catch (err) {
        if (workflowAiDetail) workflowAiDetail.textContent = `Error`;
        showToast(err?.detail || err?.message || 'Detection failed');
      } finally {
        startBtn.disabled = false;
        setProgress(0);
      }
    });
  }

  function setProgress(p) {
    if (!progressBar) return;
    const pct = Math.round(p * 100);
    progressBar.value = pct;
    const label = document.getElementById('uploadProgressLabel');
    if (label) label.textContent = pct + '%';
  }

  function renderDetections(response, imgEl) {
    if (!response) return;
    const { detections, image_url, image_width, image_height } = response;
    if (imgEl && image_url) {
      imgEl.src = image_url;
      imgEl.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = image_width;
        canvas.height = image_height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(imgEl, 0, 0, canvas.width, canvas.height);
        ctx.font = '12px Inter, Arial';

        detections.forEach(det => {
          const [x1, y1, x2, y2] = det.bbox;
          const color = rgbaFromClass(det.class_name);
          ctx.strokeStyle = color.replace('0.35', '1');
          ctx.lineWidth = 3;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

          const label = `${det.class_name} ${(det.confidence * 100).toFixed(1)}%`;
          const textW = ctx.measureText(label).width;
          ctx.fillStyle = 'rgba(0,0,0,0.6)';
          ctx.fillRect(x1, y1 - 20, textW + 8, 18);
          ctx.fillStyle = '#fff';
          ctx.fillText(label, x1 + 4, y1 - 5);
        });

        imgEl.src = canvas.toDataURL();
      };
    }
  }

  function updateStats(detections = [], totalEl, confEl) {
    if (totalEl) totalEl.textContent = detections.length;
    const maxConf = detections.length ? Math.max(...detections.map(d => d.confidence)) : 0;
    if (confEl) confEl.textContent = (maxConf * 100).toFixed(1);
  }

  function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'fixed bottom-4 right-4 bg-black text-white p-3 rounded shadow';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
  }
});
