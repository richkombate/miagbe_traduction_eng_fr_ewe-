// Correspondance des langues du projet vers les codes BCP-47 du navigateur.
// Sert à la synthèse vocale navigateur (fr/en) ; l'éwé passe par le serveur.
const BCP47 = {
  fra: 'fr-FR',
  eng: 'en-US',
  ewe: null,
};

// Langues pour lesquelles une voix serveur (MMS-TTS) existe, dont l'éwé.
const SERVER_TTS = new Set(['fra', 'eng', 'ewe']);

// Voix navigateur (instantanée) : seulement fr/en.
export const browserTtsSupported = (lang) =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && Boolean(BCP47[lang]);

// Voix disponible au total : navigateur (fr/en) OU serveur MMS-TTS (dont éwé).
export const ttsSupported = (lang) => browserTtsSupported(lang) || SERVER_TTS.has(lang);

/** Synthèse vocale navigateur (fr/en uniquement). Renvoie false si non gérée
 *  (ex. éwé) -> l'appelant bascule alors sur la synthèse serveur. */
export function speak(text, lang) {
  if (!browserTtsSupported(lang) || !text) return false;
  window.speechSynthesis.cancel();
  const utterance = new window.SpeechSynthesisUtterance(text);
  utterance.lang = BCP47[lang];
  window.speechSynthesis.speak(utterance);
  return true;
}
