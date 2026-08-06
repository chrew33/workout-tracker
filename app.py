from flask import Flask, render_template, request, redirect, url_for, flash, abort
from extensions import db
from models import User, WorkoutPlan, Exercise
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'password'

# connect this app to the database (in extensions.py)
db.init_app(app)   
    
login_manager = LoginManager()
login_manager.login_view = 'login'      # redirect user to here if user not logged in (name of the function)
login_manager.init_app(app)             # connect the login manager to this app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()


@app.route('/', methods=['GET', 'POST'])
def login():
    
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        
        username = request.form['username']
        password = request.form['password']
        
        data = {"username": username,
                "password": password}
        
        response = requests.post("http://localhost:5555/login",json=data)

        if response.status_code == 200:
            user = User.query.filter_by(username=username).first()
            login_user(user)
            return redirect(url_for('home'))
        
        elif response.status_code == 401:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # checks if register is possible by HTTP request to login microservice
        data = {
            "username":username,
            "password":password
        }
        
        # This uses the login microservice!!!!
        response = requests.post("http://localhost:5555/register",json=data)
        
        if response.status_code == 409:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('register'))

        elif response.status_code == 201:
            new_user = User(username=username, password=password)

            db.session.add(new_user)
            db.session.commit()

            flash('Account created! Please log in.')
            return redirect(url_for('login'))

        else:
            flash(f'Something went wrong please try again. Error code: {response.status_code}')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/home')
@login_required
def home():
    plans = current_user.workout_plans
    return render_template('home.html', plans=plans)


@app.route('/plan/<int:plan_id>')
@login_required
def view_plan(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)

    # check if plan is actually the user's
    if plan.user_id != current_user.id:
        abort(403)

    return render_template('view_plan.html', plan=plan)


@app.route('/plan/new', methods=['GET', 'POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        name = request.form["name"]

        if not name:
            flash('Please enter a plan name.')
            return redirect(url_for('create_template'))

        new_plan = WorkoutPlan(name=name, user_id=current_user.id)
        
        db.session.add(new_plan)
        db.session.commit()

        return redirect(url_for('edit_plan', plan_id=new_plan.id))

    return render_template('create_plan.html')

@app.route('/plan/<int:plan_id>/edit')
@login_required
def edit_plan(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)

    # check if plan is actually the user's
    if plan.user_id != current_user.id:
        abort(403)

    return render_template('edit_plan.html', plan=plan)


@app.route('/plan/<int:plan_id>/add_exercise', methods=['POST'])
@login_required
def add_exercise(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)

    if plan.user_id != current_user.id:
        abort(403)

    name = request.form.get('exercise_name')
    weights = request.form.get('exercise_weights')
    sets = request.form.get('exercise_sets')
    reps = request.form.get('exercise_reps')

    if name and sets and reps:
        exercise = Exercise(name=name, weights=float(weights) ,sets=int(sets), reps=int(reps), workout_plan_id=plan.id)
        db.session.add(exercise)
        db.session.commit()
    else:
        flash('Please fill in exercise, weights, sets, and reps.')

    return redirect(url_for('edit_plan', plan_id=plan.id))

@app.route('/plan/<int:exercise_id>/delete', methods=['POST'])
@login_required
def delete_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)

    plan = WorkoutPlan.query.get_or_404(exercise.workout_plan_id)

    if plan.user_id != current_user.id:
        abort(403)
        
    plan_id = plan.id

    db.session.delete(exercise)
    db.session.commit()

    return redirect(url_for('edit_plan', plan_id=plan_id))

@app.route('/plan/<int:plan_id>/delete_plan', methods=['POST'])
@login_required
def delete_plan(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)

    if plan.user_id != current_user.id:
        abort(403)

    db.session.delete(plan)
    db.session.commit()

    flash('Plan deleted.')
    return redirect(url_for('home'))

@app.route('/analyze', methods=['GET'])
@login_required
def analyze_user():
    plans = current_user.workout_plans
    for plan in plans:
        total_volume = 0
        for exercise in plan.exercises:
            # this portion is where I can use math microservice
            total_volume = exercise.weights * exercise.sets * exercise.reps
        plan.volume = int(total_volume)
        db.session.commit()
    
    return render_template('analyze.html', plans=plans)


@app.route('/help')
@login_required
def help():
    return render_template('help.html')

if __name__ == '__main__':
    app.run(port=5000, debug=True)