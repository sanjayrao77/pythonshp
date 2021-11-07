#!/usr/bin/python3

#  * github.com/sanjayrao77
#  * pythonshp.py - program to make maps from shp files
#  * Copyright (C) 2021 Sanjay Rao
#  *
#  * This program is free software; you can redistribute it and/or modify
#  * it under the terms of the GNU General Public License as published by
#  * the Free Software Foundation; either version 2 of the License, or
#  * (at your option) any later version.
#  *
#  * This program is distributed in the hope that it will be useful,
#  * but WITHOUT ANY WARRANTY; without even the implied warranty of
#  * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  * GNU General Public License for more details.
#  *
#  * You should have received a copy of the GNU General Public License
#  * along with this program; if not, write to the Free Software
#  * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


## Map options, ordered by importance

##	options['ispartlabels'] = True
# Setting this will draw labels pointing to the parts of the shp polygon. This is
# useful for identifying which part index corresponds to which shape on the map.
# You can toggle "ispartlabeltop_global" to draw the labels from the bottom or top.

## options['index'] = int
# The index number in the admin0 shp file to draw. Note that the admin0 dbf file
# refers to "record number" where "record number" = options['index'] + 1.

## options['isinsetleft'] = bool
# Should the Tripel full-world map be on the left-hand side? False => right-hand side.

## options['lonlabel_lat'] = int
# Where should the longitude labels be, in latitude. Value is in degrees.

## options['latlabel_lon'] = int
# Where should the latitude labels be, in longitude. Value is in degrees.

## options['title'] = string
# This is unreferenced but it is inserted in the svg header in a comment, to explain the contents.

## options['moredots'] = array of 3-tuples, (a,b,c) where a:radius beyond shape, b:width of stroke, c:partindices[]
# This will draw green circles around "parts" of polygons. The parts are referenced by their index in
# the shp record. The width of the stroke is in 1..4 for the pixel width, or False=>1 and True=>4.
# Note that the natural radius of the polygon would be a "0" value for "a".
# E.g.:
#  options['moredots'] = [ (4,1,[0]) ] # this creates a circle with 4px padding, 1px width around the first part

## options['zoomdots'] = array of 3-tuples, a la options['moredots']
# This is like options['moredots'] but it draws the circles on the zoom inset.

## options['smalldots'] = array of ints, as part indices
# This is a shortcut to options['moredots']. It's best not to use this.

## options['iszoom'] = bool
# Setting this True will create a zoom inset on the right-hand side. The default zoom scaling is 2.
# The default center of the zoom is the lon/lat position.

## options['zoomscale'] = int
# This sets the level of zoom for the zoom inset. The default value is 2. Only some values will work well.
# Working values are: 2,2.5,4,5,8,10,16,20,32,40,64,... based on clean division of "10".

## options['partindices'] = array of int, index values of parts
# The default is to draw every part in a polygon. This selects which parts (by index) should be drawn.

## options['lon'] = int, in degrees
# The default is to center the map drawing on the longitude of the center of the union of all
# the parts of a polygon. This option lets you override the longitude calculation.

## options['lat'] = int, in degrees
# The default is to center the map drawing on a longitude based on the center of the union of all
# the parts of a polygon, but scaled and clipped by the tropics.
# This option lets you override the latitude calculation. This might require options['lon'] set as well.

## options['tripelboxes'] = array of array of ints, in part indices
# The default is to draw a green rectangle on the Tripel inset around the union of the parts.
# This option lets you specify which part(s) should have the rectangle.
# E.g.
# 	options['tripelboxes']=[ [0,1,2], [70] ] # this creates 2 boxes, one around the first 3 parts and one on part 70

## options['centerdot'] = (radius:int,thickness)
# This draws a green circle around the center of the shape on the sphere. The radius is 'radius' and the thickness
# of the circle is 'thickness'. Valid values for thickness: [1,2,3,4,False,True]
# These are similar if there is only 1 part to the polygon:
#  options['centerdot']=(radius+padding,thickness)
# and
#  options['moredots']=(padding,thickness,[0])

## options['centerindices'] = array of ints, as part indices
# This will only use the specified parts to calculate the shape's center. Non-specified parts will still be drawn.

## options['istopinsets'] = bool
# If set True, this will place insets on the top of the image instead of the bottom.

## options['iszoom34'] = bool
# If set True, this will use a 3/4 size zoom inset. This requires options['iszoom']=True to draw an inset.

## options['issubland'] = bool
# Setting this False (default is True) will disable drawing admin1 state/province borders. This is used in
# places where it isn't needed anymore.

import struct
import math
import sys
import os

NULL_TYPE_SHP=0
POINT_TYPE_SHP=1
POLYLINE_TYPE_SHP=3
POLYGON_TYPE_SHP=5

NONE_PATCHTYPE=0
HEMI_PATCHTYPE=1
VERT_PATCHTYPE=2
HORIZ_PATCHTYPE=3

M_PI_2=math.pi/2.0
M_PI_4=math.pi/4.0
M_3PI_2=math.pi+M_PI_2

isverbose_global=False
ispartlabeltop_global=True
isantarcticamod_global=False

def uint32_big(buff,offset):
	b0=buff[offset]
	b1=buff[offset+1]
	b2=buff[offset+2]
	b3=buff[offset+3]
	return b0*16777216+b1*65536+b2*256+b3
def uint32_little(buff,offset):
	b0=buff[offset]
	b1=buff[offset+1]
	b2=buff[offset+2]
	b3=buff[offset+3]
	return b3*16777216+b2*65536+b1*256+b0
def uint16_little(buff,offset):
	b0=buff[offset]
	b1=buff[offset+1]
	return b1*256+b0
def getdouble(buff,offset):
	d=struct.unpack('d',buff[offset:offset+8])
	return d[0]

def shapename(typenum):
	if typenum==POLYGON_TYPE_SHP: return "polygon"
	if typenum==POLYLINE_TYPE_SHP: return "polyline"
	if typenum==POINT_TyPE_SHP: return "point"
	if typenum==NULL_TYPE_SHP: return "null"
	return "[unktype:"+str(typenum)+"]"

def tripel(lon,lat):
	if abs(lon)<0.001 and abs(lat)<0.001: return (0.5,0.5)
	rlon2=(lon*math.pi)/360.0
	rlat=(lat*math.pi)/180.0

	alpha=math.acos(math.cos(rlat)*math.cos(rlon2))
	if abs(alpha)<0.00001: raise ValueError
	sinca=math.sin(alpha)/alpha
	if abs(sinca)<0.00001: raise ValueError

	ux=2+math.pi
	ux+=4*rlon2/math.pi
	ux+=2*math.cos(rlat)*math.sin(rlon2)/sinca
	ux=ux/(4+math.tau)

	uy=math.pi
	uy+=rlat
	uy+=math.sin(rlat)/sinca
	uy=uy/math.tau

	return (ux,uy)

class Output():
	def __init__(self):
		self.file=sys.stdout
	def setfile(self,outf):
		self.file=outf
	def print(self,*a,**ka):
		ka['file']=self.file
		print(*a,**ka)

class Mbr():
	def __init__(self):
		self.isset=False
	def set(self,minx,miny,maxx,maxy):
		self.isset=True
		self.minx=minx
		self.miny=miny
		self.maxx=maxx
		self.maxy=maxy
	def add(self,x,y):
		if not self.isset:
			self.isset=True
			self.minx=x
			self.miny=y
			self.maxx=x
			self.maxy=y
		else:
			if x<self.minx: self.minx=x
			elif x>self.maxx: self.maxx=x
			if y<self.miny: self.miny=y
			elif y>self.maxy: self.maxy=y
	def print(self):
		if self.isset: print('mbr: minx:%f, miny:%f, maxx:%f, maxy:%f'%(self.minx,self.miny,self.maxx,self.maxy))

class DegLonLat():
	def __init__(self,lon,lat,side=0,patchtype=NONE_PATCHTYPE):
		self.lon=lon
		self.lat=lat
		self.side=side
		self.patchtype=patchtype
	def print(self):
		print('( %.3f,%.3f )'%(self.lon,self.lat),file=sys.stderr)
	def clone(self):
		return DegLonLat(self.lon,self.lat,self.side,self.patchtype)

def getangle(x1,y1,x2,y2):
	if y2>y1:
		if x2>x1: return math.atan((y2-y1)/(x2-x1))
		elif x2==x1: return M_PI_2
		else: return math.atan((x1-x2)/(y2-y1))+M_PI_2
	elif y2==y1:
		if x2>=x1: return 0.0 # x1==x2 is undefined, we check vertices first to avoid this
		else: return math.pi
	else:
		if x2>x1: return M_3PI_2+math.atan((x2-x1)/(y1-y2))
		elif x2==x1: return M_3PI_2
		else: return math.pi+math.atan((y1-y2)/(x1-x2))

class Polygon():
	@staticmethod
	def make(shape,pointstart,pointlimit,index,partindex):
		pg=Polygon(index,partindex)
		for i in range(pointstart,pointlimit):
			p=shape.pointlist[i]
			pg.addDegLonLat(p)
		pg.finish()
		return pg
	def __init__(self,index,partindex):
		self.points=[]
		self.index=index
		self.partindex=partindex
	def addDegLonLat(self,p):
		if 0==len(self.points): self.points.append(p)
		else:
			lp=self.points[-1]
			if p.lon!=lp.lon or p.lat!=lp.lat: self.points.append(p)
	def finish(self):
		lp=self.points[-1]
		fp=self.points[0]
		if fp.lon==lp.lon and fp.lat==lp.lat: self.points.pop()
		self.iscw=self._iscw()
	def print(self,index,dopoints):
		print('polygon %d: %d iscw:%s'%(index,len(self.points),self.iscw))
		if dopoints:
			for p in self.points:
				print('%.12f,%.12f'%(p.lon,p.lat))
	def isvertex(self,lon,lat):
		for p in self.points:
			if abs(p.lon-lon)<0.01 and abs(p.lat-lat)<0.01: return True
		return False
	def isinterior(self,lon,lat):
		p=self.points[0]
		a0=getangle(lon,lat,p.lon,p.lat)
		a=a0
		t=0.0
		for i in range(1,len(self.points)):
			p=self.points[i]
			a2=getangle(lon,lat,p.lon,p.lat)
			d=a2-a
			if d>math.pi: d-=math.tau
			elif d<-math.pi: d+=math.tau
			t+=d
			a=a2
		d=a0-a
		if d>math.pi: d-=math.tau
		elif d<-math.pi: d+=math.tau
		t+=d
		if t<-math.pi: return True
		if t>math.pi: return True
		return False

	def getlowindex(self):
		lowindex=0
		lowlon=self.points[0].lon
		lowlat=self.points[0].lat
		for i in range(1,len(self.points)):
			ilon=self.points[i].lon
			ilat=self.points[i].lat
			if ilat < lowlat or (ilat==lowlat and ilon < lowlon):
				lowindex=i
				lowlon=ilon
				lowlat=ilat
		return lowindex
	def _iscw3(self,a,b,c):
		one=self.points[a]
		two=self.points[b]
		three=self.points[c]
		xp=(two.lon-one.lon)*(three.lat-two.lat)-(two.lat-one.lat)*(three.lon-two.lon)
		if xp < 0.0: return True
		return False
	def _iscw(self):
		if len(self.points)<3: raise ValueError
		low=self.getlowindex()
		lastindex=len(self.points)-1
		if low==0: return self._iscw3(lastindex,0,1)
		if low==lastindex: return self._iscw3(low-1,low,0)
		return self._iscw3(low-1,low,low+1)

class Polyline():
	def __init__(self,shape,pointstart,pointlimit):
		self.points=shape.pointlist[pointstart:pointlimit]
	def print(self,index):
		print('polyline '+str(index)+': '+str(len(self.points)))

class ShapePlus():
	@staticmethod
	def make(shape):
		if shape.type==POLYGON_TYPE_SHP:
			ret=[]
			sp=None
			for i in range(shape.partscount):
				j=shape.pointscount
				if i+1<shape.partscount: j=shape.partlist[i+1]
				pg=Polygon.make(shape,shape.partlist[i],j,shape.index,i)
				pg.partindex=i
				if pg.iscw:
					sp=ShapePlus(shape.cssclasslist[i],shape.draworderlist[i])
					sp.type=POLYGON_TYPE_SHP
					sp.polygons=[pg]
					ret.append(sp)
				else:
					if sp==None: raise ValueError('Unexpected ccw w/o preceding cw in shape index:',shape.index)
					sp.polygons.append(pg)
			if shape.isflagged: ShapePlus.fixflagged(shape,ret)
			return ret
		elif shape.type==POLYLINE_TYPE_SHP:
			ret=[]
			for i in range(shape.partscount):
				j=shape.pointscount
				if i+1<shape.partscount: j=shape.partlist[i+1]
				pl=Polyline(shape,shape.partlist[i],j)
				pl.partindex=i
				sp=ShapePlus(shape.cssclasslist[i],shape.draworderlist[i])
				sp.type=POLYLINE_TYPE_SHP
				sp.polylines=[pl]
				ret.append(sp)
			return ret
		elif shape.type==POINT_TYPE_SHP:
			sp=ShapePlus(shape.cssclass,shape.draworder)
			sp.type=POINT_TYPE_SHP
			sp.point=shape.point
			return [sp]
		elif shape.type==NULL_TYPE_SHP:
			return []
		else: raise ValueError
	@staticmethod
	def antarctica_fixflagged(pg):
		k=len(pg.points)
		start=0
		stop=0
		for l in range(k):
			if pg.points[l].lon>179.9999:
				start=l
				break
		else: raise ValueError
		for l in range(start+1,k):
			if pg.points[l].lon<=179.9999: break
		else: raise ValueError
		for l in range(l,k):
			if pg.points[l].lat>=-89.9999: break
		else: raise ValueError
		for l in range(l,k):
			if pg.points[l].lon>-179.9999: break
		else: raise ValueError
		stop=l
		if isverbose_global: 
			global isantarcticamod_global
			if not isantarcticamod_global: # only print once, as a warning
				isantarcticamod_global=True
				print('Warning, base data modified: Antarctica removing %d..%d of %d'%(start,stop,k),file=sys.stderr)
		del pg.points[start:stop+1]
	@staticmethod
	def fixflagged(shape,pluses):
		if shape.index==172:
			if shape.type!=POLYGON_TYPE_SHP: raise ValueError
			if len(pluses)!=179:
				print('Fixing antarctica, expected 179 parts, instead found %d'%len(pluses),file=sys.stderr)
				raise ValueError
			if len(pluses[0].polygons)!=1: raise ValueError
			ShapePlus.antarctica_fixflagged(pluses[0].polygons[0])
	@staticmethod
	def makeflatbox(ispolygon,cssclass):
		shape=Shape(0,0,cssclass)
		if ispolygon: shape.type=POLYGON_TYPE_SHP
		else: shape.type=POLYLINE_TYPE_SHP
		shape.partlist=[0]
		shape.draworderlist=[0]
		shape.cssclasslist=[cssclass]
		shape.pointlist=[]
		lon=-180.0
		lat=-90.0
		while lat<=90.0:
			shape.pointlist.append(DegLonLat(lon,lat))
			lat+=0.1
		lon=180.0
		lat=90.0
		while lat>=-90.0:
			shape.pointlist.append(DegLonLat(lon,lat))
			lat-=0.1
		shape.pointlist.append(DegLonLat(-180.0,-90.0))
			
		shape.partscount=1
		shape.pointscount=len(shape.pointlist)
		if ispolygon: px=Polygon.make(shape,0,shape.pointscount,0,0)
		else: px=Polyline(shape,0,shape.pointscount)
		px.partindex=0
		sp=ShapePlus(cssclass,0)
		sp.type=shape.type
		if ispolygon: sp.polygons=[px]
		else: sp.polylines=[px]
		return sp
	def __init__(self,cssclass,draworder):
		self.cssclass=cssclass
		self.draworder=draworder
	def print(self):
		if self.type==POLYGON_TYPE_SHP:
			print('Polygon, count: '+str(len(self.polygons)))
			for i in range(len(self.polygons)):
				self.polygons[i].print(i,True)
	def ispartindex(self,partindex):
		if partindex==-1: return True
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons:
				if pg.partindex==partindex: return True
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines:
				if pl.partindex==partindex: return True
		return False

class ShapePolyline():
	@staticmethod
	def makelat(index,shapenumber,deg,cssclass):
		sp=ShapePolyline(index,shapenumber,cssclass)
		lon=-180.0
		while True:
			sp.addpoint(lon,deg)
			lon+=0.1
			if lon>180.0: break
		return sp
	@staticmethod
	def makelon(index,shapenumber,deg,cssclass):
		sp=ShapePolyline(index,shapenumber,cssclass)
		lat=-90.0
		while True:
			sp.addpoint(deg,lat)
			lat+=0.1
			if lat>90.0: break
		return sp
	def __init__(self,index,shapenumber,cssclass):
		self.index=index
		self.number=shapenumber
		self.draworder=0
		self.type=POLYLINE_TYPE_SHP
		self.partlist=[0]
		self.pointlist=[]
		self.cssclasslist=[cssclass]
		self.draworderlist=[0]
		self.partscount=1
		self.pointscount=0
	def addpoint(self,lon,lat):
		p=DegLonLat(lon,lat)
		self.pointlist.append(p)
		self.pointscount+=1

class Shape():
	@staticmethod
	def make(index,shapenumber,cssclass,shapedata):
		ret=Shape(index,shapenumber,cssclass)
		ret.type=uint32_little(shapedata,0)
		if ret.type==POLYGON_TYPE_SHP or ret.type==POLYLINE_TYPE_SHP: # polygon or polyline
			ret.partlist=[]
			ret.pointlist=[]
			ret.cssclasslist=[]
			ret.draworderlist=[]
			mbr=Mbr()
			mbr.set( getdouble(shapedata,4), getdouble(shapedata,12), getdouble(shapedata,20), getdouble(shapedata,28) )
			ret.mbr=mbr
			ret.partscount=uint32_little(shapedata,36)
			ret.pointscount=uint32_little(shapedata,40)
			offset=44
			for i in range(ret.partscount):
				part=uint32_little(shapedata,offset)
				ret.partlist.append(part)
				ret.cssclasslist.append(cssclass)
				ret.draworderlist.append(0)
				offset+=4
			for i in range(ret.pointscount):
				x=getdouble(shapedata,offset)
				y=getdouble(shapedata,offset+8)
				ret.pointlist.append(DegLonLat(x,y))
				offset+=16
		elif ret.type==POINT_TYPE_SHP:
			x=getdouble(shapedata,4)
			y=getdouble(shapedata,12)
			ret.point=DegLonLat(x,y)
			offset+=20
		elif ret.type==NULL_TYPE_SHP:
			offset+=4
		else:
			raise ValueError
		return ret
	def __init__(self,index,shapenumber,cssclass):
		self.index=index
		self.number=shapenumber
		self.cssclass=cssclass
		self.draworder=0
		self.isflagged=False
	def setflag(self,v=True): self.isflagged=v
	def print(self,prefix=''):
		print('%snumber: %d, shape: %s, parts: %d, points: %d'%(prefix,self.number,shapename(self.type),self.partscount,self.pointscount),file=sys.stderr)
		if True:
			for i in range(self.partscount):
				j=self.partlist[i]
				k=self.pointscount
				if i+1<self.partscount: k=self.partlist[i+1]
#				if True: if self.pointlist[j].lon>-77: continue
				if self.type==POLYGON_TYPE_SHP:
					pg=Polygon.make(self,j,k,0,0)
					print('%d: %d points (%d..%d), iscw:%s'%(i,k-j,j,k,pg.iscw),file=sys.stderr)
				else:
					print('%d: %d points (%d..%d)'%(i,k-j,j,k),file=sys.stderr)
				if False:
					for l in range(j,k):
						p=self.pointlist[l]
						p.print()
	def removepoints(self,start,count): # points shouldn't cross parts
		del self.pointlist[start:start+count]
		self.pointscount-=count
		for i in range(self.partscount):
			if self.partlist[i]>start: self.partlist[i]-=count

