"""Scalekit + Apollo.io helpers."""

from __future__ import annotations

import os
from typing import Any

from scalekit.client import ScalekitClient


def scalekit_configured() -> bool:
    return bool(
        os.getenv("SCALEKIT_ENV_URL", "").strip()
        and os.getenv("SCALEKIT_CLIENT_ID", "").strip()
        and os.getenv("SCALEKIT_CLIENT_SECRET", "").strip()
        and os.getenv("SCALEKIT_APOLLO_CONNECTION", "").strip()
    )


def apollo_connection_name() -> str:
    return os.getenv("SCALEKIT_APOLLO_CONNECTION", "").strip()


def get_client() -> ScalekitClient:
    env_url = os.getenv("SCALEKIT_ENV_URL", "").strip()
    client_id = os.getenv("SCALEKIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("SCALEKIT_CLIENT_SECRET", "").strip()
    if not env_url or not client_id or not client_secret:
        raise ValueError(
            "Set SCALEKIT_ENV_URL, SCALEKIT_CLIENT_ID, SCALEKIT_CLIENT_SECRET in .env"
        )
    return ScalekitClient(
        env_url=env_url,
        client_id=client_id,
        client_secret=client_secret,
    )


def tool_result_to_dict(result: Any) -> dict:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    data = getattr(result, "data", None)
    return {"data": data, "execution_id": getattr(result, "execution_id", None)}


def resolve_apollo_account(
    connection_name: str | None = None,
    identifier: str | None = None,
) -> dict:
    """
    Resolve Scalekit connected account for Apollo.
    If identifier is omitted, uses the first ACTIVE account on the connection.
    """
    conn = (connection_name or apollo_connection_name()).strip()
    if not conn:
        raise ValueError("SCALEKIT_APOLLO_CONNECTION not set")

    client = get_client()
    if identifier:
        details = client.actions.get_connected_account_details(
            connection_name=conn,
            identifier=identifier,
        )
        status = getattr(details, "status", None) or getattr(details, "account_status", "")
        return {
            "connection_name": conn,
            "identifier": identifier,
            "status": str(status),
        }

    listed = client.actions.list_connected_accounts(connection_name=conn)
    accounts = getattr(listed, "connected_accounts", None) or []
    active = [
        a
        for a in accounts
        if str(getattr(a, "status", "")).upper() == "ACTIVE"
    ]
    if not active:
        raise ValueError(
            f"No ACTIVE Apollo account on connection '{conn}'. "
            f"Authorize at GET /enrich/auth"
        )
    account = active[0]
    return {
        "connection_name": conn,
        "identifier": getattr(account, "identifier", ""),
        "status": getattr(account, "status", ""),
        "provider": getattr(account, "provider", ""),
    }


def get_auth_link(*, connection_name: str | None = None, identifier: str | None = None) -> dict:
    conn = (connection_name or apollo_connection_name()).strip()
    client = get_client()
    kwargs: dict = {"connection_name": conn}
    if identifier:
        kwargs["identifier"] = identifier
    link_response = client.actions.get_authorization_link(**kwargs)
    link = getattr(link_response, "link", None) or getattr(link_response, "magic_link", "")
    return {
        "link": link,
        "expires_at": getattr(link_response, "expires_at", None),
        "connection_name": conn,
    }


def execute_apollo_tool(
    *,
    tool_name: str,
    tool_input: dict,
    connection_name: str | None = None,
    identifier: str | None = None,
) -> dict:
    account = resolve_apollo_account(connection_name, identifier)
    client = get_client()
    result = client.actions.execute_tool(
        tool_input=tool_input,
        tool_name=tool_name,
        connection_name=account["connection_name"],
        identifier=account["identifier"],
    )
    out = tool_result_to_dict(result)
    out["connected_account"] = account
    return out


def apollo_list_sequences(
    connection_name: str | None = None,
    identifier: str | None = None,
) -> dict:
    return execute_apollo_tool(
        tool_name="apollo_list_sequences",
        tool_input={},
        connection_name=connection_name,
        identifier=identifier,
    )


def apollo_search_contacts(
    *,
    keywords: str,
    per_page: int = 5,
    connection_name: str | None = None,
    identifier: str | None = None,
) -> dict:
    return execute_apollo_tool(
        tool_name="apollo_search_contacts",
        tool_input={"q_keywords": keywords, "per_page": per_page},
        connection_name=connection_name,
        identifier=identifier,
    )
