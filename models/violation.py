from datetime import datetime
from models import db

class Violation(db.Model):
    __tablename__ = 'violations'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Redundant snapshot fields for fast querying & immutable audit log
    candidate_name = db.Column(db.String(150), nullable=False)
    hall_ticket_number = db.Column(db.String(100), nullable=False, index=True)
    team_id = db.Column(db.String(100), nullable=False)
    test_id = db.Column(db.Integer, nullable=False)

    # Violation details
    type = db.Column(db.String(50), nullable=False)
    # Types: TAB_SWITCH, WINDOW_BLUR, COPY_ATTEMPT, PASTE_ATTEMPT, CUT_ATTEMPT, RIGHT_CLICK, FULLSCREEN_EXIT, BROWSER_SWITCH, SCREEN_CHANGE
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    violation_number = db.Column(db.Integer, default=1)
    
    # 20-Second Warning Protocol
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    warning_start_time = db.Column(db.DateTime, nullable=True)
    warning_expiry_time = db.Column(db.DateTime, nullable=True)
    blocked = db.Column(db.Boolean, default=False)

    # Admin actions
    admin_action = db.Column(db.String(50), nullable=True)  # GRANT_PERMISSION, UNBLOCK, BLOCK, TERMINATE
    admin_action_at = db.Column(db.DateTime, nullable=True)
    metadata_json = db.Column(db.Text, default='{}')

    def to_dict(self):
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'candidate_name': self.candidate_name,
            'hall_ticket_number': self.hall_ticket_number,
            'team_id': self.team_id,
            'test_id': self.test_id,
            'type': self.type,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'violation_number': self.violation_number,
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at.strftime('%Y-%m-%d %H:%M:%S') if self.acknowledged_at else None,
            'warning_start_time': self.warning_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.warning_start_time else None,
            'warning_expiry_time': self.warning_expiry_time.strftime('%Y-%m-%d %H:%M:%S') if self.warning_expiry_time else None,
            'blocked': self.blocked,
            'admin_action': self.admin_action,
            'admin_action_at': self.admin_action_at.strftime('%Y-%m-%d %H:%M:%S') if self.admin_action_at else None,
            'metadata_json': self.metadata_json
        }
