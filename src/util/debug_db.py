import tempfile, os, datetime, sqlite3, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from multi_tool_agent import setup_events_db as db

# create temp db
tf = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
path = tf.name
tf.close()
print('db path', path)

# init
db.init_events_db(path)

# insert first
ev_date = datetime.date(2025,12,1)
rowid = db.add_future_event(ev_date, 'Shopping', 'Buy groceries', db_path=path)
print('rowid1', rowid)

# fetch by date
events = db.fetch_date_events(ev_date, db_path=path)
print('events by date', events)

# insert second with no date
row2 = db.add_future_event(None, 'Other', 'No date', db_path=path)
print('rowid2', row2)

# fetch all
all_events = db.fetch_date_events(None, db_path=path)
print('all_events', all_events)

# raw select
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute('SELECT id, event_date, event_type, event_details FROM future_events')
print('raw rows:', cur.fetchall())
conn.close()

# cleanup
os.remove(path)
print('done')
