import os, tempfile, sys, json, sqlite3,importlib
import datetime



def main():
    for _ in range(1):  # just to allow easy indentation

                    # Ensure src is on sys.path so package imports and relative imports work
                    SRC_PATH = os.path.join(os.getcwd(), 'src')
                    if SRC_PATH not in sys.path:
                        sys.path.insert(0, SRC_PATH)

                    # Unload any previously loaded package modules to force re-import with the new env
                    for k in list(sys.modules.keys()):
                        if k == 'multi_tool_agent' or k.startswith('multi_tool_agent.') or k == 'setup_events_db':
                            del sys.modules[k]

                    # Import the CalendarAgent as a package submodule so its relative imports resolve
                    mod = importlib.import_module('multi_tool_agent.CalendarAgent')
                    import multi_tool_agent.setup_events_db as db

                    print('setup DEFAULT_DB=', db.DEFAULT_DB)

                    # insert two events via the agent wrapper
                    id1 = mod.add_event_wrapper(
                        json.dumps({

                            'event_type': 'Other',
                            'event_date': '2025-12-01',
                            'is_recurring': True,
                            'event_details': 'Karate  at 7 PM',
                            'start_date': '2025-11-01',
                            'end_date': '2025-12-10',
                            'recurrence_frequency': "Daily",
                        })
                    )
                    print('id1', id1)
                    id2 = mod.add_event_wrapper(
                        json.dumps({
                            'event_type': 'birthday',
                            'event_date': '2025-11-24',
                            'is_recurring': False,
                            'event_details': 'Birthday Party for Joe',
                            'start_date': None,
                            'end_date': None,
                            'recurrence_frequency': None,
                        })
                    )
                    print('id2', id2)

                    rows = db.fetch_date_events(None)
                    print('rows fetch_date_events(None)=', rows)

                    # raw sql
                    conn = sqlite3.connect(db.DEFAULT_DB)
                    cur = conn.cursor()
                    try:
                        cur.execute('SELECT id,event_date,event_type,event_details FROM future_events')
                        print('raw future_events rows', cur.fetchall())
                    except sqlite3.OperationalError as e:
                        print('error reading future_events:', e)
                    try:
                        cur.execute('SELECT id,event_type,event_details FROM recurring_events')
                        print('raw recurring_events rows', cur.fetchall())
                    except sqlite3.OperationalError as e:
                        print('error reading recurring_events:', e)
                    conn.close()




if __name__ == '__main__':
    main()
