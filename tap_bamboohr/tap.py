"""BambooHR tap class."""

from pathlib import Path
from typing import List
import click
from singer_sdk import Tap, Stream
from singer_sdk.helpers.typing import (
    ArrayType,
    BooleanType,
    ComplexType,
    DateTimeType,
    IntegerType,
    NumberType,
    PropertiesList,
    StringType,
)

# TODO: Import your custom stream types here:
from tap_bamboohr.streams import (
    TapBambooHRStream,
    StreamA,
    StreamB,
)

PLUGIN_NAME = "tap-bamboohr"

# TODO: Compile a list of custom stream types here
#       OR rewrite discover_streams() below with your custom logic.
STREAM_TYPES = [
    StreamA,
    StreamB,
]

class TapBambooHR(Tap):
    """BambooHR tap class."""

    name = "tap-bamboohr"
    config_jsonschema = PropertiesList(
        StringType("auth_token", required=True),
        ArrayType("project_ids", StringType, required=True),
        DateTimeType("start_date"),
        StringType("api_url"),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]

# CLI Execution:

cli = TapBambooHR.cli
