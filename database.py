from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import config

Base = declarative_base()

# Create engine
engine = create_engine(config.DATABASE_URL, echo=False)
Session = scoped_session(sessionmaker(bind=engine))

class UploadQueue(Base):
    """Table to store videos in upload queue"""
    __tablename__ = 'upload_queue'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Telegram message details
    message_id = Column(Integer, nullable=False)
    file_id = Column(String(255), nullable=True)  # For Telegram files
    file_url = Column(Text, nullable=True)  # For direct download links
    file_name = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Video metadata
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    thumbnail_file_id = Column(String(255), nullable=True)
    
    # Upload status
    status = Column(String(50), default='pending')  # pending, uploading, uploaded, posted, failed
    lulustream_file_code = Column(String(100), nullable=True)
    lulustream_url = Column(Text, nullable=True)
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    
    # Error handling
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class PostSchedule(Base):
    """Table to track posting schedule"""
    __tablename__ = 'post_schedule'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(Integer, nullable=False)
    videos_posted = Column(Integer, default=0)
    scheduled_time = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Stats(Base):
    """Table to store bot statistics"""
    __tablename__ = 'stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    total_uploads = Column(Integer, default=0)
    total_posted = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create all tables
def init_db():
    """Initialize database and create all tables"""
    Base.metadata.create_all(engine)
    print("✅ Database initialized successfully!")

# Database helper functions
def add_to_queue(message_id, file_name, file_id=None, file_url=None, file_size=None, 
                 title=None, description=None, thumbnail_file_id=None):
    """Add a new video to upload queue"""
    session = Session()
    try:
        queue_item = UploadQueue(
            message_id=message_id,
            file_id=file_id,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            title=title or file_name,
            description=description,
            thumbnail_file_id=thumbnail_file_id,
            status='pending'
        )
        session.add(queue_item)
        session.commit()
        return queue_item.id
    except Exception as e:
        session.rollback()
        print(f"Error adding to queue: {e}")
        return None
    finally:
        session.close()

def get_pending_uploads(limit=None):
    """Get pending videos to upload"""
    session = Session()
    try:
        query = session.query(UploadQueue).filter_by(status='pending')
        if limit:
            query = query.limit(limit)
        return query.all()
    finally:
        session.close()

def get_uploaded_not_posted(limit=None):
    """Get uploaded videos that haven't been posted yet"""
    session = Session()
    try:
        query = session.query(UploadQueue).filter_by(status='uploaded')
        if limit:
            query = query.limit(limit)
        return query.all()
    finally:
        session.close()

def update_upload_status(queue_id, status, lulustream_file_code=None, 
                        lulustream_url=None, error_message=None):
    """Update upload status"""
    session = Session()
    try:
        item = session.query(UploadQueue).filter_by(id=queue_id).first()
        if item:
            item.status = status
            if lulustream_file_code:
                item.lulustream_file_code = lulustream_file_code
            if lulustream_url:
                item.lulustream_url = lulustream_url
            if error_message:
                item.error_message = error_message
            if status == 'uploaded':
                item.uploaded_at = datetime.utcnow()
            if status == 'posted':
                item.posted_at = datetime.utcnow()
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error updating status: {e}")
        return False
    finally:
        session.close()

def get_queue_stats():
    """Get queue statistics"""
    session = Session()
    try:
        total = session.query(UploadQueue).count()
        pending = session.query(UploadQueue).filter_by(status='pending').count()
        uploading = session.query(UploadQueue).filter_by(status='uploading').count()
        uploaded = session.query(UploadQueue).filter_by(status='uploaded').count()
        posted = session.query(UploadQueue).filter_by(status='posted').count()
        failed = session.query(UploadQueue).filter_by(status='failed').count()
        
        return {
            'total': total,
            'pending': pending,
            'uploading': uploading,
            'uploaded': uploaded,
            'posted': posted,
            'failed': failed
        }
    finally:
        session.close()

def increment_retry_count(queue_id):
    """Increment retry count for failed uploads"""
    session = Session()
    try:
        item = session.query(UploadQueue).filter_by(id=queue_id).first()
        if item:
            item.retry_count += 1
            session.commit()
            return item.retry_count
        return 0
    finally:
        session.close()
