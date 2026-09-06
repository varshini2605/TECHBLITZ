from datetime import datetime, timedelta

def initialize_candidate_timer(candidate, duration_minutes):
    """
    Sets the server-side start time and expiration time for a candidate.
    """
    now = datetime.utcnow()
    candidate.start_time = now
    candidate.duration_minutes = duration_minutes
    candidate.server_end_time = now + timedelta(minutes=duration_minutes)
    return candidate

def get_remaining_seconds(candidate):
    """
    Calculates the exact remaining seconds based on server time.
    """
    if not candidate.server_end_time:
        return candidate.duration_minutes * 60
    now = datetime.utcnow()
    diff = (candidate.server_end_time - now).total_seconds()
    return max(0, int(diff))

def is_time_expired(candidate, grace_seconds=5):
    """
    Checks if the test duration has elapsed, accounting for network grace period.
    """
    if not candidate.server_end_time:
        return False
    now = datetime.utcnow()
    return now > (candidate.server_end_time + timedelta(seconds=grace_seconds))
