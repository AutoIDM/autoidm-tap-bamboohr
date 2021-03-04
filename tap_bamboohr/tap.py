"""BambooHR tap class."""

from pathlib import Path
from typing import List
import logging
import click
from singer_sdk import Tap, Stream
from singer_sdk.helpers.typing import (
    ArrayType,
    BooleanType,
    ComplexType,
    DateTimeType,
    PropertiesList,
    StringType,
)

from tap_bamboohr.streams import (
    Employees,
)

PLUGIN_NAME = "tap-bamboohr"

STREAM_TYPES = [
  Employees,
]

class TapBambooHR(Tap):
    """BambooHR tap class."""

    name = "tap-bamboohr"
    config_jsonschema = PropertiesList(
        StringType("auth_token", required=True),
        StringType("subdomain", required=True),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]

# CLI Execution:

cli = TapBambooHR.cli
