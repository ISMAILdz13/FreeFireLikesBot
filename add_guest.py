"""
Quick guest account adder — no root needed.
Just run: python add_guest.py
It'll ask for UID and password, add them to the database, and loop.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "guests.db")

def add_guest():
    db = sqlite3.connect(DB_PATH)
    
    print("🔥 Guest Account Adder")
    print("=" * 40)
    
    while True:
        print()
        uid = input("Enter guest UID (or 'q' to quit): ").strip()
        if uid.lower() == 'q':
            break
        
        if not uid:
            continue
            
        password = input("Enter guest password: ").strip()
        if not password:
            print("❌ Password required!")
            continue
        
        region = input("Region (press Enter for ME): ").strip() or "ME"
        
        try:
            db.execute('''
                INSERT OR REPLACE INTO guests 
                (uid, password, region, nickname, created_at, last_used, like_count, is_active, health_status, jwt_failures)
                VALUES (?, ?, ?, '', 0, 0, 0, 1, 'unknown', 0)
            ''', (uid, password, region))
            db.commit()
            print(f"✅ Added: UID={uid} Region={region}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Show count
        count = db.execute("SELECT COUNT(*) FROM guests WHERE is_active=1").fetchone()[0]
        print(f"📊 Total active guests: {count}")
    
    db.close()
    print(f"\n👋 Done! Run: python main.py guests stats")

if __name__ == "__main__":
    add_guest()
