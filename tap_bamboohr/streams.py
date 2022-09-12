"""Stream type classes for tap-bamboohr."""

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
from memoization import cached
from singer_sdk import typing as th
from singer_sdk.exceptions import FatalAPIError
from singer_sdk.helpers.jsonpath import extract_jsonpath

from tap_bamboohr.client import TapBambooHRStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class Employees(TapBambooHRStream):
    name = "employees"
    path = "/employees/directory"
    primary_keys = ["id"]
    records_jsonpath = "$.employees[*]"
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "directory.json"


class TableStream(TapBambooHRStream):
    primary_keys = ["id", "rowid"]
    records_jsonpath = "$.employees"
    replication_key = "employeeLastChanged"

    def __init__(self, table_schema, *args, **kwargs):
        self.name = table_schema["alias"]
        self._table_fields = table_schema["fields"]
        super().__init__(*args, **kwargs)

    @property
    def path(self) -> str:
        return "/employees/changed/tables/" + requests.utils.quote(self.name, safe="")

    @property
    @cached
    def schema(self) -> dict:
        list_of_fields = [
            th.Property("id", th.IntegerType, required=True),
            th.Property("rowid", th.IntegerType, required=True),
            th.Property("employeeLastChanged", th.DateTimeType, required=True),
        ]
        for field in self._table_fields:
            list_of_fields.append(
                th.Property(
                    field["alias"],
                    self.map_type(field["type"]),
                    description=field["name"],
                )
            )
        return th.PropertiesList(*list_of_fields).to_dict()

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if self.replication_key:
            params["since"] = self.get_starting_timestamp(context)
        return params

    def validate_response(self, response: requests.Response) -> None:
        if response.status_code == 404:
            msg = f"Table {self.name} is mysteriously unavailable on BambooHR's API. You should exclude it from the catalog."
            raise FatalAPIError(msg)
        else:
            super().validate_response(response)

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        self.logger.info(self.name)
        for resp in extract_jsonpath(self.records_jsonpath, input=response.json()):
            rows = []
            if not resp:
                break
            for key_id in resp.keys():
                rowid = 0
                employeeLastChanged = resp[key_id]["lastChanged"]
                for r in resp[key_id]["rows"]:
                    r["id"] = int(key_id)
                    r["rowid"] = rowid
                    r["employeeLastChanged"] = employeeLastChanged
                    self.logger.info(r)
                    rows.append(r)
                    rowid += 1

        yield from rows


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
            list_of_fields.append(th.Property(field, th.StringType))
        return th.PropertiesList(*list_of_fields).to_dict()

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
        return {"format": "JSON"}

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
