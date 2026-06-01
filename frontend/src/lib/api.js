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
