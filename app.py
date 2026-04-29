import os
from datetime import datetime
from functools import wraps


# Menu image upload + delete support

from werkzeug.utils import secure_filename
from flask import current_app

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash




MENU_GALLERIES = {
    "Jollof Rice + Chicken": [
        "images/jollof4.jpeg",
        "images/jollof0.jpeg",
        "images/jollof1.jpeg",
    ],
    "Egusi + Pounded Yam": [
        "images/egusi1.jpeg",
        "images/egusi3.jpeg",
        "images/egusinew.jpeg",
    ],
    "Fried Rice + Chicken": [
        "images/friedrice.jpeg",
        "images/friedrice1.jpeg",
    ],
    "Beans + Plantain": [
        "images/beansandplantain2.jpeg",
        "images/beansandplantain1.jpeg",
    ],
   "Okro Soup": [
        "images/okro0.jpeg",
        "images/okro1.jpeg",
    ],
    "Custome Order": [
        "images/chat.jpeg",
        "images/custome1.jpeg",
    ],


    "Jollof Rice + Chicken": [
        "images/jollof4.jpeg",
        "images/jollof0.jpeg",
        "images/jollof1.jpeg",
    ],
    
}

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'n_kitchens.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(80), nullable=False, default='Main')
    available = db.Column(db.Boolean, default=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    menu_item = db.relationship('MenuItem')


class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Please log in as admin.', 'warning')
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)

    return wrapper


def get_cart():
    return session.setdefault('cart', {})


def cart_count():
    return sum(get_cart().values())


def cart_items_with_totals():
    cart = get_cart()
    items = []
    total = 0

    if not cart:
        return items, total

    menu_items = MenuItem.query.filter(MenuItem.id.in_(cart.keys())).all()
    lookup = {str(item.id): item for item in menu_items}

    for item_id, qty in cart.items():
        item = lookup.get(str(item_id))
        if not item:
            continue

        subtotal = item.price * qty
        total += subtotal
        items.append({
            'item': item,
            'quantity': qty,
            'subtotal': subtotal
        })

    return items, total


# whatsapp notification 

def send_whatsapp_order_notification(order):
    phone = os.getenv("WHATSAPP_PHONE")
    apikey = os.getenv("WHATSAPP_API_KEY")

    if not phone or not apikey:
        print("WhatsApp skipped: WHATSAPP_PHONE or WHATSAPP_API_KEY missing.")
        return

    message = f"""🚨 NEW ORDER

Name: {order.customer_name}
Phone: {order.phone}

Items:
"""

    for item in order.items:
        item_name = item.menu_item.name if item.menu_item else "Unknown Item"
        message += f"- {item_name} x{item.quantity}\n"

    message += f"""
Total: TZS {order.total_amount}
Address: {order.address}
"""

    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={quote(message)}&apikey={apikey}"

    try:
        print("Sending WhatsApp notification...")
        response = requests.get(url, timeout=20)
        print("WhatsApp sent:", response.status_code)
        print("WhatsApp response:", response.text)
    except Exception as e:
        print("WhatsApp failed:", e)

# app.py - Telegram order notification helper

def send_telegram_order_notification(order):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        return False

    message = f"""
🍲 New N' Kitchens Order

Order ID: {order.id}
Customer: {order.customer_name}
Phone: {order.phone}
Address: {order.address}
Total: {order.total_amount} TZS
Status: {order.status}
Notes: {order.notes or 'None'}
""".strip()

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except requests.RequestException:
        return False


