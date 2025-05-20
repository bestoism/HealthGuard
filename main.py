from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import secrets
import os
from werkzeug.utils import secure_filename
from sqlalchemy import text 
from sqlalchemy import create_engine
from sqlalchemy import and_
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

# Konfigurasi MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://root:@localhost/health_guard')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'Health Guard <default@example.com>')
mail = Mail(app)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Nama tabel di MySQL
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Data profil
    profile_pic = db.Column(db.String(255))
    full_name = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    blood_type = db.Column(db.String(5))
    
    # Reset password
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Model untuk pencatatan kesehatan
class HealthRecord(db.Model):
    __tablename__ = 'health_records'  # Nama tabel di MySQL
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Data vital
    blood_pressure_systolic = db.Column(db.Integer) 
    blood_pressure_diastolic = db.Column(db.Integer)  
    heart_rate = db.Column(db.Integer)  
    temperature = db.Column(db.Float)  
    blood_sugar = db.Column(db.Float) 
    weight = db.Column(db.Float)  
    
    # Catatan tambahan
    symptoms = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<HealthRecord {self.record_date}>'

class MedicineReminder(db.Model):
    __tablename__ = 'medicine_reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medicine_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)  
    time = db.Column(db.String(50), nullable=False) 
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MedicineReminder {self.medicine_name}>'

# Data nutrisi makanan (per 100 gram)
FOOD_NUTRITION = {
    'nasi': {
        'name': 'Nasi Putih',
        'calories': 130,
        'protein': 2.7,
        'carbs': 28,
        'unit': 'centong'
    },
    'ayam_goreng': {
        'name': 'Ayam Goreng',
        'calories': 260,
        'protein': 25,
        'carbs': 9,
        'unit': 'potong'
    },
    'telur_goreng': {
        'name': 'Telur Goreng',
        'calories': 155,
        'protein': 13,
        'carbs': 1,
        'unit': 'butir'
    },
    'tempe_goreng': {
        'name': 'Tempe Goreng',
        'calories': 175,
        'protein': 15,
        'carbs': 7,
        'unit': 'potong'
    },
    'tahu_goreng': {
        'name': 'Tahu Goreng',
        'calories': 115,
        'protein': 9,
        'carbs': 3,
        'unit': 'potong'
    },
    'sayur_bayam': {
        'name': 'Sayur Bayam',
        'calories': 23,
        'protein': 2.3,
        'carbs': 3.8,
        'unit': 'mangkok'
    },
    'sayur_kangkung': {
        'name': 'Sayur Kangkung',
        'calories': 19,
        'protein': 2.1,
        'carbs': 3.2,
        'unit': 'mangkok'
    },
    'pisang': {
        'name': 'Pisang',
        'calories': 89,
        'protein': 1.1,
        'carbs': 23,
        'unit': 'buah'
    },
    'apel': {
        'name': 'Apel',
        'calories': 52,
        'protein': 0.3,
        'carbs': 14,
        'unit': 'buah'
    },
    'jeruk': {
        'name': 'Jeruk',
        'calories': 47,
        'protein': 0.9,
        'carbs': 12,
        'unit': 'buah'
    }
}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route untuk halaman utama
@app.route('/')
def index():
    return render_template('index.html')

# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah.', 'error')
    
    return render_template('login.html')

# Route untuk registrasi dengan data tambahan
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        birth_date_str = request.form.get('birth_date')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validasi data yang sudah ada
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan!', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email sudah digunakan!', 'error')
            return redirect(url_for('register'))
        
        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date() if birth_date_str else None
            
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                full_name=full_name,
                birth_date=birth_date,
                gender=gender,
                phone=phone,
                address=address
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Terjadi kesalahan saat registrasi. Silakan coba lagi.', 'error')
            print(e)  
            
    return render_template('register.html')

