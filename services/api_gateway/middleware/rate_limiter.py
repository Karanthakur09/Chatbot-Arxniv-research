from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from shared.config import settings

# 1. Construct the Redis URI
redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"

# 2. Define the "Key" function
def get_user_or_ip(request: Request):
    """
    Tries to identify the user by their ID first (if logged in),
    otherwise falls back to their IP address.
    """
    # Note: request.state.user is only populated if you set it in a middleware.
    # For now, get_remote_address is the safest fallback.
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    return get_remote_address(request)

# 3. Create the ONE and ONLY Limiter instance
limiter = Limiter(
    key_func=get_user_or_ip,
    storage_uri=redis_url,
    strategy="moving-window"  # Most accurate for sliding windows
)
