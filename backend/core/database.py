from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import get_settings

settings = get_settings()

# Database engine configuration
def create_db_engine():
    """Create database engine with appropriate configuration"""
    
    is_sqlite = settings.database_url.startswith("sqlite")
    
    # SQLite-specific configuration
    if is_sqlite:
        engine_args = {
            "connect_args": {"check_same_thread": False},
            "echo": False,  # Set to True for SQL query debugging
        }
    # PostgreSQL/other databases
    else:
        engine_args = {
            "pool_pre_ping": True,  # Verify connections before using
            "pool_size": 10,  # Connection pool size
            "max_overflow": 20,  # Max connections beyond pool_size
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "echo": False,
        }
    
    try:
        engine = create_engine(settings.database_url, **engine_args)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print(f"✅ Database engine created: {engine.url}")
        print(f"   Database type: {'SQLite' if is_sqlite else 'PostgreSQL/Other'}")
        
        return engine
        
    except Exception as e:
        print(f"❌ Error creating database engine: {e}")
        print(f"   Database URL: {settings.database_url}")
        raise

# Create engine
engine = create_db_engine()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """
    Dependency that provides a database session.
    Automatically closes session after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables.
    Call this when starting the application.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise