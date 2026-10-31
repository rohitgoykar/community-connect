import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import re
from datetime import datetime
import json
import os
import ssl
import smtplib 
import threading
import urllib.request
from email.mime.text import MIMEText 
from email.mime.multipart import MIMEMultipart  

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
# Handle postgres:// vs postgresql:// for SQLAlchemy if using Render PostgreSQL in future
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.makedirs(app.instance_path, exist_ok=True)

# ============ CHAT FILE UPLOAD CONFIG ============
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'chat_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'xlsx', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# ============ DATABASE MODELS ============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    location = db.Column(db.String(100))
    blood_group = db.Column(db.String(5))
    skills = db.Column(db.Text)
    interests = db.Column(db.Text)
    role = db.Column(db.String(20), default='customer')
    rating = db.Column(db.Float, default=0)
    total_ratings = db.Column(db.Integer, default=0)
    trust_score = db.Column(db.Integer, default=50)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    post_type = db.Column(db.String(50), default='Request Help')
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='Local Services')
    service_subcategory = db.Column(db.String(100), default='plumber')
    location = db.Column(db.String(100), default='Sangamner')
    urgency = db.Column(db.String(50), default='Normal')
    intent = db.Column(db.String(20))
    extracted_entities = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='posts')

class OTPSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), default='email')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    
    user = db.relationship('User', backref='notifications')
    post = db.relationship('Post', backref='notifications')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))
    file_type = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    requester = db.relationship('User', foreign_keys=[requester_id])
    provider = db.relationship('User', foreign_keys=[provider_id])
    post = db.relationship('Post')

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])

