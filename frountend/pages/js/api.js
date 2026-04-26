const API_BASE = (window.API_BASE || 'http://localhost:8000');

export function detectDefects(file, confidence = 0.25, token = null, onProgress = null) {
  const form = new FormData();
  form.append('file', file);
  form.append('confidence_threshold', String(confidence));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/detect`);

    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    xhr.upload.onprogress = function (event) {
      if (event.lengthComputable && typeof onProgress === 'function') {
        onProgress(event.loaded / event.total);
      }
    };

    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const json = JSON.parse(xhr.responseText);
          resolve(json);
        } catch (err) {
          reject(err);
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(err);
        } catch (e) {
          reject(new Error(xhr.statusText || `HTTP ${xhr.status}`));
        }
      }
    };

    xhr.onerror = function () {
      // Network-level error (CORS, refused connection, DNS, etc.)
      reject(new Error(`Network error: could not reach ${API_BASE}/detect`));
    };

    xhr.send(form);
  });
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
