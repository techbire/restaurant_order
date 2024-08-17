import os
import stripe
import logging
logging.basicConfig(level=logging.DEBUG)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tmp/restaurant.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    dish_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    special_instructions = db.Column(db.Text)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    try:
        menu_items = MenuItem.query.all()
        app.logger.info(f"Retrieved {len(menu_items)} menu items")
        return render_template('index.html', menu_items=menu_items)
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return "An error occurred", 500
    
@cache.cached(timeout=60)
def index():
    menu_items = MenuItem.query.all()
    return render_template('index.html', menu_items=menu_items)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        app.logger.info(f'New user registered: {username}')
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            app.logger.info(f'User logged in: {username}')
            return redirect(url_for('index'))
        else:
            app.logger.warning(f'Failed login attempt for username: {username}')
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    app.logger.info(f'User logged out: {current_user.username}')
    logout_user()
    return redirect(url_for('index'))

@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    menu_items = MenuItem.query.all()
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        dish_name = request.form['dish_name']
        quantity = request.form['quantity']
        special_instructions = request.form['special_instructions']
        
        if not customer_name or not dish_name or not quantity:
            flash('Please fill in all required fields')
            return render_template('order.html', menu_items=menu_items)
        
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except ValueError:
            flash('Quantity must be a positive integer')
            return render_template('order.html', menu_items=menu_items)
        
        menu_item = MenuItem.query.filter_by(name=dish_name).first()
        if not menu_item:
            flash('Invalid menu item selected')
            return render_template('order.html', menu_items=menu_items)
        
        total_amount = menu_item.price * quantity
        
        new_order = Order(user_id=current_user.id, customer_name=customer_name, dish_name=dish_name, 
                          quantity=quantity, special_instructions=special_instructions)
        db.session.add(new_order)
        db.session.commit()
        
        app.logger.info(f'New order placed: Order ID {new_order.id}, User ID {current_user.id}')
        
        # Create a Stripe PaymentIntent
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),  # Stripe expects amounts in cents
                currency='usd',
                metadata={'order_id': new_order.id}
            )
            
            return render_template('payment.html', client_secret=intent.client_secret, order=new_order, total_amount=total_amount)
        except stripe.error.StripeError as e:
            app.logger.error(f'Stripe error: {str(e)}')
            flash('An error occurred while processing your payment. Please try again.')
            return redirect(url_for('order'))
    
    return render_template('order.html', menu_items=menu_items)

@app.route('/payment_success/<int:order_id>')
@login_required
def payment_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        app.logger.warning(f'Unauthorized access attempt to order {order_id} by user {current_user.id}')
        flash('Unauthorized access')
        return redirect(url_for('index'))
    
    order.status = 'Paid'
    db.session.commit()
    
    app.logger.info(f'Payment successful for order {order_id}')
    flash('Payment successful! Your order has been confirmed.')
    return redirect(url_for('order_history'))

@app.route('/payment_cancel/<int:order_id>')
@login_required
def payment_cancel(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        app.logger.warning(f'Unauthorized access attempt to cancel order {order_id} by user {current_user.id}')
        flash('Unauthorized access')
        return redirect(url_for('index'))
    
    db.session.delete(order)
    db.session.commit()
    
    app.logger.info(f'Payment cancelled for order {order_id}')
    flash('Payment cancelled. Your order has been removed.')
    return redirect(url_for('order'))

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        app.logger.error('Invalid payload')
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        app.logger.error('Invalid signature')
        return 'Invalid signature', 400

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata']['order_id']
        
        order = Order.query.get(order_id)
        if order:
            order.status = 'Paid'
            new_payment = Payment(
                order_id=order_id,
                amount=payment_intent['amount'] / 100,
                currency=payment_intent['currency'],
                status='Succeeded',
                payment_intent_id=payment_intent['id']
            )
            db.session.add(new_payment)
            db.session.commit()
            app.logger.info(f'Payment recorded for order {order_id}')

    return 'Success', 200

@app.route('/order_history')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('order_history.html', orders=orders)

@app.route('/menu')
@cache.cached(timeout=300)  # Cache for 5 minutes
def menu():
    menu_items = MenuItem.query.all()
    return render_template('menu.html', menu_items=menu_items)

def add_sample_menu_items():
    items = [
        MenuItem(name="Margherita Pizza", description="Classic tomato and mozzarella pizza", price=12.99, category="Pizza"),
        MenuItem(name="Chicken Alfredo", description="Creamy pasta with grilled chicken", price=14.99, category="Pasta"),
        MenuItem(name="Caesar Salad", description="Romaine lettuce with Caesar dressing and croutons", price=8.99, category="Salad"),
        MenuItem(name="Cheeseburger", description="Beef patty with cheese, lettuce, and tomato", price=10.99, category="Burgers"),
        MenuItem(name="Veggie Stir Fry", description="Mixed vegetables in a savory sauce", price=11.99, category="Vegetarian"),
    ]
    
    for item in items:
        existing_item = MenuItem.query.filter_by(name=item.name).first()
        if not existing_item:
            db.session.add(item)
    
    db.session.commit()

def init_db():
    with app.app_context():
        db.create_all()
        add_sample_menu_items()

if __name__ == '__main__':
    init_db()
    app.run()

if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/restaurant_app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Restaurant app startup')
    
    with app.app_context():
        db.create_all()
        add_sample_menu_items()
    app.run(debug=True)
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"500 error: {str(error)}")
    return "500 Internal Server Error", 500