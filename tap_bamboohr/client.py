"""REST client handling, including BambooHRStream base class."""

from pathlib import Path
from typing import Type

from singer_sdk import typing as th
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.streams import RESTStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class TapBambooHRStream(RESTStream):
    """BambooHR stream class."""

    @property
    def url_base(self) -> str:
        subdomain = self.config["subdomain"]
        return f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1"

    records_jsonpath = "$.employees[*]"

    @property
    def authenticator(self) -> BasicAuthenticator:
        """Return a new authenticator object."""
        return BasicAuthenticator.create_for_stream(
            self,
            username=str(self.config.get("auth_token")),
            password="anystring",
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        return headers

    def map_type(self, name: str) -> Type[th.JSONTypeHelper]:
        # https://documentation.bamboohr.com/docs/field-types
        type_lookup: dict[str, Type[th.JSONTypeHelper]] = {
            "date": th.DateType,
            "text": th.StringType,
            "ssn": th.StringType,
            "phone": th.StringType,
            "gender": th.StringType,
            "currency": th.NumberType,
            "checkbox": th.BooleanType,
            "state": th.StringType,
            "marital_status": th.StringType,
            "status": th.StringType,
            "pay_type": th.StringType,
            "employee": th.StringType,
            "timestamp": th.DateTimeType,
            "textarea": th.StringType,
            "list": th.StringType,
            "email": th.EmailType,
            "bool": th.BooleanType,
            "employee_access": th.StringType,
        }

        type = type_lookup.get(name)
        if not type:
            type = th.StringType

        return type
