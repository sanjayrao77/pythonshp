# pythonshp

## Overview
This creates wikipedia-style maps from free Natural Earth Data shp and
dbf files (naturalearthdata.com). Thank you Natural Earth Data!

It can also be used to read SHP files in general.

## Examples

### USA wiki1 locatormap
```
./pythonshp.py publicdomain verbose wiki1 unitedstatesofamerica locatormap > unitedstatesofamerica_w1_locator.svg
```
<img src="http://www.evilcouncil.com/github/unitedstatesofamerica_w1_locator.svg" width="300" />

### USA wiki2 locatormap
```
./pythonshp.py publicdomain verbose wiki2 unitedstatesofamerica locatormap > unitedstatesofamerica_w2_locator.svg
```
<img src="http://www.evilcouncil.com/github/unitedstatesofamerica_w2_locator.svg" width="300" />

### Estonia wiki1 locatormap, showing zoom inset
```
./pythonshp.py publicdomain verbose wiki1 estonia locatormap > estonia_w1_locator.svg
```
<img src="http://www.evilcouncil.com/github/estonia_w1_locator.svg" width="300" />

### Estonia wiki2 locatormap, showing zoom inset
```
./pythonshp.py publicdomain verbose wiki2 estonia locatormap > estonia_w2_locator.svg
```
<img src="http://www.evilcouncil.com/github/estonia_w2_locator.svg" width="300" />

### Luxembourg wiki1 euromap
```
./pythonshp.py publicdomain verbose wiki1 luxembourg euromap > luxembourg_w1_euromap.svg
```
<img src="http://www.evilcouncil.com/github/luxembourg_w1_euromap.svg" width="300" />

### India wiki1 disputed countrymap
```
./pythonshp.py publicdomain verbose wiki1 india/_disputed countrymap > india_disputed_w1_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/india_disputed_w1_countrymap.svg" width="300" />

### Canada wiki1 countrymap
```
./pythonshp.py publicdomain verbose wiki1 canada countrymap > canada_w1_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/canada_w1_countrymap.svg" width="300" />

### Canada wiki1 province/territory "admin1" countrymap
```
./pythonshp.py publicdomain verbose wiki1 canada/_admin1 countrymap > canada_admin1_w1_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/canada_admin1_w1_countrymap.svg" width="300" />

### Alberta wiki1 countrymap
```
./pythonshp.py publicdomain verbose wiki1 canada/alberta countrymap > canada_alberta_w1_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/canada_alberta_w1_countrymap.svg" width="300" />

### Canada wiki2 countrymap
```
./pythonshp.py publicdomain verbose wiki2 canada countrymap > canada_w2_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/canada_w2_countrymap.svg" width="300" />

### Canada wiki2 province/territory "admin1" countrymap
```
./pythonshp.py publicdomain verbose wiki2 canada/_admin1 countrymap > canada_admin1_w2_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/canada_admin1_w2_countrymap.svg" width="300" />

### Alberta wiki2 countrymap
```
./pythonshp.py publicdomain verbose wiki2 canada/alberta countrymap > canada_alberta_w2_countrymap.svg
```
<img src="http://www.evilcouncil.com/github/canada_alberta_w2_countrymap.svg" width="300" />


## License
This python code is licensed under the GPLv2. The GPL license text is widely available
and should be downloadable above (on github).

The output svg code is unlicensed by default. If you provide the "publicdomain"
command line parameter, the svg code will contain a notice of being in the
public domain.

e.g.:
```
	./pythonshp.py publicdomain verbose wiki1 laos locatormap > /tmp/laos.svg
```

## Installation

pythonshp.py will look in several directories for several versions of the files. You
can modify or review the search by looking at the "class Install()" code.

These files from naturalearthdata.com are required when using the default settings:
1. ne\_10m\_admin\_0\_countries.zip
2. ne\_10m\_admin\_0\_disputed\_areas.zip
3. ne\_10m\_admin\_1\_states\_provinces.zip
4. ne\_10m\_admin\_1\_states\_provinces\_lines.zip
5. ne\_10m\_lakes.zip
6. HYP\_HR\_SR\_OB\_DR.zip
7. ne\_50m\_admin\_0\_countries.zip
8. ne\_50m\_lakes.zip
9. ne\_110m\_land.zip

