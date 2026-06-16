import { useCallback, useEffect, useRef, useState } from 'react';

// Correspondance des langues du projet vers les codes BCP-47 du navigateur.
// L'éwé n'est pas couvert par les moteurs vocaux des navigateurs.
const BCP47 = {
  fra: 'fr-FR',
  eng: 'en-US',
  ewe: null,
};

const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

// Langues pour lesquelles une voix serveur (MMS-TTS) existe, dont l'éwé.
const SERVER_TTS = new Set(['fra', 'eng', 'ewe']);

export const sttSupported = (lang) => Boolean(SpeechRecognition && BCP47[lang]);

// Voix navigateur (instantanée) : seulement fr/en.
export const browserTtsSupported = (lang) =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && Boolean(BCP47[lang]);

// Voix disponible au total : navigateur (fr/en) OU serveur MMS-TTS (dont éwé).
export const ttsSupported = (lang) => browserTtsSupported(lang) || SERVER_TTS.has(lang);

/**
 * Reconnaissance vocale (Speech-to-Text) via l'API Web Speech du navigateur.
 * Renvoie le texte reconnu via onResult. Disponible sur Chrome/Edge pour fr/en.
 */
export function useSpeechRecognition({ lang, onResult, onError }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const finalRef = useRef('');   // texte déjà finalisé (les segments confirmés)

  const stop = useCallback(() => {
    const rec = recognitionRef.current;
    if (rec) {
      try { rec.stop(); } catch { /* déjà arrêté */ }
      recognitionRef.current = null;
    }
    setListening(false);
  }, []);

  const start = useCallback(() => {
    if (!SpeechRecognition) { onError?.('unsupported'); return; }
    if (!BCP47[lang]) { onError?.('lang'); return; }   // éwé non couvert par le navigateur
    if (recognitionRef.current) return;                // une session déjà en cours

    let recognition;
    try {
      recognition = new SpeechRecognition();
    } catch {
      onError?.('unsupported');
      return;
    }
    recognition.lang = BCP47[lang];
    recognition.interimResults = true;   // affiche le texte au fur et à mesure
    recognition.continuous = true;       // ne s'arrête pas après une phrase
    recognition.maxAlternatives = 1;

    finalRef.current = '';               // nouvelle session de dictée

    recognition.onresult = (event) => {
      // On accumule les segments confirmés (isFinal) et on y ajoute l'hypothèse
      // en cours (interim) pour montrer la transcription en temps réel.
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const segment = event.results[i];
        if (segment.isFinal) {
          finalRef.current += segment[0].transcript;
        } else {
          interim += segment[0].transcript;
        }
      }
      onResult?.((finalRef.current + interim).replace(/\s+/g, ' ').trimStart());
    };
    recognition.onerror = (event) => {
      onError?.(event.error || 'unknown');   // ex. not-allowed, no-speech, network…
      setListening(false);
      recognitionRef.current = null;
    };
    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    setListening(true);
    try {
      recognition.start();
    } catch {
      onError?.('start');
      setListening(false);
      recognitionRef.current = null;
    }
  }, [lang, onResult, onError]);

  useEffect(() => stop, [stop]);

  return { listening, start, stop, supported: sttSupported(lang) };
}

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
