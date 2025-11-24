import sqlite3, os, sys

# Ensure the project's src/ directory is on sys.path so packages can be imported
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

import datetime
import multi_tool_agent.CalendarAgent as CA
from multi_tool_agent import setup_events_db as DB

path = os.getenv('EVENTS_DB_PATH', os.path.join(os.getcwd(), 'events_db.sqlite'))
print('DB path expected:', path)

# Insert a sample event via the CalendarAgent helper using a date object
sample_date = datetime.date(2025, 12, 1)
res = CA.save_calendar_event('Buy groceries for the party', 'Shopping', sample_date)
print('Insert result:', res)

print('\nFetch specific date (2025-12-01):')
events_on_date = DB.fetch_date_events(sample_date)
for e in events_on_date:
	print(e)

print('\nFetch all events:')
all_events = DB.fetch_date_events(None)
print(f'Total: {len(all_events)}')
for e in all_events[:10]:
	print(e)
