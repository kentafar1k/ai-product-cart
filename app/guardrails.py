from __future__ import annotations

import re
from typing import Any

from app.schemas import CardDraft, ProductIn, SpecItem

MISSING_MARK = "данных нет"
SEO_TITLE_MAX = 70
SEO_DESC_MIN = 800
SEO_DESC_MAX = 1200

_TECHNICAL_KEYS = (
    "питание",
    "напряжение",
    "интерфейс",
    "диапазон",
    "класс точности",
    "погрешность",
    "ip",
    "присоедин",
    "гост",
)


def collect_missing_hints(product: ProductIn) -> list[str]:
    hints: list[str] = []
    if not product.manufacturer:
        hints.append("Не указан производитель.")
    if not product.description:
        hints.append("Нет текстового описания или фрагмента паспорта.")
    filled_specs = {k: v for k, v in product.specs.items() if v}
    if not filled_specs:
        hints.append("Нет технических характеристик.")
    else:
        only_ids = all(
            any(token in key.lower() for token in ("артикул", "код товара", "vendorcode"))
            for key in filled_specs
        )
        if only_ids:
            hints.append(
                "В specs есть только идентификаторы (артикул/код), нет измерительных параметров."
            )
    return hints


def source_text(product: ProductIn) -> str:
    parts = [product.name, product.manufacturer, product.description]
    for key, value in product.specs.items():
        parts.append(key)
        parts.append(value)
    return " ".join(parts).lower()


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("ё", "е"))


def _looks_invented(value: str, source: str) -> bool:
    if not value or _normalize(value) == MISSING_MARK:
        return False
    compact_value = _normalize(value)
    compact_source = _normalize(source)
    if compact_value in compact_source:
        return False
    tokens = re.findall(r"[a-zа-я0-9]+(?:[.,]\d+)?", compact_value)
    meaningful = [t for t in tokens if len(t) > 1]
    if not meaningful:
        return False
    return any(token not in compact_source for token in meaningful)


def apply_guardrails(product: ProductIn, raw: dict[str, Any]) -> CardDraft:
    hints = collect_missing_hints(product)
    source = source_text(product)
    warnings: list[str] = []

    seo_title = str(raw.get("seo_title") or product.name)[:SEO_TITLE_MAX].rstrip()
    seo_description = str(raw.get("seo_description") or "").strip()
    commercial = str(raw.get("commercial_block") or "").strip()
    queries = [str(q).strip() for q in raw.get("search_queries") or [] if str(q).strip()]
    missing = [str(x).strip() for x in raw.get("missing_or_unclear") or [] if str(x).strip()]

    for hint in hints:
        if hint not in missing:
            missing.append(hint)

    if len(seo_description) < SEO_DESC_MIN:
        warnings.append(
            f"SEO-описание короче {SEO_DESC_MIN} символов ({len(seo_description)}). "
            "Контент-менеджеру стоит дописать текст, не добавляя новых характеристик."
        )
    elif len(seo_description) > SEO_DESC_MAX:
        seo_description = seo_description[:SEO_DESC_MAX].rstrip()
        warnings.append(f"SEO-описание обрезано до {SEO_DESC_MAX} символов.")

    queries = queries[:5]
    if len(queries) < 3:
        warnings.append("Модель вернула меньше трёх поисковых запросов.")
        missing.append("Нужно дополнить поисковые запросы до 3–5 штук.")

    input_specs = product.specs
    raw_specs = raw.get("key_specs") or []
    model_values: dict[str, str] = {}
    if isinstance(raw_specs, list):
        for item in raw_specs:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            value = str(item.get("value") or "").strip()
            if name:
                model_values[name] = value

    key_specs: list[SpecItem] = []
    used_names = set()
    for name, original in input_specs.items():
        used_names.add(_normalize(name))
        value = original.strip() if original.strip() else MISSING_MARK
        proposed = model_values.get(name, value)
        if original.strip():
            if _looks_invented(proposed, original + " " + source):
                warnings.append(f"Отклонено значение характеристики «{name}»: нет во входных данных.")
                value = original.strip()
            else:
                value = original.strip()
        else:
            value = MISSING_MARK
        key_specs.append(SpecItem(name=name, value=value))

    for name, value in model_values.items():
        if _normalize(name) in used_names:
            continue
        if _looks_invented(value, source) or _normalize(value) != MISSING_MARK:
            warnings.append(f"Удалена характеристика «{name}»: её не было во входных specs.")
            continue
        key_specs.append(SpecItem(name=name, value=MISSING_MARK))

    if not key_specs:
        key_specs.append(SpecItem(name="характеристики", value=MISSING_MARK))
        if "Нет технических характеристик." not in missing:
            missing.append("Нет технических характеристик.")

    if any(token in _normalize(seo_title) for token in _TECHNICAL_KEYS) and _looks_invented(seo_title, source):
        seo_title = product.name[:SEO_TITLE_MAX]
        warnings.append("SEO-заголовок сброшен к названию товара: модель добавила факты не из входа.")

    return CardDraft(
        seo_title=seo_title,
        seo_description=seo_description,
        key_specs=key_specs,
        search_queries=queries,
        commercial_block=commercial or MISSING_MARK,
        missing_or_unclear=missing,
        warnings=warnings,
    )
