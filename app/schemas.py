from pydantic import BaseModel, Field, field_validator


class ProductIn(BaseModel):
    name: str = Field(..., min_length=1, description="Название товара")
    manufacturer: str = ""
    specs: dict[str, str] = Field(default_factory=dict)
    description: str = ""

    @field_validator("name", "manufacturer", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("specs", mode="before")
    @classmethod
    def normalize_specs(cls, value: object) -> object:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("поле specs должно быть объектом ключ-значение")
        cleaned: dict[str, str] = {}
        for key, raw in value.items():
            name = str(key).strip()
            if not name:
                continue
            text = "" if raw is None else str(raw).strip()
            cleaned[name] = text
        return cleaned


class SpecItem(BaseModel):
    name: str
    value: str


class CardDraft(BaseModel):
    seo_title: str
    seo_description: str
    key_specs: list[SpecItem]
    search_queries: list[str]
    commercial_block: str
    missing_or_unclear: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CardOut(CardDraft):
    markdown: str = ""
