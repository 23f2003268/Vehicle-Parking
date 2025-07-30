import os

class Config:
    SECRET_KEY = os.environ.get('qwertyuiopasdfghjkl') or 'vehicle-parking-app-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///vehicle_parking.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
