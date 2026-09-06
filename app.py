import os
from flask import Flask
from config import Config
from models import db
from data.seed import seed_database

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Production deployments must provide secrets explicitly. Tests may use
    # safe local defaults so the suite remains self-contained.
    if app.config.get('TESTING'):
        app.config.setdefault('SECRET_KEY', 'test-secret-key')
        app.config.setdefault('ADMIN_USERNAME', 'admin')
        app.config.setdefault('ADMIN_PASSWORD', 'admin123')
    else:
        missing = [k for k in ('SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD')
                   if not app.config.get(k)]
        if missing:
            raise RuntimeError(
                'Missing required environment variables: ' + ', '.join(missing)
            )

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.candidate import candidate_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Auto-seed database tables on first launch
    with app.app_context():
        seed_database()

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"Starting TECHBLITZ platform on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
