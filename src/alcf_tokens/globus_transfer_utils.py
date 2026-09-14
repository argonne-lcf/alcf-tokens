from importlib.metadata import version
from typing import Any

from globus_sdk.scopes import TransferScopes

TRANSFER_RESOURCE_SERVER = TransferScopes.resource_server
TRANSFER_SCOPE_ALL = TransferScopes.all

COLLECTION_ALIASES: dict[str, str] = {
    "eagle": "05d2c76a-e867-4f67-aa57-76edeb0beda0:data_access",
    "flare": "f39a7a0f-5bfc-46ce-9615-ba9f8592814f:data_access",
    "home": "9032dd3a-e841-4687-a163-2720da731b5b:data_access",
}

globus_sdk_installed = tuple(map(int, version("globus-sdk").split(".")))
sdk_is_above_4_0_0: bool = globus_sdk_installed >= (4, 0, 0)

if sdk_is_above_4_0_0:
    from globus_sdk.scopes import GCSCollectionScopes, TransferScopes
else:
    from globus_sdk.scopes import GCSCollectionScopeBuilder, TransferScopes


def resolve_collection(collection_str: str) -> str:
    alias_or_id, *scopes = collection_str.split(":")
    collection_id = COLLECTION_ALIASES.get(alias_or_id, alias_or_id)
    if ":" in collection_id:
        collection_id, *default_scopes = collection_id.split(":")
        scopes = sorted(set([*default_scopes, *scopes]))
    return ":".join([collection_id, *scopes])


def _gcs_collection_scope(collection_id: str, scope_name: str) -> Any:
    """
    An optional scope on a GCS collection, such as `data_access` or `https`.
    """
    if sdk_is_above_4_0_0:
        scope = getattr(GCSCollectionScopes(collection_id), scope_name)
        return scope.with_optional(True)
    return GCSCollectionScopeBuilder(collection_id).make_mutable(
        scope_name, optional=True
    )


def add_transfer_scope(
    base: dict[str, Any],
    authorize_transfer: list[str] | None = None,
) -> dict[str, Any]:
    """
    Add the Transfer scope to `base`, plus any collection scopes named by the
    `authorize_transfer` entries, which take the form
    `<collection-id-or-alias>[:data_access][:https]`.

    `data_access` becomes a dependency of the Transfer scope, because Transfer
    uses it on the user's behalf.  `https` is a scope on the collection itself,
    granting direct HTTPS reads and writes of files on that collection.
    """
    if sdk_is_above_4_0_0:
        transfer_scope = TransferScopes.all
    else:
        transfer_scope = TransferScopes.make_mutable("all")

    for raw in authorize_transfer or []:
        collection_id, *gcs_scopes = resolve_collection(raw).split(":")
        collection_scopes = []

        if "data_access" in gcs_scopes:
            data_access = _gcs_collection_scope(collection_id, "data_access")
            if sdk_is_above_4_0_0:
                transfer_scope = transfer_scope.with_dependency(data_access)
            else:
                transfer_scope.add_dependency(data_access)
            collection_scopes.append(data_access)

        if "https" in gcs_scopes:
            collection_scopes.append(_gcs_collection_scope(collection_id, "https"))

        if collection_scopes:
            base.setdefault(collection_id, []).extend(collection_scopes)

    base[TRANSFER_RESOURCE_SERVER] = [transfer_scope]
    return base
