import { ArrowLeftRight } from 'lucide-react';
import { LANGUAGES } from '../lib/languages';

function LanguageGroup({ value, onChange, label }) {
  return (
    <div className="language-group" aria-label={label}>
      {LANGUAGES.map((language) => (
        <button
          key={language.code}
          className={value === language.code ? 'language-tab active' : 'language-tab'}
          type="button"
          onClick={() => onChange(language.code)}
          style={{ '--accent': language.tone }}
        >
          {language.label}
        </button>
      ))}
    </div>
  );
}

export function LanguageSelector({ source, target, onSourceChange, onTargetChange, onSwap }) {
  return (
    <div className="language-selector">
      <LanguageGroup value={source} onChange={onSourceChange} label="Langue source" />
      <button className="swap-button" type="button" onClick={onSwap} aria-label="Permuter">
        <ArrowLeftRight size={21} />
      </button>
      <LanguageGroup value={target} onChange={onTargetChange} label="Langue cible" />
    </div>
  );
}