class Shp(): # don't try to extend shp, just store data as literally as possible
	def __init__(self,filename,cssclass):
		self.filename=filename
		self.cssclass=cssclass
		self.shapes=[]
	def printinfo(self):
		f=open(self.filename,"rb")
		header=f.read(100)
		filecode=uint32_big(header,0)
		bytes_filelength=2*uint32_big(header,24)
		version=uint32_little(header,28)
		print('filecode: 0x%x' % filecode)
		print('bytes_filelength: '+str(bytes_filelength))
		print('version: '+str(version))
		offset=100
		while True:
			if offset==bytes_filelength: break
			f.seek(offset)
			buff12=f.read(12)
			rnumber=uint32_big(buff12,0)
			rlength=2*uint32_big(buff12,4)
			shapetype=uint32_little(buff12,8)
			buff32=f.read(32)
			minx=getdouble(buff32,0)
			miny=getdouble(buff32,8)
			maxx=getdouble(buff32,16)
			maxy=getdouble(buff32,24)
			print('%d: offset: %d, shape: %s, mbr:(%d,%d) -> (%d,%d)'%(rnumber,offset,shapename(shapetype),minx,miny,maxx,maxy),file=sys.stderr)
			
			offset+=8+rlength
		f.close()
	def loadshapes(self):
		f=open(self.filename,"rb")
		header=f.read(100)
		bytes_filelength=2*uint32_big(header,24)
		offset=100
		index=0
		while True:
			if offset==bytes_filelength: break
			f.seek(offset)
			buff8=f.read(8)
			rnumber=uint32_big(buff8,0)
			rlength=2*uint32_big(buff8,4)
			shapedata=f.read(rlength)
			shape=Shape.make(index,rnumber,self.cssclass,shapedata)
			self.shapes.append(shape)
			offset+=8+rlength
			index+=1
		f.close()
	def setcssclass(self,index,partidx,cssclass,draworder):
		shape=self.shapes[index]
		if partidx<0:
			shape.cssclass=cssclass
			shape.draworder=draworder
			if hasattr(shape,'cssclasslist'):
				for i in range(len(shape.cssclasslist)):
					shape.cssclasslist[i]=cssclass
					shape.draworderlist[i]=draworder
		else:
			shape.cssclasslist[partidx]=cssclass
			shape.draworderlist[partidx]=draworder
	def resetcssclass(self,cssclass):
		for i in range(len(self.shapes)):
			self.setcssclass(i,-1,cssclass,0)
	def getcenter(self,index,partindices):
		mbr=Mbr()
		for partidx in partindices:
			shape=self.shapes[index]
			if partidx<0:
				for p in shape.pointlist:
					mbr.add(p.lon,p.lat)
			else:
				limit=shape.pointscount
				if partidx+1<shape.partscount: limit=shape.partlist[partidx+1]
				for ptidx in range(shape.partlist[partidx],limit):
					p=shape.pointlist[ptidx]
					mbr.add(p.lon,p.lat)
		return ((mbr.maxx+mbr.minx)/2,(mbr.maxy+mbr.miny)/2)
			
		

class SphereRotation():
	def __init__(self):
		self.isy=False
		self.isx=False
	def deg_getcenter(self):
		if not self.isx: return (0,0)
		if not self.isy: return (self.dlon,0)
		return (self.dlon,self.dlat)
	def set_deglon(self,dlon):
		self.isx=True
		self.dlon=dlon
	def set_deglonlat(self,dlon,dlat):
		self.isx=True
		self.isy=True
		self.dlon=dlon
		self.dlat=dlat
		rlat=(dlat*math.pi)/180.0
		self.a=math.cos(rlat)
		self.c=math.sin(rlat)
	def xyz_fromdll(self,lon,lat):
		if self.isx:
			lon-=self.dlon
		rlon=(lon*math.pi)/180.0
		rlat=(lat*math.pi)/180.0
		r=math.cos(rlat)
		x=r*math.cos(rlon)
		y=r*math.sin(rlon)
		z=math.sin(rlat)
		if self.isy:
			x2=x*self.a+z*self.c
			z2=-x*self.c+z*self.a
			x=x2
			z=z2
		return (x,y,z)
	def dll_fromxyz(self,x,y,z):
		if self.isy:
			x2=x*self.a-z*self.c
			z2=x*self.c+z*self.a
			x=x2
			z=z2
		lat=math.asin(z)
		r=math.cos(lat)
		if abs(r)<0.001:
			lon=0.0
		else:
			lon=math.asin(y/r)
			if x<0.0:
				if lon<0.0: lon=-math.pi-lon
				else: lon=math.pi-lon
		dlon=(lon*180.0)/math.pi
		dlat=(lat*180.0)/math.pi
		if self.isx:
			dlon+=self.dlon
			if dlon>180.0: dlon-=360.0
			elif dlon<-180.0: dlon+=360.0
		return (dlon,dlat)

class SpherePoint():
	@staticmethod
	def makefromdll(dll,rotation):
		sp=SpherePoint()
		sp.patchtype=NONE_PATCHTYPE
		sp.side=0
		sp.lon=dll.lon
		sp.lat=dll.lat

		if True: 
			if abs(180.0-abs(dll.lon))<0.00001: # this cleans up Russia's fake border
#					print('Setting patch for %f,%f'%(self.lon,self.lat),file=sys.stderr)
				sp.patchtype=HEMI_PATCHTYPE
			if False: # this could fix Antartica but it creates a crease, use Shape.fix180() instead
				if sp.lon<-179.99999: sp.lon=-179.999999
				elif sp.lon>179.99999: sp.lon=179.99999

		(sp.x,sp.y,sp.z)=rotation.xyz_fromdll(sp.lon,sp.lat)
		return sp
	def print(self):
		print('point: (%f,%f), (%f,%f,%f)' % (self.lon,self.lat,self.x,self.y,self.z),file=sys.stderr)
	def clone(self):
		sp=SpherePoint()
		sp.lon=self.lon
		sp.lat=self.lat
		sp.side=self.side
		sp.x=self.x
		sp.y=self.y
		sp.z=self.z
		sp.patchtype=self.patchtype
		return sp
	def flatten(self,width,height):
		ux=int(0.5+((self.y+1.0)*(width-1))/2.0)
		uy=int(0.5+((1.0-self.z)*(height-1))/2.0)
		return FlatPoint(ux,uy,NONE_PATCHTYPE)

class MercatorPoint():
	def __init__(self,obj):
		if isinstance(obj,DegLonLat):
			dll=obj
			self.lon=dll.lon
			self.lat=dll.lat
			self.side=0
			self.patchtype=NONE_PATCHTYPE
		elif isinstance(obj,MercatorPoint):
			self.lon=obj.lon
			self.lat=obj.lat
			self.side=obj.side
			self.patchtype=obj.patchtype
		elif obj==None: return
		else: raise ValueError
	def print(self):
		print('point: (%f,%f)' % (self.lon,self.lat))
	def clone(self):
		return MercatorPoint(self)

def TripelPoint(a): return MercatorPoint(a)


class FlatPoint():
	@staticmethod
	def distance(ux1,uy1,ux2,uy2):
		dx=ux2-ux1
		dy=uy2-uy1
		return math.sqrt(dx*dx+dy*dy)
	def __init__(self,ux,uy,patchtype):
		self.ux=ux
		self.uy=uy
		self.patchtype=patchtype

class FlatPolygon():
	def __init__(self,iscw,index,partindex):
		self.points=[]
		self.iscw=iscw
		self.index=index
		self.partindex=partindex
	def addpoint(self,ux,uy,patchtype):
		if len(self.points)!=0:
			if self.lastux==ux and self.lastuy==uy and self.lastpatchtype==patchtype: return
		self.lastux=ux
		self.lastuy=uy
		self.lastpatchtype=patchtype
		self.points.append(FlatPoint(ux,uy,patchtype))
	def shift(self,shift):
		for p in self.points:
			p.ux+=shift.xoff
			p.uy+=shift.yoff

class FlatPolyline():
	def __init__(self):
		self.points=[]
	def addpoint(self,ux,uy):
		if len(self.points)!=0:
			if self.lastux==ux and self.lastuy==uy: return
		self.lastux=ux
		self.lastuy=uy
		self.points.append(FlatPoint(ux,uy,False))
	def shift(self,shift):
		for p in self.points:
			p.ux+=shift.xoff
			p.uy+=shift.yoff

class Shift():
	def __init__(self,xoff,yoff):
		self.xoff=xoff
		self.yoff=yoff

class BoxZoom():
	def __init__(self,factor,left,right,bottom,top):
		self.factor=factor
		self.left=left
		self.right=right
		self.bottom=bottom
		self.top=top


class FlatShape():
	def __init__(self,cssclass):
		self.cssclass=cssclass
	def setpolygon(self):
		self.type=POLYGON_TYPE_SHP
		self.polygons=[]
	def addpolygon(self,fp):
		self.polygons.append(fp)
	def setpolyline(self):
		self.type=POLYLINE_TYPE_SHP
		self.polylines=[]
	def addpolyline(self,fp):
		self.polylines.append(fp)
	def shift(self,shift):
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons: pg.shift(shift)
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines: pl.shift(shift)
	def addtombr(self,mbr):
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons:
				for p in pg.points:
					mbr.add(p.ux,p.uy)
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines:
				for p in pl.points:
					mbr.add(p.ux,p.uy)
	def path_printsvg(self,output):
		output.print('<path class=\"'+self.cssclass+'\" d=\"M',end='')
		i=0
		pg=self.polygons[i]
		p=pg.points[0]
		output.print(' %d,%d' % (p.ux,p.uy),end='')
		for j in range(1,len(pg.points)):
			p=pg.points[j]
			output.print(' L %d,%d' % (p.ux,p.uy),end='')
		while True:
			i+=1
			if i==len(self.polygons): break
			pg=self.polygons[i]
			output.print(' Z M',end='')
			p=pg.points[0]
			output.print(' %d,%d' % (p.ux,p.uy),end='')
			for j in range(1,len(pg.points)):
				p=pg.points[j]
				output.print(' L %d,%d' % (p.ux,p.uy),end='')
		output.print(' Z\" />')
	def border_printsvg(self,output):
		for pg in self.polygons:
			if len(pg.points)<2: continue
			p=pg.points[-1]
			isonpatch=(p.patchtype!=NONE_PATCHTYPE)
			if isonpatch: output.print('<polyline class="'+self.cssclass+'_patch" points="',end='')
			else: output.print('<polyline class="'+self.cssclass+'_border" points="',end='')
			output.print('%d,%d ' % (p.ux,p.uy),end='')
			for p in pg.points:
				if isonpatch!=(p.patchtype!=NONE_PATCHTYPE):
					output.print('%d,%d" />'%(p.ux,p.uy))
					isonpatch=(p.patchtype!=NONE_PATCHTYPE)
					if isonpatch: output.print('<polyline class="'+self.cssclass+'_patch" points="',end='')
					else: output.print('<polyline class="'+self.cssclass+'_border" points="',end='')
				output.print('%d,%d ' % (p.ux,p.uy),end='')
			output.print('" />')
	def polyline_printsvg(self,output):
		for pl in self.polylines:
			if len(pl.points)<2: continue
			output.print('<polyline class="'+self.cssclass+'" points="',end='')
			for p in pl.points:
				output.print('%d,%d ' % (p.ux,p.uy),end='')
			output.print('" />')
		
	def printsvg(self,output):
		if self.type==POLYGON_TYPE_SHP:
			self.path_printsvg(output)
			self.border_printsvg(output)
		elif self.type==POLYLINE_TYPE_SHP:
			self.polyline_printsvg(output)
			

class Segments():
	@staticmethod
	def insertsegment(s,a):
		a.next=s.next
		s.next=a
	def __init__(self,param,ispolyline=False,last=None): 
		if isinstance(param,list): # param should have positive and negative side SpherePoints
			a=[]
			prevp=param[0].clone()
			a.append(prevp)
			for i in range(1,len(param)):
				p=param[i].clone()
				a.append(p)
				prevp.next=p
				prevp=p
			prevp.next=a[0]
			for p in a:
				if p.side!=0:
					self.first=p # don't want to start on 0
					break
			if ispolyline:
				self.last=a[-1]
				self.last.next=self.first
		else:
			self.first=param
			if ispolyline:
				self.last=last
	def hasposside(self):
		s=self.first
		while True:
			if s.side>0: return True
			s=s.next
			if s==self.first: break
		return False

class Intersection():
	def __init__(self,s,s0,n0,n):
		self.s=s
		self.s0=s0
		self.n0=n0
		self.n=n

class SphereIntersections():
	@staticmethod
	def setsides(points):
		hasneg=False
		haspos=False
		for p in points:
			if p.x<0.0:
				hasneg=True
				p.side=-1
			elif p.x==0.0:
				p.side=0
			else:
				haspos=True
				p.side=1
		if hasneg and haspos: return 0
		if hasneg: return 1
		return 2
	@staticmethod
	def crossukey(o): return o.crossu
	@staticmethod
	def crossucalc(y,z):
		if z>=0.0: return 1.0-y # 0 to 2
		return 3.0+y # 2 to 4
	@staticmethod
	def sidewalkahead(s):
		s=s.next
		firstzero=None
		otherzero=None
		if s.side==0:
			firstzero=s
			s=s.next
			while s.side==0:
				otherzero=s # only set if not firstzero
				s=s.next
		firstnonzero=s
		return (firstzero,otherzero,firstnonzero)
	@staticmethod
	def makeintersectionpoint(s,n):
		dx=n.x-s.x
		dy=n.y-s.y
		dz=n.z-s.z
		t=-s.x/dx

		y=s.y+t*dy
		z=s.z+t*dz
		hh=y*y+z*z
		scale=math.sqrt(1/hh)
		y=y*scale
		z=z*scale
		
		i=SpherePoint()
		i.lon=0
		i.lat=0
		i.side=0
		i.x=0.0
		i.y=y
		i.z=z
		i.patchtype=s.patchtype # s0 will change later after stitching
		return i
		
	def __init__(self,segments,limit=None):
		self.list=[]
		s=segments.first # doesn't start with a side:0
		if limit==None: limit=s
		while True:
			if s.side!=s.next.side:
				(firstzero,otherzero,firstnonzero)=SphereIntersections.sidewalkahead(s)
				if s.side!=firstnonzero.side:
					if firstzero==None:
						firstzero=SphereIntersections.makeintersectionpoint(s,firstnonzero)
						Segments.insertsegment(s,firstzero)
					if otherzero==None:
						otherzero=firstzero.clone()
						Segments.insertsegment(firstzero,otherzero)
					firstzero.next=otherzero
				self.list.append(Intersection(s,firstzero,otherzero,firstnonzero))
				s=firstnonzero
			else:
				s=s.next
			if s==limit: break
	def setcrossu(self,isinterior,y,z):
		exu=SphereIntersections.crossucalc(y,z)
		if isinterior:
			best=4.0
			for i in self.list:
				xu=SphereIntersections.crossucalc(i.s0.y,i.s0.z)
				if xu<exu: d=exu-xu
				else: d=4.0+xu-exu
				if d<best: best=d
				i.crossu=xu
			for i in self.list:
				i.crossu-=best
				if i.crossu<0.0: i.crossu+=4.0
		else:
			for i in self.list:
				xu=SphereIntersections.crossucalc(i.s0.y,i.s0.z)
				if xu<exu: xu+=4.0
				xu-=exu
				i.crossu=xu
	def fix(self,polygon,rotation):
		th=0.0
		fuse=100
		step=math.pi
		while True:
			y=math.cos(th)
			z=math.sin(th)
			(lon,lat)=rotation.dll_fromxyz(0.0,y,z)
			if not polygon.isvertex(lon,lat):
				isit=polygon.isinterior(lon,lat)
#				print('Found point %f,%f to be interior:%s, theta:%f' % (lon,lat,isit,th))
				self.setcrossu(isit,y,z)
				break
			fuse-=1
			if 0==fuse: raise ValueError
			th+=step
			if th>=math.tau:
				step=step/2.0
				th=step
		self.list.sort(key=SphereIntersections.crossukey)
	def print(self):
		if 0==len(self.list): return
		if not hasattr(self.list[0],'crossu'):
			for x in self.list:
				print('intersection (%.6f,%.3f,%.3f) to (%.6f,%.3f,%.3f) x (%.6f,%.3f,%.3f) to (%.6f,%.3f,%.3f)' % (x.s.x,x.s.y,x.s.z, x.s0.x,x.s0.y,x.s0.z, x.n0.x,x.n0.y,x.n0.z, x.n.x,x.n.y,x.n.z),file=sys.stderr)
			return
		for x in self.list:
			print('intersection (%.6f,%.2f,%.2f) to (%.6f,%.2f,%.2f) x (%.6f,%.2f,%.2f) to (%.6f,%.2f,%.2f) crossu:%.12f' % (x.s.x,x.s.y,x.s.z, x.s0.x,x.s0.y,x.s0.z, x.n0.x,x.n0.y,x.n0.z, x.n.x,x.n.y,x.n.z, x.crossu),file=sys.stderr)
		for i in range(0,len(self.list)-1):
			x=self.list[i]
			y=self.list[i+1]
			if (abs(x.crossu-y.crossu)<0.00000001):
				print('Dupe Point: (%f,%f) to (%f,%f) and (%f,%f) to (%f,%f)'%(x.s.lon,x.s.lat,x.n.lon,x.n.lat,
						y.s.lon,y.s.lat,y.n.lon,y.n.lat),file=sys.stderr)

class SphereIntersections2(): # yz
	@staticmethod
	def setsides(points,isz,ishigh,val):
		hasneg=False
		haspos=False
		if isz:
			if ishigh:
				for p in points:
					if p.z>val:
						hasneg=True
						p.side=-1
					elif p.z==val: p.side=0
					else:
						haspos=True
						p.side=1
			else:
				for p in points:
					if p.z<val:
						hasneg=True
						p.side=-1
					elif p.z==val: p.side=0
					else:
						haspos=True
						p.side=1
		else:
			if ishigh:
				for p in points:
					if p.y>val:
						hasneg=True
						p.side=-1
					elif p.y==val: p.side=0
					else:
						haspos=True
						p.side=1
			else:
				for p in points:
					if p.y<val:
						hasneg=True
						p.side=-1
					elif p.y==val: p.side=0
					else:
						haspos=True
						p.side=1
		if hasneg and haspos: return 0
		if hasneg: return 1
		return 2
	@staticmethod
	def crossukey(o): return o.crossu
	@staticmethod
	def sidewalkahead(s):
		s=s.next
		firstzero=None
		otherzero=None
		if s.side==0:
			firstzero=s
			s=s.next
			while s.side==0:
				otherzero=s # only set if not firstzero
				s=s.next
		firstnonzero=s
		return (firstzero,otherzero,firstnonzero)
	@staticmethod
	def makeintersectionpoint(s,n,isz,v):
		dy=n.y-s.y
		dz=n.z-s.z
		if isz:
			t=(v-s.z)/dz
			y=s.y+t*dy
			z=v
		else:
			t=(v-s.y)/dy
			z=s.z+t*dz
			y=v
		x=math.sqrt(1-y*y-z*z)

		i=SpherePoint()
		i.lon=0
		i.lat=0
		i.side=0
		i.x=x
		i.y=y
		i.z=z
		i.patchtype=s.patchtype # s0 will change later after stitching
		return i
		
	def __init__(self,isz,v,segments,limit=None):
		self.list=[]
		s=segments.first # doesn't start with a side:0
		if limit==None: limit=s
		while True:
			if s.side!=s.next.side:
				(firstzero,otherzero,firstnonzero)=SphereIntersections2.sidewalkahead(s)
				if s.side!=firstnonzero.side:
					if firstzero==None:
						firstzero=SphereIntersections2.makeintersectionpoint(s,firstnonzero,isz,v)
						Segments.insertsegment(s,firstzero)
					if otherzero==None:
						otherzero=firstzero.clone()
						Segments.insertsegment(firstzero,otherzero)
					firstzero.next=otherzero
				self.list.append(Intersection(s,firstzero,otherzero,firstnonzero))
				s=firstnonzero
			else:
				s=s.next
			if s==limit: break
	def sort(self,isz):
		if isz:
			for x in self.list: x.crossu=x.s0.y
		else:
			for x in self.list: x.crossu=x.s0.z
		self.list.sort(key=SphereIntersections2.crossukey)

class MercatorIntersections():
	@staticmethod
	def setsides(points,ishigh,val):
		hasneg=False
		haspos=False
		if ishigh:
			for p in points:
				if p.lat>val:
					hasneg=True
					p.side=-1
				else:
					haspos=True
					p.side=1
		else:
			for p in points:
				if p.lat<val:
					hasneg=True
					p.side=-1
				else:
					haspos=True
					p.side=1
		if hasneg and haspos: return 0
		if hasneg: return 1
		return 2
	@staticmethod
	def crossukey(o): return o.crossu
	@staticmethod
	def sidewalkahead(s):
		s=s.next
		firstzero=None
		otherzero=None
		if s.side==0:
			firstzero=s
			s=s.next
			while s.side==0:
				otherzero=s # only set if not firstzero
				s=s.next
		firstnonzero=s
		return (firstzero,otherzero,firstnonzero)
	@staticmethod
	def makeintersectionpoint(s,n,v):
		dx=n.lon-s.lon
		dy=n.lat-s.lat
		t=(v-s.lat)/dy

		x=s.lon+t*dx
		y=v

		i=DegLonLat(x,y)
		i.side=0
		i.patchtype=s.patchtype # s0 will change later after stitching
		return i
		
	def __init__(self,val,segments,limit=None):
		self.list=[]
		s=segments.first # doesn't start with a side:0
		if limit==None: limit=s
		while True:
			if s.side!=s.next.side:
				(firstzero,otherzero,firstnonzero)=MercatorIntersections.sidewalkahead(s)
				if s.side!=firstnonzero.side:
					if firstzero==None:
						firstzero=MercatorIntersections.makeintersectionpoint(s,firstnonzero,val)
						Segments.insertsegment(s,firstzero)
					if otherzero==None:
						otherzero=firstzero.clone()
						Segments.insertsegment(firstzero,otherzero)
					firstzero.next=otherzero
				self.list.append(Intersection(s,firstzero,otherzero,firstnonzero))
				s=firstnonzero
			else:
				s=s.next
			if s==limit: break
	def sort(self):
		for x in self.list: x.crossu=x.s0.lon
		self.list.sort(key=MercatorIntersections.crossukey)
		
