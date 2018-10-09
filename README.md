# elisa-dl
Python downloader script for Elisa-Viihde (New API)

-------------------- ESIVALMISTELUT

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

**TODO** Linux osuus:
apt-get -y install ffmpeg python python-pip ; pip install youtube-dl

... Lisää juttua mitä pitäisi huomioida. Tässä vielä tuo 'release' info:

https://yhteiso.elisa.fi/elisa-viihde-sovellus-ja-nettipalvelu-16/elisa-viihde-api-julkaisut-ja-bugiraportit-512104/index5.html#post588618
Kiitos @Qotscha tuosta python koodista ... Latasin sen varmaan viikko sitten ja siinä oli ihan hyvää pohjaa omalle jutulle. Siitä se sitten lähtikin.

Eli tarpeena minulla oli saada nuo Viihteen tallenteet omalle koneelle, ja tärkeä osa aikaisemmin ajamaani scriptiä (bash scripti, vanhan APIn aikana) oli tiedostojen uudelleen nimeäminen.

Väänsin tuossa sitten oman downloader koodin. Pahasti keskeneräinen alpha, mutta eiköhän tuota uskalla jo julkisesti näyttää.

Käytännössä se käy kaikki Viihde kansiot läpi ja lataa tallenteet omalle koneelle. Siinä sivussa suorittaa tiedostojen renamen. En tiedä onko tosta muille hyötyä, mutta jaetaan nyt koodia jos tulisi vaikka contributiota muilta tai vaikka ideoita.

Koodi on GitHubissa https://github.com/Hallikas/elisa-dl ja varoituksena tosiaan se että tuo on varhainen versio. (Ei poista mitään palvelimelta, siirtää ladatut 'done' kansioon, minkä pystyy itse tuolla .py koodissa määrittelemään.

Linux käyttäjänä kohdeympäristö oli tietysti Linux, mutta koska originaali python oli tehty windowssiin ja kaveri vähän pyysi, tein tuosta yhteensopivan molempiin ympäristöihin.
