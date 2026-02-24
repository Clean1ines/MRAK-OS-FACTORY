#!/usr/bin/env python3
"""
Cleanup script for test workflows and projects.
Run: python cleanup_test_data.py
"""

import os
import asyncpg
import asyncio
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def cleanup():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Delete all workflows
        result = await conn.execute("DELETE FROM workflow_edges")
        print(f"✅ Deleted edges")
        
        result = await conn.execute("DELETE FROM workflow_nodes")
        print(f"✅ Deleted nodes")
        
        result = await conn.execute("DELETE FROM workflows")
        print(f"✅ Deleted workflows")
        
        # Delete all artifacts
        result = await conn.execute("DELETE FROM artifacts")
        print(f"✅ Deleted artifacts")
        
        # Delete all clarification sessions
        result = await conn.execute("DELETE FROM clarification_sessions")
        print(f"✅ Deleted clarification sessions")
        
        # Delete all projects (просто все, без MIN)
        result = await conn.execute("DELETE FROM projects")
        print(f"✅ Deleted ALL projects")
        
        print("\n🎉 Cleanup complete!")
        print("💡 Tip: Create a fresh project in the UI")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup())