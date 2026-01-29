import httpx
import xml.etree.ElementTree as ET

VIES_ENDPOINT = "https://ec.europa.eu/taxation_customs/vies/services/checkVatService"


class ViesService:
    async def check_vat(self, country_code: str, vat_number: str) -> dict:
        envelope = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <checkVat xmlns="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
                    <countryCode>{country_code}</countryCode>
                    <vatNumber>{vat_number}</vatNumber>
                </checkVat>
            </soap:Body>
        </soap:Envelope>
        """
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        async with httpx.AsyncClient() as client:
            response = await client.post(VIES_ENDPOINT, content=envelope, headers=headers, timeout=15)
            response.raise_for_status()

        tree = ET.fromstring(response.text)
        ns = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "ns2": "urn:ec.europa.eu:taxud:vies:services:checkVat:types",
        }
        body = tree.find("soap:Body", ns)
        if body is None:
            return {"valid": False}
        result = body.find("ns2:checkVatResponse", ns)
        if result is None:
            return {"valid": False}
        valid = result.findtext("ns2:valid", default="false", namespaces=ns) == "true"
        name = result.findtext("ns2:name", default=None, namespaces=ns)
        address = result.findtext("ns2:address", default=None, namespaces=ns)
        return {"valid": valid, "name": name, "address": address}
