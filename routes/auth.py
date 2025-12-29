from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Student

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.email}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration"""
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        roll_number = request.form.get('roll_number', '').strip()
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        
        if not all([name, email, password, confirm_password, roll_number]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('auth.login'))
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered.', 'danger')
            return redirect(url_for('auth.register'))
        
        try:
            user = User(email=email, role='student')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            
            student = Student(
                user_id=user.id,
                name=name,
                roll_number=roll_number,
                department=department,
                phone=phone
            )
            db.session.add(student)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            print(f"Registration error: {e}")
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))