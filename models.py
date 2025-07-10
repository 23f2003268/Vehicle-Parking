from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin
from datetime import datetime
from pytz import timezone

IST = timezone('Asia/Kolkata')

db = SQLAlchemy()

#user model - information about user and admin
class Users(UserMixin, db.Model):
    __tablename__ = 'VUser' #this is a vehicle table name in database

    #creating primary key for each user
    U_id = db.Column(db.Integer, primary_key=True)
    U_name=db.Column(db.String(20), unique=True, nullable=False)
    Fullname = db.Column(db.String(50), unique=False, nullable=False)
    P_address = db.Column(db.String(150), unique=False, nullable= False)
    pincode= db.Column(db.Integer, unique=False, nullable=False)
    password=db.Column(db.String(128), nullable=False)
    create_at= db.Column(db.DateTime, default= datetime.utcnow)
    #identify user as admin or not
    isadmin=db.Column(db.Boolean, default=False)

    #relationship with reservation table
    relate_reservation=db.relationship('Reservation',
                                        backref='user', #extarcting user directly from reservation.users
                                        lazy=True, #loads data if required
                                        cascade='all,delete-orphan')#ensures related reservation are deleted
    #create password hash
    def set_pass(self,password):
        self.password=generate_password_hash(password)
        #creating hash from password
    
    #check hash password
    def check_pass(self, password):
        return check_password_hash(self.pass_hash, password)
    
    #to show useful user object info
    def __repr__(self):
        return f"<Users(id={self.U_id}, username='{self.U_name}' is_admin={self.isadmin})>"
    


#Parking System Models - Parking lot, Parking spt, Reservation

#Parking lot

class Parking_lots(db.Model):
    __tablename__= 'parking_lots'

    PL_id=db.Column(db.Integer, primary_key=True)
    location_name= db.Column(db.String(150), unique=True, nullable=False)
    hourly_rate=db.Column(db.Float, nullable=False)#this is the price / hour of the parking lot
    address=db.Column(db.String(300), nullable=False)
    pincode= db.Column(db.Integer, nullable=False)
    max_spots=db.Column(db.Integer, nullable=False)
    create_time=db.Column(db.DateTime, default=datetime.utcnow) #this is the time stamp when the lot was created
    
    #creating relationship between parking spots
    spots = db.relationship('Parking_spots',
                            backref='lot',
                            lazy=True,
                            cascade='all, delete-orphan')
    
    #currently available no. of spots

    def avl_spot_count(self):
        return parking_spots.query.filter_by(lot_id=self.PL_id, occupancy_status='A').count()
    
    #no. of spots occupied
    def ocpd_spot_count(self):
        return parking_spots.query.filter_by(lot_id=self.PL_id, occupancy_status='O').count()
    
    #occupancy percentage for visualisation
    def ocp_percentage(self):
        total=len(self.spots)
        if (total==0):
            return 0
        occupied = self.ocpd_spot_count()
        return (occupied/total)*100
    
    #to show useful PL Object info
    def __repr__(self):
        return f"<Parking_lots(id={self.PL_id}, name='{self.location_name}', spots={self.spots.count()})>"
    


#parking spot model
class Parking_spots(db.Model):
    __tablename__='parking_spots'

    PS_id= db.Column(db.Integer, primary_key=True)
    lot_id= db.Column(db.Integer, db.ForeignKey('parking_lots.PL_id'), nullable=False) #this relates the table with the parking_lots
    occupancy_status= db.Column(db.String(1), nullable=False, default='A') #A means Available and O mans Occupied
    spot_num=db.Column(db.String(5), nullable=False) #help identify the spot
    create_time= db.Column(db.DateTime, default=datetime.utcnow)

    relate_reservation=db.relationship('Reservation',
                                        backref='spot', #extarcting user directly from reservation.spot
                                        lazy=True, #loads data if required
                                        cascade='all,delete-orphan')
    
    #check availability
    def is_avlbl(self):
        return self.occupancy_status =='A'
    
    #check occupancy
    def is_ocpd(self):
        return self.occupancy_status=='O'
    
    #last updated status of the spot
    def reservation_status(self):
        return Reservation.query.filter_by(spot_id=self.PS_id, leaving_time=None).first()
        
    def __repr__(self):
        return f"<Parking_spots(id={self.PS_id}, lot_id={self.lot_id},spot_num='{self.spot_num}', occupancy_status='{self.occupancy_status}')>"
    

#Reseervation model to store booking of parking spot
class Reservation(db.Model):
    __tablename__='reservation_spot_bookings'#this is the table name of reservation model

    book_id=db.Column(db.Integer, primary_key=True) #here a unique reservation id is stored for each reservation
    spot_id = db.Column(db.Integer,db.ForeignKey('parking_spots.PS_id'),nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('VUser.U_id'), nullable=False)

    parking_time=db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    leaving_time=db.Column(db.DateTime)

    parking_hourly_rate=db.Column(db.Float, nullable=False)

    #t_cost=db.column(db.Float)

    create_time= db.Column(db.DateTime, default=datetime.utcnow)

    v_no=db.Column(db.String(20), nullable=False)


    #check active reservation by checking if leaving time is none or not
    def active_res(self):
        return self.leaving_time is None
    
    #total reserved time before checkout
    def total_reserved_time(self):
        if self.leaving_time:
            start=self.parking_time #when the lot was booked 
            end=self.leaving_time  #when the lot was left

            #it is required to aware the start and end time with time zone
            if start.tzinfo is None:
                start=IST.localize(start)
            if end.tzinfo is None:
                end=IST.localize(end)

            duration= end-start
            return max(duration.total_seconds()/3600 , 0.5)  #minimum 30 minutes
        return 0

    #now defining the total cost according to the total time the slot was reserved
    def total_cost(self):
        if self.leaving_time:#total cost will be calculated only if leaving_time has some value
            duration_hour = self.total_reserved_time()
            return round(duration_hour * self.parking_hourly_rate,2)
        return 0
    
    #To meadure the time passed from rreservation
    def formatted_duration(self):
        if self.leaving_time:    
            duration=self.leaving_time- self.parking_time
            hours = int(duration.total_seconds()//3600)
            minutes= int((duration.total_seconds()%3600)//60)
            if hours>0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Ongoing" 
        

    def __repr__(self):     #final reservation object
        return(f"<Reservation(id={self.book_id}, user_id={self.user_id}spot_id={self.spot_id},"
               f" parking_time={self.parking_time}, leaving_time={self.leaving_time},"
               f"total_cost={self.total_cost})>")