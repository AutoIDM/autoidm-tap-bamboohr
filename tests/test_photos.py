import pytest
import requests
from singer_sdk.exceptions import RetriableAPIError

from tap_bamboohr.streams import Photos
from tap_bamboohr.tap import TapBambooHR


def make_stream() -> Photos:
    tap = TapBambooHR(
        config={
            "auth_token": "token",
            "subdomain": "example",
            "field_mismatch": "ignore",
            "photo_size": "large",
        }
    )
    return Photos(tap=tap)


def make_response(
    *,
    status_code: int = 200,
    content: bytes,
    content_type: str = "image/jpeg",
    reason: str = "OK",
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    response.headers["Content-Type"] = content_type
    response.reason = reason
    response.url = (
        "https://api.bamboohr.com/api/gateway.php/example/v1/employees/123/photo/large"
    )
    return response


def test_validate_response_accepts_jpeg() -> None:
    stream = make_stream()
    response = make_response(content=b"\xff\xd8\xff\xe0fake-jpeg")

    stream.validate_response(response)


def test_validate_response_accepts_png() -> None:
    stream = make_stream()
    response = make_response(
        content=b"\x89PNG\r\n\x1a\nfake-png",
        content_type="image/png",
    )

    stream.validate_response(response)


def test_validate_response_retries_xml_error_payload() -> None:
    stream = make_stream()
    response = make_response(
        content=(
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<Error><Code>InvalidKey</Code></Error>"
        ),
        content_type="application/xml",
    )

    with pytest.raises(RetriableAPIError):
        stream.validate_response(response)


def test_validate_response_raises_no_photo_found_on_404() -> None:
    stream = make_stream()
    response = make_response(
        status_code=404,
        content=b"",
        content_type="application/json",
        reason="Not Found",
    )

    with pytest.raises(stream.NoPhotoFound):
        stream.validate_response(response)
