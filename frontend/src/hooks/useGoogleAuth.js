import { useEffect, useState } from 'react';
import { clearStoredUser, readStoredUser, storeUser } from '../lib/storage';
import { profileFromCredential, renderGoogleButton } from '../lib/google';

export function useGoogleAuth(buttonRef) {
  const [user, setUser] = useState(() => readStoredUser());
  const [authStatus, setAuthStatus] = useState('');

  useEffect(() => {
    if (user || !buttonRef.current) return;

    renderGoogleButton(buttonRef.current, (response) => {
      const profile = profileFromCredential(response);
      storeUser(profile);
      setUser(profile);
      setAuthStatus('');
    }).catch((error) => setAuthStatus(error.message));
  }, [buttonRef, user]);

  function signOut() {
    clearStoredUser();
    setUser(null);
  }

  return { user, authStatus, signOut };
}
