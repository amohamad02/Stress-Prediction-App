from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dateutil import parser
import pickle

app = Flask(__name__, template_folder='template', static_url_path='/static')
app.secret_key = 'secret'

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Flask-SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load prediction model
model = pickle.load(open('model.pkl', 'rb'))


class UserAuth(UserMixin):
    def __init__(self, id):
        self.id = id


def validate_user(username, password):
    if username == "admin" and password == "secret":
        return UserAuth(1)
    return None


@login_manager.user_loader
def load_user(user_id):
    return UserAuth(user_id)


class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60))
    last_name = db.Column(db.String(60))


class HRV_Stat(db.Model):
    __tablename__ = "hrv_stat"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("user", uselist=False))

    mean_rr = db.Column(db.Float)
    pNN50 = db.Column(db.Float)
    RMSSD = db.Column(db.Float)
    HR = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.utcnow)


@app.route('/', methods=['GET', 'POST'], endpoint="login")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = validate_user(username, password)
        if user is not None:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/home', methods=['GET'], endpoint='home')
@login_required
def home():
    users = User.query.all()
    return render_template("index.html", users=users)

@app.route('/robots', methods=['GET'], endpoint='robots')
@login_required
def robots():
    users = User.query.all()
    return render_template("robots.html", users=users)


@app.route('/dashboard', methods=['GET'], endpoint='dashboard')
@login_required
def dashboard():
    users = User.query.all()
    model = pickle.load(open('model.pkl', 'rb'))
    users_with_status = []
    
    for user in users:
        user_data = HRV_Stat.query.filter_by(user_id=user.id).order_by(HRV_Stat.date.desc()).all()
        if len(user_data) > 0:
            latest_hrv_record = user_data[0] # extract the latest HRV record for the user
            prediction = model.predict([[latest_hrv_record.mean_rr, latest_hrv_record.pNN50, latest_hrv_record.RMSSD, latest_hrv_record.HR]])
            is_stressed = prediction[0] == 1
            users_with_status.append((user, is_stressed))
        else:
            users_with_status.append((user, None))

    return render_template("dashboard.html", users=users_with_status)


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        user_id = request.form['id']
        first_name = request.form['first_name']
        last_name = request.form['last_name']

        user = User(id = user_id, first_name=first_name, last_name=last_name)
        db.session.add(user)
        db.session.commit()

        flash('User added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_user.html')

@app.route('/add_hrv/<int:user_id>', methods=['GET', 'POST'])
def add_hrv(user_id):
    if request.method == 'POST':
        
        date_str = request.form['date']
        date_obj = parser.parse(date_str).date()
        mean_rr = request.form['mean_rr']
        pNN50 = request.form['pNN50']
        RMSSD = request.form['RMSSD']
        HR = request.form['HR']

        hrv_stat = HRV_Stat(date=date_obj, mean_rr=mean_rr, pNN50=pNN50, RMSSD=RMSSD, HR=HR, user_id=user_id)
        db.session.add(hrv_stat)
        db.session.commit()

        flash('HRV Stat added successfully!', 'success')
        return redirect(url_for('user', user_id=user_id))

    return render_template('user.html', user_id=user_id)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    MEAN_RR = float(request.form["MEAN_RR"])
    PNN50 = float(request.form["pNN50"])
    RMSSD = float(request.form["RMSSD"])
    HR = float(request.form["HR"])
    prediction = model.predict([[MEAN_RR, PNN50, RMSSD, HR]])
    output = prediction[0]
    if output == 1:
        return render_template('index.html', prediction_text='This Person is Stressed')
    else:
        return render_template('index.html', prediction_text='This Person is Not Stressed')

@app.route('/predict2', methods=['POST'])
@login_required
def predict2():
    HRV_STAT = HRV_Stat.query.filter_by(id=int(request.form["HRV Stat ID"])).first()
    MEAN_RR = HRV_STAT.mean_rr
    PNN50 = HRV_STAT.pNN50
    RMSSD = HRV_STAT.RMSSD
    HR = HRV_STAT.HR
    prediction = model.predict([[MEAN_RR, PNN50, RMSSD, HR]])
    output = prediction[0]
    if output == 1:
        return render_template('index.html', prediction_text2='This Person is Stressed')
    else:
        return render_template('index.html', prediction_text2='This Person is Not Stressed')

@app.route('/user/<int:user_id>')
def user(user_id):
    user_data = HRV_Stat.query.filter_by(user_id=user_id).order_by(HRV_Stat.date.desc()).all()
    user = User.query.get(user_id)
    model = pickle.load(open('model.pkl', 'rb'))

    if request.method == 'POST':
        mean_rr = request.form['mean_rr']
        pNN50 = request.form['pNN50']
        RMSSD = request.form['RMSSD']
        HR = request.form['HR']
        TP = request.form['TP']
        VLF = request.form['VLF']

        hrv_stat = HRV_Stat(mean_rr=mean_rr, pNN50=pNN50, RMSSD=RMSSD, HR=HR, TP=TP, VLF=VLF, user_id=user_id)
        db.session.add(hrv_stat)
        db.session.commit()

        

    if len(user_data) > 0:
        latest_hrv_record = user_data[0] # extract the latest HRV record for the user
        prediction = model.predict([[latest_hrv_record.mean_rr, latest_hrv_record.pNN50, latest_hrv_record.RMSSD, latest_hrv_record.HR]])
        is_stressed = prediction[0] == 1
        return render_template('user.html', user=user, user_data=user_data, model=model, is_stressed=is_stressed)
    else:
        return render_template('user.html', user=user, user_data=user_data, model=model)



if __name__ == "__main__":
    app.run(debug=True)