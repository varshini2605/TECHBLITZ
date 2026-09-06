import os
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, session, send_file, current_app
from werkzeug.utils import secure_filename

from models import db, Test, Question, Registration, Candidate, Answer, Violation
from routes.auth import admin_required
from services.registration_import import preview_import_data, commit_import_data
from services.question_generator import generate_questions
from services.timer import initialize_candidate_timer, get_remaining_seconds, is_time_expired
from services.violations import (
    record_violation, acknowledge_warning,
    check_and_enforce_warning_timeout, handle_admin_action
)
from services.scoring import calculate_candidate_score, get_ranked_results
from services.excel_export import generate_results_excel

api_bp = Blueprint('api', __name__)

# ---------------------------------------------------------
# CANDIDATE AUTHENTICATION & LOGIN
# ---------------------------------------------------------

@api_bp.route('/api/candidate/login', methods=['POST'])
def candidate_login():
    data = request.get_json(silent=True) or request.form
    ht_input = data.get('hall_ticket_number', '').strip()
    name_input = data.get('name', '').strip()
    team_input = data.get('team_id', '').strip()
    test_slug = data.get('test_id', '').strip()

    if not ht_input or not name_input or not team_input:
        return jsonify({
            'success': False,
            'error': 'Hall Ticket Number, Name, and Team ID are all required.'
        }), 400

    # 1. Normalize for lookup
    norm_ht = Registration.normalize_string(ht_input)
    norm_team = Registration.normalize_string(team_input)
    norm_name = Registration.normalize_name(name_input)

    # 2. Check registration database
    registration = Registration.query.filter_by(normalized_hall_ticket=norm_ht).first()

    if not registration:
        return jsonify({
            'success': False,
            'error': 'Access Denied: Your Hall Ticket Number is not registered.'
        }), 403

    # Check Team ID and Name match
    reg_norm_team = Registration.normalize_string(registration.team_id)
    reg_norm_name = Registration.normalize_name(registration.name)

    if norm_team != reg_norm_team or norm_name != reg_norm_name:
        return jsonify({
            'success': False,
            'error': 'Access Denied: Your Hall Ticket Number, Name, and Team ID do not match the registered details.'
        }), 403

    # Check registration status
    if not registration.is_active():
        return jsonify({
            'success': False,
            'error': 'Access Denied: Your registration is currently disabled. Please contact the administrator.'
        }), 403

    # 3. Validate Test
    if test_slug:
        test = Test.query.filter_by(test_id=test_slug, active=True).first()
    else:
        test = Test.query.filter_by(active=True).first()

    if not test:
        return jsonify({
            'success': False,
            'error': 'No active test is currently available. Please contact the administrator.'
        }), 404

    # 4. Check for existing candidate attempt for this registration + test
    candidate = Candidate.query.filter_by(
        registration_id=registration.id,
        test_id=test.id
    ).first()

    if not candidate:
        # Create candidate session record
        candidate = Candidate(
            registration_id=registration.id,
            test_id=test.id,
            hall_ticket_number=registration.hall_ticket_number,
            name=registration.name,
            team_id=registration.team_id,
            email=registration.email,
            status='NOT_STARTED',
            duration_minutes=test.duration_minutes
        )
        db.session.add(candidate)
        db.session.commit()

    # Store candidate ID in session
    session['candidate_id'] = candidate.candidate_id

    # Route according to status
    next_url = '/instructions'
    if candidate.status in ['ACTIVE', 'WARNING', 'ACTIVE_AFTER_APPROVAL']:
        next_url = '/test'
    elif candidate.status == 'BLOCKED':
        next_url = '/blocked'
    elif candidate.status in ['COMPLETED', 'AUTO_SUBMITTED']:
        next_url = '/result'

    return jsonify({
        'success': True,
        'message': 'Access Granted',
        'candidate_id': candidate.candidate_id,
        'status': candidate.status,
        'redirect': next_url
    })

# ---------------------------------------------------------
# CANDIDATE EXAM APIS
# ---------------------------------------------------------

