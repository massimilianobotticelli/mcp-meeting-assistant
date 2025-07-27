from typing import Any, List, Dict
from mcp_meeting_assistant.mcp_client import MCPClient

class ChatSession:
    """
    Manages an interactive chat session between a user and the Gemini model,
    orchestrating calls to the MCP server for tools and prompts.
    """

    def __init__(self, llm_service: Any, mcp_client: MCPClient):
        """
        Initializes the ChatSession.

        Args:
            llm_service: An object responsible for interfacing with the Gemini API.
            mcp_client: A client for interacting with the MCP server.
        """
        self.llm_service: Any = llm_service
        self.mcp_client: MCPClient = mcp_client
        self.history: List[Dict[str, Any]] = []

    def _add_valid_model_response(self, response: Any, messages: List[Dict[str, Any]]) -> None:
        """
        Validates a model response and adds its content to a message list.
        This prevents "history poisoning" from empty or malformed responses.

        Args:
            response: The response object from the generative model.
            messages: The list of messages for the current turn to append to.
        """
        if response and response.candidates and response.candidates[0].content.parts:
            self.llm_service.add_message_to_history(
                messages, response.candidates[0].content
            )

    async def run(self) -> None:
        """
        Starts and manages the main interactive chat loop.
        """
        try:
            prompts: List[str] = await self.mcp_client.list_prompts()
            prompts_str: str = ", ".join(f"/{p}" for p in prompts)
            print(f"💡 Tip: Use slash commands (e.g., {prompts_str})")
        except Exception as e:
            print(f"Could not fetch prompts: {e}")
            
        while True:
            user_input: str = input("> ")
            if user_input.lower() == "exit":
                break

            messages_for_this_turn: List[Dict[str, Any]] = list(self.history)

            # Handle user input (slash command or regular message)
            if user_input.startswith("/"):
                parts: List[str] = user_input[1:].strip().split()
                prompt_name: str = parts[0]
                user_follow_up_text: str = " ".join(parts[1:])

                print(f"--- Running prompt: {prompt_name} ---")
                try:
                    prompt_content: str = await self.mcp_client.run_prompt(prompt_name, {})
                    if prompt_content:
                        full_user_message: str = f"{prompt_content}\n\n{user_follow_up_text}".strip()
                        self.llm_service.add_message_to_history(
                            messages_for_this_turn,
                            {"role": "user", "parts": [{"text": full_user_message}]}
                        )
                except Exception as e:
                    print(f"Error running prompt: {e}")
                    continue
            else:
                self.llm_service.add_message_to_history(
                    messages_for_this_turn,
                    {"role": "user", "parts": [{"text": user_input}]}
                )

            # --- Main Conversational Flow ---
            
            available_tools: List[Dict[str, Any]] = await self.llm_service.get_tools(self.mcp_client)
            response: Any = self.llm_service.chat(messages=messages_for_this_turn, tools=available_tools)
            
            # If the chat call failed (e.g., 500 error), skip the rest of the loop.
            if response is None:
                continue
            
            self._add_valid_model_response(response, messages_for_this_turn)
            
            tool_results: List[Dict[str, Any]] = await self.llm_service.execute_tool_requests(self.mcp_client, response)

            if tool_results:
                self.llm_service.add_message_to_history(
                    messages_for_this_turn,
                    {"role": "tool", "parts": tool_results}
                )
                final_response_obj: Any = self.llm_service.chat(messages=messages_for_this_turn)
                
                # If the final chat call failed, skip the rest of the loop.
                if final_response_obj is None:
                    continue

                self._add_valid_model_response(final_response_obj, messages_for_this_turn)
                final_text: str = self.llm_service.text_from_message(final_response_obj)
            else:
                final_text: str = self.llm_service.text_from_message(response)
            
            # If the flow was successful, update the permanent history
            self.history = messages_for_this_turn
            
            # Final check to ensure the user gets a meaningful response.
            if not final_text.strip():
                print("\nℹ️ The model did not provide a response. This might be due to content safety filters. Please try rephrasing your request.")
            else:
                print(f"{final_text}")