class SegmentSet():
	@staticmethod
	def setindex(first,index):
		s=first
		while True:
			s.ssindex=index
			s=s.next
			if s==first: break
	def __init__(self,segments):
		self.list=[segments]
		SegmentSet.setindex(segments.first,0)
	def split1(self,intersections):
		for one in intersections.list:
			index=one.s.ssindex
			segs=self.list[index]

			onestart=segs.first
			onelast=one.s0
			twostart=one.n0
			twolast=segs.last

			onelast.next=onestart
			twolast.next=twostart
			s1=Segments(onestart,True,onelast)
			s2=Segments(twostart,True,twolast)
			SegmentSet.setindex(twostart,len(self.list))
			self.list.append(s2)
			self.list[index]=s1
		
	def split2(self,intersections,patchtype):
		n=len(intersections.list)
		i=0
		while i<n:
			one=intersections.list[i]
			two=intersections.list[i+1]
			index=one.s.ssindex
			if index!=two.s.ssindex: raise ValueError
			onestart=one.s
			twostart=one.n
			one.s0.patchtype=patchtype
			two.s0.patchtype=patchtype
			one.s0.next=two.n0
			two.s0.next=one.n0
			s1=Segments(onestart)
			s2=Segments(twostart)
			SegmentSet.setindex(twostart,len(self.list))
			self.list.append(s2)
			self.list[index]=s1
			i+=2
	def culllist(self):
		oldlist=self.list
		self.list=[]
		for seg in oldlist:
			if seg.hasposside(): self.list.append(seg)

class SpherePolygon():
	@staticmethod
	def make(polygon,rotation):
		pg=SpherePolygon(polygon,rotation)
		for x in polygon.points: pg.points.append(SpherePoint.makefromdll(x,rotation))
		return pg
	@staticmethod
	def makefromsegments(polygon,rotation,segments):
		pg=SpherePolygon(polygon,rotation)
		s=segments.first
		while True:
			pg.points.append(s)
			s=s.next
			if s==segments.first: break
		return pg
	@staticmethod
	def shouldsplit(p,q):
		dx=q.ux-p.ux
		dy=q.uy-p.uy
		if dx*dx+dy*dy<4: return False
		return True
	def __init__(self,polygon,rotation):
		self.polygon=polygon
		self.rotation=rotation
		self.points=[]
	def print(self):
		print('polygon: '+str(len(self.points))+' iscw:'+str(self.polygon.iscw))
	def isvertex(self,lon,lat):
		return self.polygon.isvertex(self,lon,lat)
	def flatten(self,width,height):
		r=FlatPolygon(self.polygon.iscw,self.polygon.index,self.polygon.partindex)
		for p in self.points:
			p.ux=int(0.5+((p.y+1.0)*(width-1))/2.0)
			p.uy=int(0.5+((1.0-p.z)*(height-1))/2.0)
		i=0
		fuse=1000
		while True:
			p=self.points[i]
			r.addpoint(p.ux,p.uy,p.patchtype)
			q=self.points[0]
			if i+1<len(self.points): q=self.points[i+1]
			if SpherePolygon.shouldsplit(p,q):
				fuse-=1
				if fuse==0: raise ValueError('Too many interpolations, fuse expired')
				n=SpherePoint()
				if p.patchtype==HORIZ_PATCHTYPE:
					n.y=(p.y+q.y)/2.0
					n.z=p.z
					n.x=math.sqrt(1-n.y*n.y-n.z*n.z)
				elif p.patchtype==VERT_PATCHTYPE:
					n.y=p.y
					n.z=(p.z+q.z)/2.0
					n.x=math.sqrt(1-n.y*n.y-n.z*n.z)
				else:
					x=(p.x+q.x)/2.0
					y=(p.y+q.y)/2.0
					z=(p.z+q.z)/2.0
					hh=x*x+y*y+z*z
					scale=math.sqrt(1/hh)
					n.x=x*scale
					n.y=y*scale
					n.z=z*scale
				n.patchtype=p.patchtype
				n.ux=int(0.5+((n.y+1.0)*(width-1))/2.0)
				n.uy=int(0.5+((1.0-n.z)*(height-1))/2.0)
				self.points.insert(i+1,n)
			i+=1
			if i==len(self.points): break
		return r
	def hemicleave(self):
		t=SphereIntersections.setsides(self.points)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points)
		intersections=SphereIntersections(segments)
		intersections.fix(self.polygon,self.rotation)
		ss=SegmentSet(segments)
		ss.split2(intersections,HEMI_PATCHTYPE)
		ss.culllist()
		ret=[]
		for s in ss.list: ret.append(SpherePolygon.makefromsegments(self.polygon,self.rotation,s))
		return ret
	def yzcleave(self,isz,ishigh,val):
		t=SphereIntersections2.setsides(self.points,isz,ishigh,val)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points)
		intersections=SphereIntersections2(isz,val,segments)
		intersections.sort(isz)
		ss=SegmentSet(segments)
		if isz: ss.split2(intersections,HORIZ_PATCHTYPE)
		else: ss.split2(intersections,VERT_PATCHTYPE)
		ss.culllist()
		ret=[]
		for s in ss.list: ret.append(SpherePolygon.makefromsegments(self.polygon,self.rotation,s))
		return ret

class MercatorPolygon():
	@staticmethod
	def make(polygon):
		pg=MercatorPolygon(polygon)
		for x in polygon.points: pg.points.append(MercatorPoint(x))
		return pg
	@staticmethod
	def makefromsegments(polygon,segments):
		pg=MercatorPolygon(polygon)
		s=segments.first
		while True:
			pg.points.append(s)
			s=s.next
			if s==segments.first: break
		return pg
	def __init__(self,polygon):
		self.polygon=polygon
		self.points=[]
	def print(self):
		print('polygon: '+str(len(self.points))+' iscw:'+str(self.polygon.iscw))
	def flatten(self,width,height):
		widthm1=width-1
		hheight=(height-1)/2.0
		r=FlatPolygon(self.polygon.iscw,self.polygon.index,self.polygon.partindex)
		for p in self.points:
			ux=int(0.5+((p.lon+180.0)/360.0)*widthm1)
			y=(p.lat*math.pi)/360.0 # /2
			uy=int(0.5+hheight-(hheight*math.log(math.tan(M_PI_4+y)))/math.pi)
			r.addpoint(ux,uy,p.patchtype)
		return r
	def ycleave(self,ishigh,val):
		t=MercatorIntersections.setsides(self.points,ishigh,val)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points,True)
		intersections=MercatorIntersections(val,segments)
		intersections.sort()
		ss=SegmentSet(segments)
		ss.split2(intersections,HORIZ_PATCHTYPE)
		ss.culllist()
		ret=[]
		for s in ss.list: ret.append(MercatorPolygon.makefromsegments(self.polygon,s))
		return ret

class TripelPolygon():
	@staticmethod
	def make(polygon):
		pg=TripelPolygon(polygon)
		for x in polygon.points: pg.points.append(TripelPoint(x))
		return pg
	@staticmethod
	def makefromsegments(polygon,segments):
		pg=TripelPolygon(polygon)
		s=segments.first
		while True:
			pg.points.append(s)
			s=s.next
			if s==segments.first: break
		return pg
	def __init__(self,polygon):
		self.polygon=polygon
		self.points=[]
	def print(self):
		print('polygon: '+str(len(self.points))+' iscw:'+str(self.polygon.iscw))
	def flatten(self,widthm1,heightm1):
		r=FlatPolyline()
		for p in self.points:
			(ux,uy)=tripel(p.lon,p.lat)
			ux=int(0.5+ux*widthm1)
			uy=int(0.5+heightm1-uy*heightm1)
			r.addpoint(ux,uy)
		return r

class SpherePolyline():
	@staticmethod
	def make(polyline,rotation):
		pl=SpherePolyline(rotation)
		for x in polyline.points: pl.points.append(SpherePoint.makefromdll(x,rotation))
		return pl
	@staticmethod
	def makefromsegments(rotation,segments):
		pl=SpherePolyline(rotation)
		s=segments.first
		while True:
			pl.points.append(s)
			s=s.next
			if s==segments.first: break
		return pl
	def __init__(self,rotation):
		self.rotation=rotation
		self.points=[]
	def print(self):
		print('polyline: '+str(len(self.points)))
	def flatten(self,width,height):
		r=FlatPolyline()
		for p in self.points:
			ux=int(0.5+((p.y+1.0)*(width-1))/2.0)
			uy=int(0.5+((1.0-p.z)*(height-1))/2.0)
			r.addpoint(ux,uy)
		return r
	def hemicleave(self):
		t=SphereIntersections.setsides(self.points)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points,True)
		intersections=SphereIntersections(segments,segments.last)
		ss=SegmentSet(segments)
		ss.split1(intersections)
		ss.culllist()
		ret=[]
		for s in ss.list: ret.append(SpherePolyline.makefromsegments(self.rotation,s))
		return ret

class MercatorPolyline():
	@staticmethod
	def make(polyline):
		pl=MercatorPolyline()
		for x in polyline.points: pl.points.append(MercatorPoint(x))
		return pl
	@staticmethod
	def makefromsegments(segments):
		pl=MercatorPolyline()
		s=segments.first
		while True:
			pl.points.append(s)
			s=s.next
			if s==segments.first: break
		return pl
	def __init__(self):
		self.points=[]
	def print(self):
		print('polyline: '+str(len(self.points)))
	def flatten(self,width,height):
		widthm1=width-1
		hheight=(height-1)/2.0
		r=FlatPolyline()
		for p in self.points:
			ux=int(0.5+((p.lon+180.0)/360.0)*widthm1)
			y=(p.lat*math.pi)/360.0 # /2
			uy=int(0.5+hheight-(hheight*math.log(math.tan(M_PI_4+y)))/math.pi)
			r.addpoint(ux,uy)
		return r
	def ycleave(self,ishigh,val):
		t=MercatorIntersections.setsides(self.points,ishigh,val)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points,True)
		intersections=MercatorIntersections(val,segments)
		ss=SegmentSet(segments)
		ss.split1(intersections)
		ss.culllist()
		ret=[]
		for s in ss.list: ret.append(MercatorPolyline.makefromsegments(s))
		return ret


class TripelPolyline():
	@staticmethod
	def make(polyline):
		pl=TripelPolyline()
		for x in polyline.points: pl.points.append(TripelPoint(x))
		return pl
	@staticmethod
	def makefromsegments(segments):
		pl=TripelPolyline()
		s=segments.first
		while True:
			pl.points.append(s)
			s=s.next
			if s==segments.first: break
		return pl
	def __init__(self):
		self.points=[]
	def print(self):
		print('polyline: '+str(len(self.points)))
	def flatten(self,widthm1,heightm1):
		r=FlatPolyline()
		for p in self.points:
			(ux,uy)=tripel(p.lon,p.lat)
			ux=int(0.5+ux*widthm1)
			uy=int(0.5+heightm1-uy*heightm1)
			r.addpoint(ux,uy)
		return r

class SphereShape():
	def __init__(self,shapeplus,rotation):
		self.type=shapeplus.type
		self.cssclass=shapeplus.cssclass
		self.shapeplus=shapeplus
		if self.type==POLYGON_TYPE_SHP:
			self.polygons=[]
			for x in shapeplus.polygons:
				self.polygons.append(SpherePolygon.make(x,rotation))
		elif self.type==POLYLINE_TYPE_SHP:
			self.polylines=[]
			for x in shapeplus.polylines:
				self.polylines.append(SpherePolyline.make(x,rotation))
		elif self.type==POINT_TYPE_SHP:
			self.point=SpherePoint.makefromdll(shapeplus.point,rotation)
		elif self.type!=NULL_TYPE_SHP:
			raise ValueError
	def print(self):
		for x in self.polygons: x.print()
	def flatten(self,width,height):
		r=FlatShape(self.cssclass)
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(width,height))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(width,height))
		return r
	def hemicleave(self):
		if self.type==POLYGON_TYPE_SHP:
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.hemicleave()
				for pg in r: self.polygons.append(pg) # it's important to maintain order
			if len(self.polygons)==0: self.type=NULL_TYPE_SHP
		elif self.type==POLYLINE_TYPE_SHP:
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.hemicleave()
				for pl in r: self.polylines.append(pl)
			if len(self.polylines)==0: self.type=NULL_TYPE_SHP
	def yzcleave(self,isz,ishigh,val):
		if self.type==POLYGON_TYPE_SHP:
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.yzcleave(isz,ishigh,val)
				for pg in r: self.polygons.append(pg) # it's important to maintain order
			if len(self.polygons)==0: self.type=NULL_TYPE_SHP
		elif self.type==POLYLINE_TYPE_SHP:
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.yzcleave(isz,ishigh,val)
				for pl in r: self.polylines.append(pl)
			if len(self.polylines)==0: self.type=NULL_TYPE_SHP
	def highycleave(self,val): return self.yzcleave(False,True,val)
	def lowycleave(self,val): return self.yzcleave(False,False,val)
	def highzcleave(self,val): return self.yzcleave(True,True,val)
	def lowzcleave(self,val): return self.yzcleave(True,False,val)

class WebMercatorShape():
	def __init__(self,shapeplus):
		self.type=shapeplus.type
		self.cssclass=shapeplus.cssclass
		self.shapeplus=shapeplus
		if self.type==POLYGON_TYPE_SHP:
			self.polygons=[]
			for x in shapeplus.polygons:
				self.polygons.append(MercatorPolygon.make(x))
		elif self.type==POLYLINE_TYPE_SHP:
			self.polylines=[]
			for x in shapeplus.polylines:
				self.polylines.append(MercatorPolyline.make(x))
		elif self.type==POINT_TYPE_SHP:
			self.point=MercatorPoint(shapeplus.point)
		elif self.type!=NULL_TYPE_SHP:
			raise ValueError
	def print(self):
		for x in self.polygons: x.print()
	def flatten(self,width,height):
		r=FlatShape(self.cssclass)
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(width,height))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(width,height))
		return r
	def eightyfivecleave(self):
		if self.type==POLYGON_TYPE_SHP:
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.ycleave(True,85.0)
				for pg in r: self.polygons.append(pg)
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.ycleave(False,-85.0)
				for pg in r: self.polygons.append(pg)
			if len(self.polygons)==0: self.type=NULL_TYPE_SHP
		elif self.type==POLYLINE_TYPE_SHP:
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.ycleave(True,85.0)
				for pg in r: self.polylines.append(pg)
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.ycleave(False,-85.0)
				for pg in r: self.polylines.append(pg)
			if len(self.polylines)==0: self.type=NULL_TYPE_SHP
	def insetcleave(self):
		if self.type==POLYGON_TYPE_SHP:
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.ycleave(True,83.0)
				for pg in r: self.polygons.append(pg)
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.ycleave(False,-60.0)
				for pg in r: self.polygons.append(pg)
			if len(self.polygons)==0: self.type=NULL_TYPE_SHP
		elif self.type==POLYLINE_TYPE_SHP:
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.ycleave(True,83.0)
				for pg in r: self.polylines.append(pg)
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.ycleave(False,-60.0)
				for pg in r: self.polylines.append(pg)
			if len(self.polylines)==0: self.type=NULL_TYPE_SHP

class TripelShape():
	def __init__(self,shapeplus):
		self.type=shapeplus.type
		self.cssclass=shapeplus.cssclass
		self.shapeplus=shapeplus
		if self.type==POLYGON_TYPE_SHP:
			self.polygons=[]
			for x in shapeplus.polygons:
				self.polygons.append(TripelPolygon.make(x))
		elif self.type==POLYLINE_TYPE_SHP:
			self.polylines=[]
			for x in shapeplus.polylines:
				self.polylines.append(TripelPolyline.make(x))
		elif self.type==POINT_TYPE_SHP:
			self.point=TripelPoint(shapeplus.point)
		elif self.type!=NULL_TYPE_SHP:
			raise ValueError
	def print(self):
		for x in self.polygons: x.print()
	def flatten(self,width,height):
		widthm1=(width-1)
		heightm1=(height-1)/1.64
		r=FlatShape(self.cssclass)
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(widthm1,heightm1))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(widthm1,heightm1))
		return r

def one_sphere_print_svg(output,shp,one,draworder,rotation,width,height,shift=None,boxzoom=None,islabels=False):
	if boxzoom!=None:
		width=width*boxzoom.factor
		height=height*boxzoom.factor
	needmore=False
	pluses=ShapePlus.make(one)
	if draworder==-1:
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			onesphere.hemicleave()
			if boxzoom!=None:
				onesphere.highycleave(boxzoom.right)
				onesphere.lowycleave(boxzoom.left)
				onesphere.highzcleave(boxzoom.top)
				onesphere.lowzcleave(boxzoom.bottom)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output)
	else:
		for i in range(len(pluses)):
			oneplus=pluses[i]
			if oneplus.draworder==draworder:
				onesphere=SphereShape(oneplus,rotation)
				onesphere.hemicleave()
				if boxzoom!=None:
					onesphere.highycleave(boxzoom.right)
					onesphere.lowycleave(boxzoom.left)
					onesphere.highzcleave(boxzoom.top)
					onesphere.lowzcleave(boxzoom.bottom)
				if onesphere.type!=NULL_TYPE_SHP:
					flatshape=onesphere.flatten(width,height)
					if shift!=None: flatshape.shift(shift)
					flatshape.printsvg(output)
					if islabels:
						if flatshape.type==POLYGON_TYPE_SHP:
							pg=flatshape.polygons[0]
							p=pg.points[0]
							print_partlabel_svg(output,p.ux,p.uy,str(pg.partindex),0,width,height,pg.partindex,one.partscount)
			elif oneplus.draworder>draworder:needmore=True
	return needmore

def all_sphere_print_svg(output,shp,rotation,width,height,shift=None,boxzoom=None):
	draworder=0
	while True:
		needmore=False
		for one in shp.shapes:
			nm=one_sphere_print_svg(output,shp,one,draworder,rotation,width,height,shift,boxzoom)
			if nm: needmore=True
		if not needmore: break
		draworder+=1

def one_webmercator_print_svg(output,shp,one,draworder,width,height,shift=None):
	needmore=False
	pluses=ShapePlus.make(one)
	for oneplus in pluses:
		if oneplus.draworder==draworder:
			onewm=WebMercatorShape(oneplus)
			onewm.eightyfivecleave()
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output)
		elif oneplus.draworder>draworder: needmore=True
	return needmore

def one_inset_webmercator_print_svg(output,shp,one,draworder,width,height,shift=None):
	needmore=False
	pluses=ShapePlus.make(one)
	for oneplus in pluses:
		if oneplus.draworder==draworder:
			onewm=WebMercatorShape(oneplus)
			onewm.insetcleave()
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output)
		elif oneplus.draworder>draworder: needmore=True
	return needmore

def mbr_webmercator(shp,index,partindex,width,height,shift=None):
	mbr=Mbr()
	one=shp.shapes[index]
	pluses=ShapePlus.make(one)
	for oneplus in pluses:
		if not oneplus.ispartindex(partindex): continue
		onewm=WebMercatorShape(oneplus)
		onewm.eightyfivecleave()
		if onewm.type!=NULL_TYPE_SHP:
			flatshape=onewm.flatten(width,height)
			if shift!=None: flatshape.shift(shift)
			flatshape.addtombr(mbr)
	return mbr

def one_inset_tripel_print_svg(output,shp,one,draworder,width,height,shift=None):
	needmore=False
	pluses=ShapePlus.make(one)
	for oneplus in pluses:
		if oneplus.draworder==draworder:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output)
		elif oneplus.draworder>draworder: needmore=True
	return needmore

def mbr_tripel(shp,index,partindex,width,height,shift=None,mbr=None):
	if mbr==None: mbr=Mbr()
	one=shp.shapes[index]
	pluses=ShapePlus.make(one)
	for oneplus in pluses:
		if not oneplus.ispartindex(partindex): continue
		onewt=TripelShape(oneplus)
		if onewt.type!=NULL_TYPE_SHP:
			flatshape=onewt.flatten(width,height)
			if shift!=None: flatshape.shift(shift)
			flatshape.addtombr(mbr)
	return mbr

