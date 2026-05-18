import { LogOut, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useGoogleAuth } from '../hooks/useGoogleAuth';

export function TopBar({ onUserChange }) {
  const googleButtonRef = useRef(null);
  const [showLoginHelp, setShowLoginHelp] = useState(false);
  const { user, authStatus, signOut } = useGoogleAuth(googleButtonRef);

  useEffect(() => {
    if (onUserChange) onUserChange(user);
  }, [onUserChange, user]);

  return (
    <header className="topbar">
      <div className="brand-block">
        <div className="brand-mark" aria-hidden="true">
          <Sparkles size={23} />
        </div>
        <div className="brand-copy">
          <strong>MiaGbe</strong>
          <span>Traduction fran&ccedil;ais, anglais et ewe</span>
        </div>
      </div>

      <div className="topbar-actions">
        {user ? (
          <div className="profile-chip">
            {user.picture ? <img src={user.picture} alt="" /> : <span>{user.name?.[0]}</span>}
            <div>
              <strong>{user.name}</strong>
              <small>{user.email}</small>
            </div>
            <button className="icon-button" type="button" onClick={signOut} aria-label="Deconnexion">
              <LogOut size={18} />
            </button>
          </div>
        ) : (
          <div className="google-auth">
            {authStatus === 'guest' ? (
              <div className="google-fallback">
                <button className="google-login-button" type="button" onClick={() => setShowLoginHelp((visible) => !visible)}>
                  <span aria-hidden="true">G</span>
                  Se connecter avec Google
                </button>
                {showLoginHelp && <small>La connexion Google sera activ&eacute;e pour la version connect&eacute;e.</small>}
              </div>
            ) : (
              <div ref={googleButtonRef} className="google-button-slot" />
            )}
          </div>
        )}
      </div>
    </header>
  );
}
