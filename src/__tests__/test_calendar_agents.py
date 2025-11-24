import os
import sys
import tempfile
import importlib
import json
import datetime

# Ensure src/ and repo root are on sys.path so imports in the module resolve
REPO_ROOT = os.getcwd()
SRC = os.path.join(REPO_ROOT, 'src')
PKG = os.path.join(SRC, 'multi_tool_agent')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if PKG not in sys.path:
    sys.path.insert(0, PKG)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def reload_calendar_module_with_db(db_path: str):
    """Set EVENTS_DB_PATH and import/reload the CalendarAgent module so it initializes the given DB."""
    os.environ['EVENTS_DB_PATH'] = db_path
    os.environ['INIT_EVENTS_DB'] = '1'
    # Ensure a fresh import: remove any loaded multi_tool_agent modules so that
    # CalendarAgent's top-level init runs against the test DB path.
    for k in list(sys.modules.keys()):
        # Remove any previously loaded package modules
        if k == 'multi_tool_agent' or k.startswith('multi_tool_agent.'):
            del sys.modules[k]
        # Also remove the top-level setup_events_db if it was imported as a plain module
        if k == 'setup_events_db':
            del sys.modules[k]
    mod = importlib.import_module('multi_tool_agent.CalendarAgent')
    return mod


def test_fetch_all_events_returns_inserted():
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    tf.close()
    db_path = tf.name
    try:
        mod = reload_calendar_module_with_db(db_path)

        # Insert two events via add_event_wrapper
        details1 = {
            'event_text': 'Dentist appointment',
            'category': 'Meeting',
            'start_date': None,
            'end_date': None,
            'is_recurring': False,
            'event_date': '2025-12-10',
            'recurrence_frequency': None,
            'event_type': 'Appointment',
            'event_details': 'Dental checkup'
        }
        details2 = {
            'event_text': 'Office holiday party',
            'category': 'Holiday',
            'start_date': None,
            'end_date': None,
            'is_recurring': False,
            'event_date': '2025-12-25',
            'recurrence_frequency': None,
            'event_type': 'Holiday',
            'event_details': 'Company party'
        }

        id1 = mod.add_event_wrapper(json.dumps(details1))
        id2 = mod.add_event_wrapper(json.dumps(details2))

        # Fetch all events (date=None) using module default DB so it matches add_event_wrapper
        rows = mod.fetch_date_events_wrapper(None)
        # Expect at least the two we inserted
        ids = [str(r[0]) for r in rows]
        print(f"db has following data :{ids}")
        fetch1 =[r for r in ids if r in id1]
        fetch2 =[r for r in ids if r in id2]
        assert(len(fetch1)>0)
        assert(len(fetch2)>0)
        

    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_event_storing_agent_add_event_wrapper_inserts_row():
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    tf.close()
    db_path = tf.name
    try:
        mod = reload_calendar_module_with_db(db_path)

        # Build a classification output as the agent would produce
        details = {
            'event_text': 'Team meeting to review Q4',
            'category': 'Meeting',
            'start_date': None,
            'end_date': None,
            'is_recurring': False,
            'event_date': '2025-11-20',
            'recurrence_frequency': None,
            'event_type': 'Meeting',
            'event_details': 'Discuss Q4 targets'
        }

        payload = json.dumps(details)
        # add_event_wrapper parses JSON and inserts into DB
        row = mod.add_event_wrapper(payload)
        assert(row!="Failed to add event.")


        # Verify the row is present using the module's fetch_date_events
        ev_date = datetime.date.fromisoformat(details['event_date'])
        rows = mod.fetch_date_events(ev_date)
        assert any( str(r['id']) in row for r in rows)
        matching = [r for r in rows if str(r['id']) in row]
        assert len(matching) == 1
        rec = matching[0]
        assert rec['event_type'] == 'Meeting'
        assert rec['event_details'] == 'Discuss Q4 targets'
        assert rec['event_date'] == ev_date

    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass
