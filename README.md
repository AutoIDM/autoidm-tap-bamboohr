# `tap-bamboohr`
Tap was created by [AutoIDM](https://autoidm.com). Check us out for tap/target creation, maintenace, support, and more!

## Capabilities

* `catalog`
* `state`
* `discover`
* `about`
* `stream-maps`

## Settings

| Setting   | Required | Default | Description |
|:----------|:--------:|:-------:|:------------|
| auth_token| True     | None    |             |
| subdomain | True     | None    |             |

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
