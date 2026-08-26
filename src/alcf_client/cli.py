import logging

import typer

from .auth import AuthError, get_access_token, login as auth_login, SCOPE_RESOURCE_SERVERS, TOKENS_PATH

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
def login() -> None:
    """
    Log in with Globus. Triggers a single authentication flow that gathers
    access tokens for all supported services. Credentials are stored in your
    home directory.
    """
    auth_login()


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
