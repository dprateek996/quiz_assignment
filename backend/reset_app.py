import asyncio
from app.core.database import db
from app.services import chapter_service

async def wipe_all_data():
    print("🚀 Starting Clean Sweep...")
    
    # 1. Connect to DB
    if not db.is_connected():
        await db.connect()
    
    # 2. Get all chapters
    chapters = await db.chapter.find_many()
    print(f"Found {len(chapters)} chapters to delete.")

    # 3. Delete each one (This cleans DB + Google Cloud)
    for chap in chapters:
        print(f"🗑️ Deleting: {chap.title}...")
        try:
            await chapter_service.delete_chapter(chap.id)
            print(f"   ✅ Deleted {chap.title}")
        except Exception as e:
            print(f"   ⚠️ Error deleting {chap.title}: {e}")

    print("\n✨ All done! Database and Google Cloud are clean.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(wipe_all_data())