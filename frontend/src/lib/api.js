import { API_URL } from './config';

export async function translateText({ text, source, target }) {
  const response = await fetch(`${API_URL}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      source_lang: source,
      target_lang: target,
    }),
  });
  if (!response.ok) {
    throw new Error('translation_failed');
  }
  return response.json();
}

// En-têtes d'identité envoyés au serveur pour rattacher l'historique à
// l'utilisateur (jeton Google vérifié si présent, sinon identité de démo).
function authHeaders(user) {
  const headers = {};
  if (user?.token) headers.Authorization = `Bearer ${user.token}`;
  if (user?.id) headers['X-User-Id'] = String(user.id);
  if (user?.email) headers['X-User-Email'] = user.email;
  return headers;
}

// Récupère l'historique de l'utilisateur depuis le serveur (multi-navigateurs).
export async function fetchHistory(user) {
  const response = await fetch(`${API_URL}/history`, {
    headers: authHeaders(user),
  });
  if (!response.ok) {
    throw new Error('history_fetch_failed');
  }
  const data = await response.json();
  return data.entries || [];
}

// Remplace l'historique côté serveur par la liste fournie.
export async function saveHistory(user, entries) {
  const response = await fetch(`${API_URL}/history`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders(user) },
    body: JSON.stringify({ entries }),
  });
  if (!response.ok) {
    throw new Error('history_save_failed');
  }
  const data = await response.json();
  return data.entries || [];
}

// Transcription serveur (Whisper) - utilisée si la reconnaissance navigateur
// n'est pas disponible et que ENABLE_STT=true côté backend.
export async function transcribeAudio({ blob, lang }) {
  const form = new FormData();
  form.append('file', blob, 'audio.webm');
  const response = await fetch(`${API_URL}/transcribe?lang=${encodeURIComponent(lang)}`, {
    method: 'POST',
    body: form,
  });
  if (!response.ok) {
    throw new Error('transcription_failed');
  }
  return response.json();
}
