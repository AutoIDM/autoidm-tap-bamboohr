"""Stream class for tap-bamboohr."""

import requests
import base64
import http.client

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIAuthenticatorBase, SimpleAuthenticator, OAuthAuthenticator, OAuthJWTAuthenticator
from singer_sdk.helpers.typing import (
    ArrayType,
    ObjectType,
    BooleanType,
    ComplexType,
    Property,
    DateTimeType,
    NumberType,
    PropertiesList,
    StringType,
)

SCHEMAS_DIR = Path("./schemas")

class TapBambooHRStream(RESTStream):
    """BambooHR stream class."""
    @property
    def url_base(self) -> str: 
      subdomain = self.config.get("subdomain")
      return f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1"

    def get_url_params(self, partition: Optional[dict]) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params = {}
        starting_datetime = self.get_starting_datetime(partition)
        if starting_datetime:
            params.update({"updated": starting_datetime})
        return params

    @property
    def authenticator(self) -> APIAuthenticatorBase:
        http_headers = {}
        auth_token = self.config.get("auth_token")
        basic_auth = f"{auth_token}:nothingtoseehere"
        http_headers["Authorization"] = "Basic " + base64.b64encode(basic_auth.encode("utf-8")).decode('utf-8')
        #Move content-type somewhere else, auth doesn't make sense
        http_headers["Content-Type"] = "application/json"
        http_headers["Accept"] = "application/json"
        if self.config.get("user_agent"):
            http_headers["User-Agent"] = self.config.get("user_agent")
        return SimpleAuthenticator(stream=self, http_headers=http_headers)

    #TODO Try to replace this with a Schema insted of the hard coded employees
    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        resp_json = response.json()
        for row in resp_json.get("employees"):
            yield row

class Employees(TapBambooHRStream):
    name = "employees"
    path = "/employees/directory"
    primary_keys = ["id"]
    replication_key = None
    #Probably going to go with Discovery here as BambooHR offers a field list that can be different per user of BambooHR
    schema = PropertiesList(
              Property("id", StringType),
              Property("displayName", StringType),
              Property("firstName", StringType),
              Property("lastName", StringType),
              Property("gender", StringType),
              Property("jobTitle", StringType),
              Property("workPhone", StringType),
              Property("workPhoneExtension", StringType),
              Property("skypeUsername", StringType),
              Property("preferredName", StringType),
              Property("mobilePhone", StringType),
              Property("workEmail", StringType),
              Property("department", StringType),
              Property("location", StringType),
              Property("division", StringType),
              Property("linkedIn", StringType),
              Property("photoUploaded", BooleanType), 
              Property("photoUrl", StringType),
              Property("canUploadPhoto", NumberType), 
    ).to_dict()
    print(schema)


#class StreamB(TapBambooHRStream):
#    stream_name = "groups"
#    path = "/groups"
#    primary_keys = ["id"]
#    replication_key = "modified"
#    schema = PropertiesList(
#        StringType("name"),
#        StringType("id"),
#        DateTimeType("modified"),
#    ).to_dict()