class ServiceProfile(db.Model):
    """Skilled professional marketplace profile"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    trade_category = db.Column(db.String(60), nullable=False)   # e.g. Plumber, Electrician
    trade_subcategory = db.Column(db.String(100))               # e.g. Pipe repair, Wiring
    bio = db.Column(db.Text)                                    # Short intro / pitch
    skills = db.Column(db.Text)                                 # Comma-separated skills
    rate_per_hour = db.Column(db.Float, default=0.0)            # ₹ per hour
    rate_per_visit = db.Column(db.Float, default=0.0)           # ₹ flat visit charge
    pricing_type = db.Column(db.String(30), default='Per Hour') # Per Hour/Day/Visit/Job/Negotiable
    min_charge = db.Column(db.Float, default=0.0)
    max_charge = db.Column(db.Float, default=0.0)
    experience_years = db.Column(db.Integer, default=0)
    availability = db.Column(db.String(200), default='Mon-Sat, 9am-7pm')
    availability_type = db.Column(db.String(30), default='Full-time')  # Full-time/Part-time/Weekends/On-call
    work_days = db.Column(db.String(100), default='Mon,Tue,Wed,Thu,Fri,Sat')
    service_area = db.Column(db.String(200))                    # Areas / localities served
    is_available = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    certifications = db.Column(db.Text)
    portfolio_url = db.Column(db.String(300))
    profile_photo = db.Column(db.String(300))                   # Profile photo filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('service_profile', uselist=False))

class ServiceBooking(db.Model):
    """Amazon/Flipkart-style Service Booking & Order Tracking"""
    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(30), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    time_slot = db.Column(db.String(50))
    address = db.Column(db.String(250))
    phone = db.Column(db.String(20))
    payment_mode = db.Column(db.String(50), default='Cash on Service')
    status = db.Column(db.String(30), default='Booked')  # Booked, Dispatched, In Progress, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('User', foreign_keys=[customer_id], backref='my_bookings')
    provider = db.relationship('User', foreign_keys=[provider_id], backref='provider_bookings')

# ============ DATABASE SETUP ============

def init_db():
    """Initialize database with admin user"""
    with app.app_context():
        # First ensure user.role column exists before ORM queries
        try:
            from sqlalchemy import text
            existing_user_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(user)"))]
            if 'role' not in existing_user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'customer'"))
                db.session.commit()
        except Exception as e:
            print(f"Role migration notice: {e}")

        db.create_all()

        # Lightweight auto-migration: add new chat_message file columns if missing
        try:
            from sqlalchemy import text
            existing_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(chat_message)"))]
            if 'file_path' not in existing_cols:
                db.session.execute(text("ALTER TABLE chat_message ADD COLUMN file_path VARCHAR(255)"))
            if 'file_name' not in existing_cols:
                db.session.execute(text("ALTER TABLE chat_message ADD COLUMN file_name VARCHAR(255)"))
            if 'file_type' not in existing_cols:
                db.session.execute(text("ALTER TABLE chat_message ADD COLUMN file_type VARCHAR(50)"))
            
            # Post table migrations
            existing_post_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(post)"))]
            if 'title' not in existing_post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN title VARCHAR(200)"))
            if 'post_type' not in existing_post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN post_type VARCHAR(50) DEFAULT 'Request Help'"))
            if 'urgency' not in existing_post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN urgency VARCHAR(50) DEFAULT 'Normal'"))
            if 'service_subcategory' not in existing_post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN service_subcategory VARCHAR(100) DEFAULT 'plumber'"))

            # ServiceProfile new field migrations
            existing_sp_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(service_profile)"))]
            if 'skills' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN skills TEXT"))
            if 'pricing_type' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN pricing_type VARCHAR(30) DEFAULT 'Per Hour'"))
            if 'min_charge' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN min_charge FLOAT DEFAULT 0"))
            if 'max_charge' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN max_charge FLOAT DEFAULT 0"))
            if 'availability_type' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN availability_type VARCHAR(30) DEFAULT 'Full-time'"))
            if 'work_days' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN work_days VARCHAR(100) DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat'"))
            if 'profile_photo' not in existing_sp_cols:
                db.session.execute(text("ALTER TABLE service_profile ADD COLUMN profile_photo VARCHAR(300)"))

            db.session.commit()
        except Exception as e:
            print(f"Migration check skipped/failed: {e}")
        
        # Create admin user if not exists
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin123'),
                email='developerharry18@gmail.com',
                name='Administrator',
                is_admin=True,
                trust_score=100
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Admin user created (username: admin, password: admin123)")
            
        # Ensure verified ServiceProfile for skilled users (e.g. Plumber Rohit Goykar)
        try:
            plumber_users = User.query.filter((User.username.ilike('%rohit%')) | (User.skills.ilike('%plumber%'))).all()
            for rohit in plumber_users:
                if not rohit.location:
                    rohit.location = 'Sangamner'
                if not rohit.contact:
                    rohit.contact = '8767865434'
                if not rohit.name:
                    rohit.name = 'Rohit Goykar'
                if not rohit.skills:
                    rohit.skills = 'PLUMBER'
                rohit_sp = ServiceProfile.query.filter_by(user_id=rohit.id).first()
                if not rohit_sp:
                    rohit_sp = ServiceProfile(
                        user_id=rohit.id,
                        trade_category='plumber',
                        trade_subcategory='Pipe Fitting, Leakage Repair & Sanitary Fixtures',
                        bio='Certified professional plumber in Sangamner with 5+ years of experience in pipe leakage, tap repair, bathroom sanitary installations, and water tank pipeline repairs.',
                        rate_per_hour=250.0,
                        rate_per_visit=400.0,
                        experience_years=5,
                        availability='Available Mon-Sun 8:00 AM - 8:00 PM',
                        service_area='Sangamner & nearby areas',
                        is_available=True,
                        is_verified=True
                    )
                    db.session.add(rohit_sp)
                else:
                    rohit_sp.trade_category = 'plumber'
                    rohit_sp.rate_per_hour = 250.0
                    rohit_sp.rate_per_visit = 400.0
                    rohit_sp.service_area = 'Sangamner & nearby areas'
                    rohit_sp.is_available = True
                    rohit_sp.is_verified = True
                db.session.commit()
                print(f"✓ Verified Plumber profile active for user {rohit.username} ({rohit.name}) in Sangamner (₹250/hr, ₹400/visit)")
                
            # Seed additional common Sangamner service providers if not already present
            sample_providers = [
                {
                    'username': 'ganesh_electrician',
                    'name': 'Ganesh Shinde',
                    'email': 'ganesh.shinde@sangamner.org',
                    'location': 'Sangamner',
                    'contact': '9822154321',
                    'skills': 'ELECTRICIAN, Wiring, MCB Repair',
                    'trade_category': 'electrician',
                    'trade_subcategory': 'Home Wiring, MCB, Inverter & Appliance Repair',
                    'bio': 'Licensed electrician in Sangamner. Quick doorstep service for wiring, switchboards, short circuits, and inverter setups.',
                    'rate_per_hour': 200.0,
                    'rate_per_visit': 350.0,
                    'experience_years': 6,
                    'service_area': 'Sangamner'
                },
                {
                    'username': 'amit_acrepair',
                    'name': 'Amit Patil',
                    'email': 'amit.patil@sangamner.org',
                    'location': 'Sangamner',
                    'contact': '9844556677',
                    'skills': 'AC TECHNICIAN, Cooling, Gas Refill',
                    'trade_category': 'ac_technician',
                    'trade_subcategory': 'Split & Window AC Servicing, Gas Refill, Installation',
                    'bio': 'Certified HVAC & AC technician providing doorstep servicing, chemical wash, and compressor repairs in Sangamner.',
                    'rate_per_hour': 350.0,
                    'rate_per_visit': 500.0,
                    'experience_years': 7,
                    'service_area': 'Sangamner'
                },
                {
                    'username': 'sunita_cleaning',
                    'name': 'Sunita Jadhav',
                    'email': 'sunita.jadhav@sangamner.org',
                    'location': 'Sangamner',
                    'contact': '9833445566',
                    'skills': 'CLEANER, Deep Cleaning, Sanitization',
                    'trade_category': 'cleaner',
                    'trade_subcategory': 'Home Deep Cleaning, Kitchen & Bathroom Cleaning',
                    'bio': 'Professional home deep cleaning and housekeeping services in Sangamner with eco-friendly supplies.',
                    'rate_per_hour': 180.0,
                    'rate_per_visit': 300.0,
                    'experience_years': 4,
                    'service_area': 'Sangamner'
                }
            ]
            for prov in sample_providers:
                existing_u = User.query.filter_by(username=prov['username']).first()
                if not existing_u:
                    new_u = User(
                        username=prov['username'],
                        password=generate_password_hash('password123'),
                        email=prov['email'],
                        name=prov['name'],
                        location=prov['location'],
                        contact=prov['contact'],
                        skills=prov['skills'],
                        trust_score=92,
                        rating=4.9,
                        total_ratings=18,
                        is_active=True
                    )
                    db.session.add(new_u)
                    db.session.commit()
                    new_sp = ServiceProfile(
                        user_id=new_u.id,
                        trade_category=prov['trade_category'],
                        trade_subcategory=prov['trade_subcategory'],
                        bio=prov['bio'],
                        rate_per_hour=prov['rate_per_hour'],
                        rate_per_visit=prov['rate_per_visit'],
                        experience_years=prov['experience_years'],
                        availability='Mon-Sat 8:30 AM - 7:30 PM',
                        service_area=prov['service_area'],
                        is_available=True,
                        is_verified=True
                    )
                    db.session.add(new_sp)
                    db.session.commit()
                    print(f"✓ Seeded service provider {prov['name']} ({prov['trade_category']}) in Sangamner")
        except Exception as seed_err:
            print(f"Service profile seeding notice: {seed_err}")


# ============ EMAIL CONFIGURATION ============
def _load_env_file():
    for base in [os.path.dirname(__file__), os.getcwd()]:
        env_f = os.path.join(base, '.env')
        if os.path.isfile(env_f):
            try:
                with open(env_f, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass

_load_env_file()

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "oopj435@gmail.com").strip()
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "dqsnzbjvuawgxyaw").replace(" ", "").strip()
SEND_REAL_EMAIL = True  # Set to True to send real emails

def send_otp_email(to_email, otp):
    """Send OTP via email with HTTP API fallback and Gmail SMTP for cloud hosting"""
    # Read credentials fresh on every call so Render env vars are always picked up
    email_address = os.environ.get("EMAIL_ADDRESS", "").strip()
    email_password = os.environ.get("EMAIL_PASSWORD", "").replace(" ", "").strip()
    brevo_api_key = os.environ.get("BREVO_API_KEY", "").strip()
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()

    if not email_address:
        email_address = "oopj435@gmail.com"
    if not email_password:
        email_password = "dqsnzbjvuawgxyaw"

    print("\n" + "="*60)
    print(f"📧 OTP DISPATCH → Recipient: {to_email}")
    print(f"📤 Sender: {email_address}")
    print(f"🔑 OTP Code: {otp}")
    print("="*60 + "\n")

    text_content = f"Your Smart Community Login OTP is: {otp}\nThis code is valid for 5 minutes."
    html_content = f"""<!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F4F6F9; color: #0A0C10; margin: 0; padding: 30px 15px;">
        <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border: 1.5px solid rgba(197, 160, 89, 0.45); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.06);">
            <div style="background: linear-gradient(135deg, #FFFFFF, #FAFBF7); padding: 25px 30px; border-bottom: 2px solid #C5A059; text-align: center;">
                <h1 style="color: #0A0C10; font-size: 22px; margin: 0; letter-spacing: 1.5px; text-transform: uppercase;">Smart<span style="color: #C5A059;">Community</span></h1>
                <p style="color: #5E5332; font-size: 11px; letter-spacing: 2px; margin: 6px 0 0; text-transform: uppercase; font-weight: 700;">&#10022; Secure Verification Pass &#10022;</p>
            </div>
            <div style="padding: 35px 30px; text-align: center;">
                <p style="color: #0A0C10; font-size: 15px; margin: 0 0 16px; line-height: 1.6; font-weight: 600;">Welcome to Smart Community,</p>
                <p style="color: #4A5568; font-size: 14px; margin: 0 0 25px; line-height: 1.6;">Use the one-time security passcode below to access your account:</p>
                <div style="display: inline-block; background: #FAFBF7; border: 2px solid #C5A059; border-radius: 8px; padding: 16px 36px; margin-bottom: 25px;">
                    <span style="font-family: monospace, Courier, monospace; font-size: 36px; font-weight: 800; color: #0A0C10; letter-spacing: 8px;">{otp}</span>
                </div>
                <p style="color: #718096; font-size: 12.5px; margin: 0; line-height: 1.6;">This passcode is valid for <strong>5 minutes</strong>. If you did not request this, you can safely ignore this email.</p>
            </div>
            <div style="background: #F8F9FA; padding: 18px 30px; text-align: center; border-top: 1px solid rgba(10,12,16,0.06); font-size: 11.5px; color: #718096;">
                &copy; 2026 Smart Community Network &bull; Connecting Neighborhoods Securely
            </div>
        </div>
    </body>
    </html>"""

    # 1. Brevo HTTP API (Port 443 HTTPS - NEVER blocked on Render Free tier)
    if brevo_api_key:
        try:
            req_data = json.dumps({
                "sender": {"name": "Smart Community Connect", "email": email_address},
                "to": [{"email": to_email}],
                "subject": f"Your OTP is {otp} - Smart Community",
                "htmlContent": html_content
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=req_data,
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status in (200, 201):
                    print(f"✅ OTP successfully sent via Brevo HTTP API to {to_email}")
                    return True
        except Exception as e_brevo:
            print(f"⚠️ Brevo HTTP API error: {e_brevo}")

    # 2. Resend HTTP API (Port 443 HTTPS - NEVER blocked on Render Free tier)
    if resend_api_key:
        try:
            req_data = json.dumps({
                "from": f"Smart Community <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"Your OTP is {otp} - Smart Community",
                "html": html_content
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status in (200, 201):
                    print(f"✅ OTP successfully sent via Resend HTTP API to {to_email}")
                    return True
        except Exception as e_resend:
            print(f"⚠️ Resend HTTP API error: {e_resend}")

    # 3. SMTP over Port 465 SSL (tight 3.5s timeout so cloud routers never freeze)
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Smart Community Connect <{email_address}>"
        msg['To'] = to_email
        msg['Subject'] = f"Your OTP is {otp} - Smart Community"
        msg['X-Priority'] = '1'
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        ssl_context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl_context, timeout=3.5) as server:
                server.login(email_address, email_password)
                server.send_message(msg)
            print(f"✅ OTP delivered via Port 465 SSL to {to_email}")
            return True
        except Exception as e_ssl:
            print(f"⚠️ Port 465 SSL notice: {e_ssl}")

        # 4. SMTP over Port 587 STARTTLS (tight 3.5s timeout)
        try:
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=3.5) as server:
                server.ehlo()
                server.starttls(context=ssl_context)
                server.ehlo()
                server.login(email_address, email_password)
                server.send_message(msg)
            print(f"✅ OTP delivered via Port 587 STARTTLS to {to_email}")
            return True
        except Exception as e_tls:
            print(f"⚠️ Port 587 STARTTLS notice: {e_tls}")

    except Exception as e:
        print(f"❌ SMTP preparation error: {e}")

    print(f"❌ All email dispatch methods failed for {to_email}.")
    return False


def send_notification_email(to_email, subject, message):
    """Send notification email for matches"""
    if not SEND_REAL_EMAIL:
        print(f"\n📧 NOTIFICATION TO: {to_email}")
        print(f"📝 SUBJECT: {subject}")
        print(f"📋 MESSAGE: {message}")
        return True
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        
        body = f"""<html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #667eea;">Community Connect</h2>
                <p>{message}</p>
                <p>Login to your account to view more details and connect.</p>
                <br>
                <a href="http://localhost:5000" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a>
                <hr>
                <small>Community Connect - Connecting Communities</small>
            </div>
        </body>
        </html>"""
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Notification sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ============ NLP PROCESSING ============

TRADE_KEYWORDS_MAP = {
    'plumber': ['plumb', 'plumber', 'plumbing', 'pipe', 'leak', 'drain', 'tap', 'sink', 'sanitary', 'faucet', 'flush', 'water pipe', 'tank leak', 'water leakage'],
    'electrician': ['electr', 'electrician', 'electrical', 'wire', 'wiring', 'switch', 'mcb', 'fuse', 'inverter', 'light', 'fan', 'short circuit', 'power cut'],
    'cleaner': ['clean', 'cleaner', 'cleaning', 'sweep', 'maid', 'mop', 'housekeep', 'housekeeping', 'dust', 'sanitization', 'deep cleaning'],
    'ac_technician': ['ac', 'air conditioner', 'cooling', 'gas refill', 'compressor', 'split ac', 'window ac', 'ac repair', 'ac service', 'technician'],
    'carpenter': ['carpent', 'carpenter', 'carpentry', 'wood', 'door', 'furniture', 'table', 'chair', 'cupboard', 'lock', 'wooden'],
    'painter': ['paint', 'painter', 'painting', 'whitewash', 'color', 'wall paint', 'waterproofing'],
    'mason': ['mason', 'brick', 'cement', 'tile', 'plaster', 'renovation', 'construction'],
    'mechanic': ['mechanic', 'bike', 'car repair', 'vehicle', 'engine', 'garage', 'puncture'],
    'driver': ['driver', 'driving', 'cab', 'chauffeur', 'car driver'],
    'cook': ['cook', 'cooking', 'chef', 'meal', 'food', 'tiffin', 'catering'],
    'gardener': ['gardener', 'gardening', 'lawn', 'plant', 'pruning'],
    'tailor': ['tailor', 'stitching', 'alteration', 'clothes'],
    'tutor': ['tutor', 'tuition', 'coaching', 'teacher', 'classes'],
    'nurse': ['nurse', 'nursing', 'caretaker', 'elderly care', 'patient care'],
}

TRADE_DISPLAY_MAP = {
    'plumber': ('🔧', 'Plumber Specialist'),
    'electrician': ('⚡', 'Certified Electrician'),
    'cleaner': ('🧹', 'Cleaning & Housekeeping'),
    'ac_technician': ('❄️', 'AC Repair & Technician'),
    'carpenter': ('🪚', 'Woodwork & Carpenter'),
    'painter': ('🎨', 'Painting Specialist'),
    'mason': ('🧱', 'Masonry & Tiling'),
    'mechanic': ('🚗', 'Automotive Mechanic'),
    'driver': ('🚙', 'Professional Driver'),
    'cook': ('👨‍🍳', 'Chef & Meal Cook'),
    'gardener': ('🌿', 'Lawn & Gardener'),
    'tailor': ('✂️', 'Tailoring & Stitching'),
    'tutor': ('📚', 'Academic Tutor'),
    'nurse': ('🏥', 'Home Health Nurse'),
}

DEFAULT_TRADE_RATES = {
    'plumber': (250.0, 400.0, 5, 'Available Mon-Sun 8am-8pm'),
    'electrician': (200.0, 350.0, 6, 'Available 24/7 on call'),
    'cleaner': (180.0, 300.0, 4, 'Available Daily 8am-6pm'),
    'ac_technician': (350.0, 500.0, 7, 'Available Mon-Sun 9am-7pm'),
    'carpenter': (250.0, 400.0, 6, 'Available Mon-Sat 9am-7pm'),
    'painter': (200.0, 350.0, 5, 'Available Mon-Sat 8am-6pm'),
    'mason': (300.0, 450.0, 8, 'Available Daily 8am-5pm'),
    'mechanic': (250.0, 350.0, 5, 'Available Mon-Sat 9am-8pm'),
    'driver': (150.0, 300.0, 4, 'Available on booking'),
    'cook': (200.0, 300.0, 5, 'Available Morning & Evening'),
    'gardener': (150.0, 250.0, 4, 'Available Mon-Sat 7am-12pm'),
    'tailor': (150.0, 200.0, 5, 'Available Mon-Sat 10am-8pm'),
    'tutor': (250.0, 400.0, 4, 'Available Evening 4pm-8pm'),
    'nurse': (300.0, 500.0, 5, 'Available 24/7 on shift'),
}

def process_post_text(text):
    """Extract intent, category, and entities from post text"""
    text_lower = text.lower()
    
    # Determine intent
    intent = "NEED"
    if any(word in text_lower for word in ['offer', 'selling', 'available', 'providing', 'have']):
        intent = "OFFER"
    elif any(word in text_lower for word in ['sell', 'selling', 'sale']):
        intent = "SELL"
    
    # Determine category
    category = "Local Services"
    if any(word in text_lower for word in ['blood', 'medical', 'doctor', 'health', 'hospital']):
        category = "MEDICAL"
    elif any(word in text_lower for word in ['house', 'flat', 'apartment', 'real estate', 'rent', 'buy', 'property']):
        category = "REAL_ESTATE"
    elif any(word in text_lower for word in ['sell', 'buy', 'market', 'shop', 'product']):
        category = "MARKETPLACE"
    
    # Extract entities
    entities = {}
    
    # Blood group extraction
    blood_match = re.search(r'\b([ABOab][+-]?)\b', text)
    if blood_match:
        entities['blood_group'] = blood_match.group(1).upper()
    
    # Location extraction
    cities = ['sangamner', 'pune', 'mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 
              'ahmedabad', 'surat', 'jaipur', 'lucknow', 'kanpur', 'nashik', 'shirdi', 'kopargaon', 'rahuri', 'akole']
    for city in cities:
        if city in text_lower:
            entities['location'] = city.title()
            break
    if 'location' not in entities:
        entities['location'] = 'Sangamner'
    
    # Trade & Skill extraction
    for trade_key, kw_list in TRADE_KEYWORDS_MAP.items():
        if any(kw in text_lower for kw in kw_list):
            entities['trade'] = trade_key
            entities['skill'] = trade_key
            break
    
    return {
        'intent': intent,
        'category': category,
        'entities': entities
    }

# ============ MATCHING ENGINE ============

def find_matches(post):
    """Find matches for a post based on category, skills/trades, locality, and requirements"""
    matches = []
    
    try:
        entities = json.loads(post.extracted_entities) if post.extracted_entities else {}
    except:
        entities = {}
    
    post_title_desc = f"{post.title or ''} {post.description or ''}".lower()
    post_loc = (post.location or 'Sangamner').strip().lower()
    post_cat = (post.category or 'Local Services').strip().lower()
    
    # Determine target trade
    target_trade = entities.get('trade') or entities.get('skill') or getattr(post, 'service_subcategory', None)
    if not target_trade:
        for trade_key, kw_list in TRADE_KEYWORDS_MAP.items():
            if any(kw in post_title_desc for kw in kw_list):
                target_trade = trade_key
                break
    
    # If category is Local Services or post mentions local services and no trade yet, check title/desc
    is_service_category = (
        'local service' in post_cat or 
        'service' in post_cat or 
        'repair' in post_cat or 
        'maintenance' in post_cat or 
        bool(target_trade)
    )
    
    # If still not found but category is local services, default to plumber if plumbing words exist
    if is_service_category and not target_trade:
        if any(kw in post_title_desc for kw in ['plumb', 'pipe', 'leak', 'tap', 'water', 'drain']):
            target_trade = 'plumber'
        else:
            target_trade = getattr(post, 'service_subcategory', 'plumber') or 'plumber'

    # Get all active users except post author
    users = User.query.filter(User.id != post.user_id, User.is_active == True).all()
    
    for user in users:
        match_score = 0
        match_reasons = []
        is_provider = False
        sp = getattr(user, 'service_profile', None)
        
        user_skills_lower = (user.skills or '').lower()
        user_interests_lower = (user.interests or '').lower()
        user_loc = (user.location or '').strip().lower()
        
        # 1. TRADE MATCHING (e.g. Plumber for Plumbing request)
        if is_service_category and target_trade:
            trade_matched = False
            
            # Check ServiceProfile
            if sp and (sp.trade_category == target_trade or (sp.trade_category and sp.trade_category.lower() in target_trade)):
                trade_matched = True
            elif sp and any(kw in (sp.trade_subcategory or '').lower() for kw in TRADE_KEYWORDS_MAP.get(target_trade, [])):
                trade_matched = True
            
            # Check User Skills / Interests
            if not trade_matched:
                if any(kw in user_skills_lower for kw in TRADE_KEYWORDS_MAP.get(target_trade, [target_trade])):
                    trade_matched = True
                elif any(kw in user_interests_lower for kw in TRADE_KEYWORDS_MAP.get(target_trade, [target_trade])):
                    trade_matched = True
            
            if trade_matched:
                is_provider = True
                match_score += 55
                t_icon, t_label = TRADE_DISPLAY_MAP.get(target_trade, ('🛠️', target_trade.title()))
                match_reasons.append(f"{t_icon} Verified {t_label}")
                
                # Check locality / area match
                sp_area = (sp.service_area or '').lower() if sp else ''
                if post_loc and (post_loc in user_loc or user_loc in post_loc or post_loc in sp_area):
                    match_score += 35
                    match_reasons.append(f"📍 Local Provider in {post.location or 'Sangamner'}")
                elif post_loc:
                    match_score += 15
                    match_reasons.append(f"📍 Available in district")
        
        # 2. MEDICAL matching
        elif "medical" in post_cat or post.category == "MEDICAL":
            needed_blood = entities.get('blood_group')
            if needed_blood and user.blood_group:
                if user.blood_group.upper() == needed_blood.upper():
                    match_score += 55
                    match_reasons.append(f"🩸 Blood group match: {needed_blood}")
            if post_loc and user_loc and (post_loc in user_loc or user_loc in post_loc):
                match_score += 30
                match_reasons.append(f"📍 Located in {post.location or 'Sangamner'}")
        
        # 3. GENERAL / OTHER matching
        else:
            if user.skills:
                for skill_word in user.skills.split(','):
                    s_clean = skill_word.strip().lower()
                    if s_clean and len(s_clean) > 2 and s_clean in post_title_desc:
                        match_score += 45
                        match_reasons.append(f"Skill synergy: {skill_word.strip()}")
                        break
            
            if post_loc and user_loc and (post_loc in user_loc or user_loc in post_loc):
                match_score += 25
                match_reasons.append(f"📍 Located in {post.location or 'Sangamner'}")
        
        # User Quality & Trust bonuses
        if match_score > 0:
            if user.rating and user.rating >= 4.0:
                match_score += 5
                match_reasons.append(f"⭐ Rating {user.rating:.1f}")
            if user.trust_score and user.trust_score >= 70:
                match_score += 5
                match_reasons.append(f"🛡️ Trust Score {user.trust_score}%")
            
            # Determine provider rates & details
            rate_per_hour = None
            rate_per_visit = None
            experience_years = 0
            availability = None
            service_area = None
            trade_title = None
            trade_icon = '🛠️'
            
            if sp:
                is_provider = True
                rate_per_hour = sp.rate_per_hour
                rate_per_visit = sp.rate_per_visit
                experience_years = sp.experience_years
                availability = sp.availability
                service_area = sp.service_area
                t_icon, t_label = TRADE_DISPLAY_MAP.get(sp.trade_category, ('🛠️', (sp.trade_category or 'Specialist').title()))
                trade_title = t_label
                trade_icon = t_icon
            elif is_provider and target_trade:
                t_icon, t_label = TRADE_DISPLAY_MAP.get(target_trade, ('🛠️', target_trade.title()))
                trade_title = t_label
                trade_icon = t_icon
                def_data = DEFAULT_TRADE_RATES.get(target_trade, (200.0, 300.0, 5, 'Available Mon-Sat 8am-8pm'))
                rate_per_hour = def_data[0]
                rate_per_visit = def_data[1]
                experience_years = def_data[2]
                availability = def_data[3]
                service_area = user.location or post.location or 'Sangamner'
            
            calc_score = min(100, match_score)
            match_data = {
                'user': user,
                'match_score': calc_score,
                'score': calc_score,
                'match_reasons': match_reasons,
                'reasons': match_reasons,
                'reason': ', '.join(match_reasons),
                'is_service_provider': is_provider,
                'trade_category': (sp.trade_category if sp else target_trade) if is_provider else None,
                'trade_title': trade_title,
                'trade_icon': trade_icon,
                'rate_per_hour': rate_per_hour,
                'rate_per_visit': rate_per_visit,
                'experience_years': experience_years,
                'availability': availability or 'Available upon request',
                'service_area': service_area or user.location or 'Sangamner',
                'contact': getattr(user, 'contact', None) or '8767865434',
                'service_profile': sp
            }
            matches.append(match_data)
    
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches[:20]

def find_matches_for_user(user):
    """Find posts that match a user's profile"""
    matched_posts = []
    all_posts = Post.query.filter(Post.user_id != user.id, Post.status == 'active').all()
    user_skills_lower = (user.skills or '').lower()
    sp = getattr(user, 'service_profile', None)
    sp_trade = (sp.trade_category.lower() if sp and sp.trade_category else '')
    
    for post in all_posts:
        match_score = 0
        match_reasons = []
        
        try:
            entities = json.loads(post.extracted_entities) if post.extracted_entities else {}
        except:
            entities = {}
        
        post_cat = (post.category or '').lower()
        post_loc = (post.location or '').lower()
        user_loc = (user.location or '').lower()
        post_text = f"{post.title or ''} {post.description or ''}".lower()
        
        # Medical match
        if "medical" in post_cat or post.category == "MEDICAL":
            needed_blood = entities.get('blood_group')
            if needed_blood and user.blood_group:
                if user.blood_group.upper() == needed_blood.upper():
                    match_score += 55
                    match_reasons.append(f"Can donate blood: {needed_blood}")
        
        # Service / Trade match
        elif any(k in post_cat for k in ['service', 'repair', 'maintenance']) or post.category == "SERVICE":
            target_skill = entities.get('trade') or entities.get('skill') or getattr(post, 'service_subcategory', None)
            if not target_skill:
                for t_key, kw_list in TRADE_KEYWORDS_MAP.items():
                    if any(kw in post_text for kw in kw_list):
                        target_skill = t_key
                        break
            
            if target_skill:
                skill_matched = False
                if sp_trade and target_skill in sp_trade:
                    skill_matched = True
                elif any(kw in user_skills_lower for kw in TRADE_KEYWORDS_MAP.get(target_skill, [target_skill])):
                    skill_matched = True
                
                if skill_matched:
                    match_score += 55
                    t_icon, t_label = TRADE_DISPLAY_MAP.get(target_skill, ('🛠️', target_skill.title()))
                    match_reasons.append(f"Can provide {t_label}")
        
        # Location match
        if post_loc and user_loc and (post_loc in user_loc or user_loc in post_loc):
            match_score += 25
            match_reasons.append(f"Same location: {post.location}")
            
        if match_score > 0:
            matched_posts.append({
                'post': post,
                'post_creator': User.query.get(post.user_id),
                'match_score': min(100, match_score),
                'match_reasons': match_reasons
            })
    
    matched_posts.sort(key=lambda x: x['match_score'], reverse=True)
    return matched_posts[:20]

