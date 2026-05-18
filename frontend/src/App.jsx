import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ChevronDown,
  Clock3,
  Copy,
  FileText,
  Globe2,
  Grid3X3,
  Image,
  Languages,
  Loader2,
  LogOut,
  Menu,
  Mic,
  RotateCcw,
  Settings,
  Share2,
  Star,
  Trash2,
  Volume2,
  X,
} from 'lucide-react';
import './style.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
const USER_STORAGE_KEY = 'traducteur.google.user';

const languages = [
  { code: 'ewe', label: 'Ewe', short: 'EW' },
  { code: 'fra', label: 'Français', short: 'FR' },
  { code: 'eng', label: 'Anglais', short: 'EN' },
];

const modeTabs = [
  { id: 'text', label: 'Texte', icon: Languages, enabled: true },
  { id: 'images', label: 'Images', icon: Image, enabled: false },
  { id: 'documents', label: 'Documents', icon: FileText, enabled: false },
  { id: 'web', label: 'Sites Web', icon: Globe2, enabled: false },
];

function getLanguageLabel(code) {
  return languages.find((language) => language.code === code)?.label || code;
}

function makeHistoryKey(user) {
  return `traducteur.history.${user?.id || user?.email || 'anonymous'}`;
}

function readJson(key, fallback) {
  try {
    const rawValue = localStorage.getItem(key);
    return rawValue ? JSON.parse(rawValue) : fallback;
  } catch {
    return fallback;
  }
}

function decodeJwt(token) {
  const payload = token.split('.')[1];
  const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
  const decoded = atob(base64);
  const json = decodeURIComponent(
    decoded
      .split('')
      .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
      .join(''),
  );
  return JSON.parse(json);
}

function makeId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatHistoryDate(date) {
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(date));
  } catch {
    return '';
  }
}

