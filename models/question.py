from datetime import datetime
from models import db

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(2), nullable=False)  # 'A', 'B', 'C', 'D'
    marks = db.Column(db.Float, default=1.0, nullable=False)
    topic = db.Column(db.String(100), default='General')
    difficulty = db.Column(db.String(50), default='Medium')  # Easy, Medium, Hard
    explanation = db.Column(db.Text, default='')
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    answers = db.relationship('Answer', backref='question', cascade='all, delete-orphan')

    def to_dict(self, include_answer=False):
        data = {
            'id': self.id,
            'test_id': self.test_id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'marks': self.marks,
            'topic': self.topic,
            'difficulty': self.difficulty,
            'order_index': self.order_index,
        }
        if include_answer:
            data['correct_answer'] = self.correct_answer
            data['explanation'] = self.explanation
            data['created_at'] = self.created_at.isoformat() if self.created_at else None
            data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return data