# ============ ROUTES ============

@app.route('/')
def index():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user and user.role == 'provider':
            return redirect(url_for('services_provider_dashboard'))
        return redirect(url_for('services_categories'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    role = request.args.get('role') or request.args.get('portal') or 'customer'
    if request.method == 'POST':
        role = (request.form.get('role') or 'customer').strip()
        name = (request.form.get('name') or '').strip()
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        email = (request.form.get('email') or '').strip()
        contact = (request.form.get('contact') or '').strip()
        location = (request.form.get('location') or 'Sangamner').strip()

        if not username or not password or not email:
            return render_template('register.html', error="Please provide username, email, and password.", role=role, categories=TRADE_CATEGORIES)

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Username already exists! Please choose another one.", role=role, categories=TRADE_CATEGORIES)
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Email already registered! Please log in or use another email.", role=role, categories=TRADE_CATEGORIES)
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            password=hashed_password,
            email=email,
            name=name or username,
            contact=contact,
            location=location,
            role=role,
            trust_score=75,
            rating=5.0,
            total_ratings=1,
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()

        # If registering as a Service Provider, create ServiceProfile immediately
        if role == 'provider':
            trade_category = (request.form.get('trade_category') or 'plumber').strip()
            rate_per_hour = float(request.form.get('rate_per_hour') or 0)
            rate_per_visit = float(request.form.get('rate_per_visit') or 0)
            experience_years = int(request.form.get('experience_years') or 2)
            bio = (request.form.get('bio') or f"Verified community {trade_category} providing honest, reliable service.").strip()
            skills = request.form.get('skills', '').strip() or trade_category.title()

            sp = ServiceProfile(
                user_id=new_user.id,
                trade_category=trade_category,
                rate_per_hour=rate_per_hour,
                rate_per_visit=rate_per_visit,
                experience_years=experience_years,
                bio=bio,
                skills=skills,
                service_area=location,
                is_available=True,
                is_verified=True
            )
            db.session.add(sp)
            new_user.skills = trade_category.upper()
            db.session.commit()

        session['username'] = new_user.username
        session['user_id'] = new_user.id
        session['role'] = role
        flash(f"Welcome! Your {'Service Provider' if role == 'provider' else 'Service Required (Customer)'} account is active.", "success")
        
        if role == 'provider':
            return redirect(url_for('services_provider_dashboard'))
        return redirect(url_for('services_categories'))
    
    return render_template('register.html', role=role, categories=TRADE_CATEGORIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or request.form.get('ajax') == '1'
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        
        if not username or not password:
            error_msg = "Please enter both username and password."
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 400
            return render_template('login.html', error=error_msg)
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                error_msg = "Your account is deactivated. Please contact the administrator."
                if is_ajax:
                    return jsonify({'success': False, 'message': error_msg}), 403
                return render_template('login.html', error=error_msg)
            
            # Direct access for admin
            if user.is_admin:
                session['username'] = username
                if is_ajax:
                    return jsonify({
                        'success': True,
                        'message': 'Welcome Administrator! Access granted.',
                        'redirect': url_for('admin_dashboard')
                    })
                return redirect(url_for('admin_dashboard'))
            
            # For registered residents, generate OTP and dispatch to registered email
            otp = str(random.randint(100000, 999999))
            
            OTPSession.query.filter_by(username=username).delete()
            otp_session = OTPSession(username=username, otp=otp)
            db.session.add(otp_session)
            db.session.commit()
            
            # Send OTP to user's registered email asynchronously in background thread
            threading.Thread(target=send_otp_email, args=(user.email, otp), daemon=True).start()
            session['temp_username'] = username
            session['email_sent'] = True
            session['last_otp'] = otp
            
            masked_email = user.email
            if '@' in user.email:
                parts = user.email.split('@')
                name_part = parts[0]
                masked_email = (name_part[:2] + '***' + name_part[-1:] if len(name_part) > 3 else name_part[:1] + '***') + '@' + parts[1]
            
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': f"Security passcode sent to {masked_email}! Redirecting to verification...",
                    'redirect': url_for('verify_otp')
                })
            return redirect(url_for('verify_otp'))
            
        else:
            error_msg = "Invalid username or password! Please check your credentials and try again."
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 401
            return render_template('login.html', error=error_msg)
    
    return render_template('login.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'temp_username' not in session:
        return redirect(url_for('login'))
    
    username = session['temp_username']
    user = User.query.filter_by(username=username).first()
    if not user:
        session.pop('temp_username', None)
        return redirect(url_for('login'))
    
    masked_email = user.email
    if '@' in user.email:
        parts = user.email.split('@')
        name_part = parts[0]
        masked_email = (name_part[:2] + '***' + name_part[-1:] if len(name_part) > 3 else name_part[:1] + '***') + '@' + parts[1]
    
    email_sent = session.get('email_sent', True)
    last_otp = session.get('last_otp')
    
    if request.method == 'POST':
        entered_otp = (request.form.get('otp') or '').strip()
        
        otp_record = OTPSession.query.filter_by(username=username, otp=entered_otp).first()
        
        if otp_record:
            db.session.delete(otp_record)
            db.session.commit()
            
            session.pop('temp_username', None)
            session.pop('email_sent', None)
            session.pop('last_otp', None)
            session['username'] = username
            
            if user.role == 'provider':
                return redirect(url_for('services_provider_dashboard'))
            return redirect(url_for('services_categories'))
        else:
            return render_template('verify_otp.html', user=user, masked_email=masked_email, email_sent=email_sent, last_otp=last_otp, error="Invalid OTP passcode! Please enter the 6-digit code received on your registered email.")
    
    return render_template('verify_otp.html', user=user, masked_email=masked_email, email_sent=email_sent, last_otp=last_otp)

@app.route('/resend-otp', methods=['GET', 'POST'])
def resend_otp():
    if 'temp_username' not in session:
        return redirect(url_for('login'))
    
    username = session['temp_username']
    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('login'))
    
    otp = str(random.randint(100000, 999999))
    OTPSession.query.filter_by(username=username).delete()
    otp_session = OTPSession(username=username, otp=otp)
    db.session.add(otp_session)
    db.session.commit()
    
    # Dispatch OTP in background thread
    threading.Thread(target=send_otp_email, args=(user.email, otp), daemon=True).start()
    session['email_sent'] = True
    session['last_otp'] = otp
    
    masked_email = user.email
    if '@' in user.email:
        parts = user.email.split('@')
        name_part = parts[0]
        masked_email = (name_part[:2] + '***' + name_part[-1:] if len(name_part) > 3 else name_part[:1] + '***') + '@' + parts[1]
    
    return render_template('verify_otp.html', user=user, masked_email=masked_email, email_sent=email_sent, last_otp=otp, success=f"A fresh security passcode has been dispatched to {masked_email}!")

@app.route('/profile-setup', methods=['GET', 'POST'])
def profile_setup():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    if user.is_admin:
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        user.name = request.form['name']
        user.contact = request.form['contact']
        user.location = request.form['location']
        user.blood_group = request.form.get('blood_group')
        
        skills = request.form.getlist('skills')
        if skills:
            user.skills = ','.join(skills)
        
        interests = request.form.getlist('interests')
        if interests:
            user.interests = ','.join(interests)
        
        trust_score = 50
        if user.name: trust_score += 10
        if user.contact: trust_score += 5
        if user.location: trust_score += 10
        if user.blood_group: trust_score += 5
        if user.skills: trust_score += 10
        if user.interests: trust_score += 5
        user.trust_score = min(100, trust_score)
        
        db.session.commit()
        return redirect(url_for('profile'))
    
    return render_template('profile_setup.html', user=user)


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    if user.is_admin:
       return redirect(url_for('admin_dashboard'))
   
    
    unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    unread_messages = ChatMessage.query.filter_by(receiver_id=user.id, is_read=False).count()
    recent_matches = find_matches_for_user(user)[:5]
    
    return render_template('dashboard.html', 
                         user=user, 
                         unread_count=unread_count,
                         unread_messages=unread_messages,
                         recent_matches=recent_matches)

@app.route('/create-post', methods=['GET', 'POST'])
def create_post():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        post_type = (request.form.get('post_type') or 'Request Help').strip()
        category = (request.form.get('category') or 'Local Services').strip()
        service_subcategory = (request.form.get('service_subcategory') or '').strip().lower()
        title = (request.form.get('title') or '').strip()
        description = (request.form.get('description') or '').strip()
        location = (request.form.get('location') or 'Sangamner').strip()
        urgency = (request.form.get('urgency') or 'Normal').strip()
        
        full_text = f"{title}. {description}" if title else description
        nlp_data = process_post_text(full_text)
        
        # If trade subcategory was selected, attach to entities
        if not nlp_data.get('entities'):
            nlp_data['entities'] = {}
        if service_subcategory:
            nlp_data['entities']['trade'] = service_subcategory
            nlp_data['entities']['skill'] = service_subcategory
        elif 'trade' in nlp_data.get('entities', {}):
            service_subcategory = nlp_data['entities']['trade']
        else:
            service_subcategory = 'plumber'
        
        # Determine intent: if 'Request Help', intent is 'NEED'; if 'Offer', intent is 'OFFER'
        intent = nlp_data.get('intent', 'NEED')
        if 'request' in post_type.lower() or 'help' in post_type.lower():
            intent = 'NEED'
        elif 'offer' in post_type.lower():
            intent = 'OFFER'
        
        new_post = Post(
            user_id=user.id,
            title=title,
            post_type=post_type,
            description=description,
            category=category,
            service_subcategory=service_subcategory,
            location=location or 'Sangamner',
            urgency=urgency,
            intent=intent,
            extracted_entities=json.dumps(nlp_data.get('entities', {}))
        )
        db.session.add(new_post)
        db.session.commit()
        
        matches = find_matches(new_post)
        
        # Send email notifications to matches
        for match in matches[:5]:
            matched_user = match['user']
            subject = f"🔔 New {new_post.category} Match in {new_post.location}!"
            message = f"""
            Hello {matched_user.name or matched_user.username},
            
            A new notice matching your profile has been posted in {new_post.location}:
            
            Type: {new_post.post_type}
            Category: {new_post.category}
            Title: {new_post.title or 'Help Request'}
            Description: {description[:200]}...
            Urgency: {new_post.urgency}
            
            Match Score: {match['match_score']}%
            
            Login to view full details and connect.
            """
            
            # Send email notification
            send_notification_email(matched_user.email, subject, message)
            
            # Also create in-app notification
            notification = Notification(
                user_id=matched_user.id,
                message=f"New {new_post.category} post in {new_post.location} matched with you!",
                type='match',
                post_id=new_post.id
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return render_template('post_created.html', 
                             post=new_post, 
                             matches=matches,
                             user=user)
    
    # If trade was passed, redirect to dedicated Service Required form
    if request.args.get('trade'):
        return redirect(url_for('request_service', category=request.args.get('trade')))

    # Pre-filled draft defaults as specified by user
    req_trade = (request.args.get('trade') or 'plumber').strip().lower()
    draft = {
        'post_type': 'Request Help',
        'category': 'Local Services',
        'service_subcategory': req_trade,
        'title': f'Need {req_trade.replace("_", " ").title()} in Sangamner' if req_trade and req_trade != 'plumber' else '',
        'description': '',
        'location': 'Sangamner',
        'urgency': 'Normal'
    }
    return render_template('create_post.html', user=user, draft=draft)

@app.route('/request-service', methods=['GET', 'POST'])
def request_service():
    if 'username' not in session:
        return redirect(url_for('login', next=request.url))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        service_category = (request.form.get('service_category') or 'Plumbing').strip()
        required_service = (request.form.get('required_service') or '').strip()
        full_name = (request.form.get('full_name') or user.name or user.username).strip()
        mobile_number = (request.form.get('mobile_number') or user.contact or '').strip()
        service_location = (request.form.get('service_location') or user.location or 'Sangamner').strip()
        preferred_date = (request.form.get('preferred_date') or '').strip()
        expected_budget = (request.form.get('expected_budget') or 'Need provider quotation').strip()
        urgency = (request.form.get('urgency') or 'Normal').strip()
        describe_requirement = (request.form.get('describe_requirement') or '').strip()
        
        # Keep user profile up-to-date
        if mobile_number and not user.contact:
            user.contact = mobile_number
        if full_name and not user.name:
            user.name = full_name
            
        # Map category to trade subcategory
        cat_lower = service_category.lower()
        cat_map = {
            'plumb': 'plumber',
            'elec': 'electrician',
            'clean': 'cleaner',
            'ac': 'ac_technician',
            'carp': 'carpenter',
            'paint': 'painter',
            'mason': 'mason',
            'cook': 'cook',
            'driver': 'driver',
            'garden': 'gardener',
            'sec': 'security',
            'tailor': 'tailor',
            'tutor': 'tutor',
            'nurse': 'nurse'
        }
        trade_key = 'plumber'
        for key, val in cat_map.items():
            if key in cat_lower:
                trade_key = val
                break
                
        # Urgency normalization
        sys_urgency = 'Normal'
        if 'emergency' in urgency.lower():
            sys_urgency = 'Urgent'
        elif '24 hours' in urgency.lower():
            sys_urgency = 'High'
        elif 'flexible' in urgency.lower():
            sys_urgency = 'Low'

        title = f"{required_service or service_category} - {service_category}"
        description_body = f"""Required Service: {required_service}
Category: {service_category}
Client: {full_name}
Mobile: {mobile_number}
Location: {service_location}
Preferred Service Date: {preferred_date or 'Immediate / Flexible'}
Expected Budget: {expected_budget}
Urgency: {urgency}

Requirement Details:
{describe_requirement}"""

        full_text = f"{title}. {description_body}"
        nlp_data = process_post_text(full_text)
        if not nlp_data.get('entities'):
            nlp_data['entities'] = {}
        nlp_data['entities']['trade'] = trade_key
        nlp_data['entities']['skill'] = trade_key
        nlp_data['entities']['budget'] = expected_budget
        nlp_data['entities']['mobile'] = mobile_number
        if preferred_date:
            nlp_data['entities']['preferred_date'] = preferred_date

        new_post = Post(
            user_id=user.id,
            title=title,
            post_type='Request Help',
            description=description_body,
            category='Local Services',
            service_subcategory=trade_key,
            location=service_location,
            urgency=sys_urgency,
            intent='NEED',
            extracted_entities=json.dumps(nlp_data.get('entities', {}))
        )
        db.session.add(new_post)
        db.session.commit()
        
        matches = find_matches(new_post)
        
        for match in matches[:5]:
            matched_user = match['user']
            subject = f"🔔 New Service Request: {required_service or service_category} in {service_location}!"
            msg_text = f"""Hello {matched_user.name or matched_user.username},

A new service request matching your profile has been submitted:
Required Service: {required_service}
Category: {service_category}
Client Name: {full_name}
Mobile: {mobile_number}
Location: {service_location}
Budget: {expected_budget}
Urgency: {urgency}
Preferred Date: {preferred_date or 'Immediate / Flexible'}

Match Score: {match['match_score']}%
Login to view and connect with the client.
"""
            send_notification_email(matched_user.email, subject, msg_text)
            notification = Notification(
                user_id=matched_user.id,
                message=f"New service request for {required_service or service_category} in {service_location} matches your skills!",
                type='service_request',
                post_id=new_post.id
            )
            db.session.add(notification)
        db.session.commit()
        
        return render_template('post_created.html',
                               post=new_post,
                               matches=matches,
                               user=user)

    # GET request
    cat_param = (request.args.get('category') or 'plumber').strip().lower()
    selected_category = 'Plumbing'
    if 'elec' in cat_param:
        selected_category = 'Electrician'
    elif 'clean' in cat_param:
        selected_category = 'Cleaning & Housekeeping'
    elif 'ac' in cat_param:
        selected_category = 'AC Servicing & Repair'
    elif 'carp' in cat_param:
        selected_category = 'Carpentry & Woodwork'
    elif 'paint' in cat_param:
        selected_category = 'Painting & Waterproofing'
    elif 'mason' in cat_param:
        selected_category = 'Masonry & Renovation'
    elif 'cook' in cat_param:
        selected_category = 'Cook & Catering'
    elif 'driver' in cat_param:
        selected_category = 'Driver & Chauffeur'
    elif 'garden' in cat_param:
        selected_category = 'Gardening & Lawn Care'
    elif 'sec' in cat_param:
        selected_category = 'Security & Guard'
    elif 'tailor' in cat_param:
        selected_category = 'Tailoring & Alterations'
    elif 'tutor' in cat_param:
        selected_category = 'Home Tutoring'
    elif 'nurse' in cat_param:
        selected_category = 'Nursing & Elder Care'
    elif 'other' in cat_param:
        selected_category = 'Other Skilled Service'

    return render_template('request_service.html',
                           user=user,
                           selected_category=selected_category,
                           categories=TRADE_CATEGORIES)


@app.route('/my-posts')
def my_posts():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    
    # IMPORTANT: Pass 'user' to template
    return render_template('my_posts.html', posts=posts, user=user)

@app.route('/matches')
def matches():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    post_matches = []
    user_posts = Post.query.filter_by(user_id=user.id, status='active').all()
    
    for post in user_posts:
        matches_list = find_matches(post)
        for match in matches_list:
            match['post'] = post
            post_matches.append(match)
    
    profile_matches = find_matches_for_user(user)
    
    return render_template('matches.html', 
                         post_matches=post_matches,
                         profile_matches=profile_matches,
                         user=user)

@app.route('/display-results')
def display_results():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    post_id = request.args.get('post_id', type=int)
    
    if post_id:
        post = Post.query.get_or_404(post_id)
        if post.user_id == user.id:
            results = find_matches(post)
        else:
            results = []
    else:
        results = []
        potential_matches = User.query.filter(User.id != user.id, User.is_active == True).all()
        
        for potential in potential_matches:
            score = 0
            reasons = []
            if potential.location == user.location:
                score += 30
                reasons.append(f"Same location: {potential.location}")
            if potential.skills and user.interests:
                score += 20
                reasons.append("Skills match your interests")
            if potential.rating and potential.rating >= 4:
                score += 10
                reasons.append(f"High rating: {potential.rating}⭐")
            
            if score > 0:
                results.append({
                    'user': potential,
                    'match_score': score,
                    'match_reasons': reasons
                })
        
        results.sort(key=lambda x: x['match_score'], reverse=True)
    
    formatted_results = []
    for result in results[:20]:
        matched_user = result['user']
        formatted_results.append({
            'id': matched_user.id,
            'name': matched_user.name or matched_user.username,
            'contact': matched_user.contact or 'Not provided',
            'location': matched_user.location or 'Unknown',
            'rating': matched_user.rating or 0,
            'trust_score': matched_user.trust_score,
            'match_score': result['match_score'],
            'match_reasons': result.get('match_reasons', []),
            'skills': matched_user.skills,
            'blood_group': matched_user.blood_group
        })
    
    return render_template('display_results.html', results=formatted_results)

@app.route('/chat')
def chat():
    return communication()

@app.route('/communication')
def communication():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    other_user_id = request.args.get('user_id', type=int)
    other_user = User.query.get(other_user_id) if other_user_id else None
    
    # Get all users that current user has chatted with
    conversations = []
    try:
        # Get unique user IDs from messages
        sent_messages = ChatMessage.query.filter_by(sender_id=user.id).all()
        received_messages = ChatMessage.query.filter_by(receiver_id=user.id).all()
        
        chat_user_ids = set()
        for msg in sent_messages:
            chat_user_ids.add(msg.receiver_id)
        for msg in received_messages:
            chat_user_ids.add(msg.sender_id)
        
        for uid in chat_user_ids:
            chat_user = User.query.get(uid)
            if chat_user:
                # Get last message
                last_message = ChatMessage.query.filter(
                    ((ChatMessage.sender_id == user.id) & (ChatMessage.receiver_id == uid)) |
                    ((ChatMessage.sender_id == uid) & (ChatMessage.receiver_id == user.id))
                ).order_by(ChatMessage.timestamp.desc()).first()
                
                unread_count = ChatMessage.query.filter_by(
                    receiver_id=user.id, sender_id=uid, is_read=False
                ).count()
                
                conversations.append({
                    'user': chat_user,
                    'last_message': last_message,
                    'unread_count': unread_count
                })
    except Exception as e:
        print(f"Chat error: {e}")
        conversations = []
    
    # Get messages with selected user
    messages = []
    if other_user:
        try:
            messages = ChatMessage.query.filter(
                ((ChatMessage.sender_id == user.id) & (ChatMessage.receiver_id == other_user.id)) |
                ((ChatMessage.sender_id == other_user.id) & (ChatMessage.receiver_id == user.id))
            ).order_by(ChatMessage.timestamp.asc()).all()
            
            # Mark messages as read
            for msg in messages:
                if msg.receiver_id == user.id and not msg.is_read:
                    msg.is_read = True
            db.session.commit()
        except Exception as e:
            print(f"Messages error: {e}")
            messages = []
    
    return render_template('communication.html', 
                         conversations=conversations,
                         current_user=user,
                         other_user=other_user,
                         messages=messages)
@app.route('/send-message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        receiver_id = data.get('receiver_id')
        message = data.get('message')
        
        if not message or not receiver_id:
            return jsonify({'error': 'Missing data'}), 400
        
        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Check if receiver exists
        receiver = User.query.get(receiver_id)
        if not receiver:
            return jsonify({'error': 'Receiver not found'}), 404
        
        # Create new message
        new_message = ChatMessage(
            sender_id=user.id,
            receiver_id=receiver_id,
            message=message,
            is_read=False
        )
        db.session.add(new_message)
        db.session.commit()
        
        # Create notification for receiver
        notification = Notification(
            user_id=receiver_id,
            message=f"New message from {user.name or user.username}: {message[:50]}...",
            type='message'
        )
        db.session.add(notification)
        db.session.commit()
        
        print(f"✓ Message sent from {user.username} to {receiver.username}")
        
        return jsonify({
            'success': True, 
            'message_id': new_message.id,
            'message': message,
            'timestamp': new_message.timestamp.strftime('%I:%M %p')
        })
        
    except Exception as e:
        print(f"Error sending message: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/upload-chat-file', methods=['POST'])
def upload_chat_file():
    """Upload a file/image and send it as a chat message"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 401

        receiver_id = request.form.get('receiver_id')
        if not receiver_id:
            return jsonify({'error': 'Missing receiver_id'}), 400

        receiver = User.query.get(receiver_id)
        if not receiver:
            return jsonify({'error': 'Receiver not found'}), 404

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400

        original_name = secure_filename(file.filename)
        ext = original_name.rsplit('.', 1)[1].lower()
        unique_name = f"{user.id}_{int(datetime.utcnow().timestamp())}_{original_name}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)

        caption = request.form.get('message', '').strip()

        new_message = ChatMessage(
            sender_id=user.id,
            receiver_id=receiver_id,
            message=caption if caption else '',
            file_path=unique_name,
            file_name=original_name,
            file_type=ext,
            is_read=False
        )
        db.session.add(new_message)
        db.session.commit()

        notification = Notification(
            user_id=receiver_id,
            message=f"{user.name or user.username} sent you a file: {original_name}",
            type='message'
        )
        db.session.add(notification)
        db.session.commit()

        print(f"✓ File sent from {user.username} to {receiver.username}: {original_name}")

        return jsonify({
            'success': True,
            'message_id': new_message.id,
            'file_name': original_name,
            'file_url': url_for('chat_file', filename=unique_name),
            'file_type': ext,
            'timestamp': new_message.timestamp.strftime('%I:%M %p')
        })

    except Exception as e:
        print(f"Error uploading chat file: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/chat_files/<path:filename>')
def chat_file(filename):
    """Serve uploaded chat files (only to the sender or receiver of that message)"""
    if 'username' not in session:
        return "Unauthorized", 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return "Unauthorized", 401

    msg = ChatMessage.query.filter_by(file_path=filename).first()
    if not msg or (msg.sender_id != user.id and msg.receiver_id != user.id):
        return "Forbidden", 403

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
@app.route('/api/get-conversations')
def get_conversations():
    """Get all conversations for current user, optionally including a matched user"""
    if 'username' not in session:
        return jsonify({'conversations': []})
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'conversations': []})
    
    include_user_id = request.args.get('include_user_id', type=int)
    
    # Get all users that current user has exchanged messages with
    sent_messages = ChatMessage.query.filter_by(sender_id=user.id).all()
    received_messages = ChatMessage.query.filter_by(receiver_id=user.id).all()
    
    conversation_users = set()
    for msg in sent_messages:
        conversation_users.add(msg.receiver_id)
    for msg in received_messages:
        conversation_users.add(msg.sender_id)
    
    # If a specific user to chat with is requested (e.g. from Find Matches), ensure they are included!
    if include_user_id and include_user_id != user.id:
        conversation_users.add(include_user_id)
    
    conversations = []
    for other_id in conversation_users:
        other_user = User.query.get(other_id)
        if other_user:
            # Get last message
            last_msg = ChatMessage.query.filter(
                ((ChatMessage.sender_id == user.id) & (ChatMessage.receiver_id == other_id)) |
                ((ChatMessage.sender_id == other_id) & (ChatMessage.receiver_id == user.id))
            ).order_by(ChatMessage.timestamp.desc()).first()
            
            # Get unread count
            unread_count = ChatMessage.query.filter_by(
                sender_id=other_id, receiver_id=user.id, is_read=False
            ).count()
            
            conversations.append({
                'user_id': other_user.id,
                'name': other_user.name or other_user.username,
                'last_message': (last_msg.message[:50] if last_msg.message else f"📎 {last_msg.file_name}") if last_msg else "Direct match - start conversation",
                'last_time': last_msg.timestamp.strftime('%H:%M') if last_msg and last_msg.timestamp else "Now",
                'unread_count': unread_count,
                'is_target': (other_id == include_user_id)
            })
    
    # Sort conversations: Target new match first, then by last message time
    conversations.sort(key=lambda x: (1 if x.get('is_target') and x.get('last_time') == 'Now' else 0, x['last_time'] or ''), reverse=True)
    
    return jsonify({'conversations': conversations})

@app.route('/api/get-my-posts')
def get_my_posts():
    """Get the current user's own posts (for the Send Request post picker)"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    posts = Post.query.filter_by(user_id=user.id, status='active').order_by(Post.timestamp.desc()).all()

    posts_list = [{
        'id': p.id,
        'description': p.description[:80],
        'category': p.category
    } for p in posts]

    return jsonify({'posts': posts_list})

@app.route('/api/get-all-users')
def get_all_users():
    """Get all active users (for Find People to Chat With)"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    users = User.query.filter(User.id != current_user.id, User.is_active == True).all()

    users_list = [{
        'id': u.id,
        'name': u.name or u.username,
        'username': u.username,
        'location': u.location,
        'interests': u.interests,
        'rating': round(u.rating, 1) if u.rating else None,
        'trust_score': u.trust_score
    } for u in users]

    return jsonify({'users': users_list})

@app.route('/api/get-new-messages/<int:other_user_id>')
def get_new_messages(other_user_id):
    """Get new messages from specific user"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # Get ALL unread messages from the other user (not just new ones)
    new_messages = ChatMessage.query.filter_by(
        sender_id=other_user_id,
        receiver_id=user.id,
        is_read=False
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'message': msg.message,
            'file_url': url_for('chat_file', filename=msg.file_path) if msg.file_path else None,
            'file_name': msg.file_name,
            'file_type': msg.file_type,
            'timestamp': msg.timestamp.strftime('%I:%M %p'),
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.name if msg.sender else 'Unknown'
        })
        # Mark as read
        msg.is_read = True
    
    db.session.commit()
    
    print(f"📨 Found {len(messages_data)} new messages for user {user.username}")
    
    return jsonify({'messages': messages_data})


@app.route('/api/get-all-messages/<int:other_user_id>')
def get_all_messages(other_user_id):
    """Get ALL messages between users (for initial load)"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # Get all messages between the two users
    all_messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == user.id) & (ChatMessage.receiver_id == other_user_id)) |
        ((ChatMessage.sender_id == other_user_id) & (ChatMessage.receiver_id == user.id))
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    messages_data = []
    for msg in all_messages:
        messages_data.append({
            'id': msg.id,
            'message': msg.message,
            'file_url': url_for('chat_file', filename=msg.file_path) if msg.file_path else None,
            'file_name': msg.file_name,
            'file_type': msg.file_type,
            'timestamp': msg.timestamp.strftime('%I:%M %p'),
            'sender_id': msg.sender_id,
            'sender_name': (msg.sender.name or msg.sender.username) if msg.sender else 'User',
            'is_mine': msg.sender_id == user.id
        })
    
    # Mark received messages as read
    unread_messages = ChatMessage.query.filter_by(
        sender_id=other_user_id,
        receiver_id=user.id,
        is_read=False
    ).all()
    for msg in unread_messages:
        msg.is_read = True
    db.session.commit()
    
    return jsonify({'messages': messages_data})
@app.route('/send-request', methods=['POST'])
def send_request():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        provider_id = data.get('provider_id')
        post_id = data.get('post_id')
        message = data.get('message', '')
        
        if not provider_id or not post_id:
            return jsonify({'error': 'Provider ID and Post ID are required'}), 400
        
        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check if request already exists
        existing = ServiceRequest.query.filter_by(
            requester_id=user.id,
            provider_id=provider_id,
            post_id=post_id,
            status='pending'
        ).first()
        
        if existing:
            return jsonify({'error': 'Request already sent'}), 400
        
        # Create new request
        new_request = ServiceRequest(
            requester_id=user.id,
            provider_id=provider_id,
            post_id=post_id,
            message=message
        )
        db.session.add(new_request)
        db.session.commit()
        
        # Create notification for provider
        notification = Notification(
            user_id=provider_id,
            message=f"New service request from {user.name or user.username} for: {post.description[:100]}",
            type='request',
            post_id=post_id
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True, 'request_id': new_request.id})
        
    except Exception as e:
        print(f"Error sending request: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/my-requests')
def my_requests():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    sent_requests = ServiceRequest.query.filter_by(requester_id=user.id).order_by(
        ServiceRequest.created_at.desc()
    ).all()
    
    received_requests = ServiceRequest.query.filter_by(provider_id=user.id).order_by(
        ServiceRequest.created_at.desc()
    ).all()
    
    return render_template('requests.html', 
                         sent_requests=sent_requests,
                         received_requests=received_requests)

@app.route('/update-request/<int:request_id>', methods=['POST'])
def update_request(request_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        status = data.get('status')
        if not status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Get the request
        service_request = ServiceRequest.query.get(request_id)
        if not service_request:
            return jsonify({'error': 'Request not found'}), 404
        
        # Get current user
        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Check authorization - only requester or provider can update
        if service_request.requester_id != user.id and service_request.provider_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update status
        service_request.status = status
        db.session.commit()
        
        # Create notification for the other party
        notify_user_id = service_request.requester_id if service_request.provider_id == user.id else service_request.provider_id
        
        notification = Notification(
            user_id=notify_user_id,
            message=f"Request {status}: {service_request.post.description[:100] if service_request.post else 'Service request'}",
            type='request_update'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True, 'status': status})
        
    except Exception as e:
        print(f"Error updating request: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/rate-user/<int:user_id>', methods=['POST'])
def rate_user(user_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400
    
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401
    
    rated_user = User.query.get_or_404(user_id)
    
    existing = Feedback.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=user_id
    ).first()
    
    if existing:
        existing.rating = rating
        existing.comment = comment
    else:
        feedback = Feedback(
            from_user_id=current_user.id,
            to_user_id=user_id,
            rating=rating,
            comment=comment
        )
        db.session.add(feedback)
    
    db.session.flush()
    all_ratings = Feedback.query.filter_by(to_user_id=user_id).all()
    if all_ratings:
        avg_rating = sum(r.rating for r in all_ratings) / len(all_ratings)
        rated_user.rating = round(avg_rating, 1)
        rated_user.total_ratings = len(all_ratings)
        rated_user.trust_score = min(100, max(40, int(avg_rating * 18 + min(len(all_ratings) * 2, 10))))
    
    db.session.commit()
    
    return jsonify({'success': True, 'new_rating': rated_user.rating, 'trust_score': rated_user.trust_score})

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    target_user_id = request.args.get('user_id', type=int)

    if request.method == 'POST':
        to_user_id = request.form.get('to_user_id', type=int)
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()

        if not to_user_id or not rating or rating < 1 or rating > 5:
            flash("Please choose a valid rating and recipient.", "error")
            return redirect(url_for('feedback', user_id=to_user_id or ''))

        if to_user_id == user.id:
            flash("You cannot review yourself.", "error")
            return redirect(url_for('feedback'))

        rated_user = User.query.get(to_user_id)
        if not rated_user:
            flash("User not found.", "error")
            return redirect(url_for('feedback'))

        existing = Feedback.query.filter_by(
            from_user_id=user.id,
            to_user_id=to_user_id
        ).first()

        if existing:
            existing.rating = rating
            existing.comment = comment
        else:
            new_fb = Feedback(
                from_user_id=user.id,
                to_user_id=to_user_id,
                rating=rating,
                comment=comment
            )
            db.session.add(new_fb)

        # Update average rating and trust score
        db.session.flush()
        all_ratings = Feedback.query.filter_by(to_user_id=to_user_id).all()
        if all_ratings:
            avg_rating = sum(r.rating for r in all_ratings) / len(all_ratings)
            rated_user.rating = round(avg_rating, 1)
            rated_user.total_ratings = len(all_ratings)
            rated_user.trust_score = min(100, max(40, int(avg_rating * 18 + min(len(all_ratings) * 2, 10))))

        # Notify recipient
        notification = Notification(
            user_id=to_user_id,
            message=f"⭐ {user.name or user.username} left you a {rating}-star review: \"{comment[:40]}...\"" if comment else f"⭐ {user.name or user.username} left you a {rating}-star review!"
        )
        db.session.add(notification)
        db.session.commit()

        flash(f"Feedback successfully submitted for {rated_user.name or rated_user.username}!", "success")
        return redirect(url_for('feedback'))
    
    received_feedback = Feedback.query.filter_by(to_user_id=user.id).order_by(
        Feedback.created_at.desc()
    ).all()
    
    given_feedback = Feedback.query.filter_by(from_user_id=user.id).order_by(
        Feedback.created_at.desc()
    ).all()

    # Users available to give feedback to (all active users except current user)
    all_users = User.query.filter(User.id != user.id, User.is_active == True).order_by(User.name.asc()).all()
    
    return render_template('feedback.html', 
                         received_feedback=received_feedback,
                         given_feedback=given_feedback,
                         all_users=all_users,
                         target_user_id=target_user_id,
                         user=user)

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

@app.route('/notifications')
def notifications():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    user_notifications = Notification.query.filter_by(user_id=user.id).order_by(
        Notification.created_at.desc()
    ).all()
    
    for notif in user_notifications:
        if not notif.is_read:
            notif.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', notifications=user_notifications, user=user)

@app.route('/admin')
def admin_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user or not user.is_admin:
        return "Access denied", 403
    
    stats = {
        'total_users': User.query.count(),
        'total_posts': Post.query.count(),
        'active_posts': Post.query.filter_by(status='active').count(),
        'total_requests': ServiceRequest.query.count()
    }
    
    # Get all users and posts for the admin panels
    users = User.query.all()
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    
    # Get category statistics
    categories = {}
    for post in Post.query.all():
        if post.category:
            categories[post.category] = categories.get(post.category, 0) + 1
    
    return render_template('admin.html', 
                         user=user, 
                         stats=stats,
                         users=users,
                         posts=posts,
                         categories=categories)

@app.route('/admin/users')
def admin_users():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user or not user.is_admin:
        return "Access denied", 403
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/posts')
def admin_posts():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user or not user.is_admin:
        return "Access denied", 403
    
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('admin_posts.html', posts=posts, user=user)

@app.route('/admin/delete-user/<int:user_id>')
def admin_delete_user(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    admin = User.query.filter_by(username=session['username']).first()
    if not admin or not admin.is_admin:
        return "Access denied", 403
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        return "Cannot delete admin", 403
    
    user.is_active = False
    db.session.commit()
    
    return redirect(url_for('admin_users'))

@app.route('/admin/delete-post/<int:post_id>')
def admin_delete_post(post_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    admin = User.query.filter_by(username=session['username']).first()
    if not admin or not admin.is_admin:
        return "Access denied", 403
    
    post = Post.query.get_or_404(post_id)
    post.status = 'removed'
    db.session.commit()
    
    return redirect(url_for('admin_posts'))

@app.route('/admin/categories')
def admin_categories():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user or not user.is_admin:
        return "Access denied", 403
    
    categories = {}
    for post in Post.query.all():
        if post.category:
            categories[post.category] = categories.get(post.category, 0) + 1
    
    return render_template('admin_categories.html', categories=categories)

@app.route('/recommendations')
def recommendations():
    """Get personalized recommendations based on user profile"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    recommendations = []
    
    # 1. Find matching posts based on user's skills
    matching_posts = Post.query.filter(
        Post.user_id != user.id,
        Post.status == 'active'
    ).all()
    
    for post in matching_posts:
        # Skip if post doesn't exist
        if not post:
            continue
            
        match_score = 0
        match_reasons = []
        
        try:
            entities = json.loads(post.extracted_entities) if post.extracted_entities else {}
        except:
            entities = {}
        
        # Check if user can help with this post
        if post.category == "MEDICAL":
            needed_blood = entities.get('blood_group')
            if needed_blood and user.blood_group:
                if user.blood_group.upper() == needed_blood.upper():
                    match_score += 50
                    match_reasons.append(f"You can donate blood: {needed_blood}")
        
        elif post.category == "SERVICE":
            needed_skill = entities.get('skill')
            if needed_skill and user.skills:
                if needed_skill.lower() in user.skills.lower():
                    match_score += 50
                    match_reasons.append(f"You can provide: {needed_skill}")
        
        # Location match
        if post.location and user.location:
            if post.location.lower() == user.location.lower():
                match_score += 20
                match_reasons.append(f"Same location: {post.location}")
        
        if match_score > 0:
            post_creator = User.query.get(post.user_id)
            if post_creator:  # Make sure post creator exists
                recommendations.append({
                    'type': 'help_request',
                    'post': post,
                    'creator': post_creator,
                    'match_score': match_score,
                    'match_reasons': match_reasons,
                    'action': 'You can help them!'
                })
    
    # 2. Find users who can help with user's posts
    user_posts = Post.query.filter_by(user_id=user.id, status='active').all()
    for post in user_posts:
        if not post:
            continue
            
        helpers = find_matches(post)
        for helper in helpers[:3]:
            if helper and helper.get('user'):  # Check if helper exists
                recommendations.append({
                    'type': 'potential_helper',
                    'post': post,
                    'helper': helper['user'],
                    'match_score': helper['match_score'],
                    'match_reasons': helper['match_reasons'],
                    'action': 'This user can help you!'
                })
    
    # 3. General recommendations based on interests
    if user.interests:
        interest_list = [i.strip().lower() for i in user.interests.split(',')]
        relevant_posts = Post.query.filter(
            Post.user_id != user.id,
            Post.status == 'active'
        ).limit(10).all()  # Increased limit
        
        for post in relevant_posts:
            if not post:
                continue
                
            for interest in interest_list:
                if interest in post.description.lower() or interest in post.category.lower():
                    post_creator = User.query.get(post.user_id)
                    if post_creator:  # Make sure post creator exists
                        recommendations.append({
                            'type': 'interest_based',
                            'post': post,
                            'creator': post_creator,
                            'match_score': 40,
                            'match_reasons': [f"Matches your interest: {interest}"],
                            'action': 'Based on your interests'
                        })
                    break
    
    # Remove duplicates based on post ID
    seen_posts = set()
    unique_recs = []
    for rec in recommendations:
        post_id = rec.get('post', {}).id if rec.get('post') else None
        if post_id and post_id not in seen_posts:
            seen_posts.add(post_id)
            unique_recs.append(rec)
        elif not post_id:  # Keep recommendations without post_id
            unique_recs.append(rec)
    
    unique_recs.sort(key=lambda x: x['match_score'], reverse=True)
    
    return render_template('recommendations.html', 
                         recommendations=unique_recs[:20],
                         user=user)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/debug')
def debug():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'User not found'})
    
    all_users = User.query.all()
    all_posts = Post.query.all()
    
    debug_info = {
        'current_user': {
            'id': user.id,
            'username': user.username,
            'blood_group': user.blood_group,
            'skills': user.skills,
            'location': user.location
        },
        'total_users': len(all_users),
        'users': [{'id': u.id, 'username': u.username, 'blood_group': u.blood_group, 'skills': u.skills, 'location': u.location} for u in all_users if u.id != user.id],
        'total_posts': len(all_posts),
        'posts': [{'id': p.id, 'description': p.description[:100], 'category': p.category} for p in all_posts]
    }
    
    return jsonify(debug_info)

# ============ ROUTE ALIASES FOR COMPATIBILITY ============

@app.route('/find-matches/<int:post_id>')
def find_matches_route(post_id):
    """Alias for finding matches for a specific post"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    
    # Check if user owns this post
    if post.user_id != user.id:
        return "You don't have permission to view matches for this post", 403
    
    matches = find_matches(post)
    
    return render_template('find_matches.html', post=post, matches=matches, user=user)


@app.route('/view-profile/<int:user_id>')
def view_profile_route(user_id):
    """Alias for viewing another user's profile"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user:
        session.clear()
        return redirect(url_for('login'))
    
    profile_user = User.query.get_or_404(user_id)
    
    return render_template('view_profile.html', profile_user=profile_user, current_user=current_user)

@app.route('/api/get-unread-count')
def get_unread_count():
    if 'username' not in session:
        return jsonify({'count': 0})
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'count': 0})
    unread = ChatMessage.query.filter_by(receiver_id=user.id, is_read=False).count()
    return jsonify({'count': unread})


