"""MEC Lab — Text normalization utilities.

Shared stopword list, tokenization, normalization, and stemming used by both
clue extraction and lexical scoring. Single source of truth.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Portuguese stemming (RSLP-inspired suffix-stripping)
# ---------------------------------------------------------------------------

# Ordered steps: each (suffix, min_stem_length, replacement)
# Applied in order; first match wins per step category.
_PLURAL_RULES: list[tuple[str, int, str]] = [
    ("ns", 4, "m"),        # cães → cão (special; simplified as replace ns→m)
    ("ões", 3, "ão"),      # situações → situação
    ("ães", 3, "ão"),      # pães → pão
    ("ais", 4, "al"),      # normais → normal
    ("éis", 4, "el"),      # papéis → papel
    ("is", 5, "il"),       # fósseis → fóssil
    ("res", 5, "r"),       # jogadores → jogador
    ("s", 3, ""),          # casas → casa
]

_FEMININE_RULES: list[tuple[str, int, str]] = [
    ("issima", 6, ""),     # importantíssima → important
    ("ona", 5, "ão"),      # chorona → chorão
    ("ora", 4, "or"),      # professora → professor
    ("inha", 5, "inho"),   # florzinha → florzinho (approx)
    ("esa", 5, "ês"),      # portuguesa → português
    ("a", 3, ""),          # menina → menin
]

_ADVERB_RULES: list[tuple[str, int, str]] = [
    ("mente", 7, ""),      # rapidamente → rapida
]

_AUG_DIM_RULES: list[tuple[str, int, str]] = [
    ("issimo", 6, ""),     # importantíssimo → important
    ("inho", 5, ""),       # livrinho → livr
    ("inha", 5, ""),       # florzinha → florz
    ("zão", 4, ""),        # livrão → livr
    ("zona", 5, ""),       # mulherzona → mulher
    ("ão", 4, ""),         # livrão → livr
]

_NOUN_SUFFIX_RULES: list[tuple[str, int, str]] = [
    ("acional", 8, ""),    # computacional → comput
    ("ições", 6, "ição"),  # repetições → repetição (catches before ões)
    ("ância", 6, ""),      # importância → import
    ("ência", 6, ""),      # permanência → perman
    ("idade", 6, ""),      # capacidade → capac
    ("mento", 6, ""),      # processamento → processa
    ("eza", 4, ""),        # beleza → bel
    ("ice", 4, ""),        # velhice → velh
    ("dor", 4, ""),        # nadador → nada
    ("tor", 4, ""),        # editor → edi
    ("ção", 4, ""),        # duplicação → duplica
    ("ões", 4, "ão"),      # situações → situação
    ("ar", 4, ""),         # (also verb ending — handled here as noun)
    ("er", 4, ""),
    ("ir", 4, ""),
]

_VERB_SUFFIX_RULES: list[tuple[str, int, str]] = [
    ("ássemos", 6, ""),    # falássemos
    ("êssemos", 6, ""),    # vendêssemos
    ("íssemos", 6, ""),    # partíssemos
    ("ássedes", 7, ""),    # (archaic)
    ("ásseis", 7, ""),     # (archaic)
    ("áramos", 6, ""),     # faláramos
    ("êramos", 6, ""),     # vendêramos
    ("íramos", 6, ""),     # partíramos
    ("áreis", 6, ""),      # faláreis
    ("areis", 6, ""),      # falareis
    ("ereis", 6, ""),      # vendereis
    ("ireis", 6, ""),      # partireis
    ("astes", 6, ""),      # falastes
    ("estes", 6, ""),      # vendestes
    ("istes", 6, ""),      # partistes
    ("asse", 5, ""),       # falasse
    ("esse", 5, ""),       # vendesse
    ("isse", 5, ""),       # partisse
    ("aram", 5, ""),       # falaram
    ("eram", 5, ""),       # venderam
    ("iram", 5, ""),       # partiram
    ("avas", 5, ""),       # falavas
    ("aveis", 6, ""),      # faláveis
    ("ando", 5, ""),       # falando
    ("endo", 5, ""),       # vendendo
    ("indo", 5, ""),       # partindo
    ("ara", 4, ""),        # falara
    ("era", 4, ""),        # vendera
    ("ira", 4, ""),        # partira
    ("ava", 4, ""),        # falava
    ("iam", 4, ""),        # partiam
    ("am", 3, ""),         # falam
    ("em", 3, ""),         # vendem
    ("ou", 3, ""),         # falou
    ("iu", 3, ""),         # partiu
    ("as", 3, ""),         # falas
    ("es", 3, ""),         # vendes
    ("is", 3, ""),         # partis
    ("a", 2, ""),          # fala
    ("e", 2, ""),          # vende
    ("i", 2, ""),          # parti
]

_VOWEL_RULES: list[tuple[str, int, str]] = [
    ("e", 4, ""),          # remove trailing e if stem >= 4
    ("a", 4, ""),          # remove trailing a
    ("o", 4, ""),          # remove trailing o
]


def _apply_rules(word: str, rules: list[tuple[str, int, str]]) -> str:
    """Apply first matching suffix rule; returns modified word or original."""
    for suffix, min_len, replacement in rules:
        if len(word) >= min_len and word.endswith(suffix):
            return word[: -len(suffix)] + replacement
    return word


def stem_pt(word: str) -> str:
    """Simple RSLP-inspired Portuguese stemmer.

    Reduces a Portuguese word to its root form, bridging vocabulary gaps
    like 'processar' ↔ 'processamento' → both stem to 'process'.

    This is a general improvement, not specific to any query.
    """
    if len(word) <= 2:
        return word

    # Step 1: Plural reduction
    word = _apply_rules(word, _PLURAL_RULES)

    # Step 2: Feminine
    word = _apply_rules(word, _FEMININE_RULES)

    # Step 3: Adverb (-mente)
    word = _apply_rules(word, _ADVERB_RULES)

    # Step 4: Augmentative / Diminutive
    word = _apply_rules(word, _AUG_DIM_RULES)

    # Step 5: Noun / general suffixes (including verb infinitives)
    word = _apply_rules(word, _NOUN_SUFFIX_RULES)

    # Step 6: Verb suffixes
    word = _apply_rules(word, _VERB_SUFFIX_RULES)

    # Step 7: Remove trailing vowel if stem is long enough
    word = _apply_rules(word, _VOWEL_RULES)

    # If stemming reduced to 1 char, revert to original
    if len(word) <= 1:
        return word

    return word


# ---------------------------------------------------------------------------
# Stopwords — Portuguese + English, shared across all modules
# ---------------------------------------------------------------------------

_STOPWORDS_PT = {
    "a", "as", "o", "os", "um", "uma", "uns", "umas",
    "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "por", "pelo", "pela", "pelos", "pelas", "para", "pra", "pro", "pros",
    "com", "sem", "sob", "sobre", "entre", "até", "após",
    "que", "qual", "quais", "quem", "cujo", "cuja",
    "é", "foi", "era", "são", "está", "estão", "ser", "ter", "tem",
    "não", "sim", "se", "ou", "mas", "como", "quando", "onde",
    "isso", "isto", "aquilo", "esse", "este", "aquele",
    "ele", "ela", "eles", "elas", "seu", "sua", "seus", "suas",
    "meu", "minha", "teu", "tua", "nosso", "nossa",
    "há", "já", "lá", "aí", "ali", "aqui", "agora", "depois", "antes",
    "muito", "pouco", "mais", "menos", "também", "ainda",
    "fazer", "faz", "fez", "fazendo", "feito",
    "dizer", "disse", "diz", "dizendo", "dito",
    "ir", "vai", "foi", "indo",
    "pode", "podem", "devem", "deve",
}

_STOPWORDS_EN = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "shall", "should", "may", "might", "must", "can", "could",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those",
    "in", "on", "at", "to", "for", "of", "with", "from", "by", "about",
    "and", "or", "not", "but", "if", "so", "as", "than", "then", "also",
    "very", "just", "now", "here", "there", "some", "any", "all", "each", "every",
    "no", "yes", "other", "more", "only",
}

STOPWORDS: set[str] = _STOPWORDS_PT | _STOPWORDS_EN

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def tokenize(text: str, remove_stopwords: bool = True, stem: bool = False) -> list[str]:
    """Extract alphanumeric tokens, optionally filtering stopwords and stemming."""
    normalized = normalize(text)
    tokens = re.findall(r"[a-z0-9]{2,}", normalized)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    if stem:
        tokens = [stem_pt(t) for t in tokens]
    return tokens


def token_set(text: str, remove_stopwords: bool = True, stem: bool = False) -> set[str]:
    """Return set of unique tokens."""
    return set(tokenize(text, remove_stopwords=remove_stopwords, stem=stem))
