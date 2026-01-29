import re


class EoriValidationService:
    def validate_vat(self, vat_number: str) -> bool:
        return bool(re.fullmatch(r"\d{9}", vat_number))

    def generate_eori(self, vat_number: str) -> str:
        return f"GB{vat_number}000"

    def validate_eori(self, eori_number: str) -> bool:
        return bool(re.fullmatch(r"GB\d{12,15}", eori_number))