@api_bp.route('/api/candidate/start', methods=['POST'])
def candidate_start_test():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Session expired. Please login again.'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found.'}), 404

    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED']:
        return jsonify({'success': False, 'error': 'Test already submitted.', 'redirect': '/result'}), 400

    if candidate.status == 'BLOCKED':
        return jsonify({'success': False, 'error': 'Test is blocked.', 'redirect': '/blocked'}), 403

    if candidate.status == 'NOT_STARTED':
        initialize_candidate_timer(candidate, candidate.test.duration_minutes)
        candidate.status = 'ACTIVE'
        db.session.commit()

    return jsonify({
        'success': True,
        'status': candidate.status,
        'remaining_seconds': candidate.remaining_seconds(),
        'redirect': '/test'
    })

@api_bp.route('/api/candidate/status', methods=['GET'])
def candidate_status():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Session expired'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    # Check for warning 20-second timeout automatically
    timeout_occurred = check_and_enforce_warning_timeout(candidate)

    # Check for test timer expiry
    if candidate.status in ['ACTIVE', 'WARNING', 'ACTIVE_AFTER_APPROVAL'] and is_time_expired(candidate):
        calculate_candidate_score(candidate, is_auto_submit=True)

    rem_seconds = candidate.remaining_seconds()

    # Warning details if warning is active
    warning_seconds_left = 0
    if candidate.warning_active and candidate.warning_expiry_time:
        diff = (candidate.warning_expiry_time - datetime.utcnow()).total_seconds()
        warning_seconds_left = max(0, int(diff))

    latest_v = Violation.query.filter_by(candidate_id=candidate.id).order_by(Violation.timestamp.desc()).first()

    return jsonify({
        'success': True,
        'candidate_id': candidate.candidate_id,
        'name': candidate.name,
        'hall_ticket_number': candidate.hall_ticket_number,
        'team_id': candidate.team_id,
        'status': candidate.status,
        'remaining_seconds': rem_seconds,
        'violations_count': len(candidate.violations),
        'max_violations': candidate.test.max_violations if candidate.test else 3,
        'warning_active': candidate.warning_active,
        'warning_seconds_left': warning_seconds_left,
        'latest_violation_type': latest_v.type if latest_v else None,
        'block_reason': candidate.block_reason
    })

@api_bp.route('/api/candidate/questions', methods=['GET'])
def candidate_questions():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    questions = Question.query.filter_by(test_id=candidate.test_id).order_by(Question.order_index).all()

    # If randomization is enabled for the test, use deterministic shuffle based on candidate ID
    q_list = list(questions)
    if candidate.test and candidate.test.randomize_questions:
        rng = random.Random(candidate.candidate_id)
        rng.shuffle(q_list)

    # Fetch candidate's saved answers
    answers = Answer.query.filter_by(candidate_id=candidate.id).all()
    ans_map = {a.question_id: a.selected_answer for a in answers}

    # Format questions WITHOUT revealing correct_answer or explanation!
    clean_questions = []
    for idx, q in enumerate(q_list):
        q_dict = q.to_dict(include_answer=False)
        q_dict['display_index'] = idx + 1
        q_dict['selected_answer'] = ans_map.get(q.id)
        clean_questions.append(q_dict)

    return jsonify({
        'success': True,
        'questions': clean_questions,
        'total': len(clean_questions),
        'current_index': candidate.current_question_index
    })

