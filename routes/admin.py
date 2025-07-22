from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Users, Parking_lots, Parking_spots, Reservation
from datetime import datetime
import re

admin_blueprint=Blueprint('admin', __name__, template_folder='../templates')  #organize app into reusable and moduler components


#login for admin (same for user)
@admin_blueprint.route('/login', methods=['GET','POST'])
def login():
    return redirect(url_for('login'))  

#admin_dashboard 
@admin_blueprint.route('/dashboard')
@login_required
def d_board():
    #check if user is admin
    if not current_user.is_admin:
        flash('Permission denied','danger')
        return redirect(url_for('user.dashboard'))
    
    #fetch records from sql database
    lots= Parking_lots.query.all()
    spots=Parking_spots.query.all()
    reservations=Reservation.query.all()

    #computing stats
    total=len(spots)
    avlbl=len([s for s in spots if s.status=='A'])
    ocpd=len([s for s in spots if s.status=='O'])
    active_res=len([r for r in reservations if r.leaving_time is None])

    #chart using lot name and occupancy
    lot_name=[lot.location_name for lot in lots]
    ocpd_lot=[lot.ocp_percentage() for lot in lots]

    #present last 7 actions as recent activity
    rct_reservation=Reservation.query.order_by(Reservation.create_time.desc().limit(7).all)
    rct_activity=[]
    for rec_rsv in rct_reservation:
        user=rec_rsv.Users.U_name if rec_rsv.Users else 'Unknown users'
        lot=rec_rsv.spot.lot.location_name if rec_rsv.spot and rec_rsv.spot.lot else 'Unknown lot'

        if rec_rsv.leaving_time:#message if parking slot is left
            msg= f"{user} released spot {rec_rsv.spot.spot_num} in {lot} (₹{rec_rsv.total_cost:.2f}"
            time=rec_rsv.leaving_time
        #if slot was not left   
        else:
            msg= f"{user} booked spot {rec_rsv.spot.spot_num} in {lot}"
            time=rec_rsv.create_time
        rct_activity.append({'timestamp': time, 'message':msg})

    #sort again since the timestamps are changed and they may not be in desc order
    rct_activity=sorted(rct_activity, key=lambda x: x['timestamp'], reverse='True')[:7]

    return render_template(
        'admin/dashboard.html',
        lots=lots,
        total=total,
        avlbl=avlbl,
        ocpd=ocpd,
        active_res=active_res,
        lot_name=lot_name,
        ocpd_lot=ocpd_lot,
        rct_activity=rct_activity
    )


# creating parking lot

@admin_blueprint.route('/lots/create', methods=['GET','POST'])
@login_required

def create_lot():
    #admin check
    if not current_user.is_admin:
        flash('Permission Denied. Admin only', 'danger')
        return redirect(url_for('user.dashboard'))
    #get forms data
    if request.method=='POST':
        location_name=request.form.get('location_name','').strip()
        address=request.form.get('address','').strip()
        pincode=request.form.get('pincode','').strip()
        hourly_rate=request.form.get('hourly_rate','').strip()
        max_spots=request.form.get('max_spots','')


        # validating string with their lengths and integers with values as well as length
        errors=[]
        if not location_name or len(location_name)<3:
            errors.append('At least 3 characters required in location name')

        if not address or len(address)<10:
            errors.append('At least 10 characters required in address')

        if not pincode or not re.match(r'^\d{6}$',pincode):
        #the string is validated using regular expression
            errors.append('At least 6 digit numerical value required')

        try:
            hourly_rate=float(hourly_rate)
            if hourly_rate<0:
                errors.append('Hourly rate cannot be negative')
        except(ValueError, TypeError):
            errors.append('Invalid Value')

        try:
            max_spots=float(max_spots)
            if max_spots<=0 or max_spots>=99:
                errors.append('Total Spots is always between 1 to 100.')
        except(ValueError,TypeError):
            errors.append('Invalid Value')

        #flashing errors on the screen
        if errors:
            for e in errors:
                flash(e,'danger')
            return render_template('admin/create_lot.html')
        
        #check if the location already exists
        if Parking_lots.query.filter_by(location_name=location_name).first():
            flash('Duplicate Location Name recieved','danger')
            return render_template('admin/create_lot.html')
        
        #all things are checked and verified and create parking lot
        try:
            lot=Parking_lots(location_name=location_name, address=address, pincode=pincode, hourly_rate=hourly_rate, max_spots=max_spots)
            db.session.add(lot)
            db.session.commit()
            
            #generating spots
            from utility import create_spot_no
            for i in range(1,max_spots+1):
                spot_num=create_spot_no(lot.id,i)
                spot=Parking_spots(lot_id=lot.id, spot_num=spot_num, status='A')
                db.session.add(spot)
            db.session.commit
            
            #this part is hence completed and is required to give a message that the lot has been created
            flash(f'Parking Lot "{location_name}" is created successfully with {max_spots} spots','success')
            return redirect(url_for('admin.dashboard'))
        

        #for any errors occuring in try block
        except Exception as e:
            db.session.rollback()
            flash('Some error occured. Try again later.','danger')
            return render_template('admin/create_lot.html')
    #opening form
    return render_template('admin/create_lot.html')



