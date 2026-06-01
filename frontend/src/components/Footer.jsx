import { Users } from 'lucide-react';

const GROUP = 'GR02';
const MEMBERS = [
  'AZIGLOSSOU Judith Gracia',
  'NAPO NISSAO Rafia',
  'WOGLO Koffi Boris Gilbride',
  'PIO Sikirou Afeez Prince Cyrille',
  'KOMBATE Gountande',
];

export function Footer() {
  return (
    <footer className="app-footer">
      <div className="footer-title">
        <Users size={18} />
        <span>Projet de groupe&nbsp;<strong>{GROUP}</strong> &middot; Master 1 IA-BD</span>
      </div>
      <ul className="footer-members">
        {MEMBERS.map((member) => (
          <li key={member}>{member}</li>
        ))}
      </ul>
      <p className="footer-note">
        Traducteur multilingue Fran&ccedil;ais &middot; Anglais &middot; &Eacute;w&eacute; avec reconnaissance vocale
      </p>
    </footer>
  );
}
