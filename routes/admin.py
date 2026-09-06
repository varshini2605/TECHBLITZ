from flask import Blueprint, render_template, request, abort
from routes.auth import admin_required
from models import Admin, Test, Question, Registration, Candidate, Violation, Answer
from services.scoring import get_ranked_results

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def dashboard_page():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    active_test = Test.query.filter_by(active=True).first() or (tests[0] if tests else None)
    
    # Calculate summary metrics
    total_registered = Registration.query.count()
    total_candidates = Candidate.query.count()
    active_candidates = Candidate.query.filter(Candidate.status.in_(['ACTIVE', 'WARNING', 'ACTIVE_AFTER_APPROVAL'])).count()
    completed_candidates = Candidate.query.filter(Candidate.status.in_(['COMPLETED', 'AUTO_SUBMITTED'])).count()
    blocked_candidates = Candidate.query.filter(Candidate.status == 'BLOCKED').count()
    flagged_candidates = Candidate.query.filter(Candidate.status == 'FLAGGED').count()
    terminated_candidates = Candidate.query.filter(Candidate.status == 'TERMINATED').count()
    
    ranked_results = get_ranked_results(active_test.id if active_test else None)
    
    return render_template(
        'admin_dashboard.html',
        tests=tests,
        active_test=active_test,
        total_registered=total_registered,
        total_candidates=total_candidates,
        active_candidates=active_candidates,
        completed_candidates=completed_candidates,
        blocked_candidates=blocked_candidates,
        flagged_candidates=flagged_candidates,
        terminated_candidates=terminated_candidates,
        ranked_results=ranked_results[:10]  # Top 10 for dashboard preview
    )

@admin_bp.route('/admin/registrations')
@admin_required
def registrations_page():
    total_count = Registration.query.count()
    active_count = Registration.query.filter_by(status='ACTIVE').count()
    disabled_count = Registration.query.filter_by(status='DISABLED').count()
    
    return render_template(
        'registration.html',
        total_count=total_count,
        active_count=active_count,
        disabled_count=disabled_count
    )

@admin_bp.route('/admin/questions')
@admin_required
def questions_page():
    tests = Test.query.all()
    selected_test_id = request.args.get('test_id', type=int)
    
    if not selected_test_id and tests:
        selected_test_id = tests[0].id
        
    current_test = db.session.get(Test, selected_test_id) if selected_test_id else None
    questions = Question.query.filter_by(test_id=selected_test_id).order_by(Question.order_index).all() if selected_test_id else []
    
    return render_template(
        'manage_questions.html',
        tests=tests,
        current_test=current_test,
        questions=questions
    )

@admin_bp.route('/admin/question-generator')
@admin_required
def question_generator_page():
    tests = Test.query.all()
    return render_template('question_generator.html', tests=tests)

@admin_bp.route('/admin/tests')
@admin_required
def tests_page():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    return render_template('manage_tests.html', tests=tests)

@admin_bp.route('/admin/candidate/<int:candidate_id>')
@admin_required
def candidate_profile_page(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    violations = Violation.query.filter_by(candidate_id=candidate.id).order_by(Violation.timestamp.desc()).all()
    
    # Fetch questions and candidate answers
    questions = Question.query.filter_by(test_id=candidate.test_id).order_by(Question.order_index).all()
    answers_map = {a.question_id: a for a in Answer.query.filter_by(candidate_id=candidate.id).all()}
    
    question_details = []
    for q in questions:
        ans = answers_map.get(q.id)
        question_details.append({
            'question': q,
            'selected_answer': ans.selected_answer if ans else None,
            'is_correct': ans.is_correct if ans else False,
            'marks_awarded': ans.marks_awarded if ans else 0.0
        })
        
    return render_template(
        'candidate_profile.html',
        candidate=candidate,
        violations=violations,
        question_details=question_details
    )
