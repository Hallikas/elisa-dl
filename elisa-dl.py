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
__date__ = "09.10.2018"
__version__ = "0.8-devel"

import os
import sys
import time
import re
import requests
import json
import subprocess 
import glob

# Directory ID to save downloaded files
doneDir = 7693967
# Directory ID to save failed downloads
failDir = 10218902

#dirPrefix = "_new_/"
dirPrefix = ""

# Personal username and password for Elisa Viihde, you should NOT
# share this information to anyone!
username = '*ELISA VIIHDE USERNAME*'
password = '*ELISA VIIHDE PASSWORD*'

# Api Developer parameters. Please change to your own if you have one.
apiKey = '*ELISA VIIHDE DEVELOPER API KEY*'
clientSecret = 'nZhkFGz8Zd8w'

# You should not touch these!
apiUrl='https://api-viihde-gateway.dc1.elisa.fi/rest/npvr'
apiPlat='platform=external'
apiVer='v=2.1&appVersion=1.0'

false=False
true=True

auth = {}
reqHeaders = {}
accessCode = {}
accessToken = {}

doOnlyFormats = False
has_match=False
lookforcheck = 0

# Force utf8 encoding
reload(sys)
sys.setdefaultencoding('utf8')

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
	if not has_match: v=lookfor("movie", "^(?P<name>[\d\wöäåÖÄÅøé\' ,:&\-\.]{1,45})(, ?)(?P<country>[\wöäåÖÄÅ/\-]+?)(, ?| )(?P<year>(19|20)\d\d)\. (?P<description>.*)$", v)

# (Dans la maison, Ranska 2012) François Ozonin ohjaama draama äidinkielen opett
# (La loi du marché, Ranska 2015) Mm. Cannesissa palkittu elokuva työttömästä
# (Histoire immortelle/The Immortal Story, Ranska 1968) Orson Wellesin harvinainen
# (The Secret Life Of Walter Mitty, USA 2013) Walter Mitty työskentelee Life-lehd
# (My Old Lady, Englanti 2014) Sympaattisessa komediassa amerikkalainen tyhjätask
	if not has_match: v=lookfor("movie", "^\((?P<name>[\d\wöäåÖÄÅøé\' ,:&\-\./]{1,40}), (?!The|A)(?P<country>[\wöäåÖÄÅ/\-]+?) (?P<year>(19|20)\d\d)\)\.? ?(?P<description>.*)$", v)

# (USA 2012) Palkittu fantasiadraama kertoo kuusivuotiaasta Hushpuppy-tytöstä, j
# (Suomi 2015) Viktor Kärppä joutuu tahtomattaan keskelle Venäjän sisäistä v
# (Korea/Ranska 2013) Toiminnallinen scifijännäri uudelle jääkaudelle ajautunu
# (Ruotsi, 2016) Pahasti velkaantunut kirjailija joutuu pestautumaan satamatyölä
	if not has_match: v=lookfor("movie", "^\((?P<country>(USA|Suomi|Ruotsi|Britannia|Korea/Ranska)),? (?P<year>(19|20)\d\d)(, \d+')?\)\.? (?P<description>.*)$", v)

