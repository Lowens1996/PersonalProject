from flask import Flask, render_template, request, session, jsonify
import pymongo
import os
import paypalrestsdk

paypalrestsdk.configure({
  "mode": "sandbox",  # sandbox or live
  "client_id": "ASNdXIYOglgkncwMqPFadYDjhKmlET-iFnb8JY_EuBol59DIZGcX0vYrRl3lRhw2nHKAXE5ACBMIGlP9",  # merchant account
  "client_secret": "EJ6ZHrvWB5mU_Te6RSNwIaFra6PNUzk63OY-0jmaUazUKuLlZJu1IGu5dhinmbNdWXT4TKq4-4VdV1mj"})

app = Flask(__name__)
client = pymongo.MongoClient()
db = client['test_users']
collection = db['users']
# used to display product list for order pages
productdb = client['products']
specials = productdb['Specials']
orderlist = []
totalprice = 0.0

# os.urandom(24) generates random sting for app.secrete key used for sessions
app.secret_key = os.urandom(24)


@app.route('/')
def display_form() -> 'html':
    return render_template('login.html')


@app.route('/checkCredentials', methods=['POST', 'GET'])
def check_user():
    # check user details & create session
    username = request.form.get('username')
    password = request.form.get('password')
    # create user session
    login_user = collection.find_one({'username': username})
    if login_user:
        if login_user['password'] == password:
            session['username'] = username
            user = session['username']
            return render_template('Home.html',
                                   user=user)
    else:
        pop = True
        return render_template('login.html',
                               popup=pop)


@app.route('/Order')
def order_page():
    return render_template('OrderPage.html')\



@app.route('/Specials')
def specials_page():
    specialslist = []
    item = {"product": '', "price": 0}

    for product in specials.find():
        item['product'] = product['product_name']
        item['price'] = product['product_price']
        print(item)
        specialslist.append(item.copy())
        print(specialslist)

    return render_template('Specials.html',
                           specialslist=specialslist)


@app.route('/Draft')
def draft_page():
    return render_template('Draft.html')


@app.route('/PreviewOrder', methods=['POST'])
def handle_order():
    global totalprice
    if 'Submit' in request.form:
        return render_template('Orderlist.html',
                               list=orderlist, totalprice=totalprice)
    else:
        for k, v in request.form.items():  # k = product name v = the quantity selected
            v = int(v)
            if v > 0:
                orderlist.append(k)  # add product name to the list
                orderlist.append("X" + str(v))  # add quantity selected to the list
                for product in specials.find():
                    if product['product_name'] == k:
                        price = product['product_price']
                        break
                itemprice = price * v
                orderlist.append(itemprice)  # price x quantity
                totalprice = totalprice + float(itemprice)
        return render_template('OrderPage.html')


@app.route('/payment', methods=['POST'])
def payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:3000/payment/execute",
            "cancel_url": "http://localhost:3000/"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "item",
                    "sku": "item",
                    "price": "100.00",
                    "currency": "GBP",
                    "quantity": 1}]},
            "amount": {
                "total": "100.00",
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
        print('payment executed')
    else:
        print(payment.error)


if __name__ == '__main__':
    app.run(debug=True)