from flask import Flask, render_template, request, session, jsonify, Response
from passlib.hash import sha256_crypt
import datetime
import os, time
import paypalrestsdk
import uuid
import MySQLdb

# Author: Lee Owens
# Last Date of editing: 24/04/2018

app = Flask(__name__)
app.secret_key = os.urandom(24)
# Configurations
# Database Connection
def connect_db():
    global conn
    conn = MySQLdb.connect("Owens.mysql.pythonanywhere-services.com", "Owens", "drinksafe", "Owens$ProjectDB")
    db = conn.cursor()
    return db

# set timezone
os.environ['TZ'] = 'Europe/London'
time.tzset()

# PayPal sandbox merchant account config
paypalrestsdk.configure({
  "mode": "sandbox",  # sandbox or live
  "client_id": "ASNdXIYOglgkncwMqPFadYDjhKmlET-iFnb8JY_EuBol59DIZGcX0vYrRl3lRhw2nHKAXE5ACBMIGlP9",  # merchant account
  "client_secret": "EJ6ZHrvWB5mU_Te6RSNwIaFra6PNUzk63OY-0jmaUazUKuLlZJu1IGu5dhinmbNdWXT4TKq4-4VdV1mj"})

# Global Variables

#Used in /PreviewOrder
productnames = []
quantaties = []
prices = []
totalprice = 0.0


#List for loading orders for bar client
ordersList = []

# lockout time -> 12hours for flagged users
lockout_time = 43200

@app.route('/')
def start_app():
    return render_template('login.html')


@app.route('/UserLogin', methods=['POST','GET'])
def validate_user():
    # this function is used to handle customer login
    if session.get('user') is None:
        # open database connection
        db = connect_db()
        # get user input
        username = request.form.get('Cusername')
        password = request.form.get('Cpassword')
        # validate user and create session or return to login with invalid details
        query =  """select * from Customers where Username = %s"""
        db.execute(query, (username,))
        login_user = db.fetchall()
        # close database connection
        db.close()
        conn.close()
        if login_user:
            dbuser = login_user[0]
            db_username = dbuser[0]
            if db_username == username:
                db_userpswd = dbuser[1]
                if sha256_crypt.verify(password,db_userpswd):
                    session['user'] = username
                    return render_template('Home.html', user=session['user'])
                else:
                    return render_template('login.html', invalidUser=1)
            else:
                return render_template('login.html', invalidUser=1)
        else:
            return render_template('login.html', invalidUser=1)
    else:
        return render_template('Home.html', user=session['user'])


@app.route('/ManagerLogin', methods=['POST', 'GET'])
def handle_manager_login():
    # this function is used to handle manager login
    if session.get('manager') is None:
        # get user input
        db = connect_db()
        username = request.form.get('Busername')
        password = request.form.get('Bpassword')
        # validate user and create session or return to login with invalid details
        query =  """select * from Businesses where username = %s"""
        db.execute(query, (username,))
        login_user = db.fetchall()
        db.close()
        conn.close()
        if login_user:
            dbuser = login_user[0]
            db_username = dbuser[0]
            if db_username == username:
                db_userpswd = dbuser[1]
                if sha256_crypt.verify(password,db_userpswd):
                    session['manager'] = username
                    return render_template('ManagerHome.html', user=session['manager'])
                else:
                    return render_template('login.html',invalidUser=1)
            else:
                return render_template('login.html',invalidUser=1)
        else:
            return render_template('login.html',invalidUser=1)
    else:
        return render_template('ManagerHome.html', user=session['manager'])


@app.route('/BarLogin', methods=['POST','GET'])
def bar_login():
    # this function is used to handle bartender login
    if session.get('bar') is None:
        # get user input
        db = connect_db()
        username = request.form.get('Barusername')
        password = request.form.get('Barpassword')
        # validate user and create session or return to login with invalid details
        query =  """select * from Bar_Clients where username = %s"""
        db.execute(query, (username,))
        login_user = db.fetchall()
        db.close()
        conn.close()
        if login_user:
            dbuser = login_user[0]
            db_username = dbuser[2]
            if db_username == username:
                db_userpswd = dbuser[3]
                if sha256_crypt.verify(password,db_userpswd):
                    session['bar'] = username
                    return render_template('Bar.html', user=session['bar'])

                else:
                    return render_template('login.html',invalidUser=1)
            else:
                return render_template('login.html',invalidUser=1)
        else:
            return render_template('login.html',invalidUser=1)
    else:
        return render_template('Bar.html', user=session['bar'])


