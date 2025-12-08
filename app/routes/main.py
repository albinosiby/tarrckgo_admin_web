from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template('index.html')

@main_bp.route('/settings')
def settings():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('settings.html')

@main_bp.route('/tracking')
def tracking():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('tracking.html')

@main_bp.route('/attendance')
def attendance():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('attendance.html')
