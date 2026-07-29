import time
import logging

logger = logging.getLogger("Retry")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def retry_supabase(func, *args, retries: int = 2, delay: float = 0.5, **kwargs):
    """Generic retry helper for Supabase database operations."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Supabase operation failed: {e}. Retrying in {delay}s (attempt {attempt+1}/{retries})...")
                time.sleep(delay)
            else:
                logger.error(f"Supabase operation failed final attempt: {e}")
                raise

def retry_sqlite(func, *args, retries: int = 2, delay: float = 0.5, **kwargs):
    """Generic retry helper for local SQLite operations."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"SQLite operation failed: {e}. Retrying in {delay}s (attempt {attempt+1}/{retries})...")
                time.sleep(delay)
            else:
                logger.error(f"SQLite operation failed final attempt: {e}")
                raise
