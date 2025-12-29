from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
import os

from config import config
from models import db, User

app = Flask(__name__)

env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.student import student_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(student_bp, url_prefix='/student')


@app.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    return render_template('index.html')


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('errors/500.html'), 500


@app.context_processor
def inject_user():
    """Inject current user into all templates"""
    return dict(user=current_user)


def create_tables():
    """Create database tables and default admin user"""
    with app.app_context():
        db.create_all()
        
        admin = User.query.filter_by(email='admin@exam.com').first()
        if not admin:
            admin = User(
                email='admin@exam.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('✅ Default admin created: admin@exam.com / admin123')
        else:
            print('✅ Database tables ready')


if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)