import os

# Les tests s'exécutent en mode `fallback` pour rester rapides et déterministes
# (aucun téléchargement ni chargement du modèle NLLB de 600M). Doit être défini
# avant l'import de l'application, qui lit la configuration au chargement.
os.environ.setdefault("TRANSLATION_BACKEND", "fallback")
