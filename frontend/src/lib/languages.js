export const LANGUAGES = [
  { code: 'fra', label: 'Francais', nllb: 'fra_Latn', tone: '#1a73e8' },
  { code: 'eng', label: 'Anglais', nllb: 'eng_Latn', tone: '#188038' },
  { code: 'ewe', label: 'Ewe', nllb: 'ewe_Latn', tone: '#b06000' },
];

export function getLanguageLabel(code) {
  return LANGUAGES.find((language) => language.code === code)?.label || code;
}
