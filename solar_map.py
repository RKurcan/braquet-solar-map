from flask import Flask, render_template, request, Response, json, jsonify, send_file, redirect, url_for
from flask.ext.stormpath import StormpathManager, login_required, groups_required, user
from flask_mail import Mail
from flask_mail import Message
from pymongo import MongoClient
from googleplaces import GooglePlaces, types, lang
from geopy.geocoders import Nominatim
from gmap import Map
import credentials
import numpy as np
from decimal import Decimal
import json
import urllib2
import base64
import os

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT   = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = credentials.MAIL_USER_NAME
MAIL_PASSWORD = credentials.MAIL_PASSWORD

app = Flask(__name__)

# app configurations
app.config.from_object(__name__)
app.config['SECRET_KEY'] = credentials.STORMPATH_SECRET_KEY
app.config['STORMPATH_API_KEY_FILE'] = credentials.STORMPATH_API_KEY_FILE
app.config['STORMPATH_APPLICATION'] = credentials.STORMPATH_APPLICATION
app.config['STORMPATH_REGISTRATION_TEMPLATE'] = 'registration.html'
app.config['STORMPATH_LOGIN_TEMPLATE'] = 'login.html'
app.config['STORMPATH_REDIRECT_URL'] = '/dashboard'
app.config['STORMPATH_REGISTRATION_REDIRECT_URL'] = '/dashboard'

# clients connected to app
mail = Mail(app)
stormpath_manager = StormpathManager(app)
mongo = credentials.connect()
google_places = GooglePlaces(credentials.API_KEY)
geolocator = Nominatim()

@app.route("/demo", methods=["GET"])
@app.route("/index", methods=["GET"])
@app.route("/", methods=["GET"])
def freemapview():
	if user.is_authenticated():
		return redirect(url_for("dashboard"))

	rule = request.url_rule
	is_demo = False
	user_data = {'logged_in' : False}
	
	if 'demo' in rule.rule:
		is_demo = True

	logo = "Braquet | Layout"
	
	# create a map in view
	mymap = Map(
		identifier="view-side",
		lat=37.7918,
		lng=-122.4266,
		markers=[],
		style="height:600px;width:1000px;margin:0;"
	)

	return render_template('home.html', mymap=mymap, logo=logo, is_demo=is_demo, 
						   user_data=user_data)

@app.route("/dashboard", methods=["GET"])	
def dashboard():
	user_data = {}
	if user.is_authenticated():
		print "USERNAME*******************************" + user.given_name
		user_data['logged_in'] = True
		user_data['name'] = user.given_name
		user_data['email'] = user.email
	else:
		return redirect(url_for('freemapview'))

	logo = "Braquet | Layout"
	
	# create a map in view
	mymap = Map(
		identifier="view-side",
		lat=37.7918,
		lng=-122.4266,
		markers=[],
		style="height:600px;width:1000px;margin:0;"
	)

	return render_template('home.html', mymap=mymap, logo=logo, is_demo=False, 
						   user_data=user_data)

@app.route("/nrel", methods=["POST"])
def nrel():
	if request.method == "POST":
		lat = str(request.json['lat'])
		lng = str(request.json['lng'])
		tilt = str(request.json['tilt'])
		azimuth = str(request.json['azimuth'])
		capacity = str(request.json['capacity'])

		try:
			response = urllib2.urlopen("https://developer.nrel.gov/api/pvwatts/v5.json?api_key=" + credentials.NREL_API_KEY + \
				"&lat=" + lat + "&lon=" + lng + "&system_capacity=" + capacity + "&azimuth=" + azimuth + "&tilt=" + tilt + "&array_type=1&module_type=0&losses=10")
		except IOError, e:
			return "ERROR: API call failed"

		data = json.load(response)
		if data["outputs"]["dc_monthly"] != None:
			return jsonify(dict([(i, data["outputs"]["dc_monthly"][i]) for i in range(len(data))]))
		else:
			return "error retrieving energy production"

	else:
		return "404 ERROR";

@app.route("/sendEmailReport", methods=["POST"])
def sendEmailReport():
	if request.method == "POST":
		# base64 encoded image
		screenshot_base64 = str(request.json['screenshot'])[22:] # shave off the header "data:image/png;base64<comma_here>"
		chart_base64 = str(request.json['chart'])[22:]
		energy = request.json['energy']['2']
		numPanels = str(request.json['numPanels'])
		panelType = str(request.json['panelType'])

		# screenshot image location
		img_loc = "static/maps/rooftop_screenshot.png"
		chart_loc = "static/maps/production_chart.png"

		# decode base64 png screenshot
		fp1 = open(img_loc, "wb")
		fp2 = open(chart_loc, "wb")
		fp1.write(base64.b64decode(screenshot_base64))
		fp2.write(base64.b64decode(chart_base64))
		fp1.close()
		fp2.close()

		msg = Message("Braquet | Solar Report",
					  sender=("Braquet", credentials.MAIL_USER_NAME),
					  recipients=["syedm.90@gmail.com","takayuki.koizumi@gmail.com"])

		msg.html = render_template('email.html', energy=energy, numPanels=numPanels, panelType=panelType)

		with app.open_resource(img_loc) as screenshot:
			msg.attach(img_loc, "image/png", screenshot.read())

		with app.open_resource(chart_loc) as chart:
			msg.attach(chart_loc, "image/png", chart.read())

		mail.send(msg)

		return "success"

	else:
		return "404 ERROR"

@app.route("/get_screenshot")
def getScreenshot():
	filename = "static/maps/rooftop_screenshot.png"
	return send_file(filename, mimetype='image/png')

@app.route("/get_chart")
def getChart():
	filename = "static/maps/production_chart.png"
	return send_file(filename, mimetype='image/png')

if __name__ == "__main__":
	app.run(debug=True)





