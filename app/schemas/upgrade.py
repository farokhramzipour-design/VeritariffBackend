from pydantic import BaseModel


class UKExporterStartResponse(BaseModel):
    authorization_url: str


class VATSubmission(BaseModel):
    vat_number: str


class VATSubmissionResponse(BaseModel):
    eori_autodetected: bool
    requires_manual_eori: bool
    eori_number: str | None = None


class EORISubmission(BaseModel):
    eori_number: str


class UpgradeOptionsResponse(BaseModel):
    can_upgrade_uk_exporter: bool
    can_upgrade_forwarder: bool
    can_upgrade_eu_member: bool
    next_step: str


class EUVerifyVATRequest(BaseModel):
    country_code: str
    vat_number: str


class EUVerifyVATResponse(BaseModel):
    is_valid: bool
    name: str | None = None
    address: str | None = None
