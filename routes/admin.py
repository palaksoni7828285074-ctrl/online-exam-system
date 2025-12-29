from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Student, Subject, Exam, Question, Result
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with statistics"""
    total_students = Student.query.count()
    total_subjects = Subject.query.count()
    total_exams = Exam.query.count()
    total_results = Result.query.count()
    
    recent_students = Student.query.order_by(Student.created_at.desc()).limit(5).all()
    recent_results = Result.query.order_by(Result.attempted_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_subjects=total_subjects,
                         total_exams=total_exams,
                         total_results=total_results,
                         recent_students=recent_students,
                         recent_results=recent_results)


@admin_bp.route('/students')
@login_required
@admin_required
def students():
    """View all students"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Student.query
    
    if search:
        query = query.filter(
            (Student.name.contains(search)) |
            (Student.roll_number.contains(search)) |
            (Student.department.contains(search))
        )
    
    students = query.order_by(Student.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/students.html', students=students, search=search)


@admin_bp.route('/students/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_student(id):
    """Delete a student"""
    student = Student.query.get_or_404(id)
    try:
        user = User.query.get(student.user_id)
        db.session.delete(student)
        if user:
            db.session.delete(user)
        db.session.commit()
        flash('Student deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting student.', 'danger')
        print(f"Delete error: {e}")
    
    return redirect(url_for('admin.students'))


@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects():
    """View all subjects"""
    subjects = Subject.query.order_by(Subject.created_at.desc()).all()
    return render_template('admin/subjects.html', subjects=subjects)


@admin_bp.route('/subjects/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_subject():
    """Add new subject"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name or not code:
            flash('Subject name and code are required.', 'danger')
            return redirect(url_for('admin.add_subject'))
        
        if Subject.query.filter_by(code=code).first():
            flash('Subject code already exists.', 'danger')
            return redirect(url_for('admin.add_subject'))
        
        try:
            subject = Subject(name=name, code=code, description=description)
            db.session.add(subject)
            db.session.commit()
            flash('Subject added successfully.', 'success')
            return redirect(url_for('admin.subjects'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding subject.', 'danger')
            print(f"Add subject error: {e}")
    
    return render_template('admin/add_subject.html')


@admin_bp.route('/subjects/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_subject(id):
    """Delete a subject"""
    subject = Subject.query.get_or_404(id)
    try:
        db.session.delete(subject)
        db.session.commit()
        flash('Subject deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting subject.', 'danger')
        print(f"Delete error: {e}")
    
    return redirect(url_for('admin.subjects'))


@admin_bp.route('/exams')
@login_required
@admin_required
def exams():
    """View all exams"""
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams)


@admin_bp.route('/exams/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_exam():
    """Add new exam"""
    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        title = request.form.get('title', '').strip()
        duration = request.form.get('duration', type=int)
        total_marks = request.form.get('total_marks', type=int)
        pass_marks = request.form.get('pass_marks', type=int)
        
        if not all([subject_id, title, duration, total_marks, pass_marks]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.add_exam'))
        
        try:
            exam = Exam(
                subject_id=subject_id,
                title=title,
                duration=duration,
                total_marks=total_marks,
                pass_marks=pass_marks
            )
            db.session.add(exam)
            db.session.commit()
            flash('Exam created successfully. Now add questions.', 'success')
            return redirect(url_for('admin.questions', exam_id=exam.id))
        except Exception as e:
            db.session.rollback()
            flash('Error creating exam.', 'danger')
            print(f"Add exam error: {e}")
    
    subjects = Subject.query.all()
    return render_template('admin/add_exam.html', subjects=subjects)


@admin_bp.route('/exams/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_exam(id):
    """Delete an exam"""
    exam = Exam.query.get_or_404(id)
    try:
        db.session.delete(exam)
        db.session.commit()
        flash('Exam deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting exam.', 'danger')
        print(f"Delete error: {e}")
    
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/<int:exam_id>/questions')
@login_required
@admin_required
def questions(exam_id):
    """View questions for an exam"""
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()
    return render_template('admin/questions.html', exam=exam, questions=questions)


@admin_bp.route('/exams/<int:exam_id>/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_question(exam_id):
    """Add question to exam"""
    exam = Exam.query.get_or_404(exam_id)
    
    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        marks = request.form.get('marks', 1, type=int)
        
        if not all([question_text, option_a, option_b, option_c, option_d, correct_answer]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.add_question', exam_id=exam_id))
        
        if correct_answer not in ['A', 'B', 'C', 'D']:
            flash('Correct answer must be A, B, C, or D.', 'danger')
            return redirect(url_for('admin.add_question', exam_id=exam_id))
        
        try:
            question = Question(
                exam_id=exam_id,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer,
                marks=marks
            )
            db.session.add(question)
            db.session.commit()
            flash('Question added successfully.', 'success')
            
            if request.form.get('add_more'):
                return redirect(url_for('admin.add_question', exam_id=exam_id))
            else:
                return redirect(url_for('admin.questions', exam_id=exam_id))
        except Exception as e:
            db.session.rollback()
            flash('Error adding question.', 'danger')
            print(f"Add question error: {e}")
    
    return render_template('admin/add_question.html', exam=exam)


@admin_bp.route('/questions/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_question(id):
    """Delete a question"""
    question = Question.query.get_or_404(id)
    exam_id = question.exam_id
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting question.', 'danger')
        print(f"Delete error: {e}")
    
    return redirect(url_for('admin.questions', exam_id=exam_id))


@admin_bp.route('/results')
@login_required
@admin_required
def results():
    """View all results"""
    page = request.args.get('page', 1, type=int)
    results = Result.query.order_by(Result.attempted_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/results.html', results=results)


@admin_bp.route('/results/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_result(id):
    """Delete a result"""
    result = Result.query.get_or_404(id)
    try:
        db.session.delete(result)
        db.session.commit()
        flash('Result deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting result.', 'danger')
        print(f"Delete error: {e}")
    
    return redirect(url_for('admin.results'))