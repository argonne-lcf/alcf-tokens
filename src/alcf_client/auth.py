import logging
import sys
from pathlib import Path
from typing import Literal

import globus_sdk
import globus_sdk.gare
from globus_sdk.authorizers import GlobusAuthorizer

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


# Globus UserApp name
APP_NAME = "alcf_client"

# Public native app client registered with Globus
AUTH_CLIENT_ID = "7f3e61f5-e0de-4e8f-9150-0a62c65dda63"

TOKENS_PATH = Path.home() / f".globus/app/{AUTH_CLIENT_ID}/{APP_NAME}/tokens.json"

# TODO: Enforce appropriate policy when login to specific service
# Globus authorization parameters to enforce specific identity provider policies
#GA_PARAMS = globus_sdk.gare.GlobusAuthorizationParameters(
#    session_required_policies=["UUID"]
#)
GA_PARAMS = globus_sdk.gare.GlobusAuthorizationParameters()

# ALCF Inference Service
INFERENCE_CLIENT_ID = "681c10cc-f684-4540-bcd7-0b4df3bc26ef"
INFERENCE_SCOPE = f"https://auth.globus.org/scopes/{INFERENCE_CLIENT_ID}/action_all"

# ALCF IRI API
IRI_CLIENT_ID = "6be511f6-a071-471f-9bc0-02a0d0836723"
IRI_SCOPE = f"https://auth.globus.org/scopes/{IRI_CLIENT_ID}/filesystem"

# Globus Compute
COMPUTE_CLIENT_ID = "facd7ccc-c5f4-42aa-916b-a0e270e2c2a9"
COMPUTE_SCOPE = "https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all"

# Mapping: friendly name -> resource server ID
SCOPE_RESOURCE_SERVERS: dict[str, str] = {
    "inference": INFERENCE_CLIENT_ID,
    "iri": IRI_CLIENT_ID,
    "globus-compute": COMPUTE_CLIENT_ID,
}

TokenName = Literal["inference", "iri"]


class DomainBasedErrorHandler:
    def __call__(self, app: globus_sdk.GlobusApp, error: Exception) -> None:
        logger.error(f"Encountered error '{error}', initiating login...")
        app.login(auth_params=GA_PARAMS)


def _build_scope_requirements() -> dict[str, list[str]]:
    return {
        INFERENCE_CLIENT_ID: [INFERENCE_SCOPE],
        IRI_CLIENT_ID: [IRI_SCOPE],
        COMPUTE_CLIENT_ID: [COMPUTE_SCOPE],
    }


def build_user_app() -> globus_sdk.UserApp:
    return globus_sdk.UserApp(
        APP_NAME,
        client_id=AUTH_CLIENT_ID,
        scope_requirements=_build_scope_requirements(),
        config=globus_sdk.GlobusAppConfig(
            request_refresh_tokens=True,
            token_validation_error_handler=DomainBasedErrorHandler(),
        ),
    )


def login() -> None:
    app = build_user_app()
    app.login(auth_params=GA_PARAMS)


def get_authorizer(resource_server: str) -> GlobusAuthorizer:
    app = build_user_app()
    return app.get_authorizer(resource_server)


def get_access_token(name: str) -> str:
    if name not in SCOPE_RESOURCE_SERVERS:
        valid = ", ".join(sorted(SCOPE_RESOURCE_SERVERS))
        raise AuthError(f"Unknown token name '{name}'. Valid names: {valid}")

    if not TOKENS_PATH.is_file():
        raise AuthError(
            "No tokens found. "
            f'Please authenticate first by running "{sys.argv[0]} login".'
        )

    resource_server = SCOPE_RESOURCE_SERVERS[name]
    auth = get_authorizer(resource_server)
    auth.ensure_valid_token()  # type: ignore[attr-defined]
    return auth.access_token  # type: ignore[attr-defined]
