"""
This module provides a wrapper for the Google Gemini API, allowing interaction
with the Gemini model for generating text responses and executing tool calls.
It includes methods for asking questions, managing conversation history,
and handling tool requests in a format compatible with the Gemini API.
"""

import json
import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai.types import GenerateContentResponse
from mcp.client.session import RequestContext
from mcp.types import CreateMessageRequestParams, CreateMessageResult, TextContent, Tool

from mcp_meeting_assistant.mcp_client import MCPClient
from mcp_meeting_assistant.models.model import Model


def clean_schema(schema: Any) -> Any:
    """
    Recursively cleans a JSON schema to be compatible with Gemini's API.
    This is necessary because the Gemini API has stricter requirements for
    the schema format than the default Pydantic output.

    Specifically, it:
    - Removes the 'title' field from properties.
    - Converts the 'type' field's value to uppercase (e.g., 'string' -> 'STRING').

    Args:
        schema: The JSON schema (as a dict or list) to be cleaned.

    Returns:
        The cleaned JSON schema.
    """
    if isinstance(schema, dict):
        new_schema = {}
        for key, value in schema.items():
            if key == "title":
                continue
            if key == "type" and isinstance(value, str):
                new_schema[key] = value.upper()
            else:
                new_schema[key] = clean_schema(value)
        return new_schema
    if isinstance(schema, list):
        return [clean_schema(item) for item in schema]
    return schema


