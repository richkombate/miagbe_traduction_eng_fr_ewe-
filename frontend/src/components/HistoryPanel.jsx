import { Clock3, CloudOff, RefreshCw, RotateCcw, Star, Trash2 } from 'lucide-react';
import { getLanguageLabel } from '../lib/languages';
import { formatHistoryDate } from '../lib/storage';

export function HistoryPanel({
  user,
  history,
  saved,
  syncError,
  activeTab,
  onTabChange,
  onRestore,
  onToggleFavorite,
  onRemove,
  onClear,
}) {
  const items = activeTab === 'saved' ? saved : history;
  const title = activeTab === 'history' ? 'Traductions r\u00e9centes' : 'Traductions sauvegard\u00e9es';
  const count = items.length <= 1 ? `${items.length} traduction` : `${items.length} traductions`;

  return (
    <aside className="side-panel">
      <div className="side-tabs">
        <button className={activeTab === 'history' ? 'side-tab active' : 'side-tab'} type="button" onClick={() => onTabChange('history')}>
          <Clock3 size={18} />
          Historique
        </button>
        <button className={activeTab === 'saved' ? 'side-tab active' : 'side-tab'} type="button" onClick={() => onTabChange('saved')}>
          <Star size={18} />
          Favoris
        </button>
      </div>

      <div className="side-heading">
        <div>
          <strong>{title}</strong>
          <span>{user ? count : 'Disponible apr\u00e8s connexion'}</span>
        </div>
        {user && history.length > 0 && (
          <button className="icon-button compact danger" type="button" onClick={onClear} aria-label="Vider">
            <Trash2 size={17} />
          </button>
        )}
      </div>

      {user && (
        <p className={syncError ? 'sync-note offline' : 'sync-note'}>
          {syncError ? <CloudOff size={14} /> : <RefreshCw size={14} />}
          {syncError
            ? 'Hors ligne : modifications conservées localement.'
            : 'Synchronisé sur votre compte (tous vos navigateurs).'}
        </p>
      )}

      {!user ? (
        <p className="empty-state">Connectez-vous pour retrouver vos traductions plus tard.</p>
      ) : items.length === 0 ? (
        <p className="empty-state">{activeTab === 'history' ? 'Aucune traduction pour le moment.' : 'Aucun favori pour le moment.'}</p>
      ) : (
        <div className="history-list">
          {items.map((item) => (
            <article className="history-item" key={item.id}>
              <button className="history-body" type="button" onClick={() => onRestore(item)}>
                <span>
                  {getLanguageLabel(item.source)} vers {getLanguageLabel(item.target)}
                </span>
                <strong>{item.sourceText}</strong>
                <em>{item.translatedText}</em>
              </button>
              <div className="history-actions">
                <small>{formatHistoryDate(item.createdAt)}</small>
                <button className="icon-button compact" type="button" onClick={() => onRestore(item)} aria-label="Restaurer">
                  <RotateCcw size={16} />
                </button>
                <button
                  className={item.favorite ? 'icon-button compact saved' : 'icon-button compact'}
                  type="button"
                  onClick={() => onToggleFavorite(item.id)}
                  aria-label="Favori"
                >
                  <Star size={16} />
                </button>
                <button className="icon-button compact danger" type="button" onClick={() => onRemove(item.id)} aria-label="Supprimer">
                  <Trash2 size={16} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </aside>
  );
}
