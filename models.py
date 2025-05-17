from app import db
from datetime import datetime

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    courses = db.relationship('Course', backref='created_courses', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Course(db.Model):
    course_id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    materials = db.relationship('CourseMaterial', backref='course', cascade='all, delete-orphan', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', cascade='all, delete-orphan', lazy=True)
    instructor = db.relationship('User', backref='instructed_courses', lazy=True) # Changed backref name

    def __repr__(self):
        return f'<Course {self.course_name}>'

class Enrollment(db.Model):
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

    def __repr__(self):
        return f'<Enrollment student_id={self.student_id} course_id={self.course_id}>'

class CourseMaterial(db.Model):
    material_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'), nullable=False)
    material_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(255))
    url = db.Column(db.String(255))

    def __repr__(self):
        return f'<CourseMaterial title="{self.title}" type="{self.material_type}">'