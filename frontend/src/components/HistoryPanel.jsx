import { Clock3, RotateCcw, Star, Trash2 } from 'lucide-react';
import { formatHistoryDate } from '../lib/storage';
import { getLanguageLabel } from '../lib/languages';

export function HistoryPanel({
  user,
  history,
  saved,
  activeTab,
  onTabChange,
  onRestore,
  onToggleFavorite,
  onRemove,
  onClear,
}) {
  const items = activeTab === 'saved' ? saved : history;

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
          <strong>{activeTab === 'history' ? 'Traductions recentes' : 'Traductions sauvegardees'}</strong>
          <span>{user ? `${items.length} element(s)` : 'Connexion Google requise'}</span>
        </div>
        {user && history.length > 0 && (
          <button className="icon-button compact danger" type="button" onClick={onClear} aria-label="Vider">
            <Trash2 size={17} />
          </button>
        )}
      </div>

      {!user ? (
        <p className="empty-state">Connectez-vous avec Google pour conserver vos traductions.</p>
      ) : items.length === 0 ? (
        <p className="empty-state">{activeTab === 'history' ? 'Aucune traduction.' : 'Aucun favori.'}</p>
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
