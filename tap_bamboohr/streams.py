"""Stream class for tap-bamboohr."""

import requests

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIAuthenticatorBase, SimpleAuthenticator, OAuthAuthenticator, OAuthJWTAuthenticator
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

SCHEMAS_DIR = Path("./schemas")




class TapBambooHRStream(RESTStream):
    """BambooHR stream class."""

    url_base = "https://api.mysample.com"

    def get_url_params(self, partition: Optional[dict]) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params = {}
        starting_datetime = self.get_starting_datetime(partition)
        if starting_datetime:
            params.update({"updated": starting_datetime})
        return params



    @property
    def authenticator(self) -> APIAuthenticatorBase:
        http_headers = {"Private-Token": self.config.get("auth_token")}
        if self.config.get("user_agent"):
            http_headers["User-Agent"] = self.config.get("user_agent")
        return SimpleAuthenticator(stream=self, http_headers=http_headers)




# TODO: - Override `StreamA` and `StreamB` with your own stream definition.
#       - Copy-paste as many times as needed to create multiple stream types.
class StreamA(TapBambooHRStream):
    stream_name = "users"
    path = "/users"
    primary_keys = ["id"]
    replication_key = None
    schema = PropertiesList(
        StringType("name"),
        StringType("id"),
        IntegerType("age"),
        StringType("email"),
        StringType("street"),
        StringType("city"),
        StringType("state"),
        StringType("zip"),
    ).to_dict()


class StreamB(TapBambooHRStream):
    stream_name = "groups"
    path = "/groups"
    primary_keys = ["id"]
    replication_key = "modified"
    schema = PropertiesList(
        StringType("name"),
        StringType("id"),
        DateTimeType("modified"),
    ).to_dict()


