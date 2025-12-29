from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, Student, Exam, Question, Result
from datetime import datetime, timedelta

student_bp = Blueprint('student', __name__)


def student_required(f):
    """Decorator to require student access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_student():
    """Get current student object"""
    if current_user.is_authenticated and current_user.is_student():
        return Student.query.filter_by(user_id=current_user.id).first()
    return None


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard"""
    student = get_current_student()
    
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('index'))
    
    available_exams = Exam.query.all()
    attempted_exam_ids = [r.exam_id for r in student.results]
    available_exams = [exam for exam in available_exams if exam.id not in attempted_exam_ids]
    recent_results = student.results.order_by(Result.attempted_at.desc()).limit(5).all()
    
    return render_template('student/dashboard.html',
                         student=student,
                         available_exams=available_exams,
                         recent_results=recent_results)


@student_bp.route('/exam/<int:exam_id>/start')
@login_required
@student_required
def start_exam(exam_id):
    """Start an exam"""
    student = get_current_student()
    exam = Exam.query.get_or_404(exam_id)
    
    existing_result = Result.query.filter_by(
        student_id=student.id,
        exam_id=exam_id
    ).first()
    
    if existing_result:
        flash('You have already attempted this exam.', 'warning')
        return redirect(url_for('student.view_result', result_id=existing_result.id))
    
    if exam.get_question_count() == 0:
        flash('This exam has no questions yet.', 'warning')
        return redirect(url_for('student.dashboard'))
    
    session['exam_start_time'] = datetime.utcnow().isoformat()
    session['exam_id'] = exam_id
    session['current_question'] = 0
    session['answers'] = {}
    
    return redirect(url_for('student.take_exam', exam_id=exam_id))


@student_bp.route('/exam/<int:exam_id>/take')
@login_required
@student_required
def take_exam(exam_id):
    """Take exam page"""
    if session.get('exam_id') != exam_id:
        flash('Invalid exam session.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    student = get_current_student()
    exam = Exam.query.get_or_404(exam_id)
    
    existing_result = Result.query.filter_by(
        student_id=student.id,
        exam_id=exam_id
    ).first()
    
    if existing_result:
        flash('You have already attempted this exam.', 'warning')
        return redirect(url_for('student.view_result', result_id=existing_result.id))
    
    questions = Question.query.filter_by(exam_id=exam_id).all()
    
    if not questions:
        flash('This exam has no questions.', 'warning')
        return redirect(url_for('student.dashboard'))
    
    start_time = datetime.fromisoformat(session.get('exam_start_time'))
    elapsed = (datetime.utcnow() - start_time).total_seconds() / 60
    remaining_time = max(0, exam.duration - int(elapsed))
    
    if remaining_time <= 0:
        return redirect(url_for('student.submit_exam', exam_id=exam_id))
    
    current_question_index = session.get('current_question', 0)
    answers = session.get('answers', {})
    
    return render_template('student/exam.html',
                         exam=exam,
                         questions=questions,
                         current_index=current_question_index,
                         answers=answers,
                         remaining_time=remaining_time)


@student_bp.route('/exam/<int:exam_id>/answer', methods=['POST'])
@login_required
@student_required
def save_answer(exam_id):
    """Save answer for a question"""
    if session.get('exam_id') != exam_id:
        return jsonify({'success': False, 'message': 'Invalid exam session'})
    
    question_id = request.form.get('question_id', type=int)
    answer = request.form.get('answer', '').strip().upper()
    
    if not question_id or answer not in ['A', 'B', 'C', 'D']:
        return jsonify({'success': False, 'message': 'Invalid answer'})
    
    answers = session.get('answers', {})
    answers[str(question_id)] = answer
    session['answers'] = answers
    
    return jsonify({'success': True})


@student_bp.route('/exam/<int:exam_id>/submit', methods=['POST', 'GET'])
@login_required
@student_required
def submit_exam(exam_id):
    """Submit exam and calculate result"""
    if session.get('exam_id') != exam_id:
        flash('Invalid exam session.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    student = get_current_student()
    exam = Exam.query.get_or_404(exam_id)
    
    existing_result = Result.query.filter_by(
        student_id=student.id,
        exam_id=exam_id
    ).first()
    
    if existing_result:
        flash('You have already attempted this exam.', 'warning')
        return redirect(url_for('student.view_result', result_id=existing_result.id))
    
    answers = session.get('answers', {})
    questions = Question.query.filter_by(exam_id=exam_id).all()
    score = 0
    total_marks = 0
    
    for question in questions:
        total_marks += question.marks
        student_answer = answers.get(str(question.id), '').upper()
        if student_answer == question.correct_answer:
            score += question.marks
    
    percentage = (score / total_marks * 100) if total_marks > 0 else 0
    status = 'pass' if score >= exam.pass_marks else 'fail'
    
    try:
        result = Result(
            student_id=student.id,
            exam_id=exam_id,
            score=score,
            total_marks=total_marks,
            percentage=percentage,
            status=status
        )
        db.session.add(result)
        db.session.commit()
        
        session.pop('exam_id', None)
        session.pop('exam_start_time', None)
        session.pop('current_question', None)
        session.pop('answers', None)
        
        flash('Exam submitted successfully!', 'success')
        return redirect(url_for('student.view_result', result_id=result.id))
    
    except Exception as e:
        db.session.rollback()
        flash('Error submitting exam. Please try again.', 'danger')
        print(f"Submit exam error: {e}")
        return redirect(url_for('student.dashboard'))


@student_bp.route('/result/<int:result_id>')
@login_required
@student_required
def view_result(result_id):
    """View exam result"""
    student = get_current_student()
    result = Result.query.get_or_404(result_id)
    
    if result.student_id != student.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/result.html', result=result)


@student_bp.route('/history')
@login_required
@student_required
def history():
    """View exam history"""
    student = get_current_student()
    results = student.results.order_by(Result.attempted_at.desc()).all()
    
    return render_template('student/history.html', results=results)


@student_bp.route('/profile')
@login_required
@student_required
def profile():
    """View student profile"""
    student = get_current_student()
    return render_template('student/profile.html', student=student)