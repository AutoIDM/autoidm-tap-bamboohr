# `tap-bamboohr`
Tap was created by [AutoIDM](https://autoidm.com). Check us out for tap/target creation, maintenace, support, and more!

## Capabilities

* `catalog`
* `state`
* `discover`
* `about`
* `stream-maps`

## Settings

| Setting             | Required | Default | Description |
|:--------------------|:--------:|:-------:|:------------|
| auth_token          | True     | None    | Token gathered from BambooHR, instructions are [here](https://documentation.bamboohr.com/docs#section-authentication) |
| subdomain           | True     | None    | subdomain from BambooHR |
| field_mismatch      | True     | fail    | Either `fail` or `ignore`. Determines behavior when fields returned by API don't match the requested fields. |
| custom_reports      | False    | None    | CustomReport full body definition, example in meltano.yml, same format as the Body for the POST request [here](https://documentation.bamboohr.com/reference/request-custom-report-1) |
| stream_maps         | False    | None    | Config object for stream maps capability. For more information check out [Stream Maps](https://sdk.meltano.com/en/latest/stream_maps.html). |
| stream_map_config   | False    | None    | User-defined config values to be used within map expressions. |
| flattening_enabled  | False    | None    | 'True' to enable schema flattening and automatically expand nested properties. |
| flattening_max_depth| False    | None    | The max depth to flatten schemas. |
| batch_config        | False    | None    |             |

A full list of supported settings and capabilities is available by running: `tap-bamboohr --about`


## Getting Started
    ```bash
    pipx install poetry
    poetry install
    ```
    ```bash
    poetry run tap-bamboohr --help
    ```
    ```bash
    poetry run pytest
    ```
## Singer SDK Dev Guide

See the [dev guide](../../docs/dev_guide.md) for more instructions on how to use the Singer SDK to 
develop your own taps and targets.

## Config Guide

### Selecting Additional Fields in a Custom Report

To select additional fields in a custom report, pass in a manually modified catalog using a command like `meltano elt tap-bamboohr target-jsonl --catalog=catalog.json`. The `catalog.json` file should be modified such that the field you want to include is marked as available and selected. For example, to add the `zipcode` field to the set of selected fields, change its breadcrumb to the following:

```json
{
    "breadcrumb": [
        "properties",
        "zipcode"
    ],
    "metadata": {
        "inclusion": "available",
        "selected": true
    }
}
```

Alternatively, to modify the tap and permanently add a field to the default set of selected fields, add its name to `tap_bamboohr/selected_fields.json`. Or, if the field exists but is undocumented or not returned by `/meta/fields`, add its name and data type to `tap_bamboohr/merge_fields.json` to have it be merged into the default catalog (but not necessarily selected by default).

### Source Authentication and Authorization

- [ ] `TODO:` If your tap requires special access on the source system, or any special authentication requirements, provide those here.
This Singer-compliant tap was created using the [Singer SDK](https://gitlab.com/meltano/singer-sdk).

### Testing with [Meltano](https://www.meltano.com)

_**Note:** This tap will work in any Singer environment and does not require Meltano.

Install Meltano (if you haven't already) and any needed plugins:

```bash
# Install meltano
pipx install meltano
# Initialize meltano within this directory
cd tap-clickup
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano invoke tap-clickup --version
# OR run a test `elt` pipeline:
meltano elt tap-clickup target-jsonl
```

### SDK

Built with the [Meltano SDK](https://sdk.meltano.com) for Singer Taps and Targets.
