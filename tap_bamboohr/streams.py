"""Stream class for tap-bamboohr."""

import base64
from pathlib import Path

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import SimpleAuthenticator

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

class TapBambooHRStream(RESTStream):
    """BambooHR stream class."""

    @property
    def url_base(self) -> str:
        subdomain = self.config.get("subdomain")
        return f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1"

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        return headers

    @property
    def authenticator(self):
        http_headers = {}
        auth_token = self.config.get("auth_token")
        basic_auth = f"{auth_token}:nothingtoseehere"
        http_headers["Authorization"] = "Basic " + base64.b64encode(
            basic_auth.encode("utf-8")
        ).decode("utf-8")
        return SimpleAuthenticator(stream=self, auth_headers=http_headers)


class Employees(TapBambooHRStream):
    name = "employees"
    path = "/employees/directory"
    primary_keys = ["id"]
    records_jsonpath = "$.employees[*]"
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "directory.json"
