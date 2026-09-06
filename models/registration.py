from datetime import datetime
from models import db

class Registration(db.Model):
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    hall_ticket_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    normalized_hall_ticket = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    team_id = db.Column(db.String(100), nullable=False, index=True)
    normalized_team_id = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)  # 'ACTIVE' or 'DISABLED'
    source_file = db.Column(db.String(255), default='Manual Entry')
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidates = db.relationship('Candidate', backref='registration', cascade='all, delete-orphan')

    @staticmethod
    def normalize_string(val):
        if not val:
            return ''
        return str(val).strip().upper()

    @staticmethod
    def normalize_name(val):
        if not val:
            return ''
        # normalize multiple whitespace to single space and lowercase for matching
        return ' '.join(str(val).strip().split()).lower()

    def is_active(self):
        return self.status == 'ACTIVE'

    def to_dict(self):
        return {
            'id': self.id,
            'hall_ticket_number': self.hall_ticket_number,
            'name': self.name,
            'team_id': self.team_id,
            'email': self.email or '',
            'status': self.status,
            'source_file': self.source_file,
            'imported_at': self.imported_at.strftime('%Y-%m-%d %H:%M:%S') if self.imported_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
