# pythonshp

## Overview
This creates wikipedia-style locator maps from free Natural Earth Data shp and
dbf files (naturalearthdata.com). Thank you Natural Earth Data!

It can also be used to read SHP files in general.

Example:
<p float="left">
	<img src="http://www.evilcouncil.com/locators/laos_locator.png" width="100" />
</p>

## License
This python code is licensed under the GPLv2. The GPL license text is widely available
and should be downloadable above (on github).

The output svg code is unlicensed by default. If you provide the "publicdomain"
command line parameter, the svg code will contain a notice of being in the
public domain.

e.g.:
```
	./pythonshp.py verbose wiki1 laos locatormap > /tmp/laos.svg
```

## Installation

pythonshp.py will look in several directories for several versions of the files. You
can modify or review the search by looking at the "class Install()" code.

These files from naturalearthdata.com are required (with the default settings):
1. ne\_10m\_admin\_0\_countries.zip
2. ne\_50m\_admin\_0\_countries.zip
3. ne\_50m\_lakes.zip
4. ne\_110m\_land.zip


### Download steps

1. Go to http://naturalearthdata.com/downloads with a web browser
2. Click on "Cultural" under "Large scale data" (10m) 
3. Click on "Download countries" under "Admin 0 Countries"
4. Save this as a zip file (ne\_10m\_admin\_0\_countries.zip)

5. Go back to http://naturalearthdata.com/downloads with a web browser
6. Click on "Cultural" under "Medium scale data" (50m)
7. Click on "Download countries" under "Admin 0 Countries"
8. Save this as a zip file (ne\_50m\_admin\_0\_countries.zip)

9. Go back to http://naturalearthdata.com/downloads with a web browser
10. Click on "Physical" under "Medium scale data" (50m)
11. Click on "Download lakes" under "Lakes"
12. Save this as a zip file (ne\_50m\_lakes.zip)

13. Go back to http://naturalearthdata.com/downloads with a web browser
14. Click on "Physical" under "Small scale data" (110m)
15. Click on "Download land" under "Land"
16. Save this as a zip file (ne\_110m\_land.zip)

### Unzipping

1. Pick a directory for pythonshp.py and its data
2. Place pythonshp.py in that directory (download it from github)
3. Unzip the 4 zip files from naturalearthdata. Place the .dbf and .shp files from
the zip archives into the same directory.
4. After you have things working, you can move the shp and dbf files to make the
directory structure cleaner.

### Checking file locations

1. Run "./pythonshp.py check" in your destination directory to verify that all
the downloaded files were found.

Here is my output (with a different directory structure):
```
Found file admin0-lakes.shp (10m) -> ned/10m-admin/ne_10m_admin_0_countries_lakes.shp
Found file admin0-lakes.shp (50m) -> ned/50m-admin/ne_50m_admin_0_countries_lakes.shp
Found file admin0-nolakes.shp (10m) -> ned/10m-admin/ne_10m_admin_0_countries.shp
Found file admin0-nolakes.shp (50m) -> ned/50m-admin/ne_50m_admin_0_countries.shp
Found file admin0-nolakes.shp (110m) -> ned/110m-admin/ne_110m_admin_0_countries.shp
Found file admin0.dbf (10m) -> ned/10m-admin/ne_10m_admin_0_countries_lakes.dbf
Found file admin0.dbf (50m) -> ned/50m-admin/ne_50m_admin_0_countries_lakes.dbf
Found file admin0.dbf (110m) -> ned/110m-admin/ne_110m_admin_0_countries.dbf
File not found: admin1-lakes.shp -> ?
Found file admin1-nolakes.shp (10m) -> ned/10m-admin/ne_10m_admin_1_states_provinces.shp
Found file admin1.dbf (10m) -> ned/10m-admin/ne_10m_admin_1_states_provinces.dbf
Found file lakes.shp (10m) -> ned/10m-lakes/ne_10m_lakes.shp
Found file lakes.shp (50m) -> ned/50m-lakes/ne_50m_lakes.shp
Found file lakes.dbf (10m) -> ned/10m-lakes/ne_10m_lakes.dbf
Found file lakes.dbf (50m) -> ned/50m-lakes/ne_50m_lakes.dbf
Found file coast.shp (10m) -> ned/10m-coast/ne_10m_coastline.shp
Found file ocean.shp (110m) -> ned/110m-ocean/ne_110m_ocean.shp
Found file land.shp (10m) -> ned/10m-land/ne_10m_land.shp
Found file land.shp (110m) -> ned/110m-land/ne_110m_land.shp
```

