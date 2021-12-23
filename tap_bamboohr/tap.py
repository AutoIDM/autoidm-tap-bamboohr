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
    CustomReport,
]


class TapBambooHR(Tap):
    """BambooHR tap class."""

    name = "tap-bamboohr"
    config_jsonschema = th.PropertiesList(
        th.Property("auth_token", th.StringType, required=True),
        th.Property("subdomain", th.StringType, required=True),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


# CLI Execution:

cli = TapBambooHR.cli
