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

## 2. Installation Options

### Python environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install alcf-tokens
```

### Conda environment
```bash
conda create -n alcf-tokens python=3.12 -y
conda activate alcf-tokens
pip install alcf-tokens
```

### Uv
```bash
uv venv .venv
source .venv/bin/activate
uv pip install alcf-tokens
```

To invoke the tool as a one-liner without the need to manually create a virtual environment, we recommend `uvx`:

```bash
uvx alcf-tokens --help
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

### Authorizing collections

To work with data on a Globus collection, name the collection at login with
`--authorize-transfer`. Repeat the flag to authorize several collections in a
single login:
```bash
alcf-tokens login --authorize-transfer <collection-uuid>
alcf-tokens login --authorize-transfer <uuid-1> --authorize-transfer <uuid-2>
```

Each entry is a collection UUID (or alias) followed by the scopes you need on
that collection. Both scopes are optional, and may be combined in either order:

| Suffix | When you need it |
|---|---|
| `:data_access` | The collection is a Globus Connect Server (GCS) *mapped* collection that requires a `data_access` scope for Transfer to read or write it on your behalf. |
| `:https` | You want to read or write files on the collection **directly over HTTPS**, rather than as a Transfer task between two collections. |

```bash
alcf-tokens login --authorize-transfer <collection-uuid>:data_access
alcf-tokens login --authorize-transfer <collection-uuid>:https
alcf-tokens login --authorize-transfer <collection-uuid>:data_access:https
```

Be sure to include every collection you need authorized in one command.
A transfer moves data *between* two collections, so authorize both of them in
the same login -- for example, staging data from your ALCF home directory to a
guest collection you upload to over HTTPS:

```bash
alcf-tokens login \
  --authorize-transfer home \
  --authorize-transfer <guest-collection-uuid>:https
```

The following collection aliases are supported for convenience:

| Alias | Collection |
|---|---|
| `home` | `9032dd3a-e841-4687-a163-2720da731b5b` (ALCF Home, with `data_access`) |
| `eagle` | `05d2c76a-e867-4f67-aa57-76edeb0beda0` (ALCF Eagle, with `data_access`) |
| `flare` | `f39a7a0f-5bfc-46ce-9615-ba9f8592814f` (ALCF Flare, with `data_access`) |

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

## 4. Incorporating your tokens in services

### Globus Compute

```python
from globus_sdk import AccessTokenAuthorizer
from globus_compute_sdk import Client

COMPUTE_TOKEN = "<your-globus-compute-token>"

auth = AccessTokenAuthorizer(COMPUTE_TOKEN)
gcc = Client(authorizer=auth)
```

See [ALCF docs](https://docs.alcf.anl.gov/services/globus-compute/) for more details.

### Globus Transfer

```python
from globus_sdk import AccessTokenAuthorizer, TransferClient

TRANSFER_TOKEN = "<your-globus-transfer-token>"

auth = AccessTokenAuthorizer(TRANSFER_TOKEN)
tc = TransferClient(authorizer=auth)
```

See [Globus docs](https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html) for more details.

### ALCF Inference Service

Use `alcf-tokens get-token inference` to print your token, and incorporate it into your request headers. See [ALCF docs](https://docs.alcf.anl.gov/services/inference-endpoints/) for more details.

### ALCF IRI API

Use `alcf-tokens get-token iri` to print your token, and incorporate it into your request headers. See [ALCF docs](https://docs.alcf.anl.gov/services/iri-api/) for more details.

### Automatically refreshing access tokens

Rather than pasting tokens, Python callers can read the stored tokens directly.
`alcf_tokens.auth` refreshes them as needed and raises `AuthError` when a login
is necessary to proceed.

```python
from alcf_tokens.auth import get_access_token

token = get_access_token("inference")
```

There are Authorizers for the Globus SDK clients too:

```python
from globus_sdk import TransferClient
from alcf_tokens.auth import (
    get_service_authorizer,   # any service in SERVICES, e.g. "inference"
    get_transfer_authorizer,  # the Globus Transfer API
    get_https_authorizer,     # direct HTTPS reads/writes on one collection
)

# Authorized at login with: --authorize-transfer home
tc = TransferClient(authorizer=get_transfer_authorizer(["home"]))

https_auth = get_https_authorizer(COLLECTION)
headers = {"Authorization": str(https_auth.get_authorization_header())}
```

Pass `get_transfer_authorizer` the same collection entries you used at login, so
that a missing consent is reported as such rather than as a Globus API error.


## 5. Standalone shell script (no dependencies)

`alcf-tokens.sh` is a dependency-free alternative to the Python CLI. It is
written in POSIX `sh` and needs only `curl`, `jq`, `awk`, and `openssl`. It
supports the `inference`, `iri`, and `globus-compute` services
(`globus-transfer` is not supported) and mirrors the Python CLI argument
format: `<action> [<service>]`, with the service passed positionally and no
options.

To run it directly from the repository without cloning it first:

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/argonne-lcf/alcf-tokens/main/alcf-tokens.sh)" alcf-tokens.sh login iri
```

```bash
./alcf-tokens.sh list-services                  # list available services
./alcf-tokens.sh login                          # authenticate for all services
./alcf-tokens.sh login iri                      # authenticate for one service only
./alcf-tokens.sh get-token inference
./alcf-tokens.sh test-token inference
./alcf-tokens.sh clear-tokens
```
