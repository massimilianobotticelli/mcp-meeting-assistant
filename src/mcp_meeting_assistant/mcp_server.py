"""
This module defines a FastMCP server for managing meetings,
including scheduling, adding attendees, action items, and generating summaries.
It uses the MCP framework to create a structured server with tools and prompts.
It is designed to be run as a standalone server application.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

# --- 1. Server Initialization with System Prompt ---
mcp = FastMCP(
    "MeetingAssistantMCP",
    log_level="INFO",
    title="A Meeting Assistant",
    description=(
        "You are an efficient meeting assistant. Your job is to help users schedule meetings, "
        "add attendees, record action items, and generate summaries. "
        "Always refer to meetings by their unique topic."
    ),
)

# --- 2. In-Memory Data Store ---
# A dictionary to hold meeting data. The structure is:
# { "meeting_topic": {"attendees": [...], "action_items": [...]}}
meetings: dict[str, dict] = {}


# --- 3. Tool Definitions with Decorators ---


@mcp.tool()
def schedule_meeting(
    topic: str = Field(description="The unique topic or title of the meeting."),
):
    """Schedules a new, empty meeting with a given topic."""
    print(f"Executing: schedule_meeting for topic '{topic}'")
    if topic in meetings:
        return f"Error: A meeting with the topic '{topic}' already exists."

    meetings[topic] = {"attendees": [], "action_items": []}
    return f"Successfully scheduled new meeting: '{topic}'"


@mcp.tool()
def add_attendee(
    topic: str = Field(description="The topic of the meeting to add an attendee to."),
    name: str = Field(description="The name of the person attending the meeting."),
):
    """Adds an attendee to a specific meeting."""
    print(f"Executing: add_attendee '{name}' to '{topic}'")
    if topic not in meetings:
        return f"Error: Meeting '{topic}' not found."

    meetings[topic]["attendees"].append(name)
    return f"Successfully added attendee '{name}' to meeting '{topic}'."


@mcp.tool()
def add_action_item(
    topic: str = Field(description="The topic of the meeting for the action item."),
    item: str = Field(description="The description of the action item."),
):
    """Adds an action item to a specific meeting."""
    print(f"Executing: add_action_item '{item}' for '{topic}'")
    if topic not in meetings:
        return f"Error: Meeting '{topic}' not found."

    meetings[topic]["action_items"].append(item)
    return f"Successfully added action item to meeting '{topic}': '{item}'"


@mcp.tool()
def get_meeting_details(
    topic: str = Field(description="The topic of the meeting to get details for."),
):
    """Retrieves the attendees and action items for a specific meeting."""
    print(f"Executing: get_meeting_details for '{topic}'")
    if topic not in meetings:
        return f"Error: Meeting '{topic}' not found."

    details = meetings[topic]
    attendees = ", ".join(details["attendees"]) if details["attendees"] else "None"

    if not details["action_items"]:
        action_items_formatted = "No action items."
    else:
        action_items_formatted = "\n".join(
            f"- {item}" for item in details["action_items"]
        )

    return (
        f"Details for meeting '{topic}':\n"
        f"Attendees: {attendees}\n"
        f"Action Items:\n{action_items_formatted}"
    )


@mcp.tool()
def list_all_meetings():
    """Lists the topics of all currently scheduled meetings."""
    print("Executing: list_all_meetings")
    if not meetings:
        return "There are no meetings scheduled at the moment."

    meeting_topics = meetings.keys()

    # Return a simple list of topics for the model to process
    return "\n".join(list(meeting_topics))


# --- 4. Prompt Definitions ---


@mcp.prompt(
    name="minutes",
    description="Generate meeting minutes from the details.",
)
def generate_minutes():
    """Generates formatted meeting minutes for a specific meeting."""
    prompt = """
    Your goal is to create and present the meeting minutes.
    First, you may need to ask the user which meeting they want a summary for.
    Then, use the 'get_meeting_details' tool with the correct meeting topic.
    Finally, present the retrieved details back to the user in a clean, readable format
    under the heading 'Meeting Minutes for: [Topic]'.
    """
    return [base.UserMessage(prompt)]


@mcp.prompt(
    name="kickoff",
    description="Plan a new project kickoff meeting.",
)
def plan_project_kickoff():
    """Sets up a standard project kickoff meeting with initial attendees and tasks."""
    prompt = """
    Your goal is to automate the setup for a new project kickoff meeting.
    1. Ask the user for the project name to use as the meeting topic.
    2. Use the 'schedule_meeting' tool to create the meeting.
    3. Use the 'add_attendee' tool to add 'Project Manager' and 'Lead Engineer' as attendees.
    4. Use the 'add_action_item' tool to add an initial task: 'Finalize project scope and charter.'
    5. Confirm to the user that the kickoff meeting has been set up with the initial details.
    """
    return [base.UserMessage(prompt)]


@mcp.prompt(
    name="format",
    description="Format all meetings into a markdown report.",
)
def format_meetings_as_markdown():
    """
    Retrieves all meetings and their details and formats them as a
    comprehensive Markdown report.
    """
    prompt = """
    Your goal is to create a comprehensive Markdown report of all scheduled meetings.
    1. First, call the 'list_all_meetings' tool to get the list of all meeting topics.
    2. If there are no meetings, inform the user that the list is empty.
    3. For each meeting topic in the list, you must then call the 'get_meeting_details' tool
       to fetch its specific attendees and action items.
    4. After gathering all the details for all meetings, format the entire output as a single Markdown document.
    5. The document should start with a main heading: '# Meeting Report'.
    6. Each meeting should be its own sub-section with a level 2 heading, like '## Meeting: [Topic]'.
    7. Under each meeting, list the 'Attendees' and 'Action Items' with bullet points.
    """
    return [base.UserMessage(prompt)]


@mcp.prompt(
    name="demo",
    description="Populate the server with random meeting data for a demo.",
)
def populate_demo_data():
    """
    Guides the model to populate the meeting list with sample data for demonstration purposes.
    """
    prompt = """
    Your goal is to populate the application with realistic demo data.
    You must perform the following actions in sequence:

    1.  **Create Meetings:**
        * Call `schedule_meeting` with the topic "Q3 Financial Review".
        * Call `schedule_meeting` with the topic "Project Alpha Sync".
        * Call `schedule_meeting` with the topic "Marketing Brainstorm".

    2.  **Add Details for "Q3 Financial Review":**
        * Call `add_attendee` with topic "Q3 Financial Review" and name "Alice".
        * Call `add_attendee` with topic "Q3 Financial Review" and name "Bob".
        * Call `add_action_item` with topic "Q3 Financial Review" and item "Finalize revenue report".

    3.  **Add Details for "Project Alpha Sync":**
        * Call `add_attendee` with topic "Project Alpha Sync" and name "Charlie".
        * Call `add_attendee` with topic "Project Alpha Sync" and name "Dana".
        * Call `add_action_item` with topic "Project Alpha Sync" and item "Update project timeline".
        * Call `add_action_item` with topic "Project Alpha Sync" and item "Resolve blocking issue #123".

    4.  **Add Details for "Marketing Brainstorm":**
        * Call `add_attendee` with topic "Marketing Brainstorm" and name "Eve".
        * Call `add_action_item` with topic "Marketing Brainstorm" and item "Draft new ad campaign slogans".

    5.  **Confirmation:**
        * After all tool calls are complete, respond to the user with a single message: "Demo data has been successfully created."
    """
    return [base.UserMessage(prompt)]


# --- 5. Run the Server ---
if __name__ == "__main__":
    mcp.run()
