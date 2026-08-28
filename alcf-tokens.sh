#!/bin/sh
set -eu

APP_NAME="alcf_tokens"
AUTH_CLIENT_ID="7f3e61f5-e0de-4e8f-9150-0a62c65dda63"

AUTH_BASE_URL="https://auth.globus.org"
AUTHORIZE_URL="${AUTH_BASE_URL}/v2/oauth2/authorize"
TOKEN_URL="${AUTH_BASE_URL}/v2/oauth2/token"
REVOKE_URL="${AUTH_BASE_URL}/v2/oauth2/token/revoke"
REDIRECT_URI="${AUTH_BASE_URL}/v2/web/auth-code"

TOKEN_DIR="${ALCF_TOKENS_DIR:-${INFERENCE_AUTH_TOKEN_DIR:-${HOME}/.globus/app/${AUTH_CLIENT_ID}/${APP_NAME}}}"
TOKEN_FILE="${ALCF_TOKENS_FILE:-${INFERENCE_AUTH_TOKEN_FILE:-${TOKEN_DIR}/tokens-bash.json}}"
EXPIRATION_SKEW_SECONDS=60

# Services, kept sorted. Each config is a pipe-separated record:
#   resource_server|scope|session_required_policy|description|documentation_url|test_endpoint|expected_status
SERVICES_ALL="globus-compute inference iri"

INFERENCE_CFG="681c10cc-f684-4540-bcd7-0b4df3bc26ef|https://auth.globus.org/scopes/681c10cc-f684-4540-bcd7-0b4df3bc26ef/action_all|83732ff2-9c42-4548-b5ce-17e498c84f6a|ALCF Inference Service|https://docs.alcf.anl.gov/services/inference-endpoints/|https://inference-api.alcf.anl.gov/resource_server/whoami|200"
IRI_CFG="6be511f6-a071-471f-9bc0-02a0d0836723|https://auth.globus.org/scopes/6be511f6-a071-471f-9bc0-02a0d0836723/filesystem|a128e981-c9a5-417a-97ab-8571c9831bff|ALCF Integrated Research Infrastructure (IRI) API|https://docs.alcf.anl.gov/services/iri-api/|https://api.alcf.anl.gov/api/v1/task/not-a-real-task|404"
GLOBUS_COMPUTE_CFG="funcx_service|https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all||Globus Compute|https://www.globus.org/compute||"

# Globals populated by service_config.
_RS=""
_SCOPE=""
_POLICY=""
_DESC=""
_DOC=""
_TURL=""
_TSTATUS=""

usage() {
    cat <<EOF
Usage: $(basename "$0") <action> [<service>]

Services: $SERVICES_ALL

Actions:
  login [<service>]                          Authenticate with Globus. Authenticates all
                                             services unless a service is given.
  get-token <service>                        Print a valid bearer access token for a service
  test-token <service>                       Test whether the stored token for a service is accepted
  list-services                              List available services
  clear-tokens                               Remove stored tokens without revoking
  revoke-access-token <service>              Revoke cached tokens for a service and remove them
  get-time-until-token-expiration [<service>] [seconds|minutes|hours]
                                             Print time until token expiration

Environment:
  ALCF_TOKENS_FILE                     Override token cache path
  ALCF_TOKENS_DIR                      Override token cache directory
  INFERENCE_AUTH_TOKEN_FILE            Legacy override for token cache path
  INFERENCE_AUTH_TOKEN_DIR             Legacy override for token cache directory
  BROWSER                              Browser opener command
EOF
}

die() {
    printf '%s\n' "Error: $*" >&2
    exit 1
}

require_commands() {
    missing=
    for cmd in awk curl jq openssl; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing="$missing $cmd"
        fi
    done
    if [ -n "$missing" ]; then
        die "missing required command(s):$missing"
    fi
}

require_service() {
    service="$1"
    case "$service" in
        inference|iri|globus-compute) ;;
        *) die "unknown service '$service'. Valid services: $SERVICES_ALL" ;;
    esac
}

