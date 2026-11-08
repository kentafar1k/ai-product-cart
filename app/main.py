import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.llm import LLMError
from app.schemas import ProductIn
from app.service import generate_card

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="AI Product Card Draft",
    description="Черновик карточки товара КИПиА для контент-менеджера",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _sample_product() -> ProductIn:
    sample_path = BASE_DIR / "samples" / "product_1.json"
    if not sample_path.exists():
        return ProductIn(name="Товар")
    return ProductIn.model_validate_json(sample_path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    sample = _sample_product()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "name": sample.name,
            "manufacturer": sample.manufacturer,
            "description": sample.description,
            "specs_json": json.dumps(sample.specs, ensure_ascii=False, indent=2),
            "result": None,
            "error": None,
            "raw_json": "",
        },
    )


@app.post("/generate")
async def generate(product: ProductIn) -> JSONResponse:
    try:
        card = await generate_card(product)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return JSONResponse(card.model_dump())


@app.post("/generate-form", response_class=HTMLResponse)
async def generate_form(
    request: Request,
    name: str = Form(""),
    manufacturer: str = Form(""),
    description: str = Form(""),
    specs_json: str = Form(""),
) -> HTMLResponse:
    error = None
    result = None
    raw_json = ""
    try:
        specs = json.loads(specs_json) if specs_json.strip() else {}
        product = ProductIn(
            name=name,
            manufacturer=manufacturer,
            description=description,
            specs=specs,
        )
        card = await generate_card(product)
        result = card
        raw_json = json.dumps(card.model_dump(exclude={"markdown"}), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        error = "Поле specs должно быть корректным JSON-объектом, например {\"класс точности\": \"1,5\"}."
    except ValidationError as exc:
        error = "Некорректные входные данные: " + "; ".join(
            e["msg"] for e in exc.errors()
        )
    except LLMError as exc:
        error = str(exc)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "sample_json": "",
            "name": name,
            "manufacturer": manufacturer,
            "description": description,
            "specs_json": specs_json,
            "result": result,
            "error": error,
            "raw_json": raw_json,
        },
    )
