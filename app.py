import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_advanced'
DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Admin specific email
ADMIN_EMAIL = 'dipesh97@gmail.com'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_email') != ADMIN_EMAIL:
            flash('Access Denied: Admins only!', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    with app.app_context():
        # First, drop existing tables if they exist to apply new schema cleanly
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS courses')
        cursor.execute('DROP TABLE IF EXISTS students')
        cursor.execute('DROP TABLE IF EXISTS users')
        
        # Create courses table
        cursor.execute('''
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL,
                description TEXT NOT NULL,
                duration TEXT NOT NULL
            )
        ''')
        
        # Create students (enrollments) table
        cursor.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                course TEXT NOT NULL
            )
        ''')

        # Create users table for authentication
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Insert JEE and NEET specific courses
        sample_courses = [
            ('JEE Main Target Course', 'Comprehensive coverage of Class 11 & 12 syllabus for JEE Main.', '1 Year'),
            ('JEE Advanced Achievers', 'Intensive problem-solving and concept building for IIT-JEE.', '1 Year'),
            ('NEET UG Foundation', 'Expert guidance for biology, physics, and chemistry for NEET aspirants.', '2 Years'),
            ('Crash Course JEE/NEET', 'Quick revision and mock test series for upcoming exams.', '3 Months')
        ]
        cursor.executemany('''
            INSERT INTO courses (course_name, description, duration)
            VALUES (?, ?, ?)
        ''', sample_courses)
            
        conn.commit()
        conn.close()

@app.route('/')
def home():
    conn = get_db()
    courses = conn.execute('SELECT * FROM courses LIMIT 3').fetchall()
    conn.close()
    return render_template('home.html', courses=courses)

@app.route('/courses')
def courses():
    conn = get_db()
    courses_list = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    return render_template('courses.html', courses=courses_list)

@app.route('/enroll', methods=('GET', 'POST'))
def enroll():
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        course = request.form['course']
        
        if not name or not email or not phone or not course:
            flash('All fields are required!', 'error')
        else:
            conn.execute('INSERT INTO students (name, email, phone, course) VALUES (?, ?, ?, ?)',
                         (name, email, phone, course))
            conn.commit()
            flash('Enrollment successful! We will contact you soon.', 'success')
            return redirect(url_for('enroll'))
            
    courses_list = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    return render_template('enroll.html', courses=courses_list)

@app.route('/contact', methods=('GET', 'POST'))
def contact():
    if request.method == 'POST':
        name = request.form['name']
        message = request.form['message']
        if not name or not message:
            flash('Name and Message are required!', 'error')
        else:
            flash('Thank you for reaching out! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/faculty')
def faculty():
    return render_template('faculty.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Please login.', 'error')
        finally:
            conn.close()
            
    return render_template('signup.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    students = conn.execute('SELECT * FROM students').fetchall()
    courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    return render_template('admin.html', students=students, courses=courses)

@app.route('/admin/add', methods=('POST',))
@admin_required
def add_student():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    course = request.form['course']
    
    if not name or not email or not phone or not course:
        flash('All fields are required to add a student!', 'error')
    else:
        conn = get_db()
        conn.execute('INSERT INTO students (name, email, phone, course) VALUES (?, ?, ?, ?)',
                     (name, email, phone, course))
        conn.commit()
        conn.close()
        flash('Student added successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:student_id>', methods=('GET', 'POST'))
@admin_required
def edit_student(student_id):
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        course = request.form['course']
        
        if not name or not email or not phone or not course:
            flash('All fields are required to edit a student!', 'error')
        else:
            conn.execute('UPDATE students SET name = ?, email = ?, phone = ?, course = ? WHERE id = ?',
                         (name, email, phone, course, student_id))
            conn.commit()
            flash('Student updated successfully!', 'success')
            conn.close()
            return redirect(url_for('admin'))
            
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('admin'))
        
    return render_template('admin_edit.html', student=student, courses=courses)

@app.route('/admin/delete/<int:student_id>', methods=('POST',))
@admin_required
def delete_student(student_id):
    conn = get_db()
    conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()
    flash('Enrollment record deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '').lower()
    
    # Simple rule-based coaching bot
    coaching_keywords = ['fee', 'course', 'jee', 'neet', 'batch', 'faculty', 'teacher', 'duration', 'result', 'admission', 'enroll', 'timing', 'schedule', 'rank', 'coaching', 'institute', 'apex', 'class', 'hello', 'hi']
    
    # Check if message is related to coaching
    if not any(keyword in message for keyword in coaching_keywords):
        return jsonify({'response': "I can only answer questions related to Apex Coaching, such as courses, fees, faculties, and results! 😊 Please ask me something about our institute. 🙏"})
    
    if 'fee' in message:
        response = "Our fee structure varies depending on the course. 📚 Please visit the 'Courses' page or contact our office for detailed fee information! 💼"
    elif 'course' in message or 'jee' in message or 'neet' in message:
        response = "We offer premium courses for JEE Main, JEE Advanced, and NEET UG! 🚀 They include 1-year, 2-year, and crash courses. Check out the 'Courses' tab for more info! 📖"
    elif 'faculty' in message or 'teacher' in message:
        response = "Our faculty comprises highly experienced IITians, NITians, and top medical professionals! 👨‍🏫👩‍🔬 You can learn more about them on our 'Faculty' page. ✨"
    elif 'result' in message or 'rank' in message:
        response = "We consistently produce top rankers in JEE and NEET every year! 🏆 Hundreds of our students get selected. See the 'Results' page for our latest star achievers! 🌟"
    elif 'enroll' in message or 'admission' in message:
        response = "You can easily enroll by creating an account and visiting the 'Enroll' section! 📝 We look forward to having you! 🎉"
    elif 'coaching' in message or 'institute' in message or 'apex' in message:
        response = "Apex Coaching is a premier institute dedicated to helping students crack JEE and NEET! 🌟 We offer expert faculty, comprehensive study materials, and a great learning environment. What specifically would you like to know about? 🤔"
    elif 'hi' in message or 'hello' in message:
        response = "Hello! 👋 Welcome to Apex Coaching. How can I help you with your JEE or NEET preparation today? 😊"
    else:
        response = "That's a great question about our institute! 🤔 For more specific details, please feel free to reach out via our 'Contact' page, and our team will assist you! 📞"
        
    return jsonify({'response': response})

# Initialize DB if it doesn't exist
if not os.path.exists(DATABASE):
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
