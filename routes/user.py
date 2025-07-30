# routes/user.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, ParkingLot, ParkingSpot, Reservation
from datetime import datetime
import re
from pytz import timezone

user_bp = Blueprint('user', __name__, template_folder='../templates')

#time standard for initializing time for each action user takes
IST = timezone('Asia/Kolkata')

# register user
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    #check if authenticated
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    #requesting from the form and posting it
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        #validating username and password
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username can only contain letters, numbers, and underscores.')
        
        if not password or len(password) < 5:
            errors.append('Password must be at least 5 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        #popping errors
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('user/register.html')
        
        #check if username already exists in db
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('user/register.html')
        
        #create user
        try:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login with your credentials.', 'success')
            return redirect(url_for('user.login'))
        
        #for any unexpected error
        except Exception as e:
            db.session.rollback()
            flash('Error during registration. Please try again.', 'danger')
            return render_template('user/register.html')

    return render_template('user/register.html')


#user login
@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    #check for authentication
    if current_user.is_authenticated:
        #weather to admin dashboard or user dashboard
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))
    
    #getting data from the form
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        #if username or password field is empty
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('user/login.html')
        
        #match the credentials from the db
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        #in case some unexpected error
        flash('Invalid username or password.', 'danger')

    return render_template('user/login.html')

