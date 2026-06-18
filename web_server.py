"""
Flask Web Server for Survivor Detection Website
Runs independently from the detection backend
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory, abort, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import json
import pkgutil
import importlib.util
from functools import wraps
from pathlib import Path

# Import database and models
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv(Path(__file__).resolve().parent / ".env")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(errors='replace')

if not hasattr(pkgutil, 'get_loader'):
    class _CompatLoader:
        path = None

        def get_filename(self, name):
            return __file__

    def _get_loader(name):
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            spec = None
        return spec.loader if spec and spec.loader else _CompatLoader()

    pkgutil.get_loader = _get_loader

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

PROJECT_ROOT = Path(__file__).resolve().parent
SURVIVORS_JSON = PROJECT_ROOT / 'reports' / 'survivors.json'
USERS_JSON = PROJECT_ROOT / 'reports' / 'users.json'
MISSING_PERSONS_JSON = PROJECT_ROOT / 'reports' / 'missing_persons.json'
SURVIVOR_IMAGE_DIR = PROJECT_ROOT / 'survivors'
MISSING_UPLOAD_DIR = PROJECT_ROOT / 'uploads' / 'missing_persons'
WEB_SERVER_PORT = int(os.getenv('WEB_SERVER_PORT', '8000'))
ALLOWED_UPLOAD_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}

CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to contribute'

# Database initialization
db = None
user_model = None
survivor_model = None

if os.getenv('STARTUP_MONGO', '0') == '1':
    try:
        from reports.connection import init_db
        from models.user import User
        from models.survivor import Survivor

        db = init_db()
        user_model = User(db)
        survivor_model = Survivor(db)
    except Exception as e:
        print(f"Warning: Database not connected on startup: {e}")


def ensure_database():
    """Connect to MongoDB, or fall back to local JSON files."""
    global db, user_model, survivor_model

    if user_model is not None and survivor_model is not None:
        return True

    if os.getenv('USE_MONGO', '1') != '1':
        user_model = JsonUserStore(USERS_JSON)
        if survivor_model is None:
            survivor_model = JsonSurvivorStore(SURVIVORS_JSON)
        return True

    try:
        from reports.connection import init_db
        from models.user import User
        from models.survivor import Survivor

        db = init_db()
        user_model = User(db)
        survivor_model = Survivor(db)
        return True
    except Exception as e:
        print(f"Warning: Database unavailable, using local JSON storage: {e}")
        user_model = JsonUserStore(USERS_JSON)
        survivor_model = JsonSurvivorStore(SURVIVORS_JSON)
        return True


class JsonSurvivorStore:
    """Read live detector output directly from reports/survivors.json."""

    def __init__(self, json_path):
        self.json_path = Path(json_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        try:
            with self.json_path.open('r', encoding='utf-8') as f:
                survivors = json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            print(f"Warning: Could not parse {self.json_path}: {exc}")
            return []

        normalized = []
        for survivor in survivors:
            item = dict(survivor)
            item.setdefault('identified', False)
            item.setdefault('identification', None)
            item.setdefault('verified', False)
            item.setdefault('confidence', 0.0)
            item.setdefault('posture', 'unknown')
            item.setdefault('direction', '0')
            item.setdefault('recovery_status', None)
            item.setdefault('likely_hospital', None)
            normalized.append(item)
        return normalized

    def _write(self, survivors):
        with self.json_path.open('w', encoding='utf-8') as f:
            json.dump(survivors, f, indent=4)

    def get_unidentified_survivors(self, limit=20):
        survivors = [s for s in self._read() if not s.get('identified', False)]
        return survivors[-limit:][::-1]

    def get_public_unidentified_survivors(self, limit=20):
        survivors = [
            s for s in self._read()
            if (
                not s.get('identified', False)
                and s.get('public_visible') is True
                and s.get('face_detected') is True
            )
        ]
        return survivors[-limit:][::-1]

    def get_identified_survivors(self, limit=100):
        survivors = [s for s in self._read() if s.get('identified', False)]
        return survivors[-limit:][::-1]

    def get_survivor_by_id(self, survivor_id):
        for survivor in self._read():
            if str(survivor.get('survivor_id')) == str(survivor_id):
                return survivor
        return None

    def get_stats(self):
        survivors = self._read()
        identified = sum(1 for s in survivors if s.get('identified', False))
        verified = sum(1 for s in survivors if s.get('verified', False))
        return {
            'total': len(survivors),
            'unidentified': len(survivors) - identified,
            'identified': identified,
            'verified': verified
        }

    def identify_survivor(self, survivor_id, identification_data, user_id):
        survivors = self._read()
        now = datetime.utcnow().isoformat()
        updated = False

        for survivor in survivors:
            if str(survivor.get('survivor_id')) == str(survivor_id):
                survivor['identified'] = True
                survivor['verified'] = False
                survivor['last_updated'] = now
                survivor['identification'] = {
                    'name': identification_data.get('name'),
                    'age': identification_data.get('age'),
                    'phone': identification_data.get('phone'),
                    'address': identification_data.get('address'),
                    'relationship': identification_data.get('relationship'),
                    'relationship_detail': identification_data.get('relationship_detail'),
                    'other_detail': identification_data.get('other_detail'),
                    'notes': identification_data.get('notes'),
                    'identified_by_user_id': str(user_id),
                    'identified_at': now,
                    'verified': False,
                    'admin_seen': False,
                    'details_seen_by_user': False
                }
                updated = True
                break

        if not updated:
            raise ValueError("Survivor not found")

        self._write(survivors)
        return True

    def verify_identification(self, survivor_id, recovery_status, hospital):
        survivors = self._read()
        now = datetime.utcnow().isoformat()
        updated = False

        for survivor in survivors:
            if str(survivor.get('survivor_id')) == str(survivor_id):
                survivor['verified'] = True
                survivor['recovery_status'] = recovery_status
                survivor['likely_hospital'] = hospital
                survivor['last_updated'] = now
                identification = survivor.get('identification') or {}
                identification['verified'] = True
                identification['verified_at'] = now
                identification['details_seen_by_user'] = False
                survivor['identification'] = identification
                updated = True
                break

        if not updated:
            raise ValueError("Survivor not found")

        self._write(survivors)
        return True

    def get_user_submissions(self, user_id, limit=100):
        submissions = []
        for survivor in self._read():
            identification = survivor.get('identification') or {}
            if str(identification.get('identified_by_user_id')) == str(user_id):
                submissions.append(survivor)
        return submissions[-limit:][::-1]

    def count_unseen_verified_for_user(self, user_id):
        count = 0
        for survivor in self._read():
            identification = survivor.get('identification') or {}
            if (
                survivor.get('verified')
                and str(identification.get('identified_by_user_id')) == str(user_id)
                and not identification.get('details_seen_by_user')
            ):
                count += 1
        return count

    def mark_verified_seen_for_user(self, user_id):
        survivors = self._read()
        changed = False
        for survivor in survivors:
            identification = survivor.get('identification') or {}
            if (
                survivor.get('verified')
                and str(identification.get('identified_by_user_id')) == str(user_id)
                and not identification.get('details_seen_by_user')
            ):
                identification['details_seen_by_user'] = True
                survivor['identification'] = identification
                changed = True

        if changed:
            self._write(survivors)

    def count_unseen_admin_submissions(self):
        count = 0
        for survivor in self._read():
            identification = survivor.get('identification') or {}
            if survivor.get('identified') and not identification.get('admin_seen'):
                count += 1
        return count

    def mark_admin_submissions_seen(self):
        survivors = self._read()
        changed = False
        for survivor in survivors:
            identification = survivor.get('identification') or {}
            if survivor.get('identified') and not identification.get('admin_seen'):
                identification['admin_seen'] = True
                survivor['identification'] = identification
                changed = True

        if changed:
            self._write(survivors)


class JsonUserStore:
    """Local user store used when MongoDB is unavailable."""

    def __init__(self, json_path):
        self.json_path = Path(json_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        try:
            with self.json_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            print(f"Warning: Could not parse {self.json_path}: {exc}")
            return []

    def _write(self, users):
        with self.json_path.open('w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)

    def create_user(self, username, email, password):
        users = self._read()

        if any(user.get('username') == username for user in users):
            raise ValueError("Username already exists")

        if any(user.get('email') == email for user in users):
            raise ValueError("Email already exists")

        user_id = str(int(datetime.utcnow().timestamp() * 1000000))
        user_data = {
            '_id': user_id,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow().isoformat(),
            'contributions': 0,
            'is_admin': len(users) == 0
        }
        users.append(user_data)
        self._write(users)
        return user_id

    def get_user_by_username(self, username):
        for user in self._read():
            if user.get('username') == username:
                return user
        return None

    def get_user_by_email(self, email):
        for user in self._read():
            if user.get('email') == email:
                return user
        return None

    def get_user_by_id(self, user_id):
        for user in self._read():
            if str(user.get('_id')) == str(user_id):
                return user
        return None

    def authenticate(self, email, password):
        user = self.get_user_by_email(email)
        if user and check_password_hash(user.get('password_hash', ''), password):
            return user
        return None

    def increment_contributions(self, user_id):
        users = self._read()
        for user in users:
            if str(user.get('_id')) == str(user_id):
                user['contributions'] = int(user.get('contributions', 0)) + 1
                break
        self._write(users)


if survivor_model is None:
    survivor_model = JsonSurvivorStore(SURVIVORS_JSON)
    print(f"Using JSON survivor data from {SURVIVORS_JSON}")


def survivor_image_url(survivor):
    image_path = survivor.get('image') if survivor else None
    if image_path:
        return url_for('survivor_image', image_path=str(image_path).replace('\\', '/'))
    return url_for('static', filename='images/placeholder.svg')


def allowed_upload(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS
    )


def read_missing_persons():
    try:
        with MISSING_PERSONS_JSON.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        print(f"Warning: Could not parse {MISSING_PERSONS_JSON}: {exc}")
        return []


def write_missing_persons(reports):
    MISSING_PERSONS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with MISSING_PERSONS_JSON.open('w', encoding='utf-8') as f:
        json.dump(reports, f, indent=4)


def save_missing_upload(file_storage, report_id, label):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_upload(file_storage.filename):
        raise ValueError("Only png, jpg, jpeg, webp, and pdf files are allowed")

    MISSING_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    stored_name = f"{report_id}_{label}.{extension}"
    destination = MISSING_UPLOAD_DIR / stored_name
    file_storage.save(destination)
    return f"uploads/missing_persons/{stored_name}"


def missing_file_url(file_path):
    if not file_path:
        return None
    return url_for('missing_upload_file', file_path=str(file_path).replace('\\', '/'))


def public_survivor(survivor):
    """Return browser-safe survivor data with coordinates removed."""
    safe = {
        'survivor_id': survivor.get('survivor_id'),
        'image_url': survivor_image_url(survivor),
        'identified': survivor.get('identified', False),
        'verified': survivor.get('verified', False),
    }

    created_at = survivor.get('created_at')
    if created_at:
        safe['created_at'] = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)

    return safe


app.jinja_env.globals.update(survivor_image_url=survivor_image_url)
app.jinja_env.globals.update(missing_file_url=missing_file_url)


def is_submitter(survivor):
    identification = survivor.get('identification') or {}
    submitted_by = identification.get('identified_by_user_id')
    return current_user.is_authenticated and submitted_by and str(submitted_by) == str(current_user.id)


def can_view_captured_details(survivor):
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, 'is_admin', False):
        return True
    return bool(survivor.get('verified') and is_submitter(survivor))


@app.context_processor
def notification_counts():
    counts = {
        'user_notification_count': 0,
        'admin_notification_count': 0
    }

    if not current_user.is_authenticated:
        return counts

    if not ensure_database():
        return counts

    try:
        if current_user.is_admin and hasattr(survivor_model, 'count_unseen_admin_submissions'):
            counts['admin_notification_count'] = survivor_model.count_unseen_admin_submissions()
        elif hasattr(survivor_model, 'count_unseen_verified_for_user'):
            counts['user_notification_count'] = survivor_model.count_unseen_verified_for_user(current_user.id)
    except Exception as exc:
        print(f"Notification count failed: {exc}")

    return counts


# User class for Flask-Login
class LoginUser(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.is_admin = user_data.get('is_admin', False)
        self.contributions = user_data.get('contributions', 0)


@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    if not ensure_database():
        return None
    user_data = user_model.get_user_by_id(user_id)
    if user_data:
        return LoginUser(user_data)
    return None


# ==================== ROUTES ====================

@app.route('/survivor-image/<path:image_path>')
def survivor_image(image_path):
    """Serve detector output images without moving them into static/."""
    relative_path = Path(image_path.replace('\\', '/'))
    if relative_path.is_absolute() or '..' in relative_path.parts:
        abort(404)

    full_path = (PROJECT_ROOT / relative_path).resolve()
    allowed_files = {
        (PROJECT_ROOT / 'unknown.jpg').resolve()
    }

    try:
        full_path.relative_to(SURVIVOR_IMAGE_DIR.resolve())
        allowed = True
    except ValueError:
        allowed = full_path in allowed_files

    if not allowed or not full_path.is_file():
        abort(404)

    return send_from_directory(full_path.parent, full_path.name)


@app.route('/missing-upload/<path:file_path>')
@login_required
def missing_upload_file(file_path):
    """Serve missing-person uploads to logged-in users only."""
    relative_path = Path(file_path.replace('\\', '/'))
    if relative_path.is_absolute() or '..' in relative_path.parts:
        abort(404)

    full_path = (PROJECT_ROOT / relative_path).resolve()

    try:
        full_path.relative_to(MISSING_UPLOAD_DIR.resolve())
    except ValueError:
        abort(404)

    if not full_path.is_file():
        abort(404)

    return send_from_directory(full_path.parent, full_path.name)


@app.route('/')
def home():
    """Home page - Display unidentified survivors"""
    try:
        if hasattr(survivor_model, 'get_public_unidentified_survivors'):
            unidentified = survivor_model.get_public_unidentified_survivors(limit=12)
        else:
            unidentified = survivor_model.get_unidentified_survivors(limit=12)
        stats = survivor_model.get_stats()
        return render_template('home.html', 
                             survivors=unidentified,
                             stats=stats,
                             is_authenticated=current_user.is_authenticated)
    except Exception as e:
        print(f"Error loading home: {e}")
        return render_template('error.html', message='Failed to load survivors'), 500


@app.route('/survivor/<survivor_id>')
def survivor_detail(survivor_id):
    """View details of a specific survivor"""
    try:
        survivor = survivor_model.get_survivor_by_id(survivor_id)
        if not survivor:
            return render_template('error.html', message='Survivor not found'), 404
        
        return render_template(
            'survivor_detail.html',
            survivor=survivor,
            can_view_details=can_view_captured_details(survivor),
            is_submitter=is_submitter(survivor)
        )
    except Exception as e:
        print(f"Error loading survivor detail: {e}")
        return render_template('error.html', message='Failed to load survivor'), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        if not ensure_database():
            return jsonify({'success': False, 'message': 'Database unavailable'}), 500
        
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            return render_template('register.html', 
                                 error='All fields are required')
        
        if len(username) < 3:
            return render_template('register.html', 
                                 error='Name must be at least 3 characters')
        
        if len(password) < 6:
            return render_template('register.html', 
                                 error='Password must be at least 6 characters')
        
        if password != confirm_password:
            return render_template('register.html', 
                                 error='Passwords do not match')
        
        try:
            user_model.create_user(username, email, password)
            return render_template('register.html', 
                                 success='Registration successful! Please log in.')
        except ValueError as e:
            return render_template('register.html', error=str(e))
        except Exception as e:
            print(f"Registration error: {e}")
            return render_template('register.html', 
                                 error='Registration failed. Please try again.')
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        if not ensure_database():
            return jsonify({'success': False, 'message': 'Database unavailable'}), 500
        
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            return render_template('login.html', error='Email and password required')
        
        user_data = user_model.authenticate(email, password)
        if user_data:
            user = LoginUser(user_data)
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('home'))


@app.route('/identify/<survivor_id>', methods=['GET', 'POST'])
@login_required
def identify_survivor(survivor_id):
    """Identify a survivor (submit information)"""
    if not ensure_database():
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    survivor = survivor_model.get_survivor_by_id(survivor_id)
    if not survivor:
        return render_template('error.html', message='Survivor not found'), 404
    
    if survivor.get('identified') and not is_submitter(survivor) and not current_user.is_admin:
        return render_template('error.html',
                             message='Information for this survivor is already under admin review'), 400
    
    if request.method == 'POST':
        identification_data = {
            'name': request.form.get('name', '').strip(),
            'age': request.form.get('age', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'address': request.form.get('address', '').strip(),
            'relationship': request.form.get('relationship', '').strip(),
            'relationship_detail': request.form.get('relationship_detail', '').strip(),
            'other_detail': request.form.get('other_detail', '').strip(),
            'notes': request.form.get('notes', '').strip()
        }
        
        # Validation
        required = [
            identification_data['name'],
            identification_data['age'],
            identification_data['phone'],
            identification_data['address'],
            identification_data['relationship']
        ]
        if not all(required):
            return render_template('identify.html', 
                                 survivor=survivor,
                                 error='Name, age, phone, address, and relationship are required')

        if identification_data['relationship'] == 'blood_related' and not identification_data['relationship_detail']:
            return render_template('identify.html',
                                 survivor=survivor,
                                 error='Please explain how you are blood related')

        if identification_data['relationship'] == 'other' and not identification_data['other_detail']:
            return render_template('identify.html',
                                 survivor=survivor,
                                 error='Please explain how you know the survivor')
        
        try:
            survivor_model.identify_survivor(survivor_id, identification_data, current_user.id)
            user_model.increment_contributions(current_user.id)
            return render_template('identify.html', 
                                 survivor=survivor,
                                 success='Thank you. Your details were submitted for administrator verification.')
        except Exception as e:
            print(f"Identification error: {e}")
            return render_template('identify.html', 
                                 survivor=survivor,
                                 error='Failed to submit information. Please try again.')
    
    return render_template('identify.html', survivor=survivor)


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    if not ensure_database():
        return render_template('error.html', message='Database unavailable'), 500
    
    try:
        user_data = user_model.get_user_by_id(current_user.id)
        stats = survivor_model.get_stats()
        submissions = []
        if hasattr(survivor_model, 'get_user_submissions'):
            submissions = survivor_model.get_user_submissions(current_user.id)
        if hasattr(survivor_model, 'mark_verified_seen_for_user'):
            survivor_model.mark_verified_seen_for_user(current_user.id)
        missing_reports = [
            report for report in read_missing_persons()
            if str(report.get('submitted_by_user_id')) == str(current_user.id)
        ][::-1]
        
        return render_template('dashboard.html', 
                             user=user_data,
                             stats=stats,
                             submissions=submissions,
                             missing_reports=missing_reports)
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('error.html', message='Failed to load dashboard'), 500


@app.route('/missing/new', methods=['GET', 'POST'])
@login_required
def report_missing_person():
    """Let normal users submit details of a missing person."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        phone = request.form.get('phone', '').strip()
        last_met = request.form.get('last_met', '').strip()
        disaster_proof_text = request.form.get('disaster_proof_text', '').strip()
        identification_marks = request.form.get('identification_marks', '').strip()
        accessories = request.form.get('accessories', '').strip()
        visible_marks = request.form.get('visible_marks', '').strip()
        dress_color = request.form.get('dress_color', '').strip()

        if not all([
            name,
            age,
            phone,
            last_met,
            disaster_proof_text,
            identification_marks,
            accessories,
            visible_marks,
            dress_color
        ]):
            return render_template(
                'missing_person_form.html',
                error='All required missing-person details and identification clues must be filled'
            )

        try:
            age_value = int(age)
        except ValueError:
            return render_template('missing_person_form.html', error='Age must be a number')

        if age_value < 0 or age_value > 120:
            return render_template('missing_person_form.html', error='Age must be between 0 and 120')

        reports = read_missing_persons()
        report_id = f"missing_{int(datetime.utcnow().timestamp() * 1000000)}"

        try:
            photo_path = save_missing_upload(request.files.get('photo'), report_id, 'photo')
            proof_path = save_missing_upload(request.files.get('proof_file'), report_id, 'proof')
        except ValueError as exc:
            return render_template('missing_person_form.html', error=str(exc))

        report = {
            'report_id': report_id,
            'submitted_by_user_id': str(current_user.id),
            'submitted_by_email': current_user.email,
            'submitted_by_name': current_user.username,
            'name': name,
            'age': age_value,
            'phone': phone,
            'last_met': last_met,
            'disaster_proof_text': disaster_proof_text,
            'identification_marks': identification_marks,
            'accessories': accessories,
            'visible_marks': visible_marks,
            'dress_color': dress_color,
            'photo_path': photo_path,
            'proof_file_path': proof_path,
            'status': 'submitted',
            'created_at': datetime.utcnow().isoformat()
        }

        reports.append(report)
        write_missing_persons(reports)
        flash('Missing person report submitted successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('missing_person_form.html')


@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if not current_user.is_admin:
        return render_template('error.html', message='Access denied'), 403
    
    if not ensure_database():
        return render_template('error.html', message='Database unavailable'), 500
    
    try:
        stats = survivor_model.get_stats()
        identified = survivor_model.get_identified_survivors(limit=50)
        unidentified = survivor_model.get_unidentified_survivors(limit=50)
        if hasattr(survivor_model, 'mark_admin_submissions_seen'):
            survivor_model.mark_admin_submissions_seen()
        
        return render_template('admin.html',
                             stats=stats,
                             identified_survivors=identified,
                             unidentified_survivors=unidentified)
    except Exception as e:
        print(f"Admin dashboard error: {e}")
        return render_template('error.html', message='Failed to load admin panel'), 500


@app.route('/admin/verify/<survivor_id>', methods=['POST'])
@login_required
def verify_survivor(survivor_id):
    if not current_user.is_admin:
        return render_template('error.html', message='Access denied'), 403

    if not ensure_database():
        return render_template('error.html', message='Database unavailable'), 500

    recovery_status = request.form.get('recovery_status', '').strip()
    hospital = request.form.get('hospital', '').strip()

    if not recovery_status:
        return render_template('error.html', message='Recovery status is required'), 400

    if recovery_status == 'recovered' and not hospital:
        return render_template('error.html', message='Hospital is required when survivor is recovered'), 400

    try:
        survivor_model.verify_identification(survivor_id, recovery_status, hospital)
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        print(f"Verification error: {e}")
        return render_template('error.html', message='Failed to verify survivor'), 500


# ==================== API ENDPOINTS ====================

@app.route('/api/survivors/unidentified')
def api_unidentified_survivors():
    """API endpoint to get unidentified survivors (JSON)"""
    try:
        limit = request.args.get('limit', 20, type=int)
        if hasattr(survivor_model, 'get_public_unidentified_survivors'):
            survivors = survivor_model.get_public_unidentified_survivors(limit=min(limit, 100))
        else:
            survivors = survivor_model.get_unidentified_survivors(limit=min(limit, 100))
        return jsonify({
            'success': True,
            'survivors': [public_survivor(survivor) for survivor in survivors]
        })
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint to get statistics"""
    try:
        stats = survivor_model.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='Page not found'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('error.html', message='Internal server error'), 500


# ==================== CLI COMMANDS ====================

@app.cli.command()
def migrate_survivors_json():
    """Migrate survivors from JSON file to MongoDB"""
    if not ensure_database():
        print("Database connection failed")
        return
    
    try:
        json_file = os.path.join(os.path.dirname(__file__), 'reports', 'survivors.json')
        if not os.path.exists(json_file):
            print(f"File not found: {json_file}")
            return
        
        with open(json_file, 'r') as f:
            survivors = json.load(f)
        
        count = survivor_model.bulk_import_from_json(survivors)
        print(f"✓ Successfully migrated {count} survivors to MongoDB")
    except Exception as e:
        print(f"✗ Migration failed: {e}")


@app.cli.command()
def create_admin_user():
    """Create an admin user"""
    if not ensure_database():
        print("Database connection failed")
        return
    
    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()
    password = input("Enter admin password: ").strip()
    
    try:
        from bson.objectid import ObjectId

        admin_id = user_model.create_user(username, email, password)
        # Make user admin
        db['users'].update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {'is_admin': True}}
        )
        print(f"✓ Admin user '{username}' created successfully")
    except Exception as e:
        print(f"✗ Failed to create admin user: {e}")


# ==================== MAIN ====================

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    print("🚀 Starting Flask Web Server...")
    print("📍 Running on http://localhost:5000")
    print("📝 Visit http://localhost:5000 to access the website")
    
    print(f"Actual web URL: http://localhost:{WEB_SERVER_PORT}")
    app.run(debug=False, host='0.0.0.0', port=WEB_SERVER_PORT, use_reloader=False)
