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


#user logout
@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('user.login'))


#user dashboard
@user_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    #check for admin
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    #initially empty search query, shows all of them
    search_query = ''
    lots = ParkingLot.query.all()
    if request.method == 'POST':
        search_query = request.form.get('search', '').strip()

        #getting form data and filtering according to it
        if search_query:
            lots = ParkingLot.query.filter(
                (ParkingLot.prime_location_name.ilike(f'%{search_query}%')) |
                (ParkingLot.pincode.ilike(f'%{search_query}%'))
            ).all()

    for lot in lots:
        lot.available_spots = lot.get_available_spots_count()
        lot.occupied_spots = lot.get_occupied_spots_count()
    
    #get all the users reservation
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.created_at.desc()).all()
    
    #calculatr reservation stats
    active_reservations = [r for r in reservations if r.is_active()]
    past_reservations = [r for r in reservations if not r.is_active()]
    
    active_count = len(active_reservations)
    past_count = len(past_reservations)
    
    #total amount spent on reservation
    total_spent = sum(res.total_cost for res in reservations if res.total_cost)
    
    #prepare chart for total_cost
    chart_labels = []
    chart_data = []
    for res in past_reservations:
        if res.total_cost:
            chart_labels.append(f"Reservation #{res.id}")
            chart_data.append(res.total_cost)
    
    #get all currently active reservation
    current_reservation = None
    if active_count > 0:
        current_reservation = active_reservations[0]
    
    return render_template('user/dashboard.html',
                         lots=lots,
                         reservations=reservations,
                         active=active_count,
                         past=past_count,
                         total_spent=total_spent,
                         chart_labels=chart_labels,
                         chart_data=chart_data,
                         current_reservation=current_reservation,
                         history=reservations,
                         search_query=search_query)