service_config() {
    config_name="$1"
    case "$config_name" in
        inference) cfg="$INFERENCE_CFG" ;;
        iri) cfg="$IRI_CFG" ;;
        globus-compute) cfg="$GLOBUS_COMPUTE_CFG" ;;
        *) cfg="" ;;
    esac
    IFS='|' read -r _RS _SCOPE _POLICY _DESC _DOC _TURL _TSTATUS <<EOF
$cfg
EOF
}

urlencode() {
    jq -rn --arg value "$1" '$value | @uri'
}

form_body() {
    body=
    while [ "$#" -gt 0 ]; do
        key="$1"
        value="$2"
        shift 2
        if [ -n "$body" ]; then
            body="$body&"
        fi
        body="$body$(urlencode "$key")=$(urlencode "$value")"
    done
    printf '%s' "$body"
}

random_urlsafe() {
    openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
}

pkce_challenge() {
    printf '%s' "$1" |
        openssl dgst -sha256 -binary |
        openssl base64 -A |
        tr '+/' '-_' |
        tr -d '='
}

open_browser() {
    url="$1"

    if [ -n "${BROWSER:-}" ] && command -v "$BROWSER" >/dev/null 2>&1; then
        "$BROWSER" "$url" >/dev/null 2>&1 &
        return 0
    fi

    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 &
        return 0
    fi

    if command -v open >/dev/null 2>&1; then
        open "$url" >/dev/null 2>&1 &
        return 0
    fi

    return 1
}

http_post_form() {
    url="$1"
    body="$2"
    tmp=$(mktemp)
    status=$(
        printf '%s' "$body" |
            curl -sS -o "$tmp" -w '%{http_code}' \
                -H 'Content-Type: application/x-www-form-urlencoded' \
                --data-binary @- \
                "$url"
    ) || {
        rm -f "$tmp"
        die "request failed"
    }

    if [ "$status" -lt 200 ] || [ "$status" -ge 300 ]; then
        cat "$tmp" >&2
        rm -f "$tmp"
        die "request failed with HTTP ${status}"
    fi

    cat "$tmp"
    rm -f "$tmp"
}

