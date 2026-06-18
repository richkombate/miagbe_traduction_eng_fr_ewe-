# Guide de soutenance — MiaGbe (Projet GR02, INF2229)

> Document d'étude : **Partie A** = questions/réponses probables du jury.
> **Partie B** = carte du code (savoir défendre n'importe quelle partie).
> Chiffres clés à connaître par cœur : **≈ 2 M** paires traitées → **1,06 M** exploitables
> → **697 744** retenues (train 669 904 / valid 13 853 / test 13 987).
> FLORES base→modèle : **+1,24 BLEU / +1,64 chrF**. Back-translation : **+3,1 BLEU EN→EWE**.

---

## PARTIE A — Questions / réponses du jury

### 1. Contexte & motivation
**Q. Pourquoi l'éwé ?**
Langue parlée par des millions de personnes au Togo/Ghana, mais **peu dotée** : très peu
de corpus numériques, mal couverte par les traducteurs grand public. Le projet comble ce
manque.

**Q. C'est quoi MiaGbe ?**
Le nom de notre application de traduction (« notre langue »). Elle traduit dans les
**6 directions** entre FR, EN, ÉWÉ, avec reconnaissance et synthèse vocales.

**Q. Quel est votre apport, concrètement ?**
Pas la collecte brute (données publiques), mais l'**ingénierie de données** (agrégation,
alignement, filtrage, contrôle du biais) + le **fine-tuning LoRA** + la **chaîne vocale**
+ l'**interface**.

### 2. Données & collecte (cœur du cours)
**Q. Comment avez-vous trouvé les données ?**
Ce sont des **données secondaires** : corpus parallèles publics et citables. Trois canaux
d'accès — **OPUS** (`opus.nlpl.eu`), **Hugging Face `datasets`**, et **GitHub** (Masakhane).

**Q. Données primaires ou secondaires ?**
**Secondaires** (réutilisation de corpus existants). Pas de collecte primaire (ni scraping
de nouveaux sites, ni enregistrements) — c'est la voie « bases de données ouvertes » du
cahier des charges.

**Q. Quelles sources exactement ?**
OPUS : NLLB (web-miné), Bible-uedin, TED2020, Tatoeba, News-Commentary, translatewiki ;
HF : google/SMOL, FLORES-200 ; GitHub : MAFAND (lafand-mt, Masakhane). Ghana NLP **retiré**.

