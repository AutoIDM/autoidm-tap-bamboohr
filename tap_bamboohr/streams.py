"""Stream class for tap-bamboohr."""
from __future__ import annotations

import base64
import copy
import json
import typing as t
from functools import cached_property
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
from singer_sdk import typing
from singer_sdk._singerlib import Schema
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.pagination import SinglePagePaginator
from singer_sdk.streams.rest import RESTStream
from singer_sdk.tap_base import Tap

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
        auth_token = self.config.get("auth_token")
        # Password can be any string; it doesn't matter.
        return BasicAuthenticator(stream=self, username=auth_token, password="foobar")

    @property
    def temporal_fields(self) -> set:
        fields = set()
        for field, properties in self.schema["properties"].items():
            if "format" in properties and properties["format"] in {
                "date",
                "time",
                "date-time",
            }:
                fields.add(field)
        return fields

    @property
    def boolean_fields(self) -> set:
        fields = set()
        for field, properties in self.schema["properties"].items():
            if "boolean" in properties.get("type", []):
                fields.add(field)
        return fields

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        for row in super().parse_response(response):
            row = self.standardize_data(row)
            yield row

    def standardize_data(self, row: dict) -> dict:
        row_copy = copy.deepcopy(row)
        row_copy = self.nullify_temporal_data(row=row_copy)
        row_copy = self.standardize_boolean_data(row=row_copy)
        return row_copy

    def nullify_temporal_data(self, row: dict) -> dict:
        row_copy = copy.deepcopy(row)
        illegal_values = {"", "0000-00-00"}
        for field in row_copy:
            if field in self.temporal_fields and row_copy[field] in illegal_values:
                row_copy[field] = None
        return row_copy

    def standardize_boolean_data(self, row: dict) -> dict:
        row_copy = copy.deepcopy(row)
        for field in row_copy:
            if field in self.boolean_fields:
                if row_copy[field] == "true":
                    row_copy[field] = True
                elif row_copy[field] == "false":
                    row_copy[field] = False
        return row_copy


class Lists(TapBambooHRStream):
    """Not for direct use: should be subclassed."""

    path = "/meta/lists"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "lists.json"


class JobTitles(Lists):
    name = "jobtitles"
    records_jsonpath = "$[?(@.alias=='jobTitle')].options[*]"


class LocationsList(Lists):
    name = "locations"
    records_jsonpath = "$[?(@.alias=='location')].options[*]"


class Divisions(Lists):
    name = "divisions"
    records_jsonpath = "$[?(@.alias=='division')].options[*]"


class Departments(Lists):
    name = "departments"
    records_jsonpath = "$[?(@.alias=='department')].options[*]"


class EmploymentStatuses(Lists):
    name = "employmentstatuses"
    records_jsonpath = "$[?(@.alias=='employmentHistoryStatus')].options[*]"


class Employees(TapBambooHRStream):
    name = "employees"
    path = "/employees/directory"
    primary_keys = ["id"]
    records_jsonpath = "$.employees[*]"
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "directory.json"


class LocationsDetail(TapBambooHRStream):
    name = "locationdetails"
    path = "/applicant_tracking/locations"
    primary_keys = ["id"]
    records_jsonpath = "$[*]"
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "locations.json"


