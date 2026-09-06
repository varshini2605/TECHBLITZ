from datetime import datetime
from models import db

class Test(db.Model):
    __tablename__ = 'tests'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default='')
    duration_minutes = db.Column(db.Integer, default=20, nullable=False)
    total_marks = db.Column(db.Float, default=0.0)
    randomize_questions = db.Column(db.Boolean, default=False)
    randomize_options = db.Column(db.Boolean, default=False)
    max_violations = db.Column(db.Integer, default=3)
    auto_block = db.Column(db.Boolean, default=True)
    auto_terminate = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='test', cascade='all, delete-orphan', order_by='Question.order_index')
    candidates = db.relationship('Candidate', backref='test', cascade='all, delete-orphan')

    def recalculate_total_marks(self):
        self.total_marks = sum(q.marks for q in self.questions)

    def to_dict(self):
        return {
            'id': self.id,
            'test_id': self.test_id,
            'name': self.name,
            'description': self.description,
            'duration_minutes': self.duration_minutes,
            'total_marks': self.total_marks,
            'randomize_questions': self.randomize_questions,
            'randomize_options': self.randomize_options,
            'max_violations': self.max_violations,
            'auto_block': self.auto_block,
            'auto_terminate': self.auto_terminate,
            'active': self.active,
            'question_count': len(self.questions) if self.questions else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
