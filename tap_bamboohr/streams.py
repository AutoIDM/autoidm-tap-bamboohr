"""Stream class for tap-bamboohr."""

import base64
from typing import Dict, Optional, Any, Iterable
from pathlib import Path
from singer_sdk import typing
from functools import cached_property
from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import SimpleAuthenticator
import requests


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

class TapBambooHRStream(RESTStream):
    """BambooHR stream class."""

    _LOG_REQUEST_METRIC_URLS: bool = True
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

class CustomReport(TapBambooHRStream):
    path = "/reports/custom"
    primary_keys = ["id"]
    records_jsonpath = "$.employees[*]"
    replication_key = None
    rest_method = "POST"
    @property
    def schema(self):
        list_of_fields = []
        for field in self.custom_report_config["fields"]:
            list_of_fields.append(typing.Property(field, typing.StringType))
        return typing.PropertiesList(*list_of_fields).to_dict()


    def __init__(self, name, custom_report_config, *args, **kwargs):
        self.name = name
        self._custom_report_config = custom_report_config
        super().__init__(*args, **kwargs)
    
    @property
    def custom_report_config(self):
        return self._custom_report_config

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {"format":"JSON"}
    
    def prepare_request_payload(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Optional[dict]:
        """Prepare the data payload for the REST API request.

        Args:
            context: Stream partition or context dictionary.
            next_page_token: Token, page number or any request argument to request the
                next page of data.

        Returns:
            Dictionary with the body to use for the request.
        """
        return self.custom_report_config

#A more generic tables stream would be better, there is a table metadata api
class EmploymentHistoryStatus(TapBambooHRStream):
    name = "tables_employmentstatus"
    path = "/employees/changed/tables/employmentStatus"
    primary_keys = ["employee_id", "date", "employmentstatus"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "employmentstatus.json"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {"since":"2012-01-01T00:00:00Z"} #I want all of the data, 2012 is far enough back and referenced in the API Docs
    
    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows.

        Args:
            response: A raw `requests.Response`_ object.

        Yields:
            One item for every item found in the response.

        .. _requests.Response:
            https://docs.python-requests.org/en/latest/api/#requests.Response
        """
        for employeeid, value in response.json()["employees"].items():
            last_changed = value["lastChanged"]
            rows = value["rows"]
            for row in rows:
                row.update({"lastChanged":last_changed})
                row.update({"employee_id":employeeid})
                yield row
