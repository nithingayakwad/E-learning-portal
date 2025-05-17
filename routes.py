from flask import render_template, request, redirect, url_for, session, flash, abort
from app import app, db
from models import User, Course, Enrollment, CourseMaterial
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, URL, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS_IMAGE = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EXTENSIONS_VIDEO = {'mp4', 'webm', 'ogg'}
UPLOAD_FOLDER = 'static/uploads'  # Create this folder in your project

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('student', 'Student'), ('instructor', 'Instructor')], validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateCourseForm(FlaskForm):
    course_name = StringField('Course Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Create Course')

class AddMaterialForm(FlaskForm):
    title = StringField('Material Title', validators=[DataRequired()])
    material_type = SelectField('Material Type', choices=[('pdf', 'PDF'), ('image', 'Image'), ('link', 'Link'), ('video_url', 'Video URL'), ('video_upload', 'Video Upload')], validators=[DataRequired()])
    file = FileField('Upload File', validators=[Optional()])
    url = StringField('URL', validators=[Optional(), URL()])
    submit = SubmitField('Add Material')

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password, role=form.role.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.user_id
            session['role'] = user.role
            return redirect(url_for('index'))
        else:
            return render_template('login.html', form=form, error='Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/student/dashboard', methods=['GET', 'POST'])
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    student_id = session['user_id']
    enrollments = Enrollment.query.filter_by(student_id=student_id).all()
    enrolled_courses = [enrollment.course for enrollment in enrollments]
    enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]

    search_query = request.form.get('search_query')
    available_courses_query = Course.query.filter(~Course.course_id.in_(enrolled_course_ids))

    if search_query:
        available_courses = available_courses_query.filter(Course.course_name.ilike(f'%{search_query}%')).all()
    else:
        available_courses = available_courses_query.all()

    return render_template('student_dashboard.html', courses=enrolled_courses, available_courses=available_courses, search_query=search_query)

@app.route('/instructor/dashboard')
def instructor_dashboard():
    if 'user_id' not in session or session['role'] != 'instructor':
        return redirect(url_for('login'))
    instructor_id = session['user_id']
    courses = Course.query.filter_by(instructor_id=instructor_id).all()
    return render_template('instructor_dashboard.html', courses=courses)

@app.route('/instructor/create_course', methods=['GET', 'POST'])
def create_course():
    if 'user_id' not in session or session['role'] != 'instructor':
        return redirect(url_for('login'))
    form = CreateCourseForm()
    if form.validate_on_submit():
        instructor_id = session['user_id']
        new_course = Course(instructor_id=instructor_id, course_name=form.course_name.data, description=form.description.data)
        db.session.add(new_course)
        db.session.commit()
        return redirect(url_for('instructor_dashboard'))
    return render_template('create_course.html', form=form)

@app.route('/course/<int:course_id>')
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    return render_template('course_details.html', course=course, materials=materials)

@app.route('/instructor/course/<int:course_id>/manage', methods=['GET', 'POST'])
def manage_course(course_id):
    print(f"UPLOAD_FOLDER is set to: {app.config['UPLOAD_FOLDER']}")
    if 'user_id' not in session or session['role'] != 'instructor':
        return redirect(url_for('login'))
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != session['user_id']:
        return "Unauthorized", 403

    form = AddMaterialForm()
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()

    if form.validate_on_submit():
        title = form.title.data
        material_type = form.material_type.data
        file = form.file.data
        url = form.url.data

        if material_type == 'pdf' and file and allowed_file(file.filename, {'pdf'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            new_material = CourseMaterial(course_id=course_id, material_type=material_type, title=title, file_path=filepath)
            db.session.add(new_material)
            db.session.commit()
            return redirect(url_for('manage_course', course_id=course_id))
        elif material_type == 'image' and file and allowed_file(file.filename, ALLOWED_EXTENSIONS_IMAGE):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            new_material = CourseMaterial(course_id=course_id, material_type=material_type, title=title, file_path=filepath)
            db.session.add(new_material)
            db.session.commit()
            return redirect(url_for('manage_course', course_id=course_id))
        elif material_type == 'link' and url:
            new_material = CourseMaterial(course_id=course_id, material_type=material_type, title=title, url=url)
            db.session.add(new_material)
            db.session.commit()
            return redirect(url_for('manage_course', course_id=course_id))
        elif material_type == 'video_url' and url:
            new_material = CourseMaterial(course_id=course_id, material_type='video', title=title, url=url) # Store as 'video' for consistent handling in template
            db.session.add(new_material)
            db.session.commit()
            return redirect(url_for('manage_course', course_id=course_id))
        elif material_type == 'video_upload' and file and allowed_file(file.filename, ALLOWED_EXTENSIONS_VIDEO):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            new_material = CourseMaterial(course_id=course_id, material_type='video', title=title, file_path=filepath) # Store as 'video'
            db.session.add(new_material)
            db.session.commit()
            return redirect(url_for('manage_course', course_id=course_id))
        else:
            flash('Please select a valid file or provide a URL based on the material type.', 'warning')
            return redirect(url_for('manage_course', course_id=course_id))

    return render_template('manage_course.html', course=course, form=form, materials=materials)

@app.route('/instructor/course/<int:course_id>/material/<int:material_id>/delete')
def delete_material(course_id, material_id):
    if 'user_id' not in session or session['role'] != 'instructor':
        return redirect(url_for('login'))
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != session['user_id']:
        return "Unauthorized", 403
    material = CourseMaterial.query.get_or_404(material_id)
    # Optionally delete the file from the file system if it exists
    if material.file_path:
        try:
            os.remove(material.file_path)
        except FileNotFoundError:
            pass
    db.session.delete(material)
    db.session.commit()
    return redirect(url_for('manage_course', course_id=course_id))

@app.route('/instructor/course/<int:course_id>/delete')
def delete_course(course_id):
    if 'user_id' not in session or session['role'] != 'instructor':
        return redirect(url_for('login'))
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != session['user_id']:
        return "Unauthorized", 403

    enrollments_to_delete = Enrollment.query.filter_by(course_id=course_id).all()
    for enrollment in enrollments_to_delete:
        db.session.delete(enrollment)

    materials_to_delete = CourseMaterial.query.filter_by(course_id=course_id).all()
    for material in materials_to_delete:
        if material.file_path:
            try:
                os.remove(material.file_path)
            except FileNotFoundError:
                pass
        db.session.delete(material)

    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{course.course_name}" and its associated data have been deleted.', 'success')
    return redirect(url_for('instructor_dashboard'))

@app.route('/student/enroll/<int:course_id>')
def enroll_course(course_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    student_id = session['user_id']
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if not enrollment:
        new_enrollment = Enrollment(student_id=student_id, course_id=course_id)
        db.session.add(new_enrollment)
        db.session.commit()
    return redirect(url_for('student_dashboard'))

@app.route('/student/unenroll/<int:course_id>')
def unenroll_course(course_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    student_id = session['user_id']
    enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
    return redirect(url_for('student_dashboard'))