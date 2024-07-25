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
| field_mismatch      | True     | fail    | Either `fail` or `ignore`. Determines behavior when fields returned by API don't match fields specified in tap config. |
| photo_size          | True     | original | Size of photos to return from the photos stream. Pixel size information can be found in the [docs](https://documentation.bamboohr.com/reference/get-employee-photo-1) |
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

To select fields other than the default a custom report, simply update `meltano.yml` with the desired fields. Note that this sometimes requires the primary key for the custom report to be manually overridden, such as when multiple entries for the same user can be returned.

For example, to sync all Offboarding Tasks:

```yml
    config:
      custom_reports:
      - name: offboarding_tasks
        fields:
        - id
        - '4140'
        - '4142'
    metadata:
      "offboarding_tasks":
        "key_properties": []
```

### Known API Issues

Offboarding task due dates (field 4142) has off-by-one dates. The BambooHR API returns dates as 1 day before the date displayed in the UI. For example, if the date displayed in the UI for a task is "Jun 23, 2024", that task will appear in the API as "2024-06-22".

### Time Off and Holidays

To get full out-of-office information, both the `time_off_requests` and `whos_out` streams are required. Only `time_off_requests` shows information on the category (PTO, Bereavement, Floating Holiday) of request, and only `whos_out` shows holidays.

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
cd tap-bamboohr
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano invoke tap-bamboohr --version
# OR run a test `elt` pipeline:
meltano elt tap-bamboohr target-jsonl
```

### SDK

Built with the [Meltano SDK](https://sdk.meltano.com) for Singer Taps and Targets.