def print_comment_svg(output,comment):
	output.print('<!-- ')
	a=comment.split('&')
	comment='&amp;'.join(a)
	a=comment.split('<')
	comment='&lt;'.join(a)
	a=comment.split('>')
	comment='&gt;'.join(a)
	output.print(comment)
	output.print(' -->')

def print_roundwater_svg(output,diameter):
	radius=diameter/2
	rs='%.1f' % (radius)
	output.print('<circle cx="%s" cy="%s" r="%s" fill="url(#watergradient)" />' % (rs,rs,rs))
def print_squarewater_svg(output,length,fill="#5685a2"):
	output.print('<rect x="0" y="0" width="%d" height="%d" fill="%s" />'%(length,length,fill))
def print_rectangle_svg(output,xoff,yoff,w,h,fill,opacity):
	output.print('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="%.1f" />'%(xoff,yoff,w,h,fill,opacity))

def print_header_svg(output,width,height,comments=None):
	output.print('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
	output.print('<svg xmlns:svg="http://www.w3.org/2000/svg" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="%d" width="%d">' % (height,width))
	output.print('<!-- made with pythonshp.py github.com/sanjayrao77 -->')
	if comments!=None:
		for comment in comments:
			print_comment_svg(output,comment)
	output.print('<defs>')
	output.print('	<radialGradient id="watergradient" cx="500" cy="500" r="500" fx="500" fy="500" gradientUnits="userSpaceOnUse">')
	output.print('		<stop offset="0%" stop-color="#70add3"/>')
	output.print('		<stop offset="8%" stop-color="#6fabd1"/>')
	output.print('		<stop offset="16%" stop-color="#6da9ce"/>')
	output.print('		<stop offset="23%" stop-color="#6ca7cc"/>')
	output.print('		<stop offset="31%" stop-color="#6ba5c9"/>')
	output.print('		<stop offset="38%" stop-color="#6aa3c7"/>')
	output.print('		<stop offset="45%" stop-color="#68a1c4"/>')
	output.print('		<stop offset="52%" stop-color="#679fc2"/>')
	output.print('		<stop offset="59%" stop-color="#669dbf"/>')
	output.print('		<stop offset="65%" stop-color="#649bbd"/>')
	output.print('		<stop offset="71%" stop-color="#6399bb"/>')
	output.print('		<stop offset="76%" stop-color="#6297b8"/>')
	output.print('		<stop offset="81%" stop-color="#6095b6"/>')
	output.print('		<stop offset="85%" stop-color="#5f93b3"/>')
	output.print('		<stop offset="89%" stop-color="#5e91b1"/>')
	output.print('		<stop offset="92%" stop-color="#5d8fae"/>')
	output.print('		<stop offset="95%" stop-color="#5b8dac"/>')
	output.print('		<stop offset="97%" stop-color="#5a8ba9"/>')
	output.print('		<stop offset="99%" stop-color="#5989a7"/>')
	output.print('		<stop offset="100%" stop-color="#5787a4"/>')
	output.print('		<stop offset="100%" stop-color="#5685a2"/>')
	output.print('	</radialGradient>')
	output.print('	<radialGradient id="landgradient" cx="500" cy="500" r="500" fx="500" fy="500" gradientUnits="userSpaceOnUse">')
	output.print('		<stop offset="0%" stop-color="#dddddd"/>')
	output.print('		<stop offset="8%" stop-color="#d9d9d9"/>')
	output.print('		<stop offset="16%" stop-color="#d5d5d5"/>')
	output.print('		<stop offset="23%" stop-color="#d0d0d0"/>')
	output.print('		<stop offset="31%" stop-color="#cccccc"/>')
	output.print('		<stop offset="38%" stop-color="#c8c8c8"/>')
	output.print('		<stop offset="45%" stop-color="#c4c4c4"/>')
	output.print('		<stop offset="52%" stop-color="#bfbfbf"/>')
	output.print('		<stop offset="59%" stop-color="#bbbbbb"/>')
	output.print('		<stop offset="65%" stop-color="#b7b7b7"/>')
	output.print('		<stop offset="71%" stop-color="#b3b3b3"/>')
	output.print('		<stop offset="76%" stop-color="#aeaeae"/>')
	output.print('		<stop offset="81%" stop-color="#aaaaaa"/>')
	output.print('		<stop offset="85%" stop-color="#a6a6a6"/>')
	output.print('		<stop offset="89%" stop-color="#a2a2a2"/>')
	output.print('		<stop offset="92%" stop-color="#9d9d9d"/>')
	output.print('		<stop offset="95%" stop-color="#999999"/>')
	output.print('		<stop offset="97%" stop-color="#959595"/>')
	output.print('		<stop offset="99%" stop-color="#919191"/>')
	output.print('		<stop offset="100%" stop-color="#8c8c8c"/>')
	output.print('		<stop offset="100%" stop-color="#888888"/>')
	output.print('	</radialGradient>')
	output.print('	<radialGradient id="bordergradient" cx="500" cy="500" r="500" fx="500" fy="500" gradientUnits="userSpaceOnUse">')
	output.print('		<stop offset="0%" stop-color="#444444"/>')
	output.print('		<stop offset="8%" stop-color="#414141"/>')
	output.print('		<stop offset="16%" stop-color="#3d3d3d"/>')
	output.print('		<stop offset="23%" stop-color="#3a3a3a"/>')
	output.print('		<stop offset="31%" stop-color="#363636"/>')
	output.print('		<stop offset="38%" stop-color="#333333"/>')
	output.print('		<stop offset="45%" stop-color="#303030"/>')
	output.print('		<stop offset="52%" stop-color="#2c2c2c"/>')
	output.print('		<stop offset="59%" stop-color="#292929"/>')
	output.print('		<stop offset="65%" stop-color="#252525"/>')
	output.print('		<stop offset="71%" stop-color="#222222"/>')
	output.print('		<stop offset="76%" stop-color="#1f1f1f"/>')
	output.print('		<stop offset="81%" stop-color="#1b1b1b"/>')
	output.print('		<stop offset="85%" stop-color="#181818"/>')
	output.print('		<stop offset="89%" stop-color="#141414"/>')
	output.print('		<stop offset="92%" stop-color="#111111"/>')
	output.print('		<stop offset="95%" stop-color="#0e0e0e"/>')
	output.print('		<stop offset="97%" stop-color="#0a0a0a"/>')
	output.print('		<stop offset="99%" stop-color="#070707"/>')
	output.print('		<stop offset="100%" stop-color="#030303"/>')
	output.print('		<stop offset="100%" stop-color="#000000"/>')
	output.print('	</radialGradient>')
	output.print('</defs>')
	output.print('<style type="text/css">')
	output.print('<![CDATA[')
	output.print('path.land { fill:url(#landgradient);stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.land_border { stroke:url(#bordergradient);fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.land_patch { stroke:#888888;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('path.subland { fill:#449944;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.subland_border { stroke:#338833;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.subland_patch { stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('circle.highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0 }')
	output.print('circle.w2_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:2 }')
	output.print('circle.w3_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:3 }')
	output.print('circle.w4_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:4 }')
	output.print('circle.w_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6 }')
	output.print('circle.w_w2_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:2 }')
	output.print('circle.w_w3_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:3 }')
	output.print('circle.w_w4_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:4 }')
	output.print('path.highlight_land { fill:#449944;stroke:#000000;fill-opacity:0.0;stroke-opacity:0.0 }')
	output.print('polyline.highlight_land_border { stroke:#115511;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.highlight_land_patch { stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('path.highlight2_land { fill:#449944;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.highlight2_land_border { stroke:#115511;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.highlight2_land_patch { stroke:#115511;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('path.water { fill:url(#watergradient);stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.water_border { stroke:url(#watergradient);fill-opacity:0.0;stroke-opacity:0.5;stroke-width:1.0 }')
	output.print('polyline.water_patch { stroke:url(#watergradient);fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.lonlat { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.2;stroke-width:1.0 }')
	output.print('polyline.land { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.8;stroke-width:0.5 }')
	output.print('path.landz { fill:#dddddd;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.landz_border { stroke:#444444;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.landz_patch { stroke-dasharray:"3 3";stroke:#000000;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('path.outline { fill:#eeeeee;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.outline_border { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.0;stroke-width:1.0 }')
	output.print('polyline.outline_patch { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.0;stroke-width:1.0 }')
	output.print('polyline.outline { stroke:#000000;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('path.landx { fill:#aaaaaa;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
	output.print('polyline.landx_border { stroke:#aaaaaa;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.landx_patch { stroke:#aaaaaa;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
	output.print('polyline.lonlat3 { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.2;stroke-width:1.0 }')
	output.print(']]>')
	output.print('</style>')
def print_footer_svg(output):
	output.print('</svg>')
def sphere_print_svg(output,shp,rotation,width,height,ids=None):
	output=Output()
	print_header_svg(output,width,height)
	if width==height: print_roundwater_svg(output,width)
	draworder=0
	while True:
		needmore=False
		if ids==None:
			for one in shp.shapes:
				nm=one_sphere_print_svg(output,shp,one,draworder,rotation,width,height)
				if nm: needmore=True
		else:
			for i in ids:
				one=shp.shapes[i]
				nm=one_sphere_print_svg(output,shp,one,draworder,rotation,width,height)
				if nm: needmore=True
		if not needmore: break
		draworder+=1
	print_footer_svg(output)
def webmercator_print_svg(output,shp,width,height,ids=None):
	output=Output()
	print_header_svg(output,width,height)
	if width==height: print_squarewater_svg(output,width)
	draworder=0
	while True:
		needmore=False
		if ids==None:
			for one in shp.shapes:
				nm=one_webmercator_print_svg(output,shp,one,draworder,width,height)
				if nm: needmore=True
		else:
			for i in ids:
				one=shp.shapes[i]
				nm=one_webmercator_print_svg(output,shp,one,draworder,width,height)
				if nm: needmore=True
		if not needmore: break
		draworder+=1
	print_footer_svg(output)

def print_box3d_svg(output,minx,miny,maxx,maxy,color,width,opacity):
	output.print('<polyline fill-opacity="0.0" stroke-opacity="%.1f" stroke-width="%.1f" stroke="%s" points="'%(opacity,width,color),end='')
	output.print('%u,%u %u,%u %u,%u %u,%u %u,%u'%(minx,miny,maxx,miny,maxx,maxy,minx,maxy,minx,miny),end='')
	output.print('" />')

	output.print('<polyline fill-opacity="0.0" stroke-opacity="0.6" stroke-width="1" stroke="#ffffff" points="',end='')
	output.print('%u,%u %u,%u %u,%u'%(minx-1,maxy,minx-1,miny-1,maxx,miny-1),end='')
	output.print('" />')

	output.print('<polyline fill-opacity="0.0" stroke-opacity="0.6" stroke-width="1" stroke="#000000" points="',end='')
	output.print('%u,%u %u,%u %u,%u'%(minx,maxy+1,maxx+1,maxy+1,maxx+1,miny),end='')
	output.print('" />')

def print_box_svg(output,minx,miny,maxx,maxy,color,width,opacity):
	output.print('<rect x="%d" y="%d" width="%d" height="%d" fill-opacity="0" stroke="%s" stroke-opacity="%.1f" stroke-width="%.1f" />'
			%(minx,miny,maxx-minx+1,maxy-miny+1,color,opacity,width))

def print_boxw_svg(output,minx,miny,maxx,maxy,color,width,opacity):
	print_box_svg(output,minx-1,miny-1,maxx+1,maxy+1,'#ffffff',width,0.5)
	print_box_svg(output,minx+1,miny+1,maxx-1,maxy-1,'#ffffff',width,0.5)
	print_box_svg(output,minx,miny,maxx,maxy,color,width,opacity)

def print_line_svg(output,x1,y1,x2,y2,color,width,opacity):
	output.print('<polyline fill-opacity="0.0" stroke-opacity="%.1f" stroke-width="%.1f" stroke="%s" points="'%(opacity,width,color),end='')
	output.print('%u,%u %u,%u'%(x1,y1,x2,y2),end='')
	output.print('" />')

def lonlat_print_svg(output,rotation,width,height):
	lats=[-60.0,-30.0,0.0,30.0,60.0]
	lons=[-180.0,-150.0,-120.0,-90.0,-60.0,-30.0,0.0,30.0,60.0,90.0,120.0,150.0]
	for deg in lats:
		one=ShapePolyline.makelat(0,0,deg,'lonlat')
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			onesphere.hemicleave()
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height)
				flatshape.printsvg(output)
	for deg in lons:
		one=ShapePolyline.makelon(0,0,deg,'lonlat')
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			onesphere.hemicleave()
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height)
				flatshape.printsvg(output)

def tripel_lonlat_print_svg(output,width,height,shift):
	lats=[-60.0,-30.0,0.0,30.0,60.0]
	lons=[-150.0,-120.0,-90.0,-60.0,-30.0,0.0,30.0,60.0,90.0,120.0,150.0]
	for deg in lats:
		one=ShapePolyline.makelat(0,0,deg,'lonlat3')
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				flatshape.shift(shift)
				flatshape.printsvg(output)
	for deg in lons:
		one=ShapePolyline.makelon(0,0,deg,'lonlat3')
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				flatshape.shift(shift)
				flatshape.printsvg(output)

def print_partlabel_svg(output,xoff,yoff,text,textangle,width,height,partindex,partscount):
	if ispartlabeltop_global:
		step=width/(partscount+1)
		xoff2=int(step*partindex+step/2)
		yoff2=10+15*(partindex%5)
	else:
		step=width/(partscount+1)
		xoff2=int(step*partindex+step/2)
		yoff2=height-300+15*(partindex%5)
	colors=['#ff0000','#00ff00','#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffff77', '#ff77ff', '#77ffff',
			'#777700', '#770077', '#007777' ]
	color=colors[partindex%12]
	output.print('<polyline fill-opacity="0" stroke-opacity="1" stroke="%s" points="%d,%d %d,%d"/>'%(color,xoff2,yoff2,xoff,yoff))
	if True: # white outline
		output.print('<text x="0" y="0" style="font:10px sans;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1.0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(xoff2,yoff2,textangle,text))
	output.print('<text x="0" y="0" style="font:10px sans;fill:%s;fill-opacity:1;stroke-opacity:0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(color,xoff2,yoff2,textangle,text))

def print_label_svg(output,lon,lat,xoff,yoff,text,textangle,width,height,rotation):
	dll=DegLonLat(lon,lat)
	sp=SpherePoint.makefromdll(dll,rotation)
	if sp.x<0.0: return
	fp=sp.flatten(width,height)
	if True: # clipping
		if fp.ux-4<0: return
		if fp.ux+20>width: return
		norot=SphereRotation()
		csp=SpherePoint.makefromdll(DegLonLat(90.0,lat),norot)
		cfp=csp.flatten(width,height)
		if fp.ux+20>cfp.ux: 
			if isverbose_global:
				print('Clipping label (1) fp.ux:%d cfp.ux:%d %s  '%(fp.ux,cfp.ux,text),file=sys.stderr,end='')
				csp.print()
			return
		csp=SpherePoint.makefromdll(DegLonLat(-90.0,lat),norot)
		cfp=csp.flatten(width,height)
		if fp.ux-5<cfp.ux:
			if isverbose_global:
				print('Clipping label (2) fp.ux:%d cfp.ux:%d %s  '%(fp.ux,cfp.ux,text),file=sys.stderr,end='')
				csp.print()
			return
		
	if False: # white shadow
		if textangle<45:
			output.print('<text x="0" y="0" style="font:14px sans;fill:#ffffff;fill-opacity:1;stroke-opacity:0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp.ux+xoff+1,fp.uy+yoff+1,textangle,text))
		else:
			output.print('<text x="0" y="0" style="font:14px sans;fill:#ffffff;fill-opacity:1;stroke-opacity:0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp.ux+xoff-1,fp.uy+yoff+1,textangle,text))
	if True: # white outline
		output.print('<text x="0" y="0" style="font:14px sans;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:0.9;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp.ux+xoff,fp.uy+yoff,textangle,text))
	output.print('<text x="0" y="0" style="font:14px sans;fill:#000000;fill-opacity:1;stroke-opacity:0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp.ux+xoff,fp.uy+yoff,textangle,text))

class FlatCircle():
	@staticmethod
	def byweight(o): return o.weight

	def __init__(self,x,y,r,name):
		self.x=x
		self.y=y
		self.r=r
		self.weight=r
		self.isactive=True
		self.name=name

def findcircle_part_shape(shape,partindex,rotation,width_in,height_in,zoomshift=None,boxzoom=None):
	width=width_in
	height=height_in
	if boxzoom!=None:
		width=width*boxzoom.factor
		height=height*boxzoom.factor
	pointcount=0
	xsum=0
	ysum=0
	xmin=width
	xmax=0
	ymin=height
	ymax=0
	pluses=ShapePlus.make(shape)
	for oneplus in pluses:
		if not oneplus.ispartindex(partindex): continue
		onesphere=SphereShape(oneplus,rotation)
		onesphere.hemicleave()
		if onesphere.type==NULL_TYPE_SHP: continue
		flatshape=onesphere.flatten(width,height)
		if flatshape.type==POLYGON_TYPE_SHP:
			for pg in flatshape.polygons:
				for p in pg.points:
					if p.ux<xmin: xmin=p.ux
					if p.ux>xmax: xmax=p.ux
					if p.uy<ymin: ymin=p.uy
					if p.uy>ymax: ymax=p.uy
#					print('%d,%d '%(p.ux,p.uy),end='',file=sys.stderr)
					xsum+=p.ux
					ysum+=p.uy
					pointcount+=1
	if pointcount==0: return None
	ax=xsum/pointcount
	ay=ysum/pointcount
	r=0
	x1=xmax-ax
	x2=ax-xmin
	y1=ymax-ay
	y2=ay-ymin

	r2=x1*x1+y1*y1
	if r2>r: r=r2
	r2=x2*x2+y1*y1
	if r2>r: r=r2
	r2=x1*x1+y2*y2
	if r2>r: r=r2
	r2=x2*x2+y2*y2
	if r2>r: r=r2

	if zoomshift!=None:
		ax+=zoomshift.xoff
		ay+=zoomshift.yoff

	ax=int(0.5+ax)
	ay=int(0.5+ay)
	r=int(0.5+math.sqrt(r2))
	return FlatCircle(ax,ay,r,partindex)

def trimcircles(circles,sds):
	for p in circles:
		w=0
		rplus=p.r+sds
		for q in circles:
			d=FlatPoint.distance(p.x,p.y,q.x,q.y)
			if d<rplus: w+=q.r
		p.weight=w
	circles.sort(key=FlatCircle.byweight,reverse=True)
	k=len(circles)
	for i in range(1,k):
		p=circles[i]
		for j in range(i):
			q=circles[j]
			if not q.isactive: continue
			d=FlatPoint.distance(p.x,p.y,q.x,q.y)
			if d<q.r+sds:
				p.isactive=False
				break

def print_zoomdots_svg(output,shape,zoomdots,sds,cssclass,rotation,width,height,zoomshift,boxzoom):
	circles=[]
	for dot in zoomdots:
		fc=findcircle_part_shape(shape,dot,rotation,width,height,zoomshift,boxzoom)
		if fc==None: continue
		circles.append(fc)
	trimcircles(circles,sds)
	for p in circles:
		if not p.isactive:
			if isverbose_global: print('Skipping zoomdot %d'%(p.name),file=sys.stderr)
			continue
		radius=p.r
		radius+=sds
		output.print('<circle class="w_%s" cx="%d" cy="%d" r="%d" />'%(cssclass,p.x,p.y,radius+1))
		if radius>10:
			output.print('<circle class="w_%s" cx="%d" cy="%d" r="%d" />'%(cssclass,p.x,p.y,radius-1))
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d" />'%(cssclass,p.x,p.y,radius))

def print_centerdot_svg(output,lon,lat,radius,cssclass,rotation,width,height):
	sp=SpherePoint.makefromdll(DegLonLat(lon,lat),rotation)
	fp=sp.flatten(width,height)
	output.print('<circle class="w_%s" cx="%d" cy="%d" r="%d" />'%(cssclass,fp.ux,fp.uy,radius+1))
	if radius>10:
		output.print('<circle class="w_%s" cx="%d" cy="%d" r="%d" />'%(cssclass,fp.ux,fp.uy,radius-1))
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d" />'%(cssclass,fp.ux,fp.uy,radius))

def print_smalldots_svg(output,shape,smalldots,sds,cssclass,rotation,width,height):
	circles=[]
	for dot in smalldots:
		fc=findcircle_part_shape(shape,dot,rotation,width,height)
		if fc==None: continue
		circles.append(fc)
	trimcircles(circles,sds)
	for p in circles:
		if not p.isactive:
			if isverbose_global: print('Skipping smalldot %d'%(p.name),file=sys.stderr)
			continue
		radius=p.r
		radius+=sds
		output.print('<circle class="w_%s" cx="%d" cy="%d" r="%d" />'%(cssclass,p.x,p.y,radius+1))
		if radius>10:
			output.print('<circle class="w_%s" cx="%d" cy="%d" r="%d" />'%(cssclass,p.x,p.y,radius-1))
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d" />'%(cssclass,p.x,p.y,radius))
	
def combo_print_svg(output,install,options,admin0):
	width=options['width']
	height=options['height']
	index=options['index']
	partindices=options['partindices']
	if True:
		if index!=-1:
			for partindex in partindices:
				admin0.setcssclass(index,partindex,'highlight2_land',1)

	if isverbose_global:
		debug=admin0.shapes[index]
		debug.print('Highlight shape ')

	rotation=SphereRotation()
	if True:
		lon=options['lon']
		lat=options['lat']
		hlc=lat/2
		if hlc<-23.436: hlc=-23.436
		elif hlc>23.436: hlc=23.436
		rotation.set_deglonlat(lon,hlc)
	rotation2=SphereRotation()
	rotation2.set_deglonlat(options['lon'],options['lat'])

	if False: # debug
		one=admin0.shapes[172]
		one_sphere_print_svg(output,admin0,one,0,rotation,width,height) # debug split2 bug

	print_header_svg(output,width,height,[options['copyright'],options['comment']])

	if 'bgcolor' in options:
		print_rectangle_svg(output,0,0,width,height,options['bgcolor'],1.0)

	if options['isroundwater']:
		if width==height: print_roundwater_svg(output,width)
	if isverbose_global: print('Drawing admin0 sphere shapes',file=sys.stderr)
	if options['isfix172']: admin0.shapes[172].setflag()
	for one in admin0.shapes:
		one_sphere_print_svg(output,admin0,one,0,rotation,width,height) # draw all but highlight

	if options['issubland']: # provinces/states on sphere
		if isverbose_global: print('Loading admin1 data',file=sys.stderr)
		admin1=Shp(install.getfilename('admin1.shp'),"subland")
		admin1.loadshapes()
		admin1dbf=Dbf(install.getfilename('admin1.dbf'))
		admin1dbf.selectcfield('sov_a3','sov3')
		admin1dbf.selectcfield('adm0_a3','adm3')
		admin1dbf.loadrecords()
		for one in admin0.shapes: # underdraw in case admin1 isn't complete cover
			draworder=1
			while True:
				nm=one_sphere_print_svg(output,admin0,one,draworder,rotation,width,height)
				if not nm: break
				draworder+=1
		if isverbose_global: print('Drawing admin1 sphere shapes',file=sys.stderr)
		foundcount=0
		for i in range(len(admin1dbf.records)):
			r=admin1dbf.records[i]
			if r['sov3']==options['grp'] and r['adm3']==options['subgrp']:
				foundcount+=1
				one=admin1.shapes[i]
				one_sphere_print_svg(output,admin1,one,-1,rotation,width,height)
		if isverbose_global:
			if foundcount==0:
				print('No admin1 regions found, you should set options.issubland=False',file=sys.stderr)
				raise ValueError
			else: print('Admin1 regions found: %d'%foundcount,file=sys.stderr)
		for partindex in partindices:
			admin0.setcssclass(index,partindex,'highlight_land',1) # only draws border

	for one in admin0.shapes: # highlights, maybe only border
		draworder=1
		while True:
			nm=one_sphere_print_svg(output,admin0,one,draworder,rotation,width,height,islabels=options['ispartlabels'])
			if not nm: break
			draworder+=1

	if options['isfix172']: admin0.shapes[172].setflag(False)

	if options['islakes']:
		if isverbose_global: print('Loading lakes shapes',file=sys.stderr)
		lakes=Shp(install.getfilename('lakes.shp'),"water")
		lakes.loadshapes()
		if isverbose_global: print('Drawing lakes sphere shapes',file=sys.stderr)
		for one in lakes.shapes:
			one_sphere_print_svg(output,lakes,one,-1,rotation,width,height)

	if 'moredots' in options: # [ (r0,isw0,[partindex00,partindex01]), ... , (rn,iswn,[partindexn0..partindexnm]) ]
		for moredots in options['moredots']:
			shape=admin0.shapes[index]
			sds=moredots[0]
			isw=moredots[1]
			smalldots=moredots[2]
			cssclass='highlight_land'
			if isinstance(isw,bool):
				if isw: cssclass='w4_highlight_land'
			elif isw==2: cssclass='w2_highlight_land'
			elif isw==3: cssclass='w3_highlight_land'
			elif isw==4: cssclass='w4_highlight_land'
			print_smalldots_svg(output,shape,smalldots,sds,cssclass,rotation,width,height)
	if 'centerdot' in options: # (r0,isw0)
		r=options['centerdot'][0]
		cssclass='highlight_land'
		isw=options['centerdot'][1]
		cssclass='highlight_land'
		if isinstance(isw,bool):
			if isw: cssclass='w4_highlight_land'
		elif isw==2: cssclass='w2_highlight_land'
		elif isw==3: cssclass='w3_highlight_land'
		elif isw==4: cssclass='w4_highlight_land'
		print_centerdot_svg(output,options['lon'],options['lat'],r,cssclass,rotation,width,height)

	if True:
		if isverbose_global: print('Drawing lon/lat shapes',file=sys.stderr)
		lonlat_print_svg(output,rotation,width,height)

		(lon_rotation_center,lat_rotation_center)=rotation.deg_getcenter()
		lonlabels=[ (-150,'150°W'), (-120,'120°W'), (-90,'90°W'), (-60,'60°W'), (-30,'30°W'),
				(0,'0°E'), (30,'30°E'), (60,'60°E'), (90,'90°E'), (120,'120°E'), (150,'150°E'), (180,'180°E')]
		if lon_rotation_center<0:
			lonlabels=[ (-150,'150°W'), (-120,'120°W'), (-90,'90°W'), (-60,'60°W'), (-30,'30°W'),
					(0,'0°W'), (30,'30°E'), (60,'60°E'), (90,'90°E'), (120,'120°E'), (150,'150°E'), (180,'180°W')]

		for label in lonlabels:
			labely=options['lonlabel_lat']
			print_lon_label_svg(output,labely,labely+5,label[0],label[1],width,height,rotation)

		if options['isinsetleft']:
			labelx=lon_rotation_center-30
			labelx=int(labelx/30)*30+20
		else:
			labelx=lon_rotation_center+30
			labelx=int(labelx/30)*30-20
		labelx=options['latlabel_lon']
		for label in [ (-60,'60°S'), (-30,'30°S'), (0,'0°N'), (30,'30°N'), (60,'60°N')]:
			print_lat_label_svg(output,labelx,labelx+5,label[0]+0.5,label[1],width,height,rotation)

	if True: # Tripel inset
		if isverbose_global: print('Drawing Tripel inset',file=sys.stderr)
		index=options['index']
		admin0.resetcssclass("landx")
		if index!=-1:
			for partindex in partindices:
				admin0.setcssclass(index,partindex,"highlight2_land",1)
		insetwidth=int(width*0.4)
		insetheight=insetwidth
			
		if True:
			insetshift=Shift(options['xoff_inset'],options['yoff_inset'])
			oneplus=ShapePlus.makeflatbox(True,'outline')
			onewt=TripelShape(oneplus)
			flatshape=onewt.flatten(insetwidth,insetheight)
			flatshape.shift(insetshift)
			flatshape.printsvg(output)
#		print_rectangle_svg(output,int(insetshift.xoff),int(insetshift.yoff+insetheight*0.025),insetwidth,int(insetheight*0.7),'#000000',0.3)

		draworder=0
		while True:
			needmore=False
			for one in admin0.shapes:
				nm=one_inset_tripel_print_svg(output,admin0,one,draworder,insetwidth,insetheight,insetshift)
				if nm: needmore=True
			if not needmore: break
			draworder+=1

		coast=Shp(install.getfilename('coast.shp'),"land")
		coast.loadshapes()
		for one in coast.shapes:
			one_inset_tripel_print_svg(output,coast,one,0,insetwidth,insetheight,insetshift)

		tripel_lonlat_print_svg(output,insetwidth,insetheight,insetshift)

		if True:
			oneplus=ShapePlus.makeflatbox(False,'outline')
			onewt=TripelShape(oneplus)
			flatshape=onewt.flatten(insetwidth,insetheight)
			flatshape.shift(insetshift)
			flatshape.printsvg(output)

		for indices in options['tripelboxes']:
			mbr=Mbr()
			for partindex in indices:
				mbr_tripel(admin0,index,partindex,insetwidth,insetheight,insetshift,mbr)
			if mbr.isset:
				print_boxw_svg(output,mbr.minx-10,mbr.miny-10,mbr.maxx+10,mbr.maxy+10,'#449944',5,0.9)

	if options['iszoom']:
		if isverbose_global: print('Drawing zoom inset',file=sys.stderr)
		margin=0
		cutmargin=6
		coeff=0.4
		if options['iszoom34']: coeff=0.3
		zwidth=int(coeff*width)
		zheight=int(coeff*height)
		xoff=width-zwidth
		xoff2=width-int(zwidth/2)
		if options['istopinsets']:
			yoff=0
			yoff2=int(zheight/2)
			xmargin=0
			ymargin=0
			print_rectangle_svg(output,xoff-cutmargin-3,0,zwidth+cutmargin+3,zheight+cutmargin+3,'#ffffff',1.0)
			print_rectangle_svg(output,xoff-cutmargin,3,zwidth+2,zheight+2,'#000000',1.0)
			print_rectangle_svg(output,xoff-margin,margin,zwidth,zheight,'#70add3',1.0)
		else:
			yoff=height-zheight
			yoff2=height-int(zheight/2)
			xmargin=0
			ymargin=0
			print_rectangle_svg(output,xoff-cutmargin-3,yoff-cutmargin-3,zwidth+cutmargin+3,zheight+cutmargin+3,'#ffffff',1.0)
			print_rectangle_svg(output,xoff-cutmargin,yoff-cutmargin,zwidth+2,zheight+2,'#000000',1.0)
			print_rectangle_svg(output,xoff-margin,yoff-margin,zwidth,zheight,'#70add3',1.0)

		scale=options['zoomscale']
		boff=-int(scale*width/2)
		boxd=coeff/scale
		boxzoom=BoxZoom(scale,-boxd,boxd,-boxd,boxd)
		zoomshift=Shift(xoff2+boff-xmargin,yoff2+boff-ymargin)
		admin0.resetcssclass("landz")
		if index!=-1:
			for partindex in partindices:
				admin0.setcssclass(index,partindex,'highlight2_land',1)
		if options['isfix172']: admin0.shapes[172].setflag()
		for one in admin0.shapes:
			one_sphere_print_svg(output,admin0,one,0,rotation2,width,height,zoomshift,boxzoom) # draw all but highlight
		if options['issubland']:
			if 'grp' in options:
				for one in admin0.shapes: # underdraw in case admin1 has gaps
					draworder=1
					while True:
						nm=one_sphere_print_svg(output,admin0,one,draworder,rotation2,width,height,zoomshift,boxzoom)
						if not nm: break
						draworder+=1
				for i in range(len(admin1dbf.records)):
					r=admin1dbf.records[i]
					if r['sov3']==options['grp'] and r['adm3']==options['subgrp']:
						one=admin1.shapes[i]
						one_sphere_print_svg(output,admin1,one,-1,rotation2,width,height,zoomshift,boxzoom)
				for partindex in partindices:
					admin0.setcssclass(index,partindex,'highlight_land',1)
		for one in admin0.shapes: # highlights, maybe only border
			draworder=1
			while True:
				nm=one_sphere_print_svg(output,admin0,one,draworder,rotation2,width,height,zoomshift,boxzoom)
				if not nm: break
				draworder+=1
		if options['isfix172']: admin0.shapes[172].setflag(False)
		if options['islakes']:
			for one in lakes.shapes:
				one_sphere_print_svg(output,lakes,one,-1,rotation2,width,height,zoomshift,boxzoom)
		if 'zoomdots' in options: # [ (r0,isw0,[partindex00,partindex01]), ... , (rn,iswn,[partindexn0..partindexnm]) ]
			for zoomdots in options['zoomdots']:
				shape=admin0.shapes[index]
				sds=zoomdots[0]
				isw=zoomdots[1]
				dots=zoomdots[2]
				cssclass='highlight_land'
				if isinstance(isw,bool):
					if isw: cssclass='w4_highlight_land'
				elif isw==2: cssclass='w2_highlight_land'
				elif isw==3: cssclass='w3_highlight_land'
				elif isw==4: cssclass='w4_highlight_land'
				print_zoomdots_svg(output,shape,dots,sds,cssclass,rotation2,width,height,zoomshift,boxzoom)

	print_footer_svg(output)


class FieldDbf():
	def __init__(self,buff32,offset):
		for i in range(12):
			if buff32[i]==0: break
		self.name=buff32[0:i].decode() # utf8 is fine
		self.type=buff32[11]
		self.length=buff32[16]
		self.offset=offset

class Dbf():
	def __init__(self,filename):
		self.filename=filename
		self.f=open(self.filename,"rb")
		self._loadheader()
	def close(self):
		self.f.close()
	def print(self):
		print('byte0: %d'%(self.byte0))
		print('mtime: %d/%d/%d'%(self.y_mtime,self.m_mtime,self.d_mtime))
		print('numrecords: %d'%(self.numrecords))
		print('headersize: %d'%(self.headersize))
		print('recordsize: %d'%(self.recordsize))
		print('fieldcount: %d'%(self.fieldcount))
		for f in self.fields:
			print('%s %c %d, offset:%d'%(f.name,f.type,f.length,f.offset))
	def findfield(self,fieldname):
		for f in self.fields:
			if f.name==fieldname: return f
		print('Couldn\'t find field %s'%(fieldname))
		return None
	def selectcfield(self,fieldname,nickname):
		f=self.findfield(fieldname)
		if f==None: raise ValueError
		if f.type!=67: raise ValueError # C:67
		self.selectedcfields[nickname]=f
	def loadrecords(self):
		self.f.seek(self.headersize)
		for rn in range(self.numrecords):
			recorddata=self.f.read(self.recordsize)
			onerecord={}
			onerecord['isdeleted']=(recorddata[0]==42)
			for sf in self.selectedcfields:
				f=self.selectedcfields[sf]
				onerecord[sf]=recorddata[f.offset:f.offset+f.length].decode()
			self.records.append(onerecord)
	def _loadheader(self):
		buff32=self.f.read(32)
		self.byte0=buff32[0]
		self.y_mtime=buff32[1]+1900
		self.m_mtime=buff32[2]
		self.d_mtime=buff32[3]
		self.numrecords=uint32_little(buff32,4)
		self.headersize=uint16_little(buff32,8)
		self.recordsize=uint16_little(buff32,10)
		self.fieldcount=int((self.headersize-1)/32 -1)
		self.fields=[]
		self.selectedcfields={}
		self.records=[]
		fieldsoffset=1
		for i in range(self.fieldcount):
			buff32=self.f.read(32)
			f=FieldDbf(buff32,fieldsoffset)
			self.fields.append(f)
			fieldsoffset+=f.length
		buff32=self.f.read(1)
		if buff32[0]!=0x0d: raise ValueError

class Install():
	@staticmethod
	def findfile(nickname,names):
		dirs=['./','ned/','ned/10m-admin/','ned/50m-admin/','ned/10m-coast/','ned/50m-coast/','ned/10m-lakes/','ned/50m-lakes/']
		for d in dirs:
			for n in names:
				fn=d+n
				if os.path.isfile(fn):
					if (isverbose_global): print('Found file %s -> %s'%(nickname,fn),file=sys.stderr)
					return fn
		print('Couldn\'t find file: %s. We looked in the following places:'%(nickname),file=sys.stderr)
		for d in dirs:
			for n in names:
				fn=d+n
				print('Checked for %s (not found)'%(fn),file=sys.stderr)
		raise ValueError
	def __init__(self):
		self.filenames={}
		self.filenames['admin0.shp']=Install.findfile('Admin0 shp file',['admin0.shp',
				'ne_10m_admin_0_countries_lakes.shp',
				'ne_10m_admin_0_countries.shp',
				'ne_50m_admin_0_countries_lakes.shp',
				'ne_50m_admin_0_countries.shp'])
		self.filenames['admin0.dbf']=Install.findfile('Admin0 dbf file',['admin0.dbf',
				'ne_10m_admin_0_countries_lakes.dbf',
				'ne_10m_admin_0_countries.dbf',
				'ne_50m_admin_0_countries_lakes.dbf',
				'ne_50m_admin_0_countries.dbf'])
		self.filenames['admin1.shp']=Install.findfile('Admin1 shp file',['admin1.shp',
				'ne_10m_admin_1_countries_lakes.shp',
				'ne_10m_admin_1_countries.shp',
				'ne_50m_admin_1_countries_lakes.shp',
				'ne_50m_admin_1_countries.shp'])
		self.filenames['admin1.dbf']=Install.findfile('Admin1 dbf file',['admin1.dbf',
				'ne_10m_admin_1_countries_lakes.dbf',
				'ne_10m_admin_1_countries.dbf',
				'ne_50m_admin_1_countries_lakes.dbf',
				'ne_50m_admin_1_countries.dbf'])
		self.filenames['lakes.shp']=Install.findfile('Lakes shp file',['lakes.shp',
				'ne_10m_lakes.shp',
				'ne_50m_lakes.shp'])
		self.filenames['coast.shp']=Install.findfile('Coast shp file',['coast.shp',
				'ne_10m_coastline.shp',
				'ne_50m_coastline.shp'])
	def getfilename(self,tag):
		if tag in self.filenames: return self.filenames[tag]
		print('Request for unloaded file: %s'%(tag),file=sys.stderr)
		for fn in self.filenames:
			print('\tLoaded file: %s'%(fn),file=sys.stderr)
		raise ValueError


# isverbose_global=True
install=Install()

if False: # admin0 test
	admin0dbf=Dbf(install.getfilename('admin0.dbf'))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.loadrecords()
	a0r=admin0dbf.records[53]

if False: # admin1 test
	admin1dbf=Dbf(install.getfilename('admin1.dbf'))
	admin1dbf.selectcfield('sov_a3','sov3')
	admin1dbf.selectcfield('adm0_a3','adm3')
	admin1dbf.loadrecords()
	for i in range(len(admin1dbf.records)):
		r=admin1dbf.records[i]
		print("%d: %s %s"%(i,r['sov3'],r['adm3']))


if False: # webmercator test
	output=Output()
	admin0=Shp(install.getfilename('admin0.shp'),"landx")
	admin0.loadshapes()
	coast=Shp(install.getfilename('coast.shp'),"land")
	coast.loadshapes()
	width=1000
	height=1000
	print_header_svg(output,width,height)
	for shape in admin0.shapes:
		pluses=ShapePlus.make(shape)
		for oneplus in pluses:
			onewm=WebMercatorShape(oneplus)
			onewm.insetcleave()
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				flatshape.printsvg(output)
	for shape in coast.shapes:
		pluses=ShapePlus.make(shape)
		for oneplus in pluses:
			onewm=WebMercatorShape(oneplus)
			onewm.insetcleave()
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				flatshape.printsvg(output)
	print_footer_svg(output)

if False: # Winkel Tripel test
	output=Output()
	width=1000
	height=1000
	print_header_svg(output,width,height)
	print_rectangle_svg(output,0,0,width,height,'#ffffff',1.0)
	insetshift=Shift(50,50)
	insetwidth=800
	insetheight=800
	oneplus=ShapePlus.makeflatbox('outline')
	onewt=TripelShape(oneplus)
	flatshape=onewt.flatten(insetwidth,insetheight)
	flatshape.shift(insetshift)
	flatshape.printsvg(output)
	if False:
		coast=Shp(install.getfilename('coast.shp'),"land")
		coast.loadshapes()
		for shape in coast.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewt=TripelShape(oneplus)
				if onewt.type!=NULL_TYPE_SHP:
					flatshape=onewt.flatten(insetwidth,insetheight)
					flatshape.shift(insetshift)
					flatshape.printsvg(output)
	print_footer_svg(output)

if False: # zoom test
	output=Output()
	admin0=Shp(install.getfilename('admin0.shp'),"landz")
	admin0.loadshapes()
	width=1000
	height=1000
	index=68
	partindex=-1
	boxzoom=BoxZoom(2,-0.2,0.2,-0.2,0.2)
	(lon,lat)=admin0.getcenter(index,[0])
	sr=SphereRotation()
	sr.set_deglonlat(lon,lat)
	print_header_svg(output,width,height)
	print_rectangle_svg(output,0,0,width,height,'#ffffff',1.0)
	for one in admin0.shapes:
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,sr)
			onesphere.hemicleave()
			onesphere.highycleave(boxzoom.right)
			onesphere.lowycleave(boxzoom.left)
			onesphere.highzcleave(boxzoom.top)
			onesphere.lowzcleave(boxzoom.bottom)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height)
				flatshape.printsvg(output)
	print_footer_svg(output)

if False: # province test
	output=Output()
	width=1000
	height=1000
	admin0=Shp(install.getfilename('admin0.shp'),"land")
	admin0.loadshapes()
	admin1=Shp(install.getfilename('admin1.shp'),"subland")
	admin1.loadshapes()
	admin1dbf=Dbf(install.getfilename('admin1.dbf'))
	admin1dbf.selectcfield('sov_a3','sov3')
	admin1dbf.selectcfield('adm0_a3','adm3')
	admin1dbf.loadrecords()
	print_header_svg(output,width,height)
	for shape in admin0.shapes:
		pluses=ShapePlus.make(shape)
		for oneplus in pluses:
			onewm=WebMercatorShape(oneplus)
			onewm.eightyfivecleave()
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				flatshape.printsvg(output)
	for i in range(len(admin1dbf.records)):
		r=admin1dbf.records[i]
		if r['sov3']=='MEX' and r['adm3']=='MEX':
			shape=admin1.shapes[i]
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewm=WebMercatorShape(oneplus)
				onewm.eightyfivecleave()
				if onewm.type!=NULL_TYPE_SHP:
					flatshape=onewm.flatten(width,height)
					flatshape.printsvg(output)
	print_footer_svg(output)

if False: # zoom in bottom-right
	output=Output()
	width=1000
	height=1000
	index=68
	partindex=-1
	admin0=Shp(install.getfilename('admin0.shp'),"land")
	admin0.loadshapes()
	coast=Shp(install.getfilename('coast.shp'),"land")
	coast.loadshapes()
	(lon,lat)=admin0.getcenter(index,[0])
	sr=SphereRotation()
	sr.set_deglonlat(lon,lat)
	print_header_svg(output,width,height)
	print_rectangle_svg(output,0,0,width,height,'#ffffff',1.0)
	print_roundwater_svg(output,width)
	admin0.setcssclass(index,-1,"highlight_land",0)
	for one in admin0.shapes:
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,sr)
			onesphere.hemicleave()
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height)
				flatshape.printsvg(output)
	if True:
		lonlat_print_svg(output,sr,width,height)
	# zoom is 400x400, offset is 800,800
	if True:
		cx=495
		cy=495
		r=100
		margin=1
		zoomshift=Shift(-200-margin,-200-margin)
		print_box3d_svg(output,cx-r,cy-r,cx+r,cy+r,'#449944',4,1)
		print_rectangle_svg(output,1000-400-margin,1000-400-margin,400,400,'#70add3',1.0)
		print_rectangle_svg(output,1000-400-margin-10,1000-400-margin-10,10,410,'#ffffff',1.0)
		print_rectangle_svg(output,1000-400-margin-10,1000-400-margin-10,410,10,'#ffffff',1.0)
		print_box3d_svg(output,1000-400-margin,1000-400-margin,1000-margin,1000-margin,'#449944',4,0.8)
		if False:
			print_line_svg(output,cx+r,cy-r,1000-margin,1000-400-margin,'#449944',4,0.8)
			print_line_svg(output,cx-r,cy+r,1000-400-margin,1000-margin,'#449944',4,0.8)
		print_line_svg(output,1000-margin-10,1000-400-margin-10,1000-margin,1000-400-margin,'#449944',1,1)
		print_line_svg(output,1000-400-margin-10,1000-margin-10,1000-400-margin,1000-margin,'#449944',1,1)
		print_line_svg(output,1000-400-margin-10,1000-400-margin-10,1000-400-margin,1000-400-margin,'#449944',1,1)
	admin0.resetcssclass("landz")
	admin0.setcssclass(index,-1,"highlight_land",0)
	for one in admin0.shapes:
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,sr)
			onesphere.hemicleave()
			onesphere.highycleave(0.2)
			onesphere.lowycleave(-0.2)
			onesphere.highzcleave(0.2)
			onesphere.lowzcleave(-0.2)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width*2,height*2)
				flatshape.shift(zoomshift)
				flatshape.printsvg(output)
	if True:
		admin0.resetcssclass("landx")
		if index!=-1: admin0.setcssclass(index,partindex,"highlight2_land",1)
		insetwidth=int(width*0.4)
		insetheight=insetwidth
		insetshift=Shift(int(width*0.01),int(height*0.7))
		print_rectangle_svg(output,int(insetshift.xoff),int(insetshift.yoff+insetheight*0.025),insetwidth,int(insetheight*0.7),'#000000',0.3)
		draworder=0
		while True:
			needmore=False
			for one in admin0.shapes:
				nm=one_inset_webmercator_print_svg(output,admin0,one,draworder,insetwidth,insetheight,insetshift)
				if nm: needmore=True
			if not needmore: break
			draworder+=1
		coast=Shp(install.getfilename('coast.shp'),"land")
		coast.loadshapes()
		for one in coast.shapes:
			one_inset_webmercator_print_svg(output,coast,one,0,insetwidth,insetheight,insetshift)
		mbr=mbr_webmercator(admin0,index,partindex,insetwidth,insetheight,insetshift)
		if mbr.isset:
			print_box3d_svg(output,mbr.minx-10,mbr.miny-10,mbr.maxx+10,mbr.maxy+10,'#449944',5,0.9)
	print_footer_svg(output)

def print_lat_label_svg(output,lon1,lon2,lat,text,width,height,rotation):
	sp1=SpherePoint.makefromdll(DegLonLat(lon1,lat),rotation)
	sp2=SpherePoint.makefromdll(DegLonLat(lon2,lat),rotation)
	fp1=sp1.flatten(width,height)
	fp2=sp2.flatten(width,height)
	if True:
		rr=sp1.y*sp1.y+sp1.z*sp1.z
		if rr>0.9: return
	dy=fp2.uy-fp1.uy
	dx=fp2.ux-fp1.ux
	slope=dy/dx
	normal=math.atan(slope)
	textangle=(normal*180.0)/math.pi
	# output.print('<polyline fill-opacity="0" stroke-opacity="1" stroke="#ffffff" points="%d,%d %d,%d" />'%(fp1.ux,fp1.uy,fp2.ux,fp2.uy))
	xoff=0
	for i in range(len(text)):
		s=text[i:i+1]
		yoff=slope*xoff
		output.print('<text x="0" y="0" style="font:14px sans;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:0.9;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux+xoff,fp1.uy+yoff,textangle,s))
		output.print('<text x="0" y="0" style="font:14px sans;fill:#000000;fill-opacity:1;stroke-opacity:0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux+xoff,fp1.uy+yoff,textangle,s))
		xoff+=8

def print_lon_label_svg(output,lat1,lat2,lon,text,width,height,rotation):
	sp1=SpherePoint.makefromdll(DegLonLat(lon,lat1),rotation)
	sp2=SpherePoint.makefromdll(DegLonLat(lon,lat2),rotation)
	if sp1.x<0: return
	if sp2.x<0: return
	fp1=sp1.flatten(width,height)
	fp2=sp2.flatten(width,height)
	if True:
		norot=SphereRotation()
		fpx=SpherePoint.makefromdll(DegLonLat(90.0,lat2),norot).flatten(width,height)
		if fp2.ux+20>fpx.ux: return
		fpx=SpherePoint.makefromdll(DegLonLat(-90.0,lat2),norot).flatten(width,height)
		if fp2.ux-5<fpx.ux: return
	dy=fp2.uy-fp1.uy
	dx=fp2.ux-fp1.ux
	islope=dx/dy
	normal=math.atan(islope)
	textangle=90-(normal*180.0)/math.pi
	# output.print('<polyline fill-opacity="0" stroke-opacity="1" stroke="#ffffff" points="%d,%d %d,%d" />'%(fp1.ux,fp1.uy,fp2.ux,fp2.uy))
	yoff=0
	for i in range(len(text)):
		s=text[i:i+1]
		xoff=islope*yoff
		output.print('<text x="0" y="0" style="font:14px sans;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:0.9;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux+xoff,fp2.uy+yoff,textangle,s))
		output.print('<text x="0" y="0" style="font:14px sans;fill:#000000;fill-opacity:1;stroke-opacity:0;" text-anchor="middle" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux+xoff,fp2.uy+yoff,textangle,s))
		yoff+=8

	

def lonlat_test(): # test lon/lat text labels
	output=Output()
	width=1000
	height=1000
	lat_center=20
	lon_center=92
	rotation=SphereRotation()
	rotation.set_deglonlat(lon_center,lat_center)
	print_header_svg(output,width,height)
	print_roundwater_svg(output,width)
	lonlat_print_svg(output,rotation,width,height)
	labely=rotation.dlon
	if labely<0: labely=15.0
	else: labely=-15.0
	for label in [ (-150,'150°W'), (-120,'120°W'), (-90,'90°W'), (-60,'60°W'), (-30,'30°W'),
			(0,'0°'), (30,'30°E'), (60,'60°E'), (90,'90°E'), (120,'120°E'), (150,'150°E'), (180,'180°')]:
		print_lon_label_svg(output,10,15,label[0],label[1],width,height,rotation)

	for label in [ (-60,'60°S'), (-30,'30°S'), (0,'0°'), (30,'30°N'), (60,'60°N')]:
		print_lat_label_svg(output,70,75,label[0]+0.5,label[1],width,height,rotation)
	print_footer_svg(output)

def dicttostr(label,d):
	isfirst=True
	a=[]
	a.append(label+' : {')
	for n in d:
		a.append('\t\''+str(n)+'\' : \''+str(d[n])+'\'')
	a.append('}')
	return '\n'.join(a)

def locatormap(output,overrides):
	options={}
	options['comment']=''
	options['copyright']=''
	options['index']=-1
	options['partindices']=[-1]
	options['isinsetleft']=True
	options['iszoom']=False
	options['iszoom34']=False
	options['width']=1000
	options['height']=1000
	options['zoomscale']=2
	options['isroundwater']=True
	options['islakes']=True
	options['issubland']=True
	options['isfix172']=True
	options['ispartlabels']=False
	options['istopinsets']=False

	options['comment']=dicttostr('settings',overrides)
	for n in overrides: options[n]=overrides[n]

	admin0=Shp(install.getfilename('admin0.shp'),"land")
	if isverbose_global: print('Loading admin0 shape data',file=sys.stderr)
	admin0.loadshapes()
	if options['ispartlabels'] and options['index']!=-1 and admin0.shapes[options['index']].partscount==1:
		options['ispartlabels']=False

	if options['issubland']:
		if 'grp' not in options:
			if isverbose_global: print('Loading admin0 dbf data',file=sys.stderr)
			index=options['index']
			admin0dbf=Dbf(install.getfilename('admin0.dbf'))
			admin0dbf.selectcfield('SOV_A3','sov3')
			admin0dbf.selectcfield('ADM0_A3','adm3')
			admin0dbf.loadrecords()
			a0r=admin0dbf.records[index]
			options['grp']=a0r['sov3']
			options['subgrp']=a0r['adm3']

	if 'lon' not in options or 'lat' not in options:
		index=options['index']
		if 'centerindices' in options: centerindices=options['centerindices']
		else: centerindices=options['partindices']
		(lon,lat)=admin0.getcenter(index,centerindices)
		if 'lon' not in options: options['lon']=lon
		if 'lat' not in options: options['lat']=lat

	if 'xoff_inset' not in options:
		margin=0.005
		width=options['width']
		height=options['height']
		if options['isinsetleft']: options['xoff_inset']=int(width*margin)
		else: options['xoff_inset']=int(width*(1-0.4-margin))
		if options['istopinsets']:
			options['yoff_inset']=int(height*margin)
		else:
			options['yoff_inset']=int(height*(0.76-margin))

	if 'latlabel_lon' not in options:
		if options['isinsetleft']:
			labelx=options['lon']-30
			labelx=int(labelx/30)*30+20
		else:
			labelx=options['lon']+30
			labelx=int(labelx/30)*30-20
		options['latlabel_lon']=labelx

	if 'lonlabel_lat' not in options:
		if options['lat']>0: options['lonlabel_lat']=-10
		else: options['lonlabel_lat']=10

	if 'tripelboxes' not in options:
		options['tripelboxes']=[options['partindices']]

	if 'smalldots' in options:
		if 'moredots' in options: raise ValueError
		options['moredots']=[(4,False,options['smalldots'])]
	
	combo_print_svg(output,install,options,admin0)


def indonesia_locator(output,overrides):
	options={'index':0,'isinsetleft':True,'lonlabel_lat':35,'latlabel_lon':180,'title':'Indonesia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def malaysia_locator(output,overrides):
	options={'index':1,'isinsetleft':True,'lonlabel_lat':-17,'latlabel_lon':170,'title':'Malaysia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def chile_locator(output,overrides):
	options={'index':2,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,'title':'Chile locator'}
	options['moredots']=[(4,False,[2,3,4,5,6,7])]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bolivia_locator(output,overrides):
	options={'index':3,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Bolivia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def peru_locator(output,overrides):
	options={'index':4,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Peru locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def argentina_locator(output,overrides):
	options={'index':5,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Argentina locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def dhekelia_locator(output,overrides):
	options={'index':6,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Dhekelia locator'}
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def cyprus_locator(output,overrides):
	options={'index':7,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Cyprus locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots']=[ (30,3,[2]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def india_locator(output,overrides):
	options={'index':8,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':55,'title':'India locator'}
	options['moredots']=[ (4,False,[2,3,4,5,6,7,8,9,17]), (45,False,[21]) ]
#	options['ispartlabels']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def china_locator(output,overrides):
	options={'index':9,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':175,'title':'China locator'}
	options['moredots']=[ (4,False,[32,33,42,43,44,45,69]) ]
#	options['ispartlabels']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def israel_locator(output,overrides):
	options={'index':10,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Israel locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots']=[ (30,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def palestine_locator(output,overrides):
	options={'index':11,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Palestine locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots']=[ (30,True,[1]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def lebanon_locator(output,overrides):
	options={'index':12,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Lebanon locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots']=[ (30,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ethiopia_locator(output,overrides):
	options={'index':13,'isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':-25,'title':'Ethiopia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def southsudan_locator(output,overrides):
	options={'index':14,'isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'South Sudan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def somalia_locator(output,overrides):
	options={'index':15,'isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Somalia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def kenya_locator(output,overrides):
	options={'index':16,'isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Kenya locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def pakistan_locator(output,overrides):
	options={'index':17,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Pakistan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def malawi_locator(output,overrides):
	options={'index':18,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Malawi locator'}
	options['iszoom']=False
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def unitedrepublicoftanzania_locator(output,overrides):
	options={'index':19,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'United Republic of Tanzania locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def syria_locator(output,overrides):
	options={'index':20,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Syria locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def somaliland_locator(output,overrides):
	options={'index':21,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Somaliland locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def france_locator(output,overrides):
	options={'index':22,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'France locator'}
	options['iszoom']=True
	options['issubland']=False
	options['partindices']=[1,11,12,13,14,15,16,17,18,21]

	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def suriname_locator(output,overrides):
	options={'index':23,'isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Suriname locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def guyana_locator(output,overrides):
	options={'index':24,'isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Guyana locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def southkorea_locator(output,overrides):
	options={'index':25,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'South Korea locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def northkorea_locator(output,overrides):
	options={'index':26,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'North Korea locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def morocco_locator(output,overrides):
	options={'index':27,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Morocco locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def westernsahara_locator(output,overrides):
	options={'index':28,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Western Sahara locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def costarica_locator(output,overrides):
	options={'index':29,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Costa Rica locator'}
	options['moredots']=[ (4,False,[2]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def nicaragua_locator(output,overrides):
	options={'index':30,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Nicaragua locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def republicofthecongo_locator(output,overrides):
	options={'index':31,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Republic of the Congo locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def democraticrepublicofthecongo_locator(output,overrides):
	options={'index':32,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Democratic Republic of the Congo locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bhutan_locator(output,overrides):
	options={'index':33,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Bhutan locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ukraine_locator(output,overrides):
	options={'index':34,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Ukraine locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def belarus_locator(output,overrides):
	options={'index':35,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Belarus locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def namibia_locator(output,overrides):
	options={'index':36,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Namibia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def southafrica_locator(output,overrides):
	options={'index':37,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'South Africa locator'}
	options['moredots']=[ (4,True,[2,3]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saintmartin_locator(output,overrides):
	options={'index':38,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Saint Martin locator'}
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def sintmaarten_locator(output,overrides):
	options={'index':39,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Sint Maarten locator'}
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def oman_locator(output,overrides):
	options={'index':40,'isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Oman locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def uzbekistan_locator(output,overrides):
	options={'index':41,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Uzbekistan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def kazakhstan_locator(output,overrides):
	options={'index':42,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Kazakhstan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def tajikistan_locator(output,overrides):
	options={'index':43,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Tajikistan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def lithuania_locator(output,overrides):
	options={'index':44,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Lithuania locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def brazil_locator(output,overrides):
	options={'index':45,'isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Brazil locator'}
	options['moredots']=[ (4,False,[27,28,36]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def uruguay_locator(output,overrides):
	options={'index':46,'isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Uruguay locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def mongolia_locator(output,overrides):
	options={'index':47,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Mongolia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def russia_locator(output,overrides):
	options={'index':48,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':179,'title':'Russia locator'}
	options['lon']=109
	options['moredots']=[ (4,False,[137]) ]
	options['tripelboxes']=[ [0,1,2], [70] ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def czechia_locator(output,overrides):
	options={'index':49,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Czechia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def germany_locator(output,overrides):
	options={'index':50,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Germany locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def estonia_locator(output,overrides):
	options={'index':51,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Estonia locator'}
	options['iszoom']=True
	options['centerdot']=(25,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def latvia_locator(output,overrides):
	options={'index':52,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Latvia locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def norway_locator(output,overrides):
	options={'index':53,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Norway locator'}
	options['centerindices']=[0,96]
	options['moredots']=[ (4,False,[74,97]) ]
	options['zoomdots']=[ (10,False,[74,97]) ]
	options['iszoom']=True
	options['tripelboxes']=[ [0,1,2,86] ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def sweden_locator(output,overrides):
	options={'index':54,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Sweden locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def finland_locator(output,overrides):
	options={'index':55,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Finland locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def vietnam_locator(output,overrides):
	options={'index':56,'isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':165,'title':'Vietnam locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def cambodia_locator(output,overrides):
	options={'index':57,'isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':160,'title':'Cambodia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def luxembourg_locator(output,overrides):
	options={'index':58,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Luxembourg locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['moredots']=[ (30,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def unitedarabemirates_locator(output,overrides):
	options={'index':59,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'United Arab Emirates locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def belgium_locator(output,overrides):
	options={'index':60,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Belgium locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots']=[ (25,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def georgia_locator(output,overrides):
	options={'index':61,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Georgia locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def macedonia_locator(output,overrides):
	options={'index':62,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Macedonia locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def albania_locator(output,overrides):
	options={'index':63,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Albania locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def azerbaijan_locator(output,overrides):
	options={'index':64,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Azerbaijan locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def kosovo_locator(output,overrides):
	options={'index':65,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Kosovo locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def turkey_locator(output,overrides):
	options={'index':66,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Turkey locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def spain_locator(output,overrides):
	options={'index':67,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Spain locator'}
	options['moredots']=[(10,False,[1]),(24,False,[5])]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def laos_locator(output,overrides):
	options={'index':68,'isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':165,'title':'Laos locator'}
	options['iszoom']=False
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def kyrgyzstan_locator(output,overrides):
	options={'index':69,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Kyrgyzstan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def armenia_locator(output,overrides):
	options={'index':70,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Armenia locator'}
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def denmark_locator(output,overrides):
	options={'index':71,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Denmark locator'}
	options['moredots']=[ (4,False,[6]) ]
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def libya_locator(output,overrides):
	options={'index':72,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Libya locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def tunisia_locator(output,overrides):
	options={'index':73,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Tunisia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def romania_locator(output,overrides):
	options={'index':74,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Romania locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def hungary_locator(output,overrides):
	options={'index':75,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Hungary locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def slovakia_locator(output,overrides):
	options={'index':76,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Slovakia locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def poland_locator(output,overrides):
	options={'index':77,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Poland locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ireland_locator(output,overrides):
	options={'index':78,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Ireland locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def unitedkingdom_locator(output,overrides):
	options={'index':79,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'United Kingdom locator'}
	options['moredots']=[(4,False,[36, 52] ) ]
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def greece_locator(output,overrides):
	options={'index':80,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Greece locator'}
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def zambia_locator(output,overrides):
	options={'index':81,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Zambia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def sierraleone_locator(output,overrides):
	options={'index':82,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Sierra Leone locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def guinea_locator(output,overrides):
	options={'index':83,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Guinea locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def liberia_locator(output,overrides):
	options={'index':84,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Liberia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def centralafricanrepublic_locator(output,overrides):
	options={'index':85,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Central African Republic locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def sudan_locator(output,overrides):
	options={'index':86,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Sudan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def djibouti_locator(output,overrides):
	options={'index':87,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Djibouti locator'}
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def eritrea_locator(output,overrides):
	options={'index':88,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Eritrea locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def austria_locator(output,overrides):
	options={'index':89,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Austria locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def iraq_locator(output,overrides):
	options={'index':90,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Iraq locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def italy_locator(output,overrides):
	options={'index':91,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Italy locator'}
	options['moredots']=[ (4,False,[3]),(6,False,[18,24]) ] # 18,24
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def switzerland_locator(output,overrides):
	options={'index':92,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Switzerland locator'}
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def iran_locator(output,overrides):
	options={'index':93,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Iran locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def netherlands_locator(output,overrides):
	options={'index':94,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Netherlands locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['centerindices']=[0]
	options['moredots']=[ (8,True,[2,3,11]) , (25,True,[0]) ]
	options['tripelboxes']=[ [0], [2,3,11] ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def liechtenstein_locator(output,overrides):
	options={'index':95,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Liechtenstein locator'}
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ivorycoast_locator(output,overrides):
	options={'index':96,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Ivory Coast locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def republicofserbia_locator(output,overrides):
	options={'index':97,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Republic of Serbia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def mali_locator(output,overrides):
	options={'index':98,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Mali locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def senegal_locator(output,overrides):
	options={'index':99,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Senegal locator'}
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def nigeria_locator(output,overrides):
	options={'index':100,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Nigeria locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def benin_locator(output,overrides):
	options={'index':101,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Benin locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def angola_locator(output,overrides):
	options={'index':102,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Angola locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def croatia_locator(output,overrides):
	options={'index':103,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Croatia locator'}
	options['iszoom']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def slovenia_locator(output,overrides):
	options={'index':104,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Slovenia locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def qatar_locator(output,overrides):
	options={'index':105,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Qatar locator'}
	options['iszoom']=True
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saudiarabia_locator(output,overrides):
	options={'index':106,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Saudi Arabia locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def botswana_locator(output,overrides):
	options={'index':107,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Botswana locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def zimbabwe_locator(output,overrides):
	options={'index':108,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Zimbabwe locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bulgaria_locator(output,overrides):
	options={'index':109,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Bulgaria locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def thailand_locator(output,overrides):
	options={'index':110,'isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':160,'title':'Thailand locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def sanmarino_locator(output,overrides):
	options={'index':111,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'San Marino locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['moredots']=[ (25,True,[0]) ]
	options['zoomdots']=[ (15,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def haiti_locator(output,overrides):
	options={'index':112,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Haiti locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,2,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def dominicanrepublic_locator(output,overrides):
	options={'index':113,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Dominican Republic locator'}
	options['iszoom']=True
	options['zoomscale']=4
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def chad_locator(output,overrides):
	options={'index':114,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Chad locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def kuwait_locator(output,overrides):
	options={'index':115,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-22,'title':'Kuwait locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def elsalvador_locator(output,overrides):
	options={'index':116,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-150,'title':'El Salvador locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,2,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def guatemala_locator(output,overrides):
	options={'index':117,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Guatemala locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def easttimor_locator(output,overrides):
	options={'index':118,'isinsetleft':True,'lonlabel_lat':-25,'latlabel_lon':90,'title':'East Timor locator'}
	options['istopinsets']=True
	options['iszoom']=True
	options['zoomscale']=4
	options['centerdot']=(40,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def brunei_locator(output,overrides):
	options={'index':119,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,'title':'Brunei locator'}
	options['istopinsets']=True
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def monaco_locator(output,overrides):
	options={'index':120,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Monaco locator'}
	options['iszoom']=True
	options['zoomscale']=64
	options['moredots']=[ (15,4,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def algeria_locator(output,overrides):
	options={'index':121,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Algeria locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def mozambique_locator(output,overrides):
	options={'index':122,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Mozambique locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def eswatini_locator(output,overrides):
	options={'index':123,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'eSwatini locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def burundi_locator(output,overrides):
	options={'index':124,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Burundi locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots']=[ (20,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def rwanda_locator(output,overrides):
	options={'index':125,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Rwanda locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots']=[ (20,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def myanmar_locator(output,overrides):
	options={'index':126,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Myanmar locator'}
	options['smalldots']=[29,30]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bangladesh_locator(output,overrides):
	options={'index':127,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Bangladesh locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def andorra_locator(output,overrides):
	options={'index':128,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Andorra locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['moredots']=[ (15,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def afghanistan_locator(output,overrides):
	options={'index':129,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Afghanistan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def montenegro_locator(output,overrides):
	options={'index':130,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Montenegro locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bosniaandherzegovina_locator(output,overrides):
	options={'index':131,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Bosnia and Herzegovina locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def uganda_locator(output,overrides):
	options={'index':132,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Uganda locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def usnavalbaseguantanamobay_locator(output,overrides):
	options={'index':133,'isinsetleft':True,'lonlabel_lat':5,'latlabel_lon':-30,'title':'US Naval Base Guantanamo Bay locator'}
	options['iszoom']=True
	options['zoomscale']=20
	options['moredots']=[ (20,4,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def cuba_locator(output,overrides):
	options={'index':134,'isinsetleft':True,'lonlabel_lat':5,'latlabel_lon':-30,'title':'Cuba locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def honduras_locator(output,overrides):
	options={'index':135,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Honduras locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['smalldots']=[6]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ecuador_locator(output,overrides):
	options={'index':136,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Ecuador locator'}
	
	options['moredots']=[ (20,False,[7]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def colombia_locator(output,overrides):
	options={'index':137,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Colombia locator'}
	options['smalldots']=[5,6,7,10]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def paraguay_locator(output,overrides):
	options={'index':138,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Paraguay locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def portugal_locator(output,overrides):
	options={'index':139,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Portugal locator'}
	options['smalldots']=[2,3,5,6,7,8,9,10,11,12,13,14,15]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def moldova_locator(output,overrides):
	options={'index':140,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Moldova locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def turkmenistan_locator(output,overrides):
	options={'index':141,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Turkmenistan locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def jordan_locator(output,overrides):
	options={'index':142,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Jordan locator'}
	options['iszoom']=True
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def nepal_locator(output,overrides):
	options={'index':143,'isinsetleft':True,'lonlabel_lat':-5,'latlabel_lon':50,'title':'Nepal locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def lesotho_locator(output,overrides):
	options={'index':144,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Lesotho locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def cameroon_locator(output,overrides):
	options={'index':145,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Cameroon locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def gabon_locator(output,overrides):
	options={'index':146,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Gabon locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def niger_locator(output,overrides):
	options={'index':147,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Niger locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def burkinafaso_locator(output,overrides):
	options={'index':148,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Burkina Faso locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def togo_locator(output,overrides):
	options={'index':149,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Togo locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ghana_locator(output,overrides):
	options={'index':150,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Ghana locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def guineabissau_locator(output,overrides):
	options={'index':151,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Guinea-Bissau locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots']=[ (20,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def gibraltar_locator(output,overrides):
	options={'index':152,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Gibraltar locator'}
	options['iszoom']=True
	options['zoomscale']=64
	options['iszoom34']=False
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def unitedstatesofamerica_locator(output,overrides):
	options={'index':153,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-45,'title':'United States of America locator'}
	options['lon']=-110
	options['smalldots']=[272,273,274,275,276]
	options['tripelboxes']=[ [0], [85,199], [232] ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def canada_locator(output,overrides):
	options={'index':154,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Canada locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def mexico_locator(output,overrides):
	options={'index':155,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-150,'title':'Mexico locator'}
	options['smalldots']=[1,2,3,32,34,36]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def belize_locator(output,overrides):
	options={'index':156,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Belize locator'}
	options['moredots']=[ (30,2,[0]) ]
	options['iszoom']=True
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def panama_locator(output,overrides):
	options={'index':157,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Panama locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def venezuela_locator(output,overrides):
	options={'index':158,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Venezuela locator'}
	options['smalldots']=[ 20 ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def papuanewguinea_locator(output,overrides):
	options={'index':159,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Papua New Guinea locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def egypt_locator(output,overrides):
	options={'index':160,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Egypt locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def yemen_locator(output,overrides):
	options={'index':161,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Yemen locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def mauritania_locator(output,overrides):
	options={'index':162,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Mauritania locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def equatorialguinea_locator(output,overrides):
	options={'index':163,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Equatorial Guinea locator'}
	options['iszoom']=True
	options['iszoom34']=True
	options['moredots']=[ (20,2,[0]),(4,False,[1]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def gambia_locator(output,overrides):
	options={'index':164,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Gambia locator'}
	options['moredots']=[ (25,2,[0]) ]
	options['iszoom']=True
	options['zoomscale']=5
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def hongkongsar_locator(output,overrides):
	options={'index':165,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':175,'title':'Hong Kong S.A.R. locator'}
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def vatican_locator(output,overrides):
	options={'index':166,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Vatican locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=False
	options['moredots']=[ (10,True,[0]) ]
	options['zoomdots']=[ (15,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def northerncyprus_locator(output,overrides):
	options={'index':167,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Northern Cyprus locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=False
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def cyprusnomansarea_locator(output,overrides):
	options={'index':168,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Cyprus No Mans Area locator'}
	options['iszoom']=True
	options['zoomscale']=20
	options['iszoom34']=False
	options['moredots']=[ (20,3,[0]) ]
	options['issubland']=False
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def siachenglacier_locator(output,overrides):
	options={'index':169,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Siachen Glacier locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=False
	options['moredots']=[ (20,2,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def baykonurcosmodrome_locator(output,overrides):
	options={'index':170,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Baykonur Cosmodrome locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots']=[ (20,2,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def akrotirisovereignbasearea_locator(output,overrides):
	options={'index':171,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Akrotiri Sovereign Base Area locator'}
	options['iszoom']=True
	options['zoomscale']=16
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def antarctica_locator(output,overrides):
	options={'index':172,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Antarctica locator'}
	options['istopinsets']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def australia_locator(output,overrides):
	options={'index':173,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Australia locator'}
	options['smalldots']=[ 12, 33 ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def greenland_locator(output,overrides):
	options={'index':174,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Greenland locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def fiji_locator(output,overrides):
	options={'index':175,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':150,'title':'Fiji locator'}
	options['centerindices']=[20]
	options['tripelboxes']=[ [0],[24] ]
	options['smalldots']=[ 34,35,36,37 ]
	options['zoomdots']=[ (10,False,[34,35]) ]
	options['centerdot']=(55,2)
	options['iszoom']=True
	options['iszoom34']=True
	options['zoomscale']=2.5
#	options['ispartlabels']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def newzealand_locator(output,overrides):
	options={'index':176,'isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':-150,'title':'New Zealand locator'}
	options['centerindices']=[17]
	options['tripelboxes']=[ [7],[17] ]
	options['smalldots']=[ 1,2,3,4,5,6,7,8]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def newcaledonia_locator(output,overrides):
	options={'index':177,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-150,'title':'New Caledonia locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots']=[ (4,False,[10]) ]
	options['centerdot']=(40,2)
#	options['ispartlabels']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def madagascar_locator(output,overrides):
	options={'index':178,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Madagascar locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def philippines_locator(output,overrides):
	options={'index':179,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':180,'title':'Philippines locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def srilanka_locator(output,overrides):
	options={'index':180,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,'title':'Sri Lanka locator'}
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def curacao_locator(output,overrides):
	options={'index':181,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Curaçao locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def aruba_locator(output,overrides):
	options={'index':182,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Aruba locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def thebahamas_locator(output,overrides):
	options={'index':183,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'The Bahamas locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=False
#	options['moredots']=[ (50,False,[8]) ]
	options['centerdot']=(50,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def turksandcaicosislands_locator(output,overrides):
	options={'index':184,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Turks and Caicos Islands locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=False
#	options['moredots']=[ (20,True,[8]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def taiwan_locator(output,overrides):
	options={'index':185,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Taiwan locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots']=[ (4,False,[2]), (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def japan_locator(output,overrides):
	options={'index':186,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Japan locator'}
	options['smalldots']=[ 60,80, 14, 62, 12, 59, 61, 54, 84, 66, 67, 16]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saintpierreandmiquelon_locator(output,overrides):
	options={'index':187,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Saint Pierre and Miquelon locator'}
	options['iszoom']=True
	options['zoomscale']=16
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(25,4)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def iceland_locator(output,overrides):
	options={'index':188,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-60,'title':'Iceland locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def pitcairnislands_locator(output,overrides):
	options={'index':189,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Pitcairn Islands locator'}
#	options['moredots']=[ (10,True,[0,1,2,3]) ]
	options['centerdot']=(30,3)
#	options['ispartlabels']=True
	options['iszoom']=True
	options['zoomscale']=5
	options['zoomdots']=[ (15,False,[0,1,2,3]) ]
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def frenchpolynesia_locator(output,overrides):
	options={'index':190,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'French Polynesia locator'}
#	options['moredots']=[ (100,True,[87]) ]
	options['centerdot']=(110,2)
	options['iszoom']=True
	options['zoomscale']=2
	if False:
		zds=[]
		for i in range(88): zds.append(i)
		options['zoomdots']=[ (5,False,zds) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def frenchsouthernandantarcticlands_locator(output,overrides):
	options={'index':191,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'French Southern and Antarctic Lands locator'}
	options['moredots']=[ (12,3,[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def seychelles_locator(output,overrides):
	options={'index':192,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Seychelles locator'}
	dots=[]
	for i in range(26): dots.append(i)
	options['moredots']=[ (12,2,dots) ]
	options['zoomdots']=[ (10,False,dots) ]
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=False
	
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def kiribati_locator(output,overrides):
	options={'index':193,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,'title':'Kiribati locator'}
	options['centerindices']=[26]
	options['tripelboxes']=[ [0],[1,29,34] ]
	dots=[]
	for i in range(35): dots.append(i)
	options['moredots']=[ (8,False,dots) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def marshallislands_locator(output,overrides):
	options={'index':194,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Marshall Islands locator'}
	dots=[]
	for i in range(22): dots.append(i)
	options['moredots']=[ (8,False,dots) ]
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['zoomdots']=[ (5,False,dots) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def trinidadandtobago_locator(output,overrides):
	options={'index':195,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Trinidad and Tobago locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def grenada_locator(output,overrides):
	options={'index':196,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Grenada locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['moredots']=[ (30,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saintvincentandthegrenadines_locator(output,overrides):
	options={'index':197,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Vincent and the Grenadines locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def barbados_locator(output,overrides):
	options={'index':198,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Barbados locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saintlucia_locator(output,overrides):
	options={'index':199,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Lucia locator'}
#	options['ispartlabels']=True
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def dominica_locator(output,overrides):
	options={'index':200,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Dominica locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def unitedstatesminoroutlyingislands_locator(output,overrides):
	options={'index':201,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-130,'title':'United States Minor Outlying Islands locator'}
	options['tripelboxes']=[ [5],[10],[0,1,2,3,4,  6,7,8,9,  11,12] ]
	options['lon']=-120
	
	dots=[]
	for i in range(13): dots.append(i)
	options['moredots']=[ (20,True,dots) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def montserrat_locator(output,overrides):
	options={'index':202,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Montserrat locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['zoomdots']=[ (15,False,[0]) ]
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def antiguaandbarbuda_locator(output,overrides):
	options={'index':203,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Antigua and Barbuda locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['zoomdots']=[ (10,False,[0,1]) ]
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saintkittsandnevis_locator(output,overrides):
	options={'index':204,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Kitts and Nevis locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['zoomdots']=[ (25,False,[0]) ]
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def unitedstatesvirginislands_locator(output,overrides):
	options={'index':205,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'United States Virgin Islands locator'}
	options['iszoom']=True
	options['zoomscale']=16
	options['iszoom34']=False
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saintbarthelemy_locator(output,overrides):
	options={'index':206,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Barthelemy locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['zoomdots']=[ (10,False,[0]) ]
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def puertorico_locator(output,overrides):
	options={'index':207,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Puerto Rico locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['zoomdots']=[ (10,False,[0,1,2]) ]
#	options['moredots']=[ (30,True,[3]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def anguilla_locator(output,overrides):
	options={'index':208,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Anguilla locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['zoomdots']=[ (4,False,[0,1]) ]
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def britishvirginislands_locator(output,overrides):
	options={'index':209,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'British Virgin Islands locator'}
	options['iszoom']=True
	options['zoomscale']=16
	options['iszoom34']=True
#	options['zoomdots']=[ (4,False,[0,1,2,3,4,5]) ]
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def jamaica_locator(output,overrides):
	options={'index':210,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Jamaica locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots']=[ (20,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def caymanislands_locator(output,overrides):
	options={'index':211,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Cayman Islands locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bermuda_locator(output,overrides):
	options={'index':212,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Bermuda locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['moredots']=[ (15,4,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def heardislandandmcdonaldislands_locator(output,overrides):
	options={'index':213,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,'title':'Heard Island and McDonald Islands locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def sainthelena_locator(output,overrides):
	options={'index':214,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Saint Helena locator'}
	options['moredots']=[ (10,3,[0,1,2,3]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def mauritius_locator(output,overrides):
	options={'index':215,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Mauritius locator'}
	options['moredots']=[ (10,3,[0,1,2]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def comoros_locator(output,overrides):
	options={'index':216,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Comoros locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def saotomeandprincipe_locator(output,overrides):
	options={'index':217,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'São Tomé and Principe locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def caboverde_locator(output,overrides):
	options={'index':218,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Cabo Verde locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots']=[ (30,True,[5]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def malta_locator(output,overrides):
	options={'index':219,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Malta locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots']=[ (30,4,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def jersey_locator(output,overrides):
	options={'index':220,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Jersey locator'}
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
	options['moredots']=[ (30,3,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def guernsey_locator(output,overrides):
	options={'index':221,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Guernsey locator'}
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def isleofman_locator(output,overrides):
	options={'index':222,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Isle of Man locator'}
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
	options['moredots']=[ (20,4,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def aland_locator(output,overrides):
	options={'index':223,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Aland locator'}
	options['iszoom']=True
	options['zoomscale']=10
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def faroeislands_locator(output,overrides):
	options={'index':224,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Faroe Islands locator'}
	options['iszoom']=True
	options['zoomscale']=5
#	options['moredots']=[ (30,True,[0]) ]
	options['centerdot']=(30,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def indianoceanterritories_locator(output,overrides):
	options={'index':225,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Indian Ocean Territories locator'}
	options['moredots']=[ (10,True,[0,2]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def britishindianoceanterritory_locator(output,overrides):
	options={'index':226,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'British Indian Ocean Territory locator'}
#	options['moredots']=[ (40,False,[5]) ]
	options['centerdot']=(40,3)
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def singapore_locator(output,overrides):
	options={'index':227,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Singapore locator'}
	options['moredots']=[ (20,True,[0]) ]
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def norfolkisland_locator(output,overrides):
	options={'index':228,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Norfolk Island locator'}
	options['iszoom']=True
	options['zoomscale']=64
	options['iszoom34']=True
	options['moredots']=[ (20,True,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def cookislands_locator(output,overrides):
	options={'index':229,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Cook Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots']=[ (10,2,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	options['zoomdots']=[ (5,False,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def tonga_locator(output,overrides):
	options={'index':230,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Tonga locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['centerdot']=(40,3)
#	options['moredots']=[ (40,False,[0]) ]
	options['zoomdots']=[ (5,False,[0,1,2,3,4,5,6,7,8,9]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def wallisandfutuna_locator(output,overrides):
	options={'index':231,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Wallis and Futuna locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots']=[ (10,3,[0,1]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def samoa_locator(output,overrides):
	options={'index':232,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Samoa locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['centerdot']=(20,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def solomonislands_locator(output,overrides):
	options={'index':233,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Solomon Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(70,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def tuvalu_locator(output,overrides):
	options={'index':234,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Tuvalu locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['centerdot']=(30,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def maldives_locator(output,overrides):
	options={'index':235,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Maldives locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(45,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def nauru_locator(output,overrides):
	options={'index':236,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Nauru locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots']=[ (15,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def federatedstatesofmicronesia_locator(output,overrides):
	options={'index':237,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Federated States of Micronesia locator'}
	dots=[]
	for i in range(20): dots.append(i)
	options['moredots']=[ (7,2,dots) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def southgeorgiaandtheislands_locator(output,overrides):
	options={'index':238,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':0,'title':'South Georgia and the Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(50,4)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def falklandislands_locator(output,overrides):
	options={'index':239,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Falkland Islands locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['centerdot']=(25,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def vanuatu_locator(output,overrides):
	options={'index':240,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Vanuatu locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(40,3)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def niue_locator(output,overrides):
	options={'index':241,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Niue locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots']=[ (15,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def americansamoa_locator(output,overrides):
	options={'index':242,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'American Samoa locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(30,3)
	options['zoomdots']=[ (10,False,[0,1,2,3,4]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def palau_locator(output,overrides):
	options={'index':243,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Palau locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(40,3)
	options['zoomdots']=[ (8,False,[0,1,2,3,4,5,6,7,8]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def guam_locator(output,overrides):
	options={'index':244,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Guam locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(30,3)
	options['zoomdots']=[ (7,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def northernmarianaislands_locator(output,overrides):
	options={'index':245,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Northern Mariana Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(40,3)
	options['zoomdots']=[ (4,False,[0,1,2,3,4,5,6,7,8,9,10,11]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bahrain_locator(output,overrides):
	options={'index':246,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Bahrain locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['centerdot']=(20,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def coralseaislands_locator(output,overrides):
	options={'index':247,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Coral Sea Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots']=[ (10,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def spratlyislands_locator(output,overrides):
	options={'index':248,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':175,'title':'Spratly Islands locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots']=[ (4,False,[0,1,2,3,4,5,6,7,8,9,10,11]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def clippertonisland_locator(output,overrides):
	options={'index':249,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,'title':'Clipperton Island locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots']=[ (10,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def macaosar_locator(output,overrides):
	options={'index':250,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Macao S.A.R locator'}
	options['iszoom']=True
	options['zoomscale']=32
	options['iszoom34']=True
	options['centerdot']=(20,True)
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def ashmoreandcartierislands_locator(output,overrides):
	options={'index':251,'isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Ashmore and Cartier Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots']=[ (10,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def bajonuevobank_locator(output,overrides):
	options={'index':252,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Bajo Nuevo Bank (Petrel Is.) locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots']=[ (10,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def serranillabank_locator(output,overrides):
	options={'index':253,'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Serranilla Bank locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots']=[ (10,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def scarboroughreef_locator(output,overrides):
	options={'index':254,'isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':180,'title':'Scarborough Reef locator'}
#	options['ispartlabels']=True
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots']=[ (10,False,[0]) ]
	for n in overrides: options[n]=overrides[n]
	locatormap(output,options)

def addlocators(dest):
#	dest.append( ('x_locator',scarboroughreef_locator) )

	dest.append( ('indonesia_locator',indonesia_locator) )
	dest.append( ('malaysia_locator',malaysia_locator) )
	dest.append( ('chile_locator',chile_locator) )
	dest.append( ('bolivia_locator',bolivia_locator) )
	dest.append( ('peru_locator',peru_locator) )
	dest.append( ('argentina_locator',argentina_locator) )
	dest.append( ('dhekelia_locator',dhekelia_locator) )
	dest.append( ('cyprus_locator',cyprus_locator) )
	dest.append( ('india_locator',india_locator) )
	dest.append( ('china_locator',china_locator) )

	dest.append( ('israel_locator',israel_locator) )
	dest.append( ('palestine_locator',palestine_locator) )
	dest.append( ('lebanon_locator', lebanon_locator) )
	dest.append( ('ethiopia_locator', ethiopia_locator) )
	dest.append( ('southsudan_locator', southsudan_locator) )
	dest.append( ('somalia_locator', somalia_locator) )
	dest.append( ('kenya_locator', kenya_locator) )
	dest.append( ('pakistan_locator', pakistan_locator) )
	dest.append( ('malawi_locator', malawi_locator) )
	dest.append( ('unitedrepublicoftanzania_locator', unitedrepublicoftanzania_locator) )
	dest.append( ('syria_locator', syria_locator) )
	dest.append( ('somaliland_locator', somaliland_locator) )
	dest.append( ('france_locator', france_locator) )
	dest.append( ('suriname_locator', suriname_locator) )
	dest.append( ('guyana_locator', guyana_locator) )
	dest.append( ('southkorea_locator', southkorea_locator) )
	dest.append( ('northkorea_locator', northkorea_locator) )
	dest.append( ('morocco_locator', morocco_locator) )
	dest.append( ('westernsahara_locator', westernsahara_locator) )
	dest.append( ('costarica_locator', costarica_locator) )
	dest.append( ('nicaragua_locator', nicaragua_locator) )
	dest.append( ('republicofthecongo_locator', republicofthecongo_locator) )
	dest.append( ('democraticrepublicofthecongo_locator', democraticrepublicofthecongo_locator) )
	dest.append( ('bhutan_locator', bhutan_locator) )
	dest.append( ('ukraine_locator', ukraine_locator) )
	dest.append( ('belarus_locator', belarus_locator) )
	dest.append( ('namibia_locator', namibia_locator) )
	dest.append( ('southafrica_locator', southafrica_locator) )
	dest.append( ('saintmartin_locator', saintmartin_locator) )
	dest.append( ('sintmaarten_locator', sintmaarten_locator) )
	dest.append( ('oman_locator', oman_locator) )
	dest.append( ('uzbekistan_locator', uzbekistan_locator) )
	dest.append( ('kazakhstan_locator', kazakhstan_locator) )
	dest.append( ('tajikistan_locator', tajikistan_locator) )
	dest.append( ('lithuania_locator', lithuania_locator) )

	dest.append( ('brazil_locator',brazil_locator) )
	dest.append( ('uruguay_locator', uruguay_locator) )
	dest.append( ('mongolia_locator', mongolia_locator) )
	dest.append( ('russia_locator', russia_locator) )
	dest.append( ('czechia_locator', czechia_locator) )
	dest.append( ('germany_locator', germany_locator) )
	dest.append( ('estonia_locator', estonia_locator) )
	dest.append( ('latvia_locator', latvia_locator) )
	dest.append( ('norway_locator', norway_locator) )
	dest.append( ('sweden_locator', sweden_locator) )
	dest.append( ('finland_locator', finland_locator) )
	dest.append( ('vietnam_locator',vietnam_locator) )
	dest.append( ('cambodia_locator', cambodia_locator) )
	dest.append( ('luxembourg_locator', luxembourg_locator) )
	dest.append( ('unitedarabemirates_locator', unitedarabemirates_locator) )
	dest.append( ('belgium_locator', belgium_locator) )
	dest.append( ('georgia_locator', georgia_locator) )
	dest.append( ('macedonia_locator', macedonia_locator) )
	dest.append( ('albania_locator', albania_locator) )
	dest.append( ('azerbaijan_locator', azerbaijan_locator) )
	dest.append( ('kosovo_locator', kosovo_locator) )
	dest.append( ('turkey_locator', turkey_locator) )
	dest.append( ('spain_locator', spain_locator) )
	dest.append( ('laos_locator',laos_locator) )
	dest.append( ('kyrgyzstan_locator', kyrgyzstan_locator) )
	dest.append( ('armenia_locator', armenia_locator) )
	dest.append( ('denmark_locator', denmark_locator) )
	dest.append( ('libya_locator', libya_locator) )
	dest.append( ('tunisia_locator', tunisia_locator) )
	dest.append( ('romania_locator', romania_locator) )
	dest.append( ('hungary_locator', hungary_locator) )
	dest.append( ('slovakia_locator', slovakia_locator) )
	dest.append( ('poland_locator', poland_locator) )
	dest.append( ('ireland_locator', ireland_locator) )
	dest.append( ('unitedkingdom_locator', unitedkingdom_locator) )
	dest.append( ('greece_locator', greece_locator) )
	dest.append( ('zambia_locator', zambia_locator) )
	dest.append( ('sierraleone_locator', sierraleone_locator) )
	dest.append( ('guinea_locator', guinea_locator) )
	dest.append( ('liberia_locator', liberia_locator) )
	dest.append( ('centralafricanrepublic_locator', centralafricanrepublic_locator) )
	dest.append( ('sudan_locator', sudan_locator) )
	dest.append( ('djibouti_locator', djibouti_locator) )
	dest.append( ('eritrea_locator', eritrea_locator) )
	dest.append( ('austria_locator', austria_locator) )
	dest.append( ('iraq_locator', iraq_locator) )
	dest.append( ('italy_locator', italy_locator) )
	dest.append( ('switzerland_locator', switzerland_locator) )
	dest.append( ('iran_locator', iran_locator) )
	dest.append( ('netherlands_locator', netherlands_locator) )
	dest.append( ('liechtenstein_locator', liechtenstein_locator) )
	dest.append( ('ivorycoast_locator', ivorycoast_locator) )
	dest.append( ('republicofserbia_locator', republicofserbia_locator) )
	dest.append( ('mali_locator', mali_locator) )
	dest.append( ('senegal_locator', senegal_locator) )
	dest.append( ('nigeria_locator', nigeria_locator) )
	dest.append( ('benin_locator', benin_locator) )
	dest.append( ('angola_locator', angola_locator) )
	dest.append( ('croatia_locator', croatia_locator) )
	dest.append( ('slovenia_locator', slovenia_locator) )
	dest.append( ('qatar_locator', qatar_locator) )
	dest.append( ('saudiarabia_locator', saudiarabia_locator) )
	dest.append( ('botswana_locator', botswana_locator) )
	dest.append( ('zimbabwe_locator', zimbabwe_locator) )
	dest.append( ('bulgaria_locator', bulgaria_locator) )
	dest.append( ('thailand_locator', thailand_locator) )
	dest.append( ('sanmarino_locator', sanmarino_locator) )
	dest.append( ('haiti_locator', haiti_locator) )
	dest.append( ('dominicanrepublic_locator', dominicanrepublic_locator) )
	dest.append( ('chad_locator', chad_locator) )
	dest.append( ('kuwait_locator', kuwait_locator) )
	dest.append( ('elsalvador_locator', elsalvador_locator) )
	dest.append( ('guatemala_locator', guatemala_locator) )
	dest.append( ('easttimor_locator', easttimor_locator) )
	dest.append( ('brunei_locator', brunei_locator) )
	dest.append( ('monaco_locator', monaco_locator) )
	dest.append( ('algeria_locator', algeria_locator) )
	dest.append( ('mozambique_locator', mozambique_locator) )
	dest.append( ('eswatini_locator', eswatini_locator) )
	dest.append( ('burundi_locator', burundi_locator) )
	dest.append( ('rwanda_locator', rwanda_locator) )
	dest.append( ('myanmar_locator', myanmar_locator) )
	dest.append( ('bangladesh_locator', bangladesh_locator) )
	dest.append( ('andorra_locator', andorra_locator) )
	dest.append( ('afghanistan_locator', afghanistan_locator) )
	dest.append( ('montenegro_locator', montenegro_locator) )
	dest.append( ('bosniaandherzegovina_locator', bosniaandherzegovina_locator) )
	dest.append( ('uganda_locator', uganda_locator) )
	dest.append( ('usnavalbaseguantanamobay_locator', usnavalbaseguantanamobay_locator) )
	dest.append( ('cuba_locator', cuba_locator) )
	dest.append( ('honduras_locator', honduras_locator) )
	dest.append( ('ecuador_locator', ecuador_locator) )
	dest.append( ('colombia_locator', colombia_locator) )
	dest.append( ('paraguay_locator', paraguay_locator) )
	dest.append( ('portugal_locator', portugal_locator) )
	dest.append( ('moldova_locator', moldova_locator) )
	dest.append( ('turkmenistan_locator', turkmenistan_locator) )
	dest.append( ('jordan_locator', jordan_locator) )
	dest.append( ('nepal_locator', nepal_locator) )
	dest.append( ('lesotho_locator', lesotho_locator) )
	dest.append( ('cameroon_locator', cameroon_locator) )
	dest.append( ('gabon_locator', gabon_locator) )
	dest.append( ('niger_locator', niger_locator) )
	dest.append( ('burkinafaso_locator', burkinafaso_locator) )
	dest.append( ('togo_locator', togo_locator) )
	dest.append( ('ghana_locator', ghana_locator) )
	dest.append( ('guineabissau_locator', guineabissau_locator) )
	dest.append( ('gibraltar_locator', gibraltar_locator) )
	dest.append( ('unitedstatesofamerica_locator', unitedstatesofamerica_locator) )
	dest.append( ('canada_locator', canada_locator) )
	dest.append( ('mexico_locator', mexico_locator) )
	dest.append( ('belize_locator', belize_locator) )
	dest.append( ('panama_locator', panama_locator) )
	dest.append( ('venezuela_locator', venezuela_locator) )
	dest.append( ('papuanewguinea_locator', papuanewguinea_locator) )
	dest.append( ('egypt_locator', egypt_locator) )
	dest.append( ('yemen_locator', yemen_locator) )
	dest.append( ('mauritania_locator', mauritania_locator) )
	dest.append( ('equatorialguinea_locator', equatorialguinea_locator) )
	dest.append( ('gambia_locator', gambia_locator) )
	dest.append( ('hongkongsar_locator', hongkongsar_locator) )
	dest.append( ('vatican_locator', vatican_locator) )
	dest.append( ('northerncyprus_locator', northerncyprus_locator) )
	dest.append( ('cyprusnomansarea_locator', cyprusnomansarea_locator) )
	dest.append( ('siachenglacier_locator', siachenglacier_locator) )
	dest.append( ('baykonurcosmodrome_locator', baykonurcosmodrome_locator) )
	dest.append( ('akrotirisovereignbasearea_locator', akrotirisovereignbasearea_locator) )
	dest.append( ('antarctica_locator', antarctica_locator) )
	dest.append( ('australia_locator', australia_locator) )
	dest.append( ('greenland_locator', greenland_locator) )
	dest.append( ('fiji_locator', fiji_locator) )
	dest.append( ('newzealand_locator', newzealand_locator) )
	dest.append( ('newcaledonia_locator', newcaledonia_locator) )
	dest.append( ('madagascar_locator', madagascar_locator) )
	dest.append( ('philippines_locator', philippines_locator) )
	dest.append( ('srilanka_locator', srilanka_locator) )
	dest.append( ('curacao_locator', curacao_locator) )
	dest.append( ('aruba_locator', aruba_locator) )
	dest.append( ('thebahamas_locator', thebahamas_locator) )
	dest.append( ('turksandcaicosislands_locator', turksandcaicosislands_locator) )
	dest.append( ('taiwan_locator', taiwan_locator) )
	dest.append( ('japan_locator', japan_locator) )
	dest.append( ('saintpierreandmiquelon_locator', saintpierreandmiquelon_locator) )
	dest.append( ('iceland_locator', iceland_locator) )
	dest.append( ('pitcairnislands_locator', pitcairnislands_locator) )
	dest.append( ('frenchpolynesia_locator', frenchpolynesia_locator) )
	dest.append( ('frenchsouthernandantarcticlands_locator', frenchsouthernandantarcticlands_locator) )
	dest.append( ('seychelles_locator', seychelles_locator) )
	dest.append( ('kiribati_locator', kiribati_locator) )
	dest.append( ('marshallislands_locator', marshallislands_locator) )
	dest.append( ('trinidadandtobago_locator', trinidadandtobago_locator) )
	dest.append( ('grenada_locator', grenada_locator) )
	dest.append( ('saintvincentandthegrenadines_locator', saintvincentandthegrenadines_locator) )
	dest.append( ('barbados_locator', barbados_locator) )
	dest.append( ('saintlucia_locator', saintlucia_locator) )
	dest.append( ('dominica_locator', dominica_locator) )
	dest.append( ('unitedstatesminoroutlyingislands_locator', unitedstatesminoroutlyingislands_locator) )
	dest.append( ('montserrat_locator', montserrat_locator) )
	dest.append( ('antiguaandbarbuda_locator', antiguaandbarbuda_locator) )
	dest.append( ('saintkittsandnevis_locator', saintkittsandnevis_locator) )
	dest.append( ('unitedstatesvirginislands_locator', unitedstatesvirginislands_locator) )
	dest.append( ('saintbarthelemy_locator', saintbarthelemy_locator) )
	dest.append( ('puertorico_locator', puertorico_locator) )
	dest.append( ('anguilla_locator', anguilla_locator) )
	dest.append( ('britishvirginislands_locator', britishvirginislands_locator) )
	dest.append( ('jamaica_locator', jamaica_locator) )
	dest.append( ('caymanislands_locator', caymanislands_locator) )
	dest.append( ('bermuda_locator', bermuda_locator) )
	dest.append( ('heardislandandmcdonaldislands_locator', heardislandandmcdonaldislands_locator) )
	dest.append( ('sainthelena_locator', sainthelena_locator) )
	dest.append( ('mauritius_locator', mauritius_locator) )
	dest.append( ('comoros_locator', comoros_locator) )
	dest.append( ('saotomeandprincipe_locator', saotomeandprincipe_locator) )
	dest.append( ('caboverde_locator', caboverde_locator) )
	dest.append( ('malta_locator', malta_locator) )
	dest.append( ('jersey_locator', jersey_locator) )
	dest.append( ('guernsey_locator', guernsey_locator) )
	dest.append( ('isleofman_locator', isleofman_locator) )
	dest.append( ('aland_locator', aland_locator) )
	dest.append( ('faroeislands_locator', faroeislands_locator) )
	dest.append( ('indianoceanterritories_locator', indianoceanterritories_locator) )
	dest.append( ('britishindianoceanterritory_locator', britishindianoceanterritory_locator) )
	dest.append( ('singapore_locator', singapore_locator) )
	dest.append( ('norfolkisland_locator', norfolkisland_locator) )
	dest.append( ('cookislands_locator', cookislands_locator) )
	dest.append( ('tonga_locator', tonga_locator) )
	dest.append( ('wallisandfutuna_locator', wallisandfutuna_locator) )
	dest.append( ('samoa_locator', samoa_locator) )
	dest.append( ('solomonislands_locator', solomonislands_locator) )
	dest.append( ('tuvalu_locator', tuvalu_locator) )
	dest.append( ('maldives_locator', maldives_locator) )
	dest.append( ('nauru_locator', nauru_locator) )
	dest.append( ('federatedstatesofmicronesia_locator', federatedstatesofmicronesia_locator) )
	dest.append( ('southgeorgiaandtheislands_locator', southgeorgiaandtheislands_locator) )
	dest.append( ('falklandislands_locator', falklandislands_locator) )
	dest.append( ('vanuatu_locator', vanuatu_locator) )
	dest.append( ('niue_locator', niue_locator) )
	dest.append( ('americansamoa_locator', americansamoa_locator) )
	dest.append( ('palau_locator', palau_locator) )
	dest.append( ('guam_locator', guam_locator) )
	dest.append( ('northernmarianaislands_locator', northernmarianaislands_locator) )
	dest.append( ('bahrain_locator', bahrain_locator) )
	dest.append( ('coralseaislands_locator', coralseaislands_locator) )
	dest.append( ('spratlyislands_locator', spratlyislands_locator) )
	dest.append( ('clippertonisland_locator', clippertonisland_locator) )
	dest.append( ('macaosar_locator', macaosar_locator) )
	dest.append( ('ashmoreandcartierislands_locator', ashmoreandcartierislands_locator) )
	dest.append( ('bajonuevobank_locator', bajonuevobank_locator) )
	dest.append( ('serranillabank_locator', serranillabank_locator) )
	dest.append( ('scarboroughreef_locator', scarboroughreef_locator) )


def runparams(params):
	overrides={}
	output=Output()
	locators=[]
	addlocators(locators)
	overrides['cmdline']='./pythonshp.py '+' '.join(params)

	for param in params:
		if param=='check':
			global isverbose_global
			isverbose_global=True
			Install()
		elif param=='verbose':
			isverbose_global=True
		elif param=='publicdomain':
			overrides['copyright']='COPYRIGHT: THIS SVG FILE IS RELEASED INTO THE PUBLIC DOMAIN'
		elif param=='list':
			locators.sort()
			for l in locators:
				print('%s'%l[0])
		elif param=='bg':
			overrides['bgcolor']='#b4b4b4'
		elif param=='test':
			lonlat_test()
		elif param=='help':
			print('Usage: ./pythonshp.py command1 command2 command3 ...')
			print('Commands:')
			print('\tcheck            : show file locations and enable verbose messages')
			print('\tverbose          : print status messages')
			print('\tpublicdomain     : add PD copyright notice in output')
			print('\tlist             : list output commands')
			print('\tbg               : print background color')
			print('\t[OUTPUT COMMAND] : print a map from the output list')
			print('Example: "./pythonshp.py check laos_locator | inkscape -e laos.png -"')
		else:
			for l in locators:
				if param==l[0]:
					l[1](output,overrides)
					return
			print('Unknown parameter "%s"'%param)

if len(sys.argv)<2: runparams(['help'])
else: runparams(sys.argv[1:])
