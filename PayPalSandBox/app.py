from flask import Flask, render_template, jsonify, request
import os
import paypalrestsdk

paypalrestsdk.configure({
  "mode": "sandbox",  # sandbox or live
  "client_id": "ASNdXIYOglgkncwMqPFadYDjhKmlET-iFnb8JY_EuBol59DIZGcX0vYrRl3lRhw2nHKAXE5ACBMIGlP9",  # merchant account
  "client_secret": "EJ6ZHrvWB5mU_Te6RSNwIaFra6PNUzk63OY-0jmaUazUKuLlZJu1IGu5dhinmbNdWXT4TKq4-4VdV1mj"})

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/')
def display_form() -> 'html':
    return render_template('index.html')


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