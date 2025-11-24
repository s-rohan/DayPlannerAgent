
import os
import asyncio
from google.adk.agents import Agent,BaseAgent,SequentialAgent
import google.adk as adk
import json
from datetime import date, datetime
from .AgentConfig import base_model
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.adk.events.event_actions import EventActions
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator
from google.genai import types
from dotenv import load_dotenv
load_dotenv("../.env")  # Load environment variables from a .env file if present
from .setup_events_db import init_events_db, add_future_event,add_recurring_event,fetch_date_events,fetch_recurring_events
# Ensure the package-level logging configuration is applied
from . import logging_util as _pkg_logging
import logging
logger = logging.getLogger(__name__)
# Initialize events DB unless explicitly disabled
if os.getenv('INIT_EVENTS_DB', '1') not in ('0', 'false', 'False'):
  EVENTS_DB_PATH = os.getenv('EVENTS_DB_PATH', os.path.join(os.getcwd(), 'events_db.sqlite'))
  init_events_db(EVENTS_DB_PATH)
# --- Define Model Constants for easier use ---
AGENT_MODEL = os.getenv("MODEL_NAME")
prompt_template = """You are an event classification assistant. 
Your task is to read a short text describing an activity, occasion, or message, 
and classify it into one of the following categories:

- Birthday
- Anniversary
- Holiday (Christmas, New Year, Diwali, etc.)
- Shopping
- Meeting
- Festival
- Personal Greeting
- Work/Task
- Other

Rules:
1. Focus on the main intent of the text.
2. If the text mentions a birthday → Birthday.
3. If the text mentions an anniversary → Anniversary.
4. If the text mentions a holiday (Christmas, New Year, Diwali, etc.) → Holiday.
5. If the text is about buying, shopping, or purchasing → Shopping.
6. If the text is about a meeting, appointment, or scheduled gathering → Meeting.
7. If the text is about a cultural/religious festival → Festival.
8. If the text is a general greeting or well-wishing not tied to a birthday/holiday → Personal Greeting.
9. If the text is about work, tasks, or professional duties → Work/Task.
10. If none of the above apply → Other.
11. If a date is mentioned in the text, extract it in YYYY-MM-DD format; otherwise, return null for the date.
12.Determine if the event is recurring or one-time based on the text. If recurring, specify the frequency (e.g., daily, weekly, monthly, yearly).
15.Present output in JSON format as follows:
Output format: 
{
  "event_text": "<original input text>",
  "category": "<one of the categories above>",
  "start_date": "<YYYY-MM-DD if present, else null>",
  "end_date": "<YYYY-MM-DD if present for recurring events, else null>",
  "is_recurring": "<True/False>",
  "event_date": "<YYYY-MM-DD if present, else null>",
  "recurrence_frequency": "<if recurring, specify frequency like daily, weekly, monthly, yearly; else null>"
}

"""
event_fetching_prompt = """
You are a calendar assistant that retrieves events for a specific date.
Given a date in YYYY-MM-DD format, fetch all events scheduled for that date from the database.
You have two types of events to consider: one-time events and recurring events.
When fetching events, follow these steps:
1. Query the one-time events table for events matching the given date.
2. Query the recurring events table for events that recur on the given date based on their frequency.
3. Combine the results from both queries.
4.Summarize the Output and present in text format as follows:
Dont show date if event_details is null or Details is empty.
- If events are found, list them under the date header.
- For one-time events, use the following format.
  Event Date: <event_date>
  - Event Type: <event_type>  
    - Details: <event_details>
- For recurring events, Analyse each event's frequency and determine if it occurs on the given date.
  - If it does, use the following format:
    Recurring Event (Frequency: <event_frequency>)
    - Event Date: <event_date>
    - Event Type: <event_type>
      - Details: <event_details>
5.If no events are found , return "No Events are present for this period".
"""
class StoreEvent(BaseAgent):
  async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
     json_details = ctx.session.state.get("event_classification_response")
     # Call your Python function with that value
     cleaned = clean_json_block(json_details)
     logger.info(f"Storing event with details: {cleaned}")
     result = add_event_wrapper(cleaned)
        
        # Yield the result back into the agent system
     yield Event(
    author=self.name,
    content=types.Content(role='user', parts=[types.Part(text=result)]),
    actions=EventActions()
  )


import json
import re

def clean_json_block(raw: str) -> str:
    # Remove triple backticks and optional language tag
    return re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()


     
