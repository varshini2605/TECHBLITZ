from flask import Blueprint, render_template, session, redirect, url_for, request
from models import Candidate, Test, Registration

candidate_bp = Blueprint('candidate', __name__)

@candidate_bp.route('/')
def index():
    # If candidate already has an active session, route accordingly
    cand_id = session.get('candidate_id')
    if cand_id:
        candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
        if candidate:
            if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED']:
                return redirect(url_for('candidate.result_page'))
            elif candidate.status == 'BLOCKED':
                return redirect(url_for('candidate.blocked_page'))
            elif candidate.status in ['ACTIVE', 'WARNING', 'ACTIVE_AFTER_APPROVAL']:
                return redirect(url_for('candidate.test_page'))
            elif candidate.status == 'NOT_STARTED':
                return redirect(url_for('candidate.instructions_page'))
                
    # Fetch active tests for information/banner
    active_test = Test.query.filter_by(active=True).first()
    return render_template('index.html', test=active_test)

@candidate_bp.route('/instructions')
def instructions_page():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return redirect(url_for('candidate.index'))
        
    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        session.pop('candidate_id', None)
        return redirect(url_for('candidate.index'))
        
    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED', 'TERMINATED']:
        return redirect(url_for('candidate.result_page'))
    if candidate.status == 'BLOCKED':
        return redirect(url_for('candidate.blocked_page'))
    if candidate.status in ['ACTIVE', 'WARNING', 'ACTIVE_AFTER_APPROVAL']:
        return redirect(url_for('candidate.test_page'))
        
    return render_template('instructions.html', candidate=candidate, test=candidate.test)

@candidate_bp.route('/test')
def test_page():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return redirect(url_for('candidate.index'))
        
    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        session.pop('candidate_id', None)
        return redirect(url_for('candidate.index'))
        
    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED', 'TERMINATED']:
        return redirect(url_for('candidate.result_page'))
    if candidate.status == 'BLOCKED':
        return redirect(url_for('candidate.blocked_page'))
    if candidate.status == 'NOT_STARTED':
        return redirect(url_for('candidate.instructions_page'))
        
    return render_template('test.html', candidate=candidate, test=candidate.test)

@candidate_bp.route('/blocked')
def blocked_page():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return redirect(url_for('candidate.index'))
        
    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return redirect(url_for('candidate.index'))
        
    if candidate.status in ['ACTIVE', 'ACTIVE_AFTER_APPROVAL']:
        return redirect(url_for('candidate.test_page'))
    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED', 'TERMINATED']:
        return redirect(url_for('candidate.result_page'))
        
    return render_template('blocked.html', candidate=candidate, test=candidate.test)

@candidate_bp.route('/result')
def result_page():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return redirect(url_for('candidate.index'))
        
    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return redirect(url_for('candidate.index'))
        
    return render_template('result.html', candidate=candidate, test=candidate.test)
