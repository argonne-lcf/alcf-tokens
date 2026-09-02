from importlib.metadata import version
from typing import Any

from globus_sdk.scopes import TransferScopes

TRANSFER_RESOURCE_SERVER = TransferScopes.resource_server
TRANSFER_SCOPE_ALL = TransferScopes.all

COLLECTION_ALIASES: dict[str, str] = {
    "eagle": "05d2c76a-e867-4f67-aa57-76edeb0beda0:data_access",
}

globus_sdk_installed = tuple(map(int, version("globus-sdk").split(".")))
sdk_is_above_4_0_0: bool = globus_sdk_installed >= (4, 0, 0)

if sdk_is_above_4_0_0:
    from globus_sdk.scopes import GCSCollectionScopes, TransferScopes
else:
    from globus_sdk.scopes import GCSCollectionScopeBuilder, TransferScopes

print("IS ABOVE 4?", sdk_is_above_4_0_0)


def _resolve_collection(transfer_collection_id: str) -> str:
    return COLLECTION_ALIASES.get(transfer_collection_id, transfer_collection_id)


def add_transfer_scope(
    base: dict[str, Any],
    authorize_transfer: list[str] | None = None,
) -> dict[str, Any]:

    # Globus-SDK >= 4
    if sdk_is_above_4_0_0:
        transfer_scope = TransferScopes.all
        for raw in authorize_transfer:
            collection_id, *gcs_scopes = _resolve_collection(raw).split(":")
            if "data_access" in gcs_scopes:
                data_access = GCSCollectionScopes(collection_id).data_access.with_optional(True)
                transfer_scope = transfer_scope.with_dependency(data_access)
                base[collection_id] = [data_access]
        base[TRANSFER_RESOURCE_SERVER] = [transfer_scope]

    # Globus-SDK < 4
    else:
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