@app.route('/Logout', methods=['GET'])
def log_out():
    # this function logs out user and destroys all session variables
    session.clear()
    return render_template('login.html')


@app.route('/CreateAccount')
def display_create_account():
    return render_template('CreateAccount.html')


@app.route('/changeCustomerPassW',methods=['POST'])
def change_password():
    # this function handles customer changing their password
    global conn
    db = connect_db()
    # get user input
    cpassword = request.form.get('cpassword')
    newpswd = request.form.get('npassword')
    # validate passwor
    db.execute(""" select Password from Customers where Username='%s' """ % (session['user'],))
    password = db.fetchall()
    oldstr = str(password)
    password = oldstr.replace("(", "")
    password = password.replace(")", "")
    password = password.replace(",", "")
    password = password.replace("'", "")
    if sha256_crypt.verify(cpassword,password):
        # update user password
        hashed_password = sha256_crypt.encrypt(newpswd)
        query = """ update Customers set Password= %s where Username= %s"""
        db.execute(query, (hashed_password, session['user']))
        conn.commit()
        db.close()
        conn.close()
        return render_template('ProfilePage.html',pswdChanged=1, user=session['user'])
    else:
        db.close()
        conn.close()
        return render_template('ProfilePage.html',pswdChanged=2, user=session['user'],password=password)


@app.route('/CreateCustomer', methods=['POST'])
def create_customer():
    # this function handles user creating a new customer account
    global conn
    db = connect_db()
    customerList = []
    usernameTaken = False
    username = request.form.get('Cusername')
    db.execute("""select Username from Customers""")
    customerList = db.fetchall()
    for customer in customerList:
        oldstr = str(customer)
        uname = oldstr.replace("(", "")
        uname = uname.replace(")", "")
        uname = uname.replace(",", "")
        uname = uname.replace("'", "")
        if username == uname:
            usernameTaken = True
            break

    # check if username already exists
    if usernameTaken is False:
        # check if user has accepted terms & conditions
        acceptedTC = request.form.get('acceptTC')
        if acceptedTC:
            # get user input
            customerName = request.form.get('Cname')
            customerLocation = request.form.get('Clocation')
            password = request.form.get('Cpassword')
            hashed_password = sha256_crypt.encrypt(password)
            #insert new record into customers table
            query =  """INSERT INTO Customers (Username, Password, Name, Location, Flagged) VALUES(%s,%s,%s,%s,%s)"""
            db.execute(query, (username, hashed_password, customerName, customerLocation, int(0)))
            conn.commit()
            db.close()
            conn.close()
            return render_template('login.html', accountCreated = 1)
        else:
            db.close()
            conn.close()
            return render_template('CreateAccount.html', acceptTC = 1)
    else:
        db.close()
        conn.close()
        return render_template('CreateAccount.html', userNameTaken = 1)


@app.route('/CreateBusiness', methods=['POST'])
def create_business():
    # this function handles a user creating a new business account
    db = connect_db()
    usernameTaken = False
    businessList = []
    username = request.form.get('Busername')
    db.execute("""select Username from Businesses""")
    businessList = db.fetchall()
    for business in  businessList:
        oldstr = str(business)
        Buname = oldstr.replace("(", "")
        Buname = Buname.replace(")", "")
        Buname = Buname.replace(",", "")
        Buname = Buname.replace("'", "")
        if username == Buname:
            usernameTaken = True
            break

    # check if username already exists
    if usernameTaken == False:
        # get user input
        businessName = request.form.get('Bname')
        businessLocation = request.form.get('Blocation')
        password = request.form.get('Bpassword')
        hashed_password = sha256_crypt.encrypt(password)
        # insert new record into Businesses table
        query =  """INSERT INTO Businesses (name, location, username, password) VALUES(%s,%s,%s,%s)"""
        db.execute(query, (businessName, businessLocation, username,  hashed_password))
        conn.commit()
        stockTable = businessName + "StockTable"
        # create business stock table
        # price need to be float rather than double. Double results in sql error
        db.execute("""CREATE TABLE %s (name varchar(20), type varchar(20), price float, bar varchar(20))""" % (stockTable))
        conn.commit()
        db.close()
        conn.close()
        return render_template('login.html', accountCreated = 1)
    else:
        db.close()
        conn.close()
        return render_template('CreateAccount.html', userNameTaken = 1)