@api_bp.route('/api/candidate/answer', methods=['POST'])
def candidate_save_answer():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    if candidate.status in ['BLOCKED', 'WARNING', 'TERMINATED', 'COMPLETED', 'AUTO_SUBMITTED']:
        return jsonify({'success': False, 'error': f"Cannot save answer in '{candidate.status}' state"}), 403

    if candidate.status not in ['ACTIVE', 'ACTIVE_AFTER_APPROVAL']:
        return jsonify({'success': False, 'error': f"Cannot save answer in '{candidate.status}' state"}), 403

    if is_time_expired(candidate):
        calculate_candidate_score(candidate, is_auto_submit=True)
        return jsonify({'success': False, 'error': 'Test time expired. Auto-submitted.'}), 400

    data = request.get_json(silent=True) or request.form
    question_id = data.get('question_id')
    selected_answer = data.get('selected_answer')  # 'A', 'B', 'C', 'D' or None
    current_idx = data.get('current_question_index')

    if question_id is None or str(question_id).strip() == '':
        return jsonify({'success': False, 'error': 'question_id is required'}), 400

    try:
        question_id = int(question_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid question_id'}), 400

    question = Question.query.filter_by(id=question_id, test_id=candidate.test_id).first()
    if not question:
        return jsonify({'success': False, 'error': 'Question is not part of this test'}), 404

    if selected_answer:
        selected_answer = selected_answer.strip().upper()
        if selected_answer not in ['A', 'B', 'C', 'D']:
            return jsonify({'success': False, 'error': 'Invalid answer option'}), 400

    if current_idx is not None:
        candidate.current_question_index = int(current_idx)

    # Upsert answer record
    ans = Answer.query.filter_by(candidate_id=candidate.id, question_id=question_id).first()
    if not ans:
        ans = Answer(
            candidate_id=candidate.id,
            question_id=question_id,
            selected_answer=selected_answer,
            answered_at=datetime.utcnow()
        )
        db.session.add(ans)
    else:
        ans.selected_answer = selected_answer
        ans.answered_at = datetime.utcnow()

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Answer saved',
        'answered_count': candidate.answered_count()
    })

@api_bp.route('/api/candidate/violations', methods=['POST'])
def candidate_log_violation():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED', 'TERMINATED']:
        return jsonify({'success': False, 'message': 'Test already ended'}), 200

    data = request.get_json(silent=True) or request.form
    violation_type = data.get('type', 'TAB_SWITCH').strip()
    metadata = data.get('metadata', {})

    violation, created, msg = record_violation(candidate, violation_type, metadata)

    return jsonify({
        'success': True,
        'created': created,
        'message': msg,
        'violation_count': len(candidate.violations),
        'status': candidate.status,
        'warning_active': candidate.warning_active,
        'warning_seconds_left': 20
    })

@api_bp.route('/api/candidate/acknowledge', methods=['POST'])
def candidate_acknowledge_warning():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    success, msg = acknowledge_warning(candidate)

    return jsonify({
        'success': success,
        'message': msg,
        'status': candidate.status
    })

@api_bp.route('/api/candidate/submit', methods=['POST'])
def candidate_submit():
    cand_id = session.get('candidate_id')
    if not cand_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    candidate = Candidate.query.filter_by(candidate_id=cand_id).first()
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    if candidate.status in ['COMPLETED', 'AUTO_SUBMITTED']:
        return jsonify({'success': True, 'message': 'Already submitted', 'redirect': '/result'})

    calculate_candidate_score(candidate, is_auto_submit=False)

    return jsonify({
        'success': True,
        'message': 'Test submitted successfully',
        'redirect': '/result'
    })

# ---------------------------------------------------------
# ADMIN REST APIS
# ---------------------------------------------------------

@api_bp.route('/api/admin/live', methods=['GET'])
@admin_required
def admin_live_data():
    """
    Polled every 2-3s by the Admin Dashboard.
    Returns summary counters, active candidates list, and recent violation alerts.
    """
    active_test = Test.query.filter_by(active=True).first()
    test_id = active_test.id if active_test else None

    # Overview counters
    total_registered = Registration.query.count()
    total_candidates = Candidate.query.count()
    active_count = Candidate.query.filter(Candidate.status.in_(['ACTIVE', 'WARNING', 'ACTIVE_AFTER_APPROVAL'])).count()
    completed_count = Candidate.query.filter(Candidate.status.in_(['COMPLETED', 'AUTO_SUBMITTED'])).count()
    blocked_count = Candidate.query.filter_by(status='BLOCKED').count()
    flagged_count = Candidate.query.filter_by(status='FLAGGED').count()
    terminated_count = Candidate.query.filter_by(status='TERMINATED').count()

    # Candidate live rows
    candidates = Candidate.query.order_by(Candidate.start_time.desc().nullslast()).all()
    candidate_rows = []
    for c in candidates:
        # check warning timeout on the fly
        check_and_enforce_warning_timeout(c)
        candidate_rows.append(c.to_dict())

    # Recent violations (last 20)
    recent_violations = Violation.query.order_by(Violation.timestamp.desc()).limit(20).all()
    violation_feed = [v.to_dict() for v in recent_violations]

    # Live ranked results
    ranked = get_ranked_results(test_id)

    return jsonify({
        'success': True,
        'counters': {
            'total_registered': total_registered,
            'total_candidates': total_candidates,
            'active': active_count,
            'completed': completed_count,
            'blocked': blocked_count,
            'flagged': flagged_count,
            'terminated': terminated_count
        },
        'candidates': candidate_rows,
        'violations_feed': violation_feed,
        'results': ranked
    })

