from pydantic import BaseModel


class BuyerVATVerifyRequest(BaseModel):
    country_code: str
    vat_number: str


class BuyerVATVerifyResponse(BaseModel):
    is_valid: bool
    name: str | None = None
    address: str | None = None
