
import urllib
import base64

from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree, fromstring
from io import BytesIO

from OpenSSL import crypto

from Crypto.Cipher import PKCS1_v1_5, ARC4
from Crypto.PublicKey import RSA
from Crypto import Random

from logging import debug, exception


# TODO:
# remove openssl and crypto deps, only use one
# migrate to pycryptodome
# add instalement
# add <recurrence>
# add prefilled credit card data payments?

class MobilPay(object):

    def __init__(self, *args, **kwargs):

        signature = kwargs.get('signature')

        public_key = kwargs.get('public_key')
        private_key = kwargs.get('public_key')

        if not signature:
            raise Exception('Missing signature argument')

        if not public_key:
            raise Exception('Missing public_key argument')

        if not private_key:
            raise Exception('Missing private_key argument')

        # read public key
        # parse the public key and save it as a string
        with open(public_key, "r") as file:
            pub_key = crypto.load_certificate(crypto.FILETYPE_PEM, file.read()).get_pubkey()
            public_key_string = crypto.dump_publickey(crypto.FILETYPE_PEM, pub_key)

        # read private key
        with open(private_key, "r") as file:
            private_key_string = file.read()

        self.signature = signature
        self.public_key = public_key_string
        self.private_key = private_key_string

        # a flag to keep track if we are in developement mode
        # if True => more logging
        self.developement = kwargs.get('developement', False)

    def create_request_xml(self, **kwargs):

        order_id = kwargs.get('order_id')
        order_type = kwargs.get('order_type', 'card')
        timestamp = kwargs.get('timestamp')


        amount = kwargs.get('amount')
        currency = kwargs.get('currency', 'RON')
        customer_id = kwargs.get('customer_id')

        details = kwargs.get('details')

        billing = kwargs.get('billing')

        params = kwargs.get('params', {})

        confirm_url = kwargs.get('confirm_url')
        return_url = kwargs.get('return_url')

        order = Element('order', type=order_type, id=order_id, timestamp=timestamp)

        signature = SubElement(order, 'signature')
        signature.text = self.signature

        invoice = SubElement(order, 'invoice', currency=currency, amount=str(amount), customer_type="2", customer_id=str(customer_id))
        details_el = SubElement(invoice, 'details')
        details_el.text = details

        if billing:
            first_name = billing.get('first_name', '')
            last_name = billing.get('last_name', '')
            address = billing.get('address', '')
            email = billing.get('email', '')
            phone = billing.get('phone', '')

            contact_info = SubElement(invoice, 'contact_info')
            billing = SubElement(contact_info, 'billing', type="person")

            first_name_el = SubElement(billing, 'first_name')
            first_name_el.text = first_name
            last_name_el = SubElement(billing, 'last_name')
            last_name_el.text = last_name
            address_el = SubElement(billing, 'address')
            address_el.text = address
            email_el = SubElement(billing, 'email')
            email_el.text = email
            phone_el = SubElement(billing, 'mobile_phone')
            phone_el.text = phone


        # if we have other params to add
        if params:
            params = SubElement(order, 'params')

            def add_other_param(param_name, param_value):
                if param_name and param_value:
                    param = SubElement(params, 'param')
                    name = SubElement(param, 'name')
                    name.text = param_name
                    value = SubElement(param, 'value')
                    value.text = str(param_value)

            for param in params:
                add_other_param(key, params[key])

        url = SubElement(order, 'url')
        confirm = SubElement(url, 'confirm')
        confirm.text = confirm_url

        return_url_el = SubElement(url, 'return')
        return_url_el.text = return_url

        parent_element = ElementTree(order)

        virtual_file = BytesIO()
        parent_element.write(virtual_file, encoding='utf-8', xml_declaration=True) 

        return virtual_file.getvalue()

    def encrypt_message(self, xml_message):

        key = RSA.importKey(self.public_key)
        cipher = PKCS1_v1_5.new(key)
        session_key = Random.get_random_bytes(16)

        encrypted_session_key = cipher.encrypt(session_key)
        env_key = base64.b64encode(encrypted_session_key)

        rc4_cipher = ARC4.new(session_key)
        encrypted_data = rc4_cipher.encrypt(xml_message)
        data = base64.b64encode(encrypted_data)

        return {
            'env_key': env_key,
            'data': data
        }

    def decrypt_message(self, env_key, data):
        """
        Used to decrypt data from mobilpay
        """

        if not env_key or not data:
            raise Exception('Arguments missing.')

        key = RSA.importKey(self.private_key)

        env_key = urllib.unquote(env_key).decode('utf8')
        data = urllib.unquote(data).decode('utf8')

        try:
            env_key = base64.b64decode(env_key)
            data = base64.b64decode(data)
            
            cipher = PKCS1_v1_5.new(key)

            sentinel = []
            session_key = cipher.decrypt(env_key, sentinel)

            rc4_cipher = ARC4.new(session_key)

            xml_data = rc4_cipher.decrypt(data)

            # TODO: add xml validation
            # schema_root = etree.XML(xml_data)
            # schema = etree.XMLSchema(schema_root)
            # parser = etree.XMLParser(schema=schema)

            return xml_data
        except Exception as e:
            if self.developement:
                exception(e)

            raise Exception('Could not decrypt message.')

    @staticmethod
    def parse_wenhook_request(xml):

        data = {}

        root = fromstring(xml)
        data['order_id'] = root.attrib.get('id', '')

        invoice = root.findall('invoice')[0]
        data['customer_id'] = invoice.attrib.get('customer_id')

        # params that we sent
        params = root.findall('params')[0]

        data['params'] = {}
        for param in params.findall('param'):
            name = param.findall('name')[0].text
            value = param.findall('value')[0].text
            data['params'][name] = value

        # the response from them
        mobilpay = root.findall('mobilpay')[0]
        data['crc'] = mobilpay.attrib.get('crc')

        for child in mobilpay:

            if child.tag != 'customer':
                data[child.tag] = child.text

            if child.tag == 'error':
                data['error'] = {
                    "code": child.attrib.get('code'),
                    "message": child.text
                }

        return data

    @staticmethod
    def create_webhook_reponse(**kwargs):

        message = kwargs.get('message')
        crc = kwargs.get('crc')

        error_type = kwargs.get('error_type', '')
        error_code = kwargs.get('error_code', '')

        crc_element = Element('crc')
        crc_element.text = message if message else crc

        if error_type:
            crc_element.set('error_type', error_type)

        if error_code:
            crc_element.set('error_code', error_code)

        parent_element = ElementTree(crc_element)

        virtual_file = BytesIO()
        parent_element.write(virtual_file, encoding='utf-8', xml_declaration=True)

        xml_message = virtual_file.getvalue()

        return xml_message
        # return MobilPay.encrypt_message(xml_message)

    def create_payment_data(self, **kwargs):
        """
        Used to create the env_key and data to make a mobilpay request
        """

        order_id = kwargs.get('order_id')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        currency = kwargs.get('currency', 'RON')
        amount = kwargs.get('amount')
        customer_id = kwargs.get('customer_id')

        # the description of the payment
        details = kwargs.get('details')

        billing = kwargs.get('billing', {})

        params = kwargs.get('params', {})

        # urls
        confirm_url = kwargs.get('confirm_url')
        return_url = kwargs.get('return_url')

        if not order_id or not amount or not customer_id or not details or not confirm_url or not return_url:
            if self.developement:
                debug('Arguments for create_payment_data', kwargs)

            raise Exception("Can't create mobilpay request with missing args.")

        order_id = str(order_id)
        if len(order_id) > 64:
            raise Exception('order_id should not have more than 64 characters.')

        args = {
            # order tag
            "order_id": order_id,
            "order_type": "card",
            "timestamp": timestamp,

            # invoice tag
            "amount": amount, 
            "currency": currency,
            "customer_id": customer_id,

            "details": details,

            # other params
            "params": params,

            # urls
            "confirm_url": confirm_url,
            "return_url": return_url
        }

        if billing:
            args['billing'] = {
                "first_name": billing.get('first_name', ''),
                "last_name": billing.get('last_name', ''),
                "address": billing.get('address', ''),
                "phone": billing.get('phone', ''),
                "email": billing.get('email', '')
            }

        # create the xml
        xml_message = self.create_request_xml(**args)

        if self.developement:
            debug(xml_message)

        return self.encrypt_message(xml_message)