# Route untuk dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Definisikan kategori dan menu-menu yang tersedia
    categories = {
        'vital_signs': {
            'title': 'Pemeriksaan Vital',
            'icon': 'bi-heart-pulse',
            'color': 'danger',
            'menus': [
                {
                    'name': 'Cek Kesehatan',
                    'description': 'Pemeriksaan kesehatan dasar dan tanda vital',
                    'icon': 'bi-clipboard2-pulse',
                    'url': 'health_check_form',
                    'color': 'danger'
                },
                {
                    'name': 'Monitor Tekanan Darah',
                    'description': 'Pantau tekanan darah Anda',
                    'icon': 'bi-activity',
                    'url': 'blood_pressure',
                    'color': 'danger'
                }
            ]
        },
        'body_metrics': {
            'title': 'Pengukuran Tubuh',
            'icon': 'bi-rulers',
            'color': 'primary',
            'menus': [
                {
                    'name': 'Kalkulator BMI',
                    'description': 'Hitung Indeks Massa Tubuh',
                    'icon': 'bi-calculator',
                    'url': 'bmi_calculator',
                    'color': 'primary'
                },
                {
                    'name': 'Analisis Tinggi Badan',
                    'description': 'Analisis tinggi badan ideal',
                    'icon': 'bi-arrow-up-right',
                    'url': 'height_index',
                    'color': 'primary'
                }
            ]
        },
        'lifestyle': {
            'title': 'Gaya Hidup Sehat',
            'icon': 'bi-flower1',
            'color': 'success',
            'menus': [
                {
                    'name': 'Aktivitas Fisik',
                    'description': 'Catat dan hitung kalori dari aktivitas fisik',
                    'icon': 'bi-bicycle',
                    'url': 'physical_activity',
                    'color': 'success'
                },
                {
                    'name': 'Nutrisi Harian',
                    'description': 'Pantau asupan nutrisi harian Anda',
                    'icon': 'bi-egg-fried',
                    'url': 'nutrition',
                    'color': 'success'
                }
            ]
        },
        'medical': {
            'title': 'Rekam Medis',
            'icon': 'bi-journal-medical',
            'color': 'info',
            'menus': [
                {
                    'name': 'Riwayat Pemeriksaan',
                    'description': 'Lihat riwayat pemeriksaan kesehatan',
                    'icon': 'bi-clock-history',
                    'url': 'health_records',
                    'color': 'info'
                },
                {
                    'name': 'Pengingat Obat',
                    'description': 'Atur pengingat untuk konsumsi obat',
                    'icon': 'bi-bell',
                    'url': 'medicine_reminder',
                    'color': 'info'
                }
            ]
        }
    }
    
    return render_template('dashboard.html', categories=categories)

