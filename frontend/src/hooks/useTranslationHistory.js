import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchHistory, saveHistory } from '../lib/api';
import { makeHistoryKey, readJson, writeJson } from '../lib/storage';

/**
 * Historique et favoris de traduction.
 *
 * Source de vérité : le serveur (rattaché au compte de l'utilisateur), ce qui
 * permet de retrouver son historique depuis n'importe quel navigateur. Une copie
 * locale (localStorage) sert de cache : affichage instantané et repli hors-ligne
 * si le serveur est injoignable.
 */
export function useTranslationHistory(user) {
  const [history, setHistory] = useState([]);
  const [syncError, setSyncError] = useState(false);
  // Identifie le chargement courant pour ignorer les réponses obsolètes
  // (changement d'utilisateur pendant une requête réseau).
  const loadRef = useRef(0);

  useEffect(() => {
    if (!user) {
      setHistory([]);
      setSyncError(false);
      return;
    }

    const requestId = loadRef.current + 1;
    loadRef.current = requestId;

    // 1) Affichage immédiat depuis le cache local.
    const cached = readJson(makeHistoryKey(user), []);
    setHistory(cached);

    // 2) Récupération de la source de vérité côté serveur.
    fetchHistory(user)
      .then((serverHistory) => {
        if (requestId !== loadRef.current) return;
        setHistory(serverHistory);
        writeJson(makeHistoryKey(user), serverHistory);
        setSyncError(false);
      })
      .catch(() => {
        if (requestId !== loadRef.current) return;
        // Serveur injoignable : on garde le cache local.
        setSyncError(true);
      });
  }, [user]);

  // Écrit dans le cache local puis pousse vers le serveur (best effort).
  const persist = useCallback(
    (nextHistory) => {
      if (!user) return;
      writeJson(makeHistoryKey(user), nextHistory);
      saveHistory(user, nextHistory)
        .then(() => setSyncError(false))
        .catch(() => setSyncError(true));
    },
    [user],
  );

  function commit(nextHistory) {
    setHistory(nextHistory);
    persist(nextHistory);
  }

  function addEntry(entry) {
    if (!user) return;
    const nextHistory = [
      entry,
      ...history.filter(
        (item) =>
          item.sourceText !== entry.sourceText ||
          item.translatedText !== entry.translatedText ||
          item.source !== entry.source ||
          item.target !== entry.target,
      ),
    ].slice(0, 60);
    commit(nextHistory);
  }

  function toggleFavorite(id) {
    commit(history.map((item) => (item.id === id ? { ...item, favorite: !item.favorite } : item)));
  }

  function removeEntry(id) {
    commit(history.filter((item) => item.id !== id));
  }

  function clearHistory() {
    commit([]);
  }

  const saved = useMemo(() => history.filter((item) => item.favorite), [history]);

  return { history, saved, syncError, addEntry, toggleFavorite, removeEntry, clearHistory };
}
