"""Pre-save check for health/family words in session records.

This is a guidance feature, not a security boundary: when a mentor's record
contains words that suggest health or family information, the API asks for
confirmation before saving (records should hold learning content only).
Words are chosen to avoid common math/learning terms (e.g. 약수, 약분, 진단평가).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

SENSITIVE_TERMS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "health": (
            "감기",
            "독감",
            "몸살",
            "기침",
            "열이 나",
            "열이 있",
            "두통",
            "복통",
            "배탈",
            "코로나",
            "깁스",
            "병원",
            "진료",
            "입원",
            "수술",
            "복용",
            "약물",
            "처방",
            "질환",
            "질병",
            "아토피",
            "알레르기",
            "알러지",
            "우울",
            "불안장애",
            "ADHD",
            "adhd",
            "장애",
            "다쳤",
            "부상",
            "아파서",
            "아프다",
            "아팠",
        ),
        "family": (
            "이혼",
            "별거",
            "재혼",
            "가정폭력",
            "학대",
            "방임",
            "수급",
            "기초생활",
            "한부모",
            "조손",
            "부모님이 싸",
            "아빠가 때",
            "엄마가 때",
            "가출",
            "보호자 연락",
        ),
    }
)


def detect_sensitive_categories(texts: Iterable[str]) -> list[str]:
    joined = "\n".join(texts)
    return [
        category
        for category, terms in SENSITIVE_TERMS.items()
        if any(term in joined for term in terms)
    ]