@api_bp.route('/api/admin/candidates/<int:candidate_id>/action', methods=['POST'])
@admin_required
def admin_candidate_action(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    data = request.get_json(silent=True) or request.form
    action = data.get('action')
    notes = data.get('notes')

    success, msg = handle_admin_action(candidate, action, notes)
    if not success:
        return jsonify({'success': False, 'error': msg}), 400

    return jsonify({
        'success': True,
        'message': msg,
        'status': candidate.status
    })

# ---------------------------------------------------------
# ADMIN REGISTRATION APIS
# ---------------------------------------------------------

@api_bp.route('/api/admin/registrations', methods=['GET'])
@admin_required
def admin_get_registrations():
    search = request.args.get('search', '').strip()
    team_filter = request.args.get('team', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Registration.query

    if search:
        search_norm = f"%{search.upper()}%"
        query = query.filter(
            db.or_(
                Registration.normalized_hall_ticket.like(search_norm),
                Registration.name.ilike(f"%{search}%"),
                Registration.normalized_team_id.like(search_norm)
            )
        )

    if team_filter:
        query = query.filter_by(normalized_team_id=team_filter.upper())

    if status_filter:
        query = query.filter_by(status=status_filter.upper())

    records = query.order_by(Registration.imported_at.desc()).all()

    # Get unique teams for filter dropdown
    teams = [r[0] for r in db.session.query(Registration.team_id).distinct().all() if r[0]]

    return jsonify({
        'success': True,
        'registrations': [r.to_dict() for r in records],
        'total': len(records),
        'teams': sorted(teams)
    })

@api_bp.route('/api/admin/registrations', methods=['POST'])
@admin_required
def admin_create_registration():
    data = request.get_json(silent=True) or request.form
    ht = data.get('hall_ticket_number', '').strip()
    name = data.get('name', '').strip()
    team = data.get('team_id', '').strip()
    email = data.get('email', '').strip() or None
    status = data.get('status', 'ACTIVE').strip().upper()

    if not ht or not name or not team:
        return jsonify({'success': False, 'error': 'Hall Ticket Number, Name, and Team ID are required.'}), 400

    norm_ht = Registration.normalize_string(ht)
    if Registration.query.filter_by(normalized_hall_ticket=norm_ht).first():
        return jsonify({'success': False, 'error': f"Hall Ticket Number '{ht}' is already registered."}), 400

    reg = Registration(
        hall_ticket_number=ht,
        normalized_hall_ticket=norm_ht,
        name=name,
        team_id=team,
        normalized_team_id=Registration.normalize_string(team),
        email=email,
        status=status,
        source_file='Manual Entry',
        imported_at=datetime.utcnow()
    )
    db.session.add(reg)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Registration created', 'registration': reg.to_dict()})

@api_bp.route('/api/admin/registrations/<int:reg_id>', methods=['PUT'])
@admin_required
def admin_update_registration(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    data = request.get_json(silent=True) or request.form

    if 'name' in data:
        reg.name = data['name'].strip()
    if 'team_id' in data:
        reg.team_id = data['team_id'].strip()
        reg.normalized_team_id = Registration.normalize_string(reg.team_id)
    if 'email' in data:
        reg.email = data['email'].strip() or None
    if 'status' in data:
        status = data['status'].strip().upper()
        if status in ['ACTIVE', 'DISABLED']:
            reg.status = status

    reg.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Registration updated', 'registration': reg.to_dict()})

@api_bp.route('/api/admin/registrations/<int:reg_id>', methods=['DELETE'])
@admin_required
def admin_delete_registration(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    db.session.delete(reg)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Registration deleted successfully'})

@api_bp.route('/api/admin/registrations/upload-preview', methods=['POST'])
@admin_required
def admin_upload_preview():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'Empty filename'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return jsonify({
            'success': False,
            'error': 'Unsupported registration file. From Google Sheets, use File → Download → Microsoft Excel (.xlsx) or Comma-separated values (.csv), then upload that downloaded file.'
        }), 400

    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_{int(datetime.utcnow().timestamp())}_{filename}")
    file.save(temp_path)

    try:
        column_map = None
        if 'column_map' in request.form:
            import json
            column_map = json.loads(request.form['column_map'])

        preview_result = preview_import_data(temp_path, column_map)
        preview_result['temp_file_path'] = temp_path
        preview_result['original_filename'] = filename
        return jsonify(preview_result)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'success': False, 'error': str(e)}), 400

@api_bp.route('/api/admin/registrations/confirm-import', methods=['POST'])
@admin_required
def admin_confirm_import():
    data = request.get_json(silent=True) or request.form
    records = data.get('records', [])
    temp_file_path = data.get('temp_file_path')
    original_filename = data.get('original_filename', 'Imported File')
    duplicate_mode = data.get('duplicate_mode', 'skip')  # 'skip', 'keep', 'update'

    if not records and temp_file_path and os.path.exists(temp_file_path):
        preview = preview_import_data(temp_file_path)
        records = preview.get('all_valid_records', [])

    if not records:
        return jsonify({'success': False, 'error': 'No valid records to import.'}), 400

    result = commit_import_data(records, duplicate_mode, original_filename)

    # Clean up temp file
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except OSError:
            pass

    return jsonify(result)

# ---------------------------------------------------------
# ADMIN QUESTION MANAGEMENT & GENERATION
# ---------------------------------------------------------

@api_bp.route('/api/admin/questions/generate', methods=['POST'])
@admin_required
def admin_generate_questions():
    data = request.get_json(silent=True) or request.form
    topic = data.get('topic', 'Data Structures').strip()
    difficulty = data.get('difficulty', 'Medium').strip()
    count = int(data.get('count', 5))
    marks = float(data.get('marks', 1.0))
    instructions = data.get('instructions', '').strip()

    generated = generate_questions(
        topic=topic,
        difficulty=difficulty,
        count=count,
        marks_per_question=marks,
        additional_instructions=instructions
    )

    return jsonify({
        'success': True,
        'topic': topic,
        'difficulty': difficulty,
        'count': len(generated),
        'questions': generated
    })

@api_bp.route('/api/admin/questions/batch-save', methods=['POST'])
@admin_required
def admin_batch_save_questions():
    data = request.get_json(silent=True) or request.form
    test_id = data.get('test_id')
    questions_data = data.get('questions', [])

    test = Test.query.get_or_404(test_id)
    created_count = 0

    # Determine starting order_index
    max_order = db.session.query(db.func.max(Question.order_index)).filter_by(test_id=test.id).scalar() or 0

    for idx, q_data in enumerate(questions_data, start=1):
        q_text = q_data.get('question_text', '').strip()
        opt_a = q_data.get('option_a', '').strip()
        opt_b = q_data.get('option_b', '').strip()
        opt_c = q_data.get('option_c', '').strip()
        opt_d = q_data.get('option_d', '').strip()
        correct_ans = q_data.get('correct_answer', '').strip().upper()
        marks = float(q_data.get('marks', 1.0))

        if not q_text or not opt_a or not opt_b or not opt_c or not opt_d:
            continue
        if correct_ans not in ['A', 'B', 'C', 'D']:
            continue

        q = Question(
            test_id=test.id,
            question_text=q_text,
            option_a=opt_a,
            option_b=opt_b,
            option_c=opt_c,
            option_d=opt_d,
            correct_answer=correct_ans,
            marks=marks,
            topic=q_data.get('topic', 'General'),
            difficulty=q_data.get('difficulty', 'Medium'),
            explanation=q_data.get('explanation', ''),
            order_index=max_order + idx
        )
        db.session.add(q)
        created_count += 1

    test.recalculate_total_marks()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Successfully added {created_count} questions to test '{test.name}'",
        'test_id': test.id,
        'total_questions': len(test.questions),
        'total_marks': test.total_marks
    })

