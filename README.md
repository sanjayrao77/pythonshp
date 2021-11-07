# pythonshp

## Overview
This creates wikipedia-style locator maps from free Natural Earth Data shp and
dbf files (naturalearthdata.com). Thank you Natural Earth Data!

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
	./pythonshp.py verbose publicdomain laos_locator > /tmp/laos.svg
```

## Installation

This requires "admin0", "admin1", "lakes" and "coast" files from naturalearthdata.com.

pythonshp.py will look in several directories for several versions of the files. You
can modify or review the search by looking at the "class Install()" code. As-is, it looks
for 10m and 50m files.

### Download steps

1. Go to http://naturalearthdata.com/downloads with a web browser
2. Click on "Cultural" under "Large scale data" (10m) or "Medium scale data" (50m)
3. Click on "Download without boundary lakes" under "Admin 0 Countries"
4. Save this as a zip file (admin0 data)
5. Click on "Download states and provinces" under "Admin 1 - States, Provinces"
5. Save this as a zip file (admin1 data)
6. Go back to http://naturalearthdata.com/downloads with a web browser
7. Click on "Physical" under "Large scale data" (10m) or "Medium scale data" (50m)
8. Click on "Download lakes" under "Lakes"
9. Save this as a zip file (lake data)
10. Click on "Download coastline" under "Coastline"
11. Save this as a zip file (coast data)

### Unzipping

1. Pick a destination directory where you'll place pythonshp.py
1. Extract the admin0 zip file
2. Place the shp file from the zip in your destination, my file is ne\_10m\_admin\_0\_countries\_lakes.shp
3. Place the dbf file from the zip in your destination, my file is ne\_10m\_admin\_0\_countries\_lakes.dbf
4. Extract the admin1 zip file
5. Place the shp file from the zip in your destination, my file is ne\_10m\_admin\_1\_states\_provinces.shp
6. Place the dbf file from the zip in your destination, my file is ne\_10m\_admin\_1\_states\_provinces.dbf
7. Extract the lakes zip file
8. Place the shp file from the zip in your destination, my file is ne\_10m\_lakes.shp
9. Extract the coast zip file
10. Place the shp file from the zip in your destination, my file is ne\_10m\_coastline.shp

### Checking file locations

1. Run "./pythonshp.py check" in your destination directory to verify that all the files were found.

You can place the shp and dbf files wherever you'd like (~/opt/ned for example)
and use symlinks in the destination directory. I use symlinks to point to the
actual shp and dbf files. The following names will be detected automatically:
admin0.shp, admin0.dbf, admin1.shp, admin1.dbf, lakes.shp, coast.shp.

### Inkscape

python.shp will create svg files of the locator maps. To convert an svg file into a png or jpeg file,
you'll need another program. I recommend Inkscape but Gimp should work as well. You should be able to install
Inkscape using your distribution's package manager.

## Quick start

You'll first need to install dbf and shp files from naturalearthdata.com. Please follow the
*Installation* section above first.

This will create a locator map for laos:
```
./pythonshp.py check laos_locator > /tmp/laos.svg
inkscape -e laos_locator.png /tmp/laos.svg
```

Here is the terminal output from running the previous commands:
```
~/src/pythonshp$ ./pythonshp.py check laos_locator > /tmp/laos.svg
Found file Admin0 shp file -> ./admin0.shp
Found file Admin0 dbf file -> ./admin0.dbf
Found file Admin1 shp file -> ./admin1.shp
Found file Admin1 dbf file -> ./admin1.dbf
Found file Lakes shp file -> ./lakes.shp
Found file Coast shp file -> ./coast.shp
Loading admin0 shape data
Loading admin0 dbf data
Highlight shape number: 69, shape: polygon, parts: 1, points: 1761
0: 1761 points (0..1761), iscw:True
Drawing admin0 sphere shapes
Warning, base data modified: Antarctica removing 8602..9351 of 15954
Loading admin1 data
Drawing admin1 sphere shapes
Admin1 regions found: 17
Loading lakes shapes
Drawing lakes sphere shapes
Drawing lon/lat shapes
Drawing Tripel inset
~/src/pythonshp$ inkscape -e laos_locator.png /tmp/laos.svg
Background RRGGBBAA: ffffff00
Area 0:0:1000:1000 exported to 1000 x 1000 pixels (96 dpi)
Bitmap saved as: laos_locator.png
```

## Supported maps

```
~/src/pythonshp$ ./pythonshp.py list
afghanistan_locator
akrotirisovereignbasearea_locator
aland_locator
albania_locator
algeria_locator
americansamoa_locator
andorra_locator
angola_locator
anguilla_locator
antarctica_locator
antiguaandbarbuda_locator
argentina_locator
armenia_locator
aruba_locator
ashmoreandcartierislands_locator
australia_locator
austria_locator
azerbaijan_locator
bahrain_locator
bajonuevobank_locator
bangladesh_locator
barbados_locator
baykonurcosmodrome_locator
belarus_locator
belgium_locator
belize_locator
benin_locator
bermuda_locator
bhutan_locator
bolivia_locator
bosniaandherzegovina_locator
botswana_locator
brazil_locator
britishindianoceanterritory_locator
britishvirginislands_locator
brunei_locator
bulgaria_locator
burkinafaso_locator
burundi_locator
caboverde_locator
cambodia_locator
cameroon_locator
canada_locator
caymanislands_locator
centralafricanrepublic_locator
chad_locator
chile_locator
china_locator
clippertonisland_locator
colombia_locator
comoros_locator
cookislands_locator
coralseaislands_locator
costarica_locator
croatia_locator
cuba_locator
curacao_locator
cyprus_locator
cyprusnomansarea_locator
czechia_locator
democraticrepublicofthecongo_locator
denmark_locator
dhekelia_locator
djibouti_locator
dominica_locator
dominicanrepublic_locator
easttimor_locator
ecuador_locator
egypt_locator
elsalvador_locator
equatorialguinea_locator
eritrea_locator
estonia_locator
eswatini_locator
ethiopia_locator
falklandislands_locator
faroeislands_locator
federatedstatesofmicronesia_locator
fiji_locator
finland_locator
france_locator
frenchpolynesia_locator
frenchsouthernandantarcticlands_locator
gabon_locator
gambia_locator
georgia_locator
germany_locator
ghana_locator
gibraltar_locator
greece_locator
greenland_locator
grenada_locator
guam_locator
guatemala_locator
guernsey_locator
guinea_locator
guineabissau_locator
guyana_locator
haiti_locator
heardislandandmcdonaldislands_locator
honduras_locator
hongkongsar_locator
hungary_locator
iceland_locator
india_locator
indianoceanterritories_locator
indonesia_locator
iran_locator
iraq_locator
ireland_locator
isleofman_locator
israel_locator
italy_locator
ivorycoast_locator
jamaica_locator
japan_locator
jersey_locator
jordan_locator
kazakhstan_locator
kenya_locator
kiribati_locator
kosovo_locator
kuwait_locator
kyrgyzstan_locator
laos_locator
latvia_locator
lebanon_locator
lesotho_locator
liberia_locator
libya_locator
liechtenstein_locator
lithuania_locator
luxembourg_locator
macaosar_locator
macedonia_locator
madagascar_locator
malawi_locator
malaysia_locator
maldives_locator
mali_locator
malta_locator
marshallislands_locator
mauritania_locator
mauritius_locator
mexico_locator
moldova_locator
monaco_locator
mongolia_locator
montenegro_locator
montserrat_locator
morocco_locator
mozambique_locator
myanmar_locator
namibia_locator
nauru_locator
nepal_locator
netherlands_locator
newcaledonia_locator
newzealand_locator
nicaragua_locator
niger_locator
nigeria_locator
niue_locator
norfolkisland_locator
northerncyprus_locator
northernmarianaislands_locator
northkorea_locator
norway_locator
oman_locator
pakistan_locator
palau_locator
palestine_locator
panama_locator
papuanewguinea_locator
paraguay_locator
peru_locator
philippines_locator
pitcairnislands_locator
poland_locator
portugal_locator
puertorico_locator
qatar_locator
republicofserbia_locator
republicofthecongo_locator
romania_locator
russia_locator
rwanda_locator
saintbarthelemy_locator
sainthelena_locator
saintkittsandnevis_locator
saintlucia_locator
saintmartin_locator
saintpierreandmiquelon_locator
saintvincentandthegrenadines_locator
samoa_locator
sanmarino_locator
saotomeandprincipe_locator
saudiarabia_locator
scarboroughreef_locator
senegal_locator
serranillabank_locator
seychelles_locator
siachenglacier_locator
sierraleone_locator
singapore_locator
sintmaarten_locator
slovakia_locator
slovenia_locator
solomonislands_locator
somalia_locator
somaliland_locator
southafrica_locator
southgeorgiaandtheislands_locator
southkorea_locator
southsudan_locator
spain_locator
spratlyislands_locator
srilanka_locator
sudan_locator
suriname_locator
sweden_locator
switzerland_locator
syria_locator
taiwan_locator
tajikistan_locator
thailand_locator
thebahamas_locator
togo_locator
tonga_locator
trinidadandtobago_locator
tunisia_locator
turkey_locator
turkmenistan_locator
turksandcaicosislands_locator
tuvalu_locator
uganda_locator
ukraine_locator
unitedarabemirates_locator
unitedkingdom_locator
unitedrepublicoftanzania_locator
unitedstatesminoroutlyingislands_locator
unitedstatesofamerica_locator
unitedstatesvirginislands_locator
uruguay_locator
usnavalbaseguantanamobay_locator
uzbekistan_locator
vanuatu_locator
vatican_locator
venezuela_locator
vietnam_locator
wallisandfutuna_locator
westernsahara_locator
yemen_locator
zambia_locator
zimbabwe_locator
```
