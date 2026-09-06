from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.admin import Admin
from models.test import Test
from models.question import Question
from models.registration import Registration
from models.candidate import Candidate
from models.answer import Answer
from models.violation import Violation

__all__ = [
    'db',
    'Admin',
    'Test',
    'Question',
    'Registration',
    'Candidate',
    'Answer',
    'Violation'
]