@api_bp.route('/api/admin/questions', methods=['POST'])
@admin_required
def admin_create_single_question():
    data = request.get_json(silent=True) or request.form
    test_id = data.get('test_id')
    test = Test.query.get_or_404(test_id)

    correct_ans = data.get('correct_answer', '').strip().upper()
    if correct_ans not in ['A', 'B', 'C', 'D']:
        return jsonify({'success': False, 'error': 'Valid correct answer (A, B, C, or D) is required'}), 400

    max_order = db.session.query(db.func.max(Question.order_index)).filter_by(test_id=test.id).scalar() or 0

    q = Question(
        test_id=test.id,
        question_text=data.get('question_text', '').strip(),
        option_a=data.get('option_a', '').strip(),
        option_b=data.get('option_b', '').strip(),
        option_c=data.get('option_c', '').strip(),
        option_d=data.get('option_d', '').strip(),
        correct_answer=correct_ans,
        marks=float(data.get('marks', 1.0)),
        topic=data.get('topic', 'General').strip(),
        difficulty=data.get('difficulty', 'Medium').strip(),
        explanation=data.get('explanation', '').strip(),
        order_index=max_order + 1
    )
    db.session.add(q)
    test.recalculate_total_marks()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Question added successfully', 'question': q.to_dict(include_answer=True)})

