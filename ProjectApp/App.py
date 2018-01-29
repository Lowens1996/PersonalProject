from flask import Flask, render_template, request, session
import jsonify
import json
import pymongo
import os
import paypalrestsdk
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)
client = pymongo.MongoClient()
orderlist = []
# need to do this for all product categories
productdb = client['products']



@app.route('/')
def start_app():
    return render_template('login.html')


@app.route('/UserLogin', methods=['POST'])
def validate_user():
    if session.get('user') is None:
        # get users from database
        db = client['test_users']
        collection = db['users']
        # get user input
        username = request.form.get('username')
        password = request.form.get('password')
        # validate user and create session or return to login with invalid details
        login_user = collection.find_one({'username': username})
        if login_user:
            if login_user['password'] == password:
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
    with open("C:/Users/Lee/PycharmProjects/ProjectApp/static/Orders.json", "w") as file:
        file.write(j_order)



@app.route('/Specials')
def display_specials_page():
    specials = productdb['Specials']
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
        file = open("C:/Users/Lee/PycharmProjects/ProjectApp/static/Orders.json", "r")
        j_orders = file.read()
        order = json.loads(j_orders)
        # for order in orders:
        print(order['orderID'])
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
        category = productdb['Specials']

        for k, v in request.form.items():
            value = int(v)
            if value > 0:
                productnames.append(k)
                quantaties.append("X"+str(value))
                for product in category.find():
                    if product['product_name'] == k:
                        price = product['product_price']
                        break
                itemprice = price * value
                prices.append(itemprice)
                totalprice = totalprice + float(itemprice)
        return render_template('Categories.html')


if __name__ == '__main__':
    app.run(debug=True)
