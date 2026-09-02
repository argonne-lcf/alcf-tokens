from dataclasses import dataclass
from pathlib import Path
from typing import Any

import globus_sdk
import globus_sdk.gare
from globus_sdk.authorizers import GlobusAuthorizer

from .globus_transfer_utils import add_transfer_scope, TRANSFER_RESOURCE_SERVER, TRANSFER_SCOPE_ALL


class AuthError(Exception):
    pass


# Globus UserApp name
APP_NAME = "alcf_tokens"

# Public native app client registered with Globus
AUTH_CLIENT_ID = "7f3e61f5-e0de-4e8f-9150-0a62c65dda63"

# Path to tokens.json file where all the tokens are stored
TOKENS_PATH = Path.home() / f".globus/app/{AUTH_CLIENT_ID}/{APP_NAME}/tokens.json"


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
        scope=TRANSFER_SCOPE_ALL,
        session_policy=None,
        description="Globus Transfer",
        documentation_url="https://www.globus.org/data-transfer",
    ),
}

SCOPE_RESOURCE_SERVERS: dict[str, str] = {
    name: svc.resource_server for name, svc in SERVICES.items()
}


class DomainBasedErrorHandler:
    def __call__(self, app: globus_sdk.GlobusApp, error: Exception) -> None:
        app.login()


def _build_scope_requirements(
    service_name: str | None = None,
    authorize_transfer: list[str] | None = None,
) -> dict[str, Any]:
    if service_name is not None:
        svc = SERVICES[service_name]
        base: dict[str, Any] = {svc.resource_server: [svc.scope]}
    else:
        base = {svc.resource_server: [svc.scope] for svc in SERVICES.values()}

    if authorize_transfer:
        base = add_transfer_scope(base, authorize_transfer=authorize_transfer)

    return base


def build_user_app(
    service_name: str | None = None,
    authorize_transfer: list[str] | None = None,
) -> globus_sdk.UserApp:
    return globus_sdk.UserApp(
        APP_NAME,
        client_id=AUTH_CLIENT_ID,
        scope_requirements=_build_scope_requirements(service_name, authorize_transfer),
        config=globus_sdk.GlobusAppConfig(
            request_refresh_tokens=True,
            token_validation_error_handler=DomainBasedErrorHandler(),
        ),
    )


def _make_auth_params(service_name: str | None) -> globus_sdk.gare.GlobusAuthorizationParameters:
    if service_name is not None:
        policy = SERVICES[service_name].session_policy
        if policy:
            return globus_sdk.gare.GlobusAuthorizationParameters(
                session_required_policies=[policy]
            )
    return globus_sdk.gare.GlobusAuthorizationParameters()


def login(
    service_name: str | None = None,
    authorize_transfer: list[str] | None = None,
) -> None:
    build_user_app(service_name, authorize_transfer).login(
        auth_params=_make_auth_params(service_name), force=True
    )


def get_authorizer(resource_server: str) -> GlobusAuthorizer:
    app = build_user_app(service_name=None)
    return app.get_authorizer(resource_server)


def get_access_token(name: str) -> str:
    if name not in SERVICES:
        valid = ", ".join(sorted(SERVICES))
        raise AuthError(f"Unknown token name '{name}'. Valid names: {valid}")

    if not TOKENS_PATH.is_file():
        raise AuthError(
            "No tokens found. "
            f'Please authenticate first by running "alcf-tokens login".'
        )

    resource_server = SERVICES[name].resource_server
    auth = get_authorizer(resource_server)
    auth.ensure_valid_token()
    return auth.access_token
