# ALCF Tokens
Centralized ALCF CLI tool to generate and retrieve Globus access tokens for the following services:

| Service | service-name |
|---|---|
| [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/) | `inference` |
| [ALCF IRI API](https://docs.alcf.anl.gov/services/iri-api/) | `iri` |
| [Globus Compute](https://www.globus.org/compute) | `globus-compute` |
| [Globus Transfer](https://www.globus.org/data-transfer) | `globus-transfer` |

## 1. Prerequisites

- Python >= 3.10

## 2. Installation

### Pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```
If you do not see `alcf-tokens`, try to deactivate and reactivate your environment.

### Conda

```bash
conda create -n alcf-tokens python=3.12 -y
conda activate alcf-tokens
pip install .
```

### Uv

We recommend using `alcf-tokens` as a standalone tool with [uv](https://docs.astral.sh/uv/getting-started/installation/), which sidesteps the need to manually create a virtual environment.

```bash
uv tool install git+https://github.com/argonne-lcf/alcf-tokens
alcf-tokens --help

# To uninstall the tool:
uv tool uninstall alcf-tokens
```

To invoke the tool as a one-liner without a persistent tool installation, we recommend `uvx`:

```bash
uvx git+https://github.com/argonne-lcf/alcf-tokens --help
```

To install the tool into a virtual environment that you manage yourself: 

```bash
uv venv .venv
source .venv/bin/activate
uv pip install git+https://github.com/argonne-lcf/alcf-tokens
```

## 3. Usage

### Test installation

Once installed, you should be able to access `alcf-tokens` from your active environment:
```bash
alcf-tokens --help
```

### Authentication

Log in once to obtain tokens for all services:
```bash
alcf-tokens login
```

Re-authenticate for a specific service only:
```bash
alcf-tokens login <service-name>
```

### Globus Transfer token

To also authorize Globus Transfer against one of your own collections, pass its UUID with `--authorize-transfer`. Repeat the flag to authorize multiple collections:
```bash
alcf-tokens login --authorize-transfer <collection-uuid>
alcf-tokens login --authorize-transfer <uuid-1> --authorize-transfer <uuid-2>
```

If the collection is a Globus Connect Server (GCS) mapped collection that requires a `data_access` scope, append `:data_access` to the UUID:
```bash
alcf-tokens login --authorize-transfer <collection-uuid>:data_access
```

The following collection aliases are supported for convenience:

| Alias | Collection |
|---|---|
| `eagle` | `05d2c76a-e867-4f67-aa57-76edeb0beda0` (ALCF Eagle, with `data_access`) |

```bash
alcf-tokens login --authorize-transfer eagle
```


### Retrieve a token

```bash
alcf-tokens get-token <service-name>
```

### Test a token

```bash
alcf-tokens test-token <service-name>
```

Output: `{"ready": true, "error": null}` on success.

### List available services

```bash
alcf-tokens list-services
```

### Clear stored tokens

```bash
alcf-tokens clear-tokens
```
