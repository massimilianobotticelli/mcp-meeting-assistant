"""
This is the main entry point for the command-line chat application.

This script initializes the necessary services, including the language model
(LLM) service and the MCP client, and then starts an interactive chat session.
It is designed to be run from the command line.
"""

import asyncio
import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from dotenv import load_dotenv

# Corrected import paths to match the project structure
from mcp_meeting_assistant.chat_session import ChatSession
from mcp_meeting_assistant.mcp_client import MCPClient
from mcp_meeting_assistant.models.gemini import Gemini

# Load environment variables from a .env file for configuration
load_dotenv()

# Define the path to the MCP server script, making it relative to this file's location
SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")


async def main() -> None:
    """
    Sets up and runs the main application loop.

    This function performs the following steps:
    1. Determines which LLM service to use based on environment variables.
    2. Initializes the chosen LLM service (e.g., Gemini).
    3. Starts the MCP server as a background process.
    4. Establishes a client connection to the MCP server.
    5. Initializes and runs the interactive chat session.
    """
    # For now, only the Gemini model is supported.
    # This structure allows for easy extension to other models in the future.
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    llm_service: Any = Gemini(model_name=model_name)
    print(f"Initializing with model: {model_name}")

    # The AsyncExitStack ensures that all resources (like the MCP client)
    # are cleaned up properly when the application exits, even if errors occur.
    async with AsyncExitStack() as stack:
        # Define the command to start the MCP server.
        # Using sys.executable ensures we use the same Python interpreter
        # that is running this script.
        command, args = (sys.executable, [SERVER_PATH])

        # Connect to the MCP server. The client manages the server's lifecycle.
        mcp_client = await stack.enter_async_context(
            MCPClient(
                command=command,
                args=args,
                sampling_callback=llm_service.sampling_callback,
            )
        )

        # Create the chat session, injecting the LLM service and MCP client
        chat_session = ChatSession(llm_service, mcp_client)

        print("\n=======================================")
        print("Chat session started (type 'exit' to quit)")
        print("=======================================")

        # Start the interactive loop
        await chat_session.run()


if __name__ == "__main__":
    try:
        # Run the main asynchronous event loop
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle graceful exit on Ctrl+C
        print("\nExiting application.")
        sys.exit(0)
