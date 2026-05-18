const USER_KEY = 'traducteur.user';

export function readJson(key, fallback) {
  try {
    const rawValue = localStorage.getItem(key);
    return rawValue ? JSON.parse(rawValue) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function readStoredUser() {
  return readJson(USER_KEY, null);
}

export function storeUser(user) {
  writeJson(USER_KEY, user);
}

export function clearStoredUser() {
  localStorage.removeItem(USER_KEY);
}

export function makeHistoryKey(user) {
  return `traducteur.history.${user?.id || user?.email || 'anonymous'}`;
}

export function makeId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function formatHistoryDate(value) {
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return '';
  }
}
