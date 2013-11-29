from string import letters
import random
import hashlib
from google.appengine.ext import webapp
from google.appengine.ext import db

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

class User(db.Model):
	name = db.StringProperty(required = True)
	email = db.StringProperty()
	pw_hash = db.StringProperty(required = True)
	@classmethod
	def by_id(cls, uid):
		return User.get_by_id(uid, parent = users_key())
	
	@classmethod
	def register(cls, name, pw, email = None):
		pw_hash = make_pw_hash(name, pw)
		return User(parent = users_key(),
					name = name,
					pw_hash = pw_hash,
					mail = email)
	@classmethod
	def by_name(cls, name):
		u = User.all().filter('name =', name).get()
		return u
		
	@classmethod
	def login(cls, name, pw):
		u = cls.by_name(name)
		if u and valid_pw(name, pw, u.pw_hash):
			return u
	
	def get_invitations(self):
		invitations = []
		for inv in self.invitations:
			if i.state == 1:
				invitations.append(inv.user, inv.message)
		return invitations
		
	def get_journeys(self):
		journeys = []
		for i in self.journeys:
			journeys.append(i.journey)
		return journeys
		
	def get_friends(self):
		friends = []
		for f in self.friends1:
			friends.append(f.user2)
		for f in self.friends2:
			friends.append(f.user1)
		return friends;
		
	def add_friend(self, user):
		if user in self.get_friends():
			return
		else:
			friend = Friend(user1 = self, user2 = user)
			friend.put()

class Journey(db.Model):
	owner = db.ReferenceProperty(User, required = True)
	name = db.StringProperty(required = True)
	start = db.StringProperty()
	end = db.StringProperty()
	budget = db.IntegerProperty()
	enable_sugg = db.BooleanProperty()
	nbr_steps = db.IntegerProperty()

	def get_steps(self):
		suggs = self.suggestions
		steps = [];
		while len(steps) < self.nbr_steps:
				steps.append({'place':[],'accomodation':[],'food':[]})
		for suggestion in suggs:
			steps[suggestion.step-1][suggestion.type].append(suggestion)
		return steps;
	
	def delete(self):
		for i in self.guestList:
			db.delete(i)
		for u in self.participants:
			db.delete(u)
		for s in suggestions:
			s.delete()
		for m in self.messages:
			db.delete(m)
		db.delete(self)

class Suggestion(db.Model):
	journey = db.ReferenceProperty(Journey, required = True, collection_name="suggestions")
	step = db.IntegerProperty(required = True)
	type = db.StringProperty(required=True, choices=set(["place", "accommodation", "food"]))
	id = db.StringProperty(required = True)
	def get_votants(self):
		votes = []
		for v in self.votes:
			votes.append(v.user)
		return votes
		
	def delete(self):
		for v in self.votes:
			db.delete(v)
		db.delete(self)
		
	def vote(self, user):
		suggestions = self.journey.suggestions
		for s in suggestion:
			if s.step != self.step or s.type != self.type:
				suggestion.remove(s)
		for s in suggestions:
			for v in s.votes:
				if v.user == user:
					db.delete(v)
		vote = Vote(user = user, suggestion = self)
		vote.put()

class Vote(db.Model):
	user = db.ReferenceProperty(User, required = True, collection_name="user_votes")
	suggestion = db.ReferenceProperty(Suggestion, required = True, collection_name="votes")

class Invitation(db.Model):
	journey = db.ReferenceProperty(Journey, required = True, collection_name="guestList")
	user = db.ReferenceProperty(User, required = True, collection_name="invitations")
	message = db.StringProperty(multiline=True)
	state = db.IntegerProperty(required=True)

class Participant(db.Model):
	journey = db.ReferenceProperty(Journey, required = True, collection_name="participants")
	user = db.ReferenceProperty(User, required = True, collection_name="journeys")
	
class Message(db.Model):
	author = db.ReferenceProperty(User, required = True)
	journey = db.ReferenceProperty(Journey, required = True, collection_name="messages")
	message = message = db.StringProperty(multiline=True)
	
class Friend(db.Model):
	user1 = db.ReferenceProperty(User, required = True, collection_name="friends1")
	user2 = db.ReferenceProperty(User, required = True, collection_name="friends2")