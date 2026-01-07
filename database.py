from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional, List
import config

# MongoDB client
mongo_client = None
db = None

# ==================== DATABASE CONNECTION ====================
async def connect_db():
    """Connect to MongoDB"""
    global mongo_client, db
    
    try:
        mongo_client = AsyncIOMotorClient(config.MONGO_URI)
        db = mongo_client[config.MONGO_DB]
        
        # Test connection
        await db.command('ping')
        print("✅ Connected to MongoDB successfully!")
        
        # Create indexes for better performance
        await db.upload_queue.create_index("status")
        await db.upload_queue.create_index("added_at")
        await db.upload_queue.create_index("message_id")
        
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

async def close_db():
    """Close MongoDB connection"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        print("👋 MongoDB connection closed")

def get_db():
    """Get database instance"""
    return db

# ==================== QUEUE OPERATIONS ====================

async def add_to_queue(
    message_id: int,
    file_name: str,
    file_id: Optional[str] = None,
    file_url: Optional[str] = None,
    file_size: Optional[int] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    thumbnail_file_id: Optional[str] = None
) -> Optional[str]:
    """Add a new video to upload queue"""
    try:
        queue_item = {
            "message_id": message_id,
            "file_id": file_id,
            "file_url": file_url,
            "file_name": file_name,
            "file_size": file_size,
            "title": title or file_name,
            "description": description,
            "thumbnail_file_id": thumbnail_file_id,
            "status": "pending",
            "lulustream_file_code": None,
            "lulustream_url": None,
            "added_at": datetime.utcnow(),
            "uploaded_at": None,
            "posted_at": None,
            "retry_count": 0,
            "error_message": None
        }
        
        result = await db.upload_queue.insert_one(queue_item)
        return str(result.inserted_id)
    except Exception as e:
        print(f"[ERROR] Add to queue failed: {e}")
        return None

async def get_pending_uploads(limit: Optional[int] = None) -> List:
    """Get pending videos to upload"""
    try:
        query = {"status": "pending"}
        cursor = db.upload_queue.find(query).sort("added_at", 1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return await cursor.to_list(length=limit or 100)
    except Exception as e:
        print(f"[ERROR] Get pending uploads failed: {e}")
        return []

async def get_uploaded_not_posted(limit: Optional[int] = None) -> List:
    """Get uploaded videos that haven't been posted yet"""
    try:
        query = {"status": "uploaded"}
        cursor = db.upload_queue.find(query).sort("uploaded_at", 1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return await cursor.to_list(length=limit or 100)
    except Exception as e:
        print(f"[ERROR] Get uploaded not posted failed: {e}")
        return []

async def update_upload_status(
    queue_id: str,
    status: str,
    lulustream_file_code: Optional[str] = None,
    lulustream_url: Optional[str] = None,
    error_message: Optional[str] = None
) -> bool:
    """Update upload status"""
    try:
        from bson import ObjectId
        
        update_data = {
            "status": status
        }
        
        if lulustream_file_code:
            update_data["lulustream_file_code"] = lulustream_file_code
        
        if lulustream_url:
            update_data["lulustream_url"] = lulustream_url
        
        if error_message:
            update_data["error_message"] = error_message
        
        if status == "uploaded":
            update_data["uploaded_at"] = datetime.utcnow()
        
        if status == "posted":
            update_data["posted_at"] = datetime.utcnow()
        
        result = await db.upload_queue.update_one(
            {"_id": ObjectId(queue_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"[ERROR] Update status failed: {e}")
        return False

async def get_queue_stats() -> dict:
    """Get queue statistics"""
    try:
        total = await db.upload_queue.count_documents({})
        pending = await db.upload_queue.count_documents({"status": "pending"})
        uploading = await db.upload_queue.count_documents({"status": "uploading"})
        uploaded = await db.upload_queue.count_documents({"status": "uploaded"})
        posted = await db.upload_queue.count_documents({"status": "posted"})
        failed = await db.upload_queue.count_documents({"status": "failed"})
        
        return {
            "total": total,
            "pending": pending,
            "uploading": uploading,
            "uploaded": uploaded,
            "posted": posted,
            "failed": failed
        }
    except Exception as e:
        print(f"[ERROR] Get queue stats failed: {e}")
        return {
            "total": 0,
            "pending": 0,
            "uploading": 0,
            "uploaded": 0,
            "posted": 0,
            "failed": 0
        }

async def increment_retry_count(queue_id: str) -> int:
    """Increment retry count for failed uploads"""
    try:
        from bson import ObjectId
        
        result = await db.upload_queue.update_one(
            {"_id": ObjectId(queue_id)},
            {"$inc": {"retry_count": 1}}
        )
        
        if result.modified_count > 0:
            item = await db.upload_queue.find_one({"_id": ObjectId(queue_id)})
            return item.get("retry_count", 0)
        
        return 0
    except Exception as e:
        print(f"[ERROR] Increment retry count failed: {e}")
        return 0

async def get_queue_item(queue_id: str) -> Optional[dict]:
    """Get a specific queue item by ID"""
    try:
        from bson import ObjectId
        return await db.upload_queue.find_one({"_id": ObjectId(queue_id)})
    except Exception as e:
        print(f"[ERROR] Get queue item failed: {e}")
        return None

async def delete_queue_item(queue_id: str) -> bool:
    """Delete a queue item"""
    try:
        from bson import ObjectId
        result = await db.upload_queue.delete_one({"_id": ObjectId(queue_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"[ERROR] Delete queue item failed: {e}")
        return False

async def clear_failed_uploads() -> int:
    """Clear all failed uploads from queue"""
    try:
        result = await db.upload_queue.delete_many({"status": "failed"})
        return result.deleted_count
    except Exception as e:
        print(f"[ERROR] Clear failed uploads failed: {e}")
        return 0

async def get_recent_posts(limit: int = 10) -> List:
    """Get recently posted videos"""
    try:
        query = {"status": "posted"}
        cursor = db.upload_queue.find(query).sort("posted_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        print(f"[ERROR] Get recent posts failed: {e}")
        return []