# Route untuk logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Tambahkan route baru
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        print(f"Mencoba reset password untuk email: {email}")
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                # Generate token
                token = secrets.token_urlsafe(32)
                user.reset_token = token
                user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
                db.session.commit()
                
                # Siapkan email
                reset_url = url_for('reset_password', token=token, _external=True)
                msg = Message('Reset Password Health Guard',
                            sender=app.config['MAIL_DEFAULT_SENDER'],
                            recipients=[email])
                msg.body = f'''Untuk mereset password Anda, klik link berikut:
{reset_url}

Link ini akan kadaluarsa dalam 1 jam.

Jika Anda tidak meminta reset password, abaikan email ini.
'''
                print(f"Mencoba mengirim email ke: {email}") 
                print(f"Reset URL: {reset_url}")  
                
                # Kirim email
                mail.send(msg)
                print("Email berhasil dikirim!")  
                
                flash('Link reset password telah dikirim ke email Anda.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Error saat mengirim email: {str(e)}")  
                flash('Terjadi kesalahan saat mengirim email.', 'error')
        else:
            print(f"Email tidak ditemukan: {email}")  
            flash('Email tidak ditemukan.', 'error')
            
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if user is None or user.reset_token_expiry < datetime.utcnow():
        flash('Link reset password tidak valid atau sudah kadaluarsa.', 'error')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Password tidak cocok.', 'error')
            return redirect(url_for('reset_password', token=token))
            
        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Password berhasil direset! Silakan login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html')

@app.route('/nutrition', methods=['GET', 'POST'])
@login_required
def nutrition():
    if request.method == 'POST':
        try:
            meal_type = request.form.get('meal_type')
            food_items = request.form.getlist('food_items[]')
            portions = request.form.getlist('portions[]')
            
            if not food_items or not portions:
                flash('Mohon pilih makanan dan jumlah porsi', 'error')
                return redirect(url_for('nutrition'))
            
            total_calories = 0
            total_protein = 0
            total_carbs = 0
            foods_detail = []
            
            for food, portion in zip(food_items, portions):
                if food in FOOD_NUTRITION:
                    try:
                        portion_float = float(portion)
                        if portion_float <= 0:
                            raise ValueError("Porsi harus lebih dari 0")
                            
                        food_info = FOOD_NUTRITION[food]
                        calories = food_info['calories'] * portion_float
                        protein = food_info['protein'] * portion_float
                        carbs = food_info['carbs'] * portion_float
                        
                        total_calories += calories
                        total_protein += protein
                        total_carbs += carbs
                        
                        foods_detail.append({
                            'name': food_info['name'],
                            'portion': portion_float,
                            'unit': food_info['unit'],
                            'calories': round(calories, 1),
                            'protein': round(protein, 1),
                            'carbs': round(carbs, 1)
                        })
                    except ValueError:
                        flash(f'Porsi untuk {FOOD_NUTRITION[food]["name"]} harus berupa angka positif', 'error')
                        return redirect(url_for('nutrition'))
            
            # Analisis nutrisi
            calorie_status = ""
            if total_calories < 500:
                calorie_status = "Rendah kalori"
            elif total_calories <= 800:
                calorie_status = "Kalori seimbang"
            else:
                calorie_status = "Tinggi kalori"
            
            protein_status = ""
            if total_protein < 15:
                protein_status = "Rendah protein"
            elif total_protein <= 30:
                protein_status = "Protein seimbang"
            else:
                protein_status = "Tinggi protein"
            
            carbs_status = ""
            if total_carbs < 50:
                carbs_status = "Rendah karbohidrat"
            elif total_carbs <= 100:
                carbs_status = "Karbohidrat seimbang"
            else:
                carbs_status = "Tinggi karbohidrat"
            
            return render_template('nutrition_result.html',
                                meal_type=meal_type,
                                foods=foods_detail,
                                total_calories=round(total_calories, 1),
                                total_protein=round(total_protein, 1),
                                total_carbs=round(total_carbs, 1),
                                calorie_status=calorie_status,
                                protein_status=protein_status,
                                carbs_status=carbs_status)
                                
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            return redirect(url_for('nutrition'))
    
    # Kirim daftar makanan yang tersedia ke template
    available_foods = [(key, value['name'], value['unit']) for key, value in FOOD_NUTRITION.items()]
    return render_template('nutrition.html', foods=available_foods)

@app.route('/health-check', methods=['GET', 'POST'])
@login_required
def health_check_form():
    if request.method == 'POST':
        try:
            # Mengambil data vital signs
            systolic = request.form.get('systolic')
            diastolic = request.form.get('diastolic')
            heart_rate = request.form.get('heart_rate')
            temperature = request.form.get('temperature')
            blood_sugar = request.form.get('blood_sugar')
            weight = request.form.get('weight')
            
            # Validasi data vital tidak boleh kosong
            if not all([systolic, diastolic, heart_rate, temperature, blood_sugar, weight]):
                missing_fields = []
                if not systolic: missing_fields.append("Tekanan Darah Sistol")
                if not diastolic: missing_fields.append("Tekanan Darah Diastol")
                if not heart_rate: missing_fields.append("Detak Jantung")
                if not temperature: missing_fields.append("Suhu Tubuh")
                if not blood_sugar: missing_fields.append("Gula Darah")
                if not weight: missing_fields.append("Berat Badan")
                
                flash(f'Field berikut harus diisi: {", ".join(missing_fields)}', 'error')
                return redirect(url_for('health_check_form'))
            
            # Konversi data ke tipe yang sesuai
            try:
                systolic = int(systolic)
                diastolic = int(diastolic)
                heart_rate = int(heart_rate)
                temperature = float(temperature)
                blood_sugar = float(blood_sugar)
                weight = float(weight)
            except ValueError as e:
                flash('Format input tidak valid. Pastikan angka diisi dengan benar.', 'error')
                print(f"Error konversi data: {str(e)}")
                return redirect(url_for('health_check_form'))
            
            # Mengambil data opsional
            symptoms = request.form.get('symptoms')
            notes = request.form.get('notes')
            
            # Analisis tekanan darah
            if systolic < 90 or diastolic < 60:
                bp_status = "Hipotensi"
                bp_advice = "Tekanan darah Anda rendah. Konsultasikan dengan dokter untuk evaluasi lebih lanjut."
                bp_color = "info"
            elif systolic < 120 and diastolic < 80:
                bp_status = "Normal"
                bp_advice = "Tekanan darah Anda normal. Pertahankan gaya hidup sehat Anda!"
                bp_color = "success"
            elif (systolic < 130) or (diastolic < 85):
                bp_status = "Pra-hipertensi"
                bp_advice = "Tekanan darah Anda sedikit tinggi. Pertimbangkan untuk mengurangi asupan garam dan berolahraga teratur."
                bp_color = "warning"
            else:
                bp_status = "Hipertensi"
                bp_advice = "Tekanan darah Anda tinggi. Segera konsultasikan dengan dokter."

            # Analisis detak jantung
            if heart_rate < 60:
                hr_status = "Bradikardia"
                hr_advice = "Detak jantung Anda rendah. Konsultasikan dengan dokter."
                hr_color = "warning"
            elif heart_rate <= 100:
                hr_status = "Normal"
                hr_advice = "Detak jantung Anda normal."
                hr_color = "success"
            else:
                hr_status = "Takikardia"
                hr_advice = "Detak jantung Anda tinggi. Konsultasikan dengan dokter."
                hr_color = "danger"

            # Analisis suhu tubuh
            if temperature < 36:
                temp_status = "Hipotermia"
                temp_advice = "Suhu tubuh Anda rendah. Segera cari pertolongan medis."
                temp_color = "danger"
            elif temperature <= 37.5:
                temp_status = "Normal"
                temp_advice = "Suhu tubuh Anda normal."
                temp_color = "success"
            else:
                temp_status = "Demam"
                temp_advice = "Anda mengalami demam. Istirahat yang cukup dan konsultasikan dengan dokter."
                temp_color = "warning"

            # Analisis gula darah (asumsi pengukuran sewaktu/random)
            if blood_sugar < 70:
                bs_status = "Hipoglikemia"
                bs_advice = "Gula darah Anda rendah. Segera konsumsi makanan manis dan konsultasikan dengan dokter."
                bs_color = "danger"
            elif blood_sugar <= 140:
                bs_status = "Normal"
                bs_advice = "Kadar gula darah Anda normal."
                bs_color = "success"
            else:
                bs_status = "Hiperglikemia"
                bs_advice = "Gula darah Anda tinggi. Konsultasikan dengan dokter."
                bs_color = "warning"

#bestoisme :)
            
            # Menyimpan data ke database
            try:
                health_record = HealthRecord(
                    user_id=current_user.id,
                    blood_pressure_systolic=systolic,
                    blood_pressure_diastolic=diastolic,
                    heart_rate=heart_rate,
                    temperature=temperature,
                    blood_sugar=blood_sugar,
                    weight=weight,
                    symptoms=symptoms,
                    notes=notes
                )
                
                db.session.add(health_record)
                db.session.commit()
                
                # Redirect ke halaman hasil dengan parameter analisis
                return render_template('health_check_result.html',
                                    record=health_record,
                                    bp_status=bp_status,
                                    bp_advice=bp_advice,
                                    bp_color=bp_color,
                                    hr_status=hr_status,
                                    hr_advice=hr_advice,
                                    hr_color=hr_color,
                                    temp_status=temp_status,
                                    temp_advice=temp_advice,
                                    temp_color=temp_color,
                                    bs_status=bs_status,
                                    bs_advice=bs_advice,
                                    bs_color=bs_color)
                
            except Exception as e:
                db.session.rollback()
                print(f"Error saat menyimpan ke database: {str(e)}")
                flash('Terjadi kesalahan saat menyimpan data ke database.', 'error')
                return redirect(url_for('health_check_form'))
            
        except Exception as e:
            db.session.rollback()
            flash('Terjadi kesalahan saat memproses data. Pastikan semua field diisi dengan benar.', 'error')
            print(f"Error detail: {str(e)}")
            return redirect(url_for('health_check_form'))
    
    return render_template('health_check_form.html')

@app.route('/blood-pressure', methods=['GET', 'POST'])
@login_required
def blood_pressure():
    if request.method == 'POST':
        try:
            # Ambil data dari form
            systolic = int(request.form.get('systolic'))
            diastolic = int(request.form.get('diastolic'))
            pulse = int(request.form.get('pulse'))
            
            # Validasi range
            if not (70 <= systolic <= 200 and 40 <= diastolic <= 130 and 40 <= pulse <= 200):
                flash('Nilai yang dimasukkan tidak valid!', 'error')
                return redirect(url_for('blood_pressure'))
            
            # Simpan ke database
            record = HealthRecord(
                user_id=current_user.id,
                blood_pressure_systolic=systolic,
                blood_pressure_diastolic=diastolic,
                heart_rate=pulse
            )
            db.session.add(record)
            db.session.commit()
            
            # Analisis tekanan darah
            if systolic < 90 or diastolic < 60:
                category = "Hipotensi"
                advice = "Tekanan darah Anda rendah. Konsultasikan dengan dokter untuk evaluasi lebih lanjut."
                color = "info"
            elif systolic <= 120 and diastolic <= 80:
                category = "Normal"
                advice = "Tekanan darah Anda normal. Pertahankan gaya hidup sehat Anda!"
                color = "success"
            elif (120 < systolic <= 139) or (80 < diastolic <= 89):
                category = "Pre-Hipertensi"
                advice = "Anda berisiko hipertensi. Pertimbangkan untuk mengurangi garam dan melakukan olahraga teratur."
                color = "warning"
            else:
                category = "Hipertensi"
                advice = "Tekanan darah Anda tinggi. Segera konsultasikan dengan dokter untuk penanganan lebih lanjut."
                color = "danger"
            
            # Analisis detak jantung
            if pulse < 60:
                heart_status = "Bradikardia (detak jantung rendah)"
                heart_advice = "Detak jantung Anda di bawah normal. Konsultasikan dengan dokter."
            elif 60 <= pulse <= 100:
                heart_status = "Normal"
                heart_advice = "Detak jantung Anda dalam rentang normal."
            else:
                heart_status = "Takikardia (detak jantung tinggi)"
                heart_advice = "Detak jantung Anda di atas normal. Konsultasikan dengan dokter."
            
            flash(f'Analisis: {category}. {advice}', color)
            flash(f'Detak Jantung: {heart_status}. {heart_advice}', 'info')
            
            return redirect(url_for('blood_pressure_result', record_id=record.id))
            
        except ValueError:
            flash('Mohon masukkan angka yang valid!', 'error')
            return redirect(url_for('blood_pressure'))
        except Exception as e:
            db.session.rollback()
            flash('Terjadi kesalahan. Silakan coba lagi.', 'error')
            print(e)  
            return redirect(url_for('blood_pressure'))
    
    return render_template('blood_pressure.html')

@app.route('/blood_pressure/result/<int:record_id>')
@login_required
def blood_pressure_result(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        flash('Anda tidak memiliki akses ke data ini!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('blood_pressure_result.html', record=record)

@app.route('/bmi-calculator', methods=['GET', 'POST'])
@login_required
def bmi_calculator():
    if request.method == 'POST':
        try:
            # Ambil data dari form
            height = float(request.form.get('height'))
            weight = float(request.form.get('weight'))
            
            # Hitung BMI
            bmi = weight / ((height/100) ** 2)
            
            # Tentukan status dan warna
            if bmi < 18.5:
                status = "Berat Badan Kurang"
                status_color = "info"
            elif bmi <= 24.9:
                status = "Berat Badan Normal"
                status_color = "success"
            elif bmi <= 29.9:
                status = "Berat Badan Berlebih"
                status_color = "warning"
            else:
                status = "Obesitas"
                status_color = "danger"
            
            # Hitung rentang berat badan ideal
            ideal_min_bmi = 18.5
            ideal_max_bmi = 24.9
            min_weight = round(ideal_min_bmi * ((height/100) ** 2), 1)
            max_weight = round(ideal_max_bmi * ((height/100) ** 2), 1)
            optimal_weight = round((min_weight + max_weight) / 2, 1)
            
            return render_template('bmi_result.html',
                                bmi=bmi,
                                status=status,
                                status_color=status_color,
                                height=height,
                                weight=weight,
                                min_weight=min_weight,
                                optimal_weight=optimal_weight,
                                max_weight=max_weight)
                                
        except (ValueError, TypeError):
            flash('Mohon isi semua data dengan benar', 'error')
            return redirect(url_for('bmi_calculator'))
        except Exception as e:
            flash('Terjadi kesalahan. Silakan coba lagi.', 'error')
            print(f"Error: {str(e)}")  
            return redirect(url_for('bmi_calculator'))
            
    return render_template('bmi_calculator.html')

@app.route('/height-index', methods=['GET', 'POST'])
@login_required
def height_index():
    if request.method == 'POST':
        try:
            # Ambil data dari form
            age = int(request.form.get('age'))
            gender = request.form.get('gender')
            height = float(request.form.get('height'))
            
            # Tentukan standar tinggi berdasarkan usia dan jenis kelamin
            if age < 13:  # Anak-anak
                if gender == 'L':
                    min_height = 130
                    optimal_height = 145
                    max_height = 160
                else:
                    min_height = 128
                    optimal_height = 142
                    max_height = 157
            elif age < 18:  
                if gender == 'L':
                    min_height = 150
                    optimal_height = 165
                    max_height = 180
                else:
                    min_height = 145
                    optimal_height = 160
                    max_height = 175
            else: 
                if gender == 'L':
                    min_height = 160
                    optimal_height = 170
                    max_height = 185
                else:
                    min_height = 150
                    optimal_height = 160
                    max_height = 175
            
            # Hitung persentil (perkiraan sederhana)
            if height < min_height:
                percentile = round((height / min_height) * 25)
                status = "Di Bawah Rata-rata"
                status_color = "warning"
                description = "Tinggi badan Anda di bawah rata-rata untuk usia dan jenis kelamin Anda."
            elif height <= optimal_height:
                percentile = round(25 + ((height - min_height) / (optimal_height - min_height)) * 50)
                status = "Normal"
                status_color = "success"
                description = "Tinggi badan Anda dalam rentang normal untuk usia dan jenis kelamin Anda."
            else:
                percentile = round(75 + ((height - optimal_height) / (max_height - optimal_height)) * 25)
                if percentile > 100:
                    percentile = 100
                status = "Di Atas Rata-rata"
                status_color = "info"
                description = "Tinggi badan Anda di atas rata-rata untuk usia dan jenis kelamin Anda."
            
            return render_template('height_result.html',
                                height=height,
                                age=age,
                                gender=gender,
                                status=status,
                                status_color=status_color,
                                description=description,
                                percentile=percentile,
                                min_height=min_height,
                                optimal_height=optimal_height,
                                max_height=max_height)
                                
        except (ValueError, TypeError):
            flash('Mohon isi semua data dengan benar', 'error')
            return redirect(url_for('height_index'))
        except Exception as e:
            flash('Terjadi kesalahan. Silakan coba lagi.', 'error')
            print(f"Error: {str(e)}")  # untuk debugging
            return redirect(url_for('height_index'))
            
    return render_template('height_index.html')

@app.route('/physical-activity', methods=['GET', 'POST'])
@login_required
def physical_activity():
    if request.method == 'POST':
        try:
            # Validasi input
            activity = request.form.get('activity')
            duration = request.form.get('duration')
            intensity = request.form.get('intensity')
            weight = request.form.get('weight')

            # Periksa apakah semua field terisi
            if not all([activity, duration, intensity, weight]):
                flash('Mohon isi semua data yang diperlukan', 'error')
                return redirect(url_for('physical_activity'))

            # Konversi ke tipe data yang sesuai
            try:
                duration = float(duration)
                weight = float(weight)
            except ValueError:
                flash('Durasi dan berat badan harus berupa angka', 'error')
                return redirect(url_for('physical_activity'))

            # Validasi nilai
            if duration <= 0 or weight <= 0:
                flash('Durasi dan berat badan harus lebih besar dari 0', 'error')
                return redirect(url_for('physical_activity'))
            
            # Kalori yang terbakar per menit untuk setiap aktivitas (estimasi)
            calories_per_minute = {
                'walking': {'low': 3, 'medium': 4, 'high': 5},
                'running': {'low': 8, 'medium': 10, 'high': 12},
                'cycling': {'low': 5, 'medium': 7, 'high': 9},
                'swimming': {'low': 6, 'medium': 8, 'high': 10},
                'yoga': {'low': 2, 'medium': 3, 'high': 4},
                'gym': {'low': 4, 'medium': 6, 'high': 8}
            }
            
            # Periksa apakah aktivitas dan intensitas valid
            if activity not in calories_per_minute or intensity not in calories_per_minute[activity]:
                flash('Aktivitas atau intensitas tidak valid', 'error')
                return redirect(url_for('physical_activity'))
            
            # Hitung kalori yang terbakar
            base_calories = calories_per_minute[activity][intensity] * duration
            calories_burned = round(base_calories * (weight / 60), 1)
            
            # Tentukan level intensitas dan rekomendasi
            intensity_levels = {
                'low': {
                    'name': 'Ringan',
                    'recommendation': 'Tingkatkan intensitas secara bertahap untuk hasil yang lebih optimal.',
                    'color': 'info'
                },
                'medium': {
                    'name': 'Sedang',
                    'recommendation': 'Pertahankan intensitas ini dan tingkatkan durasi secara bertahap.',
                    'color': 'success'
                },
                'high': {
                    'name': 'Tinggi',
                    'recommendation': 'Pastikan cukup istirahat dan hidrasi untuk pemulihan yang baik.',
                    'color': 'warning'
                }
            }
            
            intensity_info = intensity_levels[intensity]
            
            # Tentukan aktivitas dalam bahasa Indonesia
            activity_names = {
                'walking': 'Jalan Kaki',
                'running': 'Lari',
                'cycling': 'Bersepeda',
                'swimming': 'Berenang',
                'yoga': 'Yoga',
                'gym': 'Latihan Beban'
            }
            
            activity_name = activity_names.get(activity, activity)
            
            return render_template('physical_activity_result.html',
                                activity=activity_name,
                                duration=duration,
                                intensity=intensity_info['name'],
                                calories_burned=calories_burned,
                                recommendation=intensity_info['recommendation'],
                                color=intensity_info['color'])
                                
        except Exception as e:
            print(f"Error detail: {str(e)}")  # untuk debugging
            flash('Terjadi kesalahan saat memproses data. Pastikan semua data diisi dengan benar.', 'error')
            return redirect(url_for('physical_activity'))
            
    return render_template('physical_activity.html')

@app.route('/health-records')
@login_required
def health_records():
    # Mengambil semua pemeriksaan kesehatan user yang sedang login
    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(HealthRecord.record_date.desc()).all()
    
    # Jika ada data pemeriksaan, siapkan data untuk grafik
    if records:
        # Mengambil 10 data terakhir dan membalik urutannya untuk grafik
        recent_records = records[:10][::-1]
        
        dates = [record.record_date.strftime('%d/%m') for record in recent_records]
        systolic = [record.blood_pressure_systolic for record in recent_records]
        diastolic = [record.blood_pressure_diastolic for record in recent_records]
        heart_rates = [record.heart_rate for record in recent_records]
        
        return render_template('health_records.html',
                             health_records=records,
                             dates=dates,
                             systolic=systolic,
                             diastolic=diastolic,
                             heart_rates=heart_rates)
    
    return render_template('health_records.html', health_records=[])

@app.route('/medicine-reminder', methods=['GET', 'POST'])
@login_required
def medicine_reminder():
    if request.method == 'POST':
        try:
            # Ambil data dari form
            medicine_name = request.form.get('medicine_name')
            dosage = request.form.get('dosage')
            frequency = request.form.get('frequency')
            times = request.form.getlist('times[]')  
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            notes = request.form.get('notes')
            
            # Validasi input
            if not all([medicine_name, dosage, frequency, times, start_date, end_date]):
                flash('Mohon lengkapi semua field yang diperlukan', 'error')
                return redirect(url_for('medicine_reminder'))
            
            # Konversi string tanggal ke objek date
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if start_date > end_date:
                    flash('Tanggal mulai harus sebelum tanggal selesai', 'error')
                    return redirect(url_for('medicine_reminder'))
                    
            except ValueError:
                flash('Format tanggal tidak valid', 'error')
                return redirect(url_for('medicine_reminder'))
            
            # Gabung waktu menjadi string (dipisah koma)
            time_str = ','.join(times)
            
            # Buat pengingat baru
            reminder = MedicineReminder(
                user_id=current_user.id,
                medicine_name=medicine_name,
                dosage=dosage,
                frequency=frequency,
                time=time_str,
                start_date=start_date,
                end_date=end_date,
                notes=notes,
                is_active=True
            )
            
            db.session.add(reminder)
            db.session.commit()
            
            flash('Pengingat obat berhasil ditambahkan!', 'success')
            return redirect(url_for('medicine_reminder'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            return redirect(url_for('medicine_reminder'))
    
    # Ambil semua pengingat obat aktif untuk user yang sedang login
    reminders = MedicineReminder.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(MedicineReminder.start_date.desc()).all()
    
    return render_template('medicine_reminder.html', reminders=reminders)

@app.route('/medicine-reminder/delete/<int:id>')
@login_required
def delete_reminder(id):
    reminder = MedicineReminder.query.get_or_404(id)
    
    # Pastikan reminder milik user yang sedang login
    if reminder.user_id != current_user.id:
        flash('Anda tidak memiliki akses ke pengingat ini', 'error')
        return redirect(url_for('medicine_reminder'))
    
    try:
        reminder.is_active = False 
        db.session.commit()
        flash('Pengingat obat berhasil dihapus', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
    
    return redirect(url_for('medicine_reminder'))

@app.route('/medicine-reminder/edit/<int:id>', methods=['POST'])
@login_required
def edit_reminder(id):
    reminder = MedicineReminder.query.get_or_404(id)
    
    # Pastikan reminder milik user yang sedang login
    if reminder.user_id != current_user.id:
        flash('Anda tidak memiliki akses ke pengingat ini', 'error')
        return redirect(url_for('medicine_reminder'))
    
    try:
        reminder.medicine_name = request.form.get('medicine_name')
        reminder.dosage = request.form.get('dosage')
        reminder.frequency = request.form.get('frequency')
        reminder.time = ','.join(request.form.getlist('times[]'))
        reminder.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        reminder.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        reminder.notes = request.form.get('notes')
        
        db.session.commit()
        flash('Pengingat obat berhasil diperbarui', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
    
    return redirect(url_for('medicine_reminder'))

@app.route('/health-profile', methods=['GET', 'POST'])
@login_required
def health_profile():
    if request.method == 'POST':
        try:
            # Update data profil
            current_user.full_name = request.form.get('full_name')
            if request.form.get('birth_date'):
                current_user.birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d')
            current_user.gender = request.form.get('gender')
            current_user.phone = request.form.get('phone')
            current_user.address = request.form.get('address')
            
            # Update data kesehatan
            if request.form.get('height'):
                current_user.height = float(request.form.get('height'))
            if request.form.get('weight'):
                current_user.weight = float(request.form.get('weight'))
            current_user.blood_type = request.form.get('blood_type')

            # Handle foto profil
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and file.filename:
                    # Buat direktori jika belum ada
                    if not os.path.exists('static/uploads/profile_pics'):
                        os.makedirs('static/uploads/profile_pics')
                    
                    # Simpan file
                    filename = secure_filename(file.filename)
                    file_ext = os.path.splitext(filename)[1]
                    new_filename = f"profile_{current_user.id}{file_ext}"
                    file_path = os.path.join('static/uploads/profile_pics', new_filename)
                    
                    # Hapus foto lama jika ada
                    if current_user.profile_pic:
                        old_file = os.path.join('static/uploads/profile_pics', current_user.profile_pic)
                        if os.path.exists(old_file):
                            os.remove(old_file)
                    
                    # Simpan foto baru
                    file.save(file_path)
                    current_user.profile_pic = new_filename

            # Simpan perubahan ke database
            db.session.commit()
            flash('Profil berhasil diperbarui!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            print(f"Error: {e}")
        
        return redirect(url_for('health_profile'))

    return render_template('health_profile.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        feedback_type = request.form.get('feedback_type')
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        
        # Handle file upload
        screenshot = request.files.get('screenshot')
        if screenshot and screenshot.filename:
            # Buat direktori jika belum ada
            if not os.path.exists('static/uploads/feedback'):
                os.makedirs('static/uploads/feedback')
            
            # Simpan file
            filename = secure_filename(f"{current_user.username}_{int(datetime.utcnow().timestamp())}_{screenshot.filename}")
            screenshot.save(os.path.join('static/uploads/feedback', filename))
        
        flash('Terima kasih atas masukan Anda!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('feedback.html')

@app.route('/active-reminders')
@login_required
def active_reminders():
    try:
        # Ambil pengingat obat yang aktif untuk user yang sedang login
        active_reminders = MedicineReminder.query.filter(
            and_(
                MedicineReminder.user_id == current_user.id,
                MedicineReminder.is_active == True,
                MedicineReminder.end_date >= datetime.now().date()
            )
        ).order_by(MedicineReminder.start_date).all()
        
        return render_template('active_reminders.html', reminders=active_reminders)
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            print("Database terhubung!")
            
            users = User.query.all()
            if users:
                print(f"\nJumlah user terdaftar: {len(users)}")
                for user in users:
                    print(f"- {user.username} ({user.email})")
            else:
                print("\nBelum ada user terdaftar")
        
        app.run(debug=True, port=5001)
    except Exception as e:
        print(f"Error koneksi database: {str(e)}")

