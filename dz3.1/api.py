#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from scoring import get_interests, get_score
from store import Store, RedisStore

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field:
    empty_values = (None, '', [], (), {})

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        if value is None and self.required:
            raise ValueError("This field is required")
        if value in self.empty_values and not self.nullable:
            raise ValueError("This field cannot be empty")

    def run_validators(self, value):
        return value


class CharField(Field):

    def run_validators(self, value):
        super().validate(value)
        if not value and value != 0:
            return
        if not isinstance(value, str):
            raise ValueError('Invalid value type')
        return value


class ArgumentsField(Field):

    def run_validators(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, dict):
            raise ValueError("This field must be a dictionary")
        return value


class EmailField(CharField):

    def run_validators(self, value):
        super().validate(value)
        if not value:
            return
        if '@' not in value:
            raise ValueError('Invalid email format')
        return value


class PhoneField(Field):
    def run_validators(self, value):
        super().validate(value)
        if not value:
            return value
        if not isinstance(value, (str, int)):
            raise ValueError("This field must be a number or a string")
        if not str(value)[0] == "7":
            raise ValueError('The first digit should be 7')
        if len(str(value)) < 11:
            raise ValueError('The number of digits must be 11')
        return str(value)


class DateField(CharField):
    DATE_FORMAT = "%d.%m.%Y"

    def run_validators(self, value):
        super().validate(value)
        if value is None:
            return
        try:
            df = datetime.datetime.strptime(value, self.DATE_FORMAT)
            return df
        except:
            raise ValueError("Value is not a date")

    def to_str(self, value):
        return datetime.datetime.strftime(value, self.DATE_FORMAT)

    def strptime(self, value, format):
        return datetime.datetime.strptime(value, format).date()


class BirthDayField(DateField):
    def run_validators(self, value):
        super().validate(value)
        if value is None:
            return
        birthday = super(BirthDayField, self).run_validators(value)
        diff = datetime.datetime.now() - birthday
        if (diff.days / 365) > 70:
            raise ValueError("Age is greater then 70")
        return birthday


class GenderField(Field):
    def run_validators(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, int):
            raise ValueError('Invalid field type')
        if value not in [UNKNOWN, MALE, FEMALE]:
            raise ValueError('Invalid field value')
        return value


class ClientIDsField(Field):

    def run_validators(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise ValueError('This field must be a list type')
        for clientId in value:
            if not isinstance(clientId, int) or clientId < 0:
                raise ValueError('ClientId must be positive integer type')
        return value


class RequestMeta(type):
    def __new__(cls, name, bases, attributes):
        fields = {}
        for key, val in attributes.items():
            if isinstance(val, Field):
                if val not in val.empty_values:
                    fields[key] = val

        cls = super().__new__(cls, name, bases, attributes)
        cls.fields = fields
        return cls


class Request(metaclass=RequestMeta):

    def __init__(self, params):
        self.errors = []
        for name, field in self.fields.items():
            value = params[name] if name in params else None
            try:
                cleaned_value = field.run_validators(value)
                setattr(self, name, cleaned_value)
            except ValueError as e:
                self.errors.append('field "{}": {}'.format(name, str(e)))

    def is_valid(self):
        return not self.errors


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, request_params):
        super().__init__(request_params)

        if not self.is_valid():
            return

        for first, second in self.get_valid_pairs():
            if getattr(self, first) is not None and getattr(self,
                                                            second) is not None:
                return
        self.errors.append('No valid pairs')

    @staticmethod
    def get_valid_pairs():
        return [
            ['phone', 'email'],
            ['first_name', 'last_name'],
            ['gender', 'birthday']
        ]

    def get_not_empty_fields(self):
        result = []
        for name in self.fields:
            if getattr(self, name) is not None:
                result.append(name)
        return result


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class OnlineScoreHandler:

    def process_request(self, request, context, store):
        r = OnlineScoreRequest(request.arguments)
        if not r.is_valid():
            return r.errors, INVALID_REQUEST

        if request.is_admin:
            score = 42
        else:
            score = get_score(store, r.phone, r.email, r.birthday, r.gender,
                              r.first_name, r.last_name)
        context["has"] = r.get_not_empty_fields()

        return {"score": float(score)}, OK


class ClientsInterestsHandler:

    def process_request(self, request, context, store):
        r = ClientsInterestsRequest(request.arguments)
        if not r.is_valid():
            return r.errors, INVALID_REQUEST

        context["nclients"] = len(r.client_ids)
        response_body = {cid: get_interests(store, cid) for cid in
                         r.client_ids}
        return response_body, OK


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(bytes(datetime.datetime.now().strftime(
            "%Y%m%d%H") + ADMIN_SALT, "utf-8")).hexdigest()
    else:
        digest = hashlib.sha512(bytes(
            request.account + request.login + SALT, "utf-8")).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    handlers = {
        "online_score": OnlineScoreHandler,
        "clients_interests": ClientsInterestsHandler
    }

    method_request = MethodRequest(request["body"])
    if not method_request.is_valid():
        return method_request.errors, INVALID_REQUEST
    if not check_auth(method_request):
        return "Forbidden", FORBIDDEN

    handler = handlers[method_request.method]()

    return handler.process_request(method_request, ctx, store)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = Store(RedisStore(), 3, 2, (TimeoutError, ConnectionError))

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info(
                "%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers}, context,
                        self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"),
                 "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
