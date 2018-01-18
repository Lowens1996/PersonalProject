from flask import Flask, render_template, request, session, jsonify
import pymongo
import os

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


@app.route('/HandleOrder', methods=['POST'])
def handle_order():
    global totalprice
    if 'Submit' in request.form:
        return render_template('Orderlist.html',
                               list=orderlist)
    else:
        for k, v in request.form.items():  # k = product name v = the quantity selected
            v = int(v)
            if v > 0:
                orderlist.append(k)  # add product name to the list
                orderlist.append(v)  # add quantity selected to the list
                price = specials.find_one({'product_name': k})
                itemprice = price * v
                orderlist.append(itemprice)  # price x quantity
                totalprice = totalprice + float(v)
        return render_template('OrderPage.html')


if __name__ == '__main__':
    app.run(debug=True)