# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pytz import timezone
IST = timezone('Asia/Kolkata')

db = SQLAlchemy()

# ======================
# User Models
# ======================

class User(UserMixin, db.Model):
    """User model for regular users and admin"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"


# ======================
# Parking Models
# ======================

class ParkingLot(db.Model):
    """Parking lot model"""
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(120), nullable=False, unique=True)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True, cascade='all, delete-orphan')

    def get_available_spots_count(self):
        """Get count of available spots"""
        return ParkingSpot.query.filter_by(lot_id=self.id, status='A').count()
    
    def get_occupied_spots_count(self):
        """Get count of occupied spots"""
        return ParkingSpot.query.filter_by(lot_id=self.id, status='O').count()
    
    def get_occupancy_percentage(self):
        """Get occupancy percentage"""
        total = len(self.spots)
        if total == 0:
            return 0
        occupied = self.get_occupied_spots_count()
        return round((occupied / total) * 100, 1)

    def __repr__(self):
        return f"<ParkingLot(id={self.id}, name='{self.prime_location_name}', spots={len(self.spots)})>"


class ParkingSpot(db.Model):
    """Parking spot model"""
    __tablename__ = 'parking_spots'

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # A = Available, O = Occupied
    spot_number = db.Column(db.String(10), nullable=False)  # e.g., "A1", "B2"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reservations = db.relationship('Reservation', backref='spot', lazy=True, cascade='all, delete-orphan')

    def is_available(self):
        """Check if spot is available"""
        return self.status == 'A'
    
    def is_occupied(self):
        """Check if spot is occupied"""
        return self.status == 'O'

    def get_current_reservation(self):
        """Get current active reservation for this spot"""
        return Reservation.query.filter_by(spot_id=self.id, leaving_timestamp=None).first()

    def __repr__(self):
        return f"<ParkingSpot(id={self.id}, lot_id={self.lot_id}, spot_number='{self.spot_number}', status='{self.status}')>"


class Reservation(db.Model):
    """Reservation model for parking spot bookings"""
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime)
    parking_cost_per_hour = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vehicle_no = db.Column(db.String(20))

    def is_active(self):
        """Check if reservation is active (not completed)"""
        return self.leaving_timestamp is None
    
    def get_duration_hours(self):
        """Get duration in hours"""
        if self.leaving_timestamp:
            start = self.parking_timestamp
            end = self.leaving_timestamp
            # Make both datetimes timezone-aware (IST)
            if start.tzinfo is None:
                start = IST.localize(start)
            if end.tzinfo is None:
                end = IST.localize(end)
            duration = end - start
            return max(duration.total_seconds() / 3600, 0.5)  # Minimum 30 minutes
        return 0
    
    def calculate_total_cost(self):
        """Calculate total cost based on duration"""
        if self.leaving_timestamp:
            duration_hours = self.get_duration_hours()
            return round(duration_hours * self.parking_cost_per_hour, 2)
        return 0
    
    def get_formatted_duration(self):
        """Get formatted duration string"""
        if self.leaving_timestamp:
            duration = self.leaving_timestamp - self.parking_timestamp
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Ongoing"

    def __repr__(self):
        return (f"<Reservation(id={self.id}, user_id={self.user_id}, spot_id={self.spot_id}, "
                f"parking_timestamp={self.parking_timestamp}, leaving_timestamp={self.leaving_timestamp}, "
                f"total_cost={self.total_cost})>")
