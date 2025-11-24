import sqlite3
import os
from . import logging_util as _pkg_logging
import logging
from datetime import date, datetime
from dotenv import load_dotenv
load_dotenv("../.env")  # Load environment variables from a .env file if present
logger = logging.getLogger(__name__)

DEFAULT_DB = os.getenv('EVENTS_DB_PATH', os.path.join(os.getcwd(), 'events_db.sqlite'))

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS future_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date DATE,
    event_type TEXT,
    event_details TEXT
);
'''
CREATE_TABLE_RECURRING_SQL = '''
CREATE TABLE IF NOT EXISTS recurring_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event_frequency TEXT NOT NULL,
 event_start_date DATE NOT NULL,
 event_type TEXT NOT NULL, 
 event_details TEXT,
 event_end_date DATE
);
'''
def init_events_db(db_path: str | None = None) -> str:
    """Create the SQLite database and  tables if not present.

    Returns the path to the database file.
    """
    db_path = db_path or DEFAULT_DB
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(CREATE_TABLE_SQL)
        cur.execute(CREATE_TABLE_RECURRING_SQL)
        conn.commit()
        logger.info('Initialized events DB at %s', db_path)
    finally:
        conn.close()
    return db_path

def add_recurring_event(event_frequency: str, event_start_date: date | str, event_type: str, event_details: str | None = None, event_end_date: date | str | None = None, db_path: str | None = None) -> int:
    """Insert a row into the recurring_events table.

    Returns the inserted row id.
    """
    db_path, conn = getConnection(db_path)
    try:
        cur = conn.cursor()
        # Accept datetime.date/datetime objects or strings. Store as ISO YYYY-MM-DD
        logger.debug(f"Adding recurring event: freq={event_frequency}, start_date={event_start_date}, type={event_type}, end_date={event_end_date} ,event_details={event_details}")    
        if isinstance(event_start_date, datetime):
            start_date_str = event_start_date.date().isoformat()
        elif isinstance(event_start_date, date):
            start_date_str = event_start_date.isoformat()
        else:
            # assume string-like
            start_date_str = str(event_start_date)

        if event_end_date is not None:
            if isinstance(event_end_date, datetime):
                end_date_str = event_end_date.date().isoformat()
            elif isinstance(event_end_date, date):
                end_date_str = event_end_date.isoformat()
            else:
                end_date_str = str(event_end_date)
        else:
            end_date_str = None

        cur.execute(
            "INSERT INTO recurring_events (event_frequency, event_start_date, event_type, event_details, event_end_date) VALUES (?, ?, ?, ?, ?)",
            (event_frequency, start_date_str, event_type, event_details, end_date_str),
        )
        conn.commit()
        rowid = cur.lastrowid
        logger.info('Inserted recurring event id %s into %s', rowid, db_path)
        return rowid
    except Exception as e:
        logger.error('Error inserting recurring event into %s: %s', db_path, e.with_traceback())
        raise e
    finally:
        conn.close()    
    
def fetch_recurring_events(start_date:str,end_date:str) -> list[dict]:
    """Fetch recurring events between start_date in YYYY-MM-DD format and end_date in YYYY-MM-DD format.

    Returns a list of dictionaries with keys: id, event_frequency, event_start_date, event_type, event_details, event_end_date.
    """
    db_path, conn = getConnection(None)
    try:
        cur = conn.cursor()
        # accept date object or string
        if start_date is None:
            start_date=datetime.now().date()
        if end_date is None:
            end_date=datetime.now().date()

        if isinstance(start_date, datetime):
            start_date_str = start_date.date().isoformat()
        elif isinstance(start_date, date):
            start_date_str = start_date.isoformat()
        else:
            start_date_str = str(start_date)

        if isinstance(end_date, datetime):
            end_date_str = end_date.date().isoformat()
        elif isinstance(end_date, date):
            end_date_str = end_date.isoformat()
        else:
            end_date_str = str(end_date)

        cur.execute("SELECT id, event_frequency, event_start_date, event_type, event_details, event_end_date FROM recurring_events WHERE event_start_date <= ? AND (event_end_date IS NULL OR event_end_date >= ?) ORDER BY event_start_date, id", (end_date_str, start_date_str))
        rows = cur.fetchall()

        result = []
        for r in rows:
            # convert stored date strings back to date objects when possible
            start_stored = r[2]
            end_stored = r[5]
            try:
                stored_start_date = datetime.strptime(start_stored, "%Y-%m-%d").date()
            except Exception:
                stored_start_date = start_stored
            if end_stored is None:
                stored_end_date = None
            else:
                try:
                    stored_end_date = datetime.strptime(end_stored, "%Y-%m-%d").date()
                except Exception:
                    stored_end_date = end_stored

            result.append({
                'id': r[0],
                'event_frequency': r[1],
                'event_start_date': stored_start_date,
                'event_type': r[3],
                'event_details': r[4],
                'event_end_date': stored_end_date,
            })
        logger.info('Fetched %d recurring events from %s between %s and %s', len(result), db_path, start_date, end_date)
        return result
    except Exception as e:
        logger.error('Error fetching recurring events from %s: %s', db_path, e.with_traceback())
        raise e 
    finally:
        conn.close()



def add_future_event(event_date: date | str | None, event_type: str, event_details: str | None = None, db_path: str | None = None) -> int:
    """Insert a row into the future_events table.

    Returns the inserted row id.
    """
    db_path, conn = getConnection(db_path)
    try:
        cur = conn.cursor()
        # Accept datetime.date/datetime objects or strings. Store as ISO YYYY-MM-DD
        if isinstance(event_date, datetime):
            event_date_str = event_date.date().isoformat()
        elif isinstance(event_date, date):
            event_date_str = event_date.isoformat()
        elif event_date is None:
            # maintain previous behavior: empty string when no date provided
            event_date_str = ''
        else:
            # assume string-like
            event_date_str = str(event_date)

        cur.execute(
            "INSERT INTO future_events (event_date, event_type, event_details) VALUES (?, ?, ?)",
            (event_date_str, event_type, event_details),
        )
        conn.commit()
        rowid = cur.lastrowid
        logger.info('Inserted event id %s into %s', rowid, db_path)
        return rowid
    except Exception as e:
        logger.error('Error inserting event into %s: %s', db_path, e.with_traceback)
        raise e
    finally:
        conn.close()

def getConnection(db_path):
    db_path = db_path or DEFAULT_DB
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    conn = sqlite3.connect(db_path)
    return db_path,conn


def fetch_date_events(date_param: str,db_path=None) -> list[dict]:
    """Fetch events for a specific date (datetime.date or YYYY-MM-DD string) or all events if date is None.

    Returns a list of dictionaries with keys: id, event_date (datetime.date or None), event_type, event_details.
    """
    db_path, conn = getConnection(db_path)
    try:
        cur = conn.cursor()
        if date is None:
            cur.execute("SELECT id, event_date, event_type, event_details FROM future_events ORDER BY event_date, id")
            rows = cur.fetchall()
        else:
            # accept date object or string
            if isinstance(date_param, datetime):
                date_str = date_param.date().isoformat()
            elif isinstance(date_param, date):
                date_str = date_param.isoformat()
            else:
                date_str = str(date_param)
            cur.execute("SELECT id, event_date, event_type, event_details FROM future_events WHERE event_date = ? ORDER BY id", (date_str,))
            rows = cur.fetchall()

        result = []
        for r in rows:
            # convert stored date string back to date object when possible
            stored = r[1]
            if stored is None or stored == '':
                stored_date = None
            else:
                try:
                    stored_date = datetime.strptime(stored, "%Y-%m-%d").date()
                except Exception:
                    # fallback: return raw string if parsing fails
                    stored_date = stored
            result.append({
                'id': r[0],
                'event_date': stored_date,
                'event_type': r[2],
                'event_details': r[3],
            })
        logger.info('Fetched %d events from %s for date=%s', len(result), db_path, date_param)
        return result
    finally:
        conn.close()


if __name__ == '__main__':
    print('Initializing events DB...')
    path = init_events_db()
    print('DB initialized at', path)