# Select the token whose resource server matches, or whose scope list contains
# the requested scope. Reads the token response from stdin.
select_token() {
    resource_server="$1"
    scope="$2"
    jq -c --arg resource_server "$resource_server" --arg scope "$scope" '
        ([.] + (.other_tokens // []))
        | map(select(
            (.resource_server // "") == $resource_server
            or (((.scope // "") | split(" ")) | index($scope))
        ))
        | .[0] // empty
    '
}

save_token_entry() {
    resource_server="$1"
    scope="$2"
    access_token="$3"
    refresh_token="$4"
    expires_at="$5"

    if [ -z "$access_token" ]; then
        die "token response did not include an access token"
    fi
    if [ -z "$expires_at" ]; then
        die "token response did not include an expiration"
    fi

    if [ -f "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ]; then
        input=$(cat "$TOKEN_FILE")
    else
        input='{}'
    fi

    umask 077
    mkdir -p "$TOKEN_DIR"
    tmp=$(mktemp "${TOKEN_FILE}.tmp.XXXXXX")
    printf '%s\n' "$input" |
        jq --arg app_name "$APP_NAME" \
            --arg client_id "$AUTH_CLIENT_ID" \
            --arg resource_server "$resource_server" \
            --arg scope "$scope" \
            --arg access_token "$access_token" \
            --arg refresh_token "$refresh_token" \
            --argjson expires_at "$expires_at" \
            '.app_name = $app_name
            | .client_id = $client_id
            | .by_resource_server[$resource_server] = {
                scope: $scope,
                access_token: $access_token,
                refresh_token: $refresh_token,
                expires_at: $expires_at
            }' >"$tmp"
    mv "$tmp" "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
}

remove_token_entry() {
    service="$1"

    if [ ! -f "$TOKEN_FILE" ]; then
        return 0
    fi

    service_config "$service"
    resource_server="$_RS"
    input=$(cat "$TOKEN_FILE")

    umask 077
    mkdir -p "$TOKEN_DIR"
    tmp=$(mktemp "${TOKEN_FILE}.tmp.XXXXXX")
    printf '%s\n' "$input" |
        jq --arg resource_server "$resource_server" \
            'del(.by_resource_server[$resource_server])' >"$tmp"
    mv "$tmp" "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
}

require_token_file() {
    if [ ! -f "$TOKEN_FILE" ]; then
        die "access token does not exist. Run: $(basename "$0") login"
    fi
}

# Parse a token response and store every token that belongs to a configured
# service, preserving existing entries for other services. Prints the number
# of tokens stored.
save_response_tokens() {
    response="$1"
    saved=0
    match=
    tokens=

    tokens=$(printf '%s\n' "$response" | jq -c '([.] + (.other_tokens // []))[]')

    if [ -n "$tokens" ]; then
        while IFS= read -r token; do
            resource_server=$(printf '%s\n' "$token" | jq -r '.resource_server // empty')
            scope=$(printf '%s\n' "$token" | jq -r '.scope // empty')
            access_token=$(printf '%s\n' "$token" | jq -r '.access_token // empty')
            refresh_token=$(printf '%s\n' "$token" | jq -r '.refresh_token // empty')
            expires_in=$(printf '%s\n' "$token" | jq -r '.expires_in // 0')

            if [ -n "$access_token" ]; then
                match=
                for name in $SERVICES_ALL; do
                    service_config "$name"
                    if [ "$resource_server" = "$_RS" ]; then
                        match=1
                        break
                    fi
                    if [ -n "$scope" ]; then
                        case "$scope" in
                            *"$_SCOPE"*)
                                match=1
                                break
                                ;;
                        esac
                    fi
                done
                if [ -n "$match" ]; then
                    expires_at=$(( $(date +%s) + expires_in ))
                    save_token_entry "$_RS" "$_SCOPE" "$access_token" "$refresh_token" "$expires_at"
                    saved=$((saved + 1))
                fi
            fi
        done <<EOF
$tokens
EOF
    fi

    printf '%s' "$saved"
}

authenticate() {
    service="$1"
    verifier=$(random_urlsafe)
    challenge=$(pkce_challenge "$verifier")
    scope_param=
    policy=

    if [ -n "$service" ]; then
        service_config "$service"
        scope_param="$_SCOPE"
        policy="$_POLICY"
    else
        for name in $SERVICES_ALL; do
            service_config "$name"
            scope_param="$scope_param $_SCOPE"
        done
        scope_param="${scope_param# }"
    fi

    authorize_url="${AUTHORIZE_URL}?client_id=$(urlencode "$AUTH_CLIENT_ID")"
    authorize_url="$authorize_url&redirect_uri=$(urlencode "$REDIRECT_URI")"
    authorize_url="$authorize_url&scope=$(urlencode "$scope_param")"
    authorize_url="$authorize_url&state=_default"
    authorize_url="$authorize_url&response_type=code"
    authorize_url="$authorize_url&code_challenge=$(urlencode "$challenge")"
    authorize_url="$authorize_url&code_challenge_method=S256"
    authorize_url="$authorize_url&access_type=offline"
    if [ -n "$policy" ]; then
        authorize_url="$authorize_url&session_required_policies=$(urlencode "$policy")"
    fi

    printf '%s\n' "Open this URL and log in:"
    printf '%s\n' ''
    printf '%s\n' "$authorize_url"
    printf '%s\n' ''
    open_browser "$authorize_url" || true

    printf '%s' "Paste the Globus authorization code: "
    read -r auth_code
    if [ -z "$auth_code" ]; then
        die "authorization code is required"
    fi

    response=$(http_post_form "$TOKEN_URL" "$(form_body grant_type authorization_code client_id "$AUTH_CLIENT_ID" code "$auth_code" code_verifier "$verifier" redirect_uri "$REDIRECT_URI")")

    saved=$(save_response_tokens "$response")
    if [ "$saved" -eq 0 ]; then
        die "token response did not include tokens for ${SERVICES_ALL}"
    fi

    printf '%s\n' "Authenticated. Token cache: ${TOKEN_FILE}"
}

refresh_access_token() {
    service="$1"
    require_token_file
    service_config "$service"
    resource_server="$_RS"
    scope="$_SCOPE"

    refresh_token=$(jq -r --arg rs "$resource_server" '.by_resource_server[$rs].refresh_token // empty' "$TOKEN_FILE")
    if [ -z "$refresh_token" ]; then
        die "cached refresh token is missing for '$service'. Run: $(basename "$0") login"
    fi

    response=$(http_post_form "$TOKEN_URL" "$(form_body grant_type refresh_token client_id "$AUTH_CLIENT_ID" refresh_token "$refresh_token")") || die "refresh failed. Run: $(basename "$0") login"

    token=$(printf '%s\n' "$response" | select_token "$resource_server" "$scope")
    if [ -z "$token" ]; then
        token="$response"
    fi

    access_token=$(printf '%s\n' "$token" | jq -r '.access_token // empty')
    if [ -z "$access_token" ]; then
        die "refresh response did not include an access token"
    fi
    expires_in=$(printf '%s\n' "$token" | jq -r '.expires_in // 0')
    new_refresh=$(printf '%s\n' "$token" | jq -r '.refresh_token // empty')
    if [ -z "$new_refresh" ]; then
        new_refresh="$refresh_token"
    fi
    expires_at=$(( $(date +%s) + expires_in ))

    save_token_entry "$resource_server" "$scope" "$access_token" "$new_refresh" "$expires_at"
}

get_access_token() {
    service="$1"
    require_token_file
    service_config "$service"
    resource_server="$_RS"

    expires_at=$(jq -r --arg rs "$resource_server" '.by_resource_server[$rs].expires_at // .by_resource_server[$rs].expires_at_epoch // 0' "$TOKEN_FILE")
    now=$(date +%s)

    if [ "$((now + EXPIRATION_SKEW_SECONDS))" -ge "$expires_at" ]; then
        refresh_access_token "$service"
    fi

    jq -r --arg rs "$resource_server" '.by_resource_server[$rs].access_token // empty' "$TOKEN_FILE"
}

get_time_until_token_expiration() {
    service="$1"
    units="$2"
    require_token_file
    service_config "$service"
    resource_server="$_RS"

    expires_at=$(jq -r --arg rs "$resource_server" '.by_resource_server[$rs].expires_at // .by_resource_server[$rs].expires_at_epoch // 0' "$TOKEN_FILE")
    now=$(date +%s)
    seconds=$((expires_at - now))

    case "$units" in
        seconds)
            printf '%s\n' "$seconds"
            ;;
        minutes)
            awk -v seconds="$seconds" 'BEGIN { printf "%.2f\n", seconds / 60 }'
            ;;
        hours)
            awk -v seconds="$seconds" 'BEGIN { printf "%.2f\n", seconds / 3600 }'
            ;;
        *)
            die "units must be 'seconds', 'minutes', or 'hours'"
            ;;
    esac
}

revoke_token_value() {
    token="$1"
    if [ -z "$token" ]; then
        return 0
    fi

    http_post_form "$REVOKE_URL" "$(
        form_body token "$token" client_id "$AUTH_CLIENT_ID"
    )" >/dev/null
}

revoke_access_token() {
    service="$1"
    require_token_file
    service_config "$service"
    resource_server="$_RS"

    access_token=$(jq -r --arg rs "$resource_server" '.by_resource_server[$rs].access_token // empty' "$TOKEN_FILE")
    refresh_token=$(jq -r --arg rs "$resource_server" '.by_resource_server[$rs].refresh_token // empty' "$TOKEN_FILE")

    revoke_token_value "$access_token"
    revoke_token_value "$refresh_token"
    remove_token_entry "$service"

    printf '%s\n' "Done. The Globus services can take up to ~10 minutes to incorporate the revocation."
}

clear_tokens() {
    if [ -f "$TOKEN_FILE" ]; then
        rm -f "$TOKEN_FILE"
        printf '%s\n' "Tokens removed."
    else
        printf '%s\n' "No tokens found."
    fi
}

test_token() {
    service="$1"
    service_config "$service"
    if [ -z "$_TURL" ]; then
        printf '%s\n' "test_token is not yet implemented for '$service'" >&2
        return 0
    fi
    endpoint="$_TURL"
    expected="$_TSTATUS"

    token=$(get_access_token "$service")

    tmp=$(mktemp)
    status=$(curl -sS -o "$tmp" -w '%{http_code}' -H "Authorization: Bearer $token" "$endpoint") || {
        rm -f "$tmp"
        die "request failed"
    }
    body=$(cat "$tmp")
    rm -f "$tmp"

    if [ "$status" = "$expected" ]; then
        jq -n '{ready: true, error: null}'
    else
        jq -n --arg status "HTTP $status" --arg text "$body" \
            '{ready: false, error: ($status + ": " + $text)}'
        return 1
    fi
}

list_services() {
    for name in $SERVICES_ALL; do
        service_config "$name"
        jq -n --arg name "$name" --arg desc "$_DESC" --arg doc "$_DOC" \
            '{service_name: $name, description: $desc, documentation_url: $doc}'
    done | jq -s .
}

main() {
    action="${1:-}"
    if [ -z "$action" ] || [ "$action" = "-h" ] || [ "$action" = "--help" ]; then
        usage
        exit 0
    fi
    shift || true

    # Bash-style option flags are not supported; reject any flag-like argument.
    for arg in "$@"; do
        case "$arg" in
            -*) die "unknown argument: $arg" ;;
        esac
    done

    require_commands

    case "$action" in
        login)
            if [ "$#" -eq 0 ]; then
                authenticate ""
            else
                require_service "$1"
                if [ "$#" -gt 1 ]; then
                    die "unexpected extra argument: $2"
                fi
                authenticate "$1"
            fi
            ;;
        get-token)
            if [ "$#" -eq 0 ]; then
                die "missing service argument. Run: $(basename "$0") get-token <service>"
            fi
            require_service "$1"
            if [ "$#" -gt 1 ]; then
                die "unexpected extra argument: $2"
            fi
            get_access_token "$1"
            ;;
        test-token)
            if [ "$#" -eq 0 ]; then
                die "missing service argument. Run: $(basename "$0") test-token <service>"
            fi
            require_service "$1"
            if [ "$#" -gt 1 ]; then
                die "unexpected extra argument: $2"
            fi
            test_token "$1"
            ;;
        revoke-access-token)
            if [ "$#" -eq 0 ]; then
                die "missing service argument. Run: $(basename "$0") revoke-access-token <service>"
            fi
            require_service "$1"
            if [ "$#" -gt 1 ]; then
                die "unexpected extra argument: $2"
            fi
            revoke_access_token "$1"
            ;;
        get-time-until-token-expiration)
            service="${1:-inference}"
            if [ "$#" -ge 1 ]; then
                shift
            fi
            units="${1:-seconds}"
            if [ "$#" -ge 1 ]; then
                shift
            fi
            if [ "$#" -gt 0 ]; then
                die "unexpected extra argument: $1"
            fi
            require_service "$service"
            case "$units" in
                seconds|minutes|hours) ;;
                *) die "units must be 'seconds', 'minutes', or 'hours'" ;;
            esac
            get_time_until_token_expiration "$service" "$units"
            ;;
        list-services)
            if [ "$#" -gt 0 ]; then
                die "list-services takes no arguments"
            fi
            list_services
            ;;
        clear-tokens)
            if [ "$#" -gt 0 ]; then
                die "clear-tokens takes no arguments"
            fi
            clear_tokens
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
}

main "$@"