def seed_data():
    if not MenuItem.query.first():
        sample_items = [
            MenuItem(
                name='Jollof Rice + Chicken',
                description='Smoky Nigerian jollof rice served with fried chicken.',
                price=12000,
                image_url='/static/images/jollof4.jpeg',
                category='Rice',
            ),
            MenuItem(
                name='Egusi + Pounded Yam',
                description='Rich melon soup with soft pounded yam.',
                price=15000,
                image_url='/static/images/egusi0.jpeg',
                category='Soup',
            ),
            MenuItem(
                name='Fried Rice + Chicken',
                description='Colorful fried rice with vegetables and juicy chicken.',
                price=12000,
                image_url='/static/images/friedrice1.jpeg',
                category='Rice',
            ),
            MenuItem(
                name='Beans + Plantain',
                description='Soft beans porridge served with sweet fried plantain.',
                price=9000,
                image_url='/static/images/beansandplantain0.jpeg',
                category='Specials',
            ),
            MenuItem(
                name='Okro Soup',
                description='Fresh okro soup prepared with rich flavor and served hot.',
                price=10000,
                image_url='/static/images/okro0.jpeg',
                category='Soup',
            ),
            MenuItem(
                name='Custom Order',
                description='Tell us exactly what you want on WhatsApp.',
                price=3000,
                image_url='/static/images/chat.jpeg',
                category='Specials',
            ),
        ]
        db.session.add_all(sample_items)

    if not AdminUser.query.filter_by(username=os.getenv('ADMIN_USERNAME', 'admin')).first():
        admin = AdminUser(
            username=os.getenv('ADMIN_USERNAME', 'admin'),
            password_hash=generate_password_hash(
                os.getenv('ADMIN_PASSWORD', 'admin123'),
                method='pbkdf2:sha256'
            ),
        )
        db.session.add(admin)

    db.session.commit()


@app.context_processor
def inject_globals():
    return {'cart_count': cart_count()}


@app.route('/')
def home():
    featured_items = MenuItem.query.filter_by(available=True).limit(6).all()
    return render_template('home.html', featured_items=featured_items, galleries=MENU_GALLERIES)


@app.route('/menu')
def menu():
    category = request.args.get('category')
    query = MenuItem.query.filter_by(available=True)

    if category:
        query = query.filter_by(category=category)

    items = query.order_by(MenuItem.category, MenuItem.name).all()
    categories = [row[0] for row in db.session.query(MenuItem.category).distinct().all()]

    return render_template(
        'menu.html',
        items=items,
        categories=categories,
        active_category=category,
        galleries=MENU_GALLERIES
    )

@app.post('/add-to-cart/<int:item_id>')
def add_to_cart(item_id):
    item = MenuItem.query.get_or_404(item_id)
    cart = get_cart()
    key = str(item.id)
    cart[key] = cart.get(key, 0) + int(request.form.get('quantity', 1))
    session.modified = True
    flash(f'{item.name} added to cart.', 'success')
    return redirect(request.referrer or url_for('menu'))


@app.route('/cart')
def view_cart():
    items, total = cart_items_with_totals()
    return render_template('cart.html', cart_items=items, total=total)


@app.post('/cart/update/<int:item_id>')
def update_cart(item_id):
    cart = get_cart()
    qty = max(0, int(request.form.get('quantity', 1)))
    key = str(item_id)
    if qty == 0:
        cart.pop(key, None)
    else:
        cart[key] = qty
    session.modified = True
    flash('Cart updated.', 'info')
    return redirect(url_for('view_cart'))


@app.post('/cart/remove/<int:item_id>')
def remove_from_cart(item_id):
    cart = get_cart()
    cart.pop(str(item_id), None)
    session.modified = True
    flash('Item removed from cart.', 'info')
    return redirect(url_for('view_cart'))


# app.py - checkout route

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    items, total = cart_items_with_totals()

    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('menu'))

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()

        if not customer_name or not phone or not address:
            flash('Name, phone, and address are required.', 'danger')
            return render_template('checkout.html', cart_items=items, total=total)

        order = Order(
            customer_name=customer_name,
            phone=phone,
            address=address,
            notes=notes,
            total_amount=total,
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()

        for entry in items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    menu_item_id=entry['item'].id,
                    quantity=entry['quantity'],
                    price=entry['item'].price,
                )
            )

        db.session.commit()

        try:
            send_telegram_order_notification(order)
        except Exception as e:
            print("Telegram notification error inside checkout:", e)

        try:
            send_whatsapp_order_notification(order)
        except Exception as e:
            print("WhatsApp notification error inside checkout:", e)

        session['cart'] = {}
        session['last_order_id'] = order.id
        session['customer_phone'] = order.phone
        session.modified = True

        flash('Order placed successfully.', 'success')
        return redirect(url_for('order_success'))

    return render_template('checkout.html', cart_items=items, total=total)