@app.route('/AddBar', methods=['POST'])
def add_new_bar_client():
    # this function handles a manager adding a new bar client to their account
    db = connect_db()
    # get user input
    name = request.form.get('Barname')
    username = request.form.get('Newusername')
    password = request.form.get('Newpassword')
    # encrypt password
    hashed_password = sha256_crypt.encrypt(password)
    # get business name
    query = """select name from Businesses where username = %s"""
    db.execute(query, (session['manager'],))
    bname = db.fetchall()
    oldstr = str(bname)
    bname = oldstr.replace("(", "")
    bname = bname.replace(")", "")
    bname = bname.replace(",", "")
    bname = bname.replace("'", "")
    # create new bar client
    query =  """INSERT INTO Bar_Clients (business_name, bar_name, username, password) VALUES(%s,%s,%s,%s)"""
    db.execute(query, (bname, name, username, hashed_password))
    conn.commit()
    db.close()
    conn.close()
    return render_template('ManagerHome.html', addsuccess = 1)


@app.route('/EditBar', methods=['POST'])
def edit_bar():
    # this function handles a manager editing one of their bar clients
    db = connect_db()
    # get user input
    username = request.form.get('username')
    current_password = request.form.get('cpassword')
    new_password = request.form.get('npassword')
    # validate password
    query =  """select * from Bar_Clients where username = %s"""
    db.execute(query, (username,))
    bar_client = db.fetchone()
    if bar_client:
        bar_password = bar_client[3]
        if sha256_crypt.verify(current_password,bar_password):
            # update password
            new_password = sha256_crypt.encrypt(new_password)
            query = """update Bar_Clients set password = %s where username = %s"""
            db.execute(query, (new_password, username))
            conn.commit()
            db.close()
            conn.close()
            return render_template('ManagerHome.html', editsucess = 1)
        else:
            db.close()
            conn.close()
            return render_template('ManagerHome.html', error= 3)
    else:
        db.close()
        conn.close()
        return render_template('ManagerHome.html', error= 3)


@app.route('/DeleteBar', methods=['POST'])
def delete_bar():
    # this function handles a manager deleting a bar client from their account & stock table
    conn = MySQLdb.connect("Owens.mysql.pythonanywhere-services.com", "Owens", "drinksafe", "Owens$ProjectDB")
    db = conn.cursor()
    # get user input
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    # check if confirmed password matches password
    if password == confirm_password:
        # validate password
        query = """select * from Bar_Clients where username = %s"""
        db.execute(query, (username,))
        bar = db.fetchone()
        if bar:
            bar_password = bar[3]
            if sha256_crypt.verify(password,bar_password):
                # get business name
                query = """select name from Businesses where username = %s"""
                db.execute(query, (session['manager'],))
                businessName = db.fetchall()
                businessName = str(businessName)
                oldstr = businessName
                businessName = oldstr.replace("(", "")
                businessName = businessName.replace(")", "")
                businessName = businessName.replace(",", "")
                businessName = businessName.replace("'", "")
                stockTable = businessName+"StockTable"

                # get bar name
                query = """select bar_name from Bar_Clients where username = %s"""
                db.execute(query, (username,))
                barname = db.fetchall()
                oldstr = str(barname)
                barname = oldstr.replace("(", "")
                barname = barname.replace(")", "")
                barname = barname.replace(",", "")
                barname = barname.replace("'", "")

                # delte all sotck in stock table which is associated with this bar
                db.execute("""delete from %s where bar = '%s'""" % (stockTable, barname))
                conn.commit()

                # delete bar client
                query = """delete from Bar_Clients where username = %s and password = %s"""
                db.execute(query, (username, password))
                conn.commit()
                db.close()
                conn.close()
                return render_template('ManagerHome.html', deletesuccess = 1)
            else:
                db.close()
                conn.close()
                return render_template('ManagerHome.html', error = 3)
        else:
            db.close()
            conn.close()
            return render_template('ManagerHome.html', error = 3)
    else:
        db.close()
        conn.close()
        return render_template('ManagerHome.html', error = 2)


