# Sources de corpus paralleles pour francais, anglais et ewe

Cette fiche liste les sources verifiees le 2026-05-18 pour constituer un corpus
parallele exploitable. Les colonnes canoniques du projet sont:

```text
id,src_lang,tgt_lang,src_text,tgt_text,source
```

## Priorite 1: sources deja alignees

| Source | Paires utiles | Volume constate | Usage conseille |
| --- | --- | ---: | --- |
| [FLORES-200](https://huggingface.co/datasets/facebook/flores) | `ewe_Latn`, `fra_Latn`, `eng_Latn` | 3001 phrases par langue, splits `dev`, `devtest`, `test` cache | Evaluation et validation, pas entrainement massif |
| [OPUS NLLB v1](https://opus.nlpl.eu/NLLB.php) | ewe-francais | 1 039 385 alignements | Gros volume d'entrainement, a filtrer |
| [OPUS bible-uedin v1](https://opus.nlpl.eu/bible-uedin.php) | ewe-anglais, ewe-francais | 16 001 / 8 004 alignements | Domaine biblique, bon alignement, attention au biais de domaine |
| [BibleNLP Corpus](https://huggingface.co/datasets/bible-nlp/biblenlp-corpus) | ewe, anglais, francais | corpus biblique multilingue aligne par verset | Complement Bible, utile pour trianguler les versets |
| [Ghana NLP English-Ewe 4M](https://huggingface.co/datasets/ghananlpcommunity/english-ewe-sentence-pairs-4m) | anglais-ewe | 4 408 322 exemples | Tres gros volume, a filtrer fortement par score de similarite |
| [Ewe-French Sentence Pairs](https://huggingface.co/datasets/michsethowusu/ewe-french_sentence-pairs) | ewe-francais | 1 039 409 exemples | Version Hugging Face de NLLB/OPUS, pratique en Parquet/CSV |
| [OPUS TED2020](https://opus.nlpl.eu/TED2020.php) | anglais-francais | 410 443 alignements | Conversations et exposes, bon corpus general |
| [OPUS News-Commentary](https://opus.nlpl.eu/News-Commentary.php) | anglais-francais | 156 122 alignements | Actualite/commentaire, utile pour style formel |
| [OPUS Tatoeba](https://opus.nlpl.eu/Tatoeba.php) | anglais-francais | 275 413 alignements | Phrases courtes du quotidien |
| [OPUS Europarl](https://opus.nlpl.eu/Europarl.php) | anglais-francais | 2 051 014 alignements | Qualite forte, mais domaine parlementaire |
| [OPUS Wikimedia](https://opus.nlpl.eu/wikimedia.php) | anglais-francais | 1 446 495 alignements | Encyclopedique/web, a filtrer |

## Priorite 2: petits corpus OPUS utiles

| Source OPUS | Paire | Volume constate |
| --- | --- | ---: |
| Tatoeba | ewe-anglais | 6 |
| Wikimedia | ewe-anglais | 171 |
| Wikimedia | ewe-francais | 45 |
| translatewiki | ewe-francais | petit corpus UI, volume non renseigne par l'API |

## Sources a auditer avant usage

QED v2.0a apparait dans l'API OPUS pour `ee-en` et `ee-fr`, mais un test local
du fichier `ee-en` a montre des phrases qui ne ressemblent pas a de l'ewe.
Ces corpus sont donc exclus du telechargement recommande et ne doivent pas etre
melanges au jeu final sans audit manuel.

## JW300

JW300 etait cite dans le cahier des charges, mais l'API OPUS ne retourne aucun
corpus actuel pour les paires `ee-en`, `ee-fr`, `ewe-eng` ou `ewe-fra`.
Il ne faut donc pas le mettre dans la pile principale sans verification manuelle
ou autorisation specifique de scraping.

## Eviter le biais religieux

Les corpus `bible-uedin` et BibleNLP sont utiles pour obtenir rapidement de
l'ewe aligne, mais ils ne doivent pas dominer le jeu d'entrainement. Pour un
modele generaliste, la selection recommandee exclut les corpus religieux par
defaut. Gardez les corpus bibliques dans un sous-ensemble separe et limitez-les
a 0-5 % du train final, ou utilisez-les seulement pour une experience separee.

## Liens directs OPUS convertibles avec le script

```powershell
python scripts/download_opus_parallel.py --list
python scripts/download_opus_parallel.py --source bible_ee_en
python scripts/download_opus_parallel.py --source bible_ee_fr
python scripts/download_opus_parallel.py --source nllb_ee_fr
python scripts/download_opus_parallel.py --source ted2020_en_fr
python scripts/download_opus_parallel.py --source news_commentary_en_fr
python scripts/download_opus_parallel.py --source recommended
```

Les fichiers CSV generes vont dans `data/processed/opus/`.

## Controle qualite recommande

1. Normaliser Unicode en NFC.
2. Supprimer les lignes vides, doublons exacts et segments trop longs.
3. Filtrer les paires avec ratio de longueur extreme.
4. Garder FLORES-200 uniquement pour evaluation/devtest.
5. Separer le domaine biblique des donnees generales pour eviter un modele trop specialise.
6. Faire valider un echantillon ewe par un locuteur natif ou un enseignant.

## Format final conseille pour NLLB

Chaque ligne d'entrainement doit etre directionnelle: une ligne pour `fra -> ewe`
est differente d'une ligne pour `ewe -> fra`. Les codes NLLB a utiliser sont
`fra_Latn`, `eng_Latn` et `ewe_Latn`.

Colonnes recommandees:

```text
id,split,src_lang,tgt_lang,src_lang_nllb,tgt_lang_nllb,src_text,tgt_text,source,domain,quality_score,is_religious,license
```

Repartition initiale raisonnable:

| Paire directionnelle | Part conseillee | Sources principales |
| --- | ---: | --- |
| anglais -> ewe et ewe -> anglais | 35-45 % | Ghana NLP English-Ewe 4M filtre |
| francais -> ewe et ewe -> francais | 35-45 % | OPUS NLLB / Ewe-French filtre |
| anglais -> francais et francais -> anglais | 10-20 % | TED2020, News-Commentary, Tatoeba, Europarl |
| religieux | 0-5 % max | bible-uedin / BibleNLP, separe et tague |

Gardez FLORES-200 hors du train: utilisez-le pour `dev` et `test`.

## Sources locales validees a constituer

Les sites locaux togolais sont majoritairement en francais et rarement alignes
avec l'ewe. Le meilleur complement local est donc un petit corpus controle:

- phrases administratives et scolaires traduites par un locuteur ewe;
- dialogues de sante, transport, commerce et universite;
- lexique terminologique francais-anglais-ewe;
- transcriptions audio courtes avec consentement explicite;
- fiches de validation indiquant traducteur, date, variante dialectale et niveau de confiance.