### Inkscape

python.shp will create svg files of the locator maps. To convert an svg file into a png or jpeg file,
you'll need another program. I recommend Inkscape but Gimp should work as well. You should be able to install
Inkscape using your distribution's package manager.

## Quick start

You'll first need to install dbf and shp files from naturalearthdata.com. Please follow the
*Installation* section above first.

This will create a locator map for laos:
```
./pythonshp.py verbose wiki1 laos locatormap > /tmp/laos.svg
inkscape -e laos_locator.png /tmp/laos.svg
```

## Python code

Please see _codeguide.txt_ for a description of the 'options' values and how
the classes are arranged.

## Supported maps

```
~/src/pythonshp$ ./pythonshp.py list
afghanistan
akrotirisovereignbasearea
aland
albania
algeria
americansamoa
andorra
angola
anguilla
antarctica
antiguaandbarbuda
argentina
armenia
aruba
ashmoreandcartierislands
australia
austria
azerbaijan
bahrain
bajonuevobank
bangladesh
barbados
baykonurcosmodrome
belarus
belgium
belize
benin
bermuda
bhutan
bolivia
bosniaandherzegovina
botswana
brazil
britishindianoceanterritory
britishvirginislands
brunei
bulgaria
burkinafaso
burundi
caboverde
cambodia
cameroon
canada
caymanislands
centralafricanrepublic
chad
chile
china
clippertonisland
colombia
comoros
cookislands
coralseaislands
costarica
croatia
cuba
curacao
cyprus
cyprusnomansarea
czechia
democraticrepublicofthecongo
denmark
dhekelia
djibouti
dominica
dominicanrepublic
easttimor
ecuador
egypt
elsalvador
equatorialguinea
eritrea
estonia
eswatini
ethiopia
falklandislands
faroeislands
federatedstatesofmicronesia
fiji
finland
france
frenchpolynesia
frenchsouthernandantarcticlands
gabon
gambia
georgia
germany
ghana
gibraltar
greece
greenland
grenada
guam
guatemala
guernsey
guinea
guineabissau
guyana
haiti
heardislandandmcdonaldislands
honduras
hongkongsar
hungary
iceland
india
indianoceanterritories
indonesia
iran
iraq
ireland
isleofman
israel
italy
ivorycoast
jamaica
japan
jersey
jordan
kazakhstan
kenya
kiribati
kosovo
kuwait
kyrgyzstan
laos
latvia
lebanon
lesotho
liberia
libya
liechtenstein
lithuania
luxembourg
macaosar
macedonia
madagascar
malawi
malaysia
maldives
mali
malta
marshallislands
mauritania
mauritius
mexico
moldova
monaco
mongolia
montenegro
montserrat
morocco
mozambique
myanmar
namibia
nauru
nepal
netherlands
newcaledonia
newzealand
nicaragua
niger
nigeria
niue
norfolkisland
northerncyprus
northernmarianaislands
northkorea
norway
oman
pakistan
palau
palestine
panama
papuanewguinea
paraguay
peru
philippines
pitcairnislands
poland
portugal
puertorico
qatar
republicofserbia
republicofthecongo
romania
russia
rwanda
saintbarthelemy
sainthelena
saintkittsandnevis
saintlucia
saintmartin
saintpierreandmiquelon
saintvincentandthegrenadines
samoa
sanmarino
saotomeandprincipe
saudiarabia
scarboroughreef
senegal
serranillabank
seychelles
siachenglacier
sierraleone
singapore
sintmaarten
slovakia
slovenia
solomonislands
somalia
somaliland
southafrica
southgeorgiaandtheislands
southkorea
southsudan
spain
spratlyislands
srilanka
sudan
suriname
sweden
switzerland
syria
taiwan
tajikistan
thailand
thebahamas
togo
tonga
trinidadandtobago
tunisia
turkey
turkmenistan
turksandcaicosislands
tuvalu
uganda
ukraine
unitedarabemirates
unitedkingdom
unitedrepublicoftanzania
unitedstatesminoroutlyingislands
unitedstatesofamerica
unitedstatesvirginislands
uruguay
usnavalbaseguantanamobay
uzbekistan
vanuatu
vatican
venezuela
vietnam
wallisandfutuna
westernsahara
yemen
zambia
zimbabwe
```
