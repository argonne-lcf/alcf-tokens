# ALCF Client
Centralized ALCF CLI tool to generate and retrieve Globus access tokens for the following services:

- [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/)
- [ALCF IRI API](https://docs.alcf.anl.gov/services/iri-api/)
- [Globus Compute](https://www.globus.org/compute)


## Installation

### uv

```bash
uv venv .venv
source .venv/bin/activate
uv pip install .
```

### conda

```bash
conda create -n alcf-client python=3.12
conda activate alcf-client
pip install .
```

### venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

> **Note:** On Windows, activate with `.venv\Scripts\activate` instead.

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
alcf-client auth login inference
alcf-client auth login iri
alcf-client auth login globus-compute
```

### Retrieve a token

```bash
alcf-client auth get-token inference
alcf-client auth get-token iri
alcf-client auth get-token globus-compute
```

### Test a token

```bash
alcf-client auth test-token inference
alcf-client auth test-token iri
```

Output: `{"ready": true, "error": null}` on success.

### Clear stored tokens

```bash
alcf-client auth clear-tokens
```