class CustomReport(TapBambooHRStream):
    path = "/reports/custom"
    primary_keys = ["id"]
    records_jsonpath = "$.employees[*]"
    replication_key = None
    rest_method = "POST"

    def __init__(
        self,
        tap: Tap,
        name: str | None = None,
        schema: dict[str, t.Any] | Schema | None = None,
        path: str | None = None,
        custom_report_config: dict = {},
    ) -> None:
        self._custom_report_config = custom_report_config
        super().__init__(name=name, schema=schema, tap=tap, path=path)

    @property
    def schema(self):
        list_of_fields = self.field_list
        list_of_properties = []
        for field in list_of_fields:
            list_of_properties.append(typing.Property(field["name"], field["type"]))
        return typing.PropertiesList(*list_of_properties).to_dict()

    @cached_property
    def field_list(self):
        list_of_field_names = self.custom_report_config.get("fields", [])
        list_of_field_dicts = []
        for field_name in list_of_field_names:
            list_of_field_dicts.append(
                {
                    "name": field_name,
                    "type": self.get_field_type(field_name=field_name),
                }
            )
        return list_of_field_dicts

    def get_field_type(self, field_name: str) -> str:
        """Takes the name of a BambooHR field and finds its JSON data type.

        Canonicalizes a field name, checks if its in the field_types.json file, and if
        so, returns that type. Otherwise, returns string.
        """
        with open(str(Path(__file__).parent / Path("./field_types.json"))) as file:
            return self.bamboohr_type_to_jsonschema_type(
                json.load(file).get(self.canonical_field_name(field_name), "string")
            )

    def canonical_field_name(self, field_name: int | str) -> str:
        """Converts an ambiguous field name into a single unambiguous name.

        Args:
            field_name: The field name to convert. Can be in any of the following
            formats: "name", "123", "123.0", or 123

        Returns:
            An unambiguous name in the format: "name" or "123.0".
        """
        if not isinstance(field_name, (int, str)):
            msg = "Field name cannot be canonicalized because it is not int or str."
            raise TypeError(msg)
        if isinstance(field_name, str):
            try:
                field_name = int(field_name)
            except ValueError:
                return field_name
        if isinstance(field_name, int):
            return format(field_name, ".1f")

    def bamboohr_type_to_jsonschema_type(
        self, bamboohr_type: str
    ) -> typing.JSONTypeHelper:
        """Converts a string representing a BambooHR type to the appropiate JSON type.

        For further information, refer to:
        https://documentation.bamboohr.com/docs/field-types
        but note that some field types remain undocumented and others are inconsistent
        in the formatting of the values they return.

        Args:
            bamboohr_type: A string representing a BambooHR type.

        Returns:
            A JSON type matching the BambooHR type, defaulting to string for most types.
        """
        if bamboohr_type == "bool":
            return typing.BooleanType
        if bamboohr_type == "timestamp":
            return typing.DateTimeType
        if bamboohr_type == "date":
            return typing.DateType
        return typing.StringType

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
        return self.custom_report_config

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        json_response = response.json()

        if self.config["field_mismatch"] == "fail":
            fields_config = set(
                [
                    self.canonical_field_name(field)
                    for field in self.custom_report_config["fields"]
                ]
            )
            fields_returned = set(
                [
                    self.canonical_field_name(field)
                    for field in extract_jsonpath("$.fields[*].id", json_response)
                ]
            )
            matching = fields_config.intersection(fields_returned)
            config_diff = fields_config.difference(fields_returned)
            returned_diff = fields_returned.difference(fields_config)
            if fields_config != fields_returned:
                msg = (
                    f"The fields returned by the API for {self.name} did not match the "
                    "fields selected. The matching fields were: "
                    f"{matching if matching else 'N/A'}. The fields selected for a "
                    "custom report but not returned were: "
                    f"{config_diff if config_diff else 'N/A'}. The fields returned but "
                    "not selected for a custom report were: "
                    f"{returned_diff if returned_diff else 'N/A'}. To suppress this "
                    "error, change the field_mismatch config option to 'ignore'."
                )
                raise RuntimeError(msg)

        for row in extract_jsonpath(self.records_jsonpath, json_response):
            row = self.standardize_data(row)
            yield row

    def get_new_paginator(self) -> SinglePagePaginator:
        return SinglePagePaginator()


