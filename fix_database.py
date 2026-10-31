# fix_database.py
import sqlite3

# Connect to your database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    # Add is_verified column if it doesn't exist
    cursor.execute("ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0")
    print("✅ Added 'is_verified' column successfully!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✅ Column 'is_verified' already exists!")
    else:
        print(f"Error: {e}")

try:
    # Add is_active column if it doesn't exist
    cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
    print("✅ Added 'is_active' column successfully!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✅ Column 'is_active' already exists!")
    else:
        print(f"Error: {e}")

# Commit changes and close
conn.commit()
conn.close()

print("\n✅ Database fix completed! Now run 'python app.py'")