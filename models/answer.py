from datetime import datetime
from models import db

class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    selected_answer = db.Column(db.String(2), nullable=True)  # 'A', 'B', 'C', 'D', or None
    is_correct = db.Column(db.Boolean, default=False)
    marks_awarded = db.Column(db.Float, default=0.0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('candidate_id', 'question_id', name='_candidate_question_uc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'question_id': self.question_id,
            'selected_answer': self.selected_answer,
            'is_correct': self.is_correct,
            'marks_awarded': self.marks_awarded,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None
        }