The original pythonshp.py was written for Natural Earth Data version 4.0/4.1. There
were some changes and now only version 5.0 (the latest) is supported. Only small changes would
be needed to support v4 again (e.g. ADM0\_A3 was adm0\_a3 in admin1 lines v4).


### Download steps

1. Go to http://naturalearthdata.com/downloads with a web browser
2. Click on "Cultural" under "Large scale data" (10m) 
3. Click on "Download countries" under "Admin 0 Countries"
4. Save this as a zip file (ne\_10m\_admin\_0\_countries.zip)

5. Click on "Download breakaway and disputed areas"
6. Save this as a zip file (ne\_10m\_admin\_0\_disputed\_areas.zip)

7. Click on "Download states and provinces" under "Admin 1 - States, Provinces"
8. Save this as a zip file (ne\_10m\_admin\_1\_states\_provinces.zip)

9. Click on "Download boundary lines" under "Admin 1 - States, Provinces"
10. Save this as a zip file (ne\_10m\_admin\_1\_states\_provinces\_lines.zip)

11. Go back to http://naturalearthdata.com/downloads with a web browser
12. Click on "Physical" under "Large scale data" (10m)
13. Click on "Download lakes" under "Lakes"
14. Save this as a zip file (ne\_10m\_lakes.zip)

15. Go back to http://naturalearthdata.com/downloads with a web browser
16. Click on "Raster" under "Large scale data" (10m)
17. Click on "Cross-blended Hypsometric Tints"
18. Click on "Download large size" under "Cross Blended Hypso with Relief, Water, Drains, and Ocean Bottom"
19. Save this as a zip file (HYP\_HR\_SR\_OB\_DR.zip)

20. Go back to http://naturalearthdata.com/downloads with a web browser
21. Click on "Cultural" under "Medium scale data" (50m)
22. Click on "Download countries" under "Admin 0 Countries"
23. Save this as a zip file (ne\_50m\_admin\_0\_countries.zip)

24. Go back to http://naturalearthdata.com/downloads with a web browser
25. Click on "Physical" under "Medium scale data" (50m)
26. Click on "Download lakes" under "Lakes"
27. Save this as a zip file (ne\_50m\_lakes.zip)

28. Go back to http://naturalearthdata.com/downloads with a web browser
29. Click on "Physical" under "Small scale data" (110m)
30. Click on "Download land" under "Land"
31. Save this as a zip file (ne\_110m\_land.zip)

### Unzipping

1. Pick a directory for pythonshp.py and its data
2. Place pythonshp.py in that directory (download it from github)
3. Copy the 8 ne\_\*.zip files from naturalearthdata into that directory. There is no need to unzip them.
4. Install the program "tifftopnm" (included in the "netpbm" package on my debian)
5. Unzip the HYP\_HR\_SR\_OB\_DR.zip file and note the .tif file inside. Convert the tif file with tifftopnm:
```
tifftopnm HYP_HR_SR_OB_DR.tif > hyp_hr_sr_ob_dr.pnm
```
6. The HYP .zip file and .tif file are not used by pythonshp.py and can be deleted once the pnm is created.

### Checking file locations

1. Run "./pythonshp.py check" in your destination directory to verify that all
the downloaded files were found.

