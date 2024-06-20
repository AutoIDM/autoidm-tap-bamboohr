"""Stream class for tap-bamboohr."""
from __future__ import annotations

import base64
import json
import typing as t
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
import singer_sdk.helpers._catalog as catalog
from singer_sdk import typing
from singer_sdk._singerlib import Metadata, MetadataMapping, Schema, StreamMetadata
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.helpers.jsonpath import extract_jsonpath
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
            if "format" in properties and properties["format"] in {"date", "time", "date-time"}:
                fields.add(field)
        return fields

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        for row in super().parse_response(response):
            self.nullify_temporal_data(row, self.temporal_fields)
            yield row
        
    def nullify_temporal_data(self, row: dict, temporal_fields: set) -> dict:
        illegal_values = {"", "0000-00-00"}
        for field in row:
            if field in temporal_fields and row[field] in illegal_values:
                row[field] = None
        return row

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
    merge_fields: dict = {}

    def __init__(
        self,
        tap: Tap,
        name: str | None = None,
        schema: dict[str, t.Any] | Schema | None = None,
        path: str | None = None,
        custom_report_config: dict = {},
    ) -> None:
        """This reimplements functionality of RESTStream's init method.

        It also moves the definition of self._requests_session to before the call to its
        superclass, because the Stream class calls schema during it's init method, but
        this class's schema requires _request which requires requests_session which
        requires _requests_session.
        """
        self.name = name
        self._requests_session = requests.Session()
        with open(str(Path(__file__).parent / Path("./merge_fields.json"))) as file:
            self.merge_fields = json.load(file)
        super(RESTStream, self).__init__(name=name, schema=schema, tap=tap)
        self._custom_report_config = custom_report_config
        if path:
            self.path = path
        self._http_headers: dict = {}
        self._compiled_jsonpath = None
        self._next_page_token_compiled_jsonpath = None

    @property
    def schema(self):
        list_of_fields = self.field_list
        list_of_properties = []
        for field in list_of_fields:
            list_of_properties.append(typing.Property(field["name"], field["type"]))
        return typing.PropertiesList(*list_of_properties).to_dict()

    @property
    def metadata(self) -> MetadataMapping:
        """Same as superclass property but marks some fields UNSUPPORTED."""
        if self._metadata is not None:
            return self._metadata

        if self._tap_input_catalog:
            catalog_entry = self._tap_input_catalog.get_stream(self.tap_stream_id)
            if catalog_entry:
                self._metadata = catalog_entry.metadata
                return self._metadata

        self._metadata = MetadataMapping()
        key_properties = self.primary_keys or []
        valid_replication_keys = (
            [self.replication_key] if self.replication_key else None
        )
        root = StreamMetadata(
            table_key_properties=self.primary_keys or [],
            forced_replication_method=self.forced_replication_method,
            valid_replication_keys=valid_replication_keys,
            selected_by_default=self.selected_by_default,
        )

        if self.schema:
            root.inclusion = Metadata.InclusionType.AVAILABLE

            for field_name in self.schema.get("properties", {}):
                if (
                    key_properties
                    and field_name in key_properties
                    or (valid_replication_keys and field_name in valid_replication_keys)
                ):
                    entry = Metadata(inclusion=Metadata.InclusionType.AUTOMATIC)
                elif field_name in self.default_selected_fields:
                    entry = Metadata(inclusion=Metadata.InclusionType.AVAILABLE)
                else:
                    # TODO: Pending https://github.com/meltano/meltano/issues/2511, this
                    # can be reimplemented with inclusion=AVAILABLE and
                    # selected_by_default=False.
                    entry = Metadata(inclusion=Metadata.InclusionType.UNSUPPORTED)

                self._metadata[("properties", field_name)] = entry

        self._metadata[()] = root

        # If there's no input catalog, select all streams
        self._metadata.root.selected = (
            self._tap_input_catalog is None and self.selected_by_default
        )

        return self._metadata

    @cached_property
    def default_selected_fields(self) -> list:
        with open(str(Path(__file__).parent / Path("./selected_fields.json"))) as file:
            return json.load(file)

    @cached_property
    def field_list(self):
        list_of_fields = []

        session = requests.Session()
        session.headers = super().authenticator.auth_headers

        # Decoration adds backoff-handling.
        decorated_request = self.request_decorator(self._request)

        meta_fields = session.prepare_request(
            requests.Request(
                "GET",
                super().url_base + "/meta/fields",
                {"Accept": "application/json"}, # Returns XML by default.
            ),
        )

        result: requests.Response = decorated_request(meta_fields, None)
        result_json = result.json()

        for field in result_json:
            # An alias is ideal since it is both user-friendly and unambiguous. If
            # present it should be used.
            if "alias" in field:
                list_of_fields.append(
                    {
                        "name": self.canonical_field_name(field["alias"]),
                        "type": self.bamboohr_type_to_jsonschema_type(field["type"]),
                    }
                )
            # For fields that don't have an alias, the id could be in any number of
            # formats so it needs to be canonicalized.
            else:
                field_name = self.canonical_field_name(field["id"])
                list_of_fields.append(
                    {
                        "name": field_name,
                        "type": self.bamboohr_type_to_jsonschema_type(field["type"]),
                    }
                )

        # Not all fields are returned by /meta/fields. To be sure we get them all,
        # additional fields are added from: https://documentation.bamboohr.com/docs/list-of-field-names
        for k, v in self.merge_fields.items():
            list_of_fields.append(
                {
                    "name": self.canonical_field_name(k),
                    "type": self.bamboohr_type_to_jsonschema_type(v),
                }
            )
        return list_of_fields

    def canonical_field_name(self, field_name: int | str) -> str:
        """Converts an ambiguous field name into a single unambiguous name.

        Args:
            field_name: The field name to convert. Can be in any of the following
            formats: "name", "123", "123.0", or 123

        Returns:
            An unambiguous name in the format: "name" or "123.0".
        """
        if type(field_name) is str:
            try:
                field_name = int(field_name)
            except ValueError:
                return field_name
        if type(field_name) is int:
            return format(field_name, ".1f")
        msg="Field name cannot be canonicalized because it is not int or str."
        raise TypeError(msg)

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
        selected_schema = catalog.get_selected_schema(
            stream_name=self.name,
            schema=self.schema,
            mask=self.mask,
            logger=self.logger,
        )
        self._custom_report_config.update(
            {"fields": [i for i in selected_schema["properties"]]}
        )
        return self.custom_report_config

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        json_response = response.json()

        if self.config["field_mismatch"] == "fail":
            fields_config = set([self.canonical_field_name(field) for field in self.custom_report_config["fields"]])
            fields_returned = set([self.canonical_field_name(field) for field in extract_jsonpath("$.fields[*].id", json_response)])
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
            self.nullify_temporal_data(row, self.temporal_fields)
            yield row

