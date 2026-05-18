import { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HistoryPanel } from './components/HistoryPanel';
import { LanguageSelector } from './components/LanguageSelector';
import { ModelStatus } from './components/ModelStatus';
import { TopBar } from './components/TopBar';
import { TranslatorWorkspace } from './components/TranslatorWorkspace';
import { useTranslationHistory } from './hooks/useTranslationHistory';
import { getHealth, translateText } from './lib/api';
import { makeId } from './lib/storage';
import './style.css';

function App() {
  const [user, setUser] = useState(null);
  const [source, setSource] = useState('fra');
  const [target, setTarget] = useState('ewe');
  const [text, setText] = useState('Je vais bien.');
  const [result, setResult] = useState('');
  const [backend, setBackend] = useState('');
  const [health, setHealth] = useState(null);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeHistoryTab, setActiveHistoryTab] = useState('history');

  const { history, saved, addEntry, toggleFavorite, removeEntry, clearHistory } = useTranslationHistory(user);

  useEffect(() => {
    getHealth()
      .then((data) => {
        setHealth(data);
        setBackend(data.backend);
      })
      .catch(() => {
        setStatus('API indisponible');
      });
  }, []);

  const currentSavedEntry = useMemo(
    () => history.find((item) => item.sourceText === text && item.translatedText === result && item.source === source && item.target === target),
    [history, result, source, target, text],
  );

  async function handleTranslate() {
    if (!text.trim()) return;

    setLoading(true);
    setStatus('');
    try {
      const data = await translateText({ text: text.trim(), source, target });
      const translatedText = data.translated_text || '';
      setResult(translatedText);
      setStatus(data.warning || '');

      if (user) {
        addEntry({
          id: makeId(),
          sourceText: data.source_text || text.trim(),
          translatedText,
          source,
          target,
          backend: data.backend,
          favorite: false,
          createdAt: new Date().toISOString(),
        });
      } else {
        setStatus('Connectez-vous avec Google pour garder l historique.');
      }
    } catch (error) {
      setStatus(error.message || 'Erreur de traduction');
    } finally {
      setLoading(false);
    }
  }

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
    setStatus('Traduction copiee');
  }

  function handleToggleSaved() {
    if (!currentSavedEntry) return;
    toggleFavorite(currentSavedEntry.id);
  }

  return (
    <main className="app-shell">
      <TopBar backend={backend} onUserChange={setUser} />
      <ModelStatus health={health} />

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
            onTextChange={setText}
            onTranslate={handleTranslate}
            onClear={() => {
              setText('');
              setResult('');
            }}
            onCopy={handleCopy}
            onToggleSaved={handleToggleSaved}
          />
        </div>

        <HistoryPanel
          user={user}
          history={history}
          saved={saved}
          activeTab={activeHistoryTab}
          onTabChange={setActiveHistoryTab}
          onRestore={handleRestore}
          onToggleFavorite={toggleFavorite}
          onRemove={removeEntry}
          onClear={clearHistory}
        />
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
