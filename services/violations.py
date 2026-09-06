import json
from datetime import datetime, timedelta
from models import db, Violation, Candidate

DEBOUNCE_WINDOW_SECONDS = 1.5
WARNING_DURATION_SECONDS = 20

def record_violation(candidate, violation_type, metadata=None):
    """
    Records a browser violation with debouncing and updates the candidate's proctoring state.
    Returns (violation, created_bool, message)
    """
    now = datetime.utcnow()
    
    # 1. Debounce check: if candidate had the same violation type in last 1.5s, ignore
    last_v = Violation.query.filter_by(
        candidate_id=candidate.id,
        type=violation_type
    ).order_by(Violation.timestamp.desc()).first()
    
    if last_v and (now - last_v.timestamp).total_seconds() < DEBOUNCE_WINDOW_SECONDS:
        return last_v, False, "Debounced duplicate violation"
        
    # Check if candidate is already terminated
    if candidate.status == 'TERMINATED':
        return None, False, "Candidate test is already terminated"
        
    # Current violation count
    existing_count = Violation.query.filter_by(candidate_id=candidate.id).count()
    new_violation_number = existing_count + 1
    
    # Expiry time for the 20-second warning countdown
    warning_expiry = now + timedelta(seconds=WARNING_DURATION_SECONDS)
    
    # Create violation record
    violation = Violation(
        candidate_id=candidate.id,
        candidate_name=candidate.name,
        hall_ticket_number=candidate.hall_ticket_number,
        team_id=candidate.team_id,
        test_id=candidate.test_id,
        type=violation_type,
        timestamp=now,
        violation_number=new_violation_number,
        acknowledged=False,
        warning_start_time=now,
        warning_expiry_time=warning_expiry,
        blocked=False,
        metadata_json=json.dumps(metadata or {})
    )
    db.session.add(violation)
    
    # Update candidate warning state
    candidate.warning_active = True
    candidate.warning_expiry_time = warning_expiry
    candidate.active_warning_violation_id = None  # will link after flush
    
    # Check strikes against test rules
    max_violations = candidate.test.max_violations if candidate.test else 3
    auto_block = candidate.test.auto_block if candidate.test else True
    
    if new_violation_number >= max_violations:
        if auto_block:
            candidate.status = 'BLOCKED'
            candidate.block_reason = f"Exceeded maximum allowed violations ({new_violation_number}/{max_violations})"
            violation.blocked = True
        else:
            candidate.status = 'FLAGGED'
    else:
        if candidate.status not in ['BLOCKED', 'PENDING_ADMIN_APPROVAL']:
            candidate.status = 'WARNING'
            
    db.session.flush()
    candidate.active_warning_violation_id = violation.id
    db.session.commit()
    
    return violation, True, "Violation recorded"

def acknowledge_warning(candidate):
    """
    Candidate presses OK before the 20 seconds elapse.
    """
    now = datetime.utcnow()
    
    if not candidate.warning_active:
        return True, "No active warning"
        
    # Check if candidate already exceeded 20 seconds
    if candidate.warning_expiry_time and now > candidate.warning_expiry_time:
        # Exceeded 20s window! Automatic block
        candidate.warning_active = False
        candidate.status = 'BLOCKED'
        candidate.block_reason = "Violation warning was not acknowledged within 20 seconds"
        db.session.commit()
        return False, "Acknowledgement window expired. Candidate is blocked."
        
    # Acknowledged on time
    if candidate.active_warning_violation_id:
        v = db.session.get(Violation, candidate.active_warning_violation_id)
        if v:
            v.acknowledged = True
            v.acknowledged_at = now
            
    candidate.warning_active = False
    candidate.active_warning_violation_id = None
    
    # If candidate is not blocked/flagged, restore to ACTIVE or ACTIVE_AFTER_APPROVAL
    if candidate.status not in ['BLOCKED', 'TERMINATED', 'FLAGGED']:
        candidate.status = 'ACTIVE'
        
    db.session.commit()
    return True, "Warning acknowledged successfully"

def check_and_enforce_warning_timeout(candidate):
    """
    Checks if a candidate currently has an active warning that has exceeded 20 seconds.
    If so, automatically transitions the candidate to BLOCKED.
    """
    if candidate.status in ['BLOCKED', 'TERMINATED', 'COMPLETED', 'AUTO_SUBMITTED']:
        return False
        
    if candidate.warning_active and candidate.warning_expiry_time:
        now = datetime.utcnow()
        if now > candidate.warning_expiry_time:
            candidate.warning_active = False
            candidate.status = 'BLOCKED'
            candidate.block_reason = "Violation warning was not acknowledged within 20 seconds"
            
            if candidate.active_warning_violation_id:
                v = db.session.get(Violation, candidate.active_warning_violation_id)
                if v:
                    v.blocked = True
                    
            db.session.commit()
            return True
            
    return False

def handle_admin_action(candidate, action, admin_notes=None):
    """
    Executes proctoring intervention from the admin console:
    - 'GRANT_PERMISSION': unblocks candidate and sets status to ACTIVE_AFTER_APPROVAL
    - 'UNBLOCK': unblocks candidate and sets status to ACTIVE
    - 'BLOCK': manually blocks candidate
    - 'TERMINATE': terminates candidate exam permanently
    """
    now = datetime.utcnow()
    valid_actions = ['GRANT_PERMISSION', 'UNBLOCK', 'BLOCK', 'TERMINATE']
    if action not in valid_actions:
        raise ValueError(f"Invalid admin action: {action}")
        
    if candidate.status == 'TERMINATED' and action != 'TERMINATE':
        return False, "Cannot modify a terminated test"
        
    if action == 'GRANT_PERMISSION':
        candidate.status = 'ACTIVE_AFTER_APPROVAL'
        candidate.warning_active = False
        candidate.block_reason = None
        candidate.unblocked_at = now
        msg = "Admin granted permission to continue"
        
    elif action == 'UNBLOCK':
        candidate.status = 'ACTIVE'
        candidate.warning_active = False
        candidate.block_reason = None
        candidate.unblocked_at = now
        msg = "Admin unblocked candidate"
        
    elif action == 'BLOCK':
        candidate.status = 'BLOCKED'
        candidate.warning_active = False
        candidate.block_reason = admin_notes or "Manually blocked by administrator"
        msg = "Admin manually blocked candidate"
        
    elif action == 'TERMINATE':
        candidate.status = 'TERMINATED'
        candidate.warning_active = False
        candidate.block_reason = admin_notes or "Test terminated by administrator"
        candidate.submission_time = now
        msg = "Admin terminated candidate test"
        
    # Log admin action on most recent violation
    latest_violation = Violation.query.filter_by(candidate_id=candidate.id).order_by(Violation.timestamp.desc()).first()
    if latest_violation:
        latest_violation.admin_action = action
        latest_violation.admin_action_at = now
        
    db.session.commit()
    return True, msg
