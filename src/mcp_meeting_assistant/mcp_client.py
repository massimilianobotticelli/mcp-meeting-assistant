from contextlib import AsyncExitStack
from typing import Any, List, Dict, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool, CallToolResult

class MCPClient:
    """
    An asynchronous client for managing a connection to a local MCP server
    running over standard I/O.

    This class handles the lifecycle of the server process and provides
    methods to interact with its tools and prompts. It is designed to be
    used as an async context manager.
    """

    def __init__(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
    ):
        """
        Initializes the MCPClient.

        Args:
            command: The command to execute the server (e.g., 'python').
            args: A list of arguments for the command (e.g., ['path/to/server.py']).
            env: An optional dictionary of environment variables for the server process.
        """
        self._command: str = command
        self._args: List[str] = args
        self._env: Optional[Dict[str, str]] = env
        self._session: Optional[ClientSession] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self) -> None:
        """
        Establishes a connection to the stdio server process and initializes
        the client session.
        """
        server_params = StdioServerParameters(
            command=self._command, args=self._args, env=self._env,
        )
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        _stdio, _write = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(_stdio, _write)
        )
        await self._session.initialize()

    def session(self) -> ClientSession:
        """
        Returns the active ClientSession instance.

        Raises:
            ConnectionError: If the client is not connected.

        Returns:
            The active ClientSession instance.
        """
        if self._session is None:
            raise ConnectionError("Client session not initialized. Call connect first.")
        return self._session

    async def list_tools(self) -> List[Tool]:
        """
        Fetches the list of available tools from the MCP server.

        Returns:
            A list of Tool objects.
        """
        result = await self.session().list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> CallToolResult:
        """
        Calls a specific tool on the MCP server with the given input.

        Args:
            tool_name: The name of the tool to call.
            tool_input: A dictionary of arguments for the tool.

        Returns:
            The response from the tool call.
        """
        return await self.session().call_tool(tool_name, tool_input)

    async def run_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Gets a prompt from the server and returns its raw text content.

        Args:
            name: The name of the prompt to run.
            arguments: An optional dictionary of arguments for the prompt.

        Returns:
            The raw text content of the prompt, or None if the prompt is empty.
        """
        if not self._session:
            raise ConnectionError("Not connected to the MCP server.")

        prompt_result = await self.session().get_prompt(name, arguments or {})

        if prompt_result and prompt_result.messages:
            return prompt_result.messages[0].content.text
        return None
    
    async def list_prompts(self) -> List[str]:
        """
        Lists all available prompts on the MCP server.

        Returns:
            A list of prompt names.
        """
        if not self._session:
            raise ConnectionError("Not connected to the MCP server.")
        
        prompts_result = await self.session().list_prompts()
        return [prompt.name for prompt in prompts_result.prompts]

    async def cleanup(self) -> None:
        """
        Cleans up resources and closes the connection and server process.
        """
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self) -> "MCPClient":
        """
        Enters the async context, connecting to the server.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exits the async context, cleaning up the connection.
        """
        await self.cleanup()
