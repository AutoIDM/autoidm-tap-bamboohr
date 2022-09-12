# `tap-bamboohr`
Tap was created by [AutoIDM](https://autoidm.com). Check us out for tap/target creation, maintenace, support, and more!

## Capabilities

* `catalog`
* `state`
* `discover`
* `about`
* `stream-maps`

## Settings
| Setting       | Required | Default | Description |
|:--------------|:--------:|:-------:|:------------|
| auth_token    | True     | None    | Token gathered from BambooHR, instructions are [here](https://documentation.bamboohr.com/docs#section-authentication) |
| subdomain     | True     | None    | subdomain from BambooHR |
| custom_reports| False    | None    | CustomReport full body definition, example in meltano.yml, same format as the Body for the POST request [here](https://documentation.bamboohr.com/reference/request-custom-report-1) |
| start_date    | False    | None    | Start date used in pulling table date. |

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

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the SDK to
develop your own taps and targets.

## Config Guide

### Accepted Config Options

- [ ] `TODO:` Provide a list of config options accepted by the tap.

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