Here is my output (with a different directory structure):
```
File not found: admin0-lakes.shp -> ?
Found file admin0-nolakes.shp (10m) -> ned/ne_10m_admin_0_countries.zip
Found file admin0-nolakes.shp (50m) -> ned/ne_50m_admin_0_countries.zip
Found file admin0.dbf (10m) -> ned/ne_10m_admin_0_countries.zip
Found file admin0.dbf (50m) -> ned/ne_50m_admin_0_countries.zip
Found file admin0-disputed.shp (10m) -> ned/ne_10m_admin_0_disputed_areas.zip
Found file admin0-disputed.dbf (10m) -> ned/ne_10m_admin_0_disputed_areas.zip
File not found: admin1-lakes.shp -> ?
Found file admin1-nolakes.shp (10m) -> ned/ne_10m_admin_1_states_provinces.zip
Found file admin1.dbf (10m) -> ned/ne_10m_admin_1_states_provinces.zip
Found file admin1-lines.shp (10m) -> ned/ne_10m_admin_1_states_provinces_lines.zip
Found file admin1-lines.dbf (10m) -> ned/ne_10m_admin_1_states_provinces_lines.zip
Found file lakes.shp (10m) -> ned/ne_10m_lakes.zip
Found file lakes.shp (50m) -> ned/ne_50m_lakes.zip
Found file lakes.dbf (10m) -> ned/ne_10m_lakes.zip
Found file lakes.dbf (50m) -> ned/ne_50m_lakes.zip
File not found: coast.shp -> ?
File not found: ocean.shp -> ?
Found file land.shp (110m) -> ned/110m-land/ne_110m_land.shp
Found file hypso-sr_w.pnm (50m) -> ned/50m-hypso/hyp_50m_sr_w.pnm
Found file hypso-lr_sr_ob_dr.pnm (10m) -> ned/10m-hypso/hyp_hr_sr_ob_dr.pnm
Found file hypso-hr_sr_ob_dr.pnm (10m) -> ned/10m-hypso/hyp_hr_sr_ob_dr.pnm
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
~/src/pythonshp$ ./pythonshp.py listall
afghanistan
akrotirisovereignbasearea
aland
albania
algeria
americansamoa
americansamoa/_disputed
andorra
angola
anguilla
antarctica
antiguaandbarbuda
argentina
argentina/_admin1
argentina/_disputed
argentina/buenosaires
argentina/catamarca
argentina/chaco
argentina/chubut
argentina/ciudaddebuenosaires
argentina/cordoba
argentina/corrientes
argentina/entrerios
argentina/formosa
argentina/jujuy
argentina/lapampa
argentina/larioja
argentina/mendoza
argentina/misiones
argentina/neuquen
argentina/rionegro
argentina/salta
argentina/sanjuan
argentina/sanluis
argentina/santacruz
argentina/santafe
argentina/santiagodelestero
argentina/tierradelfuego
argentina/tucuman
armenia
aruba
ashmoreandcartierislands
australia
austria
azerbaijan
azerbaijan/_disputed
bahrain
bajonuevobank
bangladesh
barbados
baykonurcosmodrome
belarus
belgium
belize
belize/_disputed
benin
bermuda
bhutan
bhutan/_disputed
birtawil
bolivia
bolivia/_admin1
bolivia/_disputed
bolivia/chuquisaca
bolivia/cochabamba
bolivia/elbeni
bolivia/lapaz
bolivia/oruro
bolivia/pando
bolivia/potosi
bolivia/santacruz
bolivia/tarija
bosniaandherzegovina
botswana
brazil
brazil/_disputed
brazilianisland
britishindianoceanterritory
britishvirginislands
brunei
brunei/_disputed
bulgaria
burkinafaso
burundi
caboverde
cambodia
cameroon
canada
canada/_admin1
canada/_disputed
canada/alberta
canada/britishcolumbia
canada/manitoba
canada/newbrunswick
canada/newfoundlandandlabrador
canada/northwestterritories
canada/novascotia
canada/nunavut
canada/ontario
canada/princeedwardisland
canada/quebec
canada/saskatchewan
canada/yukon
caymanislands
centralafricanrepublic
chad
chile
chile/_admin1
chile/_disputed
chile/aisendelgeneralcarlosibanezdelcampo
chile/antofagasta
chile/aricayparinacota
chile/atacama
chile/biobio
chile/coquimbo
chile/laaraucania
chile/libertadorgeneralbernardoohiggins
chile/loslagos
chile/losrios
chile/magallanesyantarticachilena
chile/maule
chile/nuble
chile/regionmetropolitanadesantiago
chile/tarapaca
chile/valparaiso
china
china/_admin1
china/_disputed
china/anhui
china/beijing
china/chongqing
china/fujian
china/gansu
china/guangdong
china/guangxi
china/guizhou
china/hainan
china/hebei
china/heilongjiang
china/henan
china/hubei
china/hunan
china/innermongol
china/jiangsu
china/jiangxi
china/jilin
china/liaoning
china/ningxia
china/paracelislands
china/qinghai
china/shaanxi
china/shandong
china/shanghai
china/shanxi
china/sichuan
china/tianjin
china/xinjiang
china/xizang
china/yunnan
china/zhejiang
clippertonisland
colombia
colombia/_disputed
comoros
comoros/_disputed
cookislands
coralseaislands
costarica
croatia
croatia/_disputed
cuba
cuba/_disputed
curacao
cyprus
cyprus/_admin1
cyprus/_disputed
cyprus/famagusta
cyprus/larnaca
cyprus/limassol
cyprus/nicosia
cyprus/paphos
cyprusfull
cyprusnomansarea
czechia
democraticrepublicofthecongo
denmark
denmark/_disputed
dhekelia
djibouti
djibouti/_disputed
dominica
dominicanrepublic
ecuador
egypt
egypt/_disputed
elsalvador
equatorialguinea
equatorialguinea/_disputed
eritrea
eritrea/_disputed
estonia
eswatini
ethiopia
ethiopia/_admin1
ethiopia/addisababa
ethiopia/afar
ethiopia/amhara
ethiopia/benshangulgumaz
ethiopia/diredawa
ethiopia/gambelapeoples
ethiopia/hararipeople
ethiopia/oromiya
ethiopia/somali
ethiopia/southernnationsnationalitiesandpeoples
ethiopia/tigray
falklandislands
faroeislands
federatedstatesofmicronesia
fiji
finland
france
france/_disputed
frenchpolynesia
frenchsouthernandantarcticlands
gabon
gabon/_disputed
gambia
georgia
georgia/_disputed
germany
ghana
gibraltar
greece
greenland
grenada
guam
guatemala
guatemala/_disputed
guernsey
guinea
guineabissau
guyana
guyana/_disputed
haiti
haiti/_disputed
heardislandandmcdonaldislands
honduras
honduras/_disputed
hongkongsar
hungary
iceland
india
india/_admin1
india/_disputed
india/andamanandnicobar
india/andhrapradesh
india/arunachalpradesh
india/assam
india/bihar
india/chandigarh
india/chhattisgarh
india/dadraandnagarhavelianddamananddiu
india/delhi
india/goa
india/gujarat
india/haryana
india/himachalpradesh
india/jammuandkashmir
india/jharkhand
india/karnataka
india/kerala
india/ladakh
india/lakshadweep
india/madhyapradesh
india/maharashtra
india/manipur
india/meghalaya
india/mizoram
india/nagaland
india/odisha
india/puducherry
india/punjab
india/rajasthan
india/sikkim
india/tamilnadu
india/telangana
india/tripura
india/uttarakhand
india/uttarpradesh
india/westbengal
indianoceanterritories
indonesia
indonesia/_admin1
indonesia/aceh
indonesia/bali
indonesia/bangkabelitung
indonesia/banten
indonesia/bengkulu
indonesia/gorontalo
indonesia/jakartaraya
indonesia/jambi
indonesia/jawabarat
indonesia/jawatengah
indonesia/jawatimur
indonesia/kalimantanbarat
indonesia/kalimantanselatan
indonesia/kalimantantengah
indonesia/kalimantantimur
indonesia/kepulauanriau
indonesia/lampung
indonesia/maluku
indonesia/malukuutara
indonesia/nusatenggarabarat
indonesia/nusatenggaratimur
indonesia/papua
indonesia/papuabarat
indonesia/riau
indonesia/sulawesibarat
indonesia/sulawesiselatan
indonesia/sulawesitengah
indonesia/sulawesitenggara
indonesia/sulawesiutara
indonesia/sumaterabarat
indonesia/sumateraselatan
indonesia/sumaterautara
indonesia/yogyakarta
iran
iran/_disputed
iraq
ireland
ireland/_admin1
ireland/carlow
ireland/cavan
ireland/clare
ireland/cork_city
ireland/cork_county
ireland/donegal
ireland/dublin
ireland/dunlaoghairerathdown
ireland/fingal
ireland/galway_city
ireland/galway_county
ireland/kerry
ireland/kildare
ireland/kilkenny
ireland/laoighis
ireland/leitrim
ireland/limerick_city
ireland/limerick_county
ireland/longford
ireland/louth
ireland/mayo
ireland/meath
ireland/monaghan
ireland/northtipperary
ireland/offaly
ireland/roscommon
ireland/sligo
ireland/southdublin
ireland/southtipperary
ireland/waterford_city
ireland/waterford_county
ireland/westmeath
ireland/wexford
ireland/wicklow
isleofman
israel
israel/_disputed
italy
ivorycoast
jamaica
jamaica/_disputed
japan
japan/_disputed
jersey
jordan
kazakhstan
kenya
kenya/_admin1
kenya/_disputed
kenya/central
kenya/coast
kenya/eastern
kenya/nairobi
kenya/northeastern
kenya/nyanza
kenya/riftvalley
kenya/western
kiribati
kosovo
kosovo/_disputed
kuwait
kyrgyzstan
laos
latvia
lebanon
lebanon/_admin1
lebanon/_disputed
lebanon/annabatiyah
lebanon/beirut
lebanon/beqaa
lebanon/mountlebanon
lebanon/northlebanon
lebanon/southlebanon
lesotho
liberia
libya
liechtenstein
lithuania
luxembourg
macaosar
macedonia
madagascar
madagascar/_disputed
malawi
malawi/_admin1
malawi/balaka
malawi/blantyre
malawi/chikwawa
malawi/chiradzulu
malawi/chitipa
malawi/dedza
malawi/dowa
malawi/karonga
malawi/kasungu
malawi/likoma
malawi/lilongwe
malawi/machinga
malawi/mangochi
malawi/mchinji
malawi/mulanje
malawi/mwanza
malawi/mzimba
malawi/neno
malawi/nkhatabay
malawi/nkhotakota
malawi/nsanje
malawi/ntcheu
malawi/ntchisi
malawi/phalombe
malawi/rumphi
malawi/salima
malawi/thyolo
malawi/zomba
malaysia
malaysia/_admin1
malaysia/_disputed
malaysia/johor
malaysia/kedah
malaysia/kelantan
malaysia/kualalumpur
malaysia/labuan
malaysia/melaka
malaysia/negerisembilan
malaysia/pahang
malaysia/perak
malaysia/perlis
malaysia/pulaupinang
malaysia/putrajaya
malaysia/sabah
malaysia/sarawak
malaysia/selangor
malaysia/terengganu
maldives
mali
malta
marshallislands
marshallislands/_disputed
mauritania
mauritius
mauritius/_disputed
mexico
mexico/_admin1
mexico/aguascalientes
mexico/bajacalifornia
mexico/bajacaliforniasur
mexico/campeche
mexico/chiapas
mexico/chihuahua
mexico/coahuila
mexico/colima
mexico/distritofederal
mexico/durango
mexico/guanajuato
mexico/guerrero
mexico/hidalgo
mexico/islaperez
mexico/jalisco
mexico/mexico
mexico/michoacan
mexico/morelos
mexico/nayarit
mexico/nuevoleon
mexico/oaxaca
mexico/puebla
mexico/queretaro
mexico/quintanaroo
mexico/sanluispotosi
mexico/sinaloa
mexico/sonora
mexico/tabasco
mexico/tamaulipas
mexico/tlaxcala
mexico/veracruz
mexico/yucatan
mexico/zacatecas
moldova
moldova/_disputed
monaco
mongolia
montenegro
montserrat
morocco
morocco/_disputed
mozambique
myanmar
namibia
nauru
nepal
nepal/_disputed
netherlands
newcaledonia
newzealand
newzealand/_disputed
nicaragua
nicaragua/_disputed
niger
nigeria
niue
norfolkisland
northerncyprus
northerncyprus/_disputed
northernmarianaislands
northkorea
northkorea/_disputed
norway
oman
pakistan
pakistan/_admin1
pakistan/_disputed
pakistan/azadkashmir
pakistan/baluchistan
pakistan/fata
pakistan/fct
pakistan/kp
pakistan/northernareas
pakistan/punjab
pakistan/sind
palau
palestine
palestine/_disputed
panama
papuanewguinea
paraguay
peru
peru/_admin1
peru/amazonas
peru/ancash
peru/apurimac
peru/arequipa
peru/ayacucho
peru/cajamarca
peru/callao
peru/cusco
peru/huancavelica
peru/huanuco
peru/ica
peru/junin
peru/lalibertad
peru/lambayeque
peru/lima
peru/limaprovince
peru/loreto
peru/madrededios
peru/moquegua
peru/pasco
peru/piura
peru/puno
peru/sanmartin
peru/tacna
peru/tumbes
peru/ucayali
philippines
philippines/_disputed
pitcairnislands
poland
portugal
portugal/_disputed
puertorico
qatar
republicofserbia
republicofserbia/_disputed
republicofthecongo
romania
russia
russia/_disputed
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
saudiarabia/_disputed
scarboroughreef
senegal
serranillabank
seychelles
seychelles/_disputed
siachenglacier
sierraleone
singapore
sintmaarten
slovakia
slovenia
slovenia/_disputed
solomonislands
somalia
somalia/_admin1
somalia/_disputed
somalia/bakool
somalia/banaadir
somalia/bari
somalia/bay
somalia/galguduud
somalia/gedo
somalia/hiiraan
somalia/jubbadadhexe
somalia/jubbadahoose
somalia/mudug
somalia/nugaal
somalia/shabeellahadhexe
somalia/shabeellahahoose
somaliland
southafrica
southernpatagonianicefield
southgeorgiaandtheislands
southkorea
southkorea/_disputed
southsudan
southsudan/_admin1
southsudan/_disputed
southsudan/centralequatoria
southsudan/easternequatoria
southsudan/jonglei
southsudan/lakes
southsudan/northernbahrelghazal
southsudan/unity
southsudan/uppernile
southsudan/warrap
southsudan/westernbahrelghazal
southsudan/westernequatoria
spain
spain/_disputed
spratlyislands
srilanka
sudan
sudan/_disputed
suriname
suriname/_disputed
sweden
switzerland
syria
syria/_disputed
taiwan
taiwan/_disputed
tajikistan
thailand
thebahamas
timorleste
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
ukraine/_disputed
unitedarabemirates
unitedarabemirates/_disputed
unitedkingdom
unitedkingdom/_disputed
unitedrepublicoftanzania
unitedstatesminoroutlyingislands
unitedstatesofamerica
unitedstatesofamerica/_admin1
unitedstatesofamerica/_disputed
unitedstatesofamerica/alabama
unitedstatesofamerica/alaska
unitedstatesofamerica/arizona
unitedstatesofamerica/arkansas
unitedstatesofamerica/california
unitedstatesofamerica/colorado
unitedstatesofamerica/connecticut
unitedstatesofamerica/delaware
unitedstatesofamerica/districtofcolumbia
unitedstatesofamerica/florida
unitedstatesofamerica/georgia
unitedstatesofamerica/hawaii
unitedstatesofamerica/idaho
unitedstatesofamerica/illinois
unitedstatesofamerica/indiana
unitedstatesofamerica/iowa
unitedstatesofamerica/kansas
unitedstatesofamerica/kentucky
unitedstatesofamerica/louisiana
unitedstatesofamerica/maine
unitedstatesofamerica/maryland
unitedstatesofamerica/massachusetts
unitedstatesofamerica/michigan
unitedstatesofamerica/minnesota
unitedstatesofamerica/mississippi
unitedstatesofamerica/missouri
unitedstatesofamerica/montana
unitedstatesofamerica/nebraska
unitedstatesofamerica/nevada
unitedstatesofamerica/newhampshire
unitedstatesofamerica/newjersey
unitedstatesofamerica/newmexico
unitedstatesofamerica/newyork
unitedstatesofamerica/northcarolina
unitedstatesofamerica/northdakota
unitedstatesofamerica/ohio
unitedstatesofamerica/oklahoma
unitedstatesofamerica/oregon
unitedstatesofamerica/pennsylvania
unitedstatesofamerica/rhodeisland
unitedstatesofamerica/southcarolina
unitedstatesofamerica/southdakota
unitedstatesofamerica/tennessee
unitedstatesofamerica/texas
unitedstatesofamerica/utah
unitedstatesofamerica/vermont
unitedstatesofamerica/virginia
unitedstatesofamerica/washington
unitedstatesofamerica/westvirginia
unitedstatesofamerica/wisconsin
unitedstatesofamerica/wyoming
unitedstatesvirginislands
uruguay
uruguay/_disputed
usnavalbaseguantanamobay
uzbekistan
vanuatu
vanuatu/_disputed
vatican
venezuela
venezuela/_disputed
vietnam
vietnam/_disputed
wallisandfutuna
westernsahara
westernsahara/_disputed
yemen
zambia
zimbabwe
```
