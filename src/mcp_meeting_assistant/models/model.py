"""
This module defines the abstract base class for model wrappers used in the MCP Meeting Assistant.
It provides a common interface for different model implementations, ensuring consistency in method signatures
and functionality across various models.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from google.generativeai.types import GenerateContentResponse

from mcp_meeting_assistant.mcp_client import MCPClient


class Model(ABC):
    """
    Abstract base class for all model wrappers.
    """

    @abstractmethod
    def ask(self, question: str, messages_history: List[Dict[str, Any]]) -> str:
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[GenerateContentResponse]:
        pass

    @abstractmethod
    def add_message_to_history(
        self, messages: List[Dict[str, Any]], message: Dict[str, Any]
    ) -> None:
        pass

    @abstractmethod
    def text_from_message(self, response: Optional[GenerateContentResponse]) -> str:
        pass

    @abstractmethod
    async def get_tools(self, client: MCPClient) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def execute_tool_requests(
        self, client: MCPClient, response: Optional[GenerateContentResponse]
    ) -> List[Dict[str, Any]]:
        pass
