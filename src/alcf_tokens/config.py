from dataclasses import dataclass
from pathlib import Path

from globus_sdk.scopes import TransferScopes

APP_NAME = "alcf_tokens"

AUTH_CLIENT_ID = "7f3e61f5-e0de-4e8f-9150-0a62c65dda63"

TOKENS_PATH = Path.home() / f".globus/app/{AUTH_CLIENT_ID}/{APP_NAME}/tokens.json"

TRANSFER_RESOURCE_SERVER = TransferScopes.resource_server

COLLECTION_ALIASES: dict[str, str] = {
    "eagle": "05d2c76a-e867-4f67-aa57-76edeb0beda0:data_access",
}


@dataclass
class ServiceConfig:
    resource_server: str
    scope: str
    description: str
    documentation_url: str
    session_policy: str | None = None


SERVICES: dict[str, ServiceConfig] = {
    "inference": ServiceConfig(
        resource_server="681c10cc-f684-4540-bcd7-0b4df3bc26ef",
        scope="https://auth.globus.org/scopes/681c10cc-f684-4540-bcd7-0b4df3bc26ef/action_all",
        session_policy="83732ff2-9c42-4548-b5ce-17e498c84f6a",
        description="ALCF Inference Service",
        documentation_url="https://docs.alcf.anl.gov/services/inference-endpoints/",
    ),
    "iri": ServiceConfig(
        resource_server="6be511f6-a071-471f-9bc0-02a0d0836723",
        scope="https://auth.globus.org/scopes/6be511f6-a071-471f-9bc0-02a0d0836723/filesystem",
        session_policy="a128e981-c9a5-417a-97ab-8571c9831bff",
        description="ALCF Integrated Research Infrastructure (IRI) API",
        documentation_url="https://docs.alcf.anl.gov/services/iri-api/",
    ),
    "globus-compute": ServiceConfig(
        resource_server="funcx_service",
        scope="https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all",
        session_policy=None,
        description="Globus Compute",
        documentation_url="https://www.globus.org/compute",
    ),
    "globus-transfer": ServiceConfig(
        resource_server=TRANSFER_RESOURCE_SERVER,
        scope=TransferScopes.all,
        session_policy=None,
        description="Globus Transfer",
        documentation_url="https://www.globus.org/data-transfer",
    ),
}

SCOPE_RESOURCE_SERVERS: dict[str, str] = {
    name: svc.resource_server for name, svc in SERVICES.items()
}

TEST_ENDPOINTS: dict[str, tuple[str, int] | None] = {
    "inference": ("https://inference-api.alcf.anl.gov/resource_server/whoami", 200),
    "iri": ("https://api.alcf.anl.gov/api/v1/task/not-a-real-task", 404),
    "globus-compute": None,
}