@app.route('/AddStock', methods=['POST'])
def add_stock():
    # this function handles a manager adding a new stock item to their stock table
    db = connect_db()
    # get user input
    name = request.form.get('newS')
    item_price = request.form.get('itemP')
    price = float(item_price)
    item_type = request.form['options']
    item_bar = request.form.get('itemB')
    # get business name
    query = """select name from Businesses where username = %s"""
    db.execute(query, (session['manager'],))
    bname = db.fetchall()
    oldstr = str(bname)
    bname = oldstr.replace("(", "")
    bname = bname.replace(")", "")
    bname = bname.replace(",", "")
    bname = bname.replace("'", "")
    stockTable = bname + "StockTable"
    # insert new stock item into business stock table
    db.execute("""insert into %s (name, type, price, bar) values ('%s', '%s', %s, '%s')""" % (stockTable,name, item_type, price, item_bar))
    conn.commit()
    db.close()
    conn.close()
    return render_template('ManagerHome.html', addStock = 1)


@app.route('/EditStock', methods=['POST'])
def edit_stock():
    # this function handles a manage editing a stock item in their stock table
    db = connect_db()
    # get user input
    name = request.form.get('sName')
    bar = request.form.get('sBar')
    new_price = request.form.get('itemP')
    new_price = float(new_price)
    # get business name
    query = """select name from Businesses where username = %s"""
    db.execute(query, (session['manager'],))
    bname = db.fetchall()
    oldstr = str(bname)
    bname = oldstr.replace("(", "")
    bname = bname.replace(")", "")
    bname = bname.replace(",", "")
    bname = bname.replace("'", "")
    stockTable = bname + "StockTable"
    # update stock pirce
    db.execute("""update %s set price = %s where name = '%s' and bar = '%s' """ % (stockTable, new_price, name, bar))
    conn.commit()
    row_affected = db.rowcount
    if row_affected > 0:
        db.close()
        conn.close()
        return render_template('ManagerHome.html', editStock = 1)
    else:
        db.close()
        conn.close()
        return render_template('ManagerHome.html', error = 4)


@app.route('/DeleteStock', methods=['POST'])
def delete_stock():
    # this function handles a manage deleting a stock item from their stock table
    db = connect_db()
    # get user input
    name = request.form.get('iName')
    bar = request.form.get('iBar')
    # get business name
    query = """select name from Businesses where username = %s"""
    db.execute(query, (session['manager'],))
    bname = db.fetchall()
    oldstr = str(bname)
    bname = oldstr.replace("(", "")
    bname = bname.replace(")", "")
    bname = bname.replace(",", "")
    bname = bname.replace("'", "")
    stockTable = bname + "StockTable"
    # delete stock item from business stock table
    db.execute("""delete from %s where bar = '%s' and name = '%s'""" % (stockTable, bar, name))
    conn.commit()
    row_affected = db.rowcount
    if row_affected > 0:
        db.close()
        conn.close()
        return render_template('ManagerHome.html', deleteStock = 1)
    else:
        db.close()
        conn.close()
        return render_template('ManagerHome.html', error = 4)