class Gemini(Model):
    """
    A wrapper for the Google Gemini API, responsible for making API calls,
    formatting data, and handling API-specific errors.
    """

    def __init__(self, model_name: str):
        """
        Initializes the Gemini service wrapper.

        Args:
            model_name: The name of the Gemini model to use (e.g., 'gemini-pro').
        """
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model_name)
        # This disables strict response validation, which can help prevent
        # crashes from unrecognized enum values like 'FinishReason: 12'.
        self.model._check_response_type = False

    async def sampling_callback(
        self, context: RequestContext, params: CreateMessageRequestParams
    ) -> CreateMessageResult:
        """
        Handles LLM sampling requests originating from a server-side tool.
        This is passed to the MCPClient during initialization.

        Args:
            context: The request context, provided by the MCP session.
            params: The parameters for the message creation, including the messages
                    and sampling settings like temperature.

        Returns:
            A CreateMessageResult object containing the model's response.
        """
        print("--- Server triggered sampling callback ---")
        messages = []
        for msg in params.messages:
            role = "model" if msg.role == "assistant" else msg.role
            if msg.content.type == "text":
                messages.append({"role": role, "parts": [msg.content.text]})

        # Build generation config, respecting sampling params from the server
        generation_config_args = {"max_output_tokens": params.max_tokens}
        if params.temperature is not None:
            generation_config_args["temperature"] = params.temperature
        if params.top_p is not None:
            generation_config_args["top_p"] = params.top_p

        generation_config = genai.types.GenerationConfig(**generation_config_args)

        # Call the Gemini API with the provided messages and config
        response = await self.model.generate_content_async(
            messages,
            generation_config=generation_config,
        )

        return CreateMessageResult(
            role="assistant",
            model=self.model.model_name,
            content=TextContent(type="text", text=response.text),
        )

    def ask(self, question: str, messages_history: List[Dict[str, Any]]) -> str:
        """
        Asks a question within a conversation, automatically updating the history
        with a consistent dictionary format.

        This method adds the user's question to the provided history, sends the
        entire history to the model, adds the model's response back to the
        history as a dictionary, and then returns the text part of the response.
        It directly mutates the `messages_history` list.

        Args:
            question: The question to ask the model as a simple string.
            messages_history: The conversation history list to use and update.

        Returns:
            The model's text response as a string.
        """
        # Add user's question to the history
        self.add_message_to_history(
            messages_history, {"role": "user", "parts": [{"text": question}]}
        )

        # Get response from model using the full history
        response = self.chat(messages_history)

        if response is None:
            messages_history.pop()  # Remove dangling question on API error
            return ""

        text = self.text_from_message(response)

        # If we got a valid text response, add it to history as a dictionary.
        if text:
            self.add_message_to_history(
                messages_history, {"role": "model", "parts": [{"text": text}]}
            )
        # If the response was empty, remove the user's question to keep history clean.
        else:
            messages_history.pop()

        return text

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[GenerateContentResponse]:
        """
        Sends a request to the Gemini API with a conversation history and handles potential server
        errors.

        Args:
            messages: A list of message objects representing the conversation history.
            tools: An optional list of tools available for the model to call.

        Returns:
            A `GenerateContentResponse` object on success, or `None` if a
            server-side error (like a 500 error) occurs.
        """
        params = {"contents": messages}
        if tools:
            params["tools"] = tools

        try:
            return self.model.generate_content(**params)
        except google_exceptions.InternalServerError:
            print(
                "\n🔴 A temporary error occurred on the server (500). Please try your request"
                "again in a moment."
            )
            return None
        except Exception as e:
            print(f"\nAn unexpected error occurred during the API call: {e}")
            return None

    def add_message_to_history(
        self, messages: List[Dict[str, Any]], message: Dict[str, Any]
    ) -> None:
        """
        Appends a new message to a list representing a conversation history.

        Args:
            messages: The list of messages for the current turn.
            message: The message dictionary to append.
        """
        messages.append(message)

    def text_from_message(self, response: Optional[GenerateContentResponse]) -> str:
        """
        Safely extracts the text content from a model's response object.

        Args:
            response: The response object from the generative model.

        Returns:
            The extracted text as a string, or an empty string if no text is found.
        """
        if not response:
            return ""
        try:
            return response.text
        except (ValueError, IndexError):
            return ""

    async def get_tools(self, client: MCPClient) -> List[Dict[str, Any]]:
        """
        Fetches tools from the MCP server and formats them for the Gemini API.

        Args:
            client: The MCPClient instance to fetch tools from.

        Returns:
            A list of tool definitions formatted for the Gemini API.
        """
        gemini_tools: List[Dict[str, Any]] = []
        mcp_tools: List[Tool] = await client.list_tools()
        for tool in mcp_tools:
            cleaned_schema = clean_schema(tool.inputSchema) if tool.inputSchema else {}
            gemini_tools.append(
                {
                    "function_declarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": cleaned_schema,
                        }
                    ]
                }
            )
        return gemini_tools

    async def execute_tool_requests(
        self, client: MCPClient, response: Optional[GenerateContentResponse]
    ) -> List[Dict[str, Any]]:
        """
        Parses tool call requests from a model's response, executes them via the
        MCP client, and formats the results for the next API call.

        Args:
            client: The MCPClient instance to execute tools with.
            response: The response object from the model, which may contain tool calls.

        Returns:
            A list of tool results formatted as `function_response` parts.
        """
        tool_response_parts: List[Dict[str, Any]] = []
        if not (
            response and response.candidates and response.candidates[0].content.parts
        ):
            return []

        function_calls = [
            p.function_call
            for p in response.candidates[0].content.parts
            if p.function_call
        ]
        for call in function_calls:
            tool_name = call.name
            tool_input = call.args
            print(f"--- Calling tool: {tool_name} with input: {tool_input} ---")
            try:
                tool_output = await client.call_tool(tool_name, tool_input)
                items = tool_output.content if tool_output else []
                output_content = json.dumps(
                    [item.text for item in items if isinstance(item, TextContent)]
                )
            except Exception as e:
                output_content = json.dumps(
                    {"error": f"Error executing tool '{tool_name}': {e}"}
                )
            tool_response_parts.append(
                {
                    "function_response": {
                        "name": tool_name,
                        "response": {"content": output_content},
                    }
                }
            )
        return tool_response_parts
