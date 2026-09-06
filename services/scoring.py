from datetime import datetime
from models import db, Answer, Question, Candidate

def calculate_candidate_score(candidate, is_auto_submit=False):
    """
    Evaluates candidate answers against question correct answers on the server side.
    Sets score, percentage, submission time, and final status.
    """
    now = datetime.utcnow()
    
    # Check if already submitted
    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED', 'TERMINATED']:
        return candidate
        
    total_score = 0.0
    test_total_marks = 0.0
    
    # Fetch questions for candidate's test
    questions = Question.query.filter_by(test_id=candidate.test_id).all()
    q_map = {q.id: q for q in questions}
    
    for q in questions:
        test_total_marks += q.marks
        
    # Fetch candidate answers
    answers = Answer.query.filter_by(candidate_id=candidate.id).all()
    ans_map = {a.question_id: a for a in answers}
    
    for q_id, q in q_map.items():
        ans = ans_map.get(q_id)
        if ans and ans.selected_answer:
            if ans.selected_answer.strip().upper() == q.correct_answer.strip().upper():
                ans.is_correct = True
                ans.marks_awarded = q.marks
                total_score += q.marks
            else:
                ans.is_correct = False
                ans.marks_awarded = 0.0
        else:
            # Question was unattempted
            if not ans:
                new_ans = Answer(
                    candidate_id=candidate.id,
                    question_id=q_id,
                    selected_answer=None,
                    is_correct=False,
                    marks_awarded=0.0
                )
                db.session.add(new_ans)
            else:
                ans.is_correct = False
                ans.marks_awarded = 0.0
                
    percentage = (total_score / test_total_marks * 100.0) if test_total_marks > 0 else 0.0
    
    candidate.score = round(total_score, 2)
    candidate.total_marks = round(test_total_marks, 2)
    candidate.percentage = round(percentage, 2)
    candidate.submission_time = now
    candidate.status = 'AUTO_SUBMITTED' if is_auto_submit else 'COMPLETED'
    candidate.warning_active = False
    
    db.session.commit()
    return candidate

def get_ranked_results(test_id=None):
    """
    Retrieves candidate results sorted by:
    1. Score DESC (Highest score first)
    2. Submission time ASC (Earlier submission first)
    """
    query = Candidate.query.filter(
        Candidate.status.in_(['COMPLETED', 'AUTO_SUBMITTED', 'TERMINATED', 'FLAGGED'])
    )
    if test_id:
        query = query.filter_by(test_id=test_id)
        
    candidates = query.all()
    
    # Sort in python to handle None submission times cleanly
    def sort_key(c):
        # Score desc -> negative score
        score_val = -c.score
        # Submission time asc -> timestamp or far future if None
        sub_time = c.submission_time.timestamp() if c.submission_time else float('inf')
        return (score_val, sub_time)
        
    sorted_candidates = sorted(candidates, key=sort_key)
    
    ranked = []
    for rank, c in enumerate(sorted_candidates, start=1):
        time_taken_str = "--"
        if c.start_time and c.submission_time:
            seconds_taken = int((c.submission_time - c.start_time).total_seconds())
            mins, secs = divmod(seconds_taken, 60)
            time_taken_str = f"{mins}m {secs}s"
            
        violation_types = list(set([v.type for v in c.violations]))
        
        ranked.append({
            'rank': rank,
            'id': c.id,
            'candidate_id': c.candidate_id,
            'hall_ticket_number': c.hall_ticket_number,
            'name': c.name,
            'team_id': c.team_id,
            'email': c.email or '',
            'test_id': c.test.test_id if c.test else '',
            'test_name': c.test.name if c.test else '',
            'score': c.score,
            'total_marks': c.total_marks,
            'percentage': c.percentage,
            'violations_count': len(c.violations),
            'violation_types': ", ".join(violation_types) if violation_types else "None",
            'status': c.status,
            'start_time': c.start_time.strftime('%Y-%m-%d %H:%M:%S') if c.start_time else '--',
            'submission_time': c.submission_time.strftime('%Y-%m-%d %H:%M:%S') if c.submission_time else '--',
            'time_taken': time_taken_str
        })
        
    return ranked
