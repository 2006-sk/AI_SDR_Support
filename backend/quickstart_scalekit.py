"""Scalekit + Apollo quickstart — run after setting SCALEKIT_* in .env."""

import os

from dotenv import load_dotenv
from scalekit.client import ScalekitClient

load_dotenv()

scalekit_client = ScalekitClient(
    env_url=os.getenv("SCALEKIT_ENV_URL"),
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
)
actions = scalekit_client.actions

connection_name = os.getenv("SCALEKIT_APOLLO_CONNECTION", "apollo")
identifier = os.getenv("SCALEKIT_USER_IDENTIFIER", "user_123")

link_response = actions.get_authorization_link(
    connection_name=connection_name,
    identifier=identifier,
)
print("Authorize Apollo:", link_response.link)
input("Press Enter after authorizing...")

result = actions.execute_tool(
    tool_input={},
    tool_name="apollo_list_sequences",
    connection_name=connection_name,
    identifier=identifier,
)
print(result.to_dict())
