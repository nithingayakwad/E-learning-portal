from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Or your database URI
db = SQLAlchemy(app)

# Import your routes AFTER the db object is created
from routes import *

# Import your models AFTER the db object is created
from models import User, Course, Enrollment, CourseMaterial

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True ,host='0.0.0.0')