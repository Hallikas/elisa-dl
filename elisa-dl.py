#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Semi's Python Elisa-Viihde Downloader

    Elisa-DL.py  Copyright (C) 2018-2024  Sami-Pekka Hallikas
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions; Check LISENCE file for more info.

    Original code and idea was from Qotscha's version
    https://yhteiso.elisa.fi/elisa-viihde-sovellus-ja-nettipalvelu-16/elisa-viihde-api-julkaisut-ja-bugiraportit-512104/index2.html#post587924
    https://www.dropbox.com/s/s81ckhnzx9xese3/python-skriptit.zip
"""

__author__ = "Sami-Pekka Hallikas"
__email__ = "semi@hallikas.com"
__date__ = "29.7.2024"
__version__ = "0.80-devel"

import os
import sys
import time
from datetime import datetime, timedelta, date
import re

sys.path.append('var/lib')
import requests
import json
import subprocess 
import glob

import string
global config

config = {}

# You should not touch these!
clientSecret = 'nZhkFGz8Zd8w'
#apiUrl='https://rest-api.elisaviihde.fi/rest/npvr'
#apiVer='v=2&appVersion=1.0'
# NEW API
apiUrl='https://api-viihde-gateway.dc1.elisa.fi/rest/npvr'
apiVer='v=2&appVersion=1.0'
#apiVer='v=2.1&appVersion=1.0'
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
disableAPI = False
fatalErrors = 0
lfcount = 0
v = {'type': 'unknown' }


config['os']="unix"
config['donedir']=None
config['faildir']=None
config['dupedir']=None
config['loopsleep']=60
config['infiniteLoop']=False
config['noDownload']=False
config['moveDupes']=True
config['usecache']=True
config['debugmode']=False
config['dry_run']=False
# Wait at least 120 minutes after recording is ready, so Elisa has done their conversion.
config['getAge']=240

# What age of original .mp4 is considered as too old (force download)
too_old = datetime.now() - timedelta(days=364)

# Usually best
platformFormat='ios'
# If you have problems with 'ios'
#platformFormat='online_wv'

# Force utf8 encoding
#reload(sys)
#sys.setdefaultencoding('utf8')

def info2var(doFile):
	nameDir, nameFile = os.path.split(doFile)
	nameFile = re.sub('(-formats|-var)?\.(txt|mp4|var|info)?$', '', nameFile)

	if not nameDir: nameDir="."

	varData={}
	if not os.path.exists("%s/%s-var.txt" % (nameDir, nameFile)) and not os.path.exists("%s/%s.var" % (nameDir, nameFile)):
		if os.path.exists("%s/%s.info" % (nameDir, nameFile)):
			fp=open('%s/%s.info' % (nameDir, nameFile),'r')
		elif os.path.exists("%s/%s.txt" % (nameDir, nameFile)):
			fp=open('%s/%s.txt' % (nameDir, nameFile), 'r')
		else:
			doLog("Can't find var file for %s" % nameFile)
			sys.exit(1)
			return

		time=None
		name=None
		desc=None
		while 1:
			line=fp.readline()
			if not line: break
			if line[0:2] == "T ": name=line[2:-1]
			if line[0:2] == "D ": desc=line[2:-1]
			if line[0:2] == "E ": time=re.sub("^E (\d{1,2})\.(\d{1,2})\.(\d{4}).* (\d{2}):(\d{2}):(\d{2}).*$", "\g<3> \g<2> \g<1> \g<4> \g<5> \g<6>", line[:-1]).split(" ")

		if not name and not desc:
			doLog("Can't create .var for file, no metadata files found")
			fatal=True
			sys.exit(1)
			return
		if time:
			if time[0] == "E": varData['startTime'] = date.fromtimestamp(int(time[2])).strftime('%Y-%m-%d %H:%M:%S')
			else: varData['startTime'] = '%4d-%02d-%02d %02d:%02d:%02d' % (int(time[0]), int(time[1]), int(time[2]), int(time[3]), int(time[4]), int(time[5]))
		varData['name'] = name
		varData['description'] = desc

		nameFile=osfilename(nameFile)
		save_vars(varData, "%s/%s.var" % (nameDir, nameFile))
		fp.close()

	nameFile="%s/%s" % (nameDir, nameFile)
	return nameFile



### -----------------------------------------------------------------------
### Filename parser
### -----------------------------------------------------------------------

def lookfor(istype, whatstr, fromstr=None):
	global has_match, lfcount

	if not fromstr:
		fromstr=whatstr
		whatstr=istype
		istype=None
	ret={}

	lfcount=lfcount+1
	a=re.search(whatstr, fromstr, re.IGNORECASE)
	if a:
		has_match = True
		ret = a.groupdict()
		if istype: ret['type'] = istype
		if config['debugmode']:
			print("Regexp:",whatstr)
			print("Description:",fromstr)
			print("Groups:",a.groups())
			print("Array:",a.groupdict())
#	if has_match:
#		print
#		print("\t",whatstr)
#		print("\t",fromstr)
	return ret

def str_toupper(str):
	return str.group(1).upper()

def pathfix(fromstr):
	fromstr=re.sub('/','_',fromstr)
	fromstr=re.sub('\?','_',fromstr)
	fromstr=re.sub('"','_',fromstr)
	fromstr=re.sub(': ','_ ',fromstr)
	fromstr=re.sub(':','_',fromstr)
	fromstr=re.sub(' $','',fromstr)
	fromstr=re.sub('^ ','',fromstr)
	fromstr=re.sub('\'','_',fromstr)
	fromstr=re.sub('\.$','',fromstr)
	return fromstr

def fixstrings(fromstr):
	fromstr=re.sub('%22','',fromstr)
	fromstr=re.sub('%3F','?',fromstr)
	fromstr=re.sub('%C2%A1','¡',fromstr)
	fromstr=re.sub('%C2%A2','¢',fromstr)
	fromstr=re.sub('%C2%A3','£',fromstr)
	fromstr=re.sub('%C2%A4','¤',fromstr)
	fromstr=re.sub('%C2%A5','¥',fromstr)
	fromstr=re.sub('%C2%A6','¦',fromstr)
	fromstr=re.sub('%C2%A7','§',fromstr)
	fromstr=re.sub('%C2%A8','¨',fromstr)
	fromstr=re.sub('%C2%A9','©',fromstr)
	fromstr=re.sub('%C2%AA','ª',fromstr)
	fromstr=re.sub('%C2%AB','«',fromstr)
	fromstr=re.sub('%C2%AC','¬',fromstr)
	fromstr=re.sub('%C2%AE','®',fromstr)
	fromstr=re.sub('%C2%AF','¯',fromstr)
	fromstr=re.sub('%C2%B0','°',fromstr)
	fromstr=re.sub('%C2%B1','±',fromstr)
	fromstr=re.sub('%C2%B2','²',fromstr)
	fromstr=re.sub('%C2%B3','³',fromstr)
	fromstr=re.sub('%C2%B4','´',fromstr)
	fromstr=re.sub('%C2%B5','µ',fromstr)
	fromstr=re.sub('%C2%B6','¶',fromstr)
	fromstr=re.sub('%C2%B7','·',fromstr)
	fromstr=re.sub('%C2%B8','¸',fromstr)
	fromstr=re.sub('%C2%B9','¹',fromstr)
	fromstr=re.sub('%C2%BA','º',fromstr)
	fromstr=re.sub('%C2%BB','»',fromstr)
	fromstr=re.sub('%C2%BC','¼',fromstr)
	fromstr=re.sub('%C2%BD','½',fromstr)
	fromstr=re.sub('%C2%BE','¾',fromstr)
	fromstr=re.sub('%C2%BF','¿',fromstr)
	fromstr=re.sub('%C3%80','À',fromstr)
	fromstr=re.sub('%C3%81','Á',fromstr)
	fromstr=re.sub('%C3%82','Â',fromstr)
	fromstr=re.sub('%C3%83','Ã',fromstr)
	fromstr=re.sub('%C3%84','Ä',fromstr)
	fromstr=re.sub('%C3%85','Å',fromstr)
	fromstr=re.sub('%C3%86','Æ',fromstr)
	fromstr=re.sub('%C3%87','Ç',fromstr)
	fromstr=re.sub('%C3%88','È',fromstr)
	fromstr=re.sub('%C3%89','É',fromstr)
	fromstr=re.sub('%C3%8A','Ê',fromstr)
	fromstr=re.sub('%C3%8B','Ë',fromstr)
	fromstr=re.sub('%C3%8C','Ì',fromstr)
	fromstr=re.sub('%C3%8D','Í',fromstr)
	fromstr=re.sub('%C3%8E','Î',fromstr)
	fromstr=re.sub('%C3%8F','Ï',fromstr)
	fromstr=re.sub('%C3%90','Ð',fromstr)
	fromstr=re.sub('%C3%91','Ñ',fromstr)
	fromstr=re.sub('%C3%92','Ò',fromstr)
	fromstr=re.sub('%C3%93','Ó',fromstr)
	fromstr=re.sub('%C3%94','Ô',fromstr)
	fromstr=re.sub('%C3%95','Õ',fromstr)
	fromstr=re.sub('%C3%96','Ö',fromstr)
	fromstr=re.sub('%C3%97','×',fromstr)
	fromstr=re.sub('%C3%98','Ø',fromstr)
	fromstr=re.sub('%C3%99','Ù',fromstr)
	fromstr=re.sub('%C3%9A','Ú',fromstr)
	fromstr=re.sub('%C3%9B','Û',fromstr)
	fromstr=re.sub('%C3%9C','Ü',fromstr)
	fromstr=re.sub('%C3%9D','Ý',fromstr)
	fromstr=re.sub('%C3%9E','Þ',fromstr)
	fromstr=re.sub('%C3%9F','ß',fromstr)
	fromstr=re.sub('%C3%A0','à',fromstr)
	fromstr=re.sub('%C3%A1','á',fromstr)
	fromstr=re.sub('%C3%A2','â',fromstr)
	fromstr=re.sub('%C3%A3','ã',fromstr)
	fromstr=re.sub('%C3%A4','ä',fromstr)
	fromstr=re.sub('%C3%A5','å',fromstr)
	fromstr=re.sub('%C3%A6','æ',fromstr)
	fromstr=re.sub('%C3%A7','ç',fromstr)
	fromstr=re.sub('%C3%A8','è',fromstr)
	fromstr=re.sub('%C3%A9','é',fromstr)
	fromstr=re.sub('%C3%AA','ê',fromstr)
	fromstr=re.sub('%C3%AB','ë',fromstr)
	fromstr=re.sub('%C3%AC','ì',fromstr)
	fromstr=re.sub('%C3%AD','í',fromstr)
	fromstr=re.sub('%C3%AE','î',fromstr)
	fromstr=re.sub('%C3%AF','ï',fromstr)
	fromstr=re.sub('%C3%B0','ð',fromstr)
	fromstr=re.sub('%C3%B1','ñ',fromstr)
	fromstr=re.sub('%C3%B2','ò',fromstr)
	fromstr=re.sub('%C3%B3','ó',fromstr)
	fromstr=re.sub('%C3%B4','ô',fromstr)
	fromstr=re.sub('%C3%B5','õ',fromstr)
	fromstr=re.sub('%C3%B6','ö',fromstr)
	fromstr=re.sub('%C3%B7','÷',fromstr)
	fromstr=re.sub('%C3%B8','ø',fromstr)
	fromstr=re.sub('%C3%B9','ù',fromstr)
	fromstr=re.sub('%C3%BA','ú',fromstr)
	fromstr=re.sub('%C3%BB','û',fromstr)
	fromstr=re.sub('%C3%BC','ü',fromstr)
	fromstr=re.sub('%C3%BD','ý',fromstr)
	fromstr=re.sub('%C3%BE','þ',fromstr)
	fromstr=re.sub('%C5%93','½',fromstr)

# Convert character to 
	fromstr=re.sub('À','A',fromstr)
	fromstr=re.sub('Á','A',fromstr)
	fromstr=re.sub('Â','A',fromstr)
	fromstr=re.sub('Å','A',fromstr)
	fromstr=re.sub('Æ','Æ',fromstr)
	fromstr=re.sub('Ç','C',fromstr)
	fromstr=re.sub('È','E',fromstr)
	fromstr=re.sub('É','E',fromstr)
	fromstr=re.sub('Ê','E',fromstr)
	fromstr=re.sub('Ë','E',fromstr)
	fromstr=re.sub('Ì','I',fromstr)
	fromstr=re.sub('Í','I',fromstr)
	fromstr=re.sub('Î','I',fromstr)
	fromstr=re.sub('Ï','I',fromstr)
	fromstr=re.sub('Ð','D',fromstr)
	fromstr=re.sub('Ñ','N',fromstr)
	fromstr=re.sub('Ò','O',fromstr)
	fromstr=re.sub('Ó','O',fromstr)
	fromstr=re.sub('Ô','O',fromstr)
	fromstr=re.sub('Õ','O',fromstr)
	fromstr=re.sub('Ø','O',fromstr)
	fromstr=re.sub('Ù','U',fromstr)
	fromstr=re.sub('Ú','U',fromstr)
	fromstr=re.sub('Û','U',fromstr)
	fromstr=re.sub('Ü','U',fromstr)
	fromstr=re.sub('Ý','Y',fromstr)
	fromstr=re.sub('ß','B',fromstr)
	fromstr=re.sub('à','a',fromstr)
	fromstr=re.sub('á','a',fromstr)
	fromstr=re.sub('â','a',fromstr)
	fromstr=re.sub('ã','a',fromstr)
	fromstr=re.sub('å','a',fromstr)
	fromstr=re.sub('æ','ae',fromstr)
	fromstr=re.sub('ç','c',fromstr)
	fromstr=re.sub('è','e',fromstr)
	fromstr=re.sub('é','e',fromstr)
	fromstr=re.sub('ê','e',fromstr)
	fromstr=re.sub('ë','e',fromstr)
	fromstr=re.sub('ì','i',fromstr)
	fromstr=re.sub('í','i',fromstr)
	fromstr=re.sub('î','i',fromstr)
	fromstr=re.sub('ï','i',fromstr)
	fromstr=re.sub('ð','o',fromstr)
	fromstr=re.sub('ñ','n',fromstr)
	fromstr=re.sub('ò','o',fromstr)
	fromstr=re.sub('ó','o',fromstr)
	fromstr=re.sub('ô','o',fromstr)
	fromstr=re.sub('õ','o',fromstr)
	fromstr=re.sub('ø','o',fromstr)
	fromstr=re.sub('ù','u',fromstr)
	fromstr=re.sub('ú','u',fromstr)
	fromstr=re.sub('û','u',fromstr)
	fromstr=re.sub('ü','u',fromstr)
	fromstr=re.sub('ý','y',fromstr)

	fromstr=re.sub(',, ',', ',fromstr)
	fromstr=re.sub(' & ',' and ',fromstr)
	
	return fromstr


#
# This part is probably most complicated/interesting, it takes TITLE and
# DESCRIPTION of program.  Then it tries to make 'clever' filenames just by
# comparing information it can get.  Lots of regexp and rewrite needed.
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
def fixname(vars, verbose=False):
	global has_match, lfcount, v

	has_match = False

# "ageLimit"
# "contentRatings"
# "genres"
# "startTimeUTC"
# "actors"

	v = {'type': 'unknown' }
	vars_keys = {"showType": "type", "description": "d", "series": "series", "name": "t", "genres": "genres", "startTime": "startTime"}

	for key in vars_keys:
		if key in vars:
			if key == "genres":
				v['genres'] = []
				for g in vars['genres']: v['genres'].append(g['name'].lower())
			else:
				v.update({vars_keys[key]: vars[key]})

	if 'type' in v:
		v.update({'type': v['type'].lower()})

	if 'series' in v and "seriesId" in v['series'] and v['series']["seriesId"] == 0:
		v['type'] = 'movie'
		del v['series']

### You can test regexp with online site https://regex101.com/
	if not 'd' in v: v['d'] = ''
	if not 't' in v: v['t'] = ''

### Fix/Clean title and/or description
#	v['t']=re.sub('','', v['t'])
	v['t']=re.sub(' \(K?-?1?[S\d]\)',r'',v['t'])
	v['t']=re.sub(' ?\(K?-?1?[S\d]\)$','',v['t'])
	v['t']=re.sub('([\w\)]):(\w)',r'\1: \2', v['t'])
	v['d']=re.sub('^\(K?-?1?[S\d]\) ','', v['d'])
	v['d']=re.sub(' ?\([Uu]\)$', '', v['d'])
	v['d']=re.sub(' Mv\.$', '', v['d'])
	v['d']=re.sub('  ',' ',v['d'])

	v['d']=re.sub('^Uusi .+? kausi alkaa\! ', '', v['d'], flags=re.IGNORECASE)
	v['d']=re.sub('^(\d+)\. kauden jaksot[\w ]+?\. ', 'Kausi \g<1>. ', v['d'], flags=re.IGNORECASE)

	v['d']=re.sub('(SUOMEN )?TV[- ]ENSI-ILTA!? ','',v['d'], flags=re.IGNORECASE)
	v['d']=re.sub('ENSI-ILTA The', 'ENSI-ILTA (The', v['d'])
	v['d']=re.sub('(\d)\. kauden jaksot alkavat( uusintana)\. ',r'Kausi \1. ',v['d'])
	v['d']=re.sub('(Sarja alkaa( alusta uusintana)?|UUSI SARJA|(SUOMEN )?TV-ENSI-ILTA)[\.,!]? ?','',v['d'])
	v['t']=re.sub(' uudet jaksot| \d\d\. kausi| - (SUOMEN )?TV-ENSI-ILTA','',v['t'])

	v['d']=re.sub('(\(USA (19|20)\d\d\))?, \d\d+\'\)',')', v['d'])

	v['d']=re.sub('(Länsi|Itä)-Saksa/','Saksa/', v['d'])
	v['d']=re.sub('Iso-Britannia(/|, ?)Ranska(/|, ?)Saksa','Iso-Britannia/Ranska/Saksa', v['d'])
	v['d']=re.sub('Iso-Britannia(/|, ?)Ranska(/|, ?)USA','Iso-Britannia/Ranska/USA', v['d'])
	v['d']=re.sub('USA(/|, ?)Saksa(/|, ?)Iso-Britannia','USA/Saksa/Iso-Britannia', v['d'])
	v['d']=re.sub('USA(/|, ?)Kanada(/|, ?)Iso-Britannia','USA/Kanada/Iso-Britannia', v['d'])
	v['d']=re.sub('Ranska(/|, ?)Iso-Britannia','Ranska/Iso-Britannia', v['d'])
	v['d']=re.sub('Saksa(/|, ?)UK(/|, ?)USA','Saksa/Iso-Britannia/USA', v['d'])
	v['d']=re.sub(', USA, Saksa, ',', USA/Saksa, ', v['d'])
	v['d']=re.sub('/Georgia, Viro',', Georgia/Viro', v['d'])
	v['d']=re.sub('/Britannia - USA',', Britannia/USA', v['d'])
	v['d']=re.sub('Kanada/USA, Saksa','Kanada/USA/Saksa', v['d'])

	v['d']=re.sub('\(7th Dwarf, The 2014\)', '(The 7th Dwarf, 2014)', v['d'])
	v['d']=re.sub('50/50', '50_50', v['d'])
	v['t']=re.sub('50/50', '50_50', v['t'])

	v['t']=re.sub('\.$','', v['t'])
	v['t']=re.sub('^Kummeli esittää: ','', v['t'])
	v['d']=re.sub(' Armi Toivanen, Riku$',r'',v['d'])
	v['d']=re.sub(' Vesa-Matti Loiri, Olavi Ahonen, Simo Salminen.$',r'',v['d'])

	v['d']=re.sub('^\(/\w+ (19|20)\d\d\). ','', v['d'])
	v['d']=re.sub('^Kaui ','Kausi ', v['d'])
	v['d']=re.sub('\. Ohjaus \w+ \w+$','', v['d'])
	v['d']=re.sub('(rikos), (trilleri)',r'\1/\2', v['d'])
	v['d']=re.sub('\(([\d\w ]+), The',r'(The \1,', v['d'])

	v['d']=re.sub('^\d{2,3} min\. | \d{2,3} min\.$','', v['d'])
	v['d']=re.sub('\. \d{2,3} min\. ','. ', v['d'])
	v['d']=re.sub(' \(\d+\'\)','',v['d'])
	print("DEBUG D:",v['d'])

	v['t']=fixstrings(v['t'])
	v['d']=fixstrings(v['d'])
	v['d']=re.sub(' \(\d+\'\)(.? )',r'\1', v['d'])
	v['d']=re.sub(',$',r'.',v['d'])

	v['d']=re.sub(', (Suomi (19|2[01])\d\d)',r', \1',v['d'])
	v['d']=re.sub(' T(: | - )[\wöä\- ]+[,\.]',r'',v['d'])
	v['d']=re.sub(' O(hjaus|hjaaja|hj)?(: | - |\. )[\wöä\-]+ ([\w]\. |van |von |\w+ )?[\wöä\-]+[\.,]',r'',v['d'])
	v['d']=re.sub(' [NP](ääosissa)?(: | - | )([\wöä\-]+ ([\w]\. )?[\wöä\-]+(, )?)+(\.|$)',r'',v['d'])

	a={}

	lookfor("Suomeksi puhut", v['d'])
	if has_match: v['t'] = "%s (Findub)" % (v['t'])
	v['d']=re.sub('Suomeksi puhuttu\. ',r'',v['d'])

	v['d'] = re.sub(r'^(.+)\. (Suomi (19|20)\d\d)\.(.+)$', '(\g<2>) \g<1>. \g<4>', v['d'], re.IGNORECASE)

	v['d']=re.sub('  ',r' ', v['d'])
	v['d']=re.sub('\.\. ',r'. ', v['d'])

	v['d']=re.sub('draama, musikaali','draama/musikaali', v['d'])

## Look for extra information from description
	if verbose: print("PRE d:",v['d'])
	s=re.search('^\((?P<dn>.+?)\)\.? (?P<d>.*)$', v['d'])
	if not s: s=re.search('^(?P<d>.*) \((?P<dn>[\d\wöäåÖÄÅøé\' ,:&\-]+?)\)$', v['d'])
	if not s: s=re.search('^(?P<dn>\(.+? [12][09]\d\d)\. (?P<d>.*)$', v['d'])
	if not s: s=re.search('\^(?P<d>.*)\. (?P<dn>\(.+? [12][09]\d\d)\)\.$', v['d'])
	if not s: s=re.search('\((?P<dn>.+? [12][09]\d\d)\)', v['d'])
	if not s: s=re.search('^(?P<dn>.*? [12][09]\d\d)\. ([OPN]: (([\w]+( \w\.)? [\w]+(, )?)+)\. )+(?P<d>.*)$', v['d'])
	if not s: s=re.search('^(?P<dn>.*? [12][09]\d\d)\. ([OP] - (([\w]+( \w\.)? [\w]+(, )?)+)\. )+(?P<d>.*)$', v['d'])
	if not s: s=re.search('^\((?P<dn>.+? [12][09]\d\d)\)\.$', v['d'])
	if s: v.update(s.groupdict())
	if verbose: print("POST d:",v['d'])
	if verbose and 'dn' in v: print("dn:",v['dn'])
#	if verbose: print show_vars(v)

	has_match=False
	lfcount=0
	if 'dn' in v:
		if not has_match: v.update(lookfor("^(?P<name>The[\d\wöäåÖÄÅøé\' :&\-\.\%]{1,50}?) (?P<year>(19|20)\d\d)$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<name>[\w\d\.\!\- ]{10,50}?) (?P<year>(19|20)\d\d)$", v['dn']))

		# Nimi, Genre?, Country, Year
		if not has_match: v.update(lookfor("((?P<genre>(toiminta|komedia|draama)), ?(?P<country>([\wöäåÖÄÅ\/\-]+?|Hong Kong)), ?(?P<year>(19|20)\d\d))$", v['dn']))

		# Nimi, Genre?, Country, Year
		if not has_match: v.update(lookfor("^(?P<name>([\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{1,50}?)), ?((?P<genre>([\wä\-\/ ]+)), ?)?(?P<country>([\wöäåÖÄÅ\/\-]+?|Hong Kong)), ?(?P<year>(19|20)\d\d)$", v['dn']))

		# Nimi, Country Year
		if not has_match: v.update(lookfor("^(?P<name>([\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{1,50}?)), (?P<country>([\wöäåÖÄÅ/\-]{1,40}?|Hong Kong)) (?P<year>(19|20)\d\d)\.?$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<name>([\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{1,50}?)), (?P<country>([\wöäåÖÄÅ/\-]{1,40}?|Hong Kong)), (?P<year>(19|20)\d\d)\.?$", v['dn']))

		# Nimi/Country Year
		if not has_match: v.update(lookfor("^(?P<name>([\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{1,50}?))/ ?(?P<country>[\wöäåÖÄÅ/\-]{1,40}?) (?P<year>(19|20)\d\d)\.?$", v['dn']))

		if not has_match: v.update(lookfor("^(?!Yhdysvallat)(?P<name>([\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{6,50}?)), (?P<year>(19|20)\d\d)\.?$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<country>[\wöäåÖÄÅ/\-]{1,30}?),? (?P<year>(19|20)\d\d)\.?$", v['dn']))

		if not has_match: v.update(lookfor("^(?P<name>[\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{6,50}?), (?P<country>\w+nen) (?P<genre>[\wä\-\/]+), (?P<year>(19|20)\d\d)$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<name>([\d\wöäåÖÄÅøé\' ,:&\-\.\!\%]{6,50}?)), (?P<genre>[\wä\-\/]+), (?P<year>(19|20)\d\d)$", v['dn']))

		if not has_match: v.update(lookfor("^(?P<name>[\d\wöäåÖÄÅøé\' :&\-\.\/]{6,50}?), (?!The|A)(?P<country>[\wöäåÖÄÅ\/\-]+?),? (?P<year>(19|20)\d\d)", v['dn']))

		if not has_match: v.update(lookfor("\. (?P<country>[\wöäåÖÄÅ\/\-]+) (?P<year>(19|20)\d\d)\.?$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<name>[^\.]{6,50}), (?P<country>[^\., ]+?) ((?P<year>(19|20)\d\d))?", v['dn']))

		if not has_match: v.update(lookfor("^(?P<year>(19\d\d|20[01]\d|2020)) (?P<dn>.*)$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<dn>.*) (?P<year>(19\d\d|20[01]\d|2020))$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<year>(19\d\d|20[01]\d|2020))(?P<dn>)$", v['dn']))
		if not has_match: v.update(lookfor("^(?P<name>[\d\wöäåÖÄÅøé\' :&\-\.\%]{1,50}?)$", v['dn']))
		v.update(lookfor("(?P<year>(19\d\d|20[01]\d|2020))\.?$", v['dn']))

		if 'name' in v and v['name'] in ['Ranska', 'Ruotsi']:
			if 'country' in v:
				v['country'] = "%s/%s" % (v['name'],v['country'])
			else:
				v['country'] = v['name']
			v['name']=None

		if v['dn'] == 'The Enforcer/Murder, Inc., USA':
			v['name'] = 'The Enforcer'
		if v['dn'] == 'V/H/S/2/USA-Kanada-Indonesia 2013':
			v['name'] = 'V/H/S/2'
			v['country'] = 'USA/Kanada/Indonesia'
			v['year'] = '2013'
	
	if verbose and has_match: print("LFCount:",lfcount)

	if 'd' in v:
		v.update(lookfor("(?P<country>Suomi),? (?P<year>(19\d\d|20[01]\d|2020))\.", v['d']))
		v.update(lookfor("[,\.]? (?P<year>(19\d\d|20[01]\d|2020))\.?$", v['d']))
		v.update(lookfor("^(?P<d>.*[\.\?\!]) (?P<country>[\wöäåÖÄÅ/\-]{1,40}?),? (?P<year>(19|20)\d\d)\.?$", v['d']))

## Detect type
	if 't' in v:
		(v['t'], i)=re.subn('^((Dokument|Theroux|Logged in|Stacey Dooley|Arkistomatka|Docstop|Sub.doc|JIM D|Docventures|MOT|Prisma|Historia|Inside|Tiededokumentti|Ulkomaanraportti|Ulkolinja):? ?)','\g<1>', v['t'])
		if i>0: v['type'] = 'document'

		(v['d'], i)=re.subn('^(Dokument)','\g<1>', v['d'])
		if i>0: v['type'] = 'document'

		(v['t'], i)=re.subn('^((Lyhyt)?[Ee]lokuva|Kotikatsomo|#?[\wöä]+leffa|(Uusi )?Kino ?(Suomi|Klassikko|Into|Tulio)?)(: | - )(Elokuva - )?','', v['t'])
		if i>0: v['type'] = 'movie'

	if 'name' in v and 't' in v:
# FAILS
# DEBUG D: (Der 7bte Zwerg, Saksa 2014. Seitsemän kääpiön kuopuksen Bobon
# re.error: missing ), unterminated subpattern at position 0

		try:
			v['t'] = re.sub('%s - (\w)' % (v['name']), str_toupper, v['t'])
		except:
			pass
	if ('t' in v and 'country' in v) and v['t'] == v['country']:
		del v['country']

	if 'series' in v and v['type'] == 'unknown':
		v['type'] = 'series'
		del v['series']['seriesId']
		if 'title' in v['series']:
			if v['t'] != v['series']['title']:
				print("WARNING: Inconsistent title:",v['t'],"!=",v['series']['title'])
				v['name'] = v['series']['title']

## Series
	if v['type'] in ["unknown", 'series']:
		has_match=False
		if not has_match and 'd' in v: v.update(lookfor('series', "Kausi (?P<season>\d+) ?[.,] ((Jakso|osa) )?(?P<episode>\d+)(/\d+)?([.,] (?P<eptitle>.{1,32}?))?(\. (?P<d>.*))?$", v['d']))
		if not has_match and 'd' in v: v.update(lookfor('series', "([Jj]akso|[Oo]sa) (?P<episode>\d+)(/\d+)?([.,] (?P<eptitle>.{1,32}?))?(\. (?P<d>.*))?$", v['d']))
		if not has_match and 'd' in v: v.update(lookfor('series', "^(?P<episode>\d+)(/\d+)?([.,] (?P<eptitle>.{1,32}?))?(\. (?P<d>.*))?$", v['d']))
		if not has_match and 'd' in v: v.update(lookfor('series', "(?P<season>\d+). kauden jaksot alkavat( uusintana)?\. (Jakso|osa) (?P<episode>\d+)(/\d+)?\. (?P<d>.*)$", v['d']))

		if not 'series' in v:
			v['series'] = { "title": v['t'] }
		if 'season' in v and v['season']:
			if not 'season' in v['series']:
				v['series']['season'] = v.pop('season')
			elif int(v['series']['season']) != int(v['season']):
				doLog("WARNING: inconsistency, season: %s != %s" % (v['season'], v['series']['season']))
			
		if 'episode' in v and v['episode']:
			if not 'episode' in v['series']:
				v['series']['episode'] = v.pop('episode')
			elif int(v['series']['episode']) != int(v['episode']):
				doLog("WARNING: inconsistency, episode: %s != %s" % (v['episode'],v['series']['episode']))
				v['series']['episode'] = "10%s" % (v['episode'])
			
		if 'eptitle' in v and v['eptitle']:
			if not 'eptitle' in v['series']:
				v['series']['eptitle'] = v.pop('eptitle')
			elif v['series']['eptitle'] != v['eptitle']:
				print("WARNING: inconsistency, eptitle:",v['eptitle'],'!=',v['series']['eptitle'])
			
		if has_match: v['type'] = 'series'
		if not v['d']: v['d'] = ''

## Movies
	if v['type'] in ["unknown", "movie"]:
		has_match = False
#		if not has_match: a=lookfor("Uusia jaksoja|Uusi kausi|Sarja alkaa", v['d'])
#		if not has_match: a=lookfor("(?<!Osa )(?P<episode>\d+)/\d+\. ?(?P<description>.+) (?P<season>\d+)\. tuotantokausi", v['d'])
#		if not has_match: a=lookfor("Kausi (?P<season>\d+)[.,] ?(Jakso )?(?P<episode>\d+)(/\d+)?\. ?((?P<eptitle>[\d\wöäåÖÄÅøé\' ,:&\-]{1,24}?)\.)? ?(?P<description>.*)$", v['d'])
#		if not has_match: a=lookfor("(Kausi (?P<season>\d+)[.,] ?(Jakso |osa )?)?(?<!Osa )(?P<episode>\d+)/\d+\. ?(?P<description>.*)$", v['d'])
#		if not has_match: a=lookfor("^(?P<episode>\d+)/\d+( - (?P<eptitle>.*?))?([\?!\.]+) (?P<description>.*)$", v['d'])
#		if not has_match: a=lookfor("^Osa (?P<episode>\d+)/\d+\. ?((?P<eptitle>[\d\wöäåÖÄÅøé\' &\-]{1,24}?)\.)? ?(?P<description>.*)$", v['d'])

#		if not has_match and 'dn' in v: a=lookfor("movie", "^(?P<country>(USA|Suomi|Ruotsi|Englanti|Ranska|Britannia|Korea|Japani|Saksa)(/(Ranska|Kanada))?),? (?P<year>(19|20)\d\d)(, \d+')$", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", "^\((?P<name>[\wöäåÖÄÅøé\' ,:&\-\.]{1,50}?)/(?P<country>[\wöäåÖÄÅ/\-]+?) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", "^\((?P<name>[\w ]+)\/(?P<country>[\wöäåÖÄÅ\/\-]{1,40}?) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", "^\((?P<name>[\w ]+)?\/(?P<country>[\wöäåÖÄÅ\/\- ]{1,40}?) (?P<year>(19|20)\d\d)\)\.? (?P<description>.*)$", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", "^(?P<name>.+?) (?P<year>(19|20)\d\d)$", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", "^\( ?(?P<year>(19|20)\d\d)\)\.? ", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", ", (?P<country>Suomi|USA)? ?(?P<year>(19|20)\d\d)\.? ?(?P<description>.*)$", v['dn'])
#		if not has_match and 'dn' in v: a=lookfor("movie", "^\(\w+\) (?P<description>.*\.) (?P<country>[\wöäåÖÄÅ/\-]{1,40}?) (?P<year>(19|20)\d\d)\.?$", v['dn'])


#		if not has_match and 'dn' in v: a.update(lookfor("^(?P<name>[\w ]+?)$", v['dn']))
#		a.update(lookfor("^(?P<d>.*\.) (?P<country>[\w/-]+) (?P<year>(19|20)\d\d)\.?$", v['d']))

#		if 'd' in a: v['d'] = a.pop('d')
#		if 'name' in a: v['name'] = a.pop('name')
#		if 'year' in a: v['year'] = a.pop('year')
#		if 'genre' in a: v['genre'] = a.pop('genre')
#		if 'country' in a: v['country'] = a.pop('country')
#		if 'dn' in v: del v['dn']


	if 'name' in v and v['name'] == 'Suomi':
		v['country'] = 'Suomi'
		del v['name']

# Remove empty keys
	tmpv = v.copy()
	for a in tmpv.keys():
		if not v[a]: del v[a]

## DEBUG
#	print("V",show_vars(v))
	v['t']=re.sub('American Pie: The Naked Mile',r'',v['t'])
	if not 'name' in v or not v['name']:
		v['name'] = v['t']
	if v['name'] == v['t']:
		del v['t']

	if 'series' in v and 'title' in v['series']:
		v['series']['title']=re.sub('^(The|A) (.+)',r'\2, \1',v['series']['title'])
	v['name']=re.sub('^(The|A) (.+)',r'\2, \1',v['name'])

	if 'genre2' in v:
		if v['genre2']: v['genre'] = v.pop('genre2')
		else: del v['genre2']
	if 'genre' in v and v['genre'] in ["tosi-tv", "kotimainen tosi-tv"]: v['type']='series'
	if 'genre' in v and v['genre']:
		if re.search("/", v['genre']): v['genre'] = ", ".join(v['genre'].split("/"))
		elif re.search("-(?!tv)", v['genre']): v['genre'] = ", ".join(v['genre'].split("-"))

	if 'genre' in v:
		if not 'genres' in v: v['genres'] = []
		for g in v['genre'].lower().split(', '):
			if not g in v['genres']:
				v['genres'].append(g)

	if 'country' in v and (v['country'][-6:] == "mainen" or v['country'][-6:] == "lainen"): v['country']=v['country'][:-6]
	if 'country' in v:
		if v['country'] == "koti": v['country']="Suomi"
		elif v['country'] == "amerikka": v['country']="USA"
		if re.search("/", v['country']): v['country'] = ", ".join(v['country'].split("/"))
		elif re.search("(?!Iso|Uusi)-", v['country']): v['country'] = ", ".join(v['country'].split("-"))

		if v['country'] in ['Burnt', 'Deep', 'Brave']:
			v['t'] = v['name']
			v['name'] = v['country']
			del v['country']

	if v['type'] in 'unknown':
		if 'name' in v and 'year' in v and 'country' in v: v['type']='movie'

## Format filepath and name
	if 'series' in v and 'episode' in v['series']:
		if 'title' in v['series']:
			fnSeries = "%s" % (v['series']['title'])
		else:
			fnSeries = "%s" % (v['name'])

		if 'series' in v and 'season' in v['series'] and v['series']['season']:
			fnSeason="Season %d" % (int(v['series']['season']))
		else:
			fnSeason=''
		
		fnTitle = "%s - " % (fnSeries)
		if 'season' in v['series'] and v['series']['season']:
			fnTitle = "%sS%02d" % (fnTitle, int(v['series']['season']))
		if 'episode' in v['series'] and v['series']['episode']:
			fnTitle = "%sE%02d" % (fnTitle, int(v['series']['episode']))
		if 'eptitle' in v['series'] and v['series']['eptitle']:
			fnTitle = "%s - %s" % (fnTitle, v['series']['eptitle'])

		filename="%s/%s/%s" % (pathfix(fnSeries), pathfix(fnSeason), pathfix(fnTitle))
	else:
		if not 'name' in v:
			if 'year' in v:
				filename = "%s (%s)" % (v['t'], v['year'])
			else:
				filename = "%s" % (v['t'])
		else:
			filename = "%s" % (v['name'])
			if 'year' in v:
				filename = "%s (%s)" % (filename, v['year'])
			if 't' in v and v['t']:
				filename = "%s - %s" % (filename, v['t'])
		filename=pathfix(filename)
		filename=re.sub('/','_',filename)
	filename=re.sub('\.$','',filename)
	

# DISABLE: Add character dir before movie name
#	if v['type'].lower() == 'movie':
#		if filename[0].lower() in "0123456789abcdefghijklmnopqrstuvwxyz":
#			filename = "%s/%s" % (filename[0].lower(), filename)
#		else:
#			filename = "%s/%s" % ('_', filename)

	filename = "%s/%s" % (v['type'].lower(), filename)

	v['strtime'] = "%s%s%s_%s%s" % (v["startTime"][0:4], v["startTime"][5:7], v["startTime"][8:10], v["startTime"][11:13], v["startTime"][14:16])
	if v['type'] not in ["movie"]:
		if 'series' in v:
			if not 'eptitle' in v['series'] and not 'episode' in v['series']:
				filename="%s (%s)" % (filename, v["strtime"])
		else:
			filename="%s (%s)" % (filename, v["strtime"])

### FIX *** Names
	filename=re.sub('\*\*\*','___',filename);

#	if verbose: print show_vars(v)
	return fixstrings(filename)
	sys.exit(0)









### -----------------------------------------------------------------------
### Support functions
### -----------------------------------------------------------------------

def lookYesNo(test):
	if test in ['false','off','no']: return False
	if test in ['true','on','yes']: return True
	return None

def osfilename(fn):
	return str(fn)
#	return fn.encode(sys.getfilesystemencoding())

## Save python variable to file
def save_vars(var, fname, id=None):
	fp = open(fname, "w+")
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

def doLog(t=None):
	print(t)
	if not os.path.exists("elisa-dl.conf"):
		return
	file=open("elisa-dl.log", 'a')
	file.write(t+"\n")
	file.close()
	return

### -----------------------------------------------------------------------
### Functions related to API communication
### -----------------------------------------------------------------------

def doApiProcess(ret = None):
	global fatalErrors

	r={}
	r['status'] = ret.status_code
	r['reason'] = ret.reason
	r['headers'] = {}

	if ret.status_code != 200:
		doLog("API ERROR %d: %s" % (ret.status_code,ret.reason))

		return r

		print("URL:",ret.url)
		print(show_vars(r))
#		print("Headers:",ret.headers)
		echo

		fatalErrors = fatalErrors + 1

		if fatalErrors > 2:
			doLog("Too many fatal errors %s, can't retry" % fatalErrors)
			sys.exit(1)
		doLog("Retry sleep after fatal error (1 minute)")
		time.sleep(60)
		return None

	for b in ret.headers:
		if b in ['Content-Type','Set-Cookie','X-RateLimit-Remaining-second','X-RateLimit-Remaining-minute','X-RateLimit-Limit-second','X-RateLimit-Limit-minute']:
			r['headers'][b] = ret.headers[b]
	
	if 'X-RateLimit-Limit-minute' in r['headers']:
		r['headers']['X-RateLimit-Limit-second'] = ret.headers['X-RateLimit-Limit-second']
		r['headers']['X-RateLimit-Remaining-second'] = ret.headers['X-RateLimit-Remaining-second']
		r['headers']['X-RateLimit-Limit-minute'] = ret.headers['X-RateLimit-Limit-minute']
		r['headers']['X-RateLimit-Remaining-minute'] = ret.headers['X-RateLimit-Remaining-minute']

# Print ratelimit information, for debug purpouses when doing multiple requests
#	print("RateLimit:",)
#	print("sec: "+r['headers']['X-RateLimit-Remaining-second']+'/'+r['headers']['X-RateLimit-Limit-second'],)
#	print("min: "+r['headers']['X-RateLimit-Remaining-minute']+'/'+r['headers']['X-RateLimit-Limit-minute'])

	try:
		if int(r['headers']['X-RateLimit-Remaining-second']) < 1:
			print("Requests per second left: "+r['headers']['X-RateLimit-Remaining-second']+'/'+r['headers']['X-RateLimit-Limit-second'])
#			print("Throttling because RateLimit")
			time.sleep(1)
		if int(r['headers']['X-RateLimit-Remaining-minute']) < 20:
			print("Requests per minute left: "+r['headers']['X-RateLimit-Remaining-minute']+'/'+r['headers']['X-RateLimit-Limit-minute'],)
			print("Throttling because RateLimit")
			time.sleep(10)
	except:
		pass
#	print("/doApiProcess()")
	return r

# API POST function
def doApiPost(url, data=false, nologin=False, reqHeaders=False):
	global auth

# **TODO** Check if used in config
	if disableAPI:
		print("_doApiPost()")
		return (None, None)

	if not reqHeaders:
		reqHeaders = {}
		reqHeaders["content-type"] = "application/json; charset=UTF-8"
	reqHeaders["apikey"] = config['apikey']

# Verify that we are logged in
	if not nologin:
		auth=login()
	if not auth:
		reqHeaders['content-type'] = 'application/x-www-form-urlencoded'
	else:
		reqHeaders["Authorization"] = auth["Authorization"]

#	print("RH:", reqHeaders)
#	print("Data:", data)
#	print("URL:", url)
	if data:
		ret = requests.post(url, data=data, headers=reqHeaders)
	else:
		ret = requests.post(url, headers=reqHeaders)

	r = doApiProcess(ret)
	s = json.loads(ret.text)
	return (r,s)

# API GET function
def doApiGet(url, data=false, nologin=False):
	global auth

	if disableAPI:
		print("_doApiProcess()")
		return (None, None)
# Verify that we are logged in
	if not nologin:
		auth=login()
	if not auth:
		doLog("Missing Authentication")
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
		if "expires" in token and float(token["expires"]) <= float(time.time()):
			del token['access_token']
	if not 'access_token' in token:
		payload = {
			'grant_type': 'authorization_code',
			'username': config['username'],
			'password': config['password'],
			'client_id': 'external',
			'code': getAccessCode()
		}
		(r, s) = doApiPost('https://api-viihde-gateway.dc1.elisa.fi/auth/authorize/access-token', payload, nologin=True)

		if s['response_type'] != 'token':
			doLog("Invalid access token")
			sys.exit(1)

		token['token_type'] = str(s['token_type'])
		token['access_token'] = str(s['access_token'])
		token['refresh_token'] = str(s['refresh_token'])
		token['expires'] = "%.0f" % (float(time.time()) + float(s['expires_in']))
		save_vars(token, "var/access.var")
	return "%s %s" % (token['token_type'], token['access_token'])

# login function should return headers to do authorization
def login():
	return {'Authorization': getAccessToken(), 'apikey': config['apikey']}

### -----------------------------------------------------------------------
### Tools
### -----------------------------------------------------------------------
def testVar(varFile = None):
	if not varFile:
		print("You must give -var file as parameter")
		sys.exit(1)
	varFile=info2var(varFile)
	if os.path.exists("%s.var" % (varFile)):
		varData=load_vars("%s.var" % (varFile))
	elif os.path.exists("%s-var.txt" % (varFile)):
		varData=load_vars("%s-var.txt" % (varFile))
	else:
		print("%s is not var-file or it is broken" % varFile)
		sys.exit(1)

##	if varD'channelName' in ata: print("Channel:",varData["channelName"])
##	if varD'showType' in ata: print("Type:",varData["showType"])
##	else: varData["showType"] = None
##	print("Start:",varData["startTime"])
##	print
##	print("Title:",varData['name'])
##	print("Description:")
##	print varData['description']
##	print

#	toFile=fixname(varData, verbose=False)
	toFile=fixname(varData, verbose=True)
	print(toFile)
	return

def loadConfig():
	global config

	if sys.platform == 'win32':
		config['os']="win"

	if not os.path.exists("elisa-dl.conf"):
		print("You should copy elisa-dl.sample.conf to elisa-dl.conf")
		print("And edit it to contain your Elisa-Viihde username and password")
		print("Also you need to provide apikey")
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
		a=re.search('^dupedir\s*=\s*(?P<dupedir>[\d]+)',line,re.IGNORECASE)
		if a:
			config['dupedir']=int(a.groupdict()['dupedir'])
		a=re.search('^faildir\s*=\s*(?P<faildir>[\d]+)',line,re.IGNORECASE)
		if a:
			config['faildir']=int(a.groupdict()['faildir'])
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

		a=re.search('^download\s*=\s*(?P<nodownload>[\w\d]+)',line,re.IGNORECASE)
		if a and not lookYesNo(a.groupdict()['nodownload']):
				config['noDownload']=True

		a=re.search('^loopsleep\s*=\s*(?P<loopsleep>[\w\d]+)',line,re.IGNORECASE)
		if a:
			config['loopsleep']=int(a.groupdict()['loopsleep'])
			if config['loopsleep'] < 10: config['loopsleep'] = 10

		a=re.search('^dry_run\s*=\s*(?P<dry_run>[\w\d]+)',line,re.IGNORECASE)
		if a:
			config['dry_run']=lookYesNo(a.groupdict()['dry_run'])

	fp.close()

	return config

### -----------------------------------------------------------------------
### Tools
### -----------------------------------------------------------------------
# Check if we have quit conditions, for nice end of the program.
def checkQuit():
	if os.path.exists("/quit") or os.path.exists("quit"):
		doLog("Quit requested")
		
		return True
	return None

### -----------------------------------------------------------------------
### doDownload
### -----------------------------------------------------------------------
def doDownload(filename, recordingUrl, programId, bitrate=None):
# I wish this would work, but no... youtube-dl crashes because utf8 encoding problems
#	filename = osfilename(filename)

# Not Dupe, clean first-time download
# Limit bitrate to 7Mbit and sub FullHD resoluition, if available.
	filt_video='bestvideo[ext=mp4][height=720]/bestvideo[ext=mp4][tbr<=?6900]/bestvideo[ext=mp4][width<=1920][height<=1080]/bestvideo[ext=mp4]'

# Limit audio to 192 aac, prefer Finnish track first, always try skip eac3 because problems with ffmpeg
	filt_audio="bestaudio[format_id*=aacl-192][format_id*=Finnish]/bestaudio[format_id*=AACL_mul_192]/bestaudio[format_id*=audio-aacl-192-Multiple_languages]/bestaudio[format_id!=audio-ec-3-224-Multiple_languages]/bestaudio"

#	if 1: # force_hd
#		filt_video='bestvideo[ext=mp4]'

# You should use native HLS with this, because of eac3
	#filt_video='bestvideo'
	#filt_audio='bestaudio[format_id*=ec-3]/bestaudio[format_id*=aacl-192]/audio-aacl-192-Multiple_languages/bestaudio'

	cmd = "youtube-dl"

# Select ONE HLS downloaders! Notice, ffmpeg can't handle eac3 audio but native could have audio problems
	cmd = "%s %s" % (cmd, '--hls-prefer-ffmpeg --external-downloader-args "-stats -hide_banner -loglevel warning"')
# Audio problems with this one! Be careful!
#	cmd = "%s %s" % (cmd, '--hls-prefer-native')

# Filters
	if not bitrate:
		cmd = "%s -f \"(%s)+(%s)\"" % (cmd, filt_video, filt_audio)
	else:
		cmd = "%s -f \"(%s)+(%s)\"" % (cmd, bitrate, filt_audio)
# Output
	cmd = "%s -o \"%s.%%(ext)s\"" % (cmd, filename)
# URL
	cmd = "%s \"%s\"" % (cmd, recordingUrl)

# Get with ffmpeg, 'copy-as-is', best video and audio, BIG file!
# On Windows system this can cause problems, I have one report about it.
# This OVERIDES everything above!
#	cmd = 'ffmpeg -i \"%s\" -c copy \"%s.mp4\"' % (recordingUrl, filename)

# USE ViihdeX-dl.py by Qotscha
	cmd = 'python3 ViihdeX-dl.py \"%s\" \"%s\" -e' % (recordingUrl, filename)

# Do not download, yet...
	if os.path.exists("no-download") or config['noDownload']:
		print("   Downloading disabled from config")
		return None
# Print and log
#	doLog("Downloading %s: %s.mp4" % (programId, filename))

# Write our status to elisa-dl-cmd.log
	file=open("elisa-dl-cmd.log", 'w')
	file.write("%s\n" % cmd)
	file.close()
	retr = subprocess.call(cmd, shell=True)

## Quit if Download process does not success
	if retr:
		doLog("ERROR With Download %s: %s.mp4\n" % (programId, filename))
		sys.exit(1)
		moveRecord(programId, folderId=config['faildir'])
		return None

	return filename

# Move programId to another folderId
def moveRecord(programId, folderId=config['donedir'], fromFolder=None):
	global fullData

	if not auth:
		doLog("Missing Authentication")
		sys.exit(1)

	if config['dry_run']:
		doLog("moveRecord: Moving %s to %s" % (programId, folderId))
		return

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

	if not 'program' in fullData: fullData=cacheFullData()
	for folderId in fullData['folder']:
		if 'doDirs' in config and folderId not in config['doDirs']:
			continue
		if folderId in [config['donedir'], config['faildir'], config['dupedir']]:
			continue
		doLog("Processing folder '%s' (%d)" % (fullData['folder'][folderId]['name'], folderId))
		if fullData['folder'][folderId]['count'] < 1: continue

		getInSortedOrder = False
		# Sort in title order and retrieve by it


#		print("Do Loop")
		if getInSortedOrder:
#			print("getInSortedOrder")
			nameMap = {}
			tmpData = fullData['program']
			for programId in fullData['program']:
				if not 'folderId' in fullData['program'][programId]:
					fullData['program'][programId]['folderId'] = 0
				if int(fullData['program'][programId]['folderId']) != int(folderId): continue
				nameMap[programId] = fullData['program'][programId]['name']

			alphaSort = []
#			print("For Loop")
			for programId in sorted(nameMap, key=nameMap.__getitem__):
				print()
#				print("getProgram",programId)
				getProgram(programId)
				if checkQuit(): return
			if checkQuit(): return
		else:
#			print("Plan B")
			try:
				for programId in fullData['folder'][folderId]['programs']:
					print()
#					print("getProgram",programId)
					getProgram(programId)
					if checkQuit(): return
			except:
				pass
			if checkQuit(): return
	return

### -----------------------------------------------------------------------
### Func: fileRename
### -----------------------------------------------------------------------
def fileRename(doFile = None, toTarget = None, forced=False, dupe=False):
	if not doFile:
		print("You must give file as parameter")
		sys.exit(1)

	if not toTarget:
		varData={}
		print(doFile)
		doFile=info2var(doFile)
		nameDir, nameFile = os.path.split(doFile)

		if os.path.exists("%s.var" % (doFile)): varFile="%s.var" % (doFile)
		else: varFile="%s-var.txt" % (doFile)
		try:
			if not varData or len(varData) < 3: varData=load_vars(varFile)
		except IOError as err:
			doLog("%s: %s.var" % (err.strerror, doFile))
			sys.exit(1)

		toFile=fixname(varData)
		toDir, toFName = os.path.split(toFile)
		if not nameDir: toFile = toFName
	else:
		toFile = toTarget[0]
		toDir, toFName = os.path.split(toTarget[0])
		doFile = re.sub('(-formats|-var)?\.(txt|mp4|var|info)?$', '', doFile)

	childFiles=glob.glob(doFile+"[-.]*")
	if len(childFiles) > 7:
		doLog("FATAL: More then 7 files matches with %s. Too dangerous, please verify." % doFile)
		sys.exit(1)

	FixName=doFile
	FixName=re.sub('\(','\(',FixName)
	FixName=re.sub('\)','\)',FixName)
	FixName=re.sub('\[','\[',FixName)
	FixName=re.sub('\]','\]',FixName)

	# Loop all thru first, just to make sure that target does not exist
	fatal=None

	isDupe=False
	for fromFile in childFiles:
		ext=re.sub(FixName, '', fromFile)
		if os.path.exists('%s%s' % (toFile, ext)) and ext not in ['.var','-var.txt']:
# RENAME DUPE		toFile="%s (%s)" % (toFile, v['strtime'])
			isDupe=True
		if isDupe and os.path.exists('%s%s' % (toFile, ext)) and ext not in ['.var','-var.txt']:
			doLog("Target exists: %s%s" % (toFile, ext))
			if forced:
				os.remove('%s%s' % (toFile, ext))
				continue
			return
#			fatal=True
#			break
#	if fatal: return

	nameDir, nameFile = os.path.split(toFile)
	if not nameDir: nameDir="."

	try:
		if nameDir and not os.path.exists(toDir):
			os.makedirs(toDir, 0o775)
	except IOError as err:
		doLog("%s: %s" % (err.strerror, doDir))
		sys.exit(1)

	for fromFile in childFiles:
		ext=re.sub(FixName, '', fromFile)
		if 1:
#			doLog("'%s' -> '%s%s'" % (fromFile, toFile, ext))
			if config['debugmode']:
				break
			os.rename(fromFile, "%s%s" % (toFile, ext))
	return












### -----------------------------------------------------------------------
###
### -----------------------------------------------------------------------

def findProgram(doFile = None):
### **TODO** REWORK THIS
#	if not doFile:
#		print("You must give file as parameter")
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
#			oldName="%s (%s)" % (re.sub('^(AVA |\w+)?(#Subleffa|Sub Leffa|Elokuva|leffa|torstai|perjantai)(:| -) | \(elokuva\)|Kotikatsomo(:| -) |R&A(:| -) |(Dokumenttiprojekti|(Kreisi|Toiminta)komedia|(Hirviö|Katastrofi|Kesä)leffa|Lauantain perheleffa)(:| -) |^(Uusi )?Kino ?(Klassikko|Kauko|Suomi|Into|Helmi|Tulio|Rock|Teema)?(:| -) ?','',prog['name']), re.sub(r'(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):\d\d','\g<1>\g<2>\g<3>_\g<4>\g<5>',prog['startTime']))
#			newDir, newName=os.path.split(fixname(prog))
#
##			print("Old",oldName)
##			print("Find",nameFile)
##			print("New",newName)
##			print
#
#			if nameFile == oldName or  nameFile == newName:
#				if nameDir:
#					save_vars(prog, nameDir+"/"+osfilename(nameFile)+'.var')
#				isFound = True
##			if isFound: break
##		if isFound: break
#	if isFound: fileRename(nameDir+"/"+osfilename(nameFile)+'.var')
#	if not isFound:
#		print("Can't find information about", nameFile)
	return











### -----------------------------------------------------------------------
### Func: getProgram
### -----------------------------------------------------------------------
def getProgram(programId, tmpdir="tmp"):
	global fatalErrors

	print
	print("Processing",programId,)
	try:
		program = fullData['program'][int(programId)]
	except:
		print("Can't find %s from database, maybe not suitable format found?" % programId)
		return

	if fullData['program'][int(programId)]['recordingState'] not in ['finished']:
		print("Program recording is not yet finnished.",fullData['program'][int(programId)]['progress'],"%")
		return
	recAge=round(time.time()-(int(program['endTimeUTC'])/1000), 0)/60
	if recAge < int(config['getAge']):
#		print("All formats may not be available yet.")
		doLog("Record %d (%s) is only %d minutes old (< %d min)." % (programId, fullData['program'][int(programId)]['name'], int(recAge), int(config['getAge'])))
		time.sleep(1)
		return

	fromFolder=None
	for folderId in fullData['folder']:
		if not 'programs' in fullData['folder'][folderId]: continue
		if int(programId) in fullData['folder'][folderId]['programs']:
			program=fullData['folder'][folderId]['programs'][int(programId)]
			fromFolder=folderId
			break
		if fromFolder: break
	if checkQuit(): return # /InfiniteLoop

# **TODO** We have this now in three different places, we should make function out of this
#	try:
	fullFileName=fixname(program)
	fileDir, fileName=os.path.split(fullFileName)
#	except:
#	print
#	print("fixname function failed. Can't make filename")
#	print(show_vars(program))
#	print(program['name'])
#	sys.exit(1)

	if not 'showType' in program:
		a=re.search('^(?P<showType>.+?)/', fullFileName)
		if a:
			program['showType']=a.groupdict()["showType"]
		else:
			program['showType']="unknown"

#	print(fileName)
	showType=program["showType"].lower()

# We can't check if file does exist, before we really know FULL name (with eptitle)
	storagePath=""
	if showType in ['other']: showType='unknown'
#	if os.path.exists("/share/plex1/%s" % (showType)):
#		storagePath="/share/plex1/"
#	elif os.path.exists("/share/plex2/%s" % (showType)):
#		storagePath="/share/plex2/"
#	elif os.path.exists("/share/plex3/%s" % (showType)):
#		storagePath="/share/plex3/"
#	elif os.path.exists("/share/plex4/%s" % (showType)):
#		storagePath="/share/plex4/"
#	elif os.path.exists("/share/Archive/%s" % (showType)):
#		storagePath="/share/Archive/"
#	else:
	storagePath="./"
	fullFileName="%s%s" % (storagePath, fullFileName)
#	doLog("Full filename: %s.mp4" % osfilename(fullFileName))
# DISABLED
#	tmpdir = "%s%s" % (storagePath, tmpdir)
	if not os.path.exists(tmpdir): os.makedirs(tmpdir, 0o775)
	tmpFile = osfilename("%s/%s" % (tmpdir, fileName))

	if os.path.exists("%s.mp4" % (tmpFile)):
		doLog("Exists %s: %s.mp4\n" % (programId, fullFileName))
		if config['dupedir']:
			moveRecord(programId, config['dupedir'])
#		doLog("Move from temp %s: %s.mp4\n" % (programId, fullFileName))
# DISABLED
#		fileRename("%s.mp4" % (tmpFile), toTarget = [fullFileName, fileName, storagePath, program["showType"].lower()], forced=True, dupe=True)
		return

	savePaths = {
		".",
		"/share/plex2/elisa/"+showType,
		"/share/plex2/"+showType,
		"/share/plex2/w_"+showType,
	}

# FIX
	fname=re.sub(storagePath+showType+"/", '', fullFileName)
	print(fname)

	isDupe=False
	if os.path.exists("%s.mp4" % (fullFileName)):
#		print("  IS DUPE")
		dupeFile="%s.mp4" % (fullFileName)
		isDupe=True
	else:
		for fpath in sorted(savePaths):
#			print("TEST %s/%s.mp4" % (fpath, fname))
			if os.path.exists("%s/%s.mp4" % (fpath, fname)):
#				print("  FOUND")
				dupeFile="%s/%s.mp4" % (fpath, fname)
				isDupe=True

	if isDupe and (os.path.exists("%s.info" % (fullFileName)) or os.path.exists("%s.subs_ts" % (fullFileName)) or os.path.exists("%s.srt" % (fullFileName))):
		doLog("DUPE %s: %s (Way too old original, force download)" % (programId, dupeFile))
	elif isDupe:
# We did find file with same on our disk.  Check that our old file has at
# least 720px height.  (Needs hachoir utilities).  Otherwise, mark as dupe.
		dupeHeight = ""
		dupeWidth = ""
		try:
#			parser = createParser(unicodeFilename(dupeFile, getTerminalCharset()), dupeFile)
			parser = createParser(dupeFile, dupeFile)
			metadata = extractMetadata(parser)
			dupeDur=metadata.get('duration')
			dupeWidth=metadata.get('width')
			dupeHeight=metadata.get('height')

			doLog("DUPE %s: %s (%s, %sx%s)" % (programId, dupeFile, dupeDur, dupeWidth, dupeHeight))

			# Try find better version if our version is less then 1080p
			if dupeHeight and not (dupeHeight < 1080):
				# Our version is good enough, mark this as dupe
				if config['moveDupes']:
					if config['dupedir']:
						moveRecord(programId, config['dupedir'], fromFolder)
					elif config['moveDupes'] and config['donedir']:
						moveRecord(programId, config['donedir'], fromFolder)
				return
		except:
# Getting data failed, probably >4GB file, OR hachoir fails... Move source fo faildir
			doLog("DUPE %s: Getting %s metadata failed." % (programId, dupeFile))
			moveRecord(programId, folderId=config['faildir'])
			return


# Verify that target directory does exist
#	if not os.path.exists(osfilename(fileDir)): os.makedirs(osfilename(fileDir), 0o775)
	save_vars(program, tmpFile+".var")
# Disable writing of description, no usage for it? Also we have -var file.
#	file=open(tmpFile+'.txt', 'w')
#	file.write(program['description'].encode('utf8'))
#	file.close()

# Verify that we are logged in
	auth=login()

# Retrieve download URL for program
#	url=apiUrl+'/recordings/url/'+str(programId)+'?platform='+platformFormat+'&'+apiVer
# NEW API
	url=apiUrl+'/recordings/info/'+str(programId)+'?platform=online&includeMetadata=true&'+apiVer
#	print(url)
	(r, recordingUrl) = doApiGet(url)

#	if r["status"] == 400:
#		doLog("ERROR 400 With Download %s: %s.mp4\n" % (programId, fileName))
#		sys.exit(1)
#		time.sleep(2)
#		moveRecord(programId, folderId=config['faildir'])
#		return None
#	if r["status"] == 404:
#		return None
	if r["status"] != 200:
		doLog("FATAL: ERROR %s With Download %s: %s.mp4\n" % (r["status"], programId, fileName))
		sys.exit(1)

	brToDl = None
# Check with youtube-dl if we have better version(s) available.
# NOTE! THIS NEED TO RECHECK/FIX
	if 0:
###	try:
		if isDupe and dupeHeight:
			if not os.path.exists(osfilename(fileName)+"-formats.txt"):
				cmd='youtube-dl --list-formats \"'+recordingUrl['url']+'\"'
				file=open(osfilename(tmpFile)+'-formats.txt', 'w')
				strFormats=subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
				file.write(strFormats)
				file.close()

			file=open(osfilename(tmpFile)+'-formats.txt', 'r')
			fmt = {}
			for l in file:
				m=re.match(r'^\s*(?:[^\s]+[\s]+){2}(\d+)x(\d+)', l)
				if m is not None:
					fmt_width=m.group(1)
					fmt_height=m.group(2)
				
# Download by bitrate, NOTE!  We should use first column as format id, not
# REAL bitrate like we do it now.  But these seems to be same at least for
# now.
					fmt_bitrate=re.match(r'^\s*(?:[^\s]+[\s]+){3}(\d+)k', l).group(1)
					fmt[int(fmt_bitrate)] = {"w":fmt_width, "h":fmt_height}
			file.close()

#			print("Available formats ",fmt)
			for br in sorted(fmt, reverse=False):
# Downloadable height is less then our local
				if int(fmt[br]["h"]) < int(dupeHeight): continue

# We have at least something to download (brToDl)
# Height is better or equal of MinHeight
# And Bitrate is maxium of...
# ... If Bitrate is too high and/or Height is not enough, we should DL anyway, because brToDl is not set.
				if brToDl and (int(fmt[br]["h"]) >= 720) and (br >= 6900):
					break
				brToDl = br

			if not brToDl:
				print("No better resolution available, consider as full dupe")
				moveRecord(programId, folderId=config['dupedir'])
				return None
###	except:
			doLog("DUPE %s: Getting available formats failed." % (programId))
			moveRecord(programId, folderId=config['faildir'])
			return None

	auth=login()
# Retrieve download URL for program
#	url=apiUrl+'/recordings/url/'+str(programId)+'?platform='+platformFormat+'&'+apiVer
#	(r, recordingUrl) = doApiGet(url)
# NEW API
	url='https://watchable-api.dc.elisa.fi/V3/recordings/play-options/'+str(programId)+'/ios'
	payload = '{"cdnServiceOptions":["s_ttml"],"protocol":"hls","applicationVersion":"1","deviceId":"123","drmPlatform":"ios"}'
	(r, recordingUrl) = doApiPost(url, payload, reqHeaders={'content-type': 'application/json; charset=UTF-8'})

	if r["status"] != 200:
		doLog("FATAL: ERROR %s With Download %s: %s.mp4\n" % (r["status"], programId, fileName))
		sys.exit(1)

	if isDupe:
		print("\tLocal file date: %s" % (datetime.fromtimestamp(os.path.getmtime(dupeFile))))
	if isDupe and (datetime.fromtimestamp(os.path.getmtime(dupeFile)) > too_old):
#		print("DUPE %s: %s (Local file is not expired yet)" % (programId, dupeFile))
		if config['dupedir']:
			moveRecord(programId, config['dupedir'])
		return

	
	if brToDl:
		isDupe=True
		doLog("Download %s: %s.mp4 (bitrate %s, %sx%s)" % (programId, osfilename(fullFileName), brToDl, fmt[brToDl]['w'], fmt[brToDl]['h']))
		if not config['dry_run']:
			tmpFile = doDownload("%s" % (tmpFile), recordingUrl['requestRouterUrl'], programId, bitrate=brToDl)
	else:
		doLog("Download %s: %s.mp4" % (programId, osfilename(fullFileName)))
		if not config['dry_run']:
			tmpFile = doDownload("%s" % (tmpFile), recordingUrl['requestRouterUrl'], programId)
		
	if tmpFile:
		if config['donedir']:
			moveRecord(programId, config['donedir'])
		if os.path.exists(osfilename(fileName)+"-formats.txt"):
			os.remove(osfilename(fileName)+"-formats.txt")
# DISABLED
		if not config['dry_run']:
#			fileRename("%s.mp4" % (tmpFile), toTarget = [fullFileName, fileName, storagePath, program["showType"].lower()], forced=isDupe)
# NOTE! If there is dupe, this will FORCE override!
# We need config option for this!
			fileRename("%s.mp4" % (tmpFile), toTarget = [fullFileName, fileName, storagePath, program["showType"].lower()], forced=isDupe)
#			fileRename("%s.mp4" % (tmpFile))
#	print("DEBUGGER")
#	print("From",tmpFile)
	print("Target", [storagePath, program["showType"].lower()], fileName)
	return


### -----------------------------------------------------------------------
### Cache/Get Data
### -----------------------------------------------------------------------
def cacheProgramData(folderId, force=None):
	global apiUrl, apiVer

	if force or not config['usecache'] or not os.path.exists("var/cache-fData-%d.var" % folderId):
#		(r, getData) = doApiGet(apiUrl+'/recordings/folder/'+str(folderId)+'?platform=external&'+apiVer+'&page=0&pageSize=10000&includeMetadata=true')
		(r, getData) = doApiGet(apiUrl+'/recordings/folder/'+str(folderId)+'?platform='+platformFormat+'&'+apiVer+'&page=0&pageSize=10000&includeMetadata=true')
		if (r["status"] != 200):
			doLog("Failed to load recording data for folder %d" % (folderId), r["status"])
			sys.exit(1)
		rData = {}
		for rGetData in getData["recordings"]:
			rData[rGetData["programId"]] = rGetData
		save_vars(rData, "var/cache-rData-%d.var" % folderId)
	varData=load_vars("var/cache-rData-%d.var" % folderId)
	return varData

def cacheFolderData(force=None):
	global apiUrl, apiVer

	if force or not config['usecache'] or not os.path.exists("var/cache-fData.var"):
		(r, getData) = doApiGet(apiUrl+'/folders'+'?platform=external&'+apiVer)
		if (r["status"] != 200):
			doLog("Failed to load folders data",getData.status_code)
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
			if 'doDirs' in config and folderId not in config['doDirs']: continue
#			print("Reading directory %d: %s" % (folderId, fullData['folder'][folderId]['name']))
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
#
# COMMANDS:
# test/filename
# rename( test)?
# get
# refresh
# lookup/find
#
# Show metadata from var- file
	if not sys.argv[1:]:
		pass
	elif sys.argv[1:][0] == "t" or sys.argv[1:][0] == "d":
		do_title=False
		if sys.argv[1:][0] == "t": do_title=True
		del sys.argv[0]
		del sys.argv[0]
		t = {'name': '','description': ''}
		if do_title:
			t['name']=t['name'].join(sys.argv)
#			print("ORIG:",t['name'])
		else:
			t['description']=t['description'].join(sys.argv)
#			print("ORIG:",t['description'])
		fixname(t)
		sys.exit(0)
	elif sys.argv[1:][0] == "filename" or sys.argv[1:][0] == "test":
		if len(sys.argv) >= 3:
			testVar(sys.argv[2:][0])
			sys.exit(0)
# Rename files by data from var- file
	elif sys.argv[1:][0] == "rename":
		del sys.argv[1]
		if sys.argv[1:][0] == "test":
			config['debugmode']=True
			del sys.argv[1]
			print("NOTE! Debug mode [ON]")

		if len(sys.argv) >= 2:
			for i, fn in enumerate(sys.argv[1:]):
				fileRename(fn)
			sys.exit(0)

# Make cache and temp directories if does not exist
	if not os.path.exists('var'): os.makedirs('var', 0o775)
# All other needs data from server/cache
	loadConfig()
	auth=login()
	if len(sys.argv) > 1 and sys.argv[1:][0] == "get":
		config['usecache']=False
	fullData = cacheFullData()
	if sys.argv[1:] and sys.argv[1:][0] == "refresh":
		sys.exit(1)



# try import hachoir tools, to extract media info from files
	try:
		from hachoir.core.i18n import getTerminalCharset
#		from hachoir.core.cmd_line import unicodeFilename
		from hachoir.parser import createParser
		from hachoir.metadata import extractMetadata
		print("hachoir utilities loaded")
	except:
# Fail silently if we don't have hachoir tools
		print("hachoir failed")
		pass

# Without argument, download all
#	print("Check args")
	if not sys.argv[1:]:
		while firstRun or config['infiniteLoop']:
			if not firstRun:
				loadConfig()
				auth=login()
				fullData=cacheFullData()
			firstRun = False
#			print("Do MAIN")
			main()
			
			if not config['infiniteLoop']: break
			doLog("Sleeping for %d sec until new loop" % config["loopsleep"])
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

print("default exit")
sys.exit(0)
