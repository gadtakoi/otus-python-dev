import hashlib
import datetime
import unittest
import functools

import api

from store import cases


class TestCharFieldSuite(unittest.TestCase):
    @cases([
        'абв', 'abc', 'Иван Петрович Сидоров', 'Jon Smith', '100500', '-1'
    ])
    def test_charfield_valid(self, value):
        self.assertEqual(value, api.CharField().run_validators(value))

    @cases([
        -2009, 197.9, {}, [], None, '', 0
    ])
    def test_charfield_invalid(self, value):
        self.assertRaises(ValueError, api.CharField().run_validators, value)


class TestArgumentsFieldSuite(unittest.TestCase):
    @cases([
        {'a': 1, 'b': 2},
        {'lets': 'do', 'it': 'man'},
        {1: 'digit', '2': 'string'},
        {0: 0},
    ])
    def test_argumnentsfield_valid(self, value):
        self.assertEqual(value, api.ArgumentsField().run_validators(value))

    @cases([
        2, None, list(), -1, 0, 9999999999999999999999
    ])
    def test_argumnentsfield_invalid(self, value):
        self.assertRaises(ValueError, api.ArgumentsField().run_validators,
                          value)


class TestEmailFieldSuite(unittest.TestCase):
    @cases([
        'test@example.com',
        'example@test.ru',
    ])
    def test_emailfield_valid(self, value):
        self.assertEqual(value, api.EmailField().run_validators(value))

    @cases([
        'testexample.com',
        '',
    ])
    def test_emailfield_invalid(self, value):
        self.assertRaises(ValueError, api.EmailField().run_validators, value)


class TestPhoneFieldSuite(unittest.TestCase):
    @cases([
        '79111234567',
        79344123457,
    ])
    def test_phonefield_valid(self, value):
        self.assertEqual(str(value), api.PhoneField().run_validators(value))

    @cases([
        '9111234567',
        9311234567,
        9,
        7,
    ])
    def test_phonefield_invalid(self, value):
        self.assertRaises(ValueError, api.PhoneField().run_validators, value)


class TestDateFieldSuite(unittest.TestCase):
    @cases(['18.12.1878', '07.10.1952'])
    def test_datefield_valid(self, value):
        df = api.DateField().run_validators(value)
        result = api.DateField().to_str(df)
        self.assertEqual(value, result)

    @cases(['18121878', '07101952', '0', 0, -1, None, {}, list()])
    def test_datefield_invalid(self, value):
        self.assertRaises(ValueError, api.DateField().run_validators, value)


class TestBirthDayFieldSuite(unittest.TestCase):
    @cases(['07.10.1952', '17.02.1972'])
    def test_birthdayfield_valid(self, value):
        bd = api.BirthDayField().run_validators(value)
        result = api.DateField().to_str(bd)
        self.assertEqual(value, result)

    @cases(['25.08.1530', '-1', ' ', 0])
    def test_birthdayfield_invalid(self, value):
        self.assertRaises(ValueError, api.BirthDayField().run_validators,
                          value)


class TestGenderFieldSuite(unittest.TestCase):
    @cases([0, 1, 2, ])
    def test_genderfield_valid(self, value):
        self.assertEqual(value, api.GenderField().run_validators(value))

    @cases([9, -1, ' ', '', 'simple string', {}, None])
    def test_genderfield_invalid(self, value):
        self.assertRaises(ValueError, api.GenderField().run_validators, value)


class TestClientIDsFieldSuite(unittest.TestCase):
    @cases([
        [7, 1, 2],
        [331, 1, 4],
    ])
    def test_clientidsfield_valid(self, value):
        self.assertEqual(value, api.ClientIDsField().run_validators(value))

    @cases([
        ['7', 1, 2],
        ['', ' '],
        [-1, 4],
        [],
        0,
        None
    ])
    def test_clientidsfield_invalid(self, value):
        self.assertRaises(ValueError, api.ClientIDsField().run_validators, value)
