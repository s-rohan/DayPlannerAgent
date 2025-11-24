import os
import uuid
import asyncio
from google.adk.agents import Agent,SequentialAgent,ParallelAgent
from google.adk.tools import google_search
from .AgentConfig import AGENT_MODEL
from .MultiAgent import get_flow_agent
from google.adk.runners import Runner,InMemoryRunner
from dotenv import load_dotenv
from google.adk.sessions.database_session_service import DatabaseSessionService
load_dotenv("../.env")  # Load environment variables from a .env file if present
from google.genai import types # For creating message Content/Parts

import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

from . import logging_util as _pkg_logging
import logging
logger = logging.getLogger(__name__)
logger.info("Libraries imported.")

USER_ID = "user_1"
SESSION_ID = str(uuid.uuid4())
logger.info("Session id: %s", SESSION_ID)
# Define constants for identifying the interaction context
APP_NAME = os.getenv("APP_NAME", "agents")



# Path to SQLite database file
DB_PATH = os.getenv("session_DB_PATH", "sessions_db.sqlite")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
session_service = DatabaseSessionService(
        db_url=f"sqlite:///{DB_PATH}"  # SQLAlchemy-style URL
    )

async def run_session(
    runner_instance: Runner,
    user_queries: list[str] | str = None,
    session_name: str=SESSION_ID,
):
    logger.info("\n ### Session: %s", session_name)

    # Get app name from the Runner
    app_name = runner_instance.app_name

    # Attempt to create a new session or retrieve an existing one
    try:
        session = await session_service.create_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
    except:
        session = await session_service.get_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )

    # Process queries if provided
    if user_queries:
        # Convert single query to list for uniform processing
        if type(user_queries) == str:
            user_queries = [user_queries]

        # Process each query in the list sequentially
        for query in user_queries:
            logger.info("\nUser > %s", query)

            # Convert the query string to the ADK Content format
            query = types.Content(role="user", parts=[types.Part(text=query)])

            # Stream the agent's response asynchronously
            async for event in runner_instance.run_async(
                user_id=USER_ID, session_id=session.id, new_message=query
            ):
                # Check if the event contains valid content
                if event.content and event.content.parts:
                    # Filter out empty or "None" responses before printing
                    if (
                        event.content.parts[0].text != "None"
                        and event.content.parts[0].text
                    ):
                        logger.info("%s > %s", AGENT_MODEL, event.content.parts[0].text)
                else:
                    logger.info("No content in event.")
    else:
        logger.info("No queries!")



async def call_agent_async(query: str, runner, user_id, session):
    """Sends a query to the agent and logs the final response."""
    logger.info("\n>>> User Query: %s", query)

    # Prepare the user's message in ADK format
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."  # Default

    # Key Concept: run_async executes the agent logic and yields Events.
    # We iterate through events to find the final answer.
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=content):
        # You can uncomment the line below to see *all* events during execution
        logger.info(
            "  [Event] Author: %s, Type: %s, Final: %s, Content: %s",
            event.author,
            type(event).__name__,
            event.is_final_response(),
            event.content,
        )

        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response() :
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif getattr(event, 'actions', None) and getattr(event.actions, 'escalate', None):
                # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {getattr(event, 'error_message', 'No specific message.')}"
            # Add more checks here if needed (e.g., specific error codes)
            break  # Stop processing events once the final response is found

    logger.info("<<< Agent Response: %s", final_response_text)

  # @title Run the Initial Conversation

# We need an async function to await our interaction helper


#runner = Runner(agent= get_flow_agent(), app_name=APP_NAME, session_service=session_service)



runner=InMemoryRunner(agent= get_flow_agent(), app_name=APP_NAME)  
async def run_conversation(runner, session):
    text=[
        "What are my events for 15 Dec 2025?",
    ]
    #run_session(runner, text, session_name="event_mgmt_session")
    logger.info("Starting conversation run...")
    #res=await run_session(runner, text, session_name="event_mgmt_session")
    for t in text:
        #await call_agent_async(t,runner,USER_ID,session)
        response=await runner.run_debug(t)
        logger.info("Response: %s", response)

  
    
if __name__ == "__main__":
    import atexit

    async def _cleanup_async():
        """Attempt to close common async resources gracefully.

        Looks for `runner`, `session_service`, and `session` in globals and
        calls `.aclose()` or `.close()` where available. This helps avoid
        unclosed aiohttp ClientSession/connector warnings.
        """
        names = ("session", "session_service" ,"runner")
        for name in names:
            obj = globals().get(name)
            if obj is None:
                continue
            try:
                # Prefer an async aclose()
                if hasattr(obj, "aclose"):
                    res = obj.aclose()
                    if asyncio.iscoroutine(res):
                        await res
                    logger.info("Closed (aclose) %s", name)
                elif hasattr(obj, "close"):
                    res = obj.close()
                    if asyncio.iscoroutine(res):
                        await res
                    logger.info("Closed (close) %s", name)
            except Exception as e:
                logger.exception("Error closing %s: %s", name, e)

    def _cleanup_sync():
        try:
            asyncio.run(_cleanup_async())
        except Exception as e:
            # Nothing more we can do here; just log
            logger.exception("Cleanup failed: %s", e)

    # Register an exit handler to ensure resources are closed even if the
    # process is terminated normally.
    atexit.register(_cleanup_sync)

    try:
        _runner = globals().get('runner')
        _session = globals().get('session')
        if _session is None:
                _session=asyncio.run(session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID))
                if _session is None:
                    _session = asyncio.run(
                    session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
            )
        if _runner is not None:
            asyncio.run(run_conversation(_runner, _session))
        else:
            logger.warning("Runner not initialized; skipping conversation run.")
    except Exception as e:
        logger.exception("An error occurred: %s", e)
    finally:
        # Best effort final cleanup to close any lingering async resources
        try:
            asyncio.run(_cleanup_async())
        except Exception as e:
            logger.exception("Final cleanup failed: %s", e)