**Q. Quelle quantité de données ?**
≈ **2 millions** de paires traitées → **1 090 357** exploitables après filtrage →
**697 744** retenues après plafond d'équilibrage. On a donc **écarté ~1,4 M de paires
exploitables par choix** (équilibrer les 6 directions, éviter que fr↔en écrase l'éwé).

**Q. Pourquoi avoir jeté autant de données ?**
Deux raisons : (1) **inexploitable** — ex. Ghana NLP 120 000 → 6 099 survivantes à
l'alignement (cosinus 0,34, très bruité) → écarté ; (2) **équilibrage** — plafond de
120 000/direction pour un corpus propre et équilibré, pas un volume brut déséquilibré.

**Q. Pourquoi pas de scraping (collecte primaire) ?**
Pour une langue peu dotée, produire des paires parallèles de qualité demande des
traducteurs bilingues — hors de portée d'un projet court. La pratique standard est
d'agréger et **nettoyer** les corpus publics. Le cahier des charges l'autorise.

**Q. Risque de biais dans les données ?**
Oui, le **biais biblique** (beaucoup de corpus éwé sont religieux). On le **trace**
(drapeau `is_religious`), on le **plafonne** (~5,5 % du train) et on a **retiré Ghana NLP**
(en–ewe d'origine biblique).

### 3. Prétraitement, alignement, tokenisation
**Q. Comment nettoyez-vous les données ?**
Normalisation **Unicode (NFC)** — crucial pour l'éwé accentué —, suppression des
caractères de contrôle/espaces insécables, et déduplication.

**Q. Comment alignez-vous les phrases ?**
Par **similarité cosinus** : on encode source et cible avec l'encodeur de NLLB et on garde
la paire si la similarité dépasse un seuil. Ça écarte les paires mal appariées.

**Q. Comment garantissez-vous que c'est bien de l'éwé ?**
Filtre d'**identification de langue** (fastText, modèle NLLB-LID) **+ une heuristique de
caractères éwé** (présence de ɖ ƒ ŋ ɔ ɛ ɣ ʋ), car la LID seule confond anglais et éwé sur
les phrases courtes.

**Q. C'est quoi la tokenisation, et laquelle ?**
Découper le texte en unités pour le modèle. On utilise le **tokenizer SentencePiece de
NLLB** (sous-mots, modèle *unigram*) : pas codé à la main, fourni avec le modèle. La langue
source/cible est injectée via les codes `fra_Latn`, `eng_Latn`, `ewe_Latn`.

**Q. Pas de fuite entre train et test ?**
Non : le découpage train/valid/test est figé **une fois pour toutes** et réutilisé partout.
Vérification automatique : **0 paire commune** train/test.

### 4. Modèle
**Q. Pourquoi NLLB-200 ?**
C'est un Transformer encodeur–décodeur de Meta entraîné sur **200 langues, dont l'éwé** —
idéal pour du transfert d'apprentissage vers une langue peu dotée. Version **distilled-600M**
= bon compromis qualité / coût (tient sur un GPU).

**Q. C'est quoi LoRA et pourquoi ?**
*Low-Rank Adaptation* : on **gèle** le modèle de base et on n'entraîne que de **petites
matrices** de rang faible. Quelques % de paramètres → rapide, économe, et **sans casser**
les connaissances multilingues de NLLB.

**Q. Quels hyperparamètres ?**
LoRA rang 32, α=64, dropout 0,05, sur les projections d'attention + feed-forward ;
2 époques ; lot effectif 64 ; lr 2e-4 ; bf16 + gradient checkpointing ; on garde le
meilleur checkpoint (eval_loss min).

**Q. Combien de temps / quel matériel ?**
GPU NVIDIA (RTX 5080), entraînement en bf16, ~quelques heures pour 2 époques sur ~200 k
exemples par run.

### 5. Back-translation
**Q. C'est quoi la back-translation ?**
Augmentation de données : on **garde l'éwé humain en cible** (qualité garantie) et on
fabrique une **source synthétique** (en/fr) avec le modèle entraîné. Trois jeux : A
(fr→en ⇒ en→ewe), A2 (⇒ ewe→en), B (ewe→fr ⇒ fr→ewe).

**Q. Ça a marché ?**
Oui : sur le test interne, **+3,1 BLEU en→ewe** et **+1,4 fr→ewe**, sans régression
ailleurs. La règle d'adoption (gagner sur en↔ewe sans régresser) est satisfaite → modèle
**adopté**.

**Q. N'est-ce pas tricher d'utiliser des données synthétiques ?**
Non : seule la **source** est synthétique, la **cible reste de l'éwé humain**. C'est une
technique standard pour les langues peu dotées. Garde-fou : cibles éwé pristines uniquement.

### 6. Évaluation
**Q. Quelles métriques et pourquoi deux ?**
**BLEU** (n-grammes de mots, comparable à la littérature) et **chrF** (n-grammes de
caractères, **adapté à l'éwé** morphologiquement riche et à diacritiques).

**Q. Pourquoi FLORES en plus du test interne ?**
Le **test interne** est *optimiste* (même domaine que l'entraînement). **FLORES-200**
(`devtest`) est un benchmark **externe, jamais vu**, aligné dans les 3 langues → mesure
**honnête** et comparable à l'état de l'art.

**Q. Quels résultats ?**
Sur FLORES, l'adaptateur **améliore les 6 directions** : **+1,24 BLEU / +1,64 chrF** en
moyenne, **aucune régression**.

**Q. Pourquoi l'écart entre interne (~30 BLEU) et FLORES (~11) en fr→ewe ?**
Le test interne est proche du domaine d'entraînement → trop optimiste. FLORES est hors
domaine → réaliste. C'est attendu et **assumé**.

### 7. Reconnaissance & synthèse vocales
**Q. Quels modèles pour la voix ?**
STT : **Whisper** (fr/en) + **MMS-ASR** de Meta pour l'**éwé** (1100+ langues).
TTS : **MMS-TTS** (VITS) pour l'éwé, voix navigateur pour fr/en.

**Q. Pourquoi pas Coqui/Google TTS (du cahier des charges) ?**
Ni Coqui ni Google ne fournissent de **voix éwé**. La seule voix éwé disponible est
**MMS-TTS** (`facebook/mms-tts-ewe`), servie par Transformers (déjà dans nos dépendances).

**Q. Et sans ffmpeg ?**
Le navigateur enregistre directement en **WAV**, décodé côté serveur par `librosa`
(16 kHz, mono) — pas besoin de ffmpeg.

### 8. Interface & architecture
**Q. Architecture technique ?**
Backend **FastAPI** (endpoints `/translate`, `/transcribe`, `/synthesize`, `/history`),
frontend **React/Vite**. Le modèle est chargé une fois et réutilisé.

**Q. Fonctionnalités de l'interface ?**
Saisie texte + traduction quasi instantanée, **dictée vocale** (3 langues), **écoute**
(TTS), **historique** synchronisé (connexion Google optionnelle).

### 9. Limites & perspectives
**Q. Limites ?**
La **génération vers l'éwé** reste le maillon faible (BLEU FLORES ~10–13) ; données éwé
de qualité rares ; reste un peu de biais de domaine.

**Q. Perspectives ?**
Confirmer la BT sur FLORES ; back-translation à plus grande échelle ; rang LoRA plus
élevé ; **annoter du contenu courant avec des locuteurs natifs** (levier le plus efficace).

### 10. Questions pièges
- **« Vous n'avez rien collecté vous-mêmes ? »** → données secondaires assumées ; l'apport
  est le tri/filtrage rigoureux (montrer l'entonnoir 2 M → 1,06 M → 698 k).
- **« Pourquoi si peu de BLEU vers l'éwé ? »** → langue peu dotée ; on mesure honnêtement
  sur FLORES ; la BT améliore.
- **« C'est ChatGPT qui a tout fait ? »** → on maîtrise chaque étape (cf. Partie B) ; le
  code, les choix de données et les analyses sont les nôtres.
- **« Différence primaire/secondaire ? »** → primaire = collecté directement par nous
  (scraping, enregistrement, enquête) ; secondaire = corpus déjà constitués par des tiers
  (notre cas).

---

## PARTIE B — Carte du code (défendre n'importe quelle partie)

### Notebooks (le cœur à défendre)

**`notebooks/00_donnees.ipynb` — construction du corpus (7 étapes)**
1. **Config & outils** : chemins, `clean_txt`, `write_canon`.
2. **Collecte** : OPUS (téléchargement des `.zip` Moses), HF `load_dataset` (SMOL, FLORES),
   GitHub (MAFAND).
3. **Alignement cosinus** : encodeur NLLB sur GPU ; on garde les paires au-dessus du seuil
   (`cosine_align`).
4. **Identification de langue** : fastText (`langid_filter`) puis heuristique caractères
   éwé (`ewe_filter`).
5. **Durcissement** : seuil cosinus relevé sur les sources bruitées (`_q70`).
6. **Assemblage** : chargement, dédup, **bidirectionnalisation**, plafond religieux,
   **plafond 120 000/direction**, découpage train/valid/test.
7. **Bilan** : `nllb_summary.csv`.
→ *Si on te montre une cellule au hasard, situe-la dans ces 7 étapes.*

**`notebooks/01_pipeline_nllb_lora.ipynb` — modèle**
- §2 config ; §4 chargement données ; §5 `get_peft_model(base, LoraConfig)` ;
  §6 `preprocess` (tokenisation, injection `src_lang`/`tgt_lang`) ; §7 `Seq2SeqTrainer` ;
  §9 éval BLEU/chrF ; **§10 FLORES base vs LoRA** via `model.disable_adapter()` ; §11 démo.

**`notebooks/02_backtranslation_nllb_lora.ipynb` — augmentation**
- §2 génération synthétique (A/A2/B) avec le modèle entraîné ; §3–6 ré-entraînement sur le
  train augmenté (dossier `nllb-ewe-lora-bt`) ; §8 éval ; §9 comparaison base vs BT.

### Code source `src/traducteur/`

**`config.py`** — `Settings` (pydantic) lues depuis `.env` : `translation_backend`,
`model_name`, `adapter_path`, `device`, `enable_stt/tts`. *« Tout est configurable sans
toucher au code. »*

**`nlp/languages.py`** — les 3 langues et leurs codes NLLB (`fra_Latn`…). `nllb_code()` et
`validate_lang()`. *Le pont entre nos codes courts et NLLB.*

**`nlp/normalization.py`** — `normalize_text` (NFC, **préserve les caractères éwé**) ;
`is_reasonable_text` (longueur ≤ 2000). *Pourquoi NFC : unifier les accents éwé.*

**`nlp/translator.py`** — `NLLBTranslator` : charge **paresseusement** le modèle de base +
l'adaptateur (depuis `adapter_path`), met `src_lang`, force `forced_bos_token_id` vers la
cible, génère (beam 4). En cas d'échec → **repli dictionnaire** (`FallbackTranslator`).
`build_translator()` choisit `nllb` ou `fallback`. *Lignes clés : `tokenizer.src_lang=…`,
`convert_tokens_to_ids(nllb_code(target))`.*

**`nlp/fallback_dictionary.py`** — mini-dictionnaire de démonstration (mode léger sans GPU).

**`data/ingestion.py`** — `read_parallel_csv` (ajoute un `id` UUID), `save_processed`
(CSV/Parquet). *Entrées/sorties du pipeline de données.*

**`data/cleaning.py`** — `normalize_unicode` (NFC), `clean_text` (espaces),
`clean_parallel_dataframe` (nettoie, retire les vides, **déduplique**).

**`evaluation/metrics.py`** — `compute_bleu`/`compute_chrf` (via `sacrebleu`),
`compute_wer`/`compute_cer` (via `jiwer`, pour l'audio). *Les métriques sont des appels à
des bibliothèques de référence, pas réimplémentées.*

**`audio/stt.py`** — Reconnaissance : Whisper (fr/en) + MMS-ASR (éwé). Détection GPU auto
(`_device`), adaptateur MMS **mis en cache**, fonction `warmup`. *Décodage WAV par librosa,
`argmax` sur les logits CTC pour MMS.*

**`audio/tts.py`** — Synthèse : modèles **VITS MMS-TTS** par langue (`facebook/mms-tts-*`),
`synthesize_to_wav` renvoie un WAV. *Chargement paresseux + cache (`lru_cache`).*

**`api/main.py`** — FastAPI. `get_translator()` (chargé une fois, `lru_cache`) ; endpoints
`/translate`, `/transcribe` (exécuté **hors boucle async** via `run_in_threadpool`),
`/synthesize`, `/history` ; **warm-up STT au démarrage**.

**`api/schemas.py`** — modèles pydantic des requêtes/réponses (validation entrées/sorties).

**`api/auth.py`** — `resolve_user` : vérifie un jeton Google si configuré, sinon identité de
démo (pour rattacher l'historique).

**`storage/history_store.py`** — persistance **SQLite** de l'historique (synchro
multi-navigateurs).

### Frontend `frontend/src/`
- **`App.jsx`** — état de l'app ; `handleMicToggle` → dictée **serveur** pour les 3 langues
  (enregistre puis transcrit) ; traduction *debounced* ; TTS ; historique.
- **`lib/recorder.js`** — enregistre le micro en **WAV** (Web Audio), sans ffmpeg.
- **`lib/api.js`** — appels `fetch` vers `/translate`, `/transcribe`, `/synthesize`,
  `/history`.
- **`hooks/useSpeech.js`** — synthèse vocale **navigateur** (fr/en) + `ttsSupported`.
- **`components/TranslatorWorkspace.jsx`** — l'UI (zones source/cible, boutons micro/écoute).

### Réflexe si on te pointe une ligne au hasard
1. **Quel fichier / quelle étape ?** (situe dans les 7 étapes du notebook 00, ou le module).
2. **Que fait cette ligne ?** (en une phrase).
3. **Pourquoi ce choix ?** (NFC pour l'éwé, cosinus pour l'alignement, LoRA pour le coût,
   chrF pour les diacritiques, WAV pour éviter ffmpeg…).