def build_redis_url(host, port, password=None, db_num=0):
    """Build Redis URL with optional password authentication."""
    if password:
        return f"redis://:{password}@{host}:{port}/{db_num}"
    return f"redis://{host}:{port}/{db_num}"
