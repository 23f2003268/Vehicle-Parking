# routes/admin.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, ParkingLot, ParkingSpot, Reservation
from datetime import datetime
import re

admin_bp = Blueprint('admin', __name__, template_folder='../templates')




#login for admin
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    return redirect(url_for('user.login'))



# admin dashboard
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    #check if user is admin
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    #fetch records from sql database
    lots = ParkingLot.query.all()
    spots = ParkingSpot.query.all()
    reservations = Reservation.query.all()

     #computing stats
    total = len(spots)
    available = len([s for s in spots if s.status == 'A'])
    occupied = len([s for s in spots if s.status == 'O'])
    active_reservations = len([r for r in reservations if r.leaving_timestamp is None])

    #chart using lot name and occupancy
    lot_names = [lot.prime_location_name for lot in lots]
    lot_occupancy = [lot.get_occupancy_percentage() for lot in lots]

    #present last 7 actions as recent activity
    recent_reservations = Reservation.query.order_by(Reservation.created_at.desc()).limit(7).all()
    recent_activity = []
    for res in recent_reservations:
        user = res.user.username if res.user else 'Unknown User'
        lot = res.spot.lot.prime_location_name if res.spot and res.spot.lot else 'Unknown Lot'
        
        if res.leaving_timestamp:#message if parking slot is left
            msg = f"{user} released spot {res.spot.spot_number} in {lot} (₹{res.total_cost:.2f})"
            timestamp = res.leaving_timestamp

        #if slot was not left
        else:
            msg = f"{user} booked spot {res.spot.spot_number} in {lot}"
            timestamp = res.created_at
        recent_activity.append({'timestamp': timestamp, 'message': msg})

    #sort again since the timestamps are changed and they may not be in desc order
    recent_activity = sorted(recent_activity, key=lambda x: x['timestamp'], reverse=True)[:5]

    return render_template(
        'admin/dashboard.html',
        lots=lots,
        total=total,
        available=available,
        occupied=occupied,
        active_reservations=active_reservations,
        lot_names=lot_names,
        lot_occupancy=lot_occupancy,
        recent_activity=recent_activity
    )




# creating parking Lot

@admin_bp.route('/lots/create', methods=['GET', 'POST'])
@login_required

def create_lot():
    #admin check
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('user.dashboard'))
    # Get form data
    if request.method == 'POST':        
        prime_location_name = request.form.get('prime_location_name', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()
        price_per_hour = request.form.get('price_per_hour', '')
        maximum_number_of_spots = request.form.get('maximum_number_of_spots', '')
        
        # validating string with their lengths and integers with values as well as length
        errors = []
        if not prime_location_name or len(prime_location_name) < 3:
            errors.append('Location name must be at least 3 characters long.')
        
        if not address or len(address) < 10:
            errors.append('Address must be at least 10 characters long.')
        
        #the string is validated using regular expression
        if not pincode or not re.match(r'^\d{6}$', pincode):
            errors.append('Pincode must be exactly 6 digits.')
        
        try:
            price_per_hour = float(price_per_hour)
            if price_per_hour <= 0:
                errors.append('Price per hour must be greater than 0.')
        except (ValueError, TypeError):
            errors.append('Invalid price per hour.')
        
        try:
            maximum_number_of_spots = int(maximum_number_of_spots)
            if maximum_number_of_spots <= 0 or maximum_number_of_spots > 100:
                errors.append('Maximum spots must be between 1 and 100.')
        except (ValueError, TypeError):
            errors.append('Invalid maximum spots value.')
        
        #flashing errors on the screen
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/create_lot.html')
        
        #check if the location already exists
        if ParkingLot.query.filter_by(prime_location_name=prime_location_name).first():
            flash('A parking lot with this location name already exists.', 'danger')
            return render_template('admin/create_lot.html')
        
        #all things are checked and verified and create parking lot
        try:
            lot = ParkingLot(
                prime_location_name=prime_location_name,
                address=address,
                pincode=pincode,
                price_per_hour=price_per_hour,
                maximum_number_of_spots=maximum_number_of_spots
            )
            db.session.add(lot)
            db.session.commit()
            
            # generating spots
            from create_db import generate_spot_number
            for i in range(1, maximum_number_of_spots + 1):
                spot_number = generate_spot_number(lot.id, i)
                spot = ParkingSpot(lot_id=lot.id, spot_number=spot_number, status='A')
                db.session.add(spot)
            db.session.commit()
            
            #this part is hence completed and is required to give a message that the lot has been created
            flash(f'Parking lot "{prime_location_name}" created successfully with {maximum_number_of_spots} spots.', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating parking lot. Please try again.', 'danger')
            return render_template('admin/create_lot.html')

    return render_template('admin/create_lot.html')


#edit parking slots
@admin_bp.route('/lots/edit/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def edit_lot(lot_id):
    #check for admin
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    #initialise lot
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        # get data from the form
        prime_location_name = request.form.get('prime_location_name', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()
        price_per_hour = request.form.get('price_per_hour', '')
        
        # validating form data
        errors = []
        if not prime_location_name or len(prime_location_name) < 3:
            errors.append('Location name must be at least 3 characters long.')
        
        if not address or len(address) < 10:
            errors.append('Address must be at least 10 characters long.')
        
        #validating through regular expression
        if not pincode or not re.match(r'^\d{6}$', pincode):
            errors.append('Pincode must be exactly 6 digits.')

        try:
            price_per_hour = float(price_per_hour)
            if price_per_hour <= 0:
                errors.append('Price per hour must be greater than 0.')
        except (ValueError, TypeError):
            errors.append('Invalid price per hour.')
        
        #pop the errors
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/edit_lot.html', lot=lot)
        
        #check if location already exists except current one
        existing_lot = ParkingLot.query.filter_by(prime_location_name=prime_location_name).first()
        if existing_lot and existing_lot.id != lot.id:
            flash('A parking lot with this location name already exists.', 'danger')
            return render_template('admin/edit_lot.html', lot=lot)
        
        #now update the lot
        try:
            lot.prime_location_name = prime_location_name
            lot.address = address
            lot.pincode = pincode
            lot.price_per_hour = price_per_hour
            db.session.commit()
            
            flash(f'Parking lot "{prime_location_name}" updated successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
        
        #if lot not updated
        except Exception as e:
            db.session.rollback()
            flash('Error updating parking lot. Please try again.', 'danger')
            return render_template('admin/edit_lot.html', lot=lot)

    return render_template('admin/edit_lot.html', lot=lot)


#delete lot
@admin_bp.route('/lots/delete/<int:lot_id>', methods=['POST'])
@login_required
def delete_lot(lot_id):
    #check for admin
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('user.dashboard'))

    #initialise for lot_id
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # check if spots are occupied
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
    if occupied_spots > 0:
        flash(f'Cannot delete lot "{lot.prime_location_name}" - {occupied_spots} spots are currently occupied.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    try:
        #now delete all spots
        ParkingSpot.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit()
        
        flash(f'Parking lot "{lot.prime_location_name}" deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting parking lot. Please try again.', 'danger')
    
    return redirect(url_for('admin.dashboard'))
