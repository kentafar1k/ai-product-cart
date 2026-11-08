from app.schemas import CardDraft, ProductIn


def to_markdown(product: ProductIn, card: CardDraft) -> str:
    specs = "\n".join(f"- **{item.name}:** {item.value}" for item in card.key_specs)
    queries = "\n".join(f"- {q}" for q in card.search_queries) or "- данных нет"
    missing = "\n".join(f"- {m}" for m in card.missing_or_unclear) or "- нет"
    warnings = "\n".join(f"- {w}" for w in card.warnings) or "- нет"

    return f"""# {product.name}

**Производитель:** {product.manufacturer or "данных нет"}

## SEO-заголовок
{card.seo_title}

## SEO-описание
{card.seo_description}

## Ключевые характеристики
{specs}

## Поисковые запросы
{queries}

## Commercial-блок
{card.commercial_block}

## Что уточнить
{missing}

## Предупреждения генерации
{warnings}
""".strip()
