Les donnees brutes ne sont pas versionnees. Placez les corpus dans `raw/`,
puis exportez les jeux nettoyes dans `processed/`.

Consultez `SOURCES.md` pour les sources de corpus paralleles verifiees.
La construction du corpus (telechargement OPUS, alignement, nettoyage, filtres,
decoupage train/valid/test) est entierement assuree par le notebook
`notebooks/00_donnees.ipynb`, qui ecrit les CSV canoniques dans `processed/`.
