import logging
from typing import Any

import globus_sdk
import globus_sdk.gare
from globus_sdk.authorizers import GlobusAuthorizer
from globus_sdk.scopes import GCSCollectionScopeBuilder, TransferScopes

from .config import (
    APP_NAME,
    AUTH_CLIENT_ID,
    COLLECTION_ALIASES,
    SERVICES,
    TOKENS_PATH,
    TRANSFER_RESOURCE_SERVER,
)

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


class DomainBasedErrorHandler:
    def __call__(self, app: globus_sdk.GlobusApp, error: Exception) -> None:
        logger.error(f"Encountered error '{error}', initiating login...")
        app.login()


def _resolve_collection(transfer_collection_id: str) -> str:
    return COLLECTION_ALIASES.get(transfer_collection_id, transfer_collection_id)


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
        transfer_scope = TransferScopes.make_mutable("all")
        for raw in authorize_transfer:
            collection_id, *gcs_scopes = _resolve_collection(raw).split(":")
            if "data_access" in gcs_scopes:
                data_access = GCSCollectionScopeBuilder(collection_id).make_mutable(
                    "data_access", optional=True
                )
                transfer_scope.add_dependency(data_access)
                base[collection_id] = [data_access]
        base[TRANSFER_RESOURCE_SERVER] = [transfer_scope]

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
