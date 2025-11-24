import os
import sys
import tempfile
import datetime

REPO_ROOT = os.getcwd()
SRC = os.path.join(REPO_ROOT, 'src')
PKG = os.path.join(SRC, 'multi_tool_agent')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from multi_tool_agent import setup_events_db as db


def test_init_and_insert_and_fetch():
    # create a temporary sqlite file
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    tf.close()
    db_path = tf.name

    try:
        # initialize the DB and table
        returned = db.init_events_db(db_path)
        assert os.path.exists(returned)

        # insert an event using a date object
        ev_date = datetime.date(2025, 12, 1)
        rowid = db.add_future_event(ev_date, 'Shopping', 'Buy groceries', db_path=db_path)
        assert isinstance(rowid, int) and rowid > 0

        # fetch by date (should return at least the event we inserted)
        events = db.fetch_date_events(ev_date, db_path=db_path)
        assert len(events) >= 1
        found = False
        for e in events:
            assert 'id' in e and 'event_date' in e and 'event_type' in e and 'event_details' in e
            if e['id'] == rowid:
                found = True
                assert e['event_type'] == 'Shopping'
                assert e['event_details'] == 'Buy groceries'
                assert isinstance(e['event_date'], datetime.date)
                assert e['event_date'] == ev_date
        assert found

        # insert an event with no date
        row2 = db.add_future_event(None, 'Other', 'No date event', db_path=db_path)
        assert isinstance(row2, int) and row2 > 0


    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass
