# @title Import necessary libraries
import os
import uuid
import asyncio
from google.adk.agents import Agent,SequentialAgent,ParallelAgent
from google.adk.tools import google_search

from google.adk.runners import Runner,InMemoryRunner
from dotenv import load_dotenv

from .AgentConfig import base_model
from .CalendarAgent import get_event_storing_agent,get_event_asisstant_agent
load_dotenv("../.env")  # Load environment variables from a .env file if present
from google.genai import types # For creating message Content/Parts

import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

from . import logging_util as _pkg_logging
import logging
logger = logging.getLogger(__name__)
logger.info("Libraries imported.")
# Keep external package verbosity lower
logging.getLogger("google.adk").setLevel(logging.INFO)
# Gemini API Key (Get from Google AI Studio: https://aistudio.google.com/app/apikey)
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_ADK_API_KEY") # <--- REPLACE
# --- Verify Keys (Optional Check) ---
logger.info("API Keys Set:")
logger.info("Google API Key set: %s", 'Yes' if os.environ.get('GOOGLE_API_KEY') and os.environ['GOOGLE_API_KEY'] != 'YOUR_GOOGLE_API_KEY' else 'No (REPLACE PLACEHOLDER!)')

# Configure ADK to use API keys directly (not Vertex AI for this multi-model setup)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"







# @title Define Agent Interaction Function

from google.genai import types # For creating message Content/Parts

# Define helper functions that will be reused throughout the notebook

instruction= """You are a Routing Manager Agent .Your task is to help users manage their calendar events. 
If user_task_response in state is store_event or store_and_fetch,
You will Route request to event_storing_agent to classify and store events.
If user_task_response in state is fetch_event or store_and_fetch,
You will Route request to calendar_assisstant to fetch events for specific dates.
You will Route request to calendar_assisstant to fetch events for specific dates.
Here are the sub agents you can use:
event_storing_agent: An agent that classifies events into categories and determines if they are one-time or recurring.
calendar_assisstant: An agent that provides calendar details for a specific date.
Rules:
1.If the date or date range is in the past,reply that the event is in the past and cannot be fetched.
2.If storing events,ensure to capture the event details,type,date(if provided),and recurrence information.
3.If the User asks for events for a period like a week or month,use calendar_assisstant tool to fetch events for each date in that period and consolidate the results.
4.If No event are found reply with No events found for the given date.
Output Format: 
{
   [ "date": "<YYYY-MM-DD>",
  "events_by_type": {
    "<event_type>": [
      {
        "id": <event_id>,
        "event_date": "<YYYY-MM-DD>",
        "event_details": "<details>"
      },
      ]
      }
    ]
    """

date_determination_prompt="""
You are a helpful assistant that determines dates. Given a user query about calendar events, identify the specific date or date range mentioned.
Rules:
-PLease follow the below rules strictly:
-The date range should always be greated or equal to today's date.
-Classify if The event is a single date or a date range.
-Identify dates mentioned in various formats (e.g., "next Monday", "December 25th", "from Jan 1 to Jan 7").
-Consider relative dates based on the current date (e.g., "tomorrow", "next week").
-If it is a festival or holiday,event date should be that of the festival/holiday.
-You can use tool only to determine the date using following query ."What is the date for New Year 2025?"
-You cannot fetch events using the tool.

Output the result in JSON format as follows:
{
    
    "tool_code:"Yes",
    "date": "<YYYY-MM-DD if single date>",
    "start_date": "<YYYY-MM-DD if date range>",
    "end_date": "<YYYY-MM-DD if date range>"
"""
def get_date_determination_agent():
    """It returns date determination agent which can take text and return date or date range."""
    mod = Agent(
    model=base_model,
    name="date_determination_agent",
    description="An agent that identifies specific dates or date ranges from user queries about calendar events.",
    instruction=date_determination_prompt,
    tools=[google_search],
    output_key="date_determination_response",
)
    return mod
def get_User_Task_Agent():
    userAgent=Agent(
    model=base_model,
    name="user_task_agent",
    description="An agent that helpsto classify user task as storing event or fetching event or both ",
    output_key="user_task_response",
    instruction="""You are a helpful assistant that classifies user tasks related to calendar events.
Given a user query about calendar events, determine whether the user wants to store a new event, fetch existing events, or both.
Rules:
1. If the user query includes details about a new event (e.g., event description, date, recurrence), classify it as "store_event".
2. If the user query requests information about existing events (e.g., "What events do I have on...?", "List my events for..."), classify it as "fetch_event".
3. If the user query includes both storing and fetching requests, classify it as "store_and_fetch".
Output the result in Tools format as follows:
{   
    "tool_code:"Yes",
    "task_type": "<store_event | fetch_event | store_and_fetch>"
}
"""
)
    return userAgent
def get_Parallel_agent():
    return ParallelAgent(
    name="user_task_date_determination_agent",
    sub_agents=[get_User_Task_Agent(),get_date_determination_agent()],
)

manager_agent = Agent(
    model=base_model,
    name="Manager_Agent",
    description="A text chatbot helps user with events management.It aggregates and prepare date for final summary",  # Description of the agent's purpose
    instruction=instruction,
    output_key="root_agent_response",
    sub_agents=[get_event_storing_agent(),get_event_asisstant_agent()],
    

)
def get_Summary_agent():
    return Agent(
        model=base_model,
        name="Summary_Agent",
        description="An agent that summarizes the events fetched for the user",  # Description of the agent's purpose
        instruction=""" You are a helpful assistant that summarizes calendar events for the user.
        Your task is to  evalaute Evaluate root_agent_response,event_aggregation_response and event_fetching_response if present.
         Provide a concise summary of the events.
        """,
        output_key="root_agent_response",
        )
def get_flow_agent():
    return SequentialAgent(
        name="multi_tool_manager_agent",
        description="A text chatbot helps user with events management",  # Description of the agent's purpose
        sub_agents=[get_Parallel_agent(),manager_agent,get_Summary_agent()],
    )







  