@app.route('/ViewSales', methods=['GET'])
def view_sales_chart():
    # this function displays visual charts for the manager
    # lables for chart
    barsList = []
    productList = []
    # values for chart
    orderTotals = []
    bought_total = []
    number = 0.0

    db = connect_db()
    # get business name
    query = """select name from Businesses where username = %s"""
    db.execute(query, (session['manager'],))
    bname = db.fetchall()
    oldstr = str(bname)
    bname = oldstr.replace("(", "")
    bname = bname.replace(")", "")
    bname = bname.replace(",", "")
    bname = bname.replace("'", "")

    # get bar clients associated to business
    query = """select bar_name from Bar_Clients where business_name = %s"""
    db.execute(query, (bname,))
    bars = db.fetchall()
    for bar in bars:
        oldstr = str(bar)
        bar = oldstr.replace("(", "")
        bar = bar.replace(")", "")
        bar = bar.replace(",", "")
        bar = bar.replace("'", "")
        barsList.append(bar)

    for bar in barsList:
        # get total amount of money brought in from each bar
        query = """select total from Orders where business = %s and bar = %s"""
        db.execute(query, (bname,bar))
        totals = db.fetchall()
        for total in totals:
            oldstr = str(total)
            total = oldstr.replace("(", "")
            total = total.replace(")", "")
            total = total.replace(",", "")
            total = total.replace("'", "")
            number = number + float(total)
        orderTotals.append(number)
        number = 0.0

    stockTable = bname + "StockTable"
    db.execute("""select * from %s""" % (stockTable))
    products = db.fetchall()
    for product in products:
        productList.append(product[0])
        bought_total.append(product[4])

    # conn.commit()
    db.close()
    conn.close()

    return render_template('viewSales.html', Blist = barsList, Bartotals = orderTotals, name = bname, pList = productList, btotal = bought_total)


@app.route('/CustomerOH', methods=['GET'])
def customer_OH():
    # this function displays all orders associated with the customer
    db = connect_db()
    orderHistList = []
    # get orders associated with the customer from orders table
    db.execute("""select * from Orders where customer='%s'""" % (session['user'],))
    orders = db.fetchall()
    db.close()
    conn.close()
    for order in orders:
        orderHistList.append(order)
    return render_template('OrderHistory.html', orders=orderHistList)


@app.route('/ProfilePage',  methods=['GET'])
def profile_page():
    return render_template('ProfilePage.html', user = session['user'])


@app.route('/SearchBusinessInCustomerArea',  methods=['GET'])
def search_B_InArea():
    # This function is to search for businesses in the customers area which is stored in the database
    db = connect_db()
    username = session['user']
    Blist = []
    # get customer area from their account
    query =  """select Location from Customers where Username = %s"""
    db.execute(query, (username,))
    userArea = db.fetchall()
    customerArea = userArea[0]
    # get all businesses that are in that location
    query =  """SELECT name FROM Businesses WHERE location = %s"""
    db.execute(query, (customerArea))
    businessesList = db.fetchall()
    db.close()
    conn.close()
    if  businessesList:
        # strip string of unwanted characters and append to Blist
        for business in businessesList:
            oldstr = str(business)
            name = oldstr.replace("(", "")
            name = name.replace(")", "")
            name = name.replace(",", "")
            name = name.replace("'", "")
            Blist.append(name)
        return render_template('BusinessList.html', businessesList = Blist)
    else:
        return render_template('Home.html', noneInArea = 1)


@app.route('/SearchBusinessInCustomerLocation',  methods=['POST','GET'])
def search_B_InLocation():
    if request.method == 'GET':
        return render_template('Home.html')
    else:
        # this function is to search for businesses in the location specified by the customer
        db = connect_db()
        Blist = []
        # get user input
        location = request.form.get('location')
        # get businesses from specified location
        query =  """SELECT name FROM Businesses WHERE location = %s"""
        db.execute(query, (location,))
        businessesList = db.fetchall()
        db.close()
        conn.close()
        if  businessesList:
            # strip string of unwanted characters and append to Blist
            for business in businessesList:
                oldstr = str(business)
                name = oldstr.replace("(", "")
                name = name.replace(")", "")
                name = name.replace(",", "")
                name = name.replace("'", "")
                Blist.append(name)
            return render_template('BusinessList.html', businessesList = Blist)
        else:
            return render_template('Home.html', noneInLocation = 1)


