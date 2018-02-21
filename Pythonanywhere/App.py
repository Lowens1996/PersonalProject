from flask import Flask, render_template, request, session, jsonify
import json
# import pymongo
import os
import paypalrestsdk
import uuid
import MySQLdb

paypalrestsdk.configure({
  "mode": "sandbox",  # sandbox or live
  "client_id": "ASNdXIYOglgkncwMqPFadYDjhKmlET-iFnb8JY_EuBol59DIZGcX0vYrRl3lRhw2nHKAXE5ACBMIGlP9",  # merchant account
  "client_secret": "EJ6ZHrvWB5mU_Te6RSNwIaFra6PNUzk63OY-0jmaUazUKuLlZJu1IGu5dhinmbNdWXT4TKq4-4VdV1mj"})

app = Flask(__name__)
app.secret_key = os.urandom(24)
conn = MySQLdb.connect("Owens.mysql.pythonanywhere-services.com", "Owens", "drinksafe", "Owens$ProjectDB")
db = conn.cursor()

# client = pymongo.MongoClient()
orderlist = []
# need to do this for all product categories
# productdb = client['products']



@app.route('/')
def start_app():
    return render_template('login.html')


@app.route('/UserLogin', methods=['POST'])
def validate_user():
    if session.get('user') is None:
        # get users from database
        # db = client['test_users']
        # collection = db['users']
        # get user input
        username = request.form.get('username')
        password = request.form.get('password')
        # validate user and create session or return to login with invalid details
        # login_user = collection.find_one({'username': username})
        query =  """select * from Customers where Username = %s"""
        db.execute(query, (username,))
        login_user = db.fetchall()
        dbuser = login_user[0]
        db_username = dbuser[0]
        if db_username == username:
            db_userpswd = dbuser[1]
            if db_userpswd == password:
                session['user'] = username
                return render_template('Home.html',
                                       user=session['user'])
            else:
                alert = True
                return render_template('login.html',
                                       popup=alert)
        else:
            alert = True
            return render_template('login.html',
                                   popup=alert)
    else:
        return render_template('Home.html')


@app.route('/Order')
def display_order_page():
    return render_template('Categories.html')


@app.route('/Pay', methods=['GET'])
def display_paypal():
    return render_template('Pay.html')


def write_json(productnames, quantaties, prices, totalprice, order_id):
    # create JSON object
    order = {
        'orderID': order_id,
        'product_name': productnames,
        'quantity': quantaties,
        'price': prices,
        'total': totalprice,
        'accept': 0,
        'paid': 0,
        'completed': 0,
        'user': session['user']
    }
    # write to JSON file
    j_order = json.dumps(order)  # JSON order object
    with open("/home/Owens/ProjectApp/static/Orders.json", "w") as file:
        file.write(j_order)



@app.route('/Specials')
def display_specials_page():
    query = """select * from Products"""
    db.execute(query)
    products = db.fetchall()
    specialslist = []
    item = {"product": '', "price":0}
    for product in products:
        if product[2] == 'special':
            item['product'] = product[0]
            item['price'] = product[1]
            specialslist.append(item.copy())

    return render_template('Specials.html',
    specialslist=specialslist)


@app.route('/PreviewOrder', methods=['POST'])
def prepare_order_preview():
    global productnames
    global quantaties
    global prices
    global totalprice

    if 'Submit' in request.form:
        # create order id & order session
        order_id = str(uuid.uuid4())
        session['order'] = order_id
        # create json
        write_json(productnames, quantaties, prices, totalprice, order_id)
        # read JSON
        file = open("/home/Owens/ProjectApp/static/Orders.json", "r")
        j_orders = file.read()
        order = json.loads(j_orders)
        # for order in orders:
        if order['orderID'] == session['order']:
            productnames = order['product_name']
            quantaties = order['quantity']
            prices = order['price']
            total = order['total']

        return render_template('Orderlist.html',
                               products=productnames, quantaties=quantaties, prices=prices, total=total,
                               orderID=session['order'])
    else:
        productnames = []
        quantaties = []
        prices = []
        totalprice = 0.0
        # if 'Specials' in request.form:
        query = """SELECT * FROM Products WHERE type = 'special'"""
        db.execute(query)
        category = db.fetchall()

        for k, v in request.form.items():
            value = int(v)
            if value > 0:
                productnames.append(k)
                quantaties.append("X"+str(value))
                for product in category:
                    if product[0] == k:
                        price = product[1]
                        break
                itemprice = price * value
                prices.append(itemprice)
                totalprice = totalprice + float(itemprice)
        return render_template('Categories.html')


@app.route('/payment', methods=['POST'])
def payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://owens.pythonanywhere.com/payment/execute",
            "cancel_url": "https://owens.pythonanywhere.com/"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "item",
                    "sku": "item",
                    "price": totalprice,
                    "currency": "GBP",
                    "quantity": 1}]},
            "amount": {
                "total": totalprice,
                "currency": "GBP"},
            "description": "This is the payment transaction description."}]})

    if payment.create():
        print('payment success')
    else:
        print(payment.error)

    return jsonify({'paymentID': payment.id})


@app.route('/executePayment', methods=['POST'])
def execute():

    payment = paypalrestsdk.Payment.find(request.form['paymentID'])

    if payment.execute({'payer_id': request.form['payerID']}):
         return render_template('waiting.html')
    else:
        print(payment.error)


@app.route('/waiting')
def display_waiting_page():
    message = "Waiting for order to be accepted"
    return render_template('waiting.html',
                            orderid=session['order'], refresh = 1, message=message)


@app.route('/checkOrder')
def checkOrder():
    # open("/home/Owens/ProjectApp/static/Orders.json", "r")
    file = open("/home/Owens/ProjectApp/static/Orders.json", "r")
    j_orders = file.read()
    order = json.loads(j_orders)
    if order['orderID'] == session['order']:
        accepted = order['accept']
        if accepted == 1:
            message = "Your order has been accepted"
            return render_template('waiting.html',
                                    orderid=session['order'], refresh = 0, message=message)


if __name__ == '__main__':
    app.run(debug=True)
