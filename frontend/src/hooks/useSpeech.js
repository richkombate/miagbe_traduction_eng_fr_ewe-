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

export const sttSupported = (lang) => Boolean(SpeechRecognition && BCP47[lang]);
export const ttsSupported = (lang) =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && Boolean(BCP47[lang]);

/**
 * Reconnaissance vocale (Speech-to-Text) via l'API Web Speech du navigateur.
 * Renvoie le texte reconnu via onResult. Disponible sur Chrome/Edge pour fr/en.
 */
export function useSpeechRecognition({ lang, onResult }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setListening(false);
  }, []);

  const start = useCallback(() => {
    if (!sttSupported(lang)) return;
    const recognition = new SpeechRecognition();
    recognition.lang = BCP47[lang];
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      onResult?.(transcript);
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  }, [lang, onResult]);

  useEffect(() => stop, [stop]);

  return { listening, start, stop, supported: sttSupported(lang) };
}

/** Synthèse vocale (Text-to-Speech) du navigateur pour lire la traduction. */
export function speak(text, lang) {
  if (!ttsSupported(lang) || !text) return false;
  window.speechSynthesis.cancel();
  const utterance = new window.SpeechSynthesisUtterance(text);
  utterance.lang = BCP47[lang];
  window.speechSynthesis.speak(utterance);
  return true;
}
