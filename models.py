from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Spot(db.Model):
    __tablename__ = 'spots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    longitude = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    booking_required = db.Column(db.Boolean, default=True, nullable=False)
    car_park = db.Column(db.Boolean, default=False, nullable=False)
    outdoor = db.Column(db.Boolean, default=False, nullable=False)
    hiking = db.Column(db.Boolean, default=False, nullable=False)
    biking = db.Column(db.Boolean, default=False, nullable=False)
    fishing = db.Column(db.Boolean, default=False, nullable=False)
    camping = db.Column(db.Boolean, default=False, nullable=False)
    climbing = db.Column(db.Boolean, default=False, nullable=False)
    kayaking = db.Column(db.Boolean, default=False, nullable=False)
    swimming = db.Column(db.Boolean, default=False, nullable=False)
    picnic_area = db.Column(db.Boolean, default=False, nullable=False)
    wildlife_watching = db.Column(db.Boolean, default=False, nullable=False)
    photography = db.Column(db.Boolean, default=False, nullable=False)
    bbq = db.Column(db.Boolean, default=False, nullable=False)
    campsite = db.Column(db.Boolean, default=False, nullable=False)

    # Relationship to Reviews
    reviews = db.relationship('Review', backref='spot', lazy=True)

    # Relationship to Bookings (backref creates 'bookings' property on Spot)
    bookings = db.relationship('Booking', backref='spot', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship to Reviews
    reviews = db.relationship('Review', backref='user', lazy=True)

    # Relationship to Bookings (backref creates 'bookings' property on User)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating should be an integer (1-5)
    comment = db.Column(db.Text, nullable=True)  # Comment is optional
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def formatted_created_at(self):
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S')

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    # No need to define a relationship here for 'spot', as it's already defined in Spot model with backref
    # No need to define a relationship here for 'user', as it's already defined in User model with backref
