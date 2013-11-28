#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import random
import hashlib
import hmac
import logging
import json
import time
from string import letters
from bdd import *
import urllib
import urllib2


import webapp2
import jinja2

from datetime import datetime
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

start_time=0;
this_time=0;
query_time=0;
cache = {};
secret="lolilol"
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


class RoadTripHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_json(self, d):
        json_txt = json.dumps(d)
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.write(json_txt)

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'

class MainPage(RoadTripHandler):

    def get(self):
	    self.render('front.html')


def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)



class Welcome(RoadTripHandler):
    def get(self):
        if self.user:
            self.render('welcome.html', username = self.user.name)
        else:
            self.redirect('/signup')

DATE_RE = re.compile(r'(\d+/\d+/\d+)')
def valid_date(date):
    return date and DATE_RE.match(date)

BUDGET_RE = re.compile('^-?[0-9]+$')
def valid_budget(budget):
    return budget and BUDGET_RE.match(budget)

class New_adventure(RoadTripHandler):
    def get(self):
        if self.user:
            self.render('new_adventure.html', username = self.user.name)
        else:
            self.redirect('/signup')
    def post(self):
            have_error = False
            self.date_debut = self.request.get('date_debut')
            self.date_fin = self.request.get('date_fin')
            self.budget = self.request.get('budget')

            params = dict(date_debut = self.date_debut,
                          date_fin = self.date_fin,
                          budget = self.budget)

            if not valid_date(self.date_debut):
                params['error_date_debut'] = "Ceci n'est pas une date valide."
                have_error = True

            if not valid_date(self.date_fin):
                params['error_date_fin'] = "Ceci n'est pas une date valide."
                have_error = True

            if not valid_budget(self.budget):
                params['error_budget'] = "Ceci n'est pas un budget valide."
                have_error = True

            if have_error:
                self.render('new_adventure.html', **params)
            else:
                journey = Journey(owner = self.user, name = "hey it miss a field to give a name to this wonderful journey", start = self.date_debut, end = self.date_fin, budget = int(self.budget))
                journey.put()
                self.set_journey(journey)
                participant = Participant(journey = journey, user = self.user)
                self.redirect('new_friends')

    def done(self, *a, **kw):
        raise NotImplementedError

#Fonctionement de l'api Outpost.Travel
class Travel(RoadTripHandler):
    def get(self):
        if self.user:
            url = "http://api.outpost.travel/placeRentals?city=Strasbourg"
            response = urllib2.urlopen(url)
            data = json.load(response)
            page=json.dumps(data['page'])
            self.render('travel.html',page=page)
        else:
            self.redirect('/signup')

class New_friends(RoadTripHandler):
	def get(self):
		if self.user:
			self.render('new_friends.html', username = self.user.name)
		else:
			self.redirect('/signup')

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)


class Signup(RoadTripHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/welcome?username='+str(self.username))

class Login(RoadTripHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/welcome')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(RoadTripHandler):
    def get(self):
        self.logout()
        self.redirect('/travel')


app = webapp2.WSGIApplication([('/', MainPage),
                              ('/travel', Travel),
                               ('/new_friends', New_friends),
                              ('/new_adventure', New_adventure),
                              ('/welcome', Welcome),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ],
                              debug=True)