function App() {
  const [text, setText] = useState('je vais bien');
  const [source, setSource] = useState('fra');
  const [target, setTarget] = useState('ewe');
  const [result, setResult] = useState('');
  const [warning, setWarning] = useState('');
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeCollection, setActiveCollection] = useState('history');
  const [authError, setAuthError] = useState('');
  const googleButtonRef = useRef(null);

  useEffect(() => {
    setUser(readJson(USER_STORAGE_KEY, null));
  }, []);

  useEffect(() => {
    if (!user) {
      setHistory([]);
      return;
    }
    setHistory(readJson(makeHistoryKey(user), []));
  }, [user]);

  useEffect(() => {
    if (user || !googleButtonRef.current) return;

    if (!GOOGLE_CLIENT_ID) {
      setAuthError('Ajoutez VITE_GOOGLE_CLIENT_ID pour activer Google.');
      return;
    }

    const renderGoogleButton = () => {
      if (!window.google?.accounts?.id || !googleButtonRef.current) return;
      googleButtonRef.current.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        shape: 'pill',
        text: 'signin_with',
        logo_alignment: 'left',
        width: 248,
      });
      setAuthError('');
    };

    const existingScript = document.getElementById('google-identity-services');
    if (existingScript) {
      renderGoogleButton();
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-identity-services';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = renderGoogleButton;
    script.onerror = () => setAuthError('Google Identity Services est indisponible.');
    document.head.appendChild(script);
  }, [user]);

  const visibleHistory = useMemo(() => {
    if (activeCollection === 'saved') {
      return history.filter((item) => item.favorite);
    }
    return history;
  }, [activeCollection, history]);

  function handleGoogleCredential(response) {
    const profile = decodeJwt(response.credential);
    const nextUser = {
      id: profile.sub,
      name: profile.name || profile.email,
      email: profile.email,
      picture: profile.picture,
    };
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(nextUser));
    setUser(nextUser);
  }

  function persistHistory(nextHistory) {
    if (!user) return;
    localStorage.setItem(makeHistoryKey(user), JSON.stringify(nextHistory));
  }

  function saveHistoryEntry(entry) {
    if (!user) {
      setWarning('Connectez-vous avec Google pour enregistrer l’historique.');
      return;
    }

    setHistory((currentHistory) => {
      const nextHistory = [
        entry,
        ...currentHistory.filter(
          (item) =>
            item.sourceText !== entry.sourceText ||
            item.translatedText !== entry.translatedText ||
            item.source !== entry.source ||
            item.target !== entry.target,
        ),
      ].slice(0, 40);
      persistHistory(nextHistory);
      return nextHistory;
    });
  }

  async function translate() {
    if (!text.trim() || loading) return;

    setLoading(true);
    setWarning('');
    try {
      const response = await fetch(`${API_URL}/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          source_lang: source,
          target_lang: target,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Erreur API');

      setResult(data.translated_text);
      if (data.warning) setWarning(data.warning);

      saveHistoryEntry({
        id: makeId(),
        sourceText: data.source_text || text.trim(),
        translatedText: data.translated_text,
        source,
        target,
        backend: data.backend,
        favorite: false,
        createdAt: new Date().toISOString(),
      });
    } catch (error) {
      setWarning(String(error.message || error));
    } finally {
      setLoading(false);
    }
  }

  function swapLanguages() {
    setSource(target);
    setTarget(source);
    setText(result || text);
    setResult(text);
  }

  function restoreHistory(item) {
    setSource(item.source);
    setTarget(item.target);
    setText(item.sourceText);
    setResult(item.translatedText);
  }

  function toggleFavorite(id) {
    setHistory((currentHistory) => {
      const nextHistory = currentHistory.map((item) =>
        item.id === id ? { ...item, favorite: !item.favorite } : item,
      );
      persistHistory(nextHistory);
      return nextHistory;
    });
  }

  function removeHistoryItem(id) {
    setHistory((currentHistory) => {
      const nextHistory = currentHistory.filter((item) => item.id !== id);
      persistHistory(nextHistory);
      return nextHistory;
    });
  }

  function clearHistory() {
    setHistory([]);
    persistHistory([]);
  }

  function signOut() {
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
    setHistory([]);
  }

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setWarning('Traduction copiée.');
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-side">
          <button className="icon-button" type="button" aria-label="Menu">
            <Menu size={24} />
          </button>
          <div className="brand">
            <span className="brand-letter blue">T</span>
            <span className="brand-letter red">r</span>
            <span className="brand-letter yellow">a</span>
            <span className="brand-letter blue">d</span>
            <span className="brand-letter green">u</span>
            <span className="brand-letter red">c</span>
            <strong>teur Ewe</strong>
          </div>
        </div>

        <div className="top-actions">
          <button className="icon-button hide-mobile" type="button" aria-label="Paramètres">
            <Settings size={22} />
          </button>
          <button className="icon-button hide-mobile" type="button" aria-label="Applications">
            <Grid3X3 size={21} />
          </button>

          {user ? (
            <div className="profile-pill">
              {user.picture ? <img src={user.picture} alt="" /> : <span>{user.name?.[0]}</span>}
              <div>
                <strong>{user.name}</strong>
                <small>{user.email}</small>
              </div>
              <button className="icon-button" type="button" onClick={signOut} aria-label="Déconnexion">
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <div className="google-auth">
              <div ref={googleButtonRef} className="google-button-slot" />
              {authError && <small>{authError}</small>}
            </div>
          )}
        </div>
      </header>

      <section className="mode-tabs" aria-label="Modes">
        {modeTabs.map(({ id, label, icon: Icon, enabled }) => (
          <button
            key={id}
            className={id === 'text' ? 'mode-tab active' : 'mode-tab'}
            type="button"
            disabled={!enabled}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </section>

      <section className="translator-workbench">
        <div className="language-bar">
          <div className="language-group" aria-label="Langue source">
            {languages.map((language) => (
              <button
                key={language.code}
                className={source === language.code ? 'language-tab active' : 'language-tab'}
                type="button"
                onClick={() => setSource(language.code)}
              >
                {language.label}
              </button>
            ))}
            <button className="icon-button compact" type="button" aria-label="Plus de langues source">
              <ChevronDown size={20} />
            </button>
          </div>

          <button className="swap-button" type="button" onClick={swapLanguages} aria-label="Permuter les langues">
            <RotateCcw size={21} />
          </button>

          <div className="language-group target" aria-label="Langue cible">
            {languages.map((language) => (
              <button
                key={language.code}
                className={target === language.code ? 'language-tab active' : 'language-tab'}
                type="button"
                onClick={() => setTarget(language.code)}
              >
                {language.label}
              </button>
            ))}
            <button className="icon-button compact" type="button" aria-label="Plus de langues cible">
              <ChevronDown size={20} />
            </button>
          </div>
        </div>

        <div className="translate-grid">
          <section className="translate-panel input-panel">
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Saisir le texte"
              maxLength={2000}
            />
            {text && (
              <button className="clear-button" type="button" onClick={() => setText('')} aria-label="Effacer">
                <X size={24} />
              </button>
            )}
            <div className="panel-footer">
              <div className="footer-tools">
                <button className="icon-button muted" type="button" aria-label="Entrée vocale">
                  <Mic size={21} />
                </button>
                <button className="icon-button muted" type="button" aria-label="Écouter le texte">
                  <Volume2 size={21} />
                </button>
              </div>
              <span>{text.length}/2000</span>
            </div>
          </section>

          <section className="translate-panel output-panel">
            <p className={result ? 'result-text' : 'result-text placeholder'}>
              {result || 'La traduction apparaîtra ici.'}
            </p>
            <button
              className={history.some((item) => item.translatedText === result && item.favorite) ? 'save-button saved' : 'save-button'}
              type="button"
              onClick={() => {
                const current = history.find((item) => item.translatedText === result);
                if (current) toggleFavorite(current.id);
              }}
              disabled={!result || !user}
              aria-label="Enregistrer"
            >
              <Star size={23} />
            </button>
            <div className="panel-footer">
              <div className="footer-tools">
                <button className="icon-button muted" type="button" aria-label="Écouter la traduction">
                  <Volume2 size={21} />
                </button>
                <button className="icon-button muted" type="button" onClick={copyResult} aria-label="Copier">
                  <Copy size={21} />
                </button>
                <button className="icon-button muted" type="button" aria-label="Partager">
                  <Share2 size={21} />
                </button>
              </div>
              {result && <span>{getLanguageLabel(target)}</span>}
            </div>
          </section>
        </div>

        <div className="translate-actions">
          <button className="primary-button" type="button" onClick={translate} disabled={loading || !text.trim()}>
            {loading ? <Loader2 className="spin" size={19} /> : <Languages size={19} />}
            {loading ? 'Traduction...' : 'Traduire'}
          </button>
          {warning && <p className="status-message">{warning}</p>}
        </div>
      </section>

      <section className="collections">
        <div className="collection-switcher" aria-label="Collections">
          <button
            className={activeCollection === 'history' ? 'collection-tab active' : 'collection-tab'}
            type="button"
            onClick={() => setActiveCollection('history')}
          >
            <Clock3 size={23} />
            Historique
          </button>
          <button
            className={activeCollection === 'saved' ? 'collection-tab active' : 'collection-tab'}
            type="button"
            onClick={() => setActiveCollection('saved')}
          >
            <Star size={23} />
            Enregistrées
          </button>
        </div>

        <div className="history-panel">
          <div className="history-heading">
            <div>
              <strong>{activeCollection === 'history' ? 'Traductions récentes' : 'Traductions enregistrées'}</strong>
              <span>{user ? `${visibleHistory.length} élément(s)` : 'Connexion Google requise'}</span>
            </div>
            {user && history.length > 0 && (
              <button className="text-button" type="button" onClick={clearHistory}>
                <Trash2 size={17} />
                Effacer
              </button>
            )}
          </div>

          {!user ? (
            <p className="empty-state">Connectez-vous avec Google pour conserver vos traductions.</p>
          ) : visibleHistory.length === 0 ? (
            <p className="empty-state">
              {activeCollection === 'history' ? 'Aucune traduction pour le moment.' : 'Aucune traduction enregistrée.'}
            </p>
          ) : (
            <div className="history-list">
              {visibleHistory.map((item) => (
                <article className="history-item" key={item.id}>
                  <button className="history-main" type="button" onClick={() => restoreHistory(item)}>
                    <span>
                      {getLanguageLabel(item.source)} → {getLanguageLabel(item.target)}
                    </span>
                    <strong>{item.sourceText}</strong>
                    <em>{item.translatedText}</em>
                  </button>
                  <div className="history-meta">
                    <small>{formatHistoryDate(item.createdAt)}</small>
                    <button
                      className={item.favorite ? 'icon-button compact saved' : 'icon-button compact'}
                      type="button"
                      onClick={() => toggleFavorite(item.id)}
                      aria-label="Marquer comme enregistrée"
                    >
                      <Star size={18} />
                    </button>
                    <button
                      className="icon-button compact"
                      type="button"
                      onClick={() => removeHistoryItem(item.id)}
                      aria-label="Supprimer"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