#editing a parking lot

@admin_blueprint.route('/lots/edit/<int:lot_id', methods=['GET','POST'])
@login_required
def edit_lot(lot_id):
    #check if admin
    if not current_user.is_admin:
        flash('Permission Denied','danger')
        return redirect(url_for('user.dashboard'))
    
    #if lot id found then get it else a 404 error
    lot=Parking_lots.query.get_or_404(lot_id)

    if request.method =='POST':
        location_name=request.form.get('location_name','').strip()
        address=request.form.get('address','').strip()
        pincode=request.form.get('pincode','').strip()
        hourly_rate=request.form.get('hourly_rate','').strip()

        #validate with respect to the norms
        errors=[]
        if not location_name or len(location_name)<3:
            errors.append('Location name should have atleast 3 characters')

        if not address or len(address)<10:
            errors.append('Address should be atleast 10 characters long')
        
        if not pincode or not re.match(r'^\d{6}$',pincode):
            errors.append('Pincode should have 6 digits')

        try:
            hourly_rate=float(hourly_rate)
            if hourly_rate<0:
                errors.append('Hourly rate cannot be negative')
        except(ValueError, TypeError):
            errors.append('Invalid Value')
        
        #if error arises mention it and re render the edit lot form
        if errors:
            for e in errors:
                flash(e,'danger')
            return render_template('admin/edit_lot.html', lot=lot)
        
        #check weather another parking lot has same location name or not
        existing_lot=Parking_lots.query.filter_by(location_name=location_name).first()
        if existing_lot and existing_lot.id!=lot.id:
            flash('Parking lot with this location name already exists','danger')
            return render_template('admin/edit_lot.html',lot=lot)
        
        #update the values of parkign lot
        try:
            lot.location_name=location_name
            lot.address=address
            lot.pincode=pincode
            lot.hourly_rate=hourly_rate
            db.session.commit()

            flash (f'The values of parking lot "{location_name}" is updated successfully.','success')
            return redirect(url_for('admin/dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occured while updating Parking lot. Try again after some time','danger')
            return render_template('admin/edit_lot.html','lot=lot')
        
        return render_template('admin/edit_lot.html', lot=lot)
    


#deletion of parking lot
@admin_blueprint.route('/lots/edit/<int: lot_id',methods=['POST'])
@login_required
def delete_lot():
    if not current_user.is_admmin:
        flash('Permission Denied','danger')
        return redirect(url_for('user.dashboard'))
    
    lot=Parking_lots.query.get_or_404('lot_id')

    #check occupancy status
    ocpd_spots=Parking_lots.query.filter_by(lot_id=lot.id, status='O').count()
    if ocpd_spots>0:
        flash('The lots with occupied slots can not be deleted','danger')
        return redirect(url_for('admin.dashbaord'))
    
    #delete the selected lot
    try:
        Parking_lots.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit
        flash(f'The Parking lot with {lot.location_name} is deleted successfully','success')
        
    #in case some unexpected error
    except Exception as e:
        db.session.rollback()
        flash('Error occurred while deleting the parking lot. Please try again later')

    return redirect(url_for('admin.dashboard'))



#viewing users and the reservations

@admin_blueprint.route('/Users')
@login_required

def view_user_rsv():

    #check if the admin is logging
    if not current_user.is_admin:
        flash('Permission Denied','danger')
        return redirect(url_for('user.dashboard'))
    
    user=Users.query.filter_by(isadmin=False).order_by(Users.create_at.desc()).all()

    #calculating stats
    t_rsv=sum(len(u.reservation)for u in user)
    act_user=len([u for u in user in user.reservation])
    t_revenue=sum(sum(res.total_cost for res in u.reservation if res.total_cost)for u in user)


    #we also require all reservations of all users sorted by date
    all_rsv=[]
    for u in user:
        all_rsv.extend(user.reservation)

    rct_rsv=sorted(all_rsv,key=lambda x:x.create_time, reverse=True)

    return render_template('admin/user.html', user=user, t_rsv=t_rsv, act_user=act_user, t_revenue=t_revenue, rct_rsv=rct_rsv)



#vieving lot spots
@admin_blueprint.route('/lots/<int:lot_id>/spots')
@login_required
def view_lot_spots(lot_id):
#check if admin is logged in
    if not current_user.is_admin:
        flash('Permission Denied','danger')
        return redirect(url_for('user.dashboard'))

    lot=Parking_lots.query.get_or_404(lot_id)
    spots=Parking_spots.query.filter_by(lot_id=lot.id).order_by(Parking_spots.spot_num).all()

    #create a dictionary to get surrent reseravtions
    ocpd_spot={}
    for s in spots:
        if s.status=='O':
            act_rsv=Reservation.query.filter_by(spot_id=spots.id, leave_time=None).first()
            if act_rsv:
                ocpd_spot[lot_id]=act_rsv

    return render_template('admin/lot_spots.htlm', lot=lot, spot=spots , ocpd_spot=ocpd_spot)


#searching spots
@admin_blueprint.route('/search',methods=['GET','POST'])
@login_required

def search_spots():
    #check if admin has logged in
    if not current_user.is_admin:
        flash('Permission denied','danger')
        return redirect(url_for('user.dashboard'))
    
    #create a list to be rendered
    search_results=[]
    if request.method=='POST':
        #taking search filters
        search_term=request.form.get('search_term','').strip()
        search_type=request.form.get('search_type','spot_num')

        #now checking for conditions provided int he filters
        if search_term:
            #for spot num
            if search_type=='spot_num':
                spot=Parking_spots.query.filter(Parking_spots.spot_num.contains(search_term)).all()
            #for occupancy status
            elif search_type=='occupancy_status':
                if search_term.lower() in ['occupied','o']:
                    status='O'
                else:
                    status='A'

                spot=Parking_spots.query.filter_by(status=status).all()
            #for lot num
            elif search_type=='lot_num':
                lot=Parking_lots.query.filter(Parking_lots.location_name.contains(search_term)).all()
                spot=[]                              
                for l in lot:
                    spot.extend(l.spots)
            #variable filled for final output
            search_results=spot
    return render_template('admin/search.html', search_results=search_results)



#admin logout
@admin_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out','info')
    return redirect(url_for('admin.login'))


#summary for admin visuals
@admin_blueprint.route('/summary')
@login_required
def summary():
    if not current_user.is_admin:
        flash('Permission Denied','danger')
        return redirect(url_for('user.dashboard'))
    
    lots=Parking_lots.query.all()

    #Revenue generated by each lot
    lot_names=[]  
    lot_revenue=[]
    avlbl_count=[]
    ocpd_count=[]
    for l in lots:
        lot_names.append(l.location_name)#will be used for labelling charts
        #rsv will only have reservations with completed reservations to calculate revenue
        rsv=Reservation.query.join(Parking_spots).filter(Parking_spots.id==lots.id, Reservation.leaving_time!=None).all()  
        revenue_generated=sum(r.t_cost or 0 for r in rsv)
        lot_revenue.append(revenue_generated)
        avlbl_count.append(lots.avl_spot_count()) #counts A
        ocpd_count.append(lots.ocpd_spot_count()) #counts O

    return render_template('admin/summary.html', lot_names=lot_names, lot_revenue=lot_revenue, avlbl_count=avlbl_count, ocpd_count=ocpd_count)