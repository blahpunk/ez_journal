# migrate_timezones.py
import pytz
from datetime import datetime
from app import app, db
from models import Entry  # Assuming you have a models.py file

APP_TIMEZONE = pytz.timezone('America/Chicago')

def migrate_timezones():
    with app.app_context():
        entries = Entry.query.all()
        for entry in entries:
            # Convert naive datetime to server's local timezone first
            naive_time = entry.created_at
            local_time = naive_time.replace(tzinfo=pytz.utc).astimezone(APP_TIMEZONE)
            
            entry.created_at = APP_TIMEZONE.normalize(local_time)
            db.session.add(entry)
        
        db.session.commit()
        print(f"Updated {len(entries)} entries to CST/CDT")

if __name__ == '__main__':
    migrate_timezones()