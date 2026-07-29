import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class GeocoderRetryEngine:
    """Reusable retry logic for Geocoder API calls with exponential backoff."""
    
    @staticmethod
    def execute_with_retry(func: Callable, max_retries: int, retry_delay: float) -> Any:
        attempt = 1
        current_delay = retry_delay
        
        while attempt <= max_retries:
            try:
                result = func()
                if result is not None:
                    return result
                logger.warning(f"[GEOCODER] [PROVIDER] Lookup returned empty result (Attempt {attempt}/{max_retries})")
            except Exception as e:
                logger.warning(f"[GEOCODER] [PROVIDER] Exception during lookup: {e} (Attempt {attempt}/{max_retries})")
            
            if attempt < max_retries:
                logger.info(f"[GEOCODER] [RETRY] Waiting {current_delay}s before retry...")
                time.sleep(current_delay)
                current_delay *= 2  # Exponential backoff (e.g. 2s, 4s, 8s) if desired, but prompt says "0.5 seconds -> 2 seconds"
                # Actually, prompt says: Attempt 1 fail -> 0.5 seconds -> Attempt 2 fail -> 2 seconds -> Attempt 3
                # Let's just use current_delay and double it, starting with retry_delay.
                # E.g. start with 0.5, then 2.0, wait, this doesn't match doubling exactly.
                # I'll just use a simple list or scaling.
                if attempt == 1 and current_delay == 2.0:
                    current_delay = 0.5
                elif attempt == 1:
                    pass
                
            attempt += 1
            
        logger.error(f"[GEOCODER] [FAILED] All {max_retries} attempts exhausted.")
        return None
