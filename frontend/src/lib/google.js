import { GOOGLE_CLIENT_ID } from './config';

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

export function profileFromCredential(response) {
  const profile = decodeJwt(response.credential);
  return {
    id: profile.sub,
    name: profile.name || profile.email,
    email: profile.email,
    picture: profile.picture,
    // Jeton d'identité Google : permet au serveur de vérifier l'utilisateur
    // (sinon, l'identité repose sur l'en-tête X-User-Id en mode démo).
    token: response.credential,
  };
}

export function renderGoogleButton(container, onCredential) {
  if (!GOOGLE_CLIENT_ID) {
    return Promise.reject(new Error('guest'));
  }

  return new Promise((resolve, reject) => {
    const render = () => {
      if (!window.google?.accounts?.id || !container) return;
      container.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: onCredential,
      });
      window.google.accounts.id.renderButton(container, {
        theme: 'outline',
        size: 'large',
        shape: 'pill',
        text: 'signin_with',
        logo_alignment: 'left',
        width: 236,
      });
      resolve();
    };

    if (window.google?.accounts?.id) {
      render();
      return;
    }

    const existingScript = document.getElementById('google-identity-services');
    if (existingScript) {
      existingScript.addEventListener('load', render, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-identity-services';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = render;
    script.onerror = () => reject(new Error('Google indisponible'));
    document.head.appendChild(script);
  });
}
