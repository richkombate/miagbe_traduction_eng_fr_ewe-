import { useEffect, useMemo, useState } from 'react';
import { makeHistoryKey, readJson, writeJson } from '../lib/storage';

export function useTranslationHistory(user) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!user) {
      setHistory([]);
      return;
    }
    setHistory(readJson(makeHistoryKey(user), []));
  }, [user]);

  function persist(nextHistory) {
    if (!user) return;
    writeJson(makeHistoryKey(user), nextHistory);
  }

  function addEntry(entry) {
    if (!user) return;
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
      ].slice(0, 60);
      persist(nextHistory);
      return nextHistory;
    });
  }

  function toggleFavorite(id) {
    setHistory((currentHistory) => {
      const nextHistory = currentHistory.map((item) =>
        item.id === id ? { ...item, favorite: !item.favorite } : item,
      );
      persist(nextHistory);
      return nextHistory;
    });
  }

  function removeEntry(id) {
    setHistory((currentHistory) => {
      const nextHistory = currentHistory.filter((item) => item.id !== id);
      persist(nextHistory);
      return nextHistory;
    });
  }

  function clearHistory() {
    setHistory([]);
    persist([]);
  }

  const saved = useMemo(() => history.filter((item) => item.favorite), [history]);

  return { history, saved, addEntry, toggleFavorite, removeEntry, clearHistory };
}
