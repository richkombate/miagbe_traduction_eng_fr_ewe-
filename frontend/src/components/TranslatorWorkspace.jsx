import { Copy, Loader2, SendHorizontal, Star, Trash2 } from 'lucide-react';
import { getLanguageLabel } from '../lib/languages';

export function TranslatorWorkspace({
  text,
  result,
  source,
  target,
  loading,
  saved,
  status,
  onTextChange,
  onTranslate,
  onClear,
  onCopy,
  onToggleSaved,
}) {
  const isSaved = Boolean(saved);

  return (
    <section className="translator-surface">
      <div className="panel source-panel">
        <div className="panel-heading">
          <span>{getLanguageLabel(source)}</span>
          <button className="ghost-button danger" type="button" onClick={onClear} disabled={!text}>
            <Trash2 size={17} />
            Effacer
          </button>
        </div>

        <textarea
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          placeholder="Ecrire ou coller le texte a traduire"
          maxLength={2000}
          autoFocus
        />

        <div className="panel-footer">
          <div className="tool-row">
            <span className="language-footnote">{getLanguageLabel(source)}</span>
          </div>
          <span>{text.length}/2000</span>
        </div>
      </div>

      <div className="panel target-panel">
        <div className="panel-heading">
          <span>{getLanguageLabel(target)}</span>
          <button className={isSaved ? 'ghost-button saved' : 'ghost-button'} type="button" onClick={onToggleSaved} disabled={!result}>
            <Star size={17} />
            Enregistrer
          </button>
        </div>

        <div className={result ? 'translation-output' : 'translation-output muted-output'}>
          {loading ? (
            <span className="loading-line">
              <Loader2 className="spin" size={22} />
              Traduction en cours
            </span>
          ) : (
            result || 'La traduction apparaitra ici.'
          )}
        </div>

        <div className="panel-footer">
          <div className="tool-row">
            <button className="icon-button" type="button" onClick={onCopy} disabled={!result} aria-label="Copier">
              <Copy size={19} />
            </button>
          </div>
          <span>{result ? 'Pret' : 'En attente'}</span>
        </div>
      </div>

      <div className="translate-command">
        <button className="primary-action" type="button" onClick={onTranslate} disabled={loading || !text.trim()}>
          {loading ? <Loader2 className="spin" size={19} /> : <SendHorizontal size={19} />}
          {loading ? 'Traduction' : 'Traduire'}
        </button>
        {status && <p>{status}</p>}
      </div>
    </section>
  );
}