@app.route('/api/get-matches/<int:post_id>')
def api_get_matches(post_id):
    if 'username' not in session:
        return jsonify({'matches': []})
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'matches': []})
    
    post = Post.query.get_or_404(post_id)
    
    # Check if user owns this post
    if post.user_id != user.id:
        return jsonify({'matches': []})
    
    matches = find_matches(post)
    
    matches_data = []
    for match in matches:
        matches_data.append({
            'user': {
                'id': match['user'].id,
                'name': match['user'].name or match['user'].username,
                'location': match['user'].location,
                'rating': match['user'].rating,
                'trust_score': match['user'].trust_score,
                'blood_group': match['user'].blood_group,
                'skills': match['user'].skills,
                'contact': match.get('contact') or getattr(match['user'], 'contact', None)
            },
            'score': match['match_score'],
            'match_score': match['match_score'],
            'reason': ', '.join(match.get('match_reasons', [])),
            'reasons': match.get('match_reasons', []),
            'is_service_provider': match.get('is_service_provider', False),
            'trade_title': match.get('trade_title'),
            'trade_icon': match.get('trade_icon', '🛠️'),
            'rate_per_hour': match.get('rate_per_hour'),
            'rate_per_visit': match.get('rate_per_visit'),
            'experience_years': match.get('experience_years'),
            'availability': match.get('availability'),
            'service_area': match.get('service_area')
        })
    
    return jsonify({'matches': matches_data})

