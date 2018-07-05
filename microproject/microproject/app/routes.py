import requests
import hashlib
import redis
import psycopg2
from datetime import datetime

from flask import Response, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from app.models import User


cache = redis.StrictRedis(host='redis', port=6379, db=0)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/')
@app.route('/index')
def index():
    conn = psycopg2.connect(database="pgdb", user="pguser", password="pguser", host="dbpostgres", port="5432")

    return render_template('index.html', context=locals())


@app.route('/you-are')
def you_are():
    ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    user_agent = request.user_agent.string
    user_identification = ip_address + user_agent
    user_hash = hashlib.sha256(user_identification.encode()).hexdigest()

    return render_template('you_are.html', context=locals())


@app.route('/microproject-settings')
@login_required
def microproject_settings():
    return render_template('microproject_settings.html', context=locals())


@app.route('/monster/<name>')
def get_identicon(name):
    image = cache.get(name)
    if image is None:
        print('Cache is miss')
        r = requests.get('http://dnmonster:8080/monster/' + name + '?size=160')
        image = r.content
        cache.set(name, image)

    return Response(image, mimetype='image/png')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    return render_template('user.html', user=user, posts=posts)


@app.route('/avatar/<name>')
def get_avatar(name):
    image = cache.get(name)
    if image is None:
        print('Cache is miss')
        r = requests.get('http://dnmonster:8080/monster/123?size=160')
        image = r.content
        cache.set(name, image)

    return Response(image, mimetype='image/png')


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)