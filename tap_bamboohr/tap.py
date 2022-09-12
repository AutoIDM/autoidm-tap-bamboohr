"""BambooHR tap class."""

from typing import List

import requests
from requests.auth import HTTPBasicAuth
from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_bamboohr.streams import CustomReport, Employees, TableStream

STREAM_TYPES = [
    Employees,
]


class TapBambooHR(Tap):
    """BambooHR tap class."""

    name = "tap-bamboohr"
    config_jsonschema = th.PropertiesList(
        th.Property(
            "auth_token",
            th.StringType,
            required=True,
            description="Token gathered from BambooHR, instructions are [here](https://documentation.bamboohr.com/docs#section-authentication)",
        ),
        th.Property(
            "subdomain",
            th.StringType,
            required=True,
            description="subdomain from BambooHR",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
        ),
        th.Property(
            "custom_reports",
            th.ArrayType(
                th.ObjectType(
                    th.Property("name", th.StringType, required=True),
                    th.Property(
                        "filters",
                        th.ObjectType(
                            th.Property(
                                "lastChanged",
                                th.ObjectType(
                                    th.Property("includeNull", th.StringType),
                                    th.Property("value", th.StringType),
                                ),
                            )
                        ),
                        required=True,
                    ),
                    th.Property("fields", th.ArrayType(th.StringType), required=True),
                )
            ),
            required=False,
            description="CustomReport full body definition, example in meltano.yml, same format as the Body for the POST request [here](https://documentation.bamboohr.com/reference/request-custom-report-1)",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        streams: List[Stream] = [
            stream_class(tap=self) for stream_class in STREAM_TYPES
        ]

        custom_reports = self.config.get("custom_reports")
        if custom_reports:
            for report in custom_reports:
                custom_report = CustomReport(
                    tap=self, name=report["name"], custom_report_config=report
                )
                streams.append(custom_report)

        tables_schema = self.get_meta_tables()
        for table in tables_schema:
            table_stream = TableStream(tap=self, table_schema=table)
            streams.append(table_stream)

        return streams

    def get_meta_tables(self) -> dict:
        get_tables_url = f"https://api.bamboohr.com/api/gateway.php/{self.config['subdomain']}/v1/meta/tables"
        auth = HTTPBasicAuth(self.config["auth_token"], "x")
        headers = {"Accept": "application/json"}
        res = requests.get(get_tables_url, headers=headers, auth=auth)
        if res.status_code == 200:
            return requests.get(get_tables_url, headers=headers, auth=auth).json()
        else:
            self.logger.error(
                f"Could not get list of tables from BambooHR. Check subdomain and auth_token in config. Error: {res.status_code} {res.reason}"
            )
            return {}