@api_bp.route('/api/admin/questions/<int:q_id>', methods=['PUT'])
@admin_required
def admin_update_question(q_id):
    q = Question.query.get_or_404(q_id)
    data = request.get_json(silent=True) or request.form

    if 'question_text' in data:
        q.question_text = data['question_text'].strip()
    if 'option_a' in data:
        q.option_a = data['option_a'].strip()
    if 'option_b' in data:
        q.option_b = data['option_b'].strip()
    if 'option_c' in data:
        q.option_c = data['option_c'].strip()
    if 'option_d' in data:
        q.option_d = data['option_d'].strip()
    if 'correct_answer' in data:
        ans = data['correct_answer'].strip().upper()
        if ans in ['A', 'B', 'C', 'D']:
            q.correct_answer = ans
    if 'marks' in data:
        q.marks = float(data['marks'])
    if 'topic' in data:
        q.topic = data['topic'].strip()
    if 'difficulty' in data:
        q.difficulty = data['difficulty'].strip()
    if 'explanation' in data:
        q.explanation = data['explanation'].strip()

    if q.test:
        q.test.recalculate_total_marks()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Question updated successfully', 'question': q.to_dict(include_answer=True)})

@api_bp.route('/api/admin/questions/<int:q_id>', methods=['DELETE'])
@admin_required
def admin_delete_question(q_id):
    q = Question.query.get_or_404(q_id)
    test = q.test
    db.session.delete(q)
    if test:
        test.recalculate_total_marks()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Question deleted successfully'})

# ---------------------------------------------------------
# ADMIN TEST MANAGEMENT
# ---------------------------------------------------------

