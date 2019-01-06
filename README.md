# mobilPy

mobilPy helps you with everything you need to implement [mobilPay](https://www.mobilpay.ro/public/en/)'s online payment solution.
Steps:
- create an account
- get approved
- create a merchant
- download keys (private and public)
- copy the signature (just a string)

*NOTE* You will have two private keys: for testing and production. The public key is the same.

## Install
To install the library, run:
```sh
pip install mobilpy
```

## Usage
```python
from mobilpy import MobilPay

# the signature for your account
signature = 'DLAN-1R5V-19EN-XXXX-NFJA'
# the path to the public key
public_key = "./sandbox.DLAN-1R5V-19EN-XXXX-NFJA.public.cer"
# the private_key
private_key = "./sandbox.DLAN-1R5V-19EN-XXXX-NFJA.private.key"

client = MobilPay(signature=signature, public_key=public_key, private_key=private_key)

# optional dict containing details about the customer
# if they are sent, the customer will have a short checkout by skipping the second step in the payment flow
billing_details = {
    "first_name": "",
    "last_name": "",
    "address": "",
    "phone": "",
    "email": ""
}
# optional dict with details that you would need internally
# these are returned when the webhook is called
params = {
    "subscription_id": "",
    "basket_id": "",
    etc.
}

options = {
    "order_id": "" # int/string, max 64 length
    "currency": "RON", # string, RON or other
    "amount": 1, # float, between 0.10 and 99999
    "customer_id": "", # int/string
    "details": "",  # string, description for this transaction
    "billing": billing_details, # dict, OPTIONAL
    "params": params, # dict, OPTIONAL,
    
    # the webhook where the response from mobilPay will be sent
    "confirm_url": "",
    # the url where the user will be redirected
    "return_url": ""
}
response = client.create_payment_data(**options)
```
The `response` is an dict that has two keys: `env_key` and `data`.
These need to be used in the front end and make the request to mobilPay.

For example, the HTML might look like this:
```html
<form action="http://sandboxsecure.mobilpay.ro" method="post">
    <input type="hidden" name="env_key" value="{{ env_key }}">
    <input type="hidden" name="data" value="{{ data }}">
    
    <input type="submit" value="Send">
</form>
```

The POST urls for the form are:
- testing: `http://sandboxsecure.mobilpay.ro`
- production: `https://secure.mobilpay.ro`

## Webhook
mobilPay will make a `POST` request to the url you set as `confirm_url`.
mobilPy has methods to help you parse it and offer a response.

```python
post = # get the post data
env_key = post.get('env_key')
data = post.get('data')

client = MobilPay(signature=signature, public_key=public_key, private_key=private_key)

request_xml = client.decrypt_message(env_key, data)
request_object = client.parse_request_xml(request_xml)

# do some magic
```
In order to check if the transaction was successful you need to check `error_code` AND `action`:
```python
transaction_successful = request_object.get('error_code') == '0' and request_object.get('action') == 'confirmed'
if transaction_successful:
  # everything is ok
```
## Creating a response
You need to let mobilPay know if everything is ok on your end or if something weird happened.
If everything is ok you can create a response like this:
```python
message = "All good captain"
response_xml = client.create_reponse(message=message)
```
If you had an error:
```python
# message that will help you debug. it will appear in your dashboard
message = "Everything is on fire"
# this can be "1" (temporary error) or "2" (permanent error)
error_type = "1"
# your internal error code. a number maybe. OPTIONAL
error_code = ''
response_xml = client.create_reponse(message=message)
```
The response doesn't need to be encrypted. Just respond with the xml.

### Crediting
If a transaction was credited from the Dashboard, mobilPay will make a new webhook `POST`. You can check for that:
```python
# if the transaction was credited from mobilpay
if request_object.get('action') == 'credit':
  # do something
  # return a reponse
```


# TODO
Some things that still need to be done
- tests
- too many dependencies: pyopenssl and pycrypto
- migrate to pycryptodome (pycrypto is not maintained)
- add support for: instalements, <recurrence>, 
- maybe add prefilled credit card data payments?


### Disclaimer
This library is not associated in any way with mobilPay