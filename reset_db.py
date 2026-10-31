# reset_db.py - Run this file first!
import sqlite3
import os

# Delete the old database
if os.path.exists('database.db'):
    os.remove('database.db')
    print("✅ Old database deleted")
else:
    print("⚠️ No database found")

print("✅ Now run: python app.py")