#user spot booking
@user_bp.route('/book/<int:lot_id>', methods=['GET', 'POST'], endpoint='book')
@login_required
def book(lot_id):
    #check for user
    if current_user.is_admin:
        flash('Admins cannot book parking spots.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    #get all parking lots
    lot = ParkingLot.query.get_or_404(lot_id)
    
    #check if user has active reservation
    active_reservation = Reservation.query.filter_by(
        user_id=current_user.id, 
        leaving_timestamp=None
    ).first()
    
    #user needs to release the active one to book new reservation
    if active_reservation:
        flash('You already have an active reservation. Please release it before booking a new spot.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    #find first empty spot
    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    
    #in case unavailability of spots
    if not available_spot:
        flash(f'No available spots in {lot.prime_location_name}. Please try another lot.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    #get vehicle no and authenticate it
    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no', '').strip()

        if not vehicle_no or len(vehicle_no) < 4:
            flash('Please enter a valid vehicle number.', 'danger')
            return render_template('user/book.html', lot=lot, spot=available_spot, vehicle_no=vehicle_no)
        
        #reserve the spot
        parking_time_ist = datetime.utcnow().replace(tzinfo=timezone('UTC')).astimezone(IST)
        available_spot.status = 'O'
        reservation = Reservation(
            user_id=current_user.id,
            spot_id=available_spot.id,
            parking_timestamp=parking_time_ist,
            parking_cost_per_hour=lot.price_per_hour,
            total_cost=None,
            created_at=parking_time_ist
        )
        #forward the cheanges to the db
        reservation.vehicle_no = vehicle_no
        db.session.add(reservation)
        db.session.commit()
        flash(f'Spot {available_spot.spot_number} booked successfully in {lot.prime_location_name}!', 'success')
        return redirect(url_for('user.dashboard'))
    return render_template('user/book.html', lot=lot, spot=available_spot, vehicle_no='')


#release spot
@user_bp.route('/release/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def release_spot(reservation_id):
    #check for user
    if current_user.is_admin:
        flash('Admins cannot release parking spots.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        flash('You can only release your own reservations.', 'danger')
        return redirect(url_for('user.dashboard'))
    if not reservation.is_active():
        flash('This reservation has already been completed.', 'info')
        return redirect(url_for('user.dashboard'))
    cost = None
    #using IST for time
    now_ist = datetime.utcnow().replace(tzinfo=timezone('UTC')).astimezone(IST)
    now_str = now_ist.strftime('%Y-%m-%dT%H:%M')

    if request.method == 'POST':
        releasing_time_str = request.form.get('releasing_time')
        action = request.form.get('action')
        #get the releasing time stamp
        if not releasing_time_str:
            return render_template('user/release.html', reservation=reservation, now_str=now_str, cost=cost, ist_format=True, ist_tz=IST)
        try:
            #parse and forward as IST
            releasing_time = datetime.strptime(releasing_time_str, '%Y-%m-%dT%H:%M')
            releasing_time = IST.localize(releasing_time)

        except Exception:
            flash('Invalid release time format.', 'danger')
            return render_template('user/release.html', reservation=reservation, now_str=now_str, cost=cost, ist_format=True, ist_tz=IST)
        
        #two functions calculate or release
        if action == 'calculate':
            reservation.leaving_timestamp = releasing_time
            cost = reservation.calculate_total_cost()
            reservation.leaving_timestamp = None
            return render_template('user/release.html', reservation=reservation, now_str=releasing_time_str, cost=cost, ist_format=True, ist_tz=IST)
        
        elif action == 'release':
            reservation.leaving_timestamp = releasing_time
            reservation.total_cost = reservation.calculate_total_cost()
            spot = ParkingSpot.query.get(reservation.spot_id)
            spot.status = 'A'
            db.session.commit()
            flash('Spot released successfully!', 'success')
            return redirect(url_for('user.dashboard'))
        
    return render_template('user/release.html', reservation=reservation, now_str=now_str, cost=cost, ist_format=True, ist_tz=IST)


#reservation history
@user_bp.route('/history')
@login_required
def reservation_history():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    #get all the reservations of the cuurent user
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.created_at.desc()).all()
    
    return render_template('user/history.html', reservations=reservations)


#viewing lots
@user_bp.route('/lots')
@login_required
def view_lots():
    #check for user
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    #get all the parking lots with information about their availablity
    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = lot.get_available_spots_count()
        lot.occupied_spots = lot.get_occupied_spots_count()
    
    return render_template('user/lots.html', lots=lots)


#edit profile
@user_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    #chck for user since admin can not edit their profile
    if current_user.is_admin:
        flash('Admins cannot edit profile here.', 'danger')
        return redirect(url_for('admin.dashboard'))

    #get data from the form 
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        #validate usernaem
        if not new_username or len(new_username) < 3:
            errors.append('Username must be at least 3 characters long.')
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            errors.append('Username can only contain letters, numbers, and underscores.')
        if new_username != current_user.username and User.query.filter_by(username=new_username).first():
            errors.append('Username already taken.')

        #if password cahnged then its valiation
        if new_password or confirm_password:
            if not current_password or not current_user.check_password(current_password):
                errors.append('Current password is incorrect.')
            if len(new_password) < 5:
                errors.append('New password must be at least 5 characters long.')
            if new_password != confirm_password:
                errors.append('New passwords do not match.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('user/edit_profile.html')

        #update username in the database
        current_user.username = new_username
        #update password
        if new_password:
            current_user.set_password(new_password)
        #commit to db
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('user.dashboard'))

    return render_template('user/edit_profile.html')


#user summary
@user_bp.route('/summary', endpoint='summary')
@login_required
#stats related to reservation , no. of bookings, released info,or parked out
def summary():
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    booked = len(reservations)
    released = len([r for r in reservations if r.leaving_timestamp is not None])
    parked_out = len([r for r in reservations if r.leaving_timestamp is None])
    return render_template('user/summary.html', booked=booked, released=released, parked_out=parked_out)


