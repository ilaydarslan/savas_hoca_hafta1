"""Deterministic advisory strategies; scope suggestions never grant authority."""
import re
import unicodedata
from typing import Protocol

SCOPES = ('COMMUNITY', 'DEPARTMENT', 'FACULTY', 'UNIVERSITY')


def normalize(text: str) -> str:
    return unicodedata.normalize('NFC', text).replace('I', 'ı').replace('İ', 'i').lower()


class ScopeStrategy(Protocol):
    def predict(self, text: str) -> str | None: ...


class ConstantScopeStrategy:
    """Fixed COMMUNITY reference, not a fitted majority-class estimator."""
    def predict(self, text: str) -> str:
        return 'COMMUNITY'


class KeywordScopeStrategy:
    TERMS = {
        'COMMUNITY': ('topluluk', 'kulüp', 'akran', 'çalışma grubu'),
        'DEPARTMENT': ('bölüm', 'bölüm başkanlığı', 'anabilim dalı'),
        'FACULTY': ('fakülte', 'dekanlık', 'dekan'),
        'UNIVERSITY': ('üniversite', 'rektörlük', 'senato', 'kampüs'),
    }

    def matches(self, text: str) -> dict[str, list[str]]:
        text = normalize(text)
        # Match Turkish stems at word starts to allow suffixes without matching
        # arbitrary substrings inside unrelated words. This is not morphology.
        return {scope: [term for term in terms if re.search(r'(?<!\w)' + re.escape(term), text)]
                for scope, terms in self.TERMS.items()}

    def predict(self, text: str) -> str | None:
        candidates = [scope for scope, terms in self.matches(text).items() if terms]
        return candidates[0] if len(candidates) == 1 else None

    def suggest(self, text: str) -> dict:
        matches = self.matches(text)
        candidates = [scope for scope, terms in matches.items() if terms]
        scope = candidates[0] if len(candidates) == 1 else None
        explanation = ('Tek kapsama ait anahtar sözcük bulundu. Öneriyi konu sahibi doğrulamalıdır.'
                       if scope else 'Birden fazla kapsama ait sözcük bulundu; kapsamı insan seçmelidir.'
                       if candidates else 'Kapsamı belirleyecek anahtar sözcük bulunamadı; kapsamı insan seçmelidir.')
        return {'suggested_scope': scope,
                'matched_terms': [term for terms in matches.values() for term in terms],
                'needs_review': True,
                'explanation': explanation + ' Bu kural tabanlı öneri yetki vermez ve kayıt değiştirmez.'}
