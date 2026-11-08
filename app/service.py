from app.guardrails import apply_guardrails, collect_missing_hints
from app.llm import complete_json
from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.render import to_markdown
from app.schemas import CardOut, ProductIn


async def generate_card(product: ProductIn) -> CardOut:
    hints = collect_missing_hints(product)
    payload = product.model_dump()
    raw = await complete_json(SYSTEM_PROMPT, build_user_prompt(payload, hints))
    draft = apply_guardrails(product, raw)
    return CardOut(**draft.model_dump(), markdown=to_markdown(product, draft))