@app.route('/order-success')
def order_success():
    order_id = session.get('last_order_id')
    order = Order.query.get(order_id) if order_id else None
    return render_template('order_success.html', order=order)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = AdminUser.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.id
            flash('Welcome back.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'danger')
    return render_template('admin/login.html')



@app.route('/my-orders')
def my_orders():
    customer_phone = session.get('customer_phone')

    # fallback: recover customer phone from last order if session phone is missing
    if not customer_phone:
        last_order_id = session.get('last_order_id')
        if last_order_id:
            last_order = Order.query.get(last_order_id)
            if last_order:
                customer_phone = last_order.phone
                session['customer_phone'] = customer_phone
                session.modified = True

    if not customer_phone:
        flash('No customer order history found on this device yet. Place an order first.', 'warning')
        return redirect(url_for('home'))

    orders = Order.query.filter_by(phone=customer_phone).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)


@app.route('/my-orders/<int:order_id>')
def my_order_detail(order_id):
    customer_phone = session.get('customer_phone')

    if not customer_phone:
        flash('You cannot view this order right now.', 'danger')
        return redirect(url_for('home'))

    order = Order.query.get_or_404(order_id)

    if order.phone != customer_phone:
        flash('This order does not belong to this customer session.', 'danger')
        return redirect(url_for('my_orders'))

    return render_template('my_order_detail.html', order=order)



@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_id', None)
    flash('Logged out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    total_orders = len(orders)
    total_revenue = sum(order.total_amount for order in orders)
    pending_orders = sum(1 for order in orders if order.status == 'Pending')
    return render_template(
        'admin/dashboard.html',
        orders=orders,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
    )


@app.route('/admin/order/<int:order_id>', methods=['GET', 'POST'])
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        order.status = request.form.get('status', order.status)
        db.session.commit()
        flash('Order status updated.', 'success')
        return redirect(url_for('admin_order_detail', order_id=order.id))
    return render_template('admin/order_detail.html', order=order)


# Admin menu page: add menu item with image upload
@app.route('/admin/menu', methods=['GET', 'POST'])
@admin_required
def admin_menu():
    if request.method == 'POST':
        image_url = ''

        uploaded_image = request.files.get('image')

        if uploaded_image and uploaded_image.filename:
            filename = secure_filename(uploaded_image.filename)

            upload_folder = os.path.join(
                current_app.root_path,
                'static',
                'images',
                'menu'
            )

            os.makedirs(upload_folder, exist_ok=True)

            image_path = os.path.join(upload_folder, filename)
            uploaded_image.save(image_path)

            image_url = f'/static/images/menu/{filename}'

        item = MenuItem(
            name=request.form['name'].strip(),
            description=request.form['description'].strip(),
            price=float(request.form['price']),
            image_url=image_url,
            category=request.form['category'].strip() or 'Main',
            available=bool(request.form.get('available')),
        )

        db.session.add(item)
        db.session.commit()

        flash('Menu item added.', 'success')
        return redirect(url_for('admin_menu'))

    items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template('admin/menu.html', items=items)
# Delete menu item from admin panel
@app.route('/admin/menu/delete/<int:item_id>', methods=['POST'])
@admin_required
def delete_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)

    db.session.delete(item)
    db.session.commit()

    flash('Menu item deleted.', 'success')
    return redirect(url_for('admin_menu'))



@app.route('/admin/menu/toggle/<int:item_id>', methods=['POST'])
@admin_required
def toggle_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.available = not item.available
    db.session.commit()
    flash('Menu availability updated.', 'info')
    return redirect(url_for('admin_menu'))


@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    seed_data()
    print('Database initialized and seeded.')


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == '__main__':
    app.run(debug=True)




# EDIT MENU ITEM
@app.route('/admin/menu/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)

    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.price = float(request.form['price'])
        item.category = request.form['category']
        item.image_url = request.form['image_url']

        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('admin_menu'))

    return render_template('edit_item.html', item=item)