class OffboardingTasks(CustomReport):

    name = "offboarding_tasks"

    def __init__(
        self,
        tap: Tap,
        name: str | None = None,
        schema: dict[str, t.Any] | Schema | None = None,
        path: str | None = None,
    ) -> None:
        """This reimplements functionality of RESTStream's init method.

        It also moves the definition of self._requests_session to before the call to its
        superclass, because the Stream class calls schema during it's init method, but
        this class's schema requires _request which requires requests_session which
        requires _requests_session.
        """
        if name:
            self.name = name
        custom_report_config = {"name": self.name}
        super().__init__(
            tap=tap,
            name=self.name,
            schema=schema,
            path=path,
            custom_report_config=custom_report_config,
        )

    @cached_property
    def field_list(self):
        return [
            {
                "name": "id",
                "type": self.bamboohr_type_to_jsonschema_type("int"),
            },
            {
                "name": "4140",  # Tasks: Task name
                "type": self.bamboohr_type_to_jsonschema_type("text"),
            },
            {
                "name": "4142",  # Tasks: Due Date
                "type": self.bamboohr_type_to_jsonschema_type("date")
            },
        ]

    @cached_property
    def default_selected_fields(self) -> list:
        return ["id", "4140", "4142"]
    
    def post_process(self, row: Dict, context: Dict | None = None) -> Dict | None:
        if row["4140"] is None:
            return None
        return row

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
            rows = value.get("rows", [])
            for row in rows:
                row.update({"lastChanged":last_changed})
                row.update({"employee_id":employeeid})
                self.nullify_temporal_data(row, self.temporal_fields)
                yield row

class JobInfo(TapBambooHRStream):
    name = "tables_jobinfo"
    path = "/employees/changed/tables/jobInfo"
    primary_keys = ["employee_id", "date", "location"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "jobinfo.json"

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
            rows = value.get("rows", [])
            for row in rows:
                row.update({"lastChanged":last_changed})
                row.update({"employee_id":employeeid})
                self.nullify_temporal_data(row, self.temporal_fields)
                yield row