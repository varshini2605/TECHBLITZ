import uuid
from datetime import datetime, timedelta
from models import db

class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.String(64), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id', ondelete='CASCADE'), nullable=False, index=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Snapshot of identity at test start
    hall_ticket_number = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    team_id = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=True)

    # Timing
    start_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, default=20)
    server_end_time = db.Column(db.DateTime, nullable=True)
    submission_time = db.Column(db.DateTime, nullable=True)

    # Status tracking
    status = db.Column(db.String(32), default='NOT_STARTED', nullable=False, index=True)
    # Statuses: NOT_STARTED, ACTIVE, WARNING, BLOCKED, PENDING_ADMIN_APPROVAL, ACTIVE_AFTER_APPROVAL, COMPLETED, AUTO_SUBMITTED, TERMINATED, FLAGGED
    
    # Proctoring & Warning state
    block_reason = db.Column(db.Text, nullable=True)
    unblocked_at = db.Column(db.DateTime, nullable=True)
    active_warning_violation_id = db.Column(db.Integer, nullable=True)
    warning_active = db.Column(db.Boolean, default=False)
    warning_expiry_time = db.Column(db.DateTime, nullable=True)

    # Progress & Scoring
    current_question_index = db.Column(db.Integer, default=0)
    score = db.Column(db.Float, default=0.0)
    total_marks = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)

    # Relationships
    answers = db.relationship('Answer', backref='candidate', cascade='all, delete-orphan')
    violations = db.relationship('Violation', backref='candidate', cascade='all, delete-orphan', order_by='Violation.timestamp')

    def remaining_seconds(self):
        if not self.server_end_time:
            return self.duration_minutes * 60
        now = datetime.utcnow()
        if now >= self.server_end_time:
            return 0
        return int((self.server_end_time - now).total_seconds())

    def is_expired(self):
        return self.remaining_seconds() <= 0

    def answered_count(self):
        return len([a for a in self.answers if a.selected_answer is not None])

    def to_dict(self):
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'registration_id': self.registration_id,
            'test_id': self.test_id,
            'test_name': self.test.name if self.test else '',
            'hall_ticket_number': self.hall_ticket_number,
            'name': self.name,
            'team_id': self.team_id,
            'email': self.email or '',
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'server_end_time': self.server_end_time.isoformat() if self.server_end_time else None,
            'submission_time': self.submission_time.isoformat() if self.submission_time else None,
            'remaining_seconds': self.remaining_seconds(),
            'score': round(self.score, 2),
            'total_marks': round(self.total_marks, 2),
            'percentage': round(self.percentage, 2),
            'answered_count': self.answered_count(),
            'total_questions': len(self.test.questions) if self.test and self.test.questions else 0,
            'current_question_index': self.current_question_index,
            'violations_count': len(self.violations),
            'warning_active': self.warning_active,
            'warning_expiry_time': self.warning_expiry_time.isoformat() if self.warning_expiry_time else None,
            'block_reason': self.block_reason
        }