def add_event_wrapper(details)-> str:
    """Wrapper for add_future_event to be used as a tool in the agent."""
    if not details or not details.strip():
        raise ValueError("Empty or missing event details")

    try:
      logger.debug(f"Adding event with details: {details}")
      dict=json.loads(details)
      event_date=dict.get("event_date",None)
      event_date=datetime.strptime(event_date,"%Y-%m-%d").date() if event_date else None
      event_type=dict.get("event_type")
      if not event_type:
          event_type=dict.get("category","Other")
      event_details=dict.get("event_details",None)
      if not event_details:
          event_details=dict.get("event_text")
      is_recurring=dict.get("is_recurring",False)
      if is_recurring==True:
          logger.debug("Event is recurring, adding to recurring_events table")
          # For recurring events, we might need additional fields like frequency and end_date
          recurrence_frequency=dict.get("recurrence_frequency",None)
          end_date=dict.get("end_date",None)
          end_date=datetime.strptime(end_date,"%Y-%m-%d").date() if end_date else None
          logger.debug(f"Before call to db :Recurrence frequency: {recurrence_frequency}, End date: {end_date}")
          row_id=add_recurring_event(recurrence_frequency,event_date,event_type,event_details,end_date)
          if row_id>0:
            return f"Recurring event added with id {row_id}"
      else:
        logger.debug("Event is one-time, adding to future_events table")
        row_id= add_future_event(event_date, event_type, event_details)
        if row_id>0:
            return f"One-time event added with id {row_id}"
    except Exception as e:
        logger.error(f"Error adding event:", exc_info=True)
    return "Failed to add event."
      
      

def get_event_classifier_agent():
    return Agent(
        model=base_model,
        name="calendar_agent",
        description="An agent that helps manage calendar events.IT takes the event and provide details about it.Is the event recurring or one time.Is the date fixed or variable.It classifies the event.as Anniversery,Festiwal,Work etc " \
        "",
        instruction=prompt_template,
        output_key="event_classification_response",

    ) 
def get_event_asisstant_agent():
    return Agent(
    model=base_model,
    name="calendar_assisstant",
    description="This agents provides the calendar details for the specific date",
    instruction=event_fetching_prompt,
    tools=[FunctionTool(fetch_date_events_wrapper),FunctionTool(fetch_recurring_events_wrapper)],
    output_key="event_fetching_response",

)
def fetch_date_events_wrapper(date_param:str) -> json:
    """Fetch events for a specific date (datetime.date or YYYY-MM-DD string) or all events if date is None.

    Returns json object in following format  {event_date :[{events_by_type:{event_type:[{event_date,event_details}]}}]
    """
    ret=fetch_date_events(date_param)
    if not ret or len(ret)==0:
        return {"event_date":date_param,"events_by_type":{}}
    else:
        events_by_type={}
        for r in ret:
            etype=r.get("event_type")
            edetails=r.get("event_details")
            edate=r.get("event_date")
            event_record={"event_date":edate,"event_details":edetails}
            if etype in events_by_type:
                events_by_type[etype].append(event_record)
            else:
                events_by_type[etype]=[event_record]
        return json.dumps({"event_date":date_param,"events_by_type":events_by_type},default=safe_json)
def fetch_recurring_events_wrapper(start_date:str,end_date:str) -> json:
    """Fetch recurring events between start_date in YYYY-MM-DD format and end_date in YYYY-MM-DD format.

    Returns json object in following format  {recurring_events :[{id,event_frequency,event_start_date,event_type,event_details,event_end_date}]}
    """
    ret=fetch_recurring_events(start_date,end_date)
    if not ret or len(ret)==0:
        return {"recurring_events":[]}
    else:
        return json.dumps({"recurring_events":ret},default=safe_json) 
    
def safe_json(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, datetime):
        # Return only the date part in ISO format
        return obj.date().isoformat()   # "YYYY-MM-DD"
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    if isinstance(obj, (Exception,str)):
        return str(obj)

    raise TypeError(f"Type {type(obj)} not serializable")
def get_event_aggregator_agent():
    return Agent(
        model=base_model,
        name="event_aggregator_agent",
        description="An agent that aggregates events published by StoreEvent agent.",  # Description of the agent's purpose
        instruction="""Summarize all events created by Agents sharing the same Parent as You .
        Provide a concise summary.
        """,
        output_key="event_aggregation_response",

    )

def get_event_storing_agent():
    return SequentialAgent(
   name="event_storing_agent",
   description="An agent that classifies and stores calendar events into the database.",
   sub_agents=[get_event_classifier_agent(),StoreEvent(name="StoreEvent"),get_event_aggregator_agent()],)
   