@api_bp.route('/api/admin/tests', methods=['POST'])
@admin_required
def admin_create_test():
    data = request.get_json(silent=True) or request.form
    test_id_slug = data.get('test_id', '').strip().upper()
    name = data.get('name', '').strip()

    if not test_id_slug or not name:
        return jsonify({'success': False, 'error': 'Test ID and Test Name are required'}), 400

    if Test.query.filter_by(test_id=test_id_slug).first():
        return jsonify({'success': False, 'error': f"Test ID '{test_id_slug}' already exists"}), 400

    test = Test(
        test_id=test_id_slug,
        name=name,
        description=data.get('description', '').strip(),
        duration_minutes=int(data.get('duration_minutes', 30)),
        randomize_questions=bool(data.get('randomize_questions', False)),
        randomize_options=bool(data.get('randomize_options', False)),
        max_violations=int(data.get('max_violations', 3)),
        auto_block=bool(data.get('auto_block', True)),
        auto_terminate=bool(data.get('auto_terminate', False)),
        active=bool(data.get('active', True))
    )
    db.session.add(test)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Test created successfully', 'test': test.to_dict()})

@api_bp.route('/api/admin/tests/<int:t_id>', methods=['PUT'])
@admin_required
def admin_update_test(t_id):
    test = Test.query.get_or_404(t_id)
    data = request.get_json(silent=True) or request.form

    if 'name' in data:
        test.name = data['name'].strip()
    if 'description' in data:
        test.description = data['description'].strip()
    if 'duration_minutes' in data:
        test.duration_minutes = int(data['duration_minutes'])
    if 'randomize_questions' in data:
        test.randomize_questions = bool(data['randomize_questions'])
    if 'randomize_options' in data:
        test.randomize_options = bool(data['randomize_options'])
    if 'max_violations' in data:
        test.max_violations = int(data['max_violations'])
    if 'auto_block' in data:
        test.auto_block = bool(data['auto_block'])
    if 'auto_terminate' in data:
        test.auto_terminate = bool(data['auto_terminate'])
    if 'active' in data:
        test.active = bool(data['active'])

    db.session.commit()
    return jsonify({'success': True, 'message': 'Test updated successfully', 'test': test.to_dict()})

# ---------------------------------------------------------
# EXCEL EXPORT
# ---------------------------------------------------------

@api_bp.route('/api/admin/export/excel', methods=['GET'])
@admin_required
def admin_export_excel():
    test_id = request.args.get('test_id', type=int)
    excel_stream = generate_results_excel(test_id=test_id)
    filename = f"TECHBLITZ_RESULTS_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        excel_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@api_bp.route('/api/admin/questions/import', methods=['POST'])
@admin_required
def admin_import_questions():
    try:
        from services.question_import import read_question_file

        file = request.files.get('file')
        test_id = request.form.get('test_id', type=int)

        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'Please select an Excel (.xlsx) or CSV file.'
            }), 400

        if not test_id:
            return jsonify({
                'success': False,
                'error': 'Please select a test before importing questions.'
            }), 400

        test = Test.query.get_or_404(test_id)

        records, errors = read_question_file(file)

        if errors and not records:
            return jsonify({
                'success': False,
                'error': '\n'.join(errors[:10])
            }), 400

        if not records:
            return jsonify({
                'success': False,
                'error': 'No valid questions were found in the file.'
            }), 400

       # Remove all existing questions from this test
        Question.query.filter_by(test_id=test.id).delete(synchronize_session=False)

# Add only the imported questions
        for idx, data in enumerate(records, start=1):
            db.session.add(
                Question(
                    test_id=test.id,
                    order_index=idx,
                    **data
                )
            )

        test.recalculate_total_marks()
        db.session.commit()


        response = {
            'success': True,
            'message': f'Imported {len(records)} questions into {test.name}.',
            'imported': len(records)
        }

        if errors:
            response['warnings'] = errors[:10]

        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()

        print('MCQ IMPORT ERROR:', repr(e))

        return jsonify({
            'success': False,
            'error': f'Import failed: {str(e)}'
        }), 500
@api_bp.route('/api/admin/questions/delete-all', methods=['POST'])
@admin_required
def admin_delete_all_questions():
    test_id = request.form.get('test_id', type=int)

    if not test_id:
        return jsonify({
            'success': False,
            'error': 'Test ID is required.'
        }), 400

    test = Test.query.get_or_404(test_id)

    deleted = Question.query.filter_by(test_id=test.id).delete(
        synchronize_session=False
    )

    test.recalculate_total_marks()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Deleted {deleted} questions from {test.name}.',
        'deleted': deleted
    })