from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_student(self):
        """Check if user is student"""
        return self.role == 'student'
    
    def __repr__(self):
        return f'<User {self.email}>'


class Student(db.Model):
    """Student model"""
    __tablename__ = 'student'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    department = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    results = db.relationship('Result', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.name}>'


class Subject(db.Model):
    """Subject model"""
    __tablename__ = 'subject'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    exams = db.relationship('Exam', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Subject {self.name}>'


class Exam(db.Model):
    """Exam model"""
    __tablename__ = 'exam'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    pass_marks = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('Question', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    results = db.relationship('Result', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_question_count(self):
        """Get total number of questions"""
        return self.questions.count()
    
    def __repr__(self):
        return f'<Exam {self.title}>'


class Question(db.Model):
    """Question model"""
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    marks = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Question {self.id}>'


class Result(db.Model):
    """Result model"""
    __tablename__ = 'result'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'exam_id', name='unique_attempt'),
    )
    
    def __repr__(self):
        return f'<Result Student:{self.student_id} Exam:{self.exam_id}>'