# ============ SERVICE MARKETPLACE ROUTES ============

TRADE_CATEGORIES = [
    {'key': 'plumber',       'label': 'Plumber',          'icon': '🔧', 'desc': 'Pipe fitting, leakage repair, bathroom fixtures', 'color': '#1565C0'},
    {'key': 'electrician',   'label': 'Electrician',       'icon': '⚡', 'desc': 'Wiring, switchboards, electrical faults',         'color': '#F57F17'},
    {'key': 'cleaner',       'label': 'Cleaner / Sweeper', 'icon': '🧹', 'desc': 'Home, office, deep cleaning services',            'color': '#2E7D32'},
    {'key': 'ac_technician', 'label': 'AC Technician',     'icon': '❄️', 'desc': 'AC installation, servicing, repair, gas refill',  'color': '#00838F'},
    {'key': 'carpenter',     'label': 'Carpenter',         'icon': '🪚', 'desc': 'Furniture, doors, woodwork, fittings',            'color': '#6D4C41'},
    {'key': 'painter',       'label': 'Painter',           'icon': '🎨', 'desc': 'Interior, exterior wall painting, polishing',     'color': '#AD1457'},
    {'key': 'mason',         'label': 'Mason / Labour',    'icon': '🧱', 'desc': 'Construction, tiling, cement work, renovation',   'color': '#4E342E'},
    {'key': 'cook',          'label': 'Cook / Chef',       'icon': '👨‍🍳', 'desc': 'Home cooking, catering, meal preparation',       'color': '#E65100'},
    {'key': 'driver',        'label': 'Driver',            'icon': '🚗', 'desc': 'Personal driver, cab, school van services',       'color': '#283593'},
    {'key': 'security',      'label': 'Security Guard',    'icon': '💂', 'desc': 'Residential, office, event security',             'color': '#1B5E20'},
    {'key': 'tailor',        'label': 'Tailor / Darzi',    'icon': '✂️', 'desc': 'Stitching, alterations, clothes repair',          'color': '#880E4F'},
    {'key': 'gardener',      'label': 'Gardener',          'icon': '🌿', 'desc': 'Lawn care, plant care, landscaping',              'color': '#33691E'},
    {'key': 'tutor',         'label': 'Tutor / Teacher',   'icon': '📚', 'desc': 'Home tuitions, coaching, all subjects',          'color': '#4527A0'},
    {'key': 'nurse',         'label': 'Nurse / Caretaker', 'icon': '🏥', 'desc': 'Home nursing, elderly care, child care',         'color': '#C62828'},
    {'key': 'other',         'label': 'Other Skilled',     'icon': '🛠️', 'desc': 'Other skilled trades and services',              'color': '#37474F'},
]

