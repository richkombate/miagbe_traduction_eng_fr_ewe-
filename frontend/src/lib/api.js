import { API_URL } from './config';

export async function getHealth() {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) {
    throw new Error('API indisponible');
  }
  return response.json();
}

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
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Erreur de traduction');
  }
  return data;
}
