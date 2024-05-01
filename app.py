from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
from flask import Flask
from flask_babel import Babel
import os
from dotenv import load_dotenv



app = Flask(__name__)
bcrypt = Bcrypt(app)
babel = Babel(app)
load_dotenv()

app.config['DEBUG'] = os.environ.get('FLASK_DEBUG')

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '' 
app.config['MYSQL_DB'] = 'mydatabase'
mysql = MySQL(app)

# Your secret key for sessions
app.secret_key = '3896d59c098b90d14453299e7bd2bffd62381597c048508e'

# Login form
class LoginForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Registration form
class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    contact = StringField('Contact', validators=[DataRequired()])  # Add contact field
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('delivery', 'Delivery'), ('client', 'Client'), ('admin', 'Admin')], validators=[DataRequired()])  # Update role choices
    submit = SubmitField('Register')

class TaskForm(FlaskForm):
    package_name = StringField('Package Name', validators=[DataRequired()])
    client = SelectField('Client', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[('on the way', 'On the way'), ('dispatched', 'Dispatched'), ('delivered', 'Delivered')], validators=[DataRequired()])
    time = StringField('Time', validators=[DataRequired()])
    submit = SubmitField('Assign Task')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        contact = form.contact.data
        password = form.password.data
        role = form.role.data

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert user data into the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users(name, contact, password, role) VALUES (%s, %s, %s, %s)", (name, contact, hashed_password, role))
        mysql.connection.commit()
        cursor.close()

        flash('Registration successful. You can now login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['role'] = user[4]  # Assuming role is stored in the 4th column
        
            # Determine the destination dashboard based on the user's role
            if user[4] == 'delivery':
                return redirect(url_for('delivery_dashboard'))
            elif user[4] == 'client':
                return redirect(url_for('client_dashboard', client_id=session['user_id']))
            elif user[4] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                # Redirect to the delivery person dashboard as a default
                return redirect(url_for('delivery_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html', form=form)


    

@app.route('/delivery_dashboard', methods=['GET', 'POST'])
def delivery_dashboard():
    if 'user_id' in session and session.get('role') == 'delivery':
        cursor = mysql.connection.cursor()

        # Fetch tasks assigned to the current delivery user
        delivery_id = session['user_id']
        cursor.execute("SELECT * FROM tasks WHERE delivery_id = %s", (delivery_id,))
        tasks = cursor.fetchall()

        # Fetch clients for the form dropdown
        cursor.execute("SELECT id, name FROM users WHERE role = 'client'")
        clients = cursor.fetchall()

        form = TaskForm()
        form.client.choices = [(client[0], client[1]) for client in clients]

        if request.method == 'POST' and form.validate_on_submit():
            package_name = form.package_name.data
            client_id = form.client.data
            status = form.status.data
            time = form.time.data

            cursor.execute("INSERT INTO tasks (package_name, client_id, delivery_id, status, time) VALUES (%s, %s, %s, %s, %s)", (package_name, client_id, delivery_id, status, time))
            mysql.connection.commit()
            flash('Task assigned successfully.', 'success')

            # Update tasks list after assigning new task
            cursor.execute("SELECT * FROM tasks WHERE delivery_id = %s", (delivery_id,))
            tasks = cursor.fetchall()

        cursor.close()
        return render_template('delivery_dashboard.html', form=form, tasks=tasks)
    return redirect(url_for('login'))

@app.route('/client_dashboard', methods=['GET', 'POST'])
def client_dashboard():
    if 'user_id' in session and session.get('role') == 'client':
        cursor = mysql.connection.cursor()

        client_id = session['user_id']
        
        # Fetch only required fields (package_name, status, and time)
        cursor.execute("SELECT package_name, status, time FROM tasks WHERE client_id = %s", (client_id,))
        tasks = cursor.fetchall()
        
        cursor.close()
        
        return render_template('client_dashboard.html', tasks=tasks)
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'name' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name, role FROM users")
        users = cursor.fetchall()
        cursor.close()
        return render_template('admin_dashboard.html', users=users)
    else:
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('login'))
    
@app.route('/redirect_dashboard/<name>/<role>')
def redirect_dashboard(name, role):
    if role == 'delivery':
        return redirect(url_for('delivery_dashboard', name=name))
    elif role == 'client':
        return redirect(url_for('client_dashboard', name=name))
    else:
        # Handle other roles or invalid cases
        return redirect(url_for('admin_dashboard'))

    

if __name__ == '__main__':
    app.run()
