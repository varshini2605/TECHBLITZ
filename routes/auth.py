from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from models import Admin

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Unauthorized. Admin login required.'}), 401
            return redirect(url_for('auth.admin_login_page'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/admin/login', methods=['GET'])
def admin_login_page():
    if session.get('admin_id'):
        return redirect(url_for('admin.dashboard_page'))
    return render_template('admin_login.html')

@auth_bp.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('auth.admin_login_page'))

@auth_bp.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.get_json(silent=True) or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required'}), 400
        
    admin = Admin.query.filter_by(username=username).first()
    if not admin or not admin.check_password(password):
        return jsonify({'success': False, 'error': 'Invalid administrator credentials'}), 401
        
    session['admin_id'] = admin.id
    session['admin_username'] = admin.username
    session.permanent = True
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'redirect': url_for('admin.dashboard_page')
    })
