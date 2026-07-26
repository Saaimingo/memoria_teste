"""MEC Lab — Text normalization utilities.

Shared stopword list, tokenization, and normalization used by both
clue extraction and lexical scoring. Single source of truth.
"""

import re
import unicodedata

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


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Extract alphanumeric tokens, optionally filtering stopwords."""
    normalized = normalize(text)
    tokens = re.findall(r"[a-z0-9]{2,}", normalized)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens


def token_set(text: str, remove_stopwords: bool = True) -> set[str]:
    """Return set of unique tokens."""
    return set(tokenize(text, remove_stopwords=remove_stopwords))