def get_category_info(key):
    return next((c for c in TRADE_CATEGORIES if c['key'] == key), None)

@app.route('/services')
def services_categories():
    """Public Services Marketplace - Amazon/Flipkart Style Mega Platform"""
    counts = {}
    for cat in TRADE_CATEGORIES:
        counts[cat['key']] = ServiceProfile.query.filter_by(
            trade_category=cat['key'], is_available=True).count()

    current_user = None
    my_bookings_count = 0
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()
        if current_user:
            my_bookings_count = ServiceBooking.query.filter_by(customer_id=current_user.id).count()

    # Load all verified providers with user data
    all_providers = (ServiceProfile.query
                     .join(User, ServiceProfile.user_id == User.id)
                     .filter(User.is_active == True)
                     .order_by(ServiceProfile.is_available.desc(), User.trust_score.desc())
                     .all())

    # Build rich Amazon-style featured services & deals
    search_q = (request.args.get('q') or '').strip().lower()
    selected_category = (request.args.get('category') or '').strip().lower()
    rating_filter = request.args.get('min_rating', type=float)

    filtered_providers = all_providers
    if selected_category and selected_category != 'all':
        filtered_providers = [p for p in filtered_providers if p.trade_category.lower() == selected_category]
    if search_q:
        filtered_providers = [p for p in filtered_providers if search_q in (p.user.name or '').lower() or search_q in (p.trade_category or '').lower() or search_q in (p.skills or '').lower() or search_q in (p.bio or '').lower()]
    if rating_filter:
        filtered_providers = [p for p in filtered_providers if (p.user.rating or 5.0) >= rating_filter]

    # Amazon Deals of the Day packages
    deals = [
        {
            'id': 1,
            'title': 'Emergency Tap Leakage & Sanitary Fitting',
            'category': 'plumber',
            'icon': '🔧',
            'badge': "Amazon's Choice",
            'price': 299,
            'orig_price': 499,
            'discount': '40% OFF',
            'arrival': '⚡ Within 30 Mins (Emergency Dispatch)',
            'highlights': ['Includes 30-day leak warranty', 'Spare parts checked & certified', 'Zero post-work cleanup hassle'],
            'tag': 'Bestseller in Home Repair'
        },
        {
            'id': 2,
            'title': 'Complete Ceiling Fan, Switchboard & MCB Repair',
            'category': 'electrician',
            'icon': '⚡',
            'badge': 'Top Rated Pro',
            'price': 249,
            'orig_price': 399,
            'discount': '38% OFF',
            'arrival': '⚡ Available Today by 3:00 PM',
            'highlights': ['Certified safety tester used', 'Wire insulation guaranteed', 'Same-day completion'],
            'tag': 'Neighborhood Favorite'
        },
        {
            'id': 3,
            'title': 'AC Deep Foam Jet Cleaning & Gas Top-up',
            'category': 'ac_technician',
            'icon': '❄️',
            'badge': 'Summer Deal',
            'price': 499,
            'orig_price': 899,
            'discount': '44% OFF',
            'arrival': '⚡ Today between 2 PM - 5 PM',
            'highlights': ['Indoor & outdoor jet cleaning', 'Gas pressure leak check', 'Improves cooling up to 2X'],
            'tag': 'High Demand'
        },
        {
            'id': 4,
            'title': 'Full 2BHK/3BHK Home Deep Sanitization & Scrubbing',
            'category': 'cleaner',
            'icon': '🧹',
            'badge': 'Super Value Pack',
            'price': 899,
            'orig_price': 1499,
            'discount': '40% OFF',
            'arrival': '⚡ Scheduled Morning / Evening',
            'highlights': ['Eco-friendly hospital-grade chemicals', 'Bathroom scale removal', 'Full kitchen degreasing'],
            'tag': 'Community Top Pick'
        },
        {
            'id': 5,
            'title': 'Custom Door Lock, Handle & Wooden Furniture Fix',
            'category': 'carpenter',
            'icon': '🪚',
            'badge': 'Verified Master',
            'price': 349,
            'orig_price': 499,
            'discount': '30% OFF',
            'arrival': '⚡ Available Today',
            'highlights': ['Precision alignment guaranteed', 'Heavy duty screws & bolts', 'Smoothest movement'],
            'tag': 'Precision Craft'
        },
        {
            'id': 6,
            'title': 'Living Room Waterproof Wall Painting & Touch-up',
            'category': 'painter',
            'icon': '🎨',
            'badge': 'Festive Offer',
            'price': 799,
            'orig_price': 1299,
            'discount': '38% OFF',
            'arrival': '⚡ Tomorrow Morning Slot',
            'highlights': ['Zero smell primer included', '2-coat premium finish', 'Furniture masked & protected'],
            'tag': 'Decor Choice'
        }
    ]

    return render_template('services_categories.html',
                           categories=TRADE_CATEGORIES,
                           counts=counts,
                           user=current_user,
                           all_providers=filtered_providers,
                           deals=deals,
                           my_bookings_count=my_bookings_count,
                           search_q=search_q,
                           selected_category=selected_category)

