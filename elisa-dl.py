#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Semi's Python Elisa-Viihde Downloader

    Elisa-DL.py  Copyright (C) 2018  Sami-Pekka Hallikas
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions; Check LISENCE file for more info.

    Original code and idea was from Qotscha's version
    https://yhteiso.elisa.fi/elisa-viihde-sovellus-ja-nettipalvelu-16/elisa-viihde-api-julkaisut-ja-bugiraportit-512104/index2.html#post587924
    https://www.dropbox.com/s/s81ckhnzx9xese3/python-skriptit.zip
"""

__author__ = "Sami-Pekka Hallikas"
__email__ = "semi@hallikas.com"
__date__ = "10.10.2018"
__version__ = "0.8-devel"

import os
import sys
import time
import re
import requests
import json
import subprocess 
import glob

config = {}

# You should not touch these!
clientSecret = 'nZhkFGz8Zd8w'
apiUrl='https://api-viihde-gateway.dc1.elisa.fi/rest/npvr'
apiPlat='platform=external'
apiVer='v=2.1&appVersion=1.0'
config['apikey']=None

false=False
true=True

auth = {}
fullData = {}
reqHeaders = {}
accessCode = {}
accessToken = {}

firstRun=True
has_match=False
lookforcheck = 0
disableAPI = False

config['os']="unix"
config['donedir']=None
config['loopsleep']=60
config['infiniteLoop']=False
config['moveDupes']=True
config['usecache']=True


# Force utf8 encoding
reload(sys)
sys.setdefaultencoding('utf8')

### -----------------------------------------------------------------------
### Filename parser
### -----------------------------------------------------------------------

def lookfor(istype, whatstr, fromstr):
	global lookforcheck
	global has_match

	lookforcheck += 1
	a=re.search(whatstr, fromstr['description'], re.IGNORECASE)
	if a:
		for b in a.groupdict(): fromstr[b] = a.groupdict()[b]
		fromstr['match'] = lookforcheck
		if istype == "series":
			fromstr["type"] = "Series"
		elif istype == "movie":
			fromstr["type"] = "Movie"
		has_match = True
	return fromstr

#
# This part is probably most interesting, it takes TITLE and DESCRIPTION of program.
# Then it tries to make 'clever' filenames just by comparing information it can get.
# Lots of regexp and rewrite needed.
#
# Example:
# Title: Elokuva: Pikku naisia (S)
# Description:
#              (Little Women, draama, USA, 1994) Louisa May Alcottin
#              klassikkoromaaniin perustuva valloittava draama sijoittuu
#              1800-luvun loppupuolelle ja kertoo Marchin perheestä ja sen
#              neljän tyttären vaiheista nuoruusvuosista aikuistumisen
#              kynnykselle saakka.  105 min
# 
# Filename -> Little Women - Pikku naisia (1994)
#
def fixname(t, d):
	global lookforcheck
	global has_match

	is_movie=False
	has_match=False 
	lookforcheck = 0

	tmp=re.sub('^(AVA |\w+)?(#Subleffa|Sub Leffa|Elokuva|leffa|torstai|perjantai)(:| -) | \(elokuva\)|Kotikatsomo(:| -) |R&A(:| -) |(Dokumenttiprojekti|(Kreisi|Toiminta)komedia|(Hirviö|Katastrofi|Kesä)leffa|Lauantain perheleffa)(:| -) |^(Uusi )?Kino( Klassikko| Kauko| Suomi| Into| Helmi| Tulio|Rock| Klassikko| Teema)?(:| -) ?','',t)
	if t != tmp:
		is_movie=True
	t = tmp

# Fix TYPOS
	d=re.sub('ENSI-ILTA The', 'ENSI-ILTA (The', d)
	d=re.sub('Die Hard 2: Die Harder', 'Die Hard 2: Die Harder, toiminta, USA, 1990', d)
	d=re.sub('\(The Wolverine\)', '(Wolverine, The 2013)', d)
	d=re.sub('Iso-Britannia/Ranska, Saksa','Iso-Britannia/Ranska/Saksa',d)
	d=re.sub('USA, Saksa, Iso-Britannia','USA/Saksa/Iso-Britannia',d)
	d=re.sub('Ranska, iso-Britannia','Ranska/Iso-Britannia',d)
# /Fix
	t=re.sub('  ',' ',t)
	d=re.sub(' ?\([Uu]\)$', '', d)
	t=re.sub(' ?\(K?-?1?[S\d]\)$','',t)
	t=re.sub(' uudet jaksot| - (SUOMEN )?TV-ENSI-ILTA','',t)

	d=re.sub('  ',' ',d)
	d=re.sub(' ?\(K?-?1?[S\d]\)','',d)
	d=re.sub('^Uusi .+? kausi alkaa\! ', '', d, flags=re.IGNORECASE)
	d=re.sub('(SUOMEN )?TV-ENSI-ILTA!? ','',d, flags=re.IGNORECASE)

	v={"description": d}
	v['title'] = t
	if is_movie: v['type'] = "Movie"

# Try to find year
	if 1:
		a=re.search('(?P<country>USA) (?P<year>(19|20)\d\d)\.?', v['description'], re.IGNORECASE)
		if a:
			for b in a.groupdict(): v[b] = a.groupdict()[b]

		a=re.search('^(?P<description>.*\.) (?P<country>(Amerikkalai|Yhdysvaltalai|Kotimai|Ruotsalai))nen (?P<genre>\w+)(sarja|draama)?\.', v['description'])
		if a:
			if a.groupdict()["country"] in ['Amerikkalai', 'Yhdysvaltalai']:
				v['country'] = "USA"
			if a.groupdict()["country"] in ['Kotimai','Suomalai']:
				v['country'] = "Suomi"
			if a.groupdict()["country"] in ['Ruotsalai']:
				v['country'] = "Ruotsi"
			v['genre'] = a.groupdict()["genre"]
			v['description'] = a.groupdict()["description"]

# Behind Enemy Lines - Vihollisen keskellä, USA, 2001. O: John Moore P: Owen Wilson, Gene Hackman. Amerikkalaist
# Agent Cody Banks 2: Destination London, USA 2004. O. Kevin Allen. P: Frankie Mun
# 28 Days Later, Britannia, 2002. O: Danny Boyle. P: Cillian Murphy, Naomie Harris
# 28 Weeks Later,UK/Espanja,2007. O: Juan Carlos Fresnadillo. P: Robert Carlyle, Rose Byrne, Jeremy Renner. Lont
# 1
	if not has_match: v=lookfor("movie", "^(?P<name>[\d\wöäåÖÄÅøé\' ,:&\-\.]{1,45})(, ?)(?P<country>[\wöäåÖÄÅ/\-]+?)(, ?| )(?P<year>(19|20)\d\d)\. (?P<description>.*)$", v)

# (Dans la maison, Ranska 2012) François Ozonin ohjaama draama äidinkielen opett
# (La loi du marché, Ranska 2015) Mm. Cannesissa palkittu elokuva työttömästä
# (Histoire immortelle/The Immortal Story, Ranska 1968) Orson Wellesin harvinainen
# (The Secret Life Of Walter Mitty, USA 2013) Walter Mitty työskentelee Life-lehd
# (My Old Lady, Englanti 2014) Sympaattisessa komediassa amerikkalainen tyhjätask
# 2
	if not has_match: v=lookfor("movie", "^\((?P<name>[\d\wöäåÖÄÅøé\' ,:&\-\./]{1,40}), (?!The|A)(?P<country>[\wöäåÖÄÅ/\-]+?) (?P<year>(19|20)\d\d)\)\.? ?(?P<description>.*)$", v)

# (USA 2012) Palkittu fantasiadraama kertoo kuusivuotiaasta Hushpuppy-tytöstä, j
# (Suomi 2015) Viktor Kärppä joutuu tahtomattaan keskelle Venäjän sisäistä v
# (Korea/Ranska 2013) Toiminnallinen scifijännäri uudelle jääkaudelle ajautunu
# (Ruotsi, 2016) Pahasti velkaantunut kirjailija joutuu pestautumaan satamatyölä
# 3 
	if not has_match: v=lookfor("movie", "^\((?P<country>(USA|Suomi|Ruotsi|Britannia|Korea/Ranska)),? (?P<year>(19|20)\d\d)(, \d+')?\)\.? (?P<description>.*)$", v)

# (New Police Story/Hongkong-Kiina 2004). Poliisin eliittiryhmää johtava komisar
# (Die Hard: With A Vengeance/USA 1995). Vauhdikas toimintatrilleri käynnistyy, k
# (Mission: Impossible - Ghost Protocol/USA 2011). Menestyselokuvasarjan toiseksi
# 4
	if not has_match: v=lookfor("movie", "^\((?P<name>[\wöäåÖÄÅøé\' ,:&\-\.]{1,45})/(?P<country>[\wöäåÖÄÅ/\-]+?) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# (Inside Man, trilleri, USA, 2006) Naamioituneet ryöstäjät linnoittautuvat man
# (Charlie St. Cloud, draama, USA, 2010) Charliella on kyky nähdä edesmennyt vel
# (Jurassic World, seikkailu/sci-fi, USA, 2015) Jurassic Park -elokuvasarjan nelj
# (The Break-Up, romanttinen komedia, USA, 2006) Romanttinen komedia parisuhdeonge
# (Mr. Beans Holiday, komedia, Iso-Britannia/Ranska, Saksa, 2006) Nolojen tilantei
# (The International, trilleri, USA, Saksa, Iso-Britannia, 2009) Interpolin agentt
# (Wanted, toiminta, USA, Saksa, 2008) Wesley elää tylsää kirjanpitäjän elämää, ku
# (Two Brothers, draama, Ranska, iso-Britannia, 2004) 97 min. Villieläinkertomus
# 5
	if not has_match: v=lookfor("movie", "^\((?P<name>[\wöäåÖÄÅøé\' ,:&\-\.]{1,45}), (?!USA)(?P<genre>[\wä\-/ ]+), (?P<country>[\wöäåÖÄÅ/\-]+(, [\wöäåÖÄÅ/\-]+)?), (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)
# 6
	if not has_match: v=lookfor("movie", "^\((?P<name>[\w ]+)/(?P<country>[\wöäåÖÄÅ/\-]{1,40}) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# (/Saksa-Britannia-USA-Espanja 2006). Sharon Stone palaa kirjailija Catherine Tra
# 7
	if not has_match: v=lookfor("movie", "^\(/(?P<country>[\wöäåÖÄÅ/\-]{1,40}) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# (Ocean's Thirteen 2007). Steven Soderberghin supertähdillä ryyditetty rikoskom
# (Interstellar 2014). Henkeäsalpaava, tulevaisuuteen sijoittuva tieteiselokuva a
# (22 Jump Street 2014). Toimintakomedia 21 Jump Streetin jatko-osassa konstaapel
# (Horrible Bosses 2 2014). Mustan komedian jatko-osassa yrittäjiksi ryhtyneet ka
# (Beautiful Mind, A 2001). Mestariohjaaja Ron Howardin (Apollo 13, Da Vinci -kood
# 8
	if not has_match: v=lookfor("movie", "^\((?P<name>.+?) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# ( 1995). Klassikoksi nousseessa animaatioelokuvassa cowboynukke
	if not has_match: v=lookfor("movie", "^\( ?(?P<year>(19|20)\d\d)\)\.? ", v)
	if not has_match: v=lookfor("movie", ", (?P<country>Suomi|USA)? ?(?P<year>(19|20)\d\d)\.? ?(?P<description>.*)$", v)

# (Aliens) Legendaarisen kauhuelokuvan, Alien - kahdeksas matkustaja, vähin
	if not has_match: v=lookfor("movie", "^\(\w+\) (?P<description>.*\.) (?P<country>[\wöäåÖÄÅ/\-]{1,40}) (?P<year>(19|20)\d\d)\.?$", v)
	if not has_match: v=lookfor("movie", "(?P<country>[\wöäåÖÄÅ/\-]{1,40}) (?P<year>(19|20)\d\d)\.?$", v)
	if not has_match: v=lookfor("movie", "^\((?P<name>\w+?)\)\.? (?P<description>.*)$", v)

## Series
	if not has_match: v=lookfor("series", "^(Kausi (?P<season>\d+). (Jakso )?)?(?P<episode>\d+)/\d+\. ?(?P<description>.*)$", v)

#	print "MATCH",has_match,lookforcheck
### NOT MOVIE OR EPISODE? Maybe we have eptitle anyway?
	if not v.has_key('type'):
# If known series
		if v['title'] in ['Ihmemies MacGyver', 'Myytinmurtajat']:
			v['type'] = 'Series'
		else:
# We know that " O: " and " N: " in description is for director and lead
# woman.  Usually indication of movie.
			a=re.search(' [ON]: ', v['description'])
			if a:
				v['type'] = "Movie"
			else:
				v['type'] = 'Unknown'

# If description starts with "Osa" and number, that means episode.
	a=re.search("^Osa (?P<episode>\d+)\. ?(?P<description>.*)$", v['description'])
	if a:
		v['type'] = 'Series'
		for b in a.groupdict(): v[b] = a.groupdict()[b]

	if not v.has_key('name'):
		v['name'] = v['title']
	filename = v['name']
	if v['type'] in ['Series']:
### Add "SxxExx - eptitle" to title
		v['name'] = v['title']
		if v.has_key('season') and v['season']:
			v['name'] = v['name'] + " - S%02d" % int(v['season'])
		if v.has_key('episode'):
			if not v.has_key('season') or not v['season']:
				v['name'] = v['name'] + " - "
			v['name'] = v['name'] + "E%02d" % int(v['episode'])

### If series, first sentence is title (only if less then 50 chars)
		a=re.search("^(?P<eptitle>[\wöäåÖÄÅ \-/,]{2,50})[!\?\.]{1,3}( {1,2}(?P<description>.*))?$", v['description'])
		if a:
			for b in a.groupdict(): v[b] = a.groupdict()[b]

		if v.has_key("eptitle"): v['name'] = "%s - %s" % (v['name'], v['eptitle'])

	if v['type'] in ['Movie']:
		if not v.has_key('year'): v['year'] = 'xxxx'

# We want to move The and a AFTER title, like:
# "Martian, The - Yksin Marsissa (2015)" so file sort would work.
		t = re.sub(r'^(The|a) (.+)$', '\g<2>, \g<1>', t, re.IGNORECASE)
		if not v.has_key('name'):
			v['name'] = t
		else:
			v['name'] = re.sub(r'^(The|a) (.+)$', '\g<2>, \g<1>', v['name'], re.IGNORECASE)

		filename = v['name']
		if t.lower() != v['name'].lower():
			t=re.sub(re.sub(', The','', v['name']), '', t)
			t=re.sub(v['name']+" - ", '', t)
			v['name']=re.sub(" - "+t, '', v['name'])
			v['name']="%s - %s" % (v['name'], t)
		v['name'] = re.sub(' -  - ',' - ',v['name'])
		v['name'] = "%s (%s)" % (v['name'], v['year'])

	if v.has_key('match'): del v["match"]
	v['name'] = re.sub(r'[\\/*?:"<>|]',"_",v['name'])
	v['title'] = re.sub(r'[\\/*?:"<>|]',"_",v['title'])

	filename = "%s/%s" % (v['type'].lower(), v['name'])
	if v['type'] == "Series":
		filename = "%s/%s/%s" % (v['type'].lower(), v['title'], v['name'])

	return filename

### -----------------------------------------------------------------------
### Support functions
### -----------------------------------------------------------------------

def lookYesNo(test):
	if test in ['false','off','no']: return False
	if test in ['true','on','yes']: return True
	return None

def osfilename(fn):
	return fn.encode(sys.getfilesystemencoding())

## Save python variable to file
def save_vars(var, fname, id=None):
	fp = open(fname, "w+b")
	if fp: fp.write(show_vars(var))
	fp.close()
	return

## Load variable data from file
def load_vars(fname, id=None):
	fp = open(fname, "r")
	is_raw = False
	raw = None
	do_skip = False
	buf = ""
	while 1:
		line = fp.readline()
		if len(line) < 1: break
		if line[1:10] == "\"mime\": {":
			do_skip = True
		if line[1:13] == "\"raw\": 'From":
			raw = line[9:]
			is_raw = True
		elif is_raw:
			if line == "',\n":
				is_raw = False
			else:
				raw += line
		elif do_skip:
			if line[1:3] == "},":
				do_skip = False
			pass
		else:
			buf += line
	fp.close()
	vars = eval(buf)
	if raw: vars["raw"] = raw
	return vars

# Few functions to help debug, dump and show_vars
def dump(obj):
	for attr in dir(obj):
		if hasattr( obj, attr ):
			print( "obj.%s = %s" % (attr, getattr(obj, attr)))

def show_vars(var, lvl=0):
	if lvl==0: lvl=1
	st=""
	tab = "\t"

	if type(var) is dict:
		st += "{\n"
		for k in var.keys():
			st += tab*lvl
			if(0): # Reserve space for keys
				if type(k) is int:
					st += "%-16s" % ("%d: " % k)
				else:
					st += "%-16s" % ("\"%s\": " % k)
			else:
				if type(k) is int:
					st += "%d: " % k
				else:
					st += "\"%s\": " % k
			st += show_vars(var[k], lvl+1)
			st += ",\n"
		st += tab*(lvl-1)
		st += "}"
	elif type(var) is tuple:
		if len(var) < 1:
			st += str(var)
		else:
			st += "(\n"
			for k in var:
				st += tab*lvl
				st += show_vars(k, lvl+1)
				st += ",\n"
			st += tab*(lvl-1)
			st += ")"
	elif type(var) is list:
		if len(var) < 1:
			st += str(var)
		elif len(var) == 1 and type(var[0]) in [str, int]:
			st += str(var)
		else:
			st += "[\n"
			for k in var:
				st += tab*lvl
				st += show_vars(k, lvl+1)
				st += ",\n"
			st += tab*(lvl-1)
			st += "]"
	elif type(var) is str:
		st += "\'%s\'" % re.sub("\'", "\\\'", var)
	elif type(var) is int:
		st += "%d" % var
	elif var == None:
		st += "None"
	else:
		st += "\'%s\'" % re.sub("\'", "\\\'", str(var))
	return st

### -----------------------------------------------------------------------
### Functions related to API communication
### -----------------------------------------------------------------------

def doApiProcess(ret = None):

	r={}
	r['reason'] = ret.reason
	r['status'] = ret.status_code
	r['headers'] = {}

	if ret.status_code != 200:
		print show_vars(r)
		sys.exit(1)

	for b in ret.headers:
		if b in ['Content-Type','Set-Cookie','X-RateLimit-Remaining-second','X-RateLimit-Remaining-minute','X-RateLimit-Limit-second','X-RateLimit-Limit-minute']:
			r['headers'][b] = ret.headers[b]
	
	if r['headers'].has_key('X-RateLimit-Limit-minute'):
		r['headers']['X-RateLimit-Limit-second'] = ret.headers['X-RateLimit-Limit-second']
		r['headers']['X-RateLimit-Remaining-second'] = ret.headers['X-RateLimit-Remaining-second']
		r['headers']['X-RateLimit-Limit-minute'] = ret.headers['X-RateLimit-Limit-minute']
		r['headers']['X-RateLimit-Remaining-minute'] = ret.headers['X-RateLimit-Remaining-minute']

# Print ratelimit information, for debug purpouses when doing multiple requests
#	print "RateLimit:",
#	print "sec: "+r['headers']['X-RateLimit-Remaining-second']+'/'+r['headers']['X-RateLimit-Limit-second'],
#	print "min: "+r['headers']['X-RateLimit-Remaining-minute']+'/'+r['headers']['X-RateLimit-Limit-minute']

	if int(r['headers']['X-RateLimit-Remaining-second']) < 1:
		print "Requests per second left: "+r['headers']['X-RateLimit-Remaining-second']+'/'+r['headers']['X-RateLimit-Limit-second']
#		print "Throttling because RateLimit"
		time.sleep(1)
	if int(r['headers']['X-RateLimit-Remaining-minute']) < 20:
		print "Requests per minute left: "+r['headers']['X-RateLimit-Remaining-minute']+'/'+r['headers']['X-RateLimit-Limit-minute'],
		print "Throttling because RateLimit"
		time.sleep(10)

	if r['status'] != 200:
		print "ERROR %d:" % ret.status_code,ret.reason
		print
		print "URL:",ret.url
		print
		print "Auth:",auth
		print "Headers:",ret.headers
		sys.exit(1)
#	print "/doApiProcess()"
	return r

# API POST function
def doApiPost(url, data=false):
# **TODO** Check if used in config
	if disableAPI:
		print "_doApiProcess()"
		return (None, None)
	if auth:
		reqHeaders = auth
	else:
		reqHeaders = {'content-type': 'application/x-www-form-urlencoded', 'apikey': config['apikey']}

	if data:
		ret = requests.post(url, data=data, headers=reqHeaders)
	else:
		ret = requests.post(url, headers=reqHeaders)
	r = doApiProcess(ret)
 	s = json.loads(ret.text)
 	return (r,s)

# API GET function
def doApiGet(url, data=false):
	if disableAPI:
		print "_doApiProcess()"
		return (None, None)
	if not auth:
		print "Missing Authentication"
		sys.exit(1)

	ret = requests.get(url, headers=auth)
	r = doApiProcess(ret)
 	s = json.loads(ret.text)
 	return (r,s)

### -----------------------------------------------------------------------
### Login related functions
### -----------------------------------------------------------------------

# Get access code for access token
def getAccessCode():
	ret = requests.post('https://api-viihde-gateway.dc1.elisa.fi/auth/authorize/access-code',
		json = {'client_id': 'external', 'client_secret': clientSecret, 'response_type': 'code', 'scopes': []},
		headers = {'content-type': 'application/json', 'apikey': config['apikey']})
 	return json.loads(ret.text)['code']

# This is something that you don't have to do very often. API documentation says that token is just fine for 30 days :)
# **TODO** Well, I hope my expire code just works :D
def getAccessToken():
	token={}
	if os.path.exists("var/access.var"):
		token = load_vars("var/access.var")
		if token.has_key("expires") and float(token["expires"]) <= float(time.time()):
			del token['access_token']
	if not token.has_key('access_token'):
		payload = {
			'grant_type': 'authorization_code',
			'username': config['username'],
			'password': config['password'],
			'client_id': 'external',
			'code': getAccessCode()
		}
		(r, s) = doApiPost('https://api-viihde-gateway.dc1.elisa.fi/auth/authorize/access-token', payload)

		if s['response_type'] != 'token':
			print "Invalid access token"
			sys.exit(1)

		token['token_type'] = str(s['token_type'])
		token['access_token'] = str(s['access_token'])
	 	token['refresh_token'] = str(s['refresh_token'])
	 	token['expires'] = "%.0f" % (float(time.time()) + float(s['expires_in']))
 	 	save_vars(token, "var/access.var")
	return "%s %s" % (token['token_type'], token['access_token'])


# login function should return headers to do authorization
def login():
#	print "login()"
	return {'Authorization': getAccessToken(), 'apikey': config['apikey']}

### -----------------------------------------------------------------------
### Tools
### -----------------------------------------------------------------------
def testVar(varFile = None):
	if not varFile:
		print "You must give -var file as parameter"
		sys.exit(1)
	try:
		varData=load_vars(varFile)
	except:
		print "%s is not var-file or it is broken" % varFile
		sys.exit(1)

	print "Channel:",varData["channelName"]
	print "Type:",varData["showType"]
	print "Start:",varData["startTime"]
	print
	print "Title:",varData['name']
	print "Description:"
	print varData['description']
	print
	print fixname(varData['name'], varData['description'])
	return

def loadConfig():
	global config

	if sys.platform == 'win32':
		config['os']="win"

	if not os.path.exists("elisa-dl.conf"):
		print "You should copy elisa-dl.sample.conf to elisa-dl.conf"
		print "And edit it to contain your Elisa-Viihde username and password"
		print "Also you need to provide apikey"
		print
		sys.exit(1)
	fp = open("elisa-dl.conf", 'r')
	line = ""
	while 1:
		line = fp.readline()
		if not line: break
		if len(line) <= 1 or line[1:] == "#": continue

		a=re.search('^username\s*=\s*(?P<user>[\w\d]+)',line,re.IGNORECASE)
		if a: config['username']=a.groupdict()['user']
		a=re.search('^password\s*=\s*(?P<pass>[\w\d]+)',line,re.IGNORECASE)
		if a: config['password']=a.groupdict()['pass']
		a=re.search('^apikey\s*=\s*(?P<apikey>[\w\d]+)',line,re.IGNORECASE)
		if a: config['apikey']=a.groupdict()['apikey']

		a=re.search('^donedir\s*=\s*(?P<donedir>[\d]+)',line,re.IGNORECASE)
		if a:
			config['donedir']=int(a.groupdict()['donedir'])
		a=re.search('^dodirs\s*=\s*(?P<dodirs>[\d]+)',line,re.IGNORECASE)
		if a:
			config['doDirs']=[ int(a.groupdict()['dodirs']) ]
		a=re.search('^cache\s*=\s*(?P<usecache>[\w\d]+)',line,re.IGNORECASE)
		if a:
			config['usecache']=lookYesNo(a.groupdict()['usecache'])

		a=re.search('^move-dupes\s*=\s*(?P<movedupes>[\w\d]+)',line,re.IGNORECASE)
		if a:
			config['moveDupes']=lookYesNo(a.groupdict()['movedupes'])

		a=re.search('^infinite-loop\s*=\s*(?P<infiniteloop>[\w\d]+)',line,re.IGNORECASE)
		if a:
			config['infiniteLoop']=lookYesNo(a.groupdict()['infiniteloop'])
	fp.close()

	return config

### -----------------------------------------------------------------------
### Tools
### -----------------------------------------------------------------------
# Check if we have quit conditions, for nice end of the program.
def checkQuit():
	if os.path.exists("/quit") or os.path.exists("quit"):
		print "Quit requested"
		
		return True
	return None

### -----------------------------------------------------------------------
### doDownload
### -----------------------------------------------------------------------
def doDownload(filename, recordingUrl, programId):
# I wish this would work, but no... youtube-dl crashes because utf8 encoding problems
#	filename = osfilename(filename)

	# If you need to debug formats
	if not os.path.exists(osfilename(filename)+"-formats.txt"):
		cmd='youtube-dl --list-formats \"'+recordingUrl+'\"'
		file=open(osfilename(filename)+'-formats.txt', 'w')
		strFormats=subprocess.check_output(cmd, shell=True)
		file.write(strFormats)
		file.close()

# Limit bitrate to 3Mbit and sub FullHD resoluition, if available.
	filt_video='bestvideo[tbr<=?3000]/bestvideo[width<=1920][height<=1080]/bestvideo'
# Limit audio to 192 aac, prefer Finnish track first, always try skip eac3 because problems with ffmpeg
	filt_audio="bestaudio[format_id*=aacl-192][format_id*=Finnish]/bestaudio[format_id*=aacl-192]/bestaudio[format_id!=audio-ec-3-224-Multiple_languages]"

# You should use native HLS with this, because of eac3
	#filt_video='bestvideo'
	#filt_audio='bestaudio[format_id*=ec-3]/bestaudio[format_id*=aacl-192]/bestaudio'

	cmd = "youtube-dl"

# Select ONE HLS downloaders! Notice, ffmpeg can't handle eac3 audio but native could have audio problems
	cmd = "%s %s" % (cmd, '--hls-prefer-ffmpeg --external-downloader-args "-stats -hide_banner -loglevel warning"')
# Audio problems with this one! Be careful!
#	cmd = "%s %s" % (cmd, '--hls-prefer-native')

# Filters
	cmd = "%s -f \"(%s)+(%s)\"" % (cmd, filt_video, filt_audio)
# Output
	cmd = "%s -o \"%s.%%(ext)s\"" % (cmd, filename)
# URL
	cmd = "%s \"%s\"" % (cmd, recordingUrl)

# Get with ffmpeg, 'copy-as-is', best video and audio, BIG file!
# On Windows system this can cause problems, I have one report about it.
# This OVERIDES everything above!
#	cmd = 'ffmpeg -i \"%s\" -c copy \"%s.mp4\"' % (recordingUrl, filename)

# Just my own debug interrupt
	if os.path.exists("no-download"):
		print "NOT Downloading %s: %s" % (programId, filename)
		return None
# Execute downloading
	print "Downloading %s: %s" % (programId, filename)

# Write our status to elisa-dl.log
	file=open("elisa-dl.log", 'a')
	file.write("Downloading %s: %s.mp4\n" % (programId, filename))
	file.close()

# Write our status to elisa-dl-cmd.log
	file=open("elisa-dl-cmd.log", 'w')
	file.write("%s\n" % cmd)
	file.close()
	os.system(cmd)

	return filename

# Move programId to another folderId
def moveRecord(programId, folderId=config['donedir'], fromFolder=None):
	global fullData

	if not auth:
		print "Missing Authentication"
		sys.exit(1)

	headers = auth
	headers['content-type'] = 'application/x-www-form-urlencoded'
	ret = requests.put(apiUrl+'/recordings/move?platform=external&v=2&appVersion=1.0', data='programId=%d&folderId=%d' % (int(programId), int(folderId)), headers=headers)
	r = doApiProcess(ret)
# **TODO** We don't have exception handling, YET.. What to do if moving to doneDir fails?
# Now we just crash

# Update cache too, well this is good idea... but
# In normal situation, we are in loop that utilizes fullData information now
# when we move data inside of it, that loop does not get so well.
# Maybe we need to figure out some other way to loop?
#	if fromFolder:
#		tmp=fullData['folder'][fromFolder]['programs'][int(programId)]
#		fullData['folder'][folderId]['programs'][int(programId)]=tmp
#		del fullData['folder'][fromFolder]['programs'][int(programId)]
#		save_vars(fullData, "var/cache-fullData.var")
	return

### -----------------------------------------------------------------------
### Main download loop
### -----------------------------------------------------------------------
def main():
	global auth, fullData

	if len(auth) == 0: auth = login()

	if not fullData.has_key('program'): fullData=cacheFullData()
	for folderId in fullData['folder']:
		if config.has_key('doDirs') and folderId not in config['doDirs']: continue
# Don't process doneDir
		if folderId in [config['donedir']]: continue
		print "Processing folder '%s' (%d)" % (fullData['folder'][folderId]['name'], folderId)
		if fullData['folder'][folderId]['count'] < 1: continue

		for programId in fullData['folder'][folderId]['programs']:
			getProgram(programId)
			if checkQuit(): return
		if checkQuit(): return
	return

### -----------------------------------------------------------------------
### Func: fileRename
### -----------------------------------------------------------------------
def fileRename(doFile = None):
	if not doFile:
		print "You must give file as parameter"
		sys.exit(1)

	nameDir, nameFile = os.path.split(doFile)
	nameFile = re.sub('(-formats|-var)?.(txt|mp4|var)$', '', nameFile)

	if nameDir: doFile = "%s/%s" % (nameDir, nameFile)
	else: doFile = nameFile
	if os.path.exists("%s.var" % doFile): varFile="%s.var" % doFile
	else: varFile="%s-var.txt" % doFile
	try:
		varData=load_vars(varFile)
	except IOError as err:
		print "%s: %s-var.txt" % (err.strerror, doFile)
		sys.exit(1)

	childFiles=glob.glob(doFile+"*")
	toFile=fixname(varData['name'], varData['description'])

	if len(childFiles) > 6:
		print "FATAL: More then 6 files matches with %s. Too dangerous, please verify." % doFile
		sys.exit(1)

	FixName=doFile
	FixName=re.sub('\(','\(',FixName)
	FixName=re.sub('\)','\)',FixName)
	FixName=re.sub('\[','\[',FixName)
	FixName=re.sub('\]','\]',FixName)

	# Loop all thru first, just to make sure that target does not exist
	for fromFile in childFiles:
		ext=re.sub(FixName, '', fromFile)
		if os.path.exists('%s%s' % (toFile, ext)):
			print "Fatal, target exists: %s%s" % (toFile, ext)
			sys.exit(1)

	toDir, toFName = os.path.split(toFile)
	try:
		if not os.path.exists(toDir):
			os.makedirs(toDir, 0755)
	except IOError as err:
		print "%s: %s" % (err.strerror, doDir)
		sys.exit(1)

	for fromFile in childFiles:
		ext=re.sub(FixName, '', fromFile)
		try:
			os.rename(fromFile, "%s%s" % (toFile, ext))
			print "'%s' -> '%s%s'" % (fromFile, toFile, ext)
		except OSError as err:
			print "%s: %s-var.txt" % (err.strerror, doFile)
			continue
	return












### -----------------------------------------------------------------------
###
### -----------------------------------------------------------------------

def findProgram(doFile = None):
### **TODO** REWORK THIS
#	if not doFile:
#		print "You must give file as parameter"
#		sys.exit(1)
#
#	nameDir, nameFile = os.path.split(doFile)
#	nameFile = re.sub('(-formats|-var)?.(txt|mp4|var)$', '', nameFile)
#
#	fullData = load_vars("var/cache-fullData.var")
#	isFound = None
#	if 1:
#		if 1:
##			if programId not in [12051853]: continue
#			prog = fullData[folderId]['program'][programId]
#			oldName="%s (%s)" % (re.sub('^(AVA |\w+)?(#Subleffa|Sub Leffa|Elokuva|leffa|torstai|perjantai)(:| -) | \(elokuva\)|Kotikatsomo(:| -) |R&A(:| -) |(Dokumenttiprojekti|(Kreisi|Toiminta)komedia|(Hirviö|Katastrofi|Kesä)leffa|Lauantain perheleffa)(:| -) |^(Uusi )?Kino( Klassikko| Kauko| Suomi| Into| Helmi| Tulio|Rock| Klassikko| Teema)?(:| -) ?','',prog['name']), re.sub(r'(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):\d\d','\g<1>\g<2>\g<3>_\g<4>\g<5>',prog['startTime']))
#			newDir, newName=os.path.split(fixname(prog['name'],prog['description']))
#
##			print "Old",oldName
##			print "Find",nameFile
##			print "New",newName
##			print
#
#			if nameFile == oldName or  nameFile == newName:
#				if nameDir:
#					save_vars(prog, nameDir+"/"+osfilename(nameFile)+'-var.txt')
#				isFound = True
##			if isFound: break
##		if isFound: break
#	if isFound: fileRename(nameDir+"/"+osfilename(nameFile)+'-var.txt')
#	if not isFound:
#		print "Can't find information about", nameFile
	return











### -----------------------------------------------------------------------
### Func: getProgram
### -----------------------------------------------------------------------
def getProgram(programId):
#	if checkQuit(): return # /InfiniteLoop
	program = fullData['program'][int(programId)]

	fromFolder=None
	for folderId in fullData['folder']:
		if not fullData['folder'][folderId].has_key('programs'): continue
		if fullData['folder'][folderId]['programs'].has_key(int(programId)):
			program=fullData['folder'][folderId]['programs'][int(programId)]
			fromFolder=folderId
			break
		if fromFolder: break
			
	oldName="%s (%s)" % (re.sub('^(AVA |\w+)?(#Subleffa|Sub Leffa|Elokuva|leffa|torstai|perjantai)(:| -) | \(elokuva\)|Kotikatsomo(:| -) |R&A(:| -) |(Dokumenttiprojekti|(Kreisi|Toiminta)komedia|(Hirviö|Katastrofi|Kesä)leffa|Lauantain perheleffa)(:| -) |^(Uusi )?Kino( Klassikko| Kauko| Suomi| Into| Helmi| Tulio|Rock| Klassikko| Teema)?(:| -) ?','',program['name']), re.sub(r'(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):\d\d','\g<1>\g<2>\g<3>_\g<4>\g<5>',program['startTime']))
	filename = fixname(program['name'],program['description'])
	fileDir, fileName=os.path.split(filename)

# Verify that target directory does exist
	if not os.path.exists(osfilename(fileDir)): os.makedirs(osfilename(fileDir), 0755)

	if os.path.exists("%s.mp4" % osfilename(filename)):
		print "DUPE %s: %s.mp4" % (programId, filename)
		file=open("elisa-dl.log", 'a')
		file.write("DUPE %s: %s.mp4\n" % (programId, filename))
		file.close()
		if config['moveDupes'] and config['donedir']:
			moveRecord(programId, config['donedir'], fromFolder)
	else:
		tmpFile = osfilename("tmp/%s" % fileName)

		save_vars(program, tmpFile+"-var.txt")
		file=open(tmpFile+'.txt', 'w')
		file.write(program['description'].encode('utf8'))
		file.close()

		if not os.path.exists("%s.mp4" % tmpFile):
# Verify that we are logged in
			auth=login()
# Retrieve download URL for program
			url=apiUrl+'/recordings/url/'+str(programId)+'?platform=ios&'+apiVer
			getRecordingUrl=requests.get(url, headers=auth)
			recordingUrl=json.loads(getRecordingUrl.text)

			tmpFile = doDownload("%s" % tmpFile, recordingUrl["url"], programId)
# I hope that this helps to interrupt that record is not moved to Done directory in case of CTRL-C quit
			time.sleep(1)
		else:
			print "Found program from temp %s: %s" % (programId, filename)
			file=open("elisa-dl.log", 'a')
			file.write("Move from temp %s: %s.mp4\n" % (programId, filename))
			file.close()

		if tmpFile:
			time.sleep(1)
			if config['donedir']:
				moveRecord(programId, config['donedir'])
			fileRename("%s.mp4" % tmpFile)
	return


### -----------------------------------------------------------------------
### Cache/Get Data
### -----------------------------------------------------------------------
def cacheProgramData(folderId, force=None):
	global apiUrl, apiPlat, apiVer

	if force or not config['usecache'] or not os.path.exists("var/cache-fData-%d.var" % folderId):
		(r, getData) = doApiGet(apiUrl+'/recordings/folder/'+str(folderId)+'?'+apiPlat+'&'+apiVer+'&page=0&pageSize=10000&includeMetadata=true')
		if (r["status"] != 200):
			print "Failed to load recording data for folder %d" % (folderId), r["status"]
			sys.exit(1)
		rData = {}
		for rGetData in getData["recordings"]:
			rData[rGetData["programId"]] = rGetData
		save_vars(rData, "var/cache-rData-%d.var" % folderId)
	varData=load_vars("var/cache-rData-%d.var" % folderId)
	return varData

def cacheFolderData(force=None):
	global apiUrl, apiPlat, apiVer

	if force or not config['usecache'] or not os.path.exists("var/cache-fData.var"):
		(r, getData) = doApiGet(apiUrl+'/folders'+'?'+apiPlat+'&'+apiVer)
		if (r["status"] != 200):
			print "Failed to load folders data",getData.status_code
			sys.exit(1)
		fData = {getData["id"]: {"name": getData["name"], "count": getData["recordingsCount"]}}
		for f in getData["folders"]:
			fData[f["id"]] = {"name": f["name"], "count": f["recordingsCount"]}
		save_vars(fData, "var/cache-fData.var")
	varData=load_vars("var/cache-fData.var")
	return varData

def cacheFullData(force=None):
	global fullData

	if force or not config['usecache'] or not os.path.exists("var/cache-fullData.var"):
		fullData['folder'] = cacheFolderData()
		fullData['program'] = {}
		for folderId in fullData['folder']:
			if folderId == 'program': continue
			print "Reading directory %d: %s" % (folderId, fullData['folder'][folderId]['name'])
			if fullData['folder'][folderId]['count'] < 1: continue
			rData = cacheProgramData(folderId)
			if len(rData) == 0: continue
			fullData['folder'][folderId]['programs'] = rData
			for r in rData:
				fullData['program'][r] = rData[r]
		save_vars(fullData, "var/cache-fullData.var")
	varData = load_vars("var/cache-fullData.var")
	return varData

### -----------------------------------------------------------------------
### Startup
### -----------------------------------------------------------------------
if __name__ == "__main__":
	loadConfig()
# Make cache and temp directories if does not exist
	if not os.path.exists('var'): os.makedirs('var', 0755)
	if not os.path.exists('tmp'): os.makedirs('tmp', 0755)

# Show metadata from var- file
	if not sys.argv[1:]:
		pass
	elif sys.argv[1:][0] == "filename" or sys.argv[1:][0] == "test":
		if len(sys.argv) >= 3:
			testVar(sys.argv[2:][0])
# Rename files by data from var- file
	elif sys.argv[1:][0] == "rename":
		if len(sys.argv) >= 3:
			for i, fn in enumerate(sys.argv[2:]):
				fileRename(fn)

# All other needs data from server/cache
	auth=login()
	fullData = cacheFullData()

# Without argument, download all
	if not sys.argv[1:]:
		while firstRun or config['infiniteLoop']:
			firstRun = False
			main()
			
			if not config['infiniteLoop']: break
			print "Sleeping for %d sec until new loop" % config["loopsleep"]
			i=0
			while i < config["loopsleep"]:
				i=i+1
				if checkQuit():
					config['infiniteLoop'] = False
					break
				time.sleep(1)

# Download by programId
	elif sys.argv[1:][0] == "get":
		if len(sys.argv) >= 3:
			for p in sys.argv[2:]:
				for programId in p.split(","):
					if programId:
						getProgram(programId)
# Look from fullData.var by filename
	elif sys.argv[1:][0] == "lookup" or sys.argv[1:][0] == "find":
		if len(sys.argv) >= 3:
			for i, fn in enumerate(sys.argv[2:]):
				findProgram(fn)

sys.exit(0)
