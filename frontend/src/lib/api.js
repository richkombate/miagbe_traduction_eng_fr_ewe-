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
