import { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Footer } from './components/Footer';
import { HistoryPanel } from './components/HistoryPanel';
import { LanguageSelector } from './components/LanguageSelector';
import { TopBar } from './components/TopBar';
import { TranslatorWorkspace } from './components/TranslatorWorkspace';
import { useTranslationHistory } from './hooks/useTranslationHistory';
import { speak, ttsSupported } from './hooks/useSpeech';
import { translateText, synthesizeSpeech, transcribeAudio } from './lib/api';
import { createWavRecorder } from './lib/recorder';
import { getLanguageLabel } from './lib/languages';
import { makeId } from './lib/storage';
import './style.css';

function App() {
  const [user, setUser] = useState(null);
  const [source, setSource] = useState('fra');
  const [target, setTarget] = useState('ewe');
  const [text, setText] = useState('Je vais bien.');
  const [result, setResult] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeHistoryTab, setActiveHistoryTab] = useState('history');
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const liveRequestRef = useRef(0);
  const recorderRef = useRef(null);

  const { history, saved, syncError, addEntry, toggleFavorite, removeEntry, clearHistory } =
    useTranslationHistory(user);

  // Dictée serveur pour TOUTES les langues (fr/en via Whisper, éwé via MMS-ASR) :
  // on enregistre en WAV, puis on transcrit côté serveur à l'arrêt.
  async function startServerDictation() {
    try {
      setStatus('Enregistrement… parlez, puis cliquez à nouveau pour transcrire.');
      recorderRef.current = await createWavRecorder();
      setRecording(true);
    } catch {
      setStatus('Micro inaccessible. Autorisez le micro dans le navigateur.');
    }
  }

  async function stopServerDictation() {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    setRecording(false);
    if (!recorder) return;
    setTranscribing(true);
    try {
      setStatus(`Transcription ${getLanguageLabel(source)} en cours…`);
      const blob = await recorder.stop();
      const data = await transcribeAudio({ blob, lang: source });
      if (data.text) {
        setText(data.text);
        setStatus('');
      } else {
        setStatus(data.warning || 'Aucun texte reconnu.');
      }
    } catch {
      setStatus('La transcription serveur a échoué (API + ENABLE_STT=true requis).');
    } finally {
      setTranscribing(false);
    }
  }

  function handleMicToggle() {
    if (transcribing) return;                          // transcription en cours, on ignore le clic
    if (recording) { stopServerDictation(); return; }  // enregistrement en cours -> on transcrit
    setStatus('');
    startServerDictation();
  }

  async function handleSpeak() {
    if (!result) return;
    // 1) Voix navigateur instantanée pour fr/en.
    if (speak(result, target)) return;
    // 2) Sinon (éwé) : synthèse côté serveur via MMS-TTS.
    try {
      setStatus('Synthèse vocale éwé en cours…');
      const url = await synthesizeSpeech({ text: result, lang: target });
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
      setStatus('');
    } catch {
      setStatus('Voix éwé indisponible (démarrez l’API avec ENABLE_TTS=true).');
    }
  }

  const currentSavedEntry = useMemo(
    () => history.find((item) => item.sourceText === text && item.translatedText === result && item.source === source && item.target === target),
    [history, result, source, target, text],
  );

  function buildHistoryEntry(sourceText, translatedText, favorite = false) {
    return {
      id: makeId(),
      sourceText,
      translatedText,
      source,
      target,
      favorite,
      createdAt: new Date().toISOString(),
    };
  }

  async function runTranslation({ persist = false } = {}) {
    const sourceText = text.trim();
    if (!sourceText) {
      setResult('');
      setStatus('');
      return;
    }

    const requestId = liveRequestRef.current + 1;
    liveRequestRef.current = requestId;
    setLoading(true);
    if (persist) setStatus('');

    try {
      const data = await translateText({ text: sourceText, source, target });
      if (requestId !== liveRequestRef.current) return;

      const translatedText = data.translated_text || '';
      setResult(translatedText);

      if (persist) {
        if (user) {
          addEntry(buildHistoryEntry(data.source_text || sourceText, translatedText));
        } else {
          setStatus('Connectez-vous pour conserver cette traduction.');
        }
      }
    } catch {
      if (requestId === liveRequestRef.current) {
        setStatus("La traduction n'a pas pu aboutir. R\u00e9essayez dans un instant.");
      }
    } finally {
      if (requestId === liveRequestRef.current) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    const sourceText = text.trim();
    const requestId = liveRequestRef.current + 1;
    liveRequestRef.current = requestId;

    if (!sourceText) {
      setResult('');
      setStatus('');
      setLoading(false);
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      if (requestId !== liveRequestRef.current) return;
      setLoading(true);
      setStatus('');

      try {
        const data = await translateText({ text: sourceText, source, target });
        if (requestId !== liveRequestRef.current) return;
        setResult(data.translated_text || '');
      } catch {
        if (requestId === liveRequestRef.current) {
          setStatus("La traduction n'a pas pu aboutir. R\u00e9essayez dans un instant.");
        }
      } finally {
        if (requestId === liveRequestRef.current) {
          setLoading(false);
        }
      }
    }, 650);

    return () => window.clearTimeout(timer);
  }, [source, target, text]);

  function handleSwap() {
    setSource(target);
    setTarget(source);
    setText(result || text);
    setResult(text);
  }

  function handleRestore(item) {
    setSource(item.source);
    setTarget(item.target);
    setText(item.sourceText);
    setResult(item.translatedText);
  }

  async function handleCopy() {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setStatus('Traduction copi\u00e9e.');
  }

  function handleToggleSaved() {
    if (!result) return;
    if (!user) {
      setStatus('Connectez-vous pour enregistrer cette traduction.');
      return;
    }

    if (currentSavedEntry) {
      toggleFavorite(currentSavedEntry.id);
      return;
    }

    addEntry(buildHistoryEntry(text.trim(), result, true));
    setStatus('Traduction enregistr\u00e9e.');
  }

  return (
    <main className="app-shell">
      <TopBar onUserChange={setUser} />

      <section className="workspace">
        <div className="translation-column">
          <LanguageSelector
            source={source}
            target={target}
            onSourceChange={setSource}
            onTargetChange={setTarget}
            onSwap={handleSwap}
          />
          <TranslatorWorkspace
            text={text}
            result={result}
            source={source}
            target={target}
            loading={loading}
            saved={currentSavedEntry?.favorite}
            status={status}
            recording={recording}
            transcribing={transcribing}
            speakSupported={ttsSupported(target)}
            onTextChange={setText}
            onTranslate={() => runTranslation({ persist: true })}
            onClear={() => {
              setText('');
              setResult('');
              setStatus('');
            }}
            onCopy={handleCopy}
            onToggleSaved={handleToggleSaved}
            onMicToggle={handleMicToggle}
            onSpeak={handleSpeak}
          />
        </div>

        <HistoryPanel
          user={user}
          history={history}
          saved={saved}
          syncError={syncError}
          activeTab={activeHistoryTab}
          onTabChange={setActiveHistoryTab}
          onRestore={handleRestore}
          onToggleFavorite={toggleFavorite}
          onRemove={removeEntry}
          onClear={clearHistory}
        />
      </section>

      <Footer />
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
