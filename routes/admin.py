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
