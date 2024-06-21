"""BambooHR tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_bamboohr.streams import (
    CustomReport,
    Photos,
    PhotosUsers,
    Employees,
    EmploymentHistoryStatus,
    JobInfo,
    JobTitles,
    LocationsList,
    Divisions,
    Departments,
    EmploymentStatuses,
    LocationsDetail,
)

PLUGIN_NAME = "tap-bamboohr"

STREAM_TYPES = [  # CustomReport has special handing below
    Photos,
    PhotosUsers,
    Employees,
    EmploymentHistoryStatus,
    JobInfo,
    JobTitles,
    LocationsList,
    Divisions,
    Departments,
    EmploymentStatuses,
    LocationsDetail,
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
            "field_mismatch",
            th.StringType,
            allowed_values=["fail", "ignore"],
            required=True,
            default="fail",
            description=(
                "Either `fail` or `ignore`. Determines behavior when fields returned "
                "by API don't match fields specified in tap config.",
            ),
        ),
        th.Property(
            "photo_size",
            th.StringType,
            allowed_values=["original", "large", "medium", "small", "xs", "tiny"],
            required=True,
            default="original",
            description=(
                "Size of photos to return from the photos stream. Pixel size "
                "information can be found in the [docs](https://documentation.bamboohr.com/reference/get-employee-photo-1)"
            ),
        ),
        th.Property(
            "custom_reports",
            th.ArrayType(
                th.ObjectType(
                    th.Property("name", th.StringType),
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
                    ),
                    th.Property(
                        "fields",
                        th.ArrayType(th.StringType),
                        default=[
                            "department",
                            "division",
                            "eeo",
                            "employeeNumber",
                            "employmentHistoryStatus",
                            "employeeStatusDate",
                            "firstName",
                            "gender",
                            "hireDate",
                            "homeEmail",
                            "homePhone",
                            "jobTitle",
                            "lastName",
                            "linkedIn",
                            "location",
                            "mobilePhone",
                            "originalHireDate",
                            "payType",
                            "preferredName",
                            "status",
                            "workEmail",
                            "workPhoneExtension",
                            "workPhone",
                            "displayName",
                            "supervisorEId",
                            "address1",
                            "address2",
                            "city",
                            "state",
                            "stateCode",
                            "country",
                            "zipcode",
                        ],
                    ),
                )
            ),
            required=False,
            description=(
                "CustomReport full body definition, example in meltano.yml, same "
                "format as the Body for the POST request [here](https://documentation.bamboohr.com/reference/request-custom-report-1)"
            ),
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        streams = [stream_class(tap=self) for stream_class in STREAM_TYPES]
        for report_number, report in enumerate(self.config.get("custom_reports", [])):
            streams.append(
                CustomReport(
                    tap=self,
                    name=report.get("name", f"Custom Report #{report_number+1}"),
                    custom_report_config=report,
                )
            )
        return streams


# CLI Execution:

cli = TapBambooHR.cli
