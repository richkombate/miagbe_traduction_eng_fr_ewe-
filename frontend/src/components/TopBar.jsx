import { LogOut, Settings2, Sparkles } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useGoogleAuth } from '../hooks/useGoogleAuth';

export function TopBar({ backend, onUserChange }) {
  const googleButtonRef = useRef(null);
  const { user, authStatus, signOut } = useGoogleAuth(googleButtonRef);

  useEffect(() => {
    if (onUserChange) onUserChange(user);
  }, [onUserChange, user]);

  return (
    <header className="topbar">
      <div className="brand-block">
        <div className="brand-mark">
          <Sparkles size={23} />
        </div>
        <div className="brand-copy">
          <strong>Traducteur Ewe</strong>
          <span>NLLB LoRA · Francais · Anglais · Ewe</span>
        </div>
      </div>

      <div className="topbar-actions">
        <div className="model-pill">
          <Settings2 size={17} />
          <span>{backend || 'API'}</span>
        </div>

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
            <div ref={googleButtonRef} className="google-button-slot" />
            {authStatus && <small>{authStatus}</small>}
          </div>
        )}
      </div>
    </header>
  );
}
