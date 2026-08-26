import json
import logging

import httpx
import typer

from .auth import AuthError, get_access_token, login as auth_login, SCOPE_RESOURCE_SERVERS, SERVICES, TOKENS_PATH

logger = logging.getLogger(__name__)

cli = typer.Typer(no_args_is_help=True)
auth_cli = typer.Typer(no_args_is_help=True)
cli.add_typer(auth_cli, name="auth", help="Login and manage access tokens")


@cli.callback()
def main(log_level: str = "WARNING") -> None:
    """
    ALCF client to interface with various ALCF services.
    """
    logging.basicConfig(
        level=log_level,
        format="%(name)s:%(lineno)d %(message)s",
    )


@auth_cli.command()
def login(
    service: str | None = typer.Argument(
        None,
        help=(
            "Re-authenticate for a single service only, preserving other tokens. "
            f"Valid values: {', '.join(sorted(SERVICES))}."
        ),
    ),
) -> None:
    """
    Log in with Globus. By default, triggers a single authentication flow that
    gathers access tokens for all supported services. Optionally pass a service
    name to re-authenticate for one service only without affecting other stored tokens.
    """
    if service is not None and service not in SERVICES:
        valid = ", ".join(sorted(SERVICES))
        typer.echo(f"Unknown service '{service}'. Valid values: {valid}", err=True)
        raise typer.Exit(code=1)
    auth_login(service)


@auth_cli.command()
def get_token(
    service: str = typer.Argument(
        ...,
        help=(
            "The service whose access token to retrieve. "
            f"Valid values: {', '.join(sorted(SCOPE_RESOURCE_SERVERS))}."
        ),
    ),
) -> None:
    """
    Print an access token for the given service.

    Automatically uses locally cached tokens, refreshing when necessary.
    If no token is stored or the refresh token has expired, re-run 'auth login'.

    Examples:
        alcf-client auth get-token inference
        alcf-client auth get-token iri
    """
    try:
        token = get_access_token(service)
    except AuthError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    print(token)


_TEST_ENDPOINTS: dict[str, str | None] = {
    "inference": "https://inference-api.alcf.anl.gov/resource_server/whoami",
    "iri": "https://api.alcf.anl.gov/api/v1/account/projects",
    "globus-compute": None,
}


@auth_cli.command()
def test_token(
    service: str = typer.Argument(
        ...,
        help=(
            "The service to test the token against. "
            f"Valid values: {', '.join(sorted(SCOPE_RESOURCE_SERVERS))}."
        ),
    ),
) -> None:
    """
    Test whether the stored token for a service is accepted.

    Examples:
        alcf-client auth test-token inference
        alcf-client auth test-token iri
    """
    if service not in SCOPE_RESOURCE_SERVERS:
        valid = ", ".join(sorted(SCOPE_RESOURCE_SERVERS))
        typer.echo(json.dumps({"ready": False, "error": f"Unknown service '{service}'. Valid values: {valid}"}))
        raise typer.Exit(code=1)

    endpoint = _TEST_ENDPOINTS.get(service)
    if endpoint is None:
        typer.echo(f"test-token is not yet implemented for '{service}'", err=True)
        raise typer.Exit(code=0)

    try:
        token = get_access_token(service)
    except AuthError as exc:
        typer.echo(json.dumps({"ready": False, "error": str(exc)}))
        raise typer.Exit(code=1)

    response = httpx.get(endpoint, headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        typer.echo(json.dumps({"ready": True, "error": None}))
    else:
        typer.echo(json.dumps({"ready": False, "error": f"HTTP {response.status_code}: {response.text}"}))
        raise typer.Exit(code=1)


@auth_cli.command()
def clear_tokens() -> None:
    """
    Remove locally stored tokens.
    """
    if TOKENS_PATH.is_file():
        TOKENS_PATH.unlink()
        typer.echo("Tokens removed.")
    else:
        typer.echo("No tokens found.")


if __name__ == "__main__":
    cli()
