"""Sohbete getirilen resmî kanıttan sınırlı, model tarafından yazılmayan alıntı."""

import re


def source_excerpt(text: str, query: str = "") -> str:
    # Aynı ilk 1800 karakter modele de sunulur. Alıntıya daha fazlasını ekleme.
    normalized = " ".join(text[:1800].split())
    if len(normalized) <= 360:
        return normalized
    start = 0
    # Güvenilir bulgu sözlüğündeki ilk eşleşen teknik terimin çevresini seç;
    # önceki bölümden kalan sayfa başlığını rastgele alıntılama.
    for term in re.findall(r"[^\W_]+", query):
        if len(term) < 3 or term.lower() in {"ubl", "fatura", "doğrulama", "kontrol"}:
            continue
        match = re.search(r"\b" + re.escape(term) + r"\b", normalized, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 80)
            if start and normalized[start - 1] != " ":
                boundary = normalized.find(" ", start)
                if boundary >= 0:
                    start = boundary + 1
            break
    end = min(len(normalized), start + 360)
    if end < len(normalized):
        boundary = normalized.rfind(" ", start + 240, end + 1)
        if boundary >= start + 240:
            end = boundary
    return ("…" if start else "") + normalized[start:end].strip() + ("…" if end < len(normalized) else "")
