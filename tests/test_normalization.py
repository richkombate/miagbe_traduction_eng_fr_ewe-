from traducteur.nlp.normalization import normalize_text


def test_normalize_preserves_ewe_chars():
    assert normalize_text("  ƒe   ŋɔdi  ") == "ƒe ŋɔdi"