# (New Police Story/Hongkong-Kiina 2004). Poliisin eliittiryhmää johtava komisar
# (Die Hard: With A Vengeance/USA 1995). Vauhdikas toimintatrilleri käynnistyy, k
# (Mission: Impossible - Ghost Protocol/USA 2011). Menestyselokuvasarjan toiseksi
	if not has_match: v=lookfor("movie", "^\((?P<name>[\wöäåÖÄÅøé\' ,:&\-\.]{1,45})/(?P<country>[\wöäåÖÄÅ/\-]+?) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# (Inside Man, trilleri, USA, 2006) Naamioituneet ryöstäjät linnoittautuvat man
# (Charlie St. Cloud, draama, USA, 2010) Charliella on kyky nähdä edesmennyt vel
# (Jurassic World, seikkailu/sci-fi, USA, 2015) Jurassic Park -elokuvasarjan nelj
# (The Break-Up, romanttinen komedia, USA, 2006) Romanttinen komedia parisuhdeonge

# (Mr. Beans Holiday, komedia, Iso-Britannia/Ranska, Saksa, 2006) Nolojen tilantei
# (The International, trilleri, USA, Saksa, Iso-Britannia, 2009) Interpolin agentt
# (Two Brothers, draama, Ranska, iso-Britannia, 2004) 97 min. Villieläinkertomus
	if not has_match: v=lookfor("movie", "^\((?P<name>[\wöäåÖÄÅøé\' ,:&\-\.]{1,45}), (?!USA)(?P<genre>[\wä\-/ ]+), (?P<country>[\wöäåÖÄÅ/\-]+?), (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)
	if not has_match: v=lookfor("movie", "^\((?P<name>[\w ]+)/(?P<country>[\wöäåÖÄÅ/\-]{1,40}) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# (/Saksa-Britannia-USA-Espanja 2006). Sharon Stone palaa kirjailija Catherine Tra
	if not has_match: v=lookfor("movie", "^\(/(?P<country>[\wöäåÖÄÅ/\-]{1,40}) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v)

# (Ocean's Thirteen 2007). Steven Soderberghin supertähdillä ryyditetty rikoskom
# (Interstellar 2014). Henkeäsalpaava, tulevaisuuteen sijoittuva tieteiselokuva a
# (22 Jump Street 2014). Toimintakomedia 21 Jump Streetin jatko-osassa konstaapel
# (Horrible Bosses 2 2014). Mustan komedian jatko-osassa yrittäjiksi ryhtyneet ka
# (Beautiful Mind, A 2001). Mestariohjaaja Ron Howardin (Apollo 13, Da Vinci -kood
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

### NOT MOVIE OR EPISODE? Maybe we have eptitle anyway?
	if not v.has_key('type'):
		if v['title'] in ['Ihmemies MacGyver', 'Myytinmurtajat']:
			v['type'] = 'Series'
		else:
			a=re.search(' [ON]: ', v['description'])
			if a:
				v['type'] = "Movie"
			else:
				v['type'] = 'Unknown'

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
		a=re.search("^(?P<eptitle>[\wöäåÖÄÅ \-/,]{2,50})[!\?\.]{1,2}( {1,2}(?P<description>.*))?$", v['description'])
		if a:
			for b in a.groupdict(): v[b] = a.groupdict()[b]

		if v.has_key("eptitle"): v['name'] = "%s - %s" % (v['name'], v['eptitle'])

	if v['type'] in ['Movie']:
		if not v.has_key('year'): v['year'] = 'xxxx'

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

	filename = "%s/%s" % (v['type'].lower(), v['name'])
	if v['type'] == "Series":
		filename = "%s/%s/%s" % (v['type'].lower(), v['title'], v['name'])

	return dirPrefix+filename

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

##
## Few functions to help debug
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


## Modify given string to be OS path friendly
def cleanStrPath(var):
	var = os.path.normpath(os.path.normcase(re.sub(r'[\\/*?:"<>|]',"_",var.lower())))
	return var

## Modify given string to be used as filename
def cleanStrFile(var):
	var = re.sub(r'(19|2\d)(\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):\d\d\)',r'\1\2\3\4_\5\6)',var)
	var = re.sub(r'^(AVA |\w+)?(#Subleffa|Sub Leffa|Elokuva|leffa|torstai|perjantai)(:| -) | \(elokuva\)|Kotikatsomo(:| -) |R&A(:| -) |(Dokumenttiprojekti|(Kreisi|Toiminta)komedia|(Hirviö|Katastrofi|Kesä)leffa|Lauantain perheleffa)(:| -) |^(Uusi )?Kino( Klassikko| Kauko| Suomi| Into| Helmi| Tulio|Rock| Klassikko| Teema)?(:| -) ?','',var)
	var = re.sub(r': ',' - ',var)
	var = re.sub(r'[\\/*?:"<>|]',"_",var)
	return var

def doApiProcess(ret = None):
#	print "_doApiProcess()"
	r={}
	r['reason'] = ret.reason
	r['status'] = ret.status_code
	r['headers'] = {}
	for b in ret.headers:
		if b in ['Content-Type','Set-Cookie','X-RateLimit-Remaining-second','X-RateLimit-Remaining-minute','X-RateLimit-Limit-second','X-RateLimit-Limit-minute']:
			r['headers'][b] = ret.headers[b]
	
	if r['headers'].has_key('X-RateLimit-Limit-minute'):
		r['headers']['X-RateLimit-Limit-second'] = ret.headers['X-RateLimit-Limit-second']
		r['headers']['X-RateLimit-Remaining-second'] = ret.headers['X-RateLimit-Remaining-second']
		r['headers']['X-RateLimit-Limit-minute'] = ret.headers['X-RateLimit-Limit-minute']
		r['headers']['X-RateLimit-Remaining-minute'] = ret.headers['X-RateLimit-Remaining-minute']

	print "RateLimit:",
	print "sec: "+r['headers']['X-RateLimit-Remaining-second']+'/'+r['headers']['X-RateLimit-Limit-second'],
	print "min: "+r['headers']['X-RateLimit-Remaining-minute']+'/'+r['headers']['X-RateLimit-Limit-minute']

	if int(r['headers']['X-RateLimit-Remaining-second']) < 1:
		print "Throttling because RateLimit"
		print "sec: "+r['headers']['X-RateLimit-Remaining-second']+'/'+r['headers']['X-RateLimit-Limit-second'],
		time.sleep(1)
	if int(r['headers']['X-RateLimit-Remaining-minute']) < 20:
		print "Throttling because RateLimit"
		print "min: "+r['headers']['X-RateLimit-Remaining-minute']+'/'+r['headers']['X-RateLimit-Limit-minute']
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

def doApiPost(url, data=false):
#	print "_doApiPost()"
	if auth:
		reqHeaders = auth
	else:
		reqHeaders = {'content-type': 'application/x-www-form-urlencoded', 'apikey': apiKey}

	if data:
		ret = requests.post(url, data=data, headers=reqHeaders)
	else:
		ret = requests.post(url, headers=reqHeaders)
	r = doApiProcess(ret)
 	s = json.loads(ret.text)
#	print "/doApiPost()"
 	return (r,s)

def moveRecord(programId, folderId=doneDir):
#	print "_moveRecord()"
#	print auth
	if not auth:
		print "Missing Authentication"
		sys.exit(1)

	headers = auth
	headers['content-type'] = 'application/x-www-form-urlencoded'
	try:
		ret = requests.put(apiUrl+'/recordings/move?platform=external&v=2&appVersion=1.0', data='programId=%d&folderId=%d' % (programId, folderId), headers=headers)
		r = doApiProcess(ret)
	except:
		pass
#	print "/moveRecord()"
	return

def doApiGet(url, data=false):
#	print "_doApiGet()"
	if not auth:
		print "Missing Authentication"
		sys.exit(1)

	ret = requests.get(url, headers=auth)
	r = doApiProcess(ret)
 	s = json.loads(ret.text)
#	print "/doApiGet()"
 	return (r,s)

def getAccessCode():
#	print "_getAccessCode()"
	ret = requests.post('https://api-viihde-gateway.dc1.elisa.fi/auth/authorize/access-code',
		json = {'client_id': 'external', 'client_secret': clientSecret, 'response_type': 'code', 'scopes': []},
		headers = {'content-type': 'application/json', 'apikey': apiKey})
#	print "/getAccessCode()"
 	return json.loads(ret.text)['code']

def getAccessToken():
#	print "_getAccessToken()"
	token={}
	if os.path.exists("access.var"):
		token = load_vars("access.var")
		if token.has_key("expires") and float(token["expires"]) <= float(time.time()):
			del token['access_token']
	if not token.has_key('access_token'):
		payload = {
			'grant_type': 'authorization_code',
			'username': username,
			'password': password,
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
 	 	save_vars(token, "access.var")

#	print "/getAccessToken()"
	return "%s %s" % (token['token_type'], token['access_token'])

def login():
#	print "login()"
	return {'Authorization': getAccessToken(), 'apikey': apiKey}

def doDownload(filename, recordingUrl):
	print "doDownload(%s, %s)" % (filename, recordingUrl)
# Get with ffmpeg, best video and audio, BIG file
	if not os.path.exists(filename + '_ffmeg.mp4'):
		cmd = 'ffmpeg -i \"' + recordingUrl + '\" -c copy \"' + filename + '_ffmpeg.mp4\"'
# Get best of > 720p (HD)
	if not os.path.exists(filename + ' (HD).mp4'): 
		cmd = ( 'youtube-dl --hls-prefer-ffmpeg -f \"(bestvideo[height>720])+(audio-ec-3-224-Multiple_languages/audio-aacl-192-Multiple_languages/audio-aacl-48-Multiple_languages/bestaudio)\" -o \"' + filename + ' (HD).%(ext)s\" \"' + recordingUrl + '\"' )
# Get best of <= 720p, with standard audio (or best)
	if not os.path.exists(filename + '.mp4'):
		cmd = ( 'youtube-dl --hls-prefer-ffmpeg -f \"(bestvideo[height<=?720])+(audio-aacl-192-Multiple_languages/bestaudio)\" -o \"' + filename + '.%(ext)s\" \"' + recordingUrl + '\"' )
# Get best video that is less then 3MBit/s bitrate
#	cmd = ( 'youtube-dl --hls-prefer-ffmpeg -f \"(bestvideo[vbr<=?3000])+(audio-ec-3-224-Multiple_languages/audio-aacl-192-Finnish/audio-aacl-192-Multiple_languages/audio-aacl-48-Finnish/audio-aacl-48-Multiple_languages/bestaudio)\" -o \"' + filename + '.%(ext)s\" \"' + recordingUrl + '\"' )
	cmd = ( 'youtube-dl --hls-prefer-ffmpeg -f \"(bestvideo[height<=?999])+(audio-aacl-192-Finnish/audio-aacl-192-Multiple_languages/audio-aacl-48-Finnish/audio-aacl-48-Multiple_languages/bestaudio)\" -o \"' + filename + '.%(ext)s\" \"' + recordingUrl + '\"' )

	print cmd
	file=open("elisa-dl.log", 'a')
	file.write("CMD: %s\n" % cmd)
	file.close()

	os.system(cmd)

def init_system():
	if not os.path.exists('_/var'):
		try:
			os.makedirs('_/var', 0755)
		except:
			pass
	if not os.path.exists('tmp'):
		try:
			os.makedirs("tmp", 0755)
		except:
			pass

def getFolders():
	if not os.path.exists("_/var/save-fData.var"):	
		(r, getData) = doApiGet(apiUrl+'/folders'+'?'+apiPlat+'&'+apiVer)
		if (r["status"] != 200):
			print "Failed to load folders data",getData.status_code
			sys.exit(1)

		fData = {getData["id"]: {"name": getData["name"], "count": getData["recordingsCount"]}}
		for f in getData["folders"]:
#			if(f["recordingsCount"] > 0 and (f["name"] != "aDone" and f["name"] != "Fail")):
			fData[f["id"]] = {"name": f["name"], "count": f["recordingsCount"]}
		save_vars(fData, "_/var/save-fData.var")
	fData=load_vars("_/var/save-fData.var")

	return fData

def getFolder(folderId):
	if not os.path.exists("_/var/save-fData-%d.var" % folderId):
		(r, getData) = doApiGet(apiUrl+'/recordings/folder/'+str(folderId)+'?'+apiPlat+'&'+apiVer+'&page=0&pageSize=10000&includeMetadata=true')
		if (r["status"] != 200):
			print "Failed to load recording data for folder %d" % (folderId), r["status"]
			sys.exit(1)
		rData = {}
		for r in getData["recordings"]:
			rData[r["programId"]] = r
		save_vars(rData, "_/var/save-rData-%d.var" % folderId)
	rData=load_vars("_/var/save-rData-%d.var" % folderId)
	return rData

def makeFileName(r):
	try:
		fPath = '_/%s' % cleanStrPath(r['showType'])
	except:
		fPath = '_/unknown'

	fName = cleanStrFile(r["name"] +" ("+r["startTime"]+")")

	if r.has_key("seriesId") and r["seriesId"] > 0:
		if r.has_key("series") and r["series"].has_key("season") and r["series"].has_key("episode"):
			fName = cleanStrFile("%s - S%02dE%02d - %s (%s)" % (r["series"]["title"], r["series"]["season"], r["series"]["episode"], r["series"]["episodeName"], r["startTime"]))
	try:
		os.makedirs(fPath, 0755)
	except:
		pass

	filename=fPath+'/'+fName
	return filename

def checkQuit():
	if os.path.exists("/quit") or os.path.exists("quit"):
		print "Quit requested"
		sys.exit(0)








#if __name__ == "__main__":
#	os.nice(5)
#	f=load_vars('_/var/save-fullData.var');

#### This part I have used when I did rename OLD files
#
#	for a in f:
#		if f[a].has_key('program') and len(f[a]['program']) > 0:
#			for p, d in f[a]['program'].items():
##				if p != 11960662: continue
#				c=makeFileName(d)
#				g=glob.glob(c+"*")
#				if g:
#					c=re.sub('\(','\\(',c)
#					c=re.sub('\)','\\)',c)
#					ext=[]
#					print
#					print "mkdir -p '%s'" % re.sub('/[\d\wöäåÖÄÅøé\' ,:&\-\.]+$','',fixname(d['name'],d['description']))
#					for e in g:
#						src=re.sub('\'','\\\'',e)
#						dst=fixname(d['name'],d['description'])
#						ext=re.sub(c,'',e)
#						print "mv -vi '%s' '%s'" % (e, dst+ext)
##				if p == 11960662: sys.exit(1)
#sys.exit(0)


















if __name__ == "__main__":
	if not os.path.exists("_/var/save-fullData.var"):
		init_system()

		auth = login()
		fData = getFolders()

		fullData = fData
		for f in fData:
			print "Directory %d: %s" % (f, fData[f]["name"])
			rData = getFolder(f)
			fullData[f]["program"] = rData
			if len(rData) == 0: continue
			for r in rData:
				r=rData[r]
		save_vars(fullData, "_/var/save-fullData.var")
	fullData = load_vars("_/var/save-fullData.var")

##
## Login and download
	if len(auth) == 0: auth = login()
	for a in fullData:
		folderId=a
		if folderId in [doneDir, failDir, 0]: continue
		if folderId not in [8037870, 0]: continue
		a = fullData[a]
		if a['count'] < 1: continue
		i=0
		for p in a['program']:
			i += 1
#			if i > 4: sys.exit(1)
			checkQuit()
			filename=fixname(a['program'][p]['name'],a['program'][p]['description'])

			if os.path.exists(filename+".mp4"):
				print "DUPE %s: %s.mp4" % (p, filename)
				file=open("elisa-dl.log", 'a')
				file.write("DUPE %s: %s.mp4\n" % (p, filename))
				file.close()
				continue

			auth=login()
			url=apiUrl+'/recordings/url/'+str(p)+'?platform=ios&'+apiVer
			getRecordingUrl=requests.get(url, headers=auth)
			recordingUrl=json.loads(getRecordingUrl.text)

			checkQuit()
			print "Downloading %s: %s" % (p, filename)
			file=open("elisa-dl.log", 'a')
			file.write("Downloading %s: %s\n" % (p, filename))
			file.close()
			if doOnlyFormats == True: time.sleep(1)
			nameDir, nameFile = os.path.split(filename)
			try:
				os.makedirs(nameDir, 0755)
			except:
				pass
			try:
				print "Create -formats"
				if not os.path.exists(filename+"-formats.txt"):
					cmd='youtube-dl --list-formats \"'+recordingUrl["url"]+'\"'
					file=open(filename+'-formats.txt', 'w')
					strFormats=subprocess.check_output(cmd, shell=True)
					file.write(strFormats)
					file.close()
			except:
				print "Creating FAILED: %s" % filename+'-formats.txt'
				continue
			if not doOnlyFormats == False: continue

			print "Create description"
			if a['program'][p].has_key('description'):
				if not os.path.exists(filename+".txt"):
					file=open(filename+'.txt', 'w')
					file.write(a['program'][p]['description'].encode('utf8'))
					file.close()
			if not os.path.exists(filename+".var"):
				save_vars(a['program'][p], filename+'.var')
			time.sleep(1)
			checkQuit()

#			try:
			if 1:
				if not os.path.exists("%s.mp4" % filename) and not os.path.exists("tmp/%s.mp4" % nameFile):
					doDownload("tmp/%s" % nameFile, recordingUrl["url"])
					moveRecord(p, doneDir)
					os.rename("tmp/%s.mp4" % nameFile, "%s.mp4" % filename)
#			except:
#				print "Something bad happened...."
#				sys.exit(1)
#				moveRecord(p, failDir)
			
			checkQuit()

#			sys.exit(1)
# Quit after first download
#			break
# Quit after first directory
#		break

sys.exit(0)
