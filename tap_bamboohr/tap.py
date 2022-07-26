"""BambooHR tap class."""

from pathlib import Path
from typing import List
import logging
import click
from singer_sdk import Tap, Stream
from singer_sdk import typing as th

from tap_bamboohr.streams import (
    Employees,
    CustomReport,
)

PLUGIN_NAME = "tap-bamboohr"

STREAM_TYPES = [
    Employees,
]


class TapBambooHR(Tap):
    """BambooHR tap class."""

    name = "tap-bamboohr"
    config_jsonschema = th.PropertiesList(
            th.Property("auth_token", th.StringType, required=True, description="Token gathered from BambooHR, instructions are [here](https://documentation.bamboohr.com/docs#section-authentication)"),
        th.Property("subdomain", th.StringType, required=True, description="subdomain from BambooHR"),
        th.Property("custom_reports", 
            th.ArrayType(
                th.ObjectType(
                    th.Property("name", th.StringType, required=True),
                    th.Property("filters", 
                        th.ObjectType(
                            th.Property("lastChanged", 
                                th.ObjectType(
                                    th.Property("includeNull", th.StringType),
                                    th.Property("value", th.StringType),
                                )
                            )
                        ), required=True
                    ),
                    th.Property("fields", 
                        th.ArrayType(th.StringType)
                        , required=True)
                    )
                )
            , required=False, description="CustomReport full body definition, example in meltano.yml, same format as the Body for the POST request [here](https://documentation.bamboohr.com/reference/request-custom-report-1)"),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        streams =  [stream_class(tap=self) for stream_class in STREAM_TYPES]
        custom_reports = self.config.get("custom_reports") 
        if (custom_reports):
            for report in self.config.get("custom_reports"):
                custom_report = CustomReport(tap=self, name=report["name"], custom_report_config=report)
                streams.append(custom_report)
        return streams


# CLI Execution:

cli = TapBambooHR.cli