@app.route('/BarList', methods=['POST','GET'])
def get_products():
    # this function gets all bars associated with the business selected by the customer
    barList = []
    if request.method == 'POST':
        db = connect_db()
        # get customers selection
        business = request.form['business']
        business = str(business)
        # used in /GetStock to get the stock from the business selected
        session['stockTable'] = business + "StockTable"
        # get associated bars
        db.execute("""SELECT bar_name FROM Bar_Clients WHERE business_name = '%s'""" % (business))
        bars = db.fetchall()
        db.close()
        conn.close()
        session['business'] = business
        # strip string of unwanted characters and append to barList
        for bar in bars:
            oldstr = str(bar)
            name = oldstr.replace("(", "")
            name = name.replace(")", "")
            name = name.replace(",", "")
            name = name.replace("'", "")
            barList.append(name)
        session['BList'] =  barList

        return render_template('BarsList.html', barsList = barList)
    else:
        return render_template('BarsList.html', barsList = session['BList'])


@app.route('/GetCategories', methods=['POST', 'GET'])
def get_stock_types():
    # this function is used to get the categories of products which are listed for the selected bar
    categoryList = []
    if request.method == 'POST':
        db = connect_db()
        # get customer selection
        bar = request.form['bar']
        bar = str(bar)
        stockTable = session['stockTable']
        session['selectedBar'] = bar
        # get categories
        db.execute("""select type from %s where bar ='%s'""" % (stockTable, bar))
        stocks = db.fetchall()
        db.close()
        conn.close()
        # strip string of unwanted characters and append to categoryList
        for item in stocks:
            oldstr = str(item)
            stype = oldstr.replace("(", "")
            stype = stype.replace(")", "")
            stype = stype.replace(",", "")
            stype = stype.replace("'", "")
            if len(categoryList) == 0:
                categoryList.append(stype)
            else:
                for category in categoryList:
                    if category == stype:
                        break
                else:
                    categoryList.append(stype)

        session['cList'] = categoryList
        return render_template('CategoryList.html', sList = categoryList)
    else:
        return render_template('CategoryList.html', sList = session['cList'] )


@app.route('/GetStock', methods=['POST', 'GET'])
def get_stock():
    # this functionality gets all the stock under the category selected by the customer
    db = connect_db()
    itemlist = []
    # create item object
    item = {"product": '', "price":0}
    # get selected category
    stock_type = request.form['type']
    stockTable = session['stockTable']
    bar = session['selectedBar']
    # get stock which matches the business and bar that has been selected
    db.execute("""select * from %s where bar ='%s' and type='%s'""" % (stockTable, bar, stock_type))
    items = db.fetchall()
    db.close()
    conn.close()
    for product in items:
        item['product'] = product[0]
        item['price'] = product[2]
        itemlist.append(item.copy())
    return render_template('ProductsList.html', itemsList = itemlist)


