/**
 * Techno Track AI - API Service Layer
 * Centralizes all backend communication (REST + SSE).
 * 
 * Uses native fetch() — no axios dependency needed.
 * Backend base URL defaults to localhost:8000 for dev.
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
const MOCK_USER_ID = 'mock-user-001';

// ── Helper ─────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': MOCK_USER_ID,
    ...options.headers,
  };
  
  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err) {
    const networkError = new Error(
      `Could not reach the backend (${url}). Make sure the API server is running.`,
    );
    networkError.code = 'NETWORK_ERROR';
    networkError.cause = err;
    throw networkError;
  }
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

function buildVisionPayload(imageInput, locale = 'tr') {
  if (typeof imageInput !== 'string' || !imageInput.trim()) {
    throw new Error('A valid image input is required.');
  }

  const trimmed = imageInput.trim();

  if (trimmed.startsWith('data:')) {
    const [, base64] = trimmed.split(',', 2);
    if (!base64) {
      throw new Error('Could not decode the Base64 image data.');
    }
    return {
      input_type: 'base64',
      image_data: base64,
      locale,
    };
  }

  if (/^https?:\/\//i.test(trimmed)) {
    throw new Error('Direct image URLs are not supported. Please upload an image or capture one from your camera.');
  }

  throw new Error('Image input must be in data URL format.');
}


// ── BFF AI Endpoints ───────────────────────────────────────────

export async function chatWithAssistant({ history = [], userMessage, contextData = null }) {
  return apiFetch('/chat', {
    method: 'POST',
    body: JSON.stringify({
      history,
      user_message: userMessage,
      context_data: contextData,
    }),
  });
}

export async function analyzeImage(imageInput, locale = 'tr') {
  const payload = buildVisionPayload(imageInput, locale);
  return apiFetch('/vision/analyze-image', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function compareProducts(products) {
  return apiFetch('/analyze/compare', {
    method: 'POST',
    body: JSON.stringify({ products }),
  });
}

export async function fetchPriceHistory({ productName, productId = null, currency = 'TRY', locale = 'tr' }) {
  return apiFetch('/price-history', {
    method: 'POST',
    body: JSON.stringify({
      product_name: productName,
      product_id: productId,
      currency,
      locale,
    }),
  });
}



// ── Pipeline (Orchestration) ───────────────────────────────────

/**
 * Triggers the full agent pipeline.
 * @param {Object} payload - OrchestrateRequest body
 * @param {string} payload.query - Search query or product name
 * @param {string} [payload.session_id] - SSE session ID for streaming logs
 * @param {Object} [payload.vision] - Vision agent payload (image data)
 * @param {boolean} [payload.save_to_db] - Whether to persist results
 * @returns {Promise<Object>} OrchestrateResponse
 */
export async function runPipeline(payload) {
  return apiFetch('/orchestrate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Creates an SSE EventSource for real-time pipeline logs.
 * @param {string} sessionId - Unique session identifier
 * @param {Function} onLog - Callback for each log event: (data) => void
 * @param {Function} onDone - Callback when pipeline completes
 * @param {Function} onError - Callback on error
 * @returns {EventSource} The SSE connection (call .close() to disconnect)
 */
export function subscribeToPipeline(sessionId, { onLog, onDone, onError }) {
  const url = `${API_BASE}/stream/pipeline/${sessionId}`;
  const eventSource = new EventSource(url);
  
  eventSource.addEventListener('log', (e) => {
    try {
      const data = JSON.parse(e.data);
      onLog?.(data);
    } catch (err) {
      console.error('SSE parse error:', err);
    }
  });
  
  eventSource.addEventListener('done', (e) => {
    try {
      const data = JSON.parse(e.data);
      onDone?.(data);
    } catch {
      onDone?.({});
    }
    eventSource.close();
  });
  
  eventSource.addEventListener('error', () => {
    onError?.('SSE connection lost');
    eventSource.close();
  });
  
  eventSource.onerror = () => {
    // EventSource auto-reconnects; we only close on explicit error events
  };
  
  return eventSource;
}


// ── Favorites ──────────────────────────────────────────────────

export async function getFavorites() {
  return apiFetch('/user/favorites');
}

export async function addFavorite({ product_name, price, url, image_url }) {
  return apiFetch('/user/favorites', {
    method: 'POST',
    body: JSON.stringify({ product_name, price, url, image_url }),
  });
}

export async function removeFavorite(favoriteId) {
  return apiFetch(`/user/favorites/${favoriteId}`, {
    method: 'DELETE',
  });
}


// ── Price Alerts ───────────────────────────────────────────────

export async function getAlerts() {
  return apiFetch('/user/alerts');
}

export async function addAlert({ product_id, product_name, target_price, current_price }) {
  return apiFetch('/user/alerts', {
    method: 'POST',
    body: JSON.stringify({ product_id, product_name, target_price, current_price }),
  });
}

export async function removeAlert(alertId) {
  return apiFetch(`/user/alerts/${alertId}`, {
    method: 'DELETE',
  });
}


// ── Generate a unique session ID ───────────────────────────────
export function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}
