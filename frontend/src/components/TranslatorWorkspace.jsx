import { Copy, Loader2, Mic, MicOff, SendHorizontal, Star, Trash2, Volume2 } from 'lucide-react';
import { getLanguageLabel } from '../lib/languages';

export function TranslatorWorkspace({
  text,
  result,
  source,
  target,
  loading,
  saved,
  status,
  listening,
  micSupported,
  speakSupported,
  onTextChange,
  onTranslate,
  onClear,
  onCopy,
  onToggleSaved,
  onMicToggle,
  onSpeak,
}) {
  const isSaved = Boolean(saved);

  return (
    <section className="translator-surface">
      <div className="panel source-panel">
        <div className="panel-heading">
          <span>{getLanguageLabel(source)}</span>
          <div className="panel-heading-actions">
            {micSupported && (
              <button
                className={listening ? 'ghost-button listening' : 'ghost-button'}
                type="button"
                onClick={onMicToggle}
                title="Dicter le texte (reconnaissance vocale)"
              >
                {listening ? <MicOff size={17} /> : <Mic size={17} />}
                {listening ? 'Écoute...' : 'Dicter'}
              </button>
            )}
            <button className="ghost-button danger" type="button" onClick={onClear} disabled={!text}>
              <Trash2 size={17} />
              Effacer
            </button>
          </div>
        </div>

        <textarea
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          placeholder={'\u00c9crire ou coller le texte \u00e0 traduire'}
          maxLength={2000}
          autoFocus
        />

        <div className="panel-footer">
          <span className="language-footnote">{getLanguageLabel(source)}</span>
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
              Traduction en cours...
            </span>
          ) : (
            result || 'La traduction appara\u00eetra ici.'
          )}
        </div>

        <div className="panel-footer">
          <div className="panel-heading-actions">
            <button className="icon-button" type="button" onClick={onCopy} disabled={!result} aria-label="Copier">
              <Copy size={19} />
            </button>
            {speakSupported && (
              <button
                className="icon-button"
                type="button"
                onClick={onSpeak}
                disabled={!result}
                aria-label="Écouter la traduction"
                title="Écouter la traduction"
              >
                <Volume2 size={19} />
              </button>
            )}
          </div>
          <span>{loading ? 'En direct...' : result ? 'Automatique' : 'En attente'}</span>
        </div>
      </div>

      <div className="translate-command">
        <button className="primary-action" type="button" onClick={onTranslate} disabled={loading || !text.trim()}>
          {loading ? <Loader2 className="spin" size={19} /> : <SendHorizontal size={19} />}
          {loading ? 'Traduction...' : 'Traduire'}
        </button>
        {status && <p>{status}</p>}
      </div>
    </section>
  );
}
