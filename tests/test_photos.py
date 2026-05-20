"""Tests for the Photos stream.

The endpoint returns raw image bytes by default and a
{mimeType, fileBase64} JSON envelope when Accept: application/json is sent.
The stream handles both and rejects anything else.
"""
from __future__ import annotations

import base64
import json

import pytest
import requests
from singer_sdk.exceptions import RetriableAPIError

from tap_bamboohr.streams import Photos
from tap_bamboohr.tap import TapBambooHR


PHOTO_URL = (
    "https://api.bamboohr.com/api/gateway.php/example/v1/employees/123/photo/large"
)
RAW_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01fake-jpeg-bytes"
RAW_PNG = b"\x89PNG\r\n\x1a\nfake-png-bytes"


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
    response.url = PHOTO_URL
    return response


# ---------- validate_response ------------------------------------------------


def test_validate_response_accepts_raw_jpeg() -> None:
    stream = make_stream()
    stream.validate_response(make_response(content=RAW_JPEG))


def test_validate_response_accepts_raw_png() -> None:
    stream = make_stream()
    stream.validate_response(
        make_response(content=RAW_PNG, content_type="image/png")
    )


def test_validate_response_accepts_json_envelope() -> None:
    stream = make_stream()
    envelope = {
        "mimeType": "image/jpeg",
        "fileBase64": base64.b64encode(RAW_JPEG).decode("ascii"),
    }
    response = make_response(
        content=json.dumps(envelope).encode("utf-8"),
        content_type="application/json",
    )
    stream.validate_response(response)


def test_validate_response_rejects_xml_error_payload() -> None:
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


def test_validate_response_rejects_html_error_page() -> None:
    stream = make_stream()
    response = make_response(
        content=b"<!doctype html><html><body>Maintenance</body></html>",
        content_type="text/html",
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


# ---------- parse_response ---------------------------------------------------


def test_parse_response_raw_bytes_yields_base64() -> None:
    stream = make_stream()
    records = list(stream.parse_response(make_response(content=RAW_JPEG)))
    assert len(records) == 1
    assert records[0]["photo"] == base64.b64encode(RAW_JPEG).decode("ascii")


def test_parse_response_json_envelope_yields_inner_filebase64() -> None:
    stream = make_stream()
    inner_b64 = base64.b64encode(RAW_JPEG).decode("ascii")
    envelope = {"mimeType": "image/jpeg", "fileBase64": inner_b64}
    response = make_response(
        content=json.dumps(envelope).encode("utf-8"),
        content_type="application/json",
    )
    records = list(stream.parse_response(response))
    assert len(records) == 1
    # The yielded value must decode back to the raw image, not the envelope.
    assert base64.b64decode(records[0]["photo"]) == RAW_JPEG


def test_parse_response_png_envelope_round_trip() -> None:
    stream = make_stream()
    inner_b64 = base64.b64encode(RAW_PNG).decode("ascii")
    envelope = {"mimeType": "image/png", "fileBase64": inner_b64}
    response = make_response(
        content=json.dumps(envelope).encode("utf-8"),
        content_type="application/json",
    )
    records = list(stream.parse_response(response))
    assert base64.b64decode(records[0]["photo"]) == RAW_PNG


def test_parse_response_malformed_json_falls_back_to_raw_encoding() -> None:
    # Content that starts with `{` but is not valid JSON must not be unwrapped.
    # validate_response rejects it on a real request; parse_response must still
    # return a deterministic value rather than raise.
    stream = make_stream()
    payload = b'{"not-json'
    records = list(stream.parse_response(make_response(content=payload)))
    assert records[0]["photo"] == base64.b64encode(payload).decode("ascii")


def test_parse_response_json_without_filebase64_treated_as_non_envelope() -> None:
    stream = make_stream()
    payload = json.dumps({"mimeType": "image/jpeg"}).encode("utf-8")
    records = list(stream.parse_response(make_response(content=payload)))
    assert records[0]["photo"] == base64.b64encode(payload).decode("ascii")


# ---------- Accept header ----------------------------------------------------


def test_http_headers_request_binary_image_response() -> None:
    stream = make_stream()
    assert stream.http_headers["Accept"] == "image/*"


# ---------- envelope helper --------------------------------------------------


def test_try_parse_envelope_returns_none_for_raw_image() -> None:
    stream = make_stream()
    assert stream._try_parse_envelope(make_response(content=RAW_JPEG)) is None


def test_try_parse_envelope_returns_none_for_json_missing_filebase64() -> None:
    stream = make_stream()
    response = make_response(
        content=json.dumps({"mimeType": "image/jpeg"}).encode("utf-8"),
        content_type="application/json",
    )
    assert stream._try_parse_envelope(response) is None


def test_try_parse_envelope_returns_envelope_dict_when_valid() -> None:
    stream = make_stream()
    inner_b64 = base64.b64encode(RAW_JPEG).decode("ascii")
    response = make_response(
        content=json.dumps(
            {"mimeType": "image/jpeg", "fileBase64": inner_b64}
        ).encode("utf-8"),
        content_type="application/json",
    )
    envelope = stream._try_parse_envelope(response)
    assert envelope == {"mimeType": "image/jpeg", "fileBase64": inner_b64}