class PhotosUsers(TapBambooHRStream):
    name = "photos_users"
    primary_keys = ["id"]
    records_jsonpath = "$.employees[*]"
    replication_key = None
    rest_method = "POST"
    schema_filepath = SCHEMAS_DIR / "photos_users.json"

    # Recommended path for pulling bulk employee data. From the docs: "If you're trying
    # to get employee data in bulk (for all employees), we recommend using the request a
    # custom report API."
    # https://documentation.bamboohr.com/reference/get-employee
    path = "/reports/custom"

    def get_child_context(
        self,
        record: dict,
        context: Optional[dict],  # noqa: ARG002
    ) -> dict:
        """Return a context dictionary for child streams."""
        return {
            "_sdc_id": record["id"],
            "_sdc_isPhotoUploaded": record.get("isPhotoUploaded", False),
        }

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {"format": "JSON"}

    def prepare_request_payload(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Optional[dict]:
        return {
            "name": "photos_users",
            "fields": [
                "id",
                "isPhotoUploaded",
            ],
        }

    def get_new_paginator(self) -> SinglePagePaginator:
        return SinglePagePaginator()


class Photos(TapBambooHRStream):
    name = "photos"
    primary_keys = ["_sdc_id"]
    records_jsonpath = "$[*]"
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "photos.json"
    parent_stream_type = PhotosUsers

    @cached_property
    def path(self):
        photo_size = self.config["photo_size"]
        valid_photo_sizes = ["original", "large", "medium", "small", "xs", "tiny"]
        if photo_size not in valid_photo_sizes:
            raise ValueError(f"Photo size of `{photo_size}` is not valid.")
        return f"/employees/{{_sdc_id}}/photo/{photo_size}"

    def get_records(self, context: dict | None) -> t.Iterable[dict[str, t.Any]]:
        """Override to provide no records if no photo exists.

        Without this, the API fails with a 404.
        """
        try:
            if context.get("_sdc_isPhotoUploaded", False):
                for record in self.request_records(context):
                    transformed_record = self.post_process(record, context)
                if transformed_record is None:
                    # Record filtered out during post_process()
                    continue
                yield transformed_record
            else:
                record = {"photo": None}
                record.update(context)
                yield record
        except self.NoPhotoFound:
            self.logger.info(f"No photo found for employee, skipping {context.get('_sdc_id')}")
            pass

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        yield {"photo": base64.b64encode(response.content).decode("utf-8")}
    
    class NoPhotoFound(Exception):
        pass

    def validate_response(self, response: requests.Response) -> None:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise self.NoPhotoFound()
        super().validate_response(response)


# A more generic tables stream would be better, there is a table metadata api
class EmploymentHistoryStatus(TapBambooHRStream):
    name = "tables_employmentstatus"
    path = "/employees/changed/tables/employmentStatus"
    primary_keys = ["employee_id", "date", "employmentStatus"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "employmentstatus.json"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {
            "since": "2012-01-01T00:00:00Z"
        }  # I want all of the data, 2012 is far enough back and referenced in the API Docs

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
            rows = value.get("rows", [])
            for row in rows:
                row.update({"lastChanged": last_changed})
                row.update({"employee_id": employeeid})
                row = self.standardize_data(row)
                yield row


# A more generic tables stream would be better, there is a table metadata api
class EmployeeAssets(TapBambooHRStream):
    name = "tables_employeeassets"
    path = "/employees/all/tables/employeeAssets"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "employeeassets.json"


class JobInfo(TapBambooHRStream):
    name = "tables_jobinfo"
    path = "/employees/changed/tables/jobInfo"
    primary_keys = ["employee_id", "date", "location"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "jobinfo.json"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {
            "since": "2012-01-01T00:00:00Z"
        }  # I want all of the data, 2012 is far enough back and referenced in the API Docs

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
            rows = value.get("rows", [])
            for row in rows:
                row.update({"lastChanged": last_changed})
                row.update({"employee_id": employeeid})
                row = self.standardize_data(row)
                yield row


class WhosOut(TapBambooHRStream):
    name = "whos_out"
    path = "/time_off/whos_out"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "whos_out.json"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {
            "start": "1900-01-01",
            "end": "2100-12-12"
        }  # We want all of the data; these should be far enough in the future/past


class TimeOffRequests(TapBambooHRStream):
    name = "time_off_requests"
    path = "/time_off/requests"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "time_off_requests.json"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        return {
            "start": "1900-01-01",
            "end": "2100-12-12"
        }  # We want all of the data; these should be far enough in the future/past
