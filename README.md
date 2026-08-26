# ALCF Client
Centralized ALCF CLI tool to generate and retrieve Globus access tokens for the following services:

| Service | service-name |
|---|---|
| [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/) | `inference` |
| [ALCF IRI API](https://docs.alcf.anl.gov/services/iri-api/) | `iri` |
| [Globus Compute](https://www.globus.org/compute) | `globus-compute` |


## Installation

### uv (recommended)

We recommend using `alcf-client` as a standalone tool with [uv](https://docs.astral.sh/uv/getting-started/installation/), which sidesteps the need to manually create a virtual environment.

```bash
uv tool install git+https://github.com/argonne-lcf/alcf-client
alcf-client auth --help

# To uninstall the tool:
uv tool uninstall alcf-client
```

To invoke the tool as a one-liner without a persistent tool installation, we recommend `uvx`:

```bash
uvx git+https://github.com/argonne-lcf/alcf-client auth --help
```

To install the tool into a virtual environment that you manage yourself: 

```bash
uv venv .venv
source .venv/bin/activate
uv pip install git+https://github.com/argonne-lcf/alcf-client
```

### pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

### conda

```bash
conda create -n alcf-client python=3.12
conda activate alcf-client
pip install .
```

Once installed, `alcf-client` is available in the active environment:
```bash
alcf-client --help
```


## Usage

### Authentication

Log in once to obtain tokens for all services:
```bash
alcf-client auth login
```

Re-authenticate for a specific service only:
```bash
alcf-client auth login <service-name>
```

### Retrieve a token

```bash
alcf-client auth get-token <service-name>
```

### Test a token

```bash
alcf-client auth test-token <service-name>
```

Output: `{"ready": true, "error": null}` on success.

### Clear stored tokens

```bash
alcf-client auth clear-tokens
```
