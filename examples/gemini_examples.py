import os
import json
from dotenv import load_dotenv
from mcp_meeting_assistant.models.gemini import Gemini

# --- Setup ---
load_dotenv()
model = Gemini(model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
messages = []

# --- First Question ---
print("------ First Question ------")
question = "What is the capital of Germany?"

text = model.ask(question, messages)

print("Question:", question)
print("Response:", text)


# --- Second Question (With Conversational Context) ---
print("\n------ Second Question ------")
question = "What about for France?"

text = model.ask(question, messages)

print("Question:", question)
print("Response:", text)


# --- Summary ---
print("\n------ Final Conversation History ------")
print(json.dumps(messages, indent=2))
