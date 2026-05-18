# Notebook unique

Le pipeline notebook est maintenant regroupe dans un seul fichier:

- `01_pipeline_nllb_lora.ipynb` : exploration du corpus, controle GPU, fine-tuning LoRA de NLLB, suivi des pertes, evaluation BLEU/chrF et demo de traduction.

Avant de lancer le notebook, verifiez que PyTorch detecte le GPU:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Si le resultat est `False`, installez PyTorch CUDA dans le `.venv` avant de lancer l'entrainement.
