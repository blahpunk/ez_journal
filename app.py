# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

# Update the Flask constructor to set the static_url_path and then set APPLICATION_ROOT.
app = Flask(__name__, static_url_path='/static')  # Changed static_url_path
app.config['APPLICATION_ROOT'] = '/journal'
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add PrefixMiddleware to handle SCRIPT_NAME
class PrefixMiddleware:
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.prefix
        path_info = environ['PATH_INFO']
        if path_info.startswith(self.prefix):
            environ['PATH_INFO'] = path_info[len(self.prefix):]
        return self.app(environ, start_response)

app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/journal')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    pin_hash = db.Column(db.String(128))
    is_editor = db.Column(db.Boolean, default=False)

    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(pin)

    def check_pin(self, pin):
        return check_password_hash(self.pin_hash, pin)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Allow blank titles by using an empty string as the default.
    title = db.Column(db.String(200), nullable=False, default='')
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    viewers = db.relationship('User', secondary='entry_viewers', backref='entries')

entry_viewers = db.Table('entry_viewers',
    db.Column('entry_id', db.Integer, db.ForeignKey('entry.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Initialize database
with app.app_context():
    db.create_all()
    # Create Guest user if it doesn't exist
    if not User.query.get(0):
        guest = User(id=0, label='Guest', pin_hash=None, is_editor=False)
        db.session.add(guest)
        db.session.commit()
    # Create default admin if no users exist (other than Guest)
    if User.query.filter(User.id != 0).count() == 0:
        admin = User(label='Admin', is_editor=True)
        admin.set_pin('0000')
        db.session.add(admin)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Template filter
@app.template_filter('selectattr')
def selectattr_filter(items, attr, value):
    """Filter items by attribute matching value"""
    return [item for item in items if getattr(item, attr, None) == value]

# Routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if the user is currently locked out
    if 'lockout_until' in session:
        lockout_until = datetime.fromisoformat(session['lockout_until'])
        if datetime.now() < lockout_until:
            flash('Too many failed attempts. You are locked out until {}.'.format(lockout_until.strftime('%Y-%m-%d %H:%M:%S')))
            return render_template('login.html', attempts_remaining=0)
        else:
            # Lockout period has expired; clear the counters
            session.pop('lockout_until', None)
            session.pop('failed_attempts', None)

    if request.method == 'POST':
        pin = request.form.get('pin')
        users = User.query.filter(User.pin_hash.isnot(None)).all()
        for user in users:
            if user.check_pin(pin):
                # Successful login clears failure counters
                session.pop('failed_attempts', None)
                login_user(user)
                return redirect(url_for('index'))
        # No matching PIN found – increase failure counter
        failed_attempts = session.get('failed_attempts', 0) + 1
        session['failed_attempts'] = failed_attempts
        attempts_remaining = 3 - failed_attempts
        suggestion = None

        if failed_attempts >= 3:
            # Lock out the user for one hour
            lockout_until = datetime.now() + timedelta(hours=1)
            session['lockout_until'] = lockout_until.isoformat()
            flash('Too many failed attempts. You are locked out for 1 hour.')
            attempts_remaining = 0
        else:
            flash('Invalid PIN. {} attempt(s) remaining.'.format(attempts_remaining))
            # After the first failure, provide a suggestion
            if failed_attempts >= 1:
                suggestion = "Try your birthdate in MMDDYYYY format"
        return render_template('login.html', attempts_remaining=attempts_remaining, suggestion=suggestion)
    else:
        # GET request: calculate remaining attempts (default to 3)
        attempts_remaining = 3 - session.get('failed_attempts', 0)
        if attempts_remaining < 0:
            attempts_remaining = 0
        return render_template('login.html', attempts_remaining=attempts_remaining)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if current_user.is_authenticated and current_user.is_editor:
        entries_query = Entry.query.order_by(Entry.created_at.desc())
    elif current_user.is_authenticated:
        entries_query = Entry.query.join(entry_viewers).filter(
            (entry_viewers.c.user_id == current_user.id) | (entry_viewers.c.user_id == 0)
        ).distinct().order_by(Entry.created_at.desc())
    else:
        entries_query = Entry.query.join(entry_viewers).filter(
            entry_viewers.c.user_id == 0
        ).order_by(Entry.created_at.desc())

    entries = entries_query.paginate(page=page, per_page=per_page)
    return render_template('index.html', 
                           entries=entries,
                           recent_entries=entries.items)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_entry():
    if not current_user.is_editor:
        flash('Permission denied')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Capture the title exactly as provided (which may be blank)
        title = request.form.get('title', '')
        content = request.form.get('content')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        created_at = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
        viewer_ids = list(map(int, filter(None, request.form.get('viewer_ids', '0').split(','))))

        entry = Entry(
            title=title,
            content=content,
            created_at=created_at
        )
        for user_id in viewer_ids:
            user = User.query.get(user_id)
            if user:
                entry.viewers.append(user)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('index'))

    now = datetime.now()
    users = User.query.filter(User.id != 0).all()
    return render_template('editor.html', 
                           date=now.strftime('%Y-%m-%d'), 
                           time=now.strftime('%H:%M'),
                           users=users,
                           entry=None,
                           current_viewers=[0],
                           all_users=User.query.all())

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    if not current_user.is_editor:
        flash('Permission denied')
        return redirect(url_for('index'))

    entry = Entry.query.get_or_404(entry_id)
    if request.method == 'POST':
        # Capture the title exactly as provided (which may be blank)
        entry.title = request.form.get('title', '')
        entry.content = request.form.get('content')
        entry.created_at = datetime.strptime(
            f"{request.form.get('date')} {request.form.get('time')}", 
            '%Y-%m-%d %H:%M'
        )
        viewer_ids = list(map(int, filter(None, request.form.get('viewer_ids', '0').split(','))))
        entry.viewers = []
        for user_id in viewer_ids:
            user = User.query.get(user_id)
            if user:
                entry.viewers.append(user)
        db.session.commit()
        return redirect(url_for('index'))

    users = User.query.filter(User.id != 0).all()
    current_viewers = [user.id for user in entry.viewers]
    return render_template('editor.html',
                           entry=entry,
                           date=entry.created_at.strftime('%Y-%m-%d'),
                           time=entry.created_at.strftime('%H:%M'),
                           users=users,
                           current_viewers=current_viewers,
                           all_users=User.query.all())

@app.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    if not current_user.is_editor:
        flash('Permission denied')
        return redirect(url_for('index'))

    entry = Entry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/manage_pins', methods=['GET', 'POST'])
@login_required
def manage_pins():
    if not current_user.is_editor:
        flash('Permission denied')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            label = request.form.get('label')
            pin = request.form.get('pin')
            if not pin.isdigit():
                flash('PIN must be numeric')
                return redirect(url_for('manage_pins'))
            user = User(label=label, is_editor=False)
            user.set_pin(pin)
            db.session.add(user)
            db.session.commit()
            flash('PIN added')
        elif action == 'edit':
            user = User.query.get(request.form.get('user_id'))
            user.label = request.form.get('label')
            new_pin = request.form.get('pin')
            if new_pin:
                if not new_pin.isdigit():
                    flash('PIN must be numeric')
                    return redirect(url_for('manage_pins'))
                user.set_pin(new_pin)
            db.session.commit()
            flash('PIN updated')
        elif action == 'delete':
            user = User.query.get(request.form.get('user_id'))
            if user and user.id != 0 and user.id != current_user.id:
                db.session.delete(user)
                db.session.commit()
                flash('PIN deleted')
        return redirect(url_for('manage_pins'))

    pins = User.query.filter(User.id != 0).all()
    return render_template('manage_pins.html', pins=pins)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4242, debug=True)