@app.route('/HandleOrder', methods=['POST', 'GET'])
def prepare_order_preview():
    # this function handels creating the customers order
    global productnames
    global quantaties
    global prices
    global totalprice
    global startHour
    global endHour

    if 'Submit' in request.form:
        # create order id & order session
        order_id = str(uuid.uuid4())
        order_id = order_id[:len(order_id)//3]
        # display order to customer
        session['order'] = order_id
        session['orderlist'] = productnames
        session['ordertotal'] = float(totalprice)
        return render_template('Orderlist.html',
                                products=productnames, quantaties=quantaties, prices=prices, total=totalprice,
                                orderID=session['order'])
    else:
        db = connect_db()
        locked = False
        # check if user has been flagged before allowing them to start creating an order
        db.execute("""select * from FlaggedUsers where customer_username='%s'""" % (session['user'],))
        fuser = db.fetchone()
        if fuser:
            # if the user has been flagged, check if the 12 hour period has passed
            # get time user was flagged
            flagged_datetime = fuser[1]
            oldstr = str(flagged_datetime)
            flagged_datetime = oldstr.replace("(", "")
            flagged_datetime = flagged_datetime.replace(")", "")
            flagged_datetime = flagged_datetime.replace(",", "")
            flagged_datetime = flagged_datetime.replace("'", "")
            now = datetime.datetime.now()
            dateTime =  now.strftime("%Y-%m-%d %H:%M")
            # parse to time objects for comparison
            flagged_datetime= datetime.datetime.strptime(flagged_datetime, "%Y-%m-%d %H:%M")
            dateTime= datetime.datetime.strptime(dateTime, "%Y-%m-%d %H:%M")
            elapsedTime = (dateTime - flagged_datetime).total_seconds()
            if  elapsedTime > lockout_time:
                # if period has passed delete this user from table
                db.execute("""delete from FlaggedUsers where customer_username='%s'""" % (session['user'],))
                conn.commit()
                locked = False
            else:
                db.close()
                conn.close()
                locked = True
                return render_template('Home.html', lockedOut = 1, passedTime=elapsedTime)

        if locked == False:
            # if user hasn't been flagged allow them to start creating order
            db.execute("""select * from %s where bar ='%s'""" % (session['stockTable'], session['selectedBar']))
            category = db.fetchall()
            db.close()
            conn.close()
            # get items selected, quantity selected and their prices
            for k, v in request.form.items():
                value = int(v)
                if value > 0:
                    productnames.append(k)
                    quantaties.append("X"+str(value))
                    for product in category:
                        if product[0] == k:
                            price = product[2]
                            break
                    itemprice = price * value
                    prices.append(itemprice)
                    # append to order total
                    totalprice = totalprice + float(itemprice)
            return render_template('CategoryList.html', sList = session['cList'])


@app.route('/CancelOrder', methods=['GET'])
def cancel_order():
    # this function handles the customer canceling their order
    global productnames
    global quantaties
    global prices
    global totalprice

    # clear all session variables associated with the order
    productnames.clear()
    quantaties.clear()
    prices.clear()
    totalprice = 0
    session.pop('order', None)
    return render_template('Home.html', user=session['user'])


@app.route('/payment', methods=['POST'])
def payment():
    # this function handels creating the paypal payment
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
    # this function executes the paypal payment
    payment = paypalrestsdk.Payment.find(request.form['paymentID'])

    if payment.execute({'payer_id': request.form['payerID']}):
        # if payment is successful insert new order into the database
        db = connect_db()
        global quantaties
        # create order time
        now = datetime.datetime.now()
        dateTime = now.strftime("%Y-%m-%d %H:%M")
        orderlist = session['orderlist']
        olist = ""
        add_item = ""
        i=0
        for item in orderlist:
            add_item = str(item)
            olist+=add_item
            olist+=quantaties[i]
            olist+=","
            i=i+1
        query = """insert into Orders (order_id,business,bar,customer,items_purchased,total,accepted,ready,completed,
                   user_flagged, DateTime) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        db.execute(query, (session['order'],session['business'],session['selectedBar'],session['user'],olist,session['ordertotal'],0,0,0,0, dateTime))
        conn.commit()
        db.close()
        conn.close()
        return render_template('waiting.html')
    else:
        print(payment.error)


@app.route('/waiting', methods=['GET'])
def display_waiting_page():
    # this function displays message when customer has been directed to the waiting page
    message = "Waiting for order to be accepted"
    return render_template('waiting.html', refresh = 1, message=message)


@app.route('/checkOrder', methods=['GET'])
def checkOrder():
    # This function is for checking the order status of a customers order
    db = connect_db()
    # get order from database
    db.execute("""select * from Orders where order_id ='%s'""" % (session['order'],))
    order = db.fetchone()
    orderID = order[0]
    oldstr = str(orderID)
    ID = oldstr.replace("(", "")
    ID = ID.replace(")", "")
    ID = ID.replace(",", "")
    ID =ID.replace("'", "")
    if ID == session['order']:
        accepted = order[6]
        # check if the customers order has been accepted
        if accepted == 1:
            db.close()
            conn.close()
            return Response("Your order has been accepted")
        else:
            db.close()
            conn.close()
            return Response("waiting....")


@app.route('/orderAccepted', methods=['GET'])
def orderAccepted():
    # this function is to clear all session variables associated with the order
    global productnames
    global quantaties
    global prices
    global totalprice

    productnames.clear()
    quantaties.clear()
    prices.clear()
    totalprice = 0
    return render_template('orderAccepted.html', orderid=session['order'])


@app.route('/orderCollected', methods=['GET'])
def orderCollected():
    return render_template('Home.html', user=session['user'])


@app.route('/load', methods=['GET'])
def load():
    return render_template('loadOrders.html')


@app.route('/loadOrders', methods=['GET'])
def load_orders():
    # this function gets and displays all orders for the bar client
    db = connect_db()
    global ordersList
    ordersList.clear()
    # get bar name
    db.execute("""select bar_name from Bar_Clients where username ='%s'""" % (session['bar'],))
    bar = db.fetchone()
    bar = str(bar)
    oldstr = str(bar)
    bar = oldstr.replace("(", "")
    bar = bar.replace(")", "")
    bar = bar.replace(",", "")
    bar = bar.replace("'", "")
    # get all orders made to this bar which have not been completed or customer has not been flagged
    db.execute("""select * from Orders where completed = 0 and user_flagged = 0 and bar='%s'""" % (bar,))
    orders = db.fetchall()
    db.close()
    conn.close()
    for order in orders:
        ordersList.append(order)
    return render_template('loadOrders.html', user=session['bar'], orders=ordersList)


@app.route('/orderStatus', methods=['POST'])
def update_order():
    # this function is to handle the bartender processing the order
    db = connect_db()
    global ordersList
    # get bartender selection
    order_selected = request.form['choice']
    # if bartender has selected accept order, update order to accepted
    if order_selected:
        if 'Accept Order' in request.form:
            db.execute("""update Orders set accepted=1 where order_id='%s'""" % (order_selected,))
            conn.commit()
            db.close()
            conn.close()
            return render_template('loadOrders.html', user=session['bar'], orders=ordersList)

        # if bartender has selected complete order, update order to completed
        elif 'Order Completed' in request.form:
            db.execute("""update Orders set completed=1 where order_id='%s'""" % (order_selected,))
            conn.commit()
            # reload orders for bar client
            ordersList.clear()
            db.execute("""select bar_name from Bar_Clients where username ='%s'""" % (session['bar'],))
            bar = db.fetchone()
            bar = str(bar)
            oldstr = str(bar)
            bar = oldstr.replace("(", "")
            bar = bar.replace(")", "")
            bar = bar.replace(",", "")
            bar = bar.replace("'", "")
            # reload orders for bar client
            db.execute("""select * from Orders where completed = 0 and user_flagged = 0 and bar='%s'""" % (bar,))
            orders = db.fetchall()
            db.close()
            conn.close()
            for order in orders:
                ordersList.append(order)
            return render_template('loadOrders.html', user=session['bar'], orders=ordersList)

        # if bartender has selected report customer update customer to flagged
        else:
            db.execute("""update Orders set user_flagged=1 where order_id='%s'""" % (order_selected,))
            conn.commit()
            db.execute("""select customer from Orders where order_id='%s' and user_flagged=1""" % (order_selected,))
            user_flagged = db.fetchone()
            oldstr = str(user_flagged)
            user_flagged = oldstr.replace("(", "")
            user_flagged = user_flagged.replace(")", "")
            user_flagged = user_flagged.replace(",", "")
            user_flagged = user_flagged.replace("'", "")
            # get time of customer being flagged
            now = datetime.datetime.now()
            time = now.strftime("%Y-%m-%d %H:%M")
            # insert customer into flagged users table
            query = """insert into FlaggedUsers (customer_username, time) values (%s,%s)"""
            db.execute(query,(user_flagged,time))
            conn.commit()
            # reload orders for bar client
            ordersList.clear()
            db.execute("""select bar_name from Bar_Clients where username ='%s'""" % (session['bar'],))
            bar = db.fetchone()
            bar = str(bar)
            oldstr = str(bar)
            bar = oldstr.replace("(", "")
            bar = bar.replace(")", "")
            bar = bar.replace(",", "")
            bar = bar.replace("'", "")
            db.execute("""select * from Orders where completed = 0 and user_flagged = 0 and bar='%s'""" % (bar,))
            orders = db.fetchall()
            db.close()
            conn.close()
            for order in orders:
                ordersList.append(order)
            return render_template('loadOrders.html', user=session['bar'], orders=ordersList)
    else:
        db.close()
        conn.close()
        return render_template('loadOrders.html', notSelected = 1)


if __name__ == '__main__':
    app.run(debug=True)
