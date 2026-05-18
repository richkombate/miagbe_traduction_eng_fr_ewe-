export const LANGUAGES = [
  { code: 'fra', label: 'Fran\u00e7ais', tone: '#d21034' },
  { code: 'eng', label: 'Anglais', tone: '#006a4e' },
  { code: 'ewe', label: 'Ewe', tone: '#b38600' },
];

export function getLanguageLabel(code) {
  return LANGUAGES.find((language) => language.code === code)?.label || code;
}
