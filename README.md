# Python downloader script for Elisa-Viihde (New API)

[![Waffle.io - Columns and their card count](https://badge.waffle.io/Hallikas/elisa-dl.svg?columns=all)](https://waffle.io/Hallikas/elisa-dl)

![GitHub](https://img.shields.io/github/license/Hallikas/elisa-dl.svg)
![GitHub contributors](https://img.shields.io/github/contributors/Hallikas/elisa-dl.svg)
![GitHub tag](https://img.shields.io/github/tag/Hallikas/elisa-dl.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/Hallikas/elisa-dl.svg)


/* ************************************************************************
This README is not done!  This works as notepad for now, but I will
focus on this later.  I try keep development language in english, but
because this software is mainly for Finnish people, using Finnish is just
fine too.
************************************************************************ */


Command line parameters:
elisa-dl.py find filename.mp4 - Tries to find programId by filename, writes -var.txt file for file and renames. (use in case of missing -var)
Example:
	$ ls -l tmp/Safety\ not\ Guaranteed*
	-rwxrwxrwx 1 semi semi 5287504353 Oct  5 05:57 'tmp/Safety not Guaranteed (2012).mp4'

	$ ./elisa-dl.py find tmp/Safety\ not\ Guaranteed\ \(S\)\ \(20180512_2100\).mp4
	'tmp/Safety not Guaranteed (S) (20180512_2100)-var.txt' -> 'movie/Safety not Guaranteed (2012)-var.txt'
	'tmp/Safety not Guaranteed (S) (20180512_2100).mp4' -> 'movie/Safety not Guaranteed (2012).mp4'


elisa-dl.py rename file-var.txt - Renames file* files. Uses -var file to get data for generating filename.
Example:
	(after fixing: "name": 'Simpsonit 29. kausi (7)' -> "name": 'Simpsonit (7)' from -var file)
	$ ./elisa-dl.py rename series/Simpsonit\ 29.\ kausi/Simpsonit\ 29.\ kausi\ -\ S29E14\ -\ Pellen\ pahin\ pelko-var.txt
	'series/Simpsonit 29. kausi/Simpsonit 29. kausi - S29E14 - Pellen pahin pelko-formats.txt' -> 'series/Simpsonit/Simpsonit - S29E14 - Pellen pahin pelko-formats.txt'
	'series/Simpsonit 29. kausi/Simpsonit 29. kausi - S29E14 - Pellen pahin pelko-var.txt' -> 'series/Simpsonit/Simpsonit - S29E14 - Pellen pahin pelko-var.txt'
	'series/Simpsonit 29. kausi/Simpsonit 29. kausi - S29E14 - Pellen pahin pelko-var.txt~' -> 'series/Simpsonit/Simpsonit - S29E14 - Pellen pahin pelko-var.txt~'
	'series/Simpsonit 29. kausi/Simpsonit 29. kausi - S29E14 - Pellen pahin pelko.mp4' -> 'series/Simpsonit/Simpsonit - S29E14 - Pellen pahin pelko.mp4'
	'series/Simpsonit 29. kausi/Simpsonit 29. kausi - S29E14 - Pellen pahin pelko.txt' -> 'series/Simpsonit/Simpsonit - S29E14 - Pellen pahin pelko.txt'


elisa-dl.py filename test-var.txt - Shows metadata from -var file, also shows what filename would be in case of rename.
Example:
	$ ./elisa-dl.py filename movie/007\ Skyfall\ \(2012\)-var.txt
	Channel: Nelonen
	Type: MOVIE
	Start: 2018-09-08 21:00:00

	Title: 007 Skyfall (12)
	Description:

	(007 Skyfall/UK-USA 2012). Kaikkien aikojen menestyneimmässä
        Bond-seikkailussa 007:n lojaalius joutuu koetukselle, kun
        MI6-tiedustelupalvelun johtajan M:n (Judi Dench) menneisyydestä
        nousee esiin salaperäinen uhka.

	movie/007 Skyfall (2012)


-------------------- ESIVALMISTELUT

Linux
=====

apt-get -y install ffmpeg python python-pip ; pip install youtube-dl requests


Windows
=======

Tarvittavat ohjelmat: Python 2.7, ffmpeg
Ja pythoniin: youtube-dl, requests

Lataa viimeisin windows python (2.7):
https://www.python.org/downloads/release/python-2715/

Suosittelen lataamaan "Windows x86-64 MSI installer" paketin. Lataamisen jälkeen asenna se.

Seuraavaksi lataa ffmpeg:
https://www.ffmpeg.org/download.html
Kopioi paketista ffmpeg.exe samaan hakemistoon elisa-dl.py scriptin kanssa (tai polkuun).

Komentorivillä kirjoita komento:
c:\Python27\Scripts\pip2.exe install youtube-dl
ja
c:\Python27\Scripts\pip2.exe install requests

Kopioi myös c:\Python27\Scripts\youtube-dl.exe samaan hakemistoon kun elisa-dl.py ha ffmpeg.exe

-------------------- /ESIVALMISTELUT


'release' info:

https://yhteiso.elisa.fi/elisa-viihde-sovellus-ja-nettipalvelu-16/elisa-viihde-api-julkaisut-ja-bugiraportit-512104/index5.html#post588618

Kiitos @Qotscha tuosta python koodista ... Latasin sen varmaan viikko sitten ja siinä oli ihan hyvää pohjaa omalle jutulle. Siitä se sitten lähtikin.

Eli tarpeena minulla oli saada nuo Viihteen tallenteet omalle koneelle, ja tärkeä osa aikaisemmin ajamaani scriptiä (bash scripti, vanhan APIn aikana) oli tiedostojen uudelleen nimeäminen.

Väänsin tuossa sitten oman downloader koodin. Pahasti keskeneräinen alpha, mutta eiköhän tuota uskalla jo julkisesti näyttää.

Käytännössä se käy kaikki Viihde kansiot läpi ja lataa tallenteet omalle koneelle. Siinä sivussa suorittaa tiedostojen renamen. En tiedä onko tosta muille hyötyä, mutta jaetaan nyt koodia jos tulisi vaikka contributiota muilta tai vaikka ideoita.

Koodi on GitHubissa https://github.com/Hallikas/elisa-dl ja varoituksena tosiaan se että tuo on varhainen versio. (Ei poista mitään palvelimelta, siirtää ladatut 'done' kansioon, minkä pystyy itse tuolla .py koodissa määrittelemään.

Linux käyttäjänä kohdeympäristö oli tietysti Linux, mutta koska originaali python oli tehty windowssiin ja kaveri vähän pyysi, tein tuosta yhteensopivan molempiin ympäristöihin.