@app.route('/services/book', methods=['POST'])
def book_service():
    """1-Click Amazon-style Service Booking & Checkout"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Please sign in or register to book a service.'}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found.'}), 401

    provider_id = request.form.get('provider_id', type=int)
    service_title = (request.form.get('service_title') or 'Community Home Service').strip()
    category = (request.form.get('category') or 'General').strip()
    amount = float(request.form.get('amount') or 299)
    time_slot = (request.form.get('time_slot') or 'Today, 2:00 PM - 5:00 PM').strip()
    address = (request.form.get('address') or current_user.location or 'Sangamner, Ward 3').strip()
    phone = (request.form.get('phone') or current_user.contact or '').strip()
    payment_mode = (request.form.get('payment_mode') or 'Cash on Service').strip()

    # If provider_id is missing or 0, assign the top-rated provider for this category
    provider = None
    if provider_id:
        provider = User.query.get(provider_id)
    if not provider:
        sp = ServiceProfile.query.filter_by(trade_category=category.lower(), is_available=True).first()
        if sp:
            provider = sp.user
        else:
            provider = User.query.filter_by(is_admin=True).first()

    import random
    booking_code = f"SRV-{random.randint(10000, 99999)}"

    booking = ServiceBooking(
        booking_code=booking_code,
        customer_id=current_user.id,
        provider_id=provider.id if provider else current_user.id,
        service_title=service_title,
        category=category,
        amount=amount,
        time_slot=time_slot,
        address=address,
        phone=phone,
        payment_mode=payment_mode,
        status='Booked'
    )
    db.session.add(booking)

    if provider:
        notif_p = Notification(
            user_id=provider.id,
            message=f"📦 New Amazon-Style Service Order #{booking_code}! {current_user.name or current_user.username} booked {service_title} ({time_slot}) at {address}."
        )
        db.session.add(notif_p)

    notif_c = Notification(
        user_id=current_user.id,
        message=f"✓ Booking Confirmed! Order #{booking_code} for {service_title} scheduled for {time_slot}."
    )
    db.session.add(notif_c)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            'success': True,
            'booking_code': booking_code,
            'message': 'Service booked successfully!',
            'redirect_url': url_for('my_bookings')
        })

    flash(f"🎉 Booking Confirmed! Order #{booking_code} successfully placed. We have notified {provider.name if provider else 'the technician'}.", "success")
    return redirect(url_for('my_bookings'))

@app.route('/services/my-bookings')
def my_bookings():
    """Amazon/Flipkart-style 'Your Orders' & Service Tracker"""
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('login'))

    bookings = ServiceBooking.query.filter_by(customer_id=user.id).order_by(ServiceBooking.created_at.desc()).all()
    return render_template('my_bookings.html', user=user, bookings=bookings)

@app.route('/services/provider-dashboard')
def services_provider_dashboard():
    """Flipkart Seller Central / Service Provider Dashboard"""
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('login'))

    profile = ServiceProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        flash("Please complete your Service Provider registration first.", "info")
        return redirect(url_for('service_register'))

    bookings = ServiceBooking.query.filter_by(provider_id=user.id).order_by(ServiceBooking.created_at.desc()).all()
    feedbacks = Feedback.query.filter_by(to_user_id=user.id).order_by(Feedback.created_at.desc()).all()

    return render_template('provider_dashboard.html', user=user, profile=profile, bookings=bookings, feedbacks=feedbacks)

@app.route('/services/booking/update-status', methods=['POST'])
def update_booking_status():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.filter_by(username=session['username']).first()
    booking_id = request.form.get('booking_id', type=int)
    new_status = (request.form.get('status') or 'Completed').strip()

    booking = ServiceBooking.query.get_or_404(booking_id)
    if booking.provider_id != user.id and booking.customer_id != user.id and not user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    booking.status = new_status
    db.session.commit()
    flash(f"Order #{booking.booking_code} status updated to {new_status}!", "success")
    return redirect(request.referrer or url_for('my_bookings'))

@app.route('/services/<category_key>')
def services_browse(category_key):
    """Browse all providers in a specific trade category"""
    cat_info = get_category_info(category_key)
    if not cat_info:
        return redirect(url_for('services_categories'))

    current_user = None
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()

    providers = (ServiceProfile.query
                 .filter_by(trade_category=category_key)
                 .join(User, ServiceProfile.user_id == User.id)
                 .filter(User.is_active == True)
                 .order_by(ServiceProfile.is_available.desc(),
                           User.trust_score.desc())
                 .all())

    return render_template('services_browse.html',
                           category=cat_info,
                           providers=providers,
                           user=current_user)

@app.route('/services/register', methods=['GET', 'POST'])
def service_register():
    """Register or update a skilled professional profile"""
    selected_category = request.args.get('category') or request.form.get('trade_category', 'plumber')

    current_user = None
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()

    existing = None
    if current_user:
        existing = ServiceProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        trade_category    = (request.form.get('trade_category') or selected_category).strip()
        trade_subcategory = request.form.get('trade_subcategory', '').strip()
        bio               = request.form.get('bio', '').strip()
        skills_input      = request.form.get('skills', '').strip()
        rate_per_hour     = float(request.form.get('rate_per_hour') or 0)
        rate_per_visit    = float(request.form.get('rate_per_visit') or 0)
        pricing_type      = request.form.get('pricing_type', 'Per Hour').strip()
        min_charge        = float(request.form.get('min_charge') or 0)
        max_charge        = float(request.form.get('max_charge') or 0)
        experience_years  = int(request.form.get('experience_years') or 0)
        availability      = request.form.get('availability', '').strip()
        availability_type = request.form.get('availability_type', 'Full-time').strip()
        work_days_list    = request.form.getlist('work_days')
        work_days         = ','.join(work_days_list) if work_days_list else 'Mon,Tue,Wed,Thu,Fri,Sat'
        service_area      = request.form.get('service_area', '').strip() or 'Sangamner'
        certifications    = request.form.get('certifications', '').strip()
        is_available      = request.form.get('is_available') in ['on', 'true', '1', True]
        contact_phone     = request.form.get('contact', '').strip()
        name_input        = request.form.get('name', '').strip()
        email_input       = request.form.get('email', '').strip()

        # Handle profile photo upload
        profile_photo_name = None
        if 'profile_photo' in request.files:
            photo_file = request.files['profile_photo']
            if photo_file and photo_file.filename:
                import os, uuid
                ext = os.path.splitext(photo_file.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    photo_fname = f"sp_photo_{uuid.uuid4().hex[:8]}{ext}"
                    upload_dir = os.path.join(app.static_folder, 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    photo_file.save(os.path.join(upload_dir, photo_fname))
                    profile_photo_name = f"uploads/{photo_fname}"

        # If user is not logged in yet, create their account
        if not current_user:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            if not username:
                username = (name_input or trade_category).lower().replace(' ', '_') + '_' + str(random.randint(100, 999))
            if not password:
                password = 'password123'
            if not email_input:
                email_input = f"{username}@sangamner.org"

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                current_user = existing_user
                if contact_phone:
                    current_user.contact = contact_phone
                if name_input:
                    current_user.name = name_input
            else:
                current_user = User(
                    username=username,
                    password=generate_password_hash(password),
                    name=name_input or username,
                    contact=contact_phone,
                    location=service_area or 'Sangamner',
                    email=email_input,
                    skills=trade_category.upper(),
                    trust_score=85,
                    rating=5.0,
                    total_ratings=1,
                    is_active=True
                )
                db.session.add(current_user)
                db.session.commit()

            session['username'] = current_user.username
            existing = ServiceProfile.query.filter_by(user_id=current_user.id).first()
        else:
            if contact_phone:
                current_user.contact = contact_phone
            if name_input:
                current_user.name = name_input
            if email_input:
                current_user.email = email_input

        # Update User skills field
        if trade_category:
            user_skills = current_user.skills or ''
            if trade_category.upper() not in user_skills.upper():
                current_user.skills = f"{user_skills}, {trade_category.upper()}".strip(', ')

        # Build combined availability string
        avail_str = availability or f"{availability_type}, {work_days}"

        if existing:
            existing.trade_category    = trade_category
            existing.trade_subcategory = trade_subcategory
            existing.bio               = bio
            existing.skills            = skills_input
            existing.rate_per_hour     = rate_per_hour
            existing.rate_per_visit    = rate_per_visit
            existing.pricing_type      = pricing_type
            existing.min_charge        = min_charge
            existing.max_charge        = max_charge
            existing.experience_years  = experience_years
            existing.availability      = avail_str
            existing.availability_type = availability_type
            existing.work_days         = work_days
            existing.service_area      = service_area
            existing.certifications    = certifications
            existing.is_available      = is_available
            if profile_photo_name:
                existing.profile_photo = profile_photo_name
        else:
            sp = ServiceProfile(
                user_id           = current_user.id,
                trade_category    = trade_category,
                trade_subcategory = trade_subcategory,
                bio               = bio,
                skills            = skills_input,
                rate_per_hour     = rate_per_hour,
                rate_per_visit    = rate_per_visit,
                pricing_type      = pricing_type,
                min_charge        = min_charge,
                max_charge        = max_charge,
                experience_years  = experience_years,
                availability      = avail_str,
                availability_type = availability_type,
                work_days         = work_days,
                service_area      = service_area,
                certifications    = certifications,
                is_available      = is_available,
                profile_photo     = profile_photo_name,
            )
            db.session.add(sp)

        db.session.commit()
        return redirect(url_for('services_browse', category_key=trade_category))

    return render_template('service_register.html',
                           user=current_user,
                           categories=TRADE_CATEGORIES,
                           selected_category=selected_category,
                           existing=existing)

@app.route('/services/provider/<int:user_id>')
def service_provider_profile(user_id):
    """Public profile of a skilled service provider"""
    provider_user = User.query.get_or_404(user_id)
    service = ServiceProfile.query.filter_by(user_id=user_id).first_or_404()
    cat_info = get_category_info(service.trade_category)

    current_user = None
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()

    feedbacks = (Feedback.query
                 .filter_by(to_user_id=user_id)
                 .order_by(Feedback.created_at.desc())
                 .limit(10).all())

    return render_template('service_provider_profile.html',
                           provider=provider_user,
                           service=service,
                           category=cat_info,
                           feedbacks=feedbacks,
                           user=current_user)

# ============ INITIALIZE DATABASE ============

with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Startup DB init notice: {e}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("COMMUNITY CONNECT PLATFORM STARTING...")
    print("="*60)
    print("TEST MODE: OTP will be printed in console")
    print("Admin Login: username='admin', password='admin123'")
    print("="*60 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.run(debug=False, host='0.0.0.0', port=port)