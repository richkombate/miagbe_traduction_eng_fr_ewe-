import { Activity, Database, Languages } from 'lucide-react';

export function ModelStatus({ health }) {
  return (
    <section className="status-strip">
      <div>
        <Activity size={18} />
        <span>{health?.status === 'ok' ? 'API active' : 'API en attente'}</span>
      </div>
      <div>
        <Languages size={18} />
        <span>{health?.backend || 'backend'}</span>
      </div>
      <div>
        <Database size={18} />
        <span>{health?.model_name || 'modele local'}</span>
      </div>
    </section>
  );
}
