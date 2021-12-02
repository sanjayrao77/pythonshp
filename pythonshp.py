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

## To learn about this code, please see "codeguide.txt" in my github repo

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
def patchtype_tostring(p):
	if p==NONE_PATCHTYPE: return ''
	if p==HEMI_PATCHTYPE: return 'HEMI'
	if p==VERT_PATCHTYPE: return 'VERT'
	if p==HORIZ_PATCHTYPE: return 'HORIZ'
	return 'UNK'

NONE_CCWTYPE=0
REVERSE_CCWTYPE=1 # lakes, ccws are water
HOLE_CCWTYPE=2 # Lesotho, hole in a shape
CW_CCWTYPE=3 # force CW even if CCW
def ccwtype_tostring(c):
	if c==NONE_CCWTYPE: return 'NONE'
	if c==REVERSE_CCWTYPE: return 'REVERSE'
	if c==HOLE_CCWTYPE: return 'HOLE'
	if c==CW_CCWTYPE: return 'CW'
	return 'UNK'

M_PI_2=math.pi/2.0
M_PI_4=math.pi/4.0
M_3PI_2=math.pi+M_PI_2

isverbose_global=False
ispartlabeltop_global=True
debug_global=0

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

class OutputPath():
	def __init__(self,cssclass):
		self.cssclass=cssclass
		self.dlists=[]
		self.size=0
	def addd(self,dstring):
		self.size+=len(dstring)
		self.dlists.append(dstring)
	def write(self,output):
		output.rawprint('<path class="%s" d="'%self.cssclass)
		for d in self.dlists:
			output.rawprint(d)
		output.rawprint('"/>\n')
	def isopen(self,cssclass):
		if self.cssclass!=cssclass: return False
		if self.size>2000: return False
		return True

class Output():
	def __init__(self):
		self.file=sys.stdout
		self.path=None
	def flush(self):
		self.path_flush()
	def setfile(self,outf):
		self.file=outf
	def rawprint(self,s):
		print(s,file=self.file,end='')
	def print(self,s):
		self.flush()
		self.rawprint(s)
		self.rawprint('\n')
	def print0(self,s):
		self.flush()
		self.rawprint(s)
	def newpath(self,cssclass):
		if self.path:
			if self.path.isopen(cssclass):
				return
			self.path_flush()
		self.path=OutputPath(cssclass)
	def addtopath(self,dstring):
		self.path.addd(dstring)
	def path_flush(self):
		if not self.path: return
		self.path.write(self)
		self.path=None
		

class Mbr():
	def __init__(self):
		self.isset=False
	def __str__(self):
		if not self.isset: return 'not set'
		return 'mbr: minx:%f, miny:%f, maxx:%f, maxy:%f'%(self.minx,self.miny,self.maxx,self.maxy)
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
	def print(self): print(str(self))

class DegLonLat():
	@staticmethod
	def issame(one,two):
		if one.lon==two.lon and one.lat==two.lat: return True
		return False
	@staticmethod
	def isclose(one,two):
		if abs(one.lon-two.lon)<0.0001 and abs(one.lat-two.lat)<0.0001: return True
		return False
	def __init__(self,lon,lat,side=0,patchtype=NONE_PATCHTYPE):
		self.lon=lon
		self.lat=lat
		self.side=side
		self.patchtype=patchtype
	def __str__(self):
		return '(%f,%f)'%(self.lon,self.lat)
	def print(self):
		print('( %.12f,%.12f )'%(self.lon,self.lat))
	def clone(self):
		return DegLonLat(self.lon,self.lat,self.side,self.patchtype)
	def isinmbr(self,mbr):
		if self.lon<mbr.minx: return False
		if self.lon>mbr.maxx: return False
		if self.lat<mbr.miny: return False
		if self.lat>mbr.maxy: return False
		return True

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
	def make(shape,pointstart,pointlimit,index,partindex,ccwtype=NONE_CCWTYPE):
		pg=Polygon(index,partindex,ccwtype)
		for i in range(pointstart,pointlimit):
			p=shape.pointlist[i]
			pg.addDegLonLat(p)
		pg.finish()
		return pg
	@staticmethod
	def makecheap(points):
		pg=Polygon(0,0,0)
		pg.points=points
		return pg
	@staticmethod
	def makefrompoints(points,iscw,index,partindex):
		pg=Polygon(index,partindex)
		pg.points=points
		pg.iscw=iscw
		pg.finish0()
		return pg
	@staticmethod
	def makefromshape(shape,partindex): # untested
		(start,limit)=Shape.getpartstartlimit(shape,partindex)
		ccwtype=shape.ccwtypes.get(partindex,NONE_CCWTYPE)
		return Polygon.make(shape,start,limit,shape.index,partindex,ccwtype)
	@staticmethod
	def issame(pg1,pg2):
		num=len(pg1.points)
		if num!=len(pg2.points): return False
		for i in range(num):
			for j in range(num):
				k=(i+j)%num
				if not DegLonLat.issame(pg1.points[j],pg2.points[k]): break
			else: return True
		return False
	@staticmethod
	def isclose(pg1,pg2):
		num=len(pg1.points)
		if num!=len(pg2.points): return False
		for i in range(num):
			for j in range(num):
				k=(i+j)%num
				if not DegLonLat.isclose(pg1.points[j],pg2.points[k]): break
			else: return True
		return False
	@staticmethod
	def merge(pg1,index1,pg2,index2):
		pg1len=len(pg1.points)
		pg2len=len(pg2.points)
		if pg1len==1: return None
		if pg2len==1: return None
		if Polygon.isclose(pg1,pg2): return None
		if pg1.iscw!=pg2.iscw: raise ValueError
		pg1l=(index1-1)%pg1len
		pg1r=(index1+1)%pg1len
		pg2l=(index2-1)%pg2len
		pg2r=(index2+1)%pg2len
#		print('merge start pg1len:%d pg1l:%d index1:%d pg1r:%d pg2len:%d pg2l:%d index2:%d pg2r:%d'%(pg1len,pg1l,index1,pg1r,pg2len,pg2l,index2,pg2r),file=sys.stderr)
		while DegLonLat.isclose(pg1.points[pg1l],pg2.points[pg2r]):
			pg1l=(pg1l-1)%pg1len
			if pg1l==index1: raise ValueError
			pg2r=(pg2r+1)%pg2len
		while DegLonLat.isclose(pg1.points[pg1r],pg2.points[pg2l]):
			pg1r=(pg1r+1)%pg1len
			if pg1r==index1: raise ValueError
			pg2l=(pg2l-1)%pg2len
		xpoints=[]
		i=pg1l
		while True:
			xpoints.append(pg1.points[i])
			if i==pg1r: break
			i=(i+1)%pg1len
		pl=Polyline.makefrompoints(xpoints,0,0)
		points=[]
		i=pg1r-1
		while True:
			points.append(pg1.points[i])
			if i==pg1l: break
			i=(i+1)%pg1len
		i=pg2r-1
		while True:
			points.append(pg2.points[i])
			if i==pg2l: break
			i=(i+1)%pg2len
		pg=Polygon.makefrompoints(points,pg1.iscw,0,0)
#		print('merge stop pg1len:%d pg1l:%d index1:%d pg1r:%d pg2len:%d pg2l:%d index2:%d pg2r:%d'%(pg1len,pg1l,index1,pg1r,pg2len,pg2l,index2,pg2r),file=sys.stderr)
#		print('merge stop pglen:%d xpointslen:%d'%(len(points),len(xpoints)),file=sys.stderr)
		return (pg,pl)
	@staticmethod
	def close_findintersection(pg1,pg2):
		for i in range(len(pg1.points)):
			p=pg1.points[i]
			for j in range(len(pg2.points)):
				q=pg2.points[j]
				if DegLonLat.isclose(p,q): return (i,j)
	@staticmethod
	def exact_findintersection(pg1,pg2):
		lons={}
		for i in range(len(pg1.points)):
			p=pg1.points[i]
			lon=p.lon
			lat=p.lat
			if lon in lons:
				lats=lons[lon]
				lats[lat]=(i)
			else:
				lats={}
				lats[lat]=i
				lons[lon]=lats
		for j in range(len(pg2.points)):
			q=pg2.points[j]
			lon=q.lon
			lat=q.lat
			if not lon in lons: continue
			lats=lons[lon]
			if not lat in lats: continue
			return (lats[lat],j)
	def __init__(self,index,partindex,ccwtype=NONE_CCWTYPE):
		self.points=[]
		self.index=index
		self.partindex=partindex
		self.ccwtype=ccwtype
		self.iscw=None
		if ccwtype==CW_CCWTYPE: self.iscw=True
	def addDegLonLat(self,p):
		if 0==len(self.points): self.points.append(p)
		else:
			lp=self.points[-1]
			if p.lon!=lp.lon or p.lat!=lp.lat: self.points.append(p)
	def finish0(self):
		lp=self.points[-1]
		fp=self.points[0]
		if fp.lon==lp.lon and fp.lat==lp.lat: self.points.pop()
	def finish(self):
		if not len(self.points):
			self.iscw=True
			return
		self.finish0()
		if self.iscw==None: self.iscw=self._iscw()
	def print(self,index,dopoints):
		print('polygon %d: %d iscw:%s'%(index,len(self.points),self.iscw),file=sys.stdout)
		if dopoints:
			for p in self.points:
				print('%.12f,%.12f'%(p.lon,p.lat),file=sys.stdout)
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
	@staticmethod
	def make(shape,pointstart,pointlimit,index,partindex):
		pl=Polyline(index,partindex)
		for i in range(pointstart,pointlimit):
			p=shape.pointlist[i]
			pl.addDegLonLat(p)
		return pl
	@staticmethod
	def makefrompoints(points,index,partindex):
		pl=Polyline(index,partindex)
		pl.points=points
		return pl
	@staticmethod
	def makefromlonlats(lonlats,index,partindex):
		pl=Polyline(index,partindex)
		for p in lonlats:
			dll=DegLonLat(p[0],p[1])
			pl.addDegLonLat(dll)
		return pl
	def __init__(self,index,partindex):
		self.points=[]
		self.index=index
		self.partindex=partindex
	def addDegLonLat(self,p):
		if 0==len(self.points): self.points.append(p)
		else:
			lp=self.points[-1]
			if p.lon!=lp.lon or p.lat!=lp.lat: self.points.append(p)
	def print(self,index):
		print('polyline '+str(index)+': '+str(len(self.points)))

class ShapePlus():
	@staticmethod
	def make(shape):
		if shape.type==POLYGON_TYPE_SHP:
			ret=[]
			sp=None
			for i in range(shape.partscount):
				(start,limit)=Shape.getpartstartlimit(shape,i)
				if start!=limit:
					ccwtype=shape.ccwtypes.get(i,NONE_CCWTYPE)
					pg=Polygon.make(shape,start,limit,shape.index,i,ccwtype)
					pg.partindex=i
					if pg.iscw:
						sp=ShapePlus(shape.draworderlist[i],shape)
						sp.type=POLYGON_TYPE_SHP
						sp.polygons=[pg]
						ret.append(sp)
					else:
						if sp==None:
							shape.print()
							raise ValueError('Unexpected ccw w/o preceding cw in shape index:',shape.index)
						sp.polygons.append(pg)
			return ret
		elif shape.type==POLYLINE_TYPE_SHP:
			ret=[]
			for i in range(shape.partscount):
				(start,limit)=Shape.getpartstartlimit(shape,i)
				if start!=limit:
					pl=Polyline.make(shape,start,limit,shape.index,i)
					pl.partindex=i
					sp=ShapePlus(shape.draworderlist[i],shape)
					sp.type=POLYLINE_TYPE_SHP
					sp.polylines=[pl]
					ret.append(sp)
			return ret
		elif shape.type==POINT_TYPE_SHP:
			sp=ShapePlus(shape.draworder,shape)
			sp.type=POINT_TYPE_SHP
			sp.point=shape.point
			return [sp]
		elif shape.type==NULL_TYPE_SHP:
			return []
		else: raise ValueError
	@staticmethod
	def makefrompolylines(pls,draworder):
		sp=ShapePlus(draworder,None)
		sp.type=POLYLINE_TYPE_SHP
		sp.polylines=pls
		return sp
	@staticmethod
	def makefrompolyline(pl,draworder): return ShapePlus.makefrompolylines([pl],draworder)
	@staticmethod
	def makefrompolygons(pgs,draworder):
		sp=ShapePlus(draworder,None)
		sp.type=POLYGON_TYPE_SHP
		sp.polygons=pgs
		return sp
	@staticmethod
	def makefrompolygon(pg,draworder): return ShapePlus.makefrompolygons([pg],draworder)
	@staticmethod
	def makefromdll(dll,draworder):
		sp=ShapePlus(draworder,None)
		sp.type=POINT_TYPE_SHP
		sp.point=dll
		return sp
	@staticmethod
	def pickbiggest(pluses):
		highp=None
		highc=0
		for pl in pluses:
			c=len(pl.polygons[0].points)
			if c>highc:
				highc=c
				highp=pl
		return highp
	@staticmethod
	def makeflatbox(ispolygon):
		shape=Shape(0,0)
		if ispolygon: shape.type=POLYGON_TYPE_SHP
		else: shape.type=POLYLINE_TYPE_SHP
		shape.partlist=[0]
		shape.draworderlist=[0]
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
		else: px=Polyline.make(shape,0,shape.pointscount,0,0)
		px.partindex=0
		sp=ShapePlus(0,None)
		sp.type=shape.type
		if ispolygon: sp.polygons=[px]
		else: sp.polylines=[px]
		return sp
	def __init__(self,draworder,shape):
		self.draworder=draworder
		self.shape=shape
	def print(self):
		if self.type==POLYGON_TYPE_SHP:
			print('Polygon, count: %d'%len(self.polygons),file=sys.stdout)
			for i in range(len(self.polygons)):
				self.polygons[i].print(i,True)
		elif self.type==POLYLINE_TYPE_SHP:
			print('Polyline, count: %d'%len(self.polylines),file=sys.stdout)
	def ispartindex(self,partindex):
		if partindex==-1: return True
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons:
				if pg.partindex==partindex: return True
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines:
				if pl.partindex==partindex: return True
		return False
	def toshape(self):
		if self.type!=POLYGON_TYPE_SHP: raise ValueError # unimp
		shape=Shape(-1,-1)
		shape.type=POLYGON_TYPE_SHP
		shape.ccwtypes={}
		shape.partlist=[]
		shape.pointlist=[]
		shape.draworderlist=[]
		for pg in self.polygons:
			shape.partlist.append(len(shape.pointlist))
			shape.pointlist+=pg.points
		shape.mbr=None # TODO
		shape.partscount=len(shape.partlist)
		shape.pointscount=len(shape.pointlist)
		return shape
	def augment(self,cand,isexact): # this is mostly replaced with ShapeCompress
		if cand.type!=POLYGON_TYPE_SHP: return None
		pg1=self.polygons[0]
		pg2=cand.polygons[0]
		if isexact: r=Polygon.exact_findintersection(pg1,pg2)
		else: r=Polygon.close_findintersection(pg1,pg2)
		if not r:
#			print('augment: no intersection found %d and %d'%(len(pg1.points),len(pg2.points)),file=sys.stderr)
			return None
		mret=Polygon.merge(pg1,r[0],pg2,r[1])
		if not mret:
#			print('augment: no merge returned',file=sys.stderr)
			return None
		self.polygons[0]=mret[0]
		for i in range(1,len(cand.polygons)): self.polygons.append(cand.polygons[i])
		return mret[1]

class ShapePolyline():
	@staticmethod
	def makelat(index,shapenumber,deg):
		sp=ShapePolyline(index,shapenumber)
		lon=-180.0
		while True:
			sp.addpoint(lon,deg)
			lon+=0.1
			if lon>180.0: break
		return sp
	@staticmethod
	def makelon(index,shapenumber,deg):
		sp=ShapePolyline(index,shapenumber)
		lat=90.0
		while True:
			sp.addpoint(deg,lat)
			lat-=0.1
			if lat<-90.0: break
		return sp
	def __init__(self,index,shapenumber):
		self.index=index
		self.number=shapenumber
		self.draworder=0
		self.type=POLYLINE_TYPE_SHP
		self.partlist=[0]
		self.pointlist=[]
		self.draworderlist=[0]
		self.partscount=1
		self.pointscount=0
	def addpoint(self,lon,lat):
		p=DegLonLat(lon,lat)
		self.pointlist.append(p)
		self.pointscount+=1

class Shape():
	@staticmethod
	def getpartstartlimit(shape,partindex):
		limit=shape.pointscount
		if partindex+1<shape.partscount: limit=shape.partlist[partindex+1]
		start=shape.partlist[partindex]
		return (start,limit)
	@staticmethod
	def make(index,shapenumber,shapedata):
		ret=Shape(index,shapenumber)
		ret.type=uint32_little(shapedata,0)
		if ret.type==POLYGON_TYPE_SHP or ret.type==POLYLINE_TYPE_SHP: # polygon or polyline
			ret.ccwtypes={} # ccwtypes[index]=XX_CCWTYPE
			ret.partlist=[]
			ret.pointlist=[]
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
			ret.draworder=0
		elif ret.type==NULL_TYPE_SHP:
			offset+=4
		else:
			raise ValueError
		return ret
	def __init__(self,index,shapenumber):
		self.index=index
		self.number=shapenumber
	def setdraworder(self,partidx,draworder):
		if partidx<0:
			if hasattr(self,'draworder'): self.draworder=draworder
			if hasattr(self,'draworderlist'):
				for i in range(len(self.draworderlist)):
					self.draworderlist[i]=draworder
		else:
			if partidx<self.partscount:
				self.draworderlist[partidx]=draworder
	def print(self,prefix=''):
		print('%snumber: %d, shape: %s, parts: %d, points: %d'%(prefix,self.number,shapename(self.type),self.partscount,self.pointscount))
		if True:
			for i in range(self.partscount):
				j=self.partlist[i]
				k=self.pointscount
				if i+1<self.partscount: k=self.partlist[i+1]
#				if True: if self.pointlist[j].lon>-77: continue
				if self.type==POLYGON_TYPE_SHP:
					pg=Polygon.make(self,j,k,0,0)
					print('%d: %d points (%d..%d), iscw:%s'%(i,k-j,j,k,pg.iscw))
				else:
					print('%d: %d points (%d..%d)'%(i,k-j,j,k))
				if True:
					for l in range(j,k):
						p=self.pointlist[l]
						p.print()
	def printparts(self,prefix='',file=sys.stdout):
		print('%snumber: %d, shape: %s, parts: %d, points: %d'%(prefix,self.number,shapename(self.type),self.partscount,self.pointscount),file=file)
		for i in range(self.partscount):
			j=self.partlist[i]
			k=self.pointscount
			if i+1<self.partscount: k=self.partlist[i+1]
#				if True: if self.pointlist[j].lon>-77: continue
			if self.type==POLYGON_TYPE_SHP:
				pg=Polygon.make(self,j,k,0,0)
				print('%d: %d points (%d..%d), iscw:%s'%(i,k-j,j,k,pg.iscw),file=file)
			else:
				print('%d: %d points (%d..%d)'%(i,k-j,j,k),file=file)
	def removepoints(self,start,count): # points shouldn't cross parts # TODO remove this
		del self.pointlist[start:start+count]
		self.pointscount-=count
		for i in range(self.partscount):
			if self.partlist[i]>start: self.partlist[i]-=count
	def getmbr(self,partindices):
		mbr=Mbr()
		for partidx in partindices:
			if partidx<0:
				for p in self.pointlist: mbr.add(p.lon,p.lat)
			else:
				limit=self.pointscount
				if partidx+1<self.partscount: limit=self.partlist[partidx+1]
				for ptidx in range(self.partlist[partidx],limit):
					p=self.pointlist[ptidx]
					mbr.add(p.lon,p.lat)
		return mbr
	def getcenter(self,partindices):
		mbr=self.getmbr(partindices)
		if not mbr.isset: raise ValueError
		return ((mbr.maxx+mbr.minx)/2,(mbr.maxy+mbr.miny)/2)

class Shp(): # don't try to extend shp, just store data as literally as possible
	def __init__(self,filename,installfile=None):
		self.filename=filename
		self.shapes=[]
		self.installfile=installfile
		self.bynickname={}
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
			print('%d: offset: %d, shape: %s, mbr:(%d,%d) -> (%d,%d)'%(rnumber,offset,shapename(shapetype),minx,miny,maxx,maxy))
			
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
			shape=Shape.make(index,rnumber,shapedata)
			self.shapes.append(shape)
			offset+=8+rlength
			index+=1
		f.close()
	def setdraworder(self,index,partidx,draworder):
		shape=self.shapes[index]
		shape.setdraworder(partidx,draworder)
	def resetdraworder(self):
		for shape in self.shapes:
			shape.setdraworder(-1,0)
	def getcenter(self,index,partindices): return self.shapes[index].getcenter(partindices)
	def setnickname(self,index,nickname):
		s=self.shapes[index]
		if s.nickname: del self.bynickname[s.nickname]
		s.setnickname(nickname)
		self.bynickname[nickname]=s
		

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
		self.dlat=0
		self.a=1
		self.c=0
		self.e=math.cos(rlon)
		self.f=math.sin(rlon)
	def set_deglonlat(self,dlon,dlat):
		self.isx=True
		self.isy=True
		self.dlon=dlon
		self.dlat=dlat
		rlat=(dlat*math.pi)/180.0
		rlon=(dlon*math.pi)/180.0
		self.a=math.cos(rlat)
		self.c=math.sin(rlat)
		self.e=math.cos(rlon)
		self.f=math.sin(rlon)
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
	def xyz_fromxyz(self,x,y,z):
		x2=x*self.e+y*self.f
		y2=-x*self.f+y*self.e
		z2=z
		x=x2*self.a+z2*self.c
		y=y2
		z=-x2*self.c+z2*self.a
		return (x,y,z)

class SpherePoint():
	@staticmethod
	def makefromcircle(angledeg,rotation):
		sp=SpherePoint()
		sp.patchtype=NONE_PATCHTYPE
		sp.side=0
		sp.lon=0
		sp.lat=0
		x=0
		anglerad=(math.pi*angledeg)/180.0
		y=math.cos(anglerad)
		z=math.sin(anglerad)
		(sp.x,sp.y,sp.z)=rotation.xyz_fromxyz(x,y,z)
		return sp
	@staticmethod
	def makefromlonlat(lon,lat,rotation):
		sp=SpherePoint()
		sp.patchtype=NONE_PATCHTYPE
		sp.side=0
		sp.lon=lon
		sp.lat=lat
		(sp.x,sp.y,sp.z)=rotation.xyz_fromdll(sp.lon,sp.lat)
		return sp
	@staticmethod
	def makefromdll(dll,rotation): # TODO call .makefromlonlat
		sp=SpherePoint()
		sp.patchtype=NONE_PATCHTYPE
		sp.side=0
		sp.lon=dll.lon
		sp.lat=dll.lat

		(sp.x,sp.y,sp.z)=rotation.xyz_fromdll(sp.lon,sp.lat)
		return sp
	def print(self,file=sys.stdout):
		print('point: %s' % (str(self)),file=file)
	def __str__(self): return '(%.1f,%.1f):(%.3f,%.3f,%.3f)%s'%(self.lon,self.lat,self.x,self.y,self.z,patchtype_tostring(self.patchtype))
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
	def flattenf(self,width,height):
		ux=((self.y+1.0)*(width-1))/2.0
		uy=((1.0-self.z)*(height-1))/2.0
		return FlatPoint(ux,uy,NONE_PATCHTYPE)
	def cleave(self,c):
		if 1!=c.setsides([self]): return self
		

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
	def distance2(ux1,uy1,ux2,uy2):
		dx=ux2-ux1
		dy=uy2-uy1
		return dx*dx+dy*dy
	@staticmethod
	def distance(ux1,uy1,ux2,uy2):
		dx=ux2-ux1
		dy=uy2-uy1
		return math.sqrt(dx*dx+dy*dy)
	def __init__(self,ux,uy,patchtype):
		self.ux=ux
		self.uy=uy
		self.patchtype=patchtype
	def __str__(self): return 'ux:%d uy:%d patchtype:%s'%(self.ux,self.uy,patchtype_tostring(self.patchtype))
	def distanceto(self,p):
		return FlatPoint.distance(self.ux,self.uy,p.ux,p.uy)
	def shift(self,shift):
		self.ux+=shift.xoff
		self.uy+=shift.yoff

class FlatPolygon():
	def __init__(self,iscw,index,partindex,ccwtype):
		self.points=[]
		self.iscw=iscw
		self.index=index
		self.partindex=partindex
		self.ccwtype=ccwtype
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
	def print(self,file=sys.stdout):
		print('FlatPolygon:',file=file)
		for p in self.points:
			print('point: %s'%p,file=file)

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
	def print(self,file=sys.stdout):
		print('FlatPolyline:',file=file)
		for p in self.points:
			print('point: %s'%p,file=file)

class Shift():
	def __init__(self,xoff,yoff):
		self.xoff=xoff
		self.yoff=yoff

class BoxZoomCleave():
	def __init__(self,zoomfactor,left,right,bottom,top,zoomshift=None):
		self.zoomfactor=zoomfactor
		self.left=left
		self.right=right
		self.bottom=bottom
		self.top=top
		self.zoomshift=zoomshift
	def cleave(self,onesphere):
		self.isz=False
		self.ishigh=True
		self.val=self.right
		onesphere.cleave(self)
		self.isz=False
		self.ishigh=False
		self.val=self.left
		onesphere.cleave(self)
		self.isz=True
		self.ishigh=True
		self.val=self.top
		onesphere.cleave(self)
		self.isz=True
		self.ishigh=False
		self.val=self.bottom
		onesphere.cleave(self)
	def shift(self,flatshape):
		if self.zoomshift: flatshape.shift(self.zoomshift)
	def stitchsegments(self,one,two,onecrossu,twocrossu):
		if self.isz: one.patchtype=HORIZ_PATCHTYPE
		else: one.patchtype=VERT_PATCHTYPE
		one.next=two
	def setsides(self,points):
		isz=self.isz
		ishigh=self.ishigh
		val=self.val
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
	def makeintersectionpoint(self,s,n):
		isz=self.isz
		v=self.val

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

#		print('Intersection %s to %s isz:%s v:%.2f i:%s'%(s,n,isz,v,i),file=sys.stderr)
		return i
	def setcrossus(self,intersections,spherepolygon):
		isz=self.isz
		if isz:
			for x in intersections.list: x.crossu=x.s0.y
		else:
			for x in intersections.list: x.crossu=x.s0.z

class SvgFragment():
	@staticmethod
	def isinline(x1,y1,x2,y2,x3,y3):
		dx=x3-x1
		dy=y3-y1
		if abs(dx) > abs(dy):
			dydx=dy/dx
			ey=dydx*(x2-x1)+y1
			if abs(ey-y2)<0.2: return True
		else:
			dxdy=dx/dy
			ex=dxdy*(y2-y1)+x1
			if abs(ex-x2)<0.2: return True
		return False
	@staticmethod
	def inlinecount(points,start):
		num=0
		k=len(points)
		stop=start+2
		p=points[start]
		x1=p[0]
		y1=p[1]
		startp1=start+1
		while True:
			if stop>=k: return num
			p=points[stop]
			x3=p[0]
			y3=p[1]
			if x1==x3 and y1==y3: return num
			for j in range(startp1,stop):
				p=points[j]
				if not SvgFragment.isinline(x1,y1,p[0],p[1],x3,y3): return num
			num+=1
			stop+=1
	def __init__(self):
		self.isclosed=False
		self.isreduced=False
		self.points=[]
	def reduce(self):
#		print('Reducing points: ',self.points,file=sys.stderr) #cdebug
		if self.isclosed:
			while True:
				if len(self.points)<2:
					self.points=[]
					return
				if self.points[0]==self.points[-1]:
					self.points.pop()
					continue
				break

		if True: # TODO make another version for self.isclosed
			# this always preserves first and last points, ignoring if they are inline
			k=len(self.points) -1
			i=0
			while i<k:
				j=SvgFragment.inlinecount(self.points,i)
				if j>0:
					del self.points[i+1:i+j+1]
					i+=j
					k-=j
				i+=1

class SvgPath():
	def __init__(self,cssclass):
		self.cssclass=cssclass
		self.fragments=[]
		self._addfragment()
	def _addfragment(self):
		fragment=SvgFragment()
		self.curfragment=fragment
		self.fragments.append(fragment)
	def moveto(self,x,y):
		if len(self.curfragment.points)!=0: self._addfragment()
		self.curfragment.points.append((int(x),int(y)))
	def lineto(self,x,y):
		self.curfragment.points.append((int(x),int(y)))
	def closepath(self):
		self.curfragment.isclosed=True
	def write(self,output):
		output.newpath(self.cssclass)
		for fragment in self.fragments:
			if not fragment.isreduced:
				fragment.reduce()
				fragment.isreduced=True
			points=fragment.points
			if len(points)==0: continue
			p=points[0]
			if False: # human readable for debugging #ldebug
				output.addtopath('M %d,%d'%(p[0],p[1]))
				for i in range(1,len(points)):
					p=points[i]
					output.addtopath('\n L %d,%d'%(p[0],p[1]))
			else:
				output.addtopath('M%d,%d'%(p[0],p[1]))
				for i in range(1,len(points)):
					p=points[i]
					q=points[i-1]
					if p[0]==q[0]:
						output.addtopath('v%d'%(p[1]-q[1]))
					elif p[1]==q[1]:
						output.addtopath('h%d'%(p[0]-q[0]))
					else:
						output.addtopath('l%d,%d'%(p[0]-q[0],p[1]-q[1]))
			if fragment.isclosed: output.addtopath('Z')
	def write_raw(self,output):
		output.print0('<path class=\"'+self.cssclass+'\" d=\"')
		for fragment in self.fragments:
			if not fragment.isreduced:
				fragment.reduce()
				fragment.isreduced=True
			points=fragment.points
			if len(points)==0: continue
			p=points[0]
			if True:
				output.print0('M%d,%d'%(p[0],p[1]))
				for i in range(1,len(points)):
					p=points[i]
					q=points[i-1]
					if p[0]==q[0]:
						output.print0('v%d'%(p[1]-q[1]))
					elif p[1]==q[1]:
						output.print0('h%d'%(p[0]-q[0]))
					else:
						output.print0('l%d,%d'%(p[0]-q[0],p[1]-q[1]))
			else: # human readable for debugging
				output.print0('M %d,%d'%(p[0],p[1]))
				for i in range(1,len(points)):
					p=points[i]
					output.print(' L %d,%d'%(p[0],p[1]))
			if fragment.isclosed: output.print0('Z')
		output.print('\"/>')

class SvgPolyline():
	def __init__(self,cssclass):
		self.path=SvgPath(cssclass)
		self.isfirst=True
	def addpoint(self,x,y):
		if self.isfirst:
			self.isfirst=False
			self.path.moveto(x,y)
		else:
			self.path.lineto(x,y)
	def write(self,output):
		self.path.write(output)


class FlatShape():
	@staticmethod
	def ispatch(polygons):
		for pg in polygons:
			for p in pg.points:
				if p.patchtype!=NONE_PATCHTYPE: return True
		return False
	def __init__(self):
		pass
	def print(self,file=sys.stdout):
		if self.type==POLYGON_TYPE_SHP:
			for p in self.polygons: p.print(file=file)
		elif self.type==POLYLINE_TYPE_SHP:
			for p in self.polylines: p.print(file=file)
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
	def setpoint(self,p):
		self.type=POINT_TYPE_SHP
		self.point=p
	def shift(self,shift):
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons: pg.shift(shift)
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines: pl.shift(shift)
		elif self.type==POINT_TYPE_SHP:
			self.point.shift(shift)
	def addtombr(self,mbr):
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons:
				for p in pg.points:
					mbr.add(p.ux,p.uy)
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines:
				for p in pl.points:
					mbr.add(p.ux,p.uy)
	def path_printsvg(self,output,cssclass,cssreverse):
		hasreverse=False
		svg=SvgPath(cssclass)
		i=0
		pg=self.polygons[i]
		p=pg.points[0]
		svg.moveto(p.ux,p.uy)
		for j in range(1,len(pg.points)):
			p=pg.points[j]
			svg.lineto(p.ux,p.uy)
		svg.closepath()
		while True:
			i+=1
			if i==len(self.polygons): break
			pg=self.polygons[i]
			if cssreverse and pg.ccwtype==REVERSE_CCWTYPE:
				hasreverse=True
				continue
			p=pg.points[0]
			svg.moveto(p.ux,p.uy)
			for j in range(1,len(pg.points)):
				p=pg.points[j]
				svg.lineto(p.ux,p.uy)
			svg.closepath()
		svg.write(output)
		if hasreverse:
			svg=SvgPath(cssreverse)
			for i in range(1,len(self.polygons)):
				pg=self.polygons[i]
				if pg.ccwtype!=REVERSE_CCWTYPE: continue
				p=pg.points[0]
				svg.moveto(p.ux,p.uy)
				for j in range(1,len(pg.points)):
					p=pg.points[j]
					svg.lineto(p.ux,p.uy)
				svg.closepath()
			svg.write(output)
	def border_printsvg(self,output,csspatch,cssborder):
		svg=None
		for pg in self.polygons:
			if len(pg.points)<2: continue
			p=pg.points[-1]
			isonpatch=(p.patchtype!=NONE_PATCHTYPE)
			if isonpatch:
				svg=SvgPolyline(csspatch)
			else:
				svg=SvgPolyline(cssborder)
			svg.addpoint(p.ux,p.uy)
			for p in pg.points:
				if isonpatch!=(p.patchtype!=NONE_PATCHTYPE):
					svg.addpoint(p.ux,p.uy)
					svg.write(output)
					isonpatch=(p.patchtype!=NONE_PATCHTYPE)
					if isonpatch:
						svg=SvgPolyline(csspatch)
					else:
						svg=SvgPolyline(cssborder)
				svg.addpoint(p.ux,p.uy)
			svg.write(output)
	def patch_printsvg(self,output,csspatch,reversepatch):
		svg=None
		for pg in self.polygons:
			if len(pg.points)<2: continue
			patch=csspatch
			if reversepatch and pg.ccwtype==REVERSE_CCWTYPE:
				patch=reversepatch
			p=pg.points[-1]
			isonpatch=(p.patchtype!=NONE_PATCHTYPE)
			if isonpatch:
				svg=SvgPolyline(patch)
				svg.addpoint(p.ux,p.uy)
			for p in pg.points:
				ispatch=p.patchtype!=NONE_PATCHTYPE
				if isonpatch:
					svg.addpoint(p.ux,p.uy)
					if not ispatch:
						svg.write(output)
						isonpatch=False
				else:
					if ispatch:
						svg=SvgPolyline(patch)
						svg.addpoint(p.ux,p.uy)
						isonpatch=True
			if isonpatch: svg.write(output)
	def polygon_printsvg(self,output,cssfull,csspatch,cssreverse,cssreversepatch):
		if True:
			self.path_printsvg(output,cssfull,cssreverse)
			self.patch_printsvg(output,csspatch,cssreversepatch)
		else: # TODO remove? this is cleaner on patches
			if FlatShape.ispatch(self.polygons):
				self.path_printsvg(output)
				self.border_printsvg(output)
			else:
				self.path_printsvg(output,cssfull)
	def polyline_printsvg(self,output,cssclass):
		for pl in self.polylines:
			if len(pl.points)<2: continue
			svg=SvgPolyline(cssclass)
			for p in pl.points: svg.addpoint(p.ux,p.uy)
			svg.write(output)
	def point_printsvg(self,output,cssclass):
		p=self.point
		output.print('<circle class="%s" cx="%d" cy="%d" r="4"/>'%(cssclass,p.ux,p.uy))
		
	def printsvg(self,output,cssline='line',cssfull='full',csspatch='patch',csspoint='point',cssreverse=None,cssreversepatch=None):
		if self.type==POLYGON_TYPE_SHP:
			self.polygon_printsvg(output,cssfull,csspatch,cssreverse,cssreversepatch)
		elif self.type==POLYLINE_TYPE_SHP:
			self.polyline_printsvg(output,cssline)
		elif self.type==POINT_TYPE_SHP:
			self.point_printsvg(output,csspoint)
			

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

class Intersections():
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
	def makeintersectionpoint(s,n,cleave): # this is slow but generic, best to calculate intersection instead
		fuse=100
		(px,py,pz)=(s.x,s.y,s.z)
		pside=s.side
		(qx,qy,qz)=(n.x,n.y,n.z)
		while True:
			fuse-=1
			if not fuse: raise ValueError
			x=(px+qx)/2.0
			y=(py+qy)/2.0
			z=(pz+qz)/2.0
			hh=x*x+y*y+z*z
			scale=math.sqrt(1/hh)
			nx=x*scale
			ny=y*scale
			nz=z*scale
			side=cleave.getside(nx,ny,nz)
			if not side:
				i=SpherePoint()
				i.lon=0
				i.lat=0
				i.side=0
				i.x=nx
				i.y=ny
				i.z=nz
				i.patchtype=s.patchtype
				return i
			if pside==side: (px,py,pz)=(nx,ny,nz)
			else: (qx,qy,qz)=(nx,ny,nz)
	def __init__(self,cleave,segments,limit=None):
		self.cleave=cleave
		self.list=[]
		s=segments.first # doesn't start with a side:0
		if limit==None: limit=s
		while True:
			if s.side!=s.next.side:
				(firstzero,otherzero,firstnonzero)=Intersections.sidewalkahead(s)
				if s.side!=firstnonzero.side:
					if firstzero==None:
						firstzero=cleave.makeintersectionpoint(s,firstnonzero)
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
	def sort(self): # crossu values should be set before calling this
		self.list.sort(key=self.crossukey)
	def print(self,file=sys.stderr):
		if 0==len(self.list): return
		if not hasattr(self.list[0],'crossu'):
			for x in self.list:
				print('intersection (%.6f,%.3f,%.3f) to (%.6f,%.3f,%.3f) x (%.6f,%.3f,%.3f) to (%.6f,%.3f,%.3f)' % (x.s.x,x.s.y,x.s.z, x.s0.x,x.s0.y,x.s0.z, x.n0.x,x.n0.y,x.n0.z, x.n.x,x.n.y,x.n.z),file=file)
			return
		for x in self.list:
			print('intersection (%.6f,%.2f,%.2f) to (%.6f,%.2f,%.2f) x (%.6f,%.2f,%.2f) to (%.6f,%.2f,%.2f) crossu:%.12f' % (x.s.x,x.s.y,x.s.z, x.s0.x,x.s0.y,x.s0.z, x.n0.x,x.n0.y,x.n0.z, x.n.x,x.n.y,x.n.z, x.crossu),file=file)
		for i in range(0,len(self.list)-1):
			x=self.list[i]
			y=self.list[i+1]
			if (abs(x.crossu-y.crossu)<0.00000001):
				print('Dupe Point: (%f,%f) to (%f,%f) and (%f,%f) to (%f,%f)'%(x.s.lon,x.s.lat,x.n.lon,x.n.lat,
						y.s.lon,y.s.lat,y.n.lon,y.n.lat),file=file)

class WebMercatorCleave():
	def __init__(self,isinset=False):
		self.isinset=isinset
	def cleave(self,wmshape):
		if self.isinset:
			self.ishigh=True
			self.val=83.0
			wmshape.cleave(self)
			self.ishigh=False
			self.val=-60.0
			wmshape.cleave(self)
		else:
			self.ishigh=True
			self.val=85.0
			wmshape.cleave(self)
			self.ishigh=False
			self.val=-85.0
			wmshape.cleave(self)
			
	def stitchsegments(self,one,two,onecrossu,twocrossu):
		one.patchtype=HORIZ_PATCHTYPE
		one.next=two
	def setsides(self,points):
		ishigh=self.ishigh
		val=self.val
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
	def makeintersectionpoint(self,s,n):
		v=self.val
		dx=n.lon-s.lon
		dy=n.lat-s.lat
		t=(v-s.lat)/dy

		x=s.lon+t*dx
		y=v

		i=DegLonLat(x,y)
		i.side=0
		i.patchtype=s.patchtype # s0 will change later after stitching
		return i
	def setcrossus(self,intersections,mercatorpolygon):
		for x in intersections.list: x.crossu=x.s0.lon

class HemiCleave():
	def __init__(self):
		pass
	def cleave(self,onesphere):
		onesphere.cleave(self)
	def setsides(self,points):
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
	def stitchsegments(self,one,two,onecrossu,twocrossu):
		one.patchtype=HEMI_PATCHTYPE
		one.next=two
	def makeintersectionpoint(self,s,n):
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
	@staticmethod
	def crossucalc(y,z):
		if z>=0.0: return 1.0-y # 0 to 2
		return 3.0+y # 2 to 4
	def setcrossu(self,intersections,isinterior,y,z):
		exu=HemiCleave.crossucalc(y,z)
		if isinterior:
			best=4.0
			for i in intersections.list:
				xu=HemiCleave.crossucalc(i.s0.y,i.s0.z)
				if xu<exu: d=exu-xu
				else: d=4.0+xu-exu
				if d<best: best=d
				i.crossu=xu
			for i in intersections.list:
				i.crossu-=best
				if i.crossu<0.0: i.crossu+=4.0
		else:
			for i in intersections.list:
				xu=HemiCleave.crossucalc(i.s0.y,i.s0.z)
				if xu<exu: xu+=4.0
				xu-=exu
				i.crossu=xu
	def setcrossus(self,intersections,spherepolygon):
		polygon=spherepolygon.polygon
		rotation=spherepolygon.rotation
		th=0.0
		fuse=100
		step=math.pi
		while True:
			y=math.cos(th)
			z=math.sin(th)
			(lon,lat)=rotation.dll_fromxyz(0.0,y,z)
			if not polygon.isvertex(lon,lat): # we want to avoid anything close to a vertex
				isit=polygon.isinterior(lon,lat)
#				print('Found point %f,%f to be interior:%s, theta:%f' % (lon,lat,isit,th))
				self.setcrossu(intersections,isit,y,z)
				break
			fuse-=1
			if 0==fuse: raise ValueError
			th+=step
			if th>=math.tau:
				step=step/2.0
				th=step

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
		
	def split2(self,intersections,cleave):
		n=len(intersections.list)
		i=0
		while i<n:
			one=intersections.list[i]
			two=intersections.list[i+1]
			index=one.s.ssindex
			if index!=two.s.ssindex:
				raise ValueError
			onestart=one.s
			twostart=one.n
#			one.s0.patchtype=patchtype
#			two.s0.patchtype=patchtype
#			one.s0.next=two.n0
#			two.s0.next=one.n0
			cleave.stitchsegments(one.s0,two.n0,one.crossu,two.crossu)
			cleave.stitchsegments(two.s0,one.n0,two.crossu,one.crossu)
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
	def shouldsplit(p,q,limit): # limit:4 is high quality, 8 is fine
		dx=q.ux-p.ux
		dy=q.uy-p.uy
		if dx*dx+dy*dy<limit: return False
		return True
	def __init__(self,polygon,rotation):
		self.polygon=polygon
		self.rotation=rotation
		self.points=[]
	def print(self,file=sys.stdout):
		print('polygon: '+str(len(self.points))+' iscw:'+str(self.polygon.iscw),file=file)
		for p in self.points:
			p.print(file=file)
			
	def isvertex(self,lon,lat):
		return self.polygon.isvertex(self,lon,lat)
	def flatten(self,width,height,splitlimit):
		r=FlatPolygon(self.polygon.iscw,self.polygon.index,self.polygon.partindex,self.polygon.ccwtype)
		for p in self.points:
			p.ux=int(0.5+((p.y+1.0)*(width-1))/2.0)
			p.uy=int(0.5+((1.0-p.z)*(height-1))/2.0)
		i=0
		fuse=5000 # 1000 is too few for ocean.110m on a sphere
		while True:
			p=self.points[i]
			r.addpoint(p.ux,p.uy,p.patchtype)
			if p.patchtype==HEMI_PATCHTYPE:
				q=self.points[0]
				if i+1<len(self.points): q=self.points[i+1]
				if SpherePolygon.shouldsplit(p,q,splitlimit):
					fuse-=1
					if fuse==0: raise ValueError('Too many interpolations, fuse expired')
					n=SpherePoint()

					# HEMI_PATCHTYPE is pretty generic
					x=(p.x+q.x)/2.0
					y=(p.y+q.y)/2.0
					z=(p.z+q.z)/2.0
					hh=x*x+y*y+z*z
					scale=math.sqrt(1/hh)
					n.x=x*scale
					n.y=y*scale
					n.z=z*scale

	#	there's no need to interpolate yet, that can change if we process more
	#				if p.patchtype==HORIZ_PATCHTYPE:
	#					n.y=(p.y+q.y)/2.0
	#					n.z=p.z
	#					n.x=math.sqrt(1-n.y*n.y-n.z*n.z)
	#				elif p.patchtype==VERT_PATCHTYPE:
	#					n.y=p.y
	#					n.z=(p.z+q.z)/2.0
	#					n.x=math.sqrt(1-n.y*n.y-n.z*n.z)
			
					n.patchtype=p.patchtype
					n.ux=int(0.5+((n.y+1.0)*(width-1))/2.0)
					n.uy=int(0.5+((1.0-n.z)*(height-1))/2.0)
					self.points.insert(i+1,n)
					continue
			i+=1
			if i==len(self.points): break
		return r
	def cleave(self,c):
		t=c.setsides(self.points)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points)
		intersections=Intersections(c,segments)
		c.setcrossus(intersections,self)
		intersections.sort()
#		intersections.print(file=sys.stderr) # idebug
		ss=SegmentSet(segments)
		ss.split2(intersections,c)
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
		r=FlatPolygon(self.polygon.iscw,self.polygon.index,self.polygon.partindex,self.polygon.ccwtype)
		for p in self.points:
			ux=int(0.5+((p.lon+180.0)/360.0)*widthm1)
			y=(p.lat*math.pi)/360.0 # /2
			uy=int(0.5+hheight-(hheight*math.log(math.tan(M_PI_4+y)))/math.pi)
			r.addpoint(ux,uy,p.patchtype)
		return r
	def cleave(self,c):
		t=c.setsides(self.points)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points)
		intersections=Intersections(c,segments)
		c.setcrossus(intersections,self)
		intersections.sort()
#		intersections.print(file=sys.stderr)
		ss=SegmentSet(segments)
		ss.split2(intersections,c)
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
	def cleave(self,c):
		t=c.setsides(self.points)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points,True)
		intersections=Intersections(c,segments,segments.last)
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
	def cleave(self,c):
		t=c.setsides(self.points)
		if t==1: return []
		if t==2: return [self]
		segments=Segments(self.points,True)
		intersections=Intersections(c,segments,segments.last)
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
	def print(self,file=sys.stdout):
		for x in self.polygons: x.print(file=file)
	def flatten(self,width,height,splitlimit=4):
		r=FlatShape()
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(width,height,splitlimit))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(width,height))
		elif self.type==POINT_TYPE_SHP:
			r.setpoint(self.point.flatten(width,height))
		return r
	def cleave(self,c):
		if self.type==POLYGON_TYPE_SHP:
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.cleave(c)
				for pg in r: self.polygons.append(pg) # it's important to maintain order
			if len(self.polygons)==0: self.type=NULL_TYPE_SHP
		elif self.type==POLYLINE_TYPE_SHP:
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.cleave(c)
				for pl in r: self.polylines.append(pl)
			if len(self.polylines)==0: self.type=NULL_TYPE_SHP
		elif self.type==POINT_TYPE_SHP:
			r=self.point.cleave(c)
			if not r: self.type=NULL_TYPE_SHP
			

class WebMercatorShape():
	def __init__(self,shapeplus):
		self.type=shapeplus.type
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
		r=FlatShape()
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(width,height))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(width,height))
		return r
	def cleave(self,c):
		if self.type==POLYGON_TYPE_SHP:
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.cleave(c)
				for pg in r: self.polygons.append(pg)
			oldgons=self.polygons
			self.polygons=[]
			for x in oldgons:
				r=x.cleave(c)
				for pg in r: self.polygons.append(pg)
			if len(self.polygons)==0: self.type=NULL_TYPE_SHP
		elif self.type==POLYLINE_TYPE_SHP:
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.cleave(c)
				for pg in r: self.polylines.append(pg)
			oldlines=self.polylines
			self.polylines=[]
			for x in oldlines:
				r=x.cleave(c)
				for pg in r: self.polylines.append(pg)
			if len(self.polylines)==0: self.type=NULL_TYPE_SHP

class TripelShape():
	def __init__(self,shapeplus):
		self.type=shapeplus.type
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
		r=FlatShape()
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(widthm1,heightm1))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(widthm1,heightm1))
		return r

def dll_sphere_print_svg(output,dll,rotation,width,height,csscircle,boxzoomcleave=None):
	if boxzoomcleave:
		width=width*boxzoomcleave.zoomfactor
		height=height*boxzoomcleave.zoomfactor
	hc=HemiCleave()
	oneplus=ShapePlus.makefromdll(dll,0)
	onesphere=SphereShape(oneplus,rotation)
	hc.cleave(onesphere)
	if boxzoomcleave: boxzoomcleave.cleave(onesphere)
	if onesphere.type!=NULL_TYPE_SHP:
		flatshape=onesphere.flatten(width,height)
		if boxzoomcleave: boxzoomcleave.shift(flatshape)
		flatshape.printsvg(output,csspoint=csscircle)

def text_sphere_print_svg(output,dll,text,rotation,width,height,cssfont='ft',cssfontshadow='fs',boxzoomcleave=None):
	if boxzoomcleave:
		width=width*boxzoomcleave.zoomfactor
		height=height*boxzoomcleave.zoomfactor
	hc=HemiCleave()
	oneplus=ShapePlus.makefromdll(dll,0)
	onesphere=SphereShape(oneplus,rotation)
	hc.cleave(onesphere)
	if boxzoomcleave: boxzoomcleave.cleave(onesphere)
	if onesphere.type!=NULL_TYPE_SHP:
		flatshape=onesphere.flatten(width,height)
		if boxzoomcleave: boxzoomcleave.shift(flatshape)
		p=flatshape.point
		output.print('<text x="%d" y="%d" class="%s">%s</text>'%(p.ux,p.uy,cssfontshadow,text))
		output.print('<text x="%d" y="%d" class="%s">%s</text>'%(p.ux,p.uy,cssfont,text))
		return True

def pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit,cssline=None,cssfull=None,csspatch=None,
		cssreverse=None,cssreversepatch=None,
		boxzoomcleave=None, cornercleave=None):
	if boxzoomcleave:
		width=width*boxzoomcleave.zoomfactor
		height=height*boxzoomcleave.zoomfactor
	hc=HemiCleave()

	for oneplus in pluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if cornercleave: cornercleave.cleave(onesphere)
		if boxzoomcleave: boxzoomcleave.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			flatshape=onesphere.flatten(width,height,splitlimit)
			if boxzoomcleave: boxzoomcleave.shift(flatshape)
	#		flatshape.print(file=sys.stdout) #ldebug
			flatshape.printsvg(output,
					cssline=cssline,cssfull=cssfull,csspatch=csspatch,
					cssreverse=cssreverse,cssreversepatch=cssreversepatch)

def oneplus_sphere_print_svg(output,oneplus,rotation,width,height,splitlimit,cssline=None,cssfull=None,csspatch=None,
		cssreverse=None,cssreversepatch=None,
		boxzoomcleave=None, cornercleave=None):
	pluses_sphere_print_svg(output,[oneplus],rotation,width,height,splitlimit,cssline=cssline,cssfull=cssfull,csspatch=csspatch,
		cssreverse=cssreverse,cssreversepatch=cssreversepatch,
		boxzoomcleave=boxzoomcleave,cornercleave=cornercleave)


def one_sphere_print_svg(output,one,draworder,rotation,width,height,splitlimit,cssline=None,cssfull=None,csspatch=None,
		cssreverse=None,cssreversepatch=None,
		boxzoomcleave=None, cornercleave=None,
		islabels=False):
	if boxzoomcleave:
		width=width*boxzoomcleave.zoomfactor
		height=height*boxzoomcleave.zoomfactor
	hc=HemiCleave()

	needmore=False
	if draworder==-1:
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			hc.cleave(onesphere)
			if cornercleave: cornercleave.cleave(onesphere)
			if boxzoomcleave: boxzoomcleave.cleave(onesphere)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height,splitlimit)
				if boxzoomcleave: boxzoomcleave.shift(flatshape)
				flatshape.printsvg(output,
						cssline=cssline,cssfull=cssfull,csspatch=csspatch,
						cssreverse=cssreverse,cssreversepatch=cssreversepatch)
	else:
		(has,hasmore)=one.hasdraworder(draworder)
		if not has:
			if hasmore: return True
			return False

		pluses=ShapePlus.make(one)
		for i in range(len(pluses)):
			oneplus=pluses[i]
			if oneplus.draworder==draworder:
				onesphere=SphereShape(oneplus,rotation)
				hc.cleave(onesphere)
				if cornercleave: cornercleave.cleave(onesphere)
				if boxzoomcleave: boxzoomcleave.cleave(onesphere)
				if onesphere.type!=NULL_TYPE_SHP:
					flatshape=onesphere.flatten(width,height,splitlimit)
					if boxzoomcleave: boxzoomcleave.shift(flatshape)
					flatshape.printsvg(output,
							cssline=cssline,cssfull=cssfull,csspatch=csspatch,
							cssreverse=cssreverse,cssreversepatch=cssreversepatch)
					if islabels:
						if flatshape.type==POLYGON_TYPE_SHP:
							pg=flatshape.polygons[0]
							p=pg.points[0]
							print_partlabel_svg(output,p.ux,p.uy,str(pg.partindex),0,width,height,pg.partindex,one.partscount)
			elif oneplus.draworder>draworder:needmore=True
	return needmore

def one_webmercator_print_svg(output,one,draworder,width,height,cssline,cssfull,csspatch,shift=None):
	needmore=False
	pluses=ShapePlus.make(one)

	wmc=WebMercatorCleave(False)

	for oneplus in pluses:
		if oneplus.draworder==draworder:
			onewm=WebMercatorShape(oneplus)
			wmc.cleave(onewm)
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output,cssline=cssline,cssfull=cssfull,csspatch=csspatch)
		elif oneplus.draworder>draworder: needmore=True
	return needmore

def one_inset_webmercator_print_svg(output,one,draworder,width,height,cssline,cssfull,csspatch,shift=None):
	needmore=False
	pluses=ShapePlus.make(one)
	wmc=WebMercatorCleave(False)
	for oneplus in pluses:
		if oneplus.draworder==draworder:
			onewm=WebMercatorShape(oneplus)
			wmc.cleave(onewm)
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output,cssline=cssline,cssfull=cssfull,csspatch=csspatch)
		elif oneplus.draworder>draworder: needmore=True
	return needmore

def mbr_webmercator(shp,index,partindex,width,height,shift=None):
	mbr=Mbr()
	one=shp.shapes[index]
	pluses=ShapePlus.make(one)
	wmc=WebMercatorCleave(False)
	for oneplus in pluses:
		if not oneplus.ispartindex(partindex): continue
		onewm=WebMercatorShape(oneplus)
		wmc.cleave(onewm)
		if onewm.type!=NULL_TYPE_SHP:
			flatshape=onewm.flatten(width,height)
			if shift!=None: flatshape.shift(shift)
			flatshape.addtombr(mbr)
	return mbr

def one_inset_tripel_print_svg(output,shp,one,draworder,width,height,cssline,cssfull,csspatch,shift=None):
	needmore=False
	pluses=ShapePlus.make(one)
	for oneplus in pluses:
		if oneplus.draworder==draworder:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				if shift!=None: flatshape.shift(shift)
				flatshape.printsvg(output,cssline=cssline,cssfull=cssfull,csspatch=csspatch)
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
	if len(comment)==0: return
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
	output.print('<circle cx="%s" cy="%s" r="%s" fill="url(#watergradient)"/>' % (rs,rs,rs))
def print_squarewater_svg(output,length,fill="#5685a2"):
	output.print('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>'%(length,length,fill))
def print_rectangle_svg(output,xoff,yoff,w,h,fill,opacity):
	output.print('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="%.1f"/>'%(xoff,yoff,w,h,fill,opacity))

def print_header_svg(output,width,height,opts,labelfont='14px sans',comments=None,isgradients=False):
	half=int(width/2)
	output.print('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
	output.print('<svg xmlns:svg="http://www.w3.org/2000/svg" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="%d" width="%d">' % (height,width))
	output.print('<!-- made with pythonshp (GPL): github.com/sanjayrao77/pythonshp , underlying data may come from naturalearthdata.com -->')
	if comments!=None:
		for comment in comments:
			print_comment_svg(output,comment)

	if isgradients:
		output.print('<defs>')
		output.print('	<radialGradient id="watergradient" cx="%d" cy="%d" r="%d" fx="%d" fy="%d" gradientUnits="userSpaceOnUse">'%(half,half,half,half,half))
		output.print('		<stop offset="0%" stop-color="#70add3"/>')
		output.print('		<stop offset="11%" stop-color="#6eaad0"/>')
		output.print('		<stop offset="22%" stop-color="#6ca7cc"/>')
		output.print('		<stop offset="31%" stop-color="#6ba5c9"/>')
		output.print('		<stop offset="41%" stop-color="#69a2c6"/>')
		output.print('		<stop offset="51%" stop-color="#679fc2"/>')
		output.print('		<stop offset="59%" stop-color="#669dbf"/>')
		output.print('		<stop offset="67%" stop-color="#649abc"/>')
		output.print('		<stop offset="75%" stop-color="#6297b9"/>')
		output.print('		<stop offset="81%" stop-color="#6095b6"/>')
		output.print('		<stop offset="87%" stop-color="#5f92b2"/>')
		output.print('		<stop offset="92%" stop-color="#5d8faf"/>')
		output.print('		<stop offset="95%" stop-color="#5b8dac"/>')
		output.print('		<stop offset="98%" stop-color="#598aa8"/>')
		output.print('		<stop offset="100%" stop-color="#5685a2"/>')
		output.print('	</radialGradient>')
		output.print('	<radialGradient id="landgradient" cx="%d" cy="%d" r="%d" fx="%d" fy="%d" gradientUnits="userSpaceOnUse">'%(half,half,half,half,half))
		output.print('		<stop offset="0%" stop-color="#dddddd"/>')
		output.print('		<stop offset="11%" stop-color="#d7d7d7"/>')
		output.print('		<stop offset="22%" stop-color="#d1d1d1"/>')
		output.print('		<stop offset="31%" stop-color="#cccccc"/>')
		output.print('		<stop offset="41%" stop-color="#c6c6c6"/>')
		output.print('		<stop offset="51%" stop-color="#c0c0c0"/>')
		output.print('		<stop offset="59%" stop-color="#bbbbbb"/>')
		output.print('		<stop offset="67%" stop-color="#b5b5b5"/>')
		output.print('		<stop offset="75%" stop-color="#afafaf"/>')
		output.print('		<stop offset="81%" stop-color="#aaaaaa"/>')
		output.print('		<stop offset="87%" stop-color="#a4a4a4"/>')
		output.print('		<stop offset="92%" stop-color="#9e9e9e"/>')
		output.print('		<stop offset="95%" stop-color="#999999"/>')
		output.print('		<stop offset="98%" stop-color="#939393"/>')
		output.print('		<stop offset="100%" stop-color="#888888"/>')
		output.print('	</radialGradient>')
		output.print('	<radialGradient id="bordergradient" cx="%d" cy="%d" r="%d" fx="%d" fy="%d" gradientUnits="userSpaceOnUse">'%(half,half,half,half,half))
		output.print('		<stop offset="0%" stop-color="#444444"/>')
		output.print('		<stop offset="11%" stop-color="#3f3f3f"/>')
		output.print('		<stop offset="22%" stop-color="#3a3a3a"/>')
		output.print('		<stop offset="31%" stop-color="#363636"/>')
		output.print('		<stop offset="41%" stop-color="#323232"/>')
		output.print('		<stop offset="51%" stop-color="#2d2d2d"/>')
		output.print('		<stop offset="59%" stop-color="#292929"/>')
		output.print('		<stop offset="67%" stop-color="#242424"/>')
		output.print('		<stop offset="75%" stop-color="#1f1f1f"/>')
		output.print('		<stop offset="81%" stop-color="#1b1b1b"/>')
		output.print('		<stop offset="87%" stop-color="#161616"/>')
		output.print('		<stop offset="92%" stop-color="#121212"/>')
		output.print('		<stop offset="95%" stop-color="#0e0e0e"/>')
		output.print('		<stop offset="98%" stop-color="#090909"/>')
		output.print('		<stop offset="100%" stop-color="#000000"/>')
		output.print('	</radialGradient>')
		output.print('</defs>')
	output.print('<style type="text/css">')
	output.print('<![CDATA[')

	highlight="#449944"
	highlight="#55aa44"
	highlight="#45a249"
	highlight="#45a211"
	highlight_b='#115511'
	highlight_bz='#115511'
	highlight_b='#000000'
	highlight_tb='#378100'

	if 'tc' in opts: output.print('.tc {stroke:black;fill-opacity:0}')
	if not isgradients:
		if 'sl' in opts: output.print('.sl {fill:#aaaaaa;stroke:#888888}')
		if 'sp' in opts: output.print('.sp {stroke:#aaaaaa;fill-opacity:0}')
		if 'sb' in opts: output.print('.sb {stroke:#888888;fill-opacity:0}')
		if 'sw' in opts: output.print('.sw {fill:#5685a2;stroke-opacity:0}')
		if 'sr' in opts: output.print('.sr {stroke:#5685a2;fill-opacity:0}')
	else:
		if 'sl' in opts: output.print('.sl {fill:url(#landgradient);stroke:url(#bordergradient)}')
		if 'sp' in opts: output.print('.sp {stroke:url(#landgradient);fill-opacity:0}')
		if 'sb' in opts: output.print('.sb {stroke:url(#bordergradient);fill-opacity:0}')
		if 'sw' in opts: output.print('.sw {fill:url(#watergradient);stroke:url(#watergradient);stroke-opacity:0.8}')
		if 'sr' in opts: output.print('.sr {stroke:url(#watergradient);fill-opacity:0}')
	if 'si' in opts: output.print('.si {stroke:%s;fill-opacity:0;stroke-opacity:0.3}'%highlight_b)
	if 'sh' in opts: output.print('.sh {fill:%s;stroke:%s}'%(highlight,highlight_b))
	if 'sq' in opts: output.print('.sq {stroke:%s;fill-opacity:0}'%highlight)
	if 'sh1' in opts: output.print('.sh1 {fill:%s;stroke:%s}'%(highlight,highlight_b))
	if 'sq1' in opts: output.print('.sq1 {stroke:%s;fill-opacity:0}'%highlight)

	# halflight areas
# 7aaa58
# aaaa11
	if 'al' in opts: output.print('.al {fill:#aaaa11;stroke:#707070}')
	if 'ap' in opts: output.print('.ap {stroke:#aaaa11;fill-opacity:0}')
	if 'ab' in opts: output.print('.ab {stroke:#707070;fill-opacity:0}')

	# disputed and breakaway areas
	if 'dl' in opts: output.print('.dl {fill:#11dd11;stroke:#11dd11;stroke-dasharray:3 3}')
	# disputed border
	if 'db' in opts: output.print('.db {fill:#11dd11;stroke:#11dd11;stroke-width:2;stroke-opacity:1}')
	if 'dp' in opts: output.print('.dp {stroke:#11dd11;fill-opacity:0}')
	# zoom land
	if 'dz' in opts: output.print('.dz {fill:#11dd11;stroke:#000000;stroke-dasharray:2 2}')
	# zoom border
	if 'dy' in opts: output.print('.dy {fill:#11dd11;stroke-opacity:0}')
	# zoom patch
	if 'dx' in opts: output.print('.dx {stroke:#11dd11;stroke-dasharray:3 3;fill-opacity:0}')

	# sphere lon/lat grid
	if 'sg' in opts: output.print('.sg {stroke:#000000;fill-opacity:0.0;stroke-opacity:0.2}')

	# font lon/lat shadow
	if 'fs' in opts: output.print('.fs { font:%s;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:0.9;text-anchor:middle }'%labelfont)
	# font lon/lat text
	if 'ft' in opts: output.print('.ft { font:%s;fill:#000000;fill-opacity:1;stroke-opacity:0;text-anchor:middle }'%labelfont) 


	# tripel ocean
	if 'to' in opts:
		output.print('.to {fill:#eeeeee;stroke:black}')
		if 'tb' in opts: output.print('.tb {fill:#aaaaaa;stroke:black;stroke-width:2}') # tripel background
	# tripel land
	if 'tl' in opts:
		output.print('.tl {fill:#aaaaaa;stroke:black}')
		if 'tb' in opts: output.print('.tb {fill:#eeeeee;stroke:black;stroke-width:2}') # tripel background

	# tripel lon/lat
	if 'tg' in opts: output.print('.tg {stroke:black;stroke-opacity:0.2;fill-opacity:0}')
	if 'tl1' in opts: output.print('.tl1 {fill:#dddddd;stroke:#444444}')
	# tripel patch
	if 'tp' in opts: output.print('.tp {stroke:#dddddd;fill-opacity:0}')
	if 'tp1' in opts: output.print('.tp1 {stroke:#dddddd;fill-opacity:0}')
	# trip highlight
	if 'th' in opts: output.print('.th {fill:%s;stroke:%s}'%(highlight,highlight_tb))
	if 'tq' in opts: output.print('.tq {stroke:%s;fill-opacity:0}'%highlight)

	# zoom land
	if 'zl' in opts: output.print('.zl {fill:#dddddd;stroke:#444444}')
	# zoom patch
	if 'zp' in opts: output.print('.zp {stroke:#dddddd;stroke-dasharray:3 3;fill-opacity:0}')
	# zoom border
	if 'zb' in opts: output.print('.zb {stroke:#444444;fill-opacity:0}')
	if 'debugzp' in opts: output.print('.debugzp {stroke:#00ff00;stroke-dasharray:3 3;stroke-width:2;fill-opacity:0}')
	# zoom highlight
	if 'zh' in opts: output.print('.zh {fill:%s;stroke:%s}'%(highlight,highlight_bz))
	# zoom highlight patch
	if 'zq' in opts: output.print('.zq {stroke:%s;stroke-dasharray:3 3;fill-opacity:0}'%highlight)
#	if 'zw' in opts: output.print('.zw {fill:#5685a2;stroke-opacity:0}')
	if 'zi' in opts: output.print('.zi {stroke:%s;fill-opacity:0;stroke-opacity:0.5}'%(highlight_bz))
# 0x64a8d2 * 0.9 + 0.1 * 0xdddddd = 0x70add3
	if 'zw' in opts: output.print('.zw {fill:#64a8d2;fill-opacity:0.9;stroke-opacity:0.9}')
	if 'zr' in opts: output.print('.zr {stroke:#5685a2;stroke-dasharray:3 3;fill-opacity:0}')

	if 'debugl' in opts: output.print('.debugl {stroke:#00ff00;fill-opacity:0;stroke-width:1}')
	if 'debuggreen' in opts: output.print('.debuggreen {stroke:#00ff00;fill:#005500}')
	if 'debugredline' in opts: output.print('.debugredline {stroke:#ff0000;fill-opacity:0}')

	if width==500: # circles
		if 'c1' in opts: output.print('.c1 {stroke:%s;fill-opacity:0}'%highlight)
		if 'c2' in opts: output.print('.c2 {stroke:%s;fill-opacity:0}'%highlight)
		if 'c3' in opts: output.print('.c3 {stroke:%s;fill-opacity:0;stroke-width:1.5}'%highlight)
		if 'c4' in opts: output.print('.c4 {stroke:%s;fill-opacity:0;stroke-width:2}'%highlight)
		if 'w1' in opts: output.print('.w1 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6}')
		if 'w2' in opts: output.print('.w2 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6}')
		if 'w3' in opts: output.print('.w3 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:1.5}')
		if 'w4' in opts: output.print('.w4 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:2}')
	else:
		if 'c1' in opts: output.print('.c1 {stroke:%s;fill-opacity:0}'%highlight)
		if 'c2' in opts: output.print('.c2 {stroke:%s;fill-opacity:0;stroke-width:2}'%highlight)
		if 'c3' in opts: output.print('.c3 {stroke:%s;fill-opacity:0;stroke-width:3}'%highlight)
		if 'c4' in opts: output.print('.c4 {stroke:%s;fill-opacity:0;stroke-width:4}'%highlight)
		if 'w1' in opts: output.print('.w1 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6}')
		if 'w2' in opts: output.print('.w2 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:2}')
		if 'w3' in opts: output.print('.w3 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:3}')
		if 'w4' in opts: output.print('.w4 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:4}')

	if False:
		output.print('text.shadow { font:%s;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:0.9;text-anchor:middle }'%labelfont)
		output.print('text.label { font:%s;fill:#000000;fill-opacity:1;stroke-opacity:0;text-anchor:middle }'%labelfont) 
		output.print('path.land { fill:url(#landgradient);stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.land_border { stroke:url(#bordergradient);fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.land_patch { stroke:#888888;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.land_full { fill:url(#landgradient);stroke:url(#bordergradient);fill-opacity:1.0;stroke-opacity:1.0 }')
		if issubland:
			output.print('path.subland { fill:#449944;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
			output.print('path.subland_full { fill:#449944;stroke:#338833;fill-opacity:1.0;stroke-opacity:1.0 }')
			output.print('path.subland_border { stroke:#338833;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
			output.print('path.subland_patch { stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')

		if width==500:
			output.print('circle.highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1 }')
			output.print('circle.w2_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1 }')
			output.print('circle.w3_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.5 }')
			output.print('circle.w4_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:2 }')
			output.print('circle.w_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:1 }')
			output.print('circle.w_w2_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:1 }')
			output.print('circle.w_w3_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:1.5 }')
			output.print('circle.w_w4_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:2 }')
		else:
			output.print('circle.highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0 }')
			output.print('circle.w2_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:2 }')
			output.print('circle.w3_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:3 }')
			output.print('circle.w4_highlight_land { fill:#449944;stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:4 }')
			output.print('circle.w_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6 }')
			output.print('circle.w_w2_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:2 }')
			output.print('circle.w_w3_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:3 }')
			output.print('circle.w_w4_highlight_land { fill:#449944;stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.6;stroke-width:4 }')

		output.print('path.highlight_land { fill:#449944;stroke:#000000;fill-opacity:0.0;stroke-opacity:0.0 }')
		output.print('path.highlight_land_full { fill:#449944;stroke:#115511;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.highlight_land_border { stroke:#115511;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.highlight_land_patch { stroke:#449944;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.highlight2_land { fill:#449944;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.highlight2_land_full { fill:#449944;stroke:#115511;fill-opacity:1.0;stroke-opacity:1.0 }')
		output.print('path.highlight2_land_border { stroke:#115511;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.highlight2_land_patch { stroke:#115511;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.water { fill:url(#watergradient);stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.water_full { fill:url(#watergradient);stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.water_border { stroke:url(#watergradient);fill-opacity:0.0;stroke-opacity:0.5;stroke-width:1.0 }')
		output.print('path.water_patch { stroke:url(#watergradient);fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.lonlat { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.2;stroke-width:1.0 }')
		if False:
			output.print('path.landline { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.8;stroke-width:0.5 }')
		output.print('path.landz { fill:#dddddd;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.landz_full { fill:#dddddd;stroke:#444444;fill-opacity:1.0;stroke-opacity:1.0 }')
		output.print('path.landz_border { stroke:#444444;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.landz_patch { stroke-dasharray:"3 3";stroke:#000000;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.outline { fill:#eeeeee;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.outline_full { fill:#eeeeee;stroke:#000000;fill-opacity:1.0;stroke-opacity:0.0 }')
		output.print('path.outline_border { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.0;stroke-width:1.0 }')
		output.print('path.outline_patch { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.0;stroke-width:1.0 }')
		output.print('path.landx { fill:#aaaaaa;stroke:#000000;fill-opacity:1.0;stroke-opacity:1.0 }')
		output.print('path.landx_full { fill:#aaaaaa;stroke:#aaaaaa;fill-opacity:1.0;stroke-opacity:1.0 }')
		output.print('path.landx_border { stroke:#aaaaaa;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.landx_patch { stroke:#aaaaaa;fill-opacity:0.0;stroke-opacity:1.0;stroke-width:1.0 }')
		output.print('path.lonlat3 { stroke:#000000;fill-opacity:0.0;stroke-opacity:0.2;stroke-width:1.0 }')
		if False:
			output.print('path.worldborder { fill:#000000;stroke:#000000;fill-opacity:0.0;stroke-opacity:1.0 }')
		output.print('path.worldbg_full { fill:#aaaaaa;stroke:#000000;fill-opacity:1.0;stroke-opacity:1.0;stroke-width:2 }')
		output.print('path.world_full { fill:#eeeeee;stroke:#000000;fill-opacity:1.0;stroke-opacity:1.0 }')
	
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
				nm=one_sphere_print_svg(output,one,draworder,rotation,width,height,splitlimit)
				if nm: needmore=True
		else:
			for i in ids:
				one=shp.shapes[i]
				nm=one_sphere_print_svg(output,one,draworder,rotation,width,height,splitlimit)
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
				nm=one_webmercator_print_svg(output,one,draworder,width,height)
				if nm: needmore=True
		else:
			for i in ids:
				one=shp.shapes[i]
				nm=one_webmercator_print_svg(output,one,draworder,width,height)
				if nm: needmore=True
		if not needmore: break
		draworder+=1
	print_footer_svg(output)

def print_box3d_svg(output,minx,miny,maxx,maxy,color,width,opacity):
	output.print0('<polyline fill-opacity="0" stroke-opacity="%.1f" stroke-width="%.1f" stroke="%s" points="'%(opacity,width,color))
	output.print0('%u,%u %u,%u %u,%u %u,%u %u,%u'%(minx,miny,maxx,miny,maxx,maxy,minx,maxy,minx,miny))
	output.print('"/>')

	output.print0('<polyline fill-opacity="0" stroke-opacity="0.6" stroke="#ffffff" points="')
	output.print0('%u,%u %u,%u %u,%u'%(minx-1,maxy,minx-1,miny-1,maxx,miny-1))
	output.print('"/>')

	output.print0('<polyline fill-opacity="0" stroke-opacity="0.6" stroke="#000000" points="')
	output.print0('%u,%u %u,%u %u,%u'%(minx,maxy+1,maxx+1,maxy+1,maxx+1,miny))
	output.print('"/>')

def print_box_svg(output,minx,miny,maxx,maxy,color,width,opacity):
	output.print('<rect x="%d" y="%d" width="%d" height="%d" fill-opacity="0" stroke="%s" stroke-opacity="%.1f" stroke-width="%.1f"/>'
			%(minx,miny,maxx-minx+1,maxy-miny+1,color,opacity,width))

def print_boxw_svg(output,minx,miny,maxx,maxy,color,bcolor,bcolor2,width,opacity):
	print_box_svg(output,minx-1,miny-1,maxx-1,maxy-1,bcolor2,width,0.5)
	print_box_svg(output,minx+1,miny+1,maxx+1,maxy+1,bcolor,width,0.8)
	print_box_svg(output,minx,miny,maxx,maxy,color,width,opacity)

def print_line_svg(output,x1,y1,x2,y2,color,width,opacity):
	output.print0('<polyline fill-opacity="0.0" stroke-opacity="%.1f" stroke-width="%.1f" stroke="%s" points="'%(opacity,width,color))
	output.print0('%u,%u %u,%u'%(x1,y1,x2,y2))
	output.print('"/>')

def points_lonlat_print_svg(output,rotation,width,height,splitlimit):
	lats=[-60.0,-30.0,0.0,30.0,60.0]
	lons=[-180.0,-150.0,-120.0,-90.0,-60.0,-30.0,0.0,30.0,60.0,90.0,120.0,150.0]
	
	hc=HemiCleave()
	for deg in lats:
		one=ShapePolyline.makelat(0,0,deg)
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			hc.cleave(onesphere)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height,splitlimit)
				flatshape.printsvg(output,cssline='sg')
	for deg in lons:
		one=ShapePolyline.makelon(0,0,deg)
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			hc.cleave(onesphere)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height,splitlimit)
				flatshape.printsvg(output,cssline='sg')

def arcs_lonlat_print_svg(output,rotation,width,height):
	lats=[-60.0,-30.0,0.0,30.0,60.0]
	lons=[-180,-150,-120,-90,-60,-30,0,30,60,90,120,150]
	for deg in lats:
		e=SphereLatitude(rotation.dlat,deg)
		fe=e.flatten(width,height)
		fe.printsvg(output,'sg')
	for deg in lons:
		e=SphereLongitude.make(rotation,deg)
		if e==None:
#			print('deg:%d rotation.dlon:%f skipped'%(deg,rotation.dlon),file=sys.stderr)
			continue
#		print('deg:%d rotation.dlon:%f not skipped'%(deg,rotation.dlon),file=sys.stderr)
		fe=e.flatten(width,height)
		fe.printsvg(output,'sg')

def tripel_lonlat_print_svg(output,width,height,shift):
	lats=[-60.0,-30.0,0.0,30.0,60.0]
	lons=[-150.0,-120.0,-90.0,-60.0,-30.0,0.0,30.0,60.0,90.0,120.0,150.0]
	for deg in lats:
		one=ShapePolyline.makelat(0,0,deg)
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				flatshape.shift(shift)
				flatshape.printsvg(output,cssline='tg')
	for deg in lons:
		one=ShapePolyline.makelon(0,0,deg)
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				flatshape.shift(shift)
				flatshape.printsvg(output,cssline='tg')

def print_partlabel_svg(output,xoff,yoff,text,textangle,width,height,partindex,partscount):
	if False:
		if partindex%4!=1: return
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

class PartCircle():
	@staticmethod
	def byweight(o): return o.weight

	def __init__(self,x,y,r,name):
		self.x=x
		self.y=y
		self.r=r
		self.weight=r
		self.isactive=True
		self.name=name

def findcircle_part_shape(shape,partindex,rotation,width_in,height_in,boxzoomcleave=None):
	width=width_in
	height=height_in
	if boxzoomcleave!=None:
		width=width*boxzoomcleave.zoomfactor
		height=height*boxzoomcleave.zoomfactor
	pointcount=0
	xsum=0
	ysum=0
	xmin=width
	xmax=0
	ymin=height
	ymax=0
	pluses=ShapePlus.make(shape)
	hc=HemiCleave()
	for oneplus in pluses:
		if not oneplus.ispartindex(partindex): continue
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if onesphere.type==NULL_TYPE_SHP: continue
		flatshape=onesphere.flatten(width,height,16)
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

	if boxzoomcleave and boxzoomcleave.zoomshift:
		ax+=boxzoomcleave.zoomshift.xoff
		ay+=boxzoomcleave.zoomshift.yoff

	ax=int(0.5+ax)
	ay=int(0.5+ay)
	r=int(0.5+math.sqrt(r2))
	return PartCircle(ax,ay,r,partindex)

def trimcircles(circles,sds):
	for p in circles:
		w=0
		rplus=p.r+sds
		for q in circles:
			d=FlatPoint.distance(p.x,p.y,q.x,q.y)
			if d<rplus: w+=q.r
		p.weight=w
	circles.sort(key=PartCircle.byweight,reverse=True)
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

def print_zoomdots_svg(output,shape,zoomdots,sds,cssclass1,cssclass2,rotation,width,height,boxzoomcleave):
	circles=[]
	for dot in zoomdots:
		fc=findcircle_part_shape(shape,dot,rotation,width,height,boxzoomcleave)
		if fc==None: continue
		circles.append(fc)
	trimcircles(circles,sds)
	for p in circles:
		if not p.isactive:
			if isverbose_global: print('Skipping zoomdot %d'%(p.name),file=sys.stderr)
			continue
		radius=p.r
		radius+=sds
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius+1))
		if radius>10:
			output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius-1))
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,p.x,p.y,radius))

def print_centerdot_svg(output,lon,lat,radius,cssclass1,cssclass2,rotation,width,height):
	sp=SpherePoint.makefromdll(DegLonLat(lon,lat),rotation)
	fp=sp.flatten(width,height)
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,fp.ux,fp.uy,radius+1))
	if radius>10:
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,fp.ux,fp.uy,radius-1))
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,fp.ux,fp.uy,radius))

def print_smalldots_svg(output,shape,smalldots,sds,cssclass1,cssclass2,rotation,width,height):
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
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius+1))
		if radius>10:
			output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius-1))
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,p.x,p.y,radius))
	
def combo_print_svg(output,options,full_admin0,sphere_admin0,zoom_admin0):
# we assume sphere_admin0 == zoom_admin0 if they are the same scale
	width=options['width']
	height=options['height']
	index=options['index']
	full_index=options['full_index']
	zoom_index=options['zoom_index']
	partindices=options['partindices']
	full_partindices=options['full_partindices']
	zoom_partindices=options['zoom_partindices']
	splitlimit=options['splitlimit']

	if True: #cdebug
		sphere_wc=WorldCompress(sphere_admin0,-1)
		sphere_wc.addcontinents('sphere')
		if options['iszoom']:
			if options['zoomm']==options['spherem']:
				zoom_wc=sphere_wc
			else:
				zoom_wc=WorldCompress(zoom_admin0,-1)
				zoom_wc.addcontinents('zoom')

	if 'halflightgsgs' in options:
		for gsg in options['halflightgsgs']:
			sphere_admin0.setdraworder(sphere_admin0.bynickname[gsg].index,-1,1)

	if index!=-1:
		for partindex in partindices:
			sphere_admin0.setdraworder(index,partindex,2)
	if full_index!=-1:
		for partindex in full_partindices:
			full_admin0.setdraworder(full_index,partindex,2)

	rotation=SphereRotation()
	if True:
		lon=options['lon']
		lat=options['lat']
		hlc=lat/2
		if hlc<-23.436: hlc=-23.436
		elif hlc>23.436: hlc=23.436
		rotation.set_deglonlat(lon,hlc)
		if isverbose_global: print('Rotation center: (lon,lat)=(%f,%f)'%(lon,hlc),file=sys.stderr)
	rotation2=SphereRotation()
	rotation2.set_deglonlat(options['lon'],options['lat'])

	css=['sl','sp','sb','sg','fs','ft','tl','tb','tg','sh','sq','si','th','tq']
	if options['iszoom']:
		m=['zb','zl','zp','zh','zq','zi']
		for c in m: css.append(c)
	if options['issubland']:
		m=['sl1','sp1']
		for c in m: css.append(c)
	if 'zoomdots' in options or 'moredots' in options or 'centerdot' in options:
		m=['c1','c2','c3','c4','w1','w2','w3','w4']
		for c in m: css.append(c)
	if options['islakes'] or options['iscompress']:
		m=['sw','sr']
		for c in m: css.append(c)
	if options['iszoomlakes']:
		m=['zw','zr']
		for c in m: css.append(c)
	if options['islakes']:
		m=['sw','sr']
		for c in m: css.append(c)
	if 'halflightgsgs' in options:
		m=['al','ap']
		for c in m: css.append(c)
	if options['isdisputed']:
		css.append('dp')
		if len(options['disputed']):
			m=['dl']
			for c in m: css.append(c)
		if len(options['disputed_border']):
			m=['db']
			for c in m: css.append(c)
		if options['iszoom']:
			css.append('dx')
			if len(options['disputed']):
				m=['dz']
				for c in m: css.append(c)
			if len(options['disputed_border']):
				m=['dy']
				for c in m: css.append(c)
	print_header_svg(output,width,height,css,options['labelfont'],[options['copyright'],options['comment']],isgradients=True)

	if 'bgcolor' in options: print_rectangle_svg(output,0,0,width,height,options['bgcolor'],1.0)

	if options['isroundwater']:
		if width==height: print_roundwater_svg(output,width)
	if isverbose_global: print('Drawing admin0 sphere shapes',file=sys.stderr)

	cornercleave=None
	if options['iszoom']:
		if not options['istopinsets']:
			if options['iszoom34']: cornercleave=CornerCleave(0,0.4,-0.4)
			else: cornercleave=CornerCleave(0,0.2,-0.2)

	if options['isdisputed']:
		sphere_admin0.loaddisputed()
		sphere_admin0.selectdisputed(options['disputed'],1)
		sphere_admin0.selectdisputed(options['disputed_border'],2)
		if options['spherem']!=options['zoomm']:
			zoom_admin0.loaddisputed()
			zoom_admin0.selectdisputed(options['disputed'],1)
			zoom_admin0.selectdisputed(options['disputed_border'],2)

	if True: #cdebug
		sphere_wc.removeoverlaps(sphere_admin0.shapes,2) # remove draworder 2 (highlights) from border polylines
		if options['isdisputed']: # TODO check if we can remove this?
			sphere_wc.removeoverlaps(sphere_admin0.disputed_shapes,1)
			
		if options['iszoom'] and options['spherem']!=options['zoomm']:
			zoom_wc.removeoverlaps(sphere_admin0.shapes,2) # remove draworder 2 (highlights) from border polylines
			if options['isdisputed']: # TODO potential remove
				zoom_wc.removeoverlaps(zoom_admin0.disputed_shapes,1)

		pluses=sphere_wc.getpluses(isnegatives=False,isoverlaps=False)
		negatives=sphere_wc.getnegatives()

		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit,
				cornercleave=cornercleave, cssfull='sl',csspatch='sp')
		for one in sphere_admin0.shapes:
				one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit, cornercleave=cornercleave, cssfull='sl',csspatch='sp')
		pluses_sphere_print_svg(output,negatives,rotation,width,height,splitlimit,
				cornercleave=cornercleave, cssfull='sw',csspatch='sr')

	if False:
		for one in sphere_admin0.shapes:
#			if one.nickname!='TZA.TZA': continue #cdebug
#			print('drawing %s %d'%(one.nickname,one.draworder),file=sys.stderr) #cdebug
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,
					cssfull='sl',csspatch='sp',cssreverse='sw',cssreversepatch='sr',cornercleave=cornercleave)
		for one in sphere_admin0.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull='al',csspatch='ap',
					cornercleave=cornercleave) # halflights

	if options['issubland']: # provinces/states on sphere
		if isverbose_global: print('Loading admin1 data',file=sys.stderr)
		ifile=install.getinstallfile('admin1.shp',[options['spherem']])
		admin1=Shp(ifile.filename,ifile)
		admin1.loadshapes()
		admin1dbf=Dbf(install.getfilename('admin1.dbf',[ifile.scale]))
		admin1dbf.selectcfield('sov_a3','sov3')
		admin1dbf.selectcfield('adm0_a3','adm3')
		admin1dbf.loadrecords()
		for one in sphere_admin0.shapes: # underdraw in case admin1 isn't complete cover
			draworder=1
			while True:
				nm=one_sphere_print_svg(output,one,draworder,rotation,width,height,splitlimit)
				if not nm: break
				draworder+=1
		if isverbose_global: print('Drawing admin1 sphere shapes',file=sys.stderr)
		foundcount=0
		for i in range(len(admin1dbf.records)):
			r=admin1dbf.records[i]
			if r['sov3']==options['grp'] and r['adm3']==options['subgrp']:
				foundcount+=1
				one=admin1.shapes[i]
				one_sphere_print_svg(output,one,-1,rotation,width,height,splitlimit)
		if isverbose_global:
			if foundcount==0:
				print('No admin1 regions found, you should set options.issubland=False',file=sys.stderr)
				raise ValueError
			else: print('Admin1 regions found: %d'%foundcount,file=sys.stderr)
		for partindex in partindices:
			sphere_admin0.setdraworder(index,partindex,1) # only draws border

	if options['isfullhighlight']:
		for one in full_admin0.shapes: # highlights
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull='sh',csspatch='sq',islabels=options['ispartlabels'])
	else:
		for one in sphere_admin0.shapes: # highlights
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull='sh',csspatch='sq',islabels=options['ispartlabels'])

	if options['isdisputed']:
		for one in sphere_admin0.disputed_shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull='dl',csspatch='dp')
		for one in sphere_admin0.disputed_shapes:
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull='db',csspatch='dp')

	if options['isfullpartlabels']:
		for one in full_admin0.shapes: # highlights
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull='sh',csspatch='sq',islabels=True)

	if options['islakes']:
		if isverbose_global: print('Drawing lakes sphere shapes',file=sys.stderr)
		pluses=sphere_admin0.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull='sw',csspatch='sr')

	pluses=sphere_wc.getpluses(ispositives=False,isoverlaps=True)
	pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssline='sb')

	borderlakeshapes=None
	zoom_borderlakeshapes=None
	if True and 'borderlakes' in options:
		if isverbose_global: print('Drawing border lakes (%s)'%options['spherem'],file=sys.stderr)
		sasi=ShpAdminShapeIntersection()
		sasi.addfromshapes(sphere_admin0.shapes,2)
		if options['isdisputed']: sasi.addfromshapes(sphere_admin0.disputed_shapes,1)
		for n in options['borderlakes']:
			l=sphere_admin0.lakes_bynickname[n]
			if not l:
				print('Border lake (%s) not found: %s'%(options['spherem'],n),file=sys.stderr)
				continue
			sasi.setinside(l)
		borderlakeshapes=sasi.exportlines()
		if options['iszoom']:
			if options['spherem']==options['zoomm']:
				zoom_borderlakeshapes=borderlakeshapes
			else:
				if isverbose_global: print('Drawing border lakes (%s)'%options['zoomm'],file=sys.stderr)
				sasi=ShpAdminShapeIntersection()
				sasi.addfromshapes(zoom_admin0.shapes,2)
				if options['isdisputed']: sasi.addfromshapes(zoom_admin0.disputed_shapes,1)
				for n in options['borderlakes']:
					l=zoom_admin0.lakes_bynickname[n]
					if not l:
						print('Border lake (%s) not found: %s'%(options['zoomm'],n),file=sys.stderr)
						continue
					sasi.setinside(l)
				zoom_borderlakeshapes=sasi.exportlines()

		for plus in borderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline='si')

	if 'moredots' in options: # [ (r0,isw0,[partindex00,partindex01]), ... , (rn,iswn,[partindexn0..partindexnm]) ]
		for moredots in options['moredots']:
			shape=full_admin0.shapes[full_index]
			sds=int((moredots[0]*width)/1000)
			isw=moredots[1]
			smalldots=moredots[2]
			cssclass='c1'
			if isinstance(isw,bool) and isw: cssclass='c4'
			elif isw==1: cssclass='c1'
			elif isw==2: cssclass='c2'
			elif isw==3: cssclass='c3'
			elif isw==4: cssclass='c4'
			cssclass2='w'+cssclass[1]
			print_smalldots_svg(output,shape,smalldots,sds,cssclass,cssclass2,rotation,width,height)

	if 'centerdot' in options: # (r0,isw0)
		r=int((options['centerdot'][0]*width)/1000)
		isw=options['centerdot'][1]
		cssclass='c1'
		if isinstance(isw,bool) and isw: cssclass='c4'
		elif isw==1: cssclass='c1'
		elif isw==2: cssclass='c2'
		elif isw==3: cssclass='c3'
		elif isw==4: cssclass='c4'
		cssclass2='w'+cssclass[1]
		print_centerdot_svg(output,options['lon'],options['lat'],r,cssclass,cssclass2,rotation,width,height)

	if True:
		if isverbose_global: print('Drawing lon/lat shapes',file=sys.stderr)
		if False: # this could be more accurate (if splitlimit is small and renderer isn't great)
			points_lonlat_print_svg(output,rotation,width,height,splitlimit)
		else: # this saves about 14k in svg
			arcs_lonlat_print_svg(output,rotation,width,height)

		(lon_rotation_center,lat_rotation_center)=rotation.deg_getcenter()
		lonlabels=[ (-150,'150°W'), (-120,'120°W'), (-90,'90°W'), (-60,'60°W'), (-30,'30°W'),
				(0,'0°E'), (30,'30°E'), (60,'60°E'), (90,'90°E'), (120,'120°E'), (150,'150°E'), (180,'180°E')]
		if lon_rotation_center<0:
			lonlabels=[ (-150,'150°W'), (-120,'120°W'), (-90,'90°W'), (-60,'60°W'), (-30,'30°W'),
					(0,'0°W'), (30,'30°E'), (60,'60°E'), (90,'90°E'), (120,'120°E'), (150,'150°E'), (180,'180°W')]

		labely=options['lonlabel_lat']
		for label in lonlabels:
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

	if options['istripelinset']  and full_index>=0: # Tripel inset #cdebug
		if isverbose_global: print('Drawing Tripel inset',file=sys.stderr)

		insetwidth=int(width*0.4)
		insetheight=insetwidth
			
		if True:
			insetshift=Shift(options['xoff_inset'],options['yoff_inset'])
			oneplus=ShapePlus.makeflatbox(True)
			onewt=TripelShape(oneplus)
			flatshape=onewt.flatten(insetwidth,insetheight)
			flatshape.shift(insetshift)
			flatshape.printsvg(output,cssfull='tb')
#		print_rectangle_svg(output,int(insetshift.xoff),int(insetshift.yoff+insetheight*0.025),insetwidth,int(insetheight*0.7),'#000000',0.3)

		if True:
			land=Shp(install.getfilename('land.shp',['110m']))
			land.loadshapes()
			for one in land.shapes:
				one_inset_tripel_print_svg(output,land,one,0,insetwidth,insetheight,None,'tl',None,insetshift)

		for one in full_admin0.shapes: # highlights
			one_inset_tripel_print_svg(output,full_admin0,one,2,insetwidth,insetheight,None,'th','tq',insetshift)

		tripel_lonlat_print_svg(output,insetwidth,insetheight,insetshift)

		for indices in options['tripelboxes']:
			mbr=Mbr()
			for partindex in indices:
				mbr_tripel(full_admin0,full_index,partindex,insetwidth,insetheight,insetshift,mbr)
			if mbr.isset:
				print_boxw_svg(output,mbr.minx-10,mbr.miny-10,mbr.maxx+10,mbr.maxy+10,'#45a249','#113311','#ffffff',int((5*width)/1000),0.9)

	if True and options['iszoom']: #cdebug
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
		zoomshift=Shift(xoff2+boff-xmargin,yoff2+boff-ymargin)
		bzc=BoxZoomCleave(scale,-boxd,boxd,-boxd,boxd,zoomshift)
		if zoom_index!=-1:
			for partindex in zoom_partindices:
				zoom_admin0.setdraworder(zoom_index,partindex,2)

		pluses=zoom_wc.getpluses(isnegatives=False,isoverlaps=False)
		negatives=zoom_wc.getnegatives()

		pluses_sphere_print_svg(output,pluses,rotation2,width,height,splitlimit,
				boxzoomcleave=bzc, cssfull='zl',csspatch='zp')
		for one in zoom_admin0.shapes:
				one_sphere_print_svg(output,one,0,rotation2,width,height,splitlimit,
						boxzoomcleave=bzc, cssfull='zl',csspatch='zp')
		pluses_sphere_print_svg(output,negatives,rotation2,width,height,splitlimit,
				boxzoomcleave=bzc, cssfull='sw',csspatch='sr')

		if options['issubland']:
			if 'grp' in options:
				for one in full_admin0.shapes: # underdraw in case admin1 has gaps
					draworder=1
					while True:
						nm=one_sphere_print_svg(output,one,draworder,rotation2,width,height,splitlimit,zoomshift,boxzoom)
						if not nm: break
						draworder+=1
				for i in range(len(admin1dbf.records)):
					r=admin1dbf.records[i]
					if r['sov3']==options['grp'] and r['adm3']==options['subgrp']:
						one=admin1.shapes[i]
						one_sphere_print_svg(output,one,-1,rotation2,width,height,splitlimit,zoomshift,boxzoom)
				for partindex in full_partindices:
					full_admin0.setdraworder(full_index,partindex,1)
		for one in full_admin0.shapes: # highlights
			one_sphere_print_svg(output,one,2,rotation2,width,height,splitlimit,cssfull='zh',csspatch='zq',
					boxzoomcleave=bzc)
		if options['isdisputed']:
			for one in zoom_admin0.disputed_shapes:
				one_sphere_print_svg(output,one,1,rotation2,width,height,splitlimit,cssfull='dz',csspatch='dx',boxzoomcleave=bzc)
			for one in zoom_admin0.disputed_shapes:
				one_sphere_print_svg(output,one,2,rotation2,width,height,splitlimit,cssfull='dy',csspatch='dx',boxzoomcleave=bzc)

		if options['iszoomlakes']:
			if isverbose_global: print('Drawing zoom lakes',file=sys.stderr)
			pluses=zoom_admin0.getlakes()
			pluses_sphere_print_svg(output,pluses,rotation2,width,height,splitlimit, cssfull='zw',csspatch='zp',boxzoomcleave=bzc)

		pluses=zoom_wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation2,width,height,splitlimit, cssline='zb',boxzoomcleave=bzc)

		if zoom_borderlakeshapes:
			for plus in zoom_borderlakeshapes:
				if plus.type!=POLYLINE_TYPE_SHP: continue
				oneplus_sphere_print_svg(output,plus,rotation2,width,height,splitlimit,cssline='zi',boxzoomcleave=bzc)

		if 'zoomdots' in options: # [ (r0,isw0,[partindex00,partindex01]), ... , (rn,iswn,[partindexn0..partindexnm]) ]
			for zoomdots in options['zoomdots']:
				shape=full_admin0.shapes[full_index]
				sds=int((zoomdots[0]*width)/1000)
				isw=zoomdots[1]
				dots=zoomdots[2]
				cssclass='c1'
				if isinstance(isw,bool) and isw: cssclass='c4'
				elif isw==1: cssclass='c1'
				elif isw==2: cssclass='c2'
				elif isw==3: cssclass='c3'
				elif isw==4: cssclass='c4'
				cssclass2='w'+cssclass[1]
				print_zoomdots_svg(output,shape,dots,sds,cssclass,cssclass2,rotation2,width,height,bzc)

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
		if f.type!=67: raise ValueError # C=67
		self.selectedcfields[nickname]=f
	def loadrecords(self):
		self.f.seek(self.headersize)
		for idx in range(self.numrecords):
			recorddata=self.f.read(self.recordsize)
			onerecord={}
			onerecord['_isdeleted']=(recorddata[0]==42)
			onerecord['_index']=idx
			for sf in self.selectedcfields:
				f=self.selectedcfields[sf]
				onerecord[sf]=recorddata[f.offset:f.offset+f.length].decode().rstrip()
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
	def query(self,q):
		ret=[]
		for r in self.records:
			for n in q:
				if q[n]!=r[n]: break
			else: ret.append(r)
		return ret
	def query1(self,q):
		rs=self.query(q)
		if len(rs)==1: return rs[0]['_index']
		return None

class InstallFile():
	def __init__(self,nickname,scale,dclass,filenames):
		self.nickname=nickname
		self.scale=scale
		self.dclass=dclass
		self.filenames=filenames
		self.isfound=False
		self.filename=None
		self.log=[]
	def findfile(self):
		dirs=['./','ned/']
		dirs.append('ned/'+self.scale+'/')
		dirs.append('ned/'+self.scale+'-'+self.dclass+'/')
		names=[]
		names.append(self.scale+'-'+self.nickname)
		for n in self.filenames: names.append(n)
		for d in dirs:
			for n in names:
				fn=d+n
				if os.path.isfile(fn):
					self.filename=fn
					self.isfound=True
					return True
		self.log.append('Couldn\'t find file: %s (%s). We looked in the following places:'%(self.nickname,self.scale))
		for d in dirs:
			for n in names:
				fn=d+n
				self.log.append('Checked for %s (not found)'%fn)
		return False

class Install():
	def __init__(self):
		self.filenames_10m={}
		self.filenames_50m={}
		self.filenames_110m={}
		self.addfile('admin0-lakes.shp','10m','admin', ['ne_10m_admin_0_countries_lakes.shp'])
		self.addfile('admin0-lakes.shp','50m','admin', ['ne_50m_admin_0_countries_lakes.shp'])
		self.addfile('admin0-lakes.shp','110m','admin', ['ne_110m_admin_0_countries_lakes.shp'])

		self.addfile('admin0-nolakes.shp','10m','admin', ['ne_10m_admin_0_countries.shp'])
		self.addfile('admin0-nolakes.shp','50m','admin', ['ne_50m_admin_0_countries.shp'])
		self.addfile('admin0-nolakes.shp','110m','admin', ['ne_110m_admin_0_countries.shp'])

		self.addfile('admin0-lakes.dbf','10m','admin', ['ne_10m_admin_0_countries_lakes.dbf'])
		self.addfile('admin0-lakes.dbf','50m','admin', ['ne_50m_admin_0_countries_lakes.dbf'])
		self.addfile('admin0-lakes.dbf','110m','admin', ['ne_110m_admin_0_countries_lakes.dbf'])

		self.addfile('admin0-nolakes.dbf','10m','admin', ['ne_10m_admin_0_countries.dbf'])
		self.addfile('admin0-nolakes.dbf','50m','admin', ['ne_50m_admin_0_countries.dbf'])
		self.addfile('admin0-nolakes.dbf','110m','admin', ['ne_110m_admin_0_countries.dbf'])

		self.addfile('admin1-lakes.shp','10m','admin', ['ne_10m_admin_1_states_provinces_lakes.shp'])
		self.addfile('admin1-lakes.shp','50m','admin', ['ne_50m_admin_1_states_provinces_lakes.shp'])
		self.addfile('admin1-lakes.shp','110m','admin', ['ne_110m_admin_1_states_provinces_lakes.shp'])

		self.addfile('admin1-nolakes.shp','10m','admin', ['ne_10m_admin_1_states_provinces.shp'])
		self.addfile('admin1-nolakes.shp','50m','admin', ['ne_50m_admin_1_states_provinces.shp'])
		self.addfile('admin1-nolakes.shp','110m','admin', ['ne_110m_admin_1_states_provinces.shp'])

		self.addfile('admin1-lakes.dbf','10m','admin', ['ne_10m_admin_1_states_provinces_lakes.dbf'])
		self.addfile('admin1-lakes.dbf','50m','admin', ['ne_50m_admin_1_states_provinces_lakes.dbf'])
		self.addfile('admin1-lakes.dbf','110m','admin', ['ne_110m_admin_1_states_provinces_lakes.dbf'])

		self.addfile('admin1-nolakes.dbf','10m','admin', ['ne_10m_admin_1_states_provinces.dbf'])
		self.addfile('admin1-nolakes.dbf','50m','admin', ['ne_50m_admin_1_states_provinces.dbf'])
		self.addfile('admin1-nolakes.dbf','110m','admin', ['ne_110m_admin_1_states_provinces.dbf'])

		self.addfile('lakes.shp','10m','lakes', [ 'ne_10m_lakes.shp' ])
		self.addfile('lakes.shp','50m','lakes', [ 'ne_50m_lakes.shp' ])
		self.addfile('lakes.shp','110m','lakes', [ 'ne_110m_lakes.shp' ])

		self.addfile('lakes.dbf','10m','lakes', [ 'ne_10m_lakes.dbf' ])
		self.addfile('lakes.dbf','50m','lakes', [ 'ne_50m_lakes.dbf' ])
		self.addfile('lakes.dbf','110m','lakes', [ 'ne_110m_lakes.dbf' ])

		self.addfile('ocean.shp','10m','ocean', [ 'ne_10m_ocean.shp' ])
		self.addfile('ocean.shp','50m','ocean', [ 'ne_50m_ocean.shp' ])
		self.addfile('ocean.shp','110m','ocean', [ 'ne_110m_ocean.shp' ])

		self.addfile('coast.shp','10m','coast', [ 'ne_10m_coastline.shp' ])
		self.addfile('coast.shp','50m','coast', [ 'ne_50m_coastline.shp' ])
		self.addfile('coast.shp','110m','coast', [ 'ne_110m_coastline.shp' ])

		self.addfile('land.shp','10m','land', [ 'ne_10m_land.shp' ])
		self.addfile('land.shp','50m','land', [ 'ne_50m_land.shp' ])
		self.addfile('land.shp','110m','land', [ 'ne_110m_land.shp' ])

		self.addfile('admin0-disputed.shp','10m','admin', [ 'ne_10m_admin_0_breakaway_disputed_areas.shp' ])
		self.addfile('admin0-disputed.shp','50m','admin', [ 'ne_50m_admin_0_breakaway_disputed_areas.shp' ])
		self.addfile('admin0-disputed.shp','110m','admin', [ 'ne_110m_admin_0_breakaway_disputed_areas.shp' ])

		self.addfile('admin0-disputed.dbf','10m','admin', [ 'ne_10m_admin_0_breakaway_disputed_areas.dbf' ])
		self.addfile('admin0-disputed.dbf','50m','admin', [ 'ne_50m_admin_0_breakaway_disputed_areas.dbf' ])
		self.addfile('admin0-disputed.dbf','110m','admin', [ 'ne_110m_admin_0_breakaway_disputed_areas.dbf' ])
	def addfile(self,nickname,scale,dclass,filenames):
		f=InstallFile(nickname,scale,dclass,filenames)
		f.findfile()
		if scale=='10m': self.filenames_10m[nickname]=f
		elif scale=='50m': self.filenames_50m[nickname]=f
		elif scale=='110m': self.filenames_110m[nickname]=f
		else: raise ValueError

	def getinstallfile(self,nicknames,scales=None):
		if not isinstance(nicknames,list):
			if nicknames=='admin0.shp': return self.getinstallfile(['admin0-lakes.shp','admin0-nolakes.shp'],scales)
			if nicknames=='admin1.shp': return self.getinstallfile(['admin1-lakes.shp','admin1-nolakes.shp'],scales)
			if nicknames=='admin0.dbf': return self.getinstallfile(['admin0-lakes.dbf','admin0-nolakes.dbf'],scales)
			if nicknames=='admin1.dbf': return self.getinstallfile(['admin1-lakes.dbf','admin1-nolakes.dbf'],scales)
			return self.getinstallfile([nicknames],scales)
		if scales==None: scales=['10m','50m','110m']
		for nickname in nicknames:
			for scale in scales:
				if scale=='10m': f=self.filenames_10m[nickname]
				elif scale=='50m': f=self.filenames_50m[nickname]
				elif scale=='110m': f=self.filenames_110m[nickname]
				else: raise ValueError("Unsupported scale: "+str(scale))
				if f.isfound: return f
		return None
	def getfilename(self,nickname,scales=None):
		f=self.getinstallfile(nickname,scales)
		return f.filename
	def print(self,n=None,scales=None):
		if n:
			if scales==None: scales=['10m','50m','110m']
			isfound=False
			for scale in scales:
				f=self.getinstallfile(n,[scale])
				if f and f.isfound:
					isfound=True
					print('Found file %s (%s) -> %s'%(n,f.scale,f.filename),file=sys.stdout)
			if not isfound: print('File not found: %s -> ?'%n,file=sys.stdout)
			return
		self.print('admin0-lakes.shp')
		self.print('admin0-nolakes.shp')
		self.print('admin0.dbf')
		self.print('admin1-lakes.shp')
		self.print('admin1-nolakes.shp')
		self.print('admin1.dbf')
		self.print('lakes.shp')
		self.print('lakes.dbf')
		self.print('coast.shp')
		self.print('ocean.shp')
		self.print('land.shp')
		self.print('admin0-disputed.shp')
		self.print('admin0-disputed.dbf')
	def printlog(self):
		for d in [self.filenames_10m,self.filenames_50m,self.filenames_110m]:
			for n in d:
				f=d[n]
				for l in f.log: print(l,file=sys.stdout)
		
		


# isverbose_global=True
install=Install()

def admin0dbf_test(): # admin0 test
	scale='10m'
	admin0dbf=Dbf(install.getfilename('admin0-nolakes.dbf',[scale]))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.print()
	admin0dbf.loadrecords()
	for i in range(len(admin0dbf.records)):
		print(i,': ',admin0dbf.records[i])

def lakesdbf_test(): # lakes test
	scale='50m'
	bynickname={}
	lakesdbf=Dbf(install.getfilename('lakes.dbf',[scale]))
	lakesdbf.selectcfield('name','name')
	lakesdbf.loadrecords()
	if True:
		lakesdbf.print()
		for i in range(len(lakesdbf.records)):
			print(i,': ',lakesdbf.records[i])

	lakesshp=Shp(install.getfilename('lakes.shp',[scale]))
	lakesshp.loadshapes()

	for i in range(len(lakesdbf.records)):
		nickname=lakesdbf.records[i]['name']
		bynickname[nickname]=lakesshp.shapes[i]

	l=bynickname['Lake Michigan']
	mbr=l.getmbr([-1])
	print('Lake Michigan: %s'%str(mbr))

	for i in range(len(lakesdbf.records)):
		l=lakesshp.shapes[i]
		mbr=l.getmbr([-1])
		if mbr.minx < -85: continue
		if mbr.minx > -80: continue
		if mbr.miny < 40: continue
		if mbr.maxy > 45: continue
		print('%s: %s'%(lakesdbf.records[i]['name'],mbr))


def lakesintersection_test(): # lakes intersecting shape -> border
	scale='50m'
	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.loadlakes()

	admin0.setdraworder(admin0.bynickname['CAN.CAN'].index,-1,2)

	sasi=ShpAdminShapeIntersection()

	for shape in admin0.shapes:
		(has,_)=shape.hasdraworder(2)
		if not has: continue
		pluses=ShapePlus.make(shape)
		for plus in pluses:
			if plus.draworder!=2: continue
			pg=plus.polygons[0]
			sasi.addpolygon(pg)

	for n in ['Lake Superior','Lake Ontario','Lake Erie','Lake Huron','Lake of the Woods','Upper Red Lake']:
		l=admin0.lakes_bynickname[n]
		sasi.setinside(l)

	exportpluses=sasi.exportlines()

	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	rotation.set_deglonlat(-84,23)
	print_header_svg(output,width,height,['sl','sp','sb','sw','sr','debugl','c4'],isgradients=True)
	print_roundwater_svg(output,width)

	one_sphere_print_svg(output,admin0.bynickname['US1.USA'],-1,rotation,width,height,8,cssfull='sl',csspatch='sp')
	one_sphere_print_svg(output,admin0.bynickname['CAN.CAN'],-1,rotation,width,height,8,cssfull='sl',csspatch='sp')

	lakepluses=admin0.getlakes()
	pluses_sphere_print_svg(output,lakepluses,rotation,width,height,8, cssfull='sw',csspatch='sr')

	for plus in exportpluses:
		if plus.type!=POLYLINE_TYPE_SHP: continue
		oneplus_sphere_print_svg(output,plus,rotation,width,height,8,cssline='debugl')

	if False:
		dll=DegLonLat(-95,49)
		dll_sphere_print_svg(output,dll,rotation,width,height,'c4')

	print_footer_svg(output)

def disputeddbf_test(): # disputed admin0 test
	dbf=Dbf(install.getfilename('admin0-disputed.dbf'))
	dbf.selectcfield('BRK_NAME','name')
	dbf.selectcfield('SOV_A3','sov3')
	dbf.selectcfield('ADM0_A3','adm3')
	dbf.loadrecords()
	for i in range(len(dbf.records)):
		r=dbf.records[i]
		print("%d: \"%s\" %s.%s"%(i,r['name'],r['sov3'],r['adm3']))

def admin1dbf_test(): # admin1 test
	admin1dbf=Dbf(install.getfilename('admin1.dbf'))
	admin1dbf.selectcfield('sov_a3','sov3')
	admin1dbf.selectcfield('adm0_a3','adm3')
	admin1dbf.loadrecords()
	for i in range(len(admin1dbf.records)):
		r=admin1dbf.records[i]
		print("%d: %s %s"%(i,r['sov3'],r['adm3']))

def webmercator_test(): # webmercator test
	output=Output()
	admin0=Shp(install.getfilename('admin0.shp',['110m']))
	admin0.loadshapes()
	coast=Shp(install.getfilename('coast.shp'))
	coast.loadshapes()
	width=1000
	height=1000
	print_header_svg(output,width,height,['sl','sp','tc'])

	wmc=WebMercatorCleave(True)

	if True:
		for shape in admin0.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewm=WebMercatorShape(oneplus)
				wmc.cleave(onewm)
				if onewm.type!=NULL_TYPE_SHP:
					flatshape=onewm.flatten(width,height)
					flatshape.printsvg(output,cssfull='sl',csspatch='sp')
	if True:
		for shape in coast.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewm=WebMercatorShape(oneplus)
				wmc.cleave(onewm)
				if onewm.type!=NULL_TYPE_SHP:
					flatshape=onewm.flatten(width,height)
					flatshape.printsvg(output,cssline='tc')
	print_footer_svg(output)

def ocean_test(): # ocean shp test
	output=Output()
	width=1630
	height=990
	print_header_svg(output,width,height,['tb','to','tg','debuggreen'])
#	print_rectangle_svg(output,0,0,width,height,'#5685a2',1.0)
	insetshift=Shift(5,5)
	insetwidth=1600
	insetheight=1600
	oneplus=ShapePlus.makeflatbox(True)
	onewt=TripelShape(oneplus)
	flatshape=onewt.flatten(insetwidth,insetheight)
	flatshape.shift(insetshift)
	flatshape.printsvg(output,cssfull='tb')
	if True:
		ocean=Shp(install.getfilename('ocean.shp'))
		ocean.loadshapes()
		for i in range(0,len(ocean.shapes)):
			shape=ocean.shapes[i]
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewt=TripelShape(oneplus)
				if onewt.type!=NULL_TYPE_SHP:
					flatshape=onewt.flatten(insetwidth,insetheight)
					flatshape.shift(insetshift)
					flatshape.printsvg(output,cssfull='debuggreen')
	tripel_lonlat_print_svg(output,insetwidth,insetheight,insetshift)
	if False:
		oneplus=ShapePlus.makeflatbox(False)
		onewt=TripelShape(oneplus)
		flatshape=onewt.flatten(insetwidth,insetheight)
		flatshape.shift(insetshift)
		flatshape.printsvg(output)
	print_footer_svg(output)

def land_test(): # land shp test
	output=Output()
	width=1630
	height=990
	print_header_svg(output,width,height,['tb','to','tg','debuggreen'])
#	print_rectangle_svg(output,0,0,width,height,'#5685a2',1.0)
	insetshift=Shift(5,5)
	insetwidth=1600
	insetheight=1600

	land=Shp(install.getfilename('land.shp',['110m']))
	land.loadshapes()
	if False:
		land.printinfo()
		for shape in land.shapes:
			shape.printparts()
		return

	oneplus=ShapePlus.makeflatbox(True)
	onewt=TripelShape(oneplus)
	flatshape=onewt.flatten(insetwidth,insetheight)
	flatshape.shift(insetshift)
	flatshape.printsvg(output,cssfull='tb')
	if True:
#		for i in range(0,len(land.shapes)):
		print('land.shapes.len:%d'%(len(land.shapes)),file=sys.stderr)
# africa: 112
		for i in range(112,113):
			shape=land.shapes[i]
			pluses=ShapePlus.make(shape)
#			pluses[0].polygons=[pluses[0].polygons[0]]

			for oneplus in pluses:
				onewt=TripelShape(oneplus)
				if onewt.type!=NULL_TYPE_SHP:
					flatshape=onewt.flatten(insetwidth,insetheight)
					flatshape.shift(insetshift)
					flatshape.printsvg(output,cssfull='debuggreen')
	tripel_lonlat_print_svg(output,insetwidth,insetheight,insetshift)
	if False:
		oneplus=ShapePlus.makeflatbox(False)
		onewt=TripelShape(oneplus)
		flatshape=onewt.flatten(insetwidth,insetheight)
		flatshape.shift(insetshift)
		flatshape.printsvg(output)
	print_footer_svg(output)

class MinusPoint():
	@staticmethod
	def getmlonlat(dll): return ( int(dll.lon*10000000) , int(dll.lat*10000000) )
	@staticmethod
	def printlist(points,file=sys.stdout):
		for p in points:
			print(p.mlonlat,file=file)
	def __init__(self,dll,shapeindex):
		self.mlonlat=MinusPoint.getmlonlat(dll)
		self.dll=dll
		# shapeindex and dupeindex aren't used but they probably work
		# originally I thought this would be useful for overlap removal but that's not practical
		self.shapeindex=shapeindex # creator
		self.dupeindex=-1 # creator of remover

class WorldMinus():
	@staticmethod
	def isreversepolygons2(one,two,offset):
		k=len(one.points)
		for p in one.points:
			q=two.points[offset]
			if MinusPoint.getmlonlat(p)!=MinusPoint.getmlonlat(q): return False
			offset=(offset-1)%k
		return True
	@staticmethod
	def isreversepolygons(one,two):
		if len(one.points)!=len(two.points): return False
		for i in range(len(one.points)):
			if WorldMinus.isreversepolygons2(one,two,i): return True
		return False
	def __init__(self,polygon,nickname=None):
		self.nickname=nickname
		self.polygon=polygon
		self.points=[]
		if polygon:
			for p in polygon.points: self.points.append(MinusPoint(p,polygon.index))
	def print(self,file=sys.stdout):
		print('WorldMinus(%s):'%self.nickname,file=file)
		for p in self.points:
			print(p.mlonlat,file=file)
	def addtoindex2(self,newpoints): # for polygons
		if not len(newpoints): return
		index=self.index
		lastp=newpoints[-1].mlonlat
		for p in newpoints:
			p=p.mlonlat
			a=index.get(lastp,None)
			if not a:
				a=[]
				index[lastp]=a
			a.append(p)
			lastp=p
	def addtoindex(self,newpoints): # for polylines
		index=self.index
		lastp=newpoints[0].mlonlat
		for i in range(1,len(newpoints)):
			p=newpoints[i].mlonlat
			a=index.get(lastp,None)
			if not a:
				a=[]
				index[lastp]=a
			a.append(p)
			lastp=p
	def buildindex(self):
		self.index={}
		self.addtoindex2(self.points)
	def isin(self,p,q):
		a=self.index.get(p.mlonlat,None)
		if not a: return False
		if q.mlonlat in a: return True
		return False
	def findlastmatch(self,minus):
		k=len(minus.points)
		prevp=minus.points[-1]
		for startindex in range(k):
			p=minus.points[startindex]
			if self.isin(p,prevp): break
			prevp=p
		else:
#			print('No match found, %d.%d:'%(minus.polygon.index,minus.polygon.partindex),file=sys.stderr)
			return None
		lastindex=startindex
		while True:
			prevp=p
			lastindex=(lastindex+1)%k
			if lastindex==startindex: raise ValueError("Full duplicate")
			p=minus.points[lastindex]
			if not self.isin(p,prevp):
#				print('Match found %d, %d.%d:'%((lastindex-1)%k,minus.polygon.index,minus.polygon.partindex),file=sys.stderr)
				return (lastindex-1)%k
	def findfirstmatch(self,minus,lastindex):
		k=len(minus.points)
		i=lastindex
		while True:
			i=(i-1)%k
			j=(i-1)%k
			if i==lastindex: raise ValueError # inf loop
			p=minus.points[i]
			prevp=minus.points[j]
			if not self.isin(p,prevp):
				return i
	def cutout(self,firstindex,lastindex):
		if firstindex<=lastindex: return self.points[firstindex:lastindex+1]
		return self.points[firstindex:]+self.points[0:lastindex+1]
	def notcutout(self,startindex,stopindex):
		if startindex<stopindex: return self.points[stopindex:]+self.points[0:startindex+1]
		return self.points[stopindex:startindex+1]
	@staticmethod
	def isstartswith_reverse(haystack,offset,needle):
		k=len(haystack)
		for i in range(len(needle)-1,-1,-1):
			if haystack[offset].mlonlat!=needle[i].mlonlat: return False
			offset=(offset+1)%k
		return True
	def removereverse(self,overlap):
		k=len(self.points)
		for i in range(k):
			if WorldMinus.isstartswith_reverse(self.points,i,overlap):
				startindex=i
				stopindex=(i+len(overlap)-1)%k
				break
		else:
			print('removereverse: Couldn\'t find overlap',file=sys.stderr)
			print('removereverse: blob: ',file=sys.stdout,end='')
			self.print(file=sys.stdout)
			print('removereverse: overlap: ',file=sys.stdout)
			MinusPoint.printlist(overlap,file=sys.stdout)
			raise ValueError
		if startindex==stopindex: raise ValueError

		j=startindex
		for i in range(len(overlap)-1,-1,-1):
#			if overlap[i].mlonlat!=self.points[j].mlonlat: raise ValueError # debug assert
			overlap[i].dupeindex=self.points[j].shapeindex
			j=(j+1)%k

		if startindex<stopindex: # we're going to lose the end points and then add them back with notcutout
			points=self.points[stopindex+1:]+self.points[0:startindex]
		else:
			points=self.points[stopindex+1:startindex]
		self.points=points
	def unshift(self,newpoints):
		self.points=newpoints+self.points
		self.addtoindex(newpoints)
	def getpolygon(self):
		pg=Polygon(0,0)
		pg.iscw=self.polygon.iscw
		for p in self.points: pg.points.append(p.dll)
		return pg
	def getplus(self):
		return ShapePlus.makefrompolygon(self.getpolygon(),0)

class WorldBlob():
	@staticmethod
	def makefrompolygon(polygon): return WorldBlob(WorldMinus(polygon))
	@staticmethod
	def makefromplus(plus):
		wb=WorldBlob.makefrompolygon(plus.polygons[0])
		for i in range(1,len(plus.polygons)):
			wb.negatives.append(plus.polygons[i])
		wb.plus=plus
		return wb
	def __init__(self,minus):
		self.negatives=[]
		self.blob=minus
		self.blob.buildindex()
		self.overlaps=[]
	def addtoblob_minus(self,minus):
		lastindex=self.blob.findlastmatch(minus)
		if lastindex==None:
			if False:
				print('addtoblob: No match found for %s'%minus.nickname,file=sys.stderr)
				print('Blob: ',file=sys.stdout,end='')
				self.blob.print(file=sys.stdout)
				minus.print(file=sys.stdout)
			return False
		firstindex=self.blob.findfirstmatch(minus,lastindex)
		if firstindex==lastindex: return False # this _would_ work if it weren't for rounding uncertainty
		overlap=minus.cutout(firstindex,lastindex)
		self.blob.removereverse(overlap)
		self.overlaps.append(overlap)
		nonoverlap=minus.notcutout(firstindex,lastindex)
		self.blob.unshift(nonoverlap)
		return True
	def addtoblob(self,plus):
		minus=WorldMinus(plus.polygons[0])
		if not self.addtoblob_minus(minus): return False
		for i in range(1,len(plus.polygons)):
			self.negatives.append(plus.polygons[i])
		return True
	def skipfromblob(self,plus):
		minus=WorldMinus(plus.polygons[0])
		if not self.addtoblob_minus(minus): return False
		return True
	def subtractfromblob(self,plus):
		pg=plus.polygons[0]
		for i in range(len(self.negatives)):
			neg=self.negatives[i]
			if not WorldMinus.isreversepolygons(neg,pg): continue
#			print('Found subtract match, %d points'%(len(pg.points)),file=sys.stderr)
			del self.negatives[i]
			minus=WorldMinus(neg,'subtraction')
			points=minus.points
			points.append(points[0])
			self.overlaps.append(points)
			return True
		return False
	def getplus(self,isnegatives=True): 
		sp=self.blob.getplus()
		if isnegatives:
			for neg in self.negatives: sp.polygons.append(neg)
		return sp
	def addpolygons(self,pgs):
		pgs.append(self.blob.getpolygon())
		for neg in self.negatives: pgs.append(neg)
	def getoverlaps(self):
		if not len(self.overlaps): return None
		sp=ShapePlus(0,None)
		sp.type=POLYLINE_TYPE_SHP
		sp.polylines=[]
		for o in self.overlaps:
			pl=Polyline(0,0)
			for p in o: pl.addDegLonLat(p.dll)
			sp.polylines.append(pl)
		return sp
	def getnegative(self):
		if not len(self.negatives): return None
		sp=ShapePlus(0,None)
		sp.type=POLYGON_TYPE_SHP
		sp.polygons=[]
		for neg in self.negatives: sp.polygons.append(neg)
		return sp
	def trimoverlaps(self,minus):
		overlaps=self.overlaps
		self.overlaps=[]
		for o in overlaps:
			k=len(o) -1
			i=0
			while i<k:
				p=o[i]
				q=o[i+1]
				if minus.isin(p,q) or minus.isin(q,p):
					if i: self.overlaps.append(o[0:i+1])
					del o[0:i+1]
					k=k-i-1
					i=0
					continue
				i+=1
			if len(o)>1: self.overlaps.append(o)

class ShapeCompress():
	def __init__(self,dest_draworder,source_draworder=0):
		self.dest_draworder=dest_draworder
		self.source_draworder=source_draworder
		self.blobs=[]
	def addshape(self,shape):
		pluses=ShapePlus.make(shape)
		for plus in pluses:
			if self.source_draworder!=plus.draworder: continue
			found=False
			for blob in self.blobs:
				if blob.addtoblob(plus):
					found=True
					shape.draworderlist[plus.polygons[0].partindex]=self.dest_draworder
					break
			if not found:
				blob=WorldBlob.makefromplus(plus)
				self.blobs.append(blob)
				shape.draworderlist[plus.polygons[0].partindex]=self.dest_draworder
	def exportshape(self):
		pgs=[]
		for blob in self.blobs:
			blob.addpolygons(pgs)
		sp=ShapePlus.makefrompolygons(pgs,0)
		shape=sp.toshape()
		return shape
		
class WorldCompress():
	def __init__(self,shp,dest_draworder,source_draworder=0):
		self.shp=shp
		self.dest_draworder=dest_draworder
		self.source_draworder=source_draworder
		self.blobs=[]
		self.currentblob=None
		self.skiplist=[]
	def startblob(self,gsg):
		s=self.shp.bynickname[gsg]
		if not s: raise ValueError
		plus=ShapePlus.pickbiggest(ShapePlus.make(s))
		if self.source_draworder!=s.draworderlist[plus.polygons[0].partindex]: raise ValueError # this is plus.draworder
		blob=WorldBlob.makefromplus(plus)
		s.draworderlist[plus.polygons[0].partindex]=self.dest_draworder
		self.blobs.append(blob)
		self.currentblob=blob
	def addtoblob(self,gsg,isfindall=False):
		s=self.shp.bynickname[gsg]
		if not s: return
		pluses=ShapePlus.make(s)
		found=0
		for pl in pluses:
			if self.source_draworder!=s.draworderlist[pl.polygons[0].partindex]: continue # this is plus.draworder
			if self.currentblob.addtoblob(pl):
				found+=1
#				print('adding to blob: %s.%d'%(pl.shape.nickname,pl.polygons[0].partindex),file=sys.stderr) #cdebug
				s.draworderlist[pl.polygons[0].partindex]=self.dest_draworder
				if not isfindall: break
#		if not found: print('NOT adding to blob: %s'%(pl.shape.nickname),file=sys.stderr) #cdebug
	def skipfromblob(self,gsg,isfindall=False):
		s=self.shp.bynickname[gsg]
		if not s: return
		self.skiplist.append(s)
		pluses=ShapePlus.make(s)
		found=0
		for pl in pluses:
			if self.currentblob.skipfromblob(pl):
				found+=1
#				print('adding to blob: %s.%d'%(pl.shape.nickname,pl.polygons[0].partindex),file=sys.stderr) #cdebug
				if not isfindall: break
#		if not found: print('NOT adding to blob: %s'%(pl.shape.nickname),file=sys.stderr) #cdebug
	def subtractfromblob(self,gsg):
		s=self.shp.bynickname[gsg]
		if not s: return
		pluses=ShapePlus.make(s)
		for pl in pluses: # this removes ccw as well as removing a redundant floodfill
			if self.source_draworder!=s.draworderlist[pl.polygons[0].partindex]: continue # this is pl.draworder
			if self.currentblob.subtractfromblob(pl):
				s.draworderlist[pl.polygons[0].partindex]=self.dest_draworder
				break
	def getpluses(self,ispositives=True,isnegatives=True,isoverlaps=True):
		ret=[]
		if ispositives:
			for blob in self.blobs:
				ret.append(blob.getplus(isnegatives))
		if isoverlaps:
			for blob in self.blobs:
				os=blob.getoverlaps()
				if os: ret.append(os)
		return ret
	def getnegatives(self):
		ret=[]
		for blob in self.blobs:
			sp=blob.getnegative()
			if sp: ret.append(sp)
		return ret
	def addasia(self):
		if self.shp.installfile.scale in ['10m']:
			self.startblob('LAO.LAO')
			set1=('VNM.VNM','KHM.KHM','MMR.MMR','THA.THA','CH1.CHN','PRK.PRK','KOR.KOR',
					'KAS.KAS',
					'MNG.MNG','RUS.RUS','KAZ.KAZ','NPL.NPL','BTN.BTN','IND.IND','PAK.PAK',
					'BGD.BGD'
					)
			set2=('KGZ.KGZ','TJK.TJK')
	# ,'UZB.UZB')
			set3=('FI1.FIN','SWE.SWE','NOR.NOR')
			for gsg in set1: self.addtoblob(gsg)
	#		self.addtoblob('RUS.RUS',isfindall=True)
			for gsg in set2: self.addtoblob(gsg)
			for gsg in set3: self.addtoblob(gsg)
		if self.shp.installfile.scale == '50m':
			self.startblob('LAO.LAO')
			set1=('VNM.VNM','KHM.KHM','MMR.MMR','THA.THA','CH1.CHN','PRK.PRK','KOR.KOR',
					'KAS.KAS',
					'MNG.MNG','RUS.RUS','KAZ.KAZ','NPL.NPL','BTN.BTN','IND.IND','PAK.PAK',
					'BGD.BGD'
					)
			set2=('KGZ.KGZ','TJK.TJK','UZB.UZB','TKM.TKM')
	# ,'UZB.UZB')
			set3=('AFG.AFG','FI1.FIN','SWE.SWE','NOR.NOR')
			for gsg in set1: self.addtoblob(gsg)
	#		self.addtoblob('RUS.RUS',isfindall=True)
			for gsg in set2: self.addtoblob(gsg)
			self.addtoblob('AZE.AZE',isfindall=True)
			for gsg in set3: self.addtoblob(gsg)
	def addmiddleeast(self):
		if self.shp.installfile.scale in ['10m','50m']:
			set1=('IRQ.IRQ','KWT.KWT','SAU.SAU','ARE.ARE','OMN.OMN','OMN.OMN','YEM.YEM','JOR.JOR',
					'IS1.PSX','IS1.ISR',
					'SYR.SYR','LBN.LBN','TUR.TUR')
			set2=( 'ARM.ARM','GEO.GEO' )
			self.startblob('IRN.IRN')
			for gsg in set1: self.addtoblob(gsg)
			for gsg in set2: self.addtoblob(gsg)
	def addafrica(self):
		if self.shp.installfile.scale=='10m':
			if self.shp.installfile.nickname=='admin0-lakes.shp':
				set1=('DZA.DZA',
				'TUN.TUN','LBY.LBY','EGY.EGY','SDN.SDN','ERI.ERI','DJI.DJI','SOL.SOL','SOM.SOM','KEN.KEN')
				set2=('ETH.ETH','SDS.SDS','CAF.CAF','TCD.TCD','NER.NER','MLI.MLI','SAH.SAH','MRT.MRT','SEN.SEN','GMB.GMB',
						'COG.COG',
						'AGO.AGO', 'BFA.BFA','NGA.NGA','BEN.BEN','TGO.TGO','GHA.GHA','CIV.CIV',
						'LBR.LBR','SLE.SLE','GIN.GIN','GNB.GNB','CMR.CMR','GNQ.GNQ','GAB.GAB',
					)
				set3=('COD.COD','ZMB.ZMB','AGO.AGO','ZWE.ZWE','BWA.BWA','NAM.NAM','MOZ.MOZ','ZAF.ZAF')
		#		'UGA.UGA','RWA.RWA','BDI.BDI',
		#		set2=('COD.COD','ZMB.ZMB', 'MOZ.MOZ', 'NAM.NAM', 'ZWE.ZWE','BWA.BWA', 'SWZ.SWZ','ZAF.ZAF'
				self.startblob('MAR.MAR')
				for gsg in set1: self.addtoblob(gsg)
				for gsg in set2: self.addtoblob(gsg)
				for gsg in set3: self.addtoblob(gsg)
				self.subtractfromblob('LSO.LSO')
			elif self.shp.installfile.nickname=='admin0-nolakes.shp':
				set1=('DZA.DZA','TUN.TUN','LBY.LBY','EGY.EGY','SDN.SDN','ERI.ERI','DJI.DJI','ETH.ETH','SOL.SOL','SOM.SOM','KEN.KEN',
						'SAH.SAH','MRT.MRT','MLI.MLI','NER.NER','TCD.TCD','SEN.SEN','GMB.GMB','GNB.GNB','GIN.GIN','BFA.BFA','SLE.SLE',
						'LBR.LBR','CIV.CIV','GHA.GHA','TGO.TGO','BEN.BEN','NGA.NGA','CMR.CMR','CAF.CAF','SDS.SDS','GNQ.GNQ','GAB.GAB',
						'COG.COG','COD.COD','UGA.UGA','RWA.RWA','BDI.BDI','TZA.TZA','AGO.AGO','AGO.AGO','ZMB.ZMB','MWI.MWI','NAM.NAM',
						'BWA.BWA')
				set2=('ZWE.ZWE','ZAF.ZAF','SWZ.SWZ','MOZ.MOZ')
				self.startblob('MAR.MAR')
				for gsg in set1: self.addtoblob(gsg)
				for gsg in set2: self.addtoblob(gsg)
				self.subtractfromblob('LSO.LSO')
		elif self.shp.installfile.scale=='50m':
			set1=('DZA.DZA','TUN.TUN','LBY.LBY','EGY.EGY','SDN.SDN','ERI.ERI','DJI.DJI','ETH.ETH','SOL.SOL','SOM.SOM','KEN.KEN',
					'SAH.SAH','MRT.MRT','MLI.MLI','NER.NER','TCD.TCD','SEN.SEN','GMB.GMB','GNB.GNB','GIN.GIN','BFA.BFA','SLE.SLE',
					'LBR.LBR','CIV.CIV','GHA.GHA','TGO.TGO','BEN.BEN','NGA.NGA','CMR.CMR','CAF.CAF','SDS.SDS','GNQ.GNQ','GAB.GAB',
					'COG.COG','COD.COD','UGA.UGA','RWA.RWA','BDI.BDI','TZA.TZA','AGO.AGO','AGO.AGO','ZMB.ZMB','MWI.MWI','NAM.NAM',
					'BWA.BWA')
			set2=('ZWE.ZWE','ZAF.ZAF','SWZ.SWZ','MOZ.MOZ')
			self.startblob('MAR.MAR')
			for gsg in set1: self.addtoblob(gsg)
			for gsg in set2: self.addtoblob(gsg)
			self.subtractfromblob('LSO.LSO')
	def addsouthamerica(self):
		if self.shp.installfile.scale=='10m':
			set1=('PRY.PRY','BOL.BOL','ARG.ARG','URY.URY')
#'ARG.ARG','PRY.PRY','CHL.CHL', 'BOL.BOL', 'BRA.BRA')
# , 'PER.PER', 'ECU.ECU', 'COL.COL','VEN.VEN', 'GUY.GUY', 'SUR.SUR', 'FR1.FRA')
			self.startblob('BRA.BRA')
			for gsg in set1: self.addtoblob(gsg)
		elif self.shp.installfile.scale=='50m':
			set1=('ARG.ARG','PRY.PRY','CHL.CHL', 'BOL.BOL', 'PER.PER', 'ECU.ECU', 'COL.COL','VEN.VEN', 'GUY.GUY', 'SUR.SUR', 'FR1.FRA', 'BRA.BRA')
			self.startblob('URY.URY')
			for gsg in set1: self.addtoblob(gsg)
	def addnorthamerica(self):
		if self.shp.installfile.scale=='10m':
			if self.shp.installfile.nickname=='admin0-lakes.shp':
				set1=('CRI.CRI','NIC.NIC','HND.HND','GTM.GTM','BLZ.BLZ','SLV.SLV','MEX.MEX','US1.USA')
				self.startblob('PAN.PAN')
				for gsg in set1: self.addtoblob(gsg)
			elif self.shp.installfile.nickname=='admin0-nolakes.shp':
				set1=('CRI.CRI','NIC.NIC','HND.HND','GTM.GTM','BLZ.BLZ','SLV.SLV','MEX.MEX','US1.USA','CAN.CAN','US1.USA')
				self.startblob('PAN.PAN')
				for gsg in set1: self.addtoblob(gsg)
		elif self.shp.installfile.scale=='50m':
			set1=('CRI.CRI','NIC.NIC','HND.HND','GTM.GTM','BLZ.BLZ','SLV.SLV','MEX.MEX','US1.USA','CAN.CAN','US1.USA')
			self.startblob('PAN.PAN')
			for gsg in set1: self.addtoblob(gsg)
	def addeurope(self):
		if self.shp.installfile.scale=='10m':
			if self.shp.installfile.nickname=='admin0-lakes.shp':
				set1=('ESP.ESP','AND.AND','FR1.FRA','LUX.LUX',
						'BEL.BEL','NL1.NLD','DEU.DEU', 'CHE.CHE','LIE.LIE',
						'AUT.AUT','HUN.HUN','CZE.CZE','SVK.SVK',
						'POL.POL','RUS.RUS','LTU.LTU','LVA.LVA','EST.EST',
						'BLR.BLR','UKR.UKR','MDA.MDA','ROU.ROU','BGR.BGR',
						'ITA.ITA', 'SVN.SVN', 'HRV.HRV', 'SRB.SRB','MKD.MKD',
						'BIH.BIH','KOS.KOS', 'GRC.GRC','ALB.ALB','MNE.MNE','TUR.TUR')
				self.startblob('PRT.PRT')
				for gsg in set1: self.addtoblob(gsg)
			elif self.shp.installfile.nickname=='admin0-nolakes.shp':
				set1=('ESP.ESP','AND.AND','FR1.FRA','LUX.LUX',
						'BEL.BEL','NL1.NLD','DEU.DEU', 'CHE.CHE','LIE.LIE',
						'AUT.AUT','HUN.HUN','CZE.CZE','SVK.SVK',
						'POL.POL','RUS.RUS','LTU.LTU','LVA.LVA','EST.EST',
						'BLR.BLR','UKR.UKR','MDA.MDA','ROU.ROU','BGR.BGR',
						'ITA.ITA', 'SVN.SVN', 'HRV.HRV', 'SRB.SRB','MKD.MKD',
						'BIH.BIH','KOS.KOS', 'GRC.GRC','ALB.ALB','MNE.MNE','TUR.TUR',
						'LVA.LVA','LTU.LTU','EST.EST'
						)
				self.startblob('PRT.PRT')
				for gsg in set1: self.addtoblob(gsg)
		elif self.shp.installfile.scale=='50m':
			set1=('ESP.ESP','AND.AND','FR1.FRA','LUX.LUX',
					'BEL.BEL','NL1.NLD','DEU.DEU', 'CHE.CHE','LIE.LIE',
					'AUT.AUT','HUN.HUN','CZE.CZE','SVK.SVK',
					'POL.POL','RUS.RUS','LTU.LTU','LVA.LVA','EST.EST',
					'BLR.BLR','UKR.UKR','MDA.MDA','ROU.ROU','BGR.BGR',
					'ITA.ITA', 'SVN.SVN', 'HRV.HRV', 'SRB.SRB','MKD.MKD',
					'BIH.BIH','KOS.KOS', 'GRC.GRC','ALB.ALB','MNE.MNE','TUR.TUR',
					'LVA.LVA','LTU.LTU','EST.EST'
					)
			self.startblob('PRT.PRT')
			for gsg in set1: self.addtoblob(gsg)
	def _addeuro(self,isscand):
			self.startblob('PRT.PRT')
			self.addtoblob('ESP.ESP')
			self.skipfromblob('AND.AND')
			for gsg in ['FR1.FRA','LUX.LUX','BEL.BEL','NL1.NLD','DEU.DEU','DN1.DNK']: self.addtoblob(gsg)
			self.skipfromblob('CHE.CHE')
			self.skipfromblob('LIE.LIE')
			for gsg in ['AUT.AUT','HUN.HUN','CZE.CZE','SVK.SVK','POL.POL','LTU.LTU','LVA.LVA','EST.EST']: self.addtoblob(gsg)
			for gsg in ['ROU.ROU','BGR.BGR','ITA.ITA','HRV.HRV','SVN.SVN','GRC.GRC']: self.addtoblob(gsg)
			self.removeskips()
			if isscand:
				self.startblob('SWE.SWE')
				self.addtoblob('FI1.FIN')
	def addcontinents(self,label=''):
		if self.shp.installfile.scale=='10m':
			print('Not making worldcompress for 10m: %s'%label,file=sys.stderr)
			return
		if len(label): label+=' '
		if isverbose_global: print('Creating %sblobs: '%label,end='',file=sys.stderr,flush=True)
		if isverbose_global: print('Europe ',end='',file=sys.stderr,flush=True)
		self.addeurope()
		if isverbose_global: print('North America ',end='',file=sys.stderr,flush=True)
		self.addnorthamerica()
		if isverbose_global: print('South America ',end='',file=sys.stderr,flush=True)
		self.addsouthamerica()
		if isverbose_global: print('Africa ',end='',file=sys.stderr,flush=True)
		self.addafrica()
		if isverbose_global: print('Middle East ',end='',file=sys.stderr,flush=True)
		self.addmiddleeast()
		if isverbose_global: print('Asia ',end='',file=sys.stderr,flush=True)
		self.addasia()
		if isverbose_global: print('done',file=sys.stderr,flush=True)
	def addeuro(self,isscand=True):
		label='euro '
		if isverbose_global: print('Creating %sblobs: '%label,end='',file=sys.stderr,flush=True)
		if isverbose_global: print('Euro ',end='',file=sys.stderr,flush=True)
		self._addeuro(isscand)
		if isverbose_global: print('done',file=sys.stderr,flush=True)
	def removeskips(self):
		self.removeoverlaps(self.skiplist,None)
		self.skiplist=[]
	def removeoverlaps(self,shapes,draworder):
		minus=WorldMinus(None)
		minus.buildindex()
		for shape in shapes:
			for i in range(len(shape.draworderlist)):
				if draworder!=None and shape.draworderlist[i]!=draworder: continue
				start=shape.partlist[i]
				limit=shape.pointscount
				if i+1<shape.partscount: limit=shape.partlist[i+1]
				mpoints=[]
				for j in range(start,limit):
					p=shape.pointlist[j]
					mpoints.append(MinusPoint(p,shape.index))
				minus.addtoindex2(mpoints)
		for blob in self.blobs:
			blob.trimoverlaps(minus)


def worldcompress_test():
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='10m'
	scale='50m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.setccwtypes()
	admin0.loadlakes()

	rotation.set_deglonlat(60,20)

	wc=WorldCompress(admin0,-1)
	wc.addcontinents('worldcompress_test')

#	admin0.setdraworder(admin0.bynickname['NAM.NAM'].index,-1,2)
	wc.removeoverlaps(admin0.shapes,2)
#	admin0.setdraworder(admin0.bynickname['NAM.NAM'].index,-1,0)

	print_header_svg(output,width,height,['sb','sl','sp','debugl','sh','sq','sw','sr'],isgradients=True)

	pluses=wc.getpluses(isnegatives=False,isoverlaps=False)
	pluses_sphere_print_svg(output,pluses,rotation,width,height,4, cssfull='sl',csspatch='sp')

	if False:
		negatives=wc.getnegatives()
		pluses_sphere_print_svg(output,negatives,rotation,width,height,4, cssfull='sw',csspatch='sr')

	if False:
		pluses=admin0.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,4, cssfull='sw',csspatch='sr')

	if False:
		pluses=wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,4, cssline='sb')

	if False:
		for one in admin0.shapes: one_sphere_print_svg(output,one,0,rotation,width,height,4,cssfull='sh',csspatch='sq')

	print_footer_svg(output)

def ccw_test():
	ifile=install.getinstallfile('admin0.shp',['10m'])
	admin0=Shp(ifile.filename,ifile)
	admin0.loadshapes()
	admin0dbf=Dbf(install.getfilename('admin0.dbf',['10m']))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.loadrecords()
	for i in range(admin0dbf.numrecords):
		r=admin0dbf.records[i]
		nickname=r['sov3']+'.'+r['adm3']
		admin0.setnickname(i,nickname)

	admin0_setccwtypes(admin0)

	shape=admin0.bynickname['CAN.CAN']
	print('%s number: %d, shape: %s, parts: %d, points: %d'%(shape.nickname,shape.number,shapename(shape.type),shape.partscount,shape.pointscount),file=sys.stdout)
	pluses=ShapePlus.make(shape)
	for plus in pluses:
		for pg in plus.polygons:
			if pg.iscw: continue
			print('%d: iscw:%s ccwtype:%s'%(pg.partindex,pg.iscw,ccwtype_tostring(pg.ccwtype)))
	if False:
		for i in range(shape.partscount):
			j=shape.partlist[i]
			k=shape.pointscount
			if i+1<shape.partscount: k=shape.partlist[i+1]
			pg=Polygon.make(shape,j,k,0,0)
			if not pg.iscw or pg.ccwtype:
				print('%d: %d points (%d..%d), iscw:%s ccwtype:%s'%(i,k-j,j,k,pg.iscw,ccwtype_tostring(pg.ccwtype)),file=sys.stdout)
	
	

def tripel_test(): # Winkel Tripel test
	output=Output()
	width=500
	height=500
	print_header_svg(output,width,height,['tb','to','tg'])
#	print_rectangle_svg(output,0,0,width,height,'#5685a2',1.0)
	insetshift=Shift(5,5)
	insetwidth=400
	insetheight=400
	oneplus=ShapePlus.makeflatbox(True)
	onewt=TripelShape(oneplus)
	flatshape=onewt.flatten(insetwidth,insetheight)
	flatshape.shift(insetshift)
	flatshape.printsvg(output,cssfull='tb')
	if True:
		ocean=Shp(install.getfilename('ocean.shp'))
		ocean.loadshapes()
		for shape in ocean.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewt=TripelShape(oneplus)
				if onewt.type!=NULL_TYPE_SHP:
					flatshape=onewt.flatten(insetwidth,insetheight)
					flatshape.shift(insetshift)
					flatshape.printsvg(output,cssfull='to')
	tripel_lonlat_print_svg(output,insetwidth,insetheight,insetshift)
	if False:
		oneplus=ShapePlus.makeflatbox(False)
		onewt=TripelShape(oneplus)
		flatshape=onewt.flatten(insetwidth,insetheight)
		flatshape.shift(insetshift)
		flatshape.printsvg(output)

	print_footer_svg(output)

def zoom_test(): # zoom test
	output=Output()
	width=1000
	height=1000
	admin0=ShpAdmin('admin0-nolakes.shp',['110m'])
	index=admin0.bynickname['LAO.LAO'].index
	partindex=-1
	scale=2
	boxd=1/(2*scale)
	boff=-int(scale*width/2)+int(width/2)
	zoomshift=Shift(boff,boff)
	bzc=BoxZoomCleave(scale,-boxd,boxd,-boxd,boxd,zoomshift)
	(lon,lat)=admin0.getcenter(index,[0])
	sr=SphereRotation()
	sr.set_deglonlat(lon,lat)
	print_header_svg(output,width,height,['zl','debugzp'])
	print_rectangle_svg(output,0,0,width,height,'#000000',1.0)
	print_rectangle_svg(output,200,200,600,600,'#5685a2',1.0)
	hc=HemiCleave()
	for one in admin0.shapes:
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
#			if oneplus.shape.nickname!='CH1.CHN': continue
#			if not oneplus.ispartindex(1): continue
			onesphere=SphereShape(oneplus,sr)
			hc.cleave(onesphere)
			bzc.cleave(onesphere)
#			onesphere.print(file=sys.stdout)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(scale*width,scale*height,4)
				bzc.shift(flatshape)
#				flatshape.print(file=sys.stdout)
				flatshape.printsvg(output,cssfull='zl',csspatch='debugzp')
	print_footer_svg(output)

def province_test(): # province test
	output=Output()
	width=1000
	height=1000
	admin0=Shp(install.getfilename('admin0.shp',['10m']))
	admin0.loadshapes()
	admin1=Shp(install.getfilename('admin1.shp',['10m']))
	admin1.loadshapes()
	admin1dbf=Dbf(install.getfilename('admin1.dbf',['10m']))
	admin1dbf.selectcfield('sov_a3','sov3')
	admin1dbf.selectcfield('adm0_a3','adm3')
	admin1dbf.loadrecords()
	print_header_svg(output,width,height,['tl','tp','tl1','tp1'])
	wmc=WebMercatorCleave(False)
	for shape in admin0.shapes:
		pluses=ShapePlus.make(shape)
		for oneplus in pluses:
			onewm=WebMercatorShape(oneplus)
			wmc.cleave(onewm)
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				flatshape.printsvg(output,cssfull='tl',csspatch='tp')
	for i in range(len(admin1dbf.records)):
		r=admin1dbf.records[i]
		if r['sov3']=='MEX' and r['adm3']=='MEX':
			output.print('<!-- admin1 %d -->'%i)
			shape=admin1.shapes[i]
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewm=WebMercatorShape(oneplus)
				wmc.cleave(onewm)
				if onewm.type!=NULL_TYPE_SHP:
					flatshape=onewm.flatten(width,height)
					flatshape.printsvg(output,cssfull='tl1',csspatch='tp1')
	print_footer_svg(output)

def admin0info_test():
	admin0=Shp(install.getfilename('admin0.shp'))
	admin0.printinfo()

def admin0parts_test():
	scales=['110m']
	scales=['10m']
	scales=['50m']

	gsgs=['RUS.RUS']
	gsgs=['TTO.TTO']
	gsgs=['ATA.ATA']
	gsgs=['CYP.CYP','CYN.CYN']

	sfi=install.getinstallfile('admin0-nolakes.shp',scales)
	print('shp filename: %s'%sfi.filename)
	admin0=Shp(sfi.filename)
	admin0.loadshapes()
	dfi=install.getinstallfile(sfi.nickname[:-3]+'dbf',scales)
	print('dbf filename: %s'%dfi.filename)
	admin0dbf=Dbf(dfi.filename)
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.loadrecords()
	for i in range(admin0dbf.numrecords):
		r=admin0dbf.records[i]
		nickname=r['sov3']+'.'+r['adm3']
		if nickname in gsgs:
			print('Shape: %s'%nickname)
			shape=admin0.shapes[i]
			shape.printparts()
#			shape.print()
	

def print_lat_label_svg(output,lon1,lon2,lat,text,width,height,rotation,fontstep=8):
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
	# output.print('<polyline fill-opacity="0" stroke-opacity="1" stroke="#ffffff" points="%d,%d %d,%d"/>'%(fp1.ux,fp1.uy,fp2.ux,fp2.uy))
	if False:
		xoff=0
		for i in range(len(text)):
			s=text[i:i+1]
			yoff=slope*xoff
			output.print('<text x="0" y="0" class="fs" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux+xoff,fp1.uy+yoff,textangle,s))
			output.print('<text x="0" y="0" class="ft" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux+xoff,fp1.uy+yoff,textangle,s))
			xoff+=fontstep
	output.print('<text x="0" y="0" class="fs" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux,fp1.uy,textangle,text))
	output.print('<text x="0" y="0" class="ft" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux,fp1.uy,textangle,text))

def print_lon_label_svg(output,lat1,lat2,lon,text,width,height,rotation,fontstep=8):
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
	# output.print('<polyline fill-opacity="0" stroke-opacity="1" stroke="#ffffff" points="%d,%d %d,%d"/>'%(fp1.ux,fp1.uy,fp2.ux,fp2.uy))
	if False:
		yoff=0
		for i in range(len(text)):
			s=text[i:i+1]
			xoff=islope*yoff
			output.print('<text x="0" y="0" class="fs" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux+xoff,fp2.uy+yoff,textangle,s))
			output.print('<text x="0" y="0" class="ft" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux+xoff,fp2.uy+yoff,textangle,s))
			yoff+=fontstep
	else:
		output.print('<text x="0" y="0" class="fs" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux,fp2.uy,textangle,text))
		output.print('<text x="0" y="0" class="ft" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux,fp2.uy,textangle,text))

class CornerCleave():
	def __init__(self,corner,xval,yval):
		self.corner=corner
		self.xval=xval
		self.yval=yval
	def cleave(self,sphereshape):
		sphereshape.cleave(self)
	def stitchsegments(self,one,two,onecrossu,twocrossu):
#		print('stitching corner %s to %s, onecrossu:%f, twocrossu:%f'%(one,two,onecrossu,twocrossu),file=sys.stderr)
		if self.corner==0:
			if onecrossu<=1 and twocrossu<=1:
				one.patchtype=VERT_PATCHTYPE
				one.next=two
			elif onecrossu>=1 and twocrossu>=1:
				one.patchtype=HORIZ_PATCHTYPE
				one.next=two
			else:
				mid=SpherePoint()
				mid.lon=0
				mid.lat=0
				mid.side=0
				mid.y=self.xval
				mid.z=self.yval
				mid.x=math.sqrt(1-mid.y*mid.y-mid.z*mid.z)
				if onecrossu<1:
					mid.patchtype=HORIZ_PATCHTYPE
					one.patchtype=VERT_PATCHTYPE
				else:
					mid.patchtype=VERT_PATCHTYPE
					one.patchtype=HORIZ_PATCHTYPE
#				print('Adding midpoint %s, between %s and %s'%(one,mid,two),file=sys.stderr)
				one.next=mid
				mid.next=two
				
		else: raise ValueError
	def getside(self,x,y,z):
		if self.corner==0: # bottom right
			if z<=self.yval and y>=self.xval:
				if z<self.yval and y>self.xval: return -1
				else: return 0
			else: return 1
		else: raise ValueError
	def setsides(self,points):
		yval=self.yval
		xval=self.xval
		hasneg=False
		haspos=False
		if self.corner==0: # bottom right
			for p in points:
				if p.z<=yval and p.y>=xval:
					if p.z<yval and p.y>xval:
						hasneg=True
						p.side=-1
					else:
						p.side=0
				else:
					haspos=True
					p.side=1
		else: raise ValueError
		if hasneg and haspos: return 0
		if hasneg: return 1
		return 2
	def makeintersectionpoint(self,s,n):
		if self.corner!=0: raise ValueError
		if s.patchtype==HEMI_PATCHTYPE:
			return Intersections.makeintersectionpoint(s,n,self)

		yval=self.xval
		zval=self.yval
		(inside,outside)=(s,n)
		if s.side<0: (inside,outside)=(n,s)

		dy=outside.y-inside.y
		dz=outside.z-inside.z

		if inside.y>yval and inside.z<zval:
			t=(yval-inside.y)/dy
			y1=yval
			z1=inside.z+t*dz

			t=(zval-inside.z)/dz
			z2=zval
			y2=inside.y+t*dy

			dd1=FlatPoint.distance2(y1,z1,inside.y,inside.z)
			dd2=FlatPoint.distance2(y2,z2,inside.y,inside.z)
			if dd1>dd2: (y,z)=(y1,z1)
			else: (y,z)=(y2,z2)
		elif inside.y<=yval:
			t=(yval-inside.y)/dy
			y=yval
			z=inside.z+t*dz
		else: # inside.z>=zval
			t=(zval-inside.z)/dz
			z=zval
			y=inside.y+t*dy

		if False: #idebug
			print('Creating intersection from %f,%f to %f,%f, made %f,%f'%(s.y,s.z,n.y,n.z,y,z),file=sys.stderr)


		x=math.sqrt(1-y*y-z*z)

		i=SpherePoint()
		i.lon=0
		i.lat=0
		i.side=0
		i.x=x
		i.y=y
		i.z=z
		i.patchtype=s.patchtype # s0 will change later after stitching
#		print('making intersection %s between %s and %s'%(i,s,n),file=sys.stderr)
		return i
	def setcrossus(self,intersections,spherepolygon):
		if self.corner==0: # 0..1 are vertical and 1..2 are horizontal
			for x in intersections.list:
				if x.s0.z<self.yval: x.crossu=1+x.s0.z
				else: x.crossu=1+x.s0.y
#				print('Setting crossu %f to %s'%(x.crossu,x.s0),file=sys.stderr)
		else: raise ValueError

def sphere_test(): # test simple sphere
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'
	admin0=Shp(install.getfilename('admin0-nolakes.shp',[scale]))
	admin0.loadshapes()

	print_header_svg(output,width,height,['sl','sp','debugl','c4'],isgradients=True)
	print_roundwater_svg(output,width)

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull='sl',csspatch='sp')

	dll=DegLonLat(0,0)
	dll_sphere_print_svg(output,dll,rotation,width,height,'c4')

	print_footer_svg(output)

class ShpAdminShape():
	def __init__(self,shape,nickname):
		self.nickname=nickname
		self.ccwtypes={}
		self.index=shape.index
		self.number=shape.number
		self.type=shape.type
		self.isclone=False
		if self.type==POLYGON_TYPE_SHP or self.type==POLYLINE_TYPE_SHP:
			self.partlist=shape.partlist
			self.pointlist=shape.pointlist
			self.mbr=shape.mbr
			self.partscount=shape.partscount
			self.pointscount=shape.pointscount
			self.draworderlist=[0]*self.partscount
		elif self.type==POINT_TYPE_SHP:
			self.point=shape.point
			self.draworder=0
		else: raise ValueError
	def extractpart(self,partindex):
		(start,limit)=Shape.getpartstartlimit(self,partindex)
		return self.pointlist[start:limit]
	def clonelists(self):
		if self.isclone: return
		self.partlist=self.partlist[:]
		points=[]
		for p in self.pointlist: points.append(p.clone())
		self.pointlist=points
		self.isclone=True
	def replacepart(self,partindex,points):
		self.clonelists()
		(start,limit)=Shape.getpartstartlimit(self,partindex)
		head=self.pointlist[0:start]
		tail=self.pointlist[limit:]
		self.pointlist=head+points+tail
		delta=limit-start-len(points)
		for i in range(partindex+1,self.partscount):
			self.partlist[i]-=delta
		self.pointscount-=delta
	def printparts(self,file=sys.stderr): return Shape.printparts(self,file=file)
	def getmbr(self,partindices): return Shape.getmbr(self,partindices)
	def getcenter(self,partindices): return Shape.getcenter(self,partindices)
	def setdraworder(self,partidx,draworder): return Shape.setdraworder(self,partidx,draworder)
	def hasdraworder(self,draworder):
		has=False
		hasmore=False
		if self.type==POINT_TYPE_SHP:
			if self.draworder==draworder: has=True
			elif self.draworder>draworder: hasmore=True
		else:
			for i in range(self.partscount):
				d=self.draworderlist[i]
				if d==draworder: has=True
				elif d>draworder: hasmore=True
		return (has,hasmore)
	def fixantarctica(self,partindex):
		points=self.extractpart(partindex)

		k=len(points)
		start=0
		stop=0
		for l in range(k):
			if points[l].lon>179.9999:
				start=l
				break
		else: raise ValueError
		for l in range(start+1,k):
			if points[l].lon<=179.9999: break
		else: raise ValueError
		for l in range(l,k):
			if points[l].lat>=-89.99: break
		else: raise ValueError
		for l in range(l,k):
			if points[l].lon>-179.9999: break
		else: raise ValueError
		stop=l
#		print('Warning: base data modified, Antarctica removing %d..%d of %d'%(start,stop,k),file=sys.stderr)
		del points[start:stop+1]

		self.replacepart(partindex,points)
	def fixrussia(self,partindex,tailpartindex,istrimhead=False,istrimtail=False):
		tailpoints=self.extractpart(tailpartindex)
		tailpg=Polygon.makefrompoints(tailpoints,True,self.index,tailpartindex)
		tailminus=WorldMinus(tailpg,nickname='Russia tail')
		fixcount=0

		i=0
		while i<len(tailminus.points):
			p=tailminus.points[i]
			if p.mlonlat[0]<=-1799999000:
				fixcount+=1
				if istrimtail:
					if p.mlonlat[1] > 650672363 and p.mlonlat[1] < 689834472:
						del tailminus.points[i]
						continue
				p.mlonlat=(1800000000,p.mlonlat[1])
			i+=1

		mainpoints=self.extractpart(partindex)
		mainpg=Polygon.makefrompoints(mainpoints,True,self.index,partindex)
		mainminus=WorldMinus(mainpg)

		if istrimhead:
			i=0
			while i<len(mainminus.points):
				p=mainminus.points[i]
				if p.mlonlat[0]>=1800000000:
					fixcount+=1
					if p.mlonlat[1] > 650672363 and p.mlonlat[1] < 689834472:
						del mainminus.points[i]
						continue
				i+=1

#		if fixcount: print('Fixed %d points in russiafix'%fixcount,file=sys.stderr)

		blob=WorldBlob(mainminus)
		if not blob.addtoblob_minus(tailminus): raise ValueError
		points=[]
		for p in blob.blob.points:
			points.append(p.dll)
		self.replacepart(partindex,points)
		self.replacepart(tailpartindex,[])

class ShpAdminShapeIntersection():
	def __init__(self):
		self.pointslist=[]
	def addpolygon(self,pg):
		if not pg.iscw: return # all polygons are CW
		points=[]
		for p in pg.points: points.append(p.clone())
		self.pointslist.append(points)
	def addfromplus(self,plus):
		pg=plus.polygons[0]
		self.addpolygon(pg)
	def addfromshapes(self,shapes,draworder):
		for shape in shapes:
			(has,_)=shape.hasdraworder(draworder)
			if not has: continue
			pluses=ShapePlus.make(shape)
			for plus in pluses:
				if plus.draworder!=draworder: continue
				self.addfromplus(plus)
	def clearside(self):
		for points in self.pointslist:
			for p in points: p.side=-1
	def setinside(self,shape):
		pluses=ShapePlus.make(shape)
		mbr=shape.getmbr([-1])
		for points in self.pointslist:
			for p in points:
				if p.side==1: continue
				if not p.isinmbr(mbr): continue
				for plus in pluses:
					pg=plus.polygons[0]
					if pg.isvertex(p.lon,p.lat) or pg.isinterior(p.lon,p.lat):
						p.side=1
						break
	def exportlines(self):
		ret=[]
		cur=None
		for points in self.pointslist:
			for p in points:
				if p.side!=1: break
			else: # entire polygon is inside
				pg=Polygon.makefrompoints(points,True,0,0) # all polygons are CW
				ret.append(ShapePlus.makefrompolygon(pg,0))
				continue
			lastp=None
			for p in points:
				if p.side==1:
					if not cur:
						cur=Polyline(0,0)
						if lastp: cur.addDegLonLat(lastp)
					cur.addDegLonLat(p)
				elif cur: # and side!=1
					cur.addDegLonLat(p)
					ret.append(ShapePlus.makefrompolyline(cur,0))
					cur=None
				lastp=p
			if cur:
				cur.addDegLonLat(points[0])
				ret.append(ShapePlus.makefrompolyline(cur,0))
				cur=None
		return ret

class ShpAdmin():
	def __init__(self,filename,scales):
		self.filename=filename
		self.installfile=install.getinstallfile(filename,scales)
		if not self.installfile:
			print('Couldn\'t find admin0 shp file (%s)'%str(scales),file=sys.stderr)
			raise ValueError
		self.scale=self.installfile.scale
		self.admin0shp=Shp(self.installfile.filename,self.installfile)
		if isverbose_global: print('Loading admin0 shape data (%s)'%self.scale,file=sys.stderr)
		self.admin0shp.loadshapes()
		self.shapes=[]
		self.bynickname={}

		dbfname=self.installfile.nickname[:-3]+'dbf'
		self.dbf=Dbf(install.getfilename(dbfname,[self.scale]))
		if isverbose_global: print('Loading admin0 dbf data (%s)'%self.scale,file=sys.stderr)
		self.dbf.selectcfield('SOV_A3','sov3')
		self.dbf.selectcfield('ADM0_A3','adm3')
		self.dbf.loadrecords()
		for i in range(self.dbf.numrecords):
			r=self.dbf.records[i]
			nickname=r['sov3']+'.'+r['adm3']
			self.addshape(self.admin0shp.shapes[i],nickname)
		self.islakesloaded=False
		self.isdisputedloaded=False
	def other_addshape(self,shapes,bynickname,shape,nickname):
		sas=ShpAdminShape(shape,nickname)
		bynickname[nickname]=sas
		shapes.append(sas)
	def addshape(self,shape,nickname):
		self.other_addshape(self.shapes,self.bynickname,shape,nickname)
	def setdraworder(self,index,partidx,draworder):
		shape=self.shapes[index]
		shape.setdraworder(partidx,draworder)
	def resetdraworder(self):
		for shape in self.shapes:
			shape.setdraworder(-1,0)
	def getcenter(self,index,partindices):
		return Shp.getcenter(self,index,partindices)
	def setccwtypes(self):
		if self.installfile.scale=='10m':
			if self.installfile.nickname=='admin0-lakes.shp':
				canada=self.shapes.bynickname['CAN.CAN']
				if canada.partscount==455:
					lakes=[1,2,3]
					for i in lakes: canada.ccwtypes[i]=REVERSE_CCWTYPE
	def fixantarctica(self):
		ata=self.bynickname['ATA.ATA']
		if self.installfile.scale=='50m':
			if ata.partscount!=108: raise ValueError
			ata.fixantarctica(2)
			ata.ccwtypes[2]=CW_CCWTYPE
		elif self.installfile.scale=='10m':
			if ata.partscount!=179: raise ValueError
			ata.fixantarctica(0)
			ata.ccwtypes[0]=CW_CCWTYPE
		else: raise ValueError
	def fixrussia(self):
		rus=self.bynickname['RUS.RUS']
		if self.installfile.scale=='50m':
			if rus.partscount!=101: raise ValueError
			rus.fixrussia(18,17,istrimtail=True)
			rus.ccwtypes[18]=CW_CCWTYPE
		elif self.installfile.scale=='10m':
			if rus.partscount!=214: raise ValueError
			rus.fixrussia(0,3) # this is for nolakes, lakes is probably 0,5
			rus.ccwtypes[0]=CW_CCWTYPE
		else: raise ValueError
	def makecyprusfull(self):
		nickname='_cyprusfull'
		names=['CYP.CYP','CNM.CNM','CYN.CYN']
		sc=ShapeCompress(-1)
		for n in names:
			if not n in self.bynickname: continue
			sc.addshape(self.bynickname[n])
		shape=sc.exportshape()
		self.addshape(shape,nickname)
	def loadlakes(self):
		if self.islakesloaded: return
		if isverbose_global: print('Loading lakes data (%s)'%self.scale,file=sys.stderr)
		self.islakesloaded=True
		self.lakes_ifile=install.getinstallfile('lakes.shp',[self.scale])
		if not self.lakes_ifile:
			print('Couldn\'t find lakes file (%s)'%self.scale,file=sys.stderr)
			raise ValueError
		self.lakes_shp=Shp(self.lakes_ifile.filename,self.lakes_ifile)
		self.lakes_shp.loadshapes()
		self.lakes_shapes=[]
		self.lakes_bynickname={}

		self.lakes_dbf=Dbf(install.getfilename('lakes.dbf',[self.scale]))
		if isverbose_global: print('Loading lakes dbf data (%s)'%self.scale,file=sys.stderr)
		self.lakes_dbf.selectcfield('name','name')
		self.lakes_dbf.loadrecords()

		for i in range(self.lakes_dbf.numrecords):
			r=self.lakes_dbf.records[i]
			nickname=r['name']
			self.other_addshape(self.lakes_shapes,self.lakes_bynickname,self.lakes_shp.shapes[i],nickname)
		if self.lakes_dbf.numrecords==275 and self.scale=='50m':
			nickpairs=((266,'_deadseasouth'),)
			for np in nickpairs:
				sas=self.lakes_shapes[np[0]]
				if sas.nickname: continue
				sas.nickname=np[1]
				self.lakes_bynickname[np[1]]=sas
		else:
			print('Unrecognized lakes, %d records at scale %s'%(self.lakes_dbf.numrecords,self.scale),file=sys.stderr)
	def getlakes(self):
		self.loadlakes()
		ret=[]
		for shape in self.lakes_shapes:
			pluses=ShapePlus.make(shape)
			for plus in pluses: ret.append(plus)
		return ret
	def loaddisputed(self):
		if self.isdisputedloaded: return
		if isverbose_global: print('Loading disputed data (%s)'%self.scale,file=sys.stderr)
		self.isdisputedloaded=True
		self.disputed_ifile=install.getinstallfile('admin0-disputed.shp',[self.scale])
		if not self.disputed_ifile:
			print('Couldn\'t find admin0 disputed file (%s)'%self.scale,file=sys.stderr)
			raise ValueError
		self.disputed_shp=Shp(self.disputed_ifile.filename,self.disputed_ifile)
		self.disputed_shp.loadshapes()
		self.disputed_shapes=[]
		self.disputed_bynickname={}

		self.disputed_dbf=Dbf(install.getfilename('admin0-disputed.dbf',[self.scale]))
		if isverbose_global: print('Loading disputed dbf data (%s)'%self.scale,file=sys.stderr)
		self.disputed_dbf.selectcfield('BRK_NAME','name')
		self.disputed_dbf.loadrecords()

		for i in range(self.disputed_dbf.numrecords):
			r=self.disputed_dbf.records[i]
			nickname=r['name']
			self.other_addshape(self.disputed_shapes,self.disputed_bynickname,self.disputed_shp.shapes[i],nickname)
	def selectdisputed(self,names,draworder):
		self.loaddisputed()
		for n in names:
			shape=self.disputed_bynickname[n]
			shape.setdraworder(-1,draworder)
	
def sphere2_test(): # test ShpAdmin
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.setccwtypes()

	(lon,lat)=admin0.bynickname['JPN.JPN'].getcenter([-1])
	rotation.set_deglonlat(lon,lat)

	scale=1
	if scale==1:
		bzc=None
	else:
		boxd=1/scale
		boff=-int(scale*width/2)+int(width/2)
		shift=Shift(boff,boff)
		bzc=BoxZoomCleave(scale,-boxd,boxd,-boxd,boxd,shift)

	cc=CornerCleave(0,0.1,-0.1)
	cc=None

	if scale==1:
		print_header_svg(output,width,height,['sl','sp','debugl','c4','sw','sr','sb'],isgradients=True)
		print_roundwater_svg(output,width)
	else:
		print_header_svg(output,width,height,['sl','sp','debugl','c4','sw','sr','sb'])

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull='sl',csspatch='sp',
				boxzoomcleave=bzc,cornercleave=cc)

	if False:
		dll=DegLonLat(-82.5,42.5)
		dll_sphere_print_svg(output,dll,rotation,width,height,'c4',boxzoomcleave=bzc)

	print_footer_svg(output)

def disputed_test(): # find disputed shapes
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.setccwtypes()
	admin0.loaddisputed()

	names=[
		'Arunachal Pradesh', # india and china
		'Tirpani Valleys', # india and china, border
		'Bara Hotii Valleys', # india and china, border
		'Demchok', # kashmir and china, border, redundant
		'Samdu Valleys', # india and china, border
		'Jammu and Kashmir', # india and pakistan and china, kashmir
		'Shaksam Valley', # india pakistan and china
		'Aksai Chin', # india and china
		'Northern Areas', # pakistan and india and china, north of kashmir
		'Abyei', # sudan and southsudan
		'Lawa Headwaters', # suriname and france
		'Courantyne Headwaters', # guyana and suriname
		'Golan Heights', # israel and lebanon
		'Ilemi Triangle', # kenya and south sudan
		'W. Sahara', # w sahara and morocco
		'N. Cyprus', # north cyprus separatists
		'Kuril Is.', # japan and russia
		'Somaliland', # somaliland and somalia
		'Abkhazia', # georgia separatists
		'Transnistria', # moldova separatists
		'South Ossetia', # georgia separatists
		'Nagorno-Karabakh', # azerbaijan separatists
		'Siachen Glacier', # pakistan and india
		'Crimea', # ukraine and russia
		'Donbass' # ukraine separatists
		]
	name=names[24]
	scale=4
	print('Inspecting %s'%name,file=sys.stderr)

	disputed=admin0.disputed_bynickname[name]

	(lon,lat)=disputed.getcenter([-1])
	rotation.set_deglonlat(lon,lat)
	if scale==1:
		bzc=None
		print_header_svg(output,width,height,['sl','sp','debugl','debuggreen','c4','sw','sr','sb'],isgradients=True)
		print_roundwater_svg(output,width)
	else:
		boxd=1/scale
		boff=-int(scale*width/2)+int(width/2)
		shift=Shift(boff,boff)
		bzc=BoxZoomCleave(scale,-boxd,boxd,-boxd,boxd,shift)
		print_header_svg(output,width,height,['sl','sp','debugl','debuggreen','c4','sw','sr','sb'])

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull='sl',csspatch='sp',
				boxzoomcleave=bzc)
	one_sphere_print_svg(output,disputed,0,rotation,width,height,8,cssfull='debuggreen',csspatch='sp',
			boxzoomcleave=bzc)

	print_footer_svg(output)

def borderlakes_test(): # find lakes that intersect with borders
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.setccwtypes()
	admin0.loadlakes()

	(lon,lat)=admin0.bynickname['IS1.ISR'].getcenter([-1])
	rotation.set_deglonlat(lon,lat)

	scale=32
	if scale==1:
		bzc=None
	else:
		boxd=1/scale
		boff=-int(scale*width/2)+int(width/2)
		shift=Shift(boff,boff)
		bzc=BoxZoomCleave(scale,-boxd,boxd,-boxd,boxd,shift)
	cc=None

	if scale==1:
		print_header_svg(output,width,height,['sl','sp','debugl','c4','sw','sr','sb','ft','fs'],isgradients=True)
		print_roundwater_svg(output,width)
	else:
		print_header_svg(output,width,height,['sl','sp','debugl','c4','sw','sr','sb','ft','fs'])

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull='sl',csspatch='sp',
				boxzoomcleave=bzc,cornercleave=cc)

	pluses=admin0.getlakes()
	for plus in pluses:
		plus.shape
		oneplus_sphere_print_svg(output,plus,rotation,width,height,4, cssfull='sw',csspatch='sr',
				boxzoomcleave=bzc,cornercleave=cc)
		p=plus.polygons[0].points[0]
		if text_sphere_print_svg(output,p,str(plus.shape.index),rotation,width,height,cssfont='ft',cssfontshadow='fs', boxzoomcleave=bzc):
			print('%d:"%s" '%(plus.shape.index,plus.shape.nickname),file=sys.stderr)
			if scale!=1:
				q=p.clone()
				q.lat-=2/scale
				text_sphere_print_svg(output,q,plus.shape.nickname,rotation,width,height,cssfont='ft',cssfontshadow='fs', boxzoomcleave=bzc)

	print_footer_svg(output)

def sphere3_test(): # test merging ShapePlus to reduce border drawing, this is obsolete by WorldCompress and worldcompress_test
	output=Output()
	width=500
	height=500
	lat_center=0
	lon_center=0
	rotation=SphereRotation()

	admin0=Shp(install.getfilename('admin0.shp'))
	admin0.loadshapes()
	admin0dbf=Dbf(install.getfilename('admin0.dbf'))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.loadrecords()
	indices=[]
	gsgs=['ZAF.ZAF','SWZ.SWZ','MOZ.MOZ','TZA.TZA','KEN.KEN','BWA.BWA','ZWE.ZWE']

	# indices.append(admin0dbf.query1({'sov3':'NAM','adm3':'NAM'}))
	for gsg in gsgs:
		(grp,subgrp)=gsg.split('.')
		indices.append(admin0dbf.query1({'sov3':grp,'adm3':subgrp}))

	print_header_svg(output,width,height,['sl','sp','sb'])
	print_rectangle_svg(output,0,0,width,height,'#ffffff',1.0)

	one=admin0.shapes[admin0dbf.query1({'sov3':'NAM','adm3':'NAM'})]
	pluses=ShapePlus.make(one)
	if len(pluses)!=1: raise ValueError
	mainplus=pluses[0]
	allpluses=[]
	allextracts=[]
	for index in indices:
		one=admin0.shapes[index]
		pluses=ShapePlus.make(one)
		for pl in pluses:
			extract=mainplus.augment(pl,True)
			if not extract: allpluses.append(pl)
			else: allextracts.append(extract)
	allpluses.append(mainplus)
	allpluses=[mainplus]
	hc=HemiCleave()
	for oneplus in allpluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			flatshape=onesphere.flatten(width,height,8)
			flatshape.printsvg(output,cssfull='sl',csspatch='sp')
	if False:
		for onepl in allextracts:
			oneplus=ShapePlus.makefrompolyline(onepl,0)
			onesphere=SphereShape(oneplus,rotation)
			hc.cleave(onesphere)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height,8)
				flatshape.printsvg(output,cssline='sb')
	print_footer_svg(output)

def isallin(big,small):
	for s in small:
		if not s in big: return False
	return True

def nocompressshapes(shp,draworder):
	allpluses=[]
	for s in shp.shapes:
		if s.draworder!=draworder: continue
		pluses=ShapePlus.make(s)
		for pl in pluses: allpluses.append(pl)
	return allpluses

def compressshapes(shp,draworder):
	allpluses=[]
	extracts=[]
	bygsg={}
	for s in shp.shapes:
		if s.draworder!=draworder: continue
		bygsg[s.nickname]=s

	groups=[]
	groups.append(['VNM.VNM','LAO.LAO','KHM.KHM','THA.THA','MMR.MMR'])
	groups.append(['BRN.BRN','MYS.MYS','IDN.IDN'])
	groups.append(['MNG.MNG','CH1.CHN','RUS.RUS','PRK.PRK','KOR.KOR'])
	groups.append(['BGD.BGD','IND.IND','NPL.NPL','BTN.BTN','PAK.PAK','AFG.AFG'])
	groups.append(['SAU.SAU','YEM.YEM','OMN.OMN','ARE.ARE'])
	groups.append(['IRQ.IRQ','KWT.KWT','IRN.IRN','SYR.SYR','TUR.TUR','JOR.JOR'])
	groups.append(['KAZ.KAZ','UZB.UZB','ARM.ARM','KGZ.KGZ','TJK.TJK','TKM.TKM','AZE.AZE','GEO.GEO'])
	groups.append(['ETH.ETH','SOM.SOM','SOL.SOL','DJI.DJI','ERI.ERI','KEN.KEN','TZA.TZA','UGA.UGA','RWA.RWA','BDI.BDI'])
	groups.append(['PRT.PRT','ESP.ESP'])
	groups.append(['MAR.MAR','SAH.SAH','DZA.DZA','MLI.MLI','MRT.MRT','TUN.TUN'])
	groups.append(['PRY.PRY','ARG.ARG','BRA.BRA','BOL.BOL','URY.URY','GUY.GUY','SUR.SUR','VEN.VEN','COL.COL','ECU.ECU','PER.PER','CHL.CHL'])
	groups.append(['LBY.LBY','EGY.EGY','SDN.SDN','SDS.SDS','TCD.TCD','CAF.CAF'])
	groups.append(['MOZ.MOZ','MWI.MWI','ZWE.ZWE','BWA.BWA','ZMB.ZMB','COD.COD','NAM.NAM','AGO.AGO','COG.COG','GAB.GAB','GNQ.GNQ'])
	groups.append(['CMR.CMR','NGA.NGA','NER.NER'])
	groups.append(['SEN.SEN','GNB.GNB','GIN.GIN','LBR.LBR','CIV.CIV','GHA.GHA','TGO.TGO','BEN.BEN','BFA.BFA','SLE.SLE'])
	groups.append(['SWE.SWE','FI1.FIN','NOR.NOR'])
	groups.append(['EST.EST','LVA.LVA','LTU.LTU','POL.POL','BLR.BLR','UKR.UKR','MDA.MDA'])

	groups.append(['CZE.CZE','SVK.SVK','HUN.HUN','AUT.AUT','DEU.DEU','ROU.ROU','BGR.BGR','CHE.CHE','ITA.ITA','NL1.NLD','BEL.BEL',
			'HRV.HRV','SVN.SVN','BIH.BIH','MNE.MNE','SRB.SRB','MKD.MKD','GRC.GRC','KOS.KOS','ALB.ALB'])

	groups.append(['CAN.CAN','US1.USA','MEX.MEX'])
	groups.append(['GTM.GTM','BLZ.BLZ','HND.HND','NIC.NIC','CRI.CRI','SLV.SLV','PAN.PAN'])
	
	for g in groups:
		if isverbose_global: print('Compressing borders for group %s'%g,file=sys.stderr)
		if not isallin(bygsg,g): continue
		n=g[0]
		one=bygsg[n]
		del bygsg[n]
		pluses=ShapePlus.make(one)
		mainplus=pluses[0]
		for i in range(1,len(pluses)): allpluses.append(pluses[i])
		for i in range(1,len(g)):
			n=g[i]
			one=bygsg[n]
			del bygsg[n]
			pluses=ShapePlus.make(one)
			for pl in pluses:
				extract=mainplus.augment(pl,True)
				if not extract: allpluses.append(pl)
				else: extracts.append(extract)
		allpluses.append(mainplus)	

	for n in bygsg:
		s=bygsg[n]
		pluses=ShapePlus.make(s)
		for p in pluses: allpluses.append(p)
	for x in extracts:
		oneplus=ShapePlus.makefrompolyline(x,draworder)
		allpluses.append(oneplus)

	return allpluses

def sphere4_test(): # merge ShapePlus to reduce border drawing, this is obsolete by WorldCompress and worldcompress_test
# start with 43493
# ended with 38432
	output=Output()
	width=1000
	height=1000
	lat_center=0
	lon_center=0
	rotation=SphereRotation()
	rotation.set_deglonlat(2.213390,23)

	admin0=Shp(install.getfilename('admin0.shp',['10m']))
	admin0.loadshapes()
	admin0dbf=Dbf(install.getfilename('admin0.dbf',['10m']))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.loadrecords()
	for i in range(admin0dbf.numrecords):
		r=admin0dbf.records[i]
		nickname=r['sov3']+'.'+r['adm3']
		admin0.setnickname(i,nickname)

	hindex=admin0dbf.query1({'sov3':'IDN','adm3':'IDN'})
	admin0.setdraworder(hindex,-1,1)

	if True:
		allpluses=compressshapes(admin0,0)
	else:
		allpluses=nocompressshapes(admin0,0)

	hpluses=[]
	if True:
		one=admin0.shapes[hindex]
		pluses=ShapePlus.make(one)
		for p in pluses: hpluses.append(p)

	print_header_svg(output,width,height,['sb','sl','sp','si','sh','sq'],isgradients=True)
	print_rectangle_svg(output,0,0,width,height,'#ffffff',1.0)
	print_roundwater_svg(output,width)

	hc=HemiCleave()
	for oneplus in allpluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			if onesphere.type==POLYLINE_TYPE_SHP:
				pass
			else:
				flatshape=onesphere.flatten(width,height,8)
				flatshape.printsvg(output,cssline='sb',cssfull='sl',csspatch='sp')
	for oneplus in hpluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			flatshape=onesphere.flatten(width,height,8)
			flatshape.printsvg(output,cssline='si',cssfull='sh',csspatch='sq')

	print_footer_svg(output)

def lonlat_test(): # test lon/lat text labels
	output=Output()
	width=1000
	height=1000
	lat_center=-20
	lon_center=25

	rotation=SphereRotation()
	rotation.set_deglonlat(lon_center,lat_center)
	print_header_svg(output,width,height,['ft','fs','sg'],isgradients=True)
	print_roundwater_svg(output,width)
	arcs_lonlat_print_svg(output,rotation,width,height)
	labely=rotation.dlon
	if labely<0: labely=15.0
	else: labely=-15.0
	for label in [ (-150,'150°W'), (-120,'120°W'), (-90,'90°W'), (-60,'60°W'), (-30,'30°W'),
			(0,'0°'), (30,'30°E'), (60,'60°E'), (90,'90°E'), (120,'120°E'), (150,'150°E'), (180,'180°')]:
		print_lon_label_svg(output,10,15,label[0],label[1],width,height,rotation,8)

	for label in [ (-60,'60°S'), (-30,'30°S'), (0,'0°'), (30,'30°N'), (60,'60°N')]:
		print_lat_label_svg(output,70,75,label[0]+0.5,label[1],width,height,rotation,8)
	print_footer_svg(output)

def print_ellipse_svg(output,cx,cy,rx,ry):
	xl=cx-rx
	xr=cx+rx
	output.print('<path d="M %d %d A %d %d, 0, 0 0, %d %d" style="stroke:black; fill-opacity:0"/>'% (xl,cy,rx,ry,xr,cy ))
	output.print('<path d="M %d %d A %d %d, 0, 0 1, %d %d" style="stroke:black; fill-opacity:0"/>'% (xl,cy,rx,ry,xr,cy ))

def findlonend(rotation):
	sp1=SpherePoint.makefromcircle(90,rotation)
	sp2=SpherePoint.makefromcircle(-90,rotation)
	if sp1.x>0 and sp2.x<0:
		start=90
		limit=-90
	elif sp1.x<0 and sp2.x>0:
		start=-90
		limit=90
	elif abs(sp1.x)<0.000001 and abs(sp2.x)<0.000001:
		return 90
	else:
		print('sp1.x:%f sp2.x:%f'%(sp1.x,sp2.x),file=sys.stderr)
		raise ValueError
	while True:
		t=(start+limit)/2
#		print('trying t:%d'%t,file=sys.stderr)
		sp=SpherePoint.makefromcircle(t,rotation)
		if abs(sp.x)<0.0000001: break
		if sp.x>0:
			start=t
		else:
			limit=t
	return t

def findlatstart(rotation,latdeg,isstart):
	sp=SpherePoint.makefromlonlat(0,latdeg,rotation)
	if sp.x<=0: raise ValueError
	start=0
	limit=180
	if isstart: limit=-180
	while True:
		t=(start+limit)/2
		sp=SpherePoint.makefromlonlat(t,latdeg,rotation)
		if abs(sp.x)<0.000001: break
		if sp.x>0:
			start=t
		else:
			limit=t
	return sp
	
class FlatCircle():
	def __init__(self,points):
		self.points=points
	def printsvg(self,output,cssclass):
		for p in self.points:
			output.print('<rect x="%d" y="%d" width="2" height="2" fill="%s"/>'%(p.ux,p.uy,p.color))

class SphereCircle():
	def __init__(self,rotation):
		self.rotation=rotation
		self.points=[]
		for i in range(360):
			self.points.append(SpherePoint.makefromcircle(i,rotation))
	def flatten(self,width,height):
		flat=[]
		for p in self.points:
			color='#555555'
			if p.x>=0: color='#00ff00'
			fp=p.flatten(width,height)
			fp.color=color
			flat.append(fp)
		return FlatCircle(flat)

class FlatLongitude():
	def __init__(self,left,right,top,bottom,angle,londeg,tiltdeg):
		self.left=left
		self.right=right
		self.top=top
		self.bottom=bottom
		self.angle=angle
		self.londeg=londeg
		self.tiltdeg=tiltdeg
	def printsvg(self,output,cssclass):
		x1=self.left.ux
		y1=self.left.uy
		x2=self.right.ux
		y2=self.right.uy
		ry=self.left.distanceto(self.right)/2.0
		rx=self.top.distanceto(self.bottom)/2.0
		rotdeg=self.angle

		if rx<1 or ry<1:
			output.print('<path class="%s" d="M%d,%dL%d,%dZ"/>'%(cssclass,x1,y1,x2,y2))
			return

		if False:
			output.print('<polyline style="stroke:purple;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.left.ux,self.left.uy, self.right.ux,self.right.uy))
			output.print('<polyline style="stroke:cyan;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.top.ux,self.top.uy, self.bottom.ux,self.bottom.uy))
		if self.tiltdeg>=0:
			if self.londeg>90:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))
			else:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))
		else:
			if self.londeg>90:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))
			else:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))

class SphereLongitude():
	@staticmethod
	def make(rotation_in,londeg):
		deg=londeg-rotation_in.dlon+90
		while deg<=0: deg+=360
		if deg>=180: return None
#		print('londeg:%f rotation_in.dlon:%f -> deg:%f'%(londeg,rotation_in.dlon,deg),file=sys.stderr)
		rotation=SphereRotation()
		rotation.set_deglonlat(-deg,rotation_in.dlat)
		self=SphereLongitude()
		self.rotation=rotation
		ao=findlonend(rotation)
		self.ao=ao
		self.left=SpherePoint.makefromcircle(180+ao,rotation)
		self.right=SpherePoint.makefromcircle(0+ao,rotation)
		self.top=SpherePoint.makefromcircle(90+ao,rotation)
		self.bottom=SpherePoint.makefromcircle(270+ao,rotation)
		rotdeg=90-(180.0*getangle(0,0,self.right.y,self.right.z))/math.pi
		self.rotdeg=rotdeg
		self.deg=deg
		self.tiltdeg=rotation_in.dlat
		return self
	def flatten(self,width,height):
		return FlatLongitude( self.left.flattenf(width,height), self.right.flattenf(width,height),
				self.top.flattenf(width,height), self.bottom.flattenf(width,height), self.rotdeg,self.deg,self.tiltdeg)

class FlatLatitude():
	def __init__(self,left,right,top,bottom,start,stop,tiltdeg,latdeg):
		self.left=left
		self.right=right
		self.top=top
		self.bottom=bottom
		self.start=start
		self.stop=stop
		self.tiltdeg=tiltdeg
		self.latdeg=latdeg
	def printsvg(self,output,cssclass):
		x1=self.start.ux
		y1=self.start.uy
		x2=self.stop.ux
		y2=self.stop.uy
		rx=self.left.distanceto(self.right)/2.0
		ry=self.top.distanceto(self.bottom)/2.0
		if rx<1 or ry<1:
			output.print('<path class="%s" d="M%d,%dL%d,%dZ"/>'%(cssclass,x1,y1,x2,y2))
			return
		if False:
			output.print('<polyline style="stroke:purple;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.left.ux,self.left.uy, self.right.ux,self.right.uy))
			output.print('<polyline style="stroke:cyan;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.top.ux,self.top.uy, self.bottom.ux,self.bottom.uy))
		if self.tiltdeg>0:
			if self.latdeg>0:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 1 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))
			else:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 0 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))
		else:
			if self.latdeg>0:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 0 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))
			else:
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 1 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))

class SphereLatitude():
	def __init__(self,tiltdeg,latdeg):
		self.tiltdeg=tiltdeg
		self.latdeg=latdeg
		sr=SphereRotation()
		sr.set_deglonlat(0,tiltdeg)
		self.left=SpherePoint.makefromlonlat(-90,latdeg,sr)
		self.right=SpherePoint.makefromlonlat(90,latdeg,sr)
		self.bottom=SpherePoint.makefromlonlat(0,latdeg,sr)
		self.top=SpherePoint.makefromlonlat(180,latdeg,sr)
		self.start=findlatstart(sr,latdeg,True)
		self.stop=findlatstart(sr,latdeg,False)
		self.tiltdeg=tiltdeg
		self.latdeg=latdeg
	def flatten(self,width,height):
		return FlatLatitude( self.left.flattenf(width,height), self.right.flattenf(width,height),
				self.top.flattenf(width,height), self.bottom.flattenf(width,height),
				self.start.flattenf(width,height), self.stop.flattenf(width,height),self.tiltdeg,self.latdeg)

def lonlat2_test(): # test ellipse paths for lines
	output=Output()
	width=1000
	height=1000
	print_header_svg(output,width,height,['sg'],isgradients=True)
	print_roundwater_svg(output,width)
#	for i in range(8): lon=i*45+10
	for lon in [ 0, -30, -60, -90, 30, 60 ]:
		lon+=10
		rotation=SphereRotation()
		rotation.set_deglonlat(lon,23)
		c=SphereCircle(rotation)
		fc=c.flatten(width,height)
		fc.printsvg(output,'sg')
	for lon in [ 0, -30, -60, -90, 30, 60 ]:
		lon+=10
		rotation=SphereRotation()
		rotation.set_deglonlat(lon,23)
		e=SphereLongitude.make(rotation,0) # 0 is untested, we changed how this works
		if e==None: continue
		fe=e.flatten(width,height)
		fe.printsvg(output,'sg')
	print_footer_svg(output)
	

def dicttostr(label,d):
	isfirst=True
	a=[]
	a.append(label+' : {')
	for n in d:
		a.append('\t\''+str(n)+'\' : \''+str(d[n])+'\'')
	a.append('}')
	return '\n'.join(a)

def loaddbf_locatormap(shp):
	dbf=Dbf(install.getfilename('admin0.dbf',[shp.installfile.scale]))
	if isverbose_global: print('Loading admin0 dbf data (%s)'%shp.installfile.scale,file=sys.stderr)
	dbf.selectcfield('SOV_A3','sov3')
	dbf.selectcfield('ADM0_A3','adm3')
	dbf.loadrecords()
	for i in range(dbf.numrecords):
		r=dbf.records[i]
		nickname=r['sov3']+'.'+r['adm3']
		shp.setnickname(i,nickname)
	return dbf

def loadshp_locatormap(m):
	ifile=install.getinstallfile('admin0.shp',[m])
	if not ifile:
		print('Couldn\'t find admin0 shp file (%s)'%m,file=sys.stderr)
		raise ValueError
	shp=Shp(ifile.filename,ifile)
	if isverbose_global: print('Loading admin0 shape data (%s)'%m,file=sys.stderr)
	shp.loadshapes()
	return shp

def getmoption(options,key,mkey,dest=None):
	if not dest: dest=key
	n=key+'_'+options[mkey]
	if n not in options: return
	options[dest]=options[n]

def	admin0_setccwtypes(shp): # TODO move this over to ShpAdmin
	if shp.installfile.nickname=='admin0-lakes.shp':
		if shp.installfile.scale=='10m':
			canada=shp.bynickname['CAN.CAN']
			if canada.partscount==455:
				lakes=[1,2,3]
#				print('Setting reverse types',file=sys.stderr)
				for i in lakes: canada.ccwtypes[i]=REVERSE_CCWTYPE

def locatormap(output,overrides):
	options={}
	options['comment']=''
	options['copyright']=''
	options['index']=-1
	options['full_index']=-1
	options['zoom_index']=-1
	options['partindices']=[-1]
	options['full_partindices']=[-1]
	options['zoom_partindices']=[-1]
	options['istripelinset']=True
	options['isinsetleft']=True
	options['iszoom']=False
	options['iszoom34']=False
	options['width']=1000
	options['height']=1000
	options['zoomscale']=2
	options['isroundwater']=True
	options['islakes']=True
	options['iszoomlakes']=True
	options['issubland']=False # needs updating to work
	options['ispartlabels']=False
	options['isfullpartlabels']=False
	options['istopinsets']=False
	options['labelfont']='14px sans'
#	options['labelfontstep']=8
	options['spherem']='10m'
	options['zoomm']='10m'
	options['fullm']='10m'
	options['splitlimit']=4
	options['isfullhighlight']=False
	options['isdisputed']=False

	if True:
		pub=dict(overrides)
		if 'copyright' in pub: del pub['copyright']
		options['comment']=dicttostr('settings',pub)
	for n in overrides: options[n]=overrides[n]

	full_admin0=ShpAdmin('admin0-nolakes.shp',[options['fullm']])

	sphere_admin0=ShpAdmin('admin0-nolakes.shp',[options['spherem']])
	sphere_admin0.fixantarctica()
	sphere_admin0.fixrussia()
	sphere_admin0.setccwtypes()
	sphere_admin0.loadlakes()

	if options['zoomm']==options['spherem']:
		zoom_admin0=sphere_admin0
	else:
		zoom_admin0=ShpAdmin('admin0-nolakes.shp',[options['zoomm']])
		zoom_admin0.fixantarctica()
		zoom_admin0.fixrussia()
		zoom_admin0.setccwtypes()
		zoom_admin0.loadlakes()

	if 'gsg' in options:
		l=((sphere_admin0,'index'),(full_admin0,'full_index'),(zoom_admin0,'zoom_index'))
		gsg=options['gsg']
		for p in l:
			s=p[0].bynickname.get(gsg,None)
			options[p[1]]=s.index if s else -1

	index=options['index']
	full_index=options['full_index']
	zoom_index=options['zoom_index']

	if full_index<0:
		print('No location specified?',file=sys.stderr)
		return

	if options['issubland']:
		if 'grp' not in options:
			a0r=admin0dbf.records[index]
			options['grp']=a0r['sov3']
			options['subgrp']=a0r['adm3']

	if 'lon' not in options or 'lat' not in options:
		n='centerindices_'+options['fullm']
		if n in options: (lon,lat)=full_admin0.getcenter(full_index,options[n])
		else:
			n='centerindices_'+options['spherem']
			if n in options: (lon,lat)=sphere_admin0.getcenter(full_index,options[n])
			else:
				(lon,lat)=full_admin0.getcenter(full_index,[-1])
		if 'lon' not in options: options['lon']=lon
		if 'lat' not in options: options['lat']=lat
		if isverbose_global: print('Geographic center: (lon,lat)=(%f,%f)'%(lon,lat),file=sys.stderr)

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

	getmoption(options,'tripelboxes','fullm')
	if 'tripelboxes' not in options: options['tripelboxes']=[[-1]]

	for p in [ ('smalldots_10m','moredots_10m'), ('smalldots_50m','moredots_50m'), ('smalldots_110m','moredots_110m')]:
		if p[0] in options:
			if p[1] in options: raise ValueError
			options[p[1]]=[(4,False,options[p[0]])]

	getmoption(options,'moredots','fullm')
	getmoption(options,'zoomdots','fullm')
	getmoption(options,'partindices','spherem')
	getmoption(options,'partindices','fullm','full_partindices')
	getmoption(options,'partindices','zoomm','zoom_partindices')

	if 'disputed' in options or 'disputed_border' in options:
		options['isdisputed']=True
		if not 'disputed' in options: options['disputed']=[]
		if not 'disputed_border' in options: options['disputed_border']=[]

	combo_print_svg(output,options,full_admin0,sphere_admin0,zoom_admin0)

def euromap(output,overrides):
	options={}
	options['comment']=''
	options['copyright']=''
	options['width']=1000
	options['height']=1000
	options['islakes']=True
	options['spherem']='10m'
	options['splitlimit']=4
	options['labelfont']='14px sans'
	options['gsgs']=None
	options['borderlakes']=[]
	options['ispartlabels']=False
	options['euromapdots_50m']=None
	allowedoverrides=['comment','copyright','width','height','islakes','spherem','splitlimit','labelfont','gsgs','borderlakes',
			'ispartlabels','euromapdots_50m']
	publicoverrides=['comment','width','height','islakes','spherem','splitlimit','labelfont','gsg','gsgs','borderlakes',
			'ispartlabels','euromapdots_50m']

	if 'gsg' in overrides: options['gsgs']=[overrides['gsg']]
	if True:
		pub={}
		for n in overrides:
			 if n in publicoverrides: pub[n]=overrides[n]
		options['comment']=dicttostr('settings',pub)

	for n in overrides:
		 if n in allowedoverrides: options[n]=overrides[n]

	width=options['width']
	height=options['height']
	splitlimit=options['splitlimit']
	moredots=options['euromapdots_50m']
	rotation=SphereRotation()

	admin0=ShpAdmin('admin0-nolakes.shp',[options['spherem']])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.makecyprusfull()
	admin0.setccwtypes()
	admin0.loadlakes()

	(lon,lat)=admin0.bynickname['DEU.DEU'].getcenter([-1])
	rotation.set_deglonlat(lon-6,lat)

	zoomscale=2
	boxd=1/zoomscale
	boff=-int(zoomscale*width/2)+int(width/2)
	shift=Shift(boff,boff)
	bzc=BoxZoomCleave(zoomscale,-boxd,boxd,-boxd,boxd,shift)

	cc=None

# Austria Belgium Bulgaria Croatia Cyprus(whole) Czech Denmark Estonia Finland France
# Germany Greece Hungary Ireland Italy Latvia Lithuania Luxembourg Malta Netherlands Poland Portugal
# Romania Slovakia Slovenia Spain Sweden

	eugsgs=['AUT.AUT','BEL.BEL','BGR.BGR','HRV.HRV','_cyprusfull','CZE.CZE','DN1.DNK','EST.EST','FI1.FIN','FR1.FRA',
			'DEU.DEU','GRC.GRC','HUN.HUN','IRL.IRL','ITA.ITA','LVA.LVA','LTU.LTU','LUX.LUX','MLT.MLT','NL1.NLD','POL.POL','PRT.PRT',
			'ROU.ROU','SVK.SVK','SVN.SVN','ESP.ESP','SWE.SWE']
# 'CYP.CYP','CYN.CYN','CNM.CNM'
	for gsg in eugsgs:
		admin0.bynickname[gsg].setdraworder(-1,1)
	for gsg in ['AND.AND','CHE.CHE']:
		admin0.bynickname[gsg].setdraworder(-1,2)

	eu_wc=WorldCompress(admin0,-1,source_draworder=1)
	iscompressscandinavia=True
	if 'SWE.SWE' in options['gsgs'] or 'FI1.FIN' in options['gsgs']: iscompressscandinavia=False
	eu_wc.addeuro(iscompressscandinavia)
	other_wc=WorldCompress(admin0,-1)
	other_wc.addafrica()
	other_wc.addmiddleeast()

	css=['sl','sp','sb','al','ap','ab','sw','sr']

	if moredots:
		m=['c1','w1']
		for c in m: css.append(c)

	if options['gsgs']:
		for gsg in options['gsgs']:
			if gsg in admin0.bynickname: admin0.bynickname[gsg].setdraworder(-1,3)
			else: print('Skipping gsg:%s, not found in %s'%(gsg,options['spherem']),file=sys.stderr)
		css.append('sh')
		css.append('sq')

	eu_wc.removeoverlaps(admin0.shapes,3) # remove draworder 3 (highlights) from border polylines

	euborderlakeshapes=[]
	if 'EST.EST' not in options['gsgs']: 
		euborderlakes=['Pskoyskoye Ozero', 'Lake Peipus']
		sasi=ShpAdminShapeIntersection()
		pluses=eu_wc.getpluses(isnegatives=False,isoverlaps=False)
		for plus in pluses:
			sasi.addfromplus(plus)
		for n in euborderlakes:
			l=admin0.lakes_bynickname[n]
			if not l:
				print('Border lake (%s) not found: %s'%(options['spherem'],n),file=sys.stderr)
				continue
			sasi.setinside(l)
		euborderlakeshapes=sasi.exportlines()

	gsgborderlakeshapes=[]
	if True:
		sasi=ShpAdminShapeIntersection()
		sasi.addfromshapes(admin0.shapes,3)
		for n in options['borderlakes']:
			l=admin0.lakes_bynickname[n]
			if not l:
				print('Border lake (%s) not found: %s'%(options['spherem'],n),file=sys.stderr)
				continue
			sasi.setinside(l)
		gsgborderlakeshapes=sasi.exportlines()
		if len(gsgborderlakeshapes): css.append('si')

	print_header_svg(output,width,height,css,options['labelfont'],[options['copyright'],options['comment']])
	print_squarewater_svg(output,width)

	if True: # draw plain background countries
		for one in admin0.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull='sl',csspatch='sp',
					boxzoomcleave=bzc,cornercleave=cc)

	if True: # draw worldcompress continents
		pluses=other_wc.getpluses(isnegatives=False,isoverlaps=False)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull='sl',csspatch='sp',boxzoomcleave=bzc)

		pluses=eu_wc.getpluses(isnegatives=False,isoverlaps=False)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull='al',csspatch='ap',boxzoomcleave=bzc)

	if True: # draw andorra, switzerland, halflights and highlights
		for one in admin0.shapes:
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull='sl',csspatch='sp',
					boxzoomcleave=bzc,cornercleave=cc)

		for one in admin0.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull='al',csspatch='ap',
					boxzoomcleave=bzc,cornercleave=cc)

		for one in admin0.shapes:
			one_sphere_print_svg(output,one,3,rotation,width,height,splitlimit,cssfull='sh',csspatch='sq',
					boxzoomcleave=bzc,cornercleave=cc,islabels=options['ispartlabels'])

	if True: # draw continent ccws
		negatives=eu_wc.getnegatives()
		pluses_sphere_print_svg(output,negatives,rotation,width,height,splitlimit, cssfull='sw',csspatch='sr',boxzoomcleave=bzc)
		negatives=other_wc.getnegatives()
		pluses_sphere_print_svg(output,negatives,rotation,width,height,splitlimit, cssfull='sw',csspatch='sr',boxzoomcleave=bzc)

	if True: # draw lakes
		pluses=admin0.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull='sw',csspatch='sr',boxzoomcleave=bzc)

	if True: # draw continent borders, intersections with highlights already removed
		pluses=other_wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssline='sb',boxzoomcleave=bzc)
		pluses=eu_wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssline='ab',boxzoomcleave=bzc)

	if True: # draw highlight intersections with lakes over lakes
		for plus in euborderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline='sb',boxzoomcleave=bzc)
		for plus in gsgborderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline='si',boxzoomcleave=bzc)

	if moredots:
		for dots in moredots:
			gsg=dots[0]
			shape=admin0.bynickname[gsg]
			sds=int((dots[1]*width)/1000)
			isw=dots[2]
			smalldots=dots[3]
			cssclass='c1' # only c1/w1 are included in css above
			if isinstance(isw,bool) and isw: cssclass='c4'
			elif isw==1: cssclass='c1'
			elif isw==2: cssclass='c2'
			elif isw==3: cssclass='c3'
			elif isw==4: cssclass='c4'
			cssclass2='w'+cssclass[1]
			print_zoomdots_svg(output,shape,smalldots,sds,cssclass,cssclass2,rotation,width,height,boxzoomcleave=bzc)

	print_footer_svg(output)


def indonesia_options():
	options={'gsg':'IDN.IDN','isinsetleft':True,'lonlabel_lat':40,'latlabel_lon':175,'title':'Indonesia locator'}
	return options

def malaysia_options():
	options={'gsg':'MYS.MYS','isinsetleft':True,'lonlabel_lat':-17,'latlabel_lon':170,'title':'Malaysia locator'}
	return options

def chile_options():
	options={'gsg':'CHL.CHL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,'title':'Chile locator'}
	options['moredots_10m']=[(4,False,[2,3,4,5,6,7])]
	return options

def bolivia_options():
	options={'gsg':'BOL.BOL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Bolivia locator'}
	options['borderlakes']=['Lago Titicaca']
	return options

def peru_options():
	options={'gsg':'PER.PER','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Peru locator'}
	options['borderlakes']=['Lago Titicaca']
	return options

def argentina_options():
	options={'gsg':'ARG.ARG','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Argentina locator'}
	return options

def dhekelia_options():
	options={'gsg':'GB1.ESB','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Dhekelia locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def cyprus_options():
	options={'gsg':'CYP.CYP','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Cyprus locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_10m']=[ (30,3,[2]) ]
	return options

def cyprus_disputed_options():
	options=cyprus_options()
	options['disputed']=['N. Cyprus']
	return options

def cyprusfull_options():
	options={'gsgs':['_cyprusfull'],'isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Cyprus locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_50m']=[ (30,3,[0]) ]
	options['euromapdots_50m']= [('_cyprusfull',24,False,[0]) ]
#	options['ispartlabels']=True
	return options

def india_options():
	options={'gsg':'IND.IND','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':55,'title':'India locator'}
	options['moredots_10m']=[ (4,False,[2,3,4,5,6,7,8,9,17]), (45,False,[21]) ]
#	options['ispartlabels']=True
	return options

def india_disputed_options():
	options=india_options()
	d=[]
	db=[]
	d.append('Arunachal Pradesh') # india and china
	db.append('Tirpani Valleys') # india and china, border
	db.append('Bara Hotii Valleys') # india and china, border
	db.append('Demchok') # kashmir and china, border, redundant
	db.append('Samdu Valleys') # india and china, border
	d.append('Jammu and Kashmir') # india and pakistan and china, kashmir
	d.append('Shaksam Valley') # india pakistan and china
	d.append('Aksai Chin') # india and china
	d.append('Northern Areas') # pakistan and india and china, north of kashmir
	d.append('Siachen Glacier') # pakistan and india
	options['disputed']=d
	options['disputed_border']=db
	return options

def china_options():
	options={'gsg':'CH1.CHN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':165,'title':'China locator'}
	options['moredots_10m']=[ (4,False,[32,33,42,43,44,45,69]) ]
#	options['ispartlabels']=True
	return options

def china_disputed_options():
	options=china_options()
	db=[]
	d=[]
	d.append('Arunachal Pradesh') # india and china
	db.append('Tirpani Valleys') # india and china, border
	db.append('Bara Hotii Valleys') # india and china, border
	db.append('Demchok') # kashmir and china, border, redundant
	db.append('Samdu Valleys') # india and china, border
	d.append('Jammu and Kashmir') # india and pakistan and china, kashmir
	d.append('Shaksam Valley') # india pakistan and china
	d.append('Aksai Chin') # india and china
	d.append('Northern Areas') # pakistan and india and china, north of kashmir
	options['disputed']=d
	options['disputed_border']=db
	return options

def israel_options():
	options={'gsg':'IS1.ISR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Israel locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_10m']=[ (30,True,[0]) ]
	options['borderlakes']=['Dead Sea','_deadseasouth']
	return options

def israel_disputed_options():
	options=israel_options()
	options['disputed']=['Golan Heights']
	return options

def palestine_options():
	options={'gsg':'IS1.PSX','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Palestine locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_10m']=[ (30,True,[1]) ]
	options['borderlakes']=['Dead Sea']
	return options

def lebanon_options():
	options={'gsg':'LBN.LBN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Lebanon locator'}
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_10m']=[ (30,True,[0]) ]
	return options

def lebanon_disputed_options():
	options=lebanon_options()
	options['disputed']=['Golan Heights']
	return options

def ethiopia_options():
	options={'gsg':'ETH.ETH','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':-25,'title':'Ethiopia locator'}
	options['borderlakes']=['Lake Turkana']
	return options

def southsudan_options():
	options={'gsg':'SDS.SDS','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'South Sudan locator'}
	return options

def southsudan_disputed_options():
	options=southsudan_options()
	options['disputed']=['Abyei', 'Ilemi Triangle']
	return options

def somalia_options():
	options={'gsg':'SOM.SOM','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Somalia locator'}
	return options

def somalia_disputed_options():
	options=somalia_options()
	options['disputed']=['Somaliland']
	return options

def kenya_options():
	options={'gsg':'KEN.KEN','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Kenya locator'}
	options['borderlakes']=['Lake Victoria','Lake Turkana']
	return options

def kenya_disputed_options():
	options=kenya_options()
	options['disputed']=['Ilemi Triangle']
	return options

def pakistan_options():
	options={'gsg':'PAK.PAK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Pakistan locator'}
	return options

def pakistan_disputed_options():
	options=pakistan_options()
	d=[]
	d.append('Jammu and Kashmir') # india and pakistan and china, kashmir
	d.append('Shaksam Valley') # india pakistan and china
	d.append('Northern Areas') # pakistan and india and china, north of kashmir
	d.append('Siachen Glacier') # pakistan and india
	options['disputed']=d
	return options

def malawi_options():
	options={'gsg':'MWI.MWI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Malawi locator'}
	options['iszoom']=False
	options['borderlakes']=['Lake Malawi']
	return options

def unitedrepublicoftanzania_options():
	options={'gsg':'TZA.TZA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'United Republic of Tanzania locator'}
	options['borderlakes']=['Lake Victoria','Lake Malawi']
	return options

def syria_options():
	options={'gsg':'SYR.SYR','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Syria locator'}
	return options

def somaliland_options():
	options={'gsg':'SOL.SOL','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Somaliland locator'}
	return options

def france_options():
	options={'gsg':'FR1.FRA','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,'title':'France locator'}
	options['iszoom']=True
	options['issubland']=False
	europarts_10m=[1,11,12,13,14,15,16,17,18,21]
	options['tripelboxes']=[[0],[3,4,5,6,7,19,20],[8,9,10],europarts_10m]
	options['centerindices_10m']=europarts_10m

#	options['isfullpartlabels']=True
	return options

def france_disputed_options():
	options={'gsg':'FR1.FRA','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,'title':'France locator'}
	options['disputed']=['Lawa Headwaters']
	europarts_10m=[1,11,12,13,14,15,16,17,18,21]
	options['tripelboxes']=[[0],[3,4,5,6,7,19,20],[8,9,10],europarts_10m]
	options['centerindices_10m']=[0]
	options['iszoom']=True
	options['iszoom34']=True
	options['zoomscale']=4
	return options

def suriname_options():
	options={'gsg':'SUR.SUR','isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Suriname locator'}
	return options

def suriname_disputed_options():
	options=suriname_options()
	options['disputed']=['Lawa Headwaters','Courantyne Headwaters']
	return options

def guyana_options():
	options={'gsg':'GUY.GUY','isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Guyana locator'}
	return options

def guyana_disputed_options():
	options=guyana_options()
	options['disputed']=['Courantyne Headwaters']
	return options

def southkorea_options():
	options={'gsg':'KOR.KOR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'South Korea locator'}
	return options

def northkorea_options():
	options={'gsg':'PRK.PRK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'North Korea locator'}
	return options

def morocco_options():
	options={'gsg':'MAR.MAR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Morocco locator'}
	return options

def morocco_disputed_options():
	options=morocco_options()
	options['disputed']=['W. Sahara']
	return options

def westernsahara_options():
	options={'gsg':'SAH.SAH','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Western Sahara locator'}
	return options

def westernsahara_disputed_options():
	options=westernsahara_options()
	options['disputed']=['W. Sahara']
	return options

def costarica_options():
	options={'gsg':'CRI.CRI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Costa Rica locator'}
	options['moredots_10m']=[ (4,False,[2]) ]
	return options

def nicaragua_options():
	options={'gsg':'NIC.NIC','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Nicaragua locator'}
	return options

def republicofthecongo_options():
	options={'gsg':'COG.COG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Republic of the Congo locator'}
	return options

def democraticrepublicofthecongo_options():
	options={'gsg':'COD.COD','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Democratic Republic of the Congo locator'}
	options['borderlakes']=['Lac Moeru','Lake Kivu','Lake Edward','Lake Albert']
	return options

def bhutan_options():
	options={'gsg':'BTN.BTN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Bhutan locator'}
	options['iszoom']=True
	return options

def ukraine_options():
	options={'gsg':'UKR.UKR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Ukraine locator'}
	return options

def ukraine_disputed_options():
	options=ukraine_options()
	options['disputed']=['Crimea','Donbass']
	options['iszoom']=True
	options['iszoom34']=True
	return options

def belarus_options():
	options={'gsg':'BLR.BLR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Belarus locator'}
	return options

def namibia_options():
	options={'gsg':'NAM.NAM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Namibia locator'}
	return options

def southafrica_options():
	options={'gsg':'ZAF.ZAF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'South Africa locator'}
	options['moredots_10m']=[ (4,True,[2,3]) ]
	return options

def saintmartin_options():
	options={'gsg':'FR1.MAF','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Saint Martin locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def sintmaarten_options():
	options={'gsg':'NL1.SXM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Sint Maarten locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def oman_options():
	options={'gsg':'OMN.OMN','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Oman locator'}
#	options['ispartlabels']=True
	return options

def uzbekistan_options():
	options={'gsg':'UZB.UZB','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Uzbekistan locator'}
	options['borderlakes']=['Aral Sea','Sarygamysh Köli']
	return options

def kazakhstan_options():
	options={'gsg':'KAZ.KAZ','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Kazakhstan locator'}
	return options

def tajikistan_options():
	options={'gsg':'TJK.TJK','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Tajikistan locator'}
	return options

def lithuania_options():
	options={'gsg':'LTU.LTU','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Lithuania locator'}
	options['iszoom']=True
	return options

def brazil_options():
	options={'gsg':'BRA.BRA','isinsetleft':False,'lonlabel_lat':21,'latlabel_lon':-30,'title':'Brazil locator'}
	options['moredots_10m']=[ (6,False,[27,28,36]) ]
	options['borderlakes']=['Itaipú Reservoir']
	return options

def uruguay_options():
	options={'gsg':'URY.URY','isinsetleft':False,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Uruguay locator'}
	return options

def mongolia_options():
	options={'gsg':'MNG.MNG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Mongolia locator'}
	return options

def russia_options():
	options={'gsg':'RUS.RUS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':179,'title':'Russia locator'}
	options['lon']=109
	options['moredots_10m']=[ (4,False,[137]) ]
	options['tripelboxes_10m']=[ [0,1,2], [70] ]
#	options['ispartlabels']=True
	options['borderlakes']=['Pskoyskoye Ozero', 'Lake Peipus','Aral Sea']
	return options

def russia_disputed_options():
	options=russia_options()
	options['disputed']=['Crimea']
	options['disputed_border']=['Kuril Is.']
	return options

def czechia_options():
	options={'gsg':'CZE.CZE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Czechia locator'}
	return options

def germany_options():
	options={'gsg':'DEU.DEU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Germany locator'}
	return options

def estonia_options():
	options={'gsg':'EST.EST','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Estonia locator'}
	options['iszoom']=True
	options['centerdot']=(25,True)
	options['borderlakes']=['Pskoyskoye Ozero', 'Lake Peipus']
	return options

def latvia_options():
	options={'gsg':'LVA.LVA','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Latvia locator'}
	options['iszoom']=True
	return options

def norway_options():
	options={'gsg':'NOR.NOR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Norway locator'}
	options['centerindices_10m']=[0,96]
	options['moredots_10m']=[ (4,False,[74,97]) ]
	options['zoomdots_10m']=[ (10,False,[74,97]) ]
	options['iszoom']=True
	options['tripelboxes_10m']=[ [0,1,2,86] ]
	return options

def sweden_options():
	options={'gsg':'SWE.SWE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Sweden locator'}
	return options

def finland_options():
	options={'gsg':'FI1.FIN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Finland locator'}
	return options

def vietnam_options():
	options={'gsg':'VNM.VNM','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':165,'title':'Vietnam locator'}
	return options

def cambodia_options():
	options={'gsg':'KHM.KHM','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':160,'title':'Cambodia locator'}
	return options

def luxembourg_options():
	options={'gsg':'LUX.LUX','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Luxembourg locator'}
	options['iszoom']=True
	options['zoomscale']=8
	options['moredots_10m']=[ (30,True,[0]) ]
	options['euromapdots_50m']= [('LUX.LUX',24,False,[0]) ]
	return options

def unitedarabemirates_options():
	options={'gsg':'ARE.ARE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'United Arab Emirates locator'}
	options['iszoom']=True
	return options

def belgium_options():
	options={'gsg':'BEL.BEL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Belgium locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_10m']=[ (25,True,[0]) ]
	return options

def georgia_options():
	options={'gsg':'GEO.GEO','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Georgia locator'}
	options['iszoom']=True
	return options

def georgia_disputed_options():
	options=georgia_options()
	options['disputed']=['Abkhazia','South Ossetia']
	return options

def macedonia_options():
	options={'gsg':'MKD.MKD','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Macedonia locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def albania_options():
	options={'gsg':'ALB.ALB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Albania locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def azerbaijan_options():
	options={'gsg':'AZE.AZE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Azerbaijan locator'}
	options['iszoom']=True
	return options

def azerbaijan_disputed_options():
	options=azerbaijan_options()
	options['disputed']=['Nagorno-Karabakh']
	return options

def kosovo_options():
	options={'gsg':'KOS.KOS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Kosovo locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def turkey_options():
	options={'gsg':'TUR.TUR','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Turkey locator'}
	return options

def spain_options():
	options={'gsg':'ESP.ESP','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Spain locator'}
	options['moredots_10m']=[(10,False,[1]),(24,False,[5])]
	options['euromapdots_50m']=[('ESP.ESP',56,False,[5])]
#	options['ispartlabels']=True
	return options

def laos_options():
	options={'gsg':'LAO.LAO','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':165,'title':'Laos locator'}
	options['iszoom']=False
#	options['halflightgsgs']=['VNM.VNM','KHM.KHM','MMR.MMR','THA.THA']
	return options

def kyrgyzstan_options():
	options={'gsg':'KGZ.KGZ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Kyrgyzstan locator'}
	return options

def armenia_options():
	options={'gsg':'ARM.ARM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Armenia locator'}
	options['iszoom']=True
	options['zoomscale']=4
	return options

def denmark_options():
	options={'gsg':'DN1.DNK','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Denmark locator'}
	options['moredots_10m']=[ (4,False,[6]),(25,True,[0]) ]
	options['iszoom']=True
	options['zoomscale']=4
#	options['ispartlabels']=True
	return options

def libya_options():
	options={'gsg':'LBY.LBY','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Libya locator'}
	return options

def tunisia_options():
	options={'gsg':'TUN.TUN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Tunisia locator'}
	return options

def romania_options():
	options={'gsg':'ROU.ROU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Romania locator'}
	return options

def hungary_options():
	options={'gsg':'HUN.HUN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Hungary locator'}
	options['iszoom']=True
	return options

def slovakia_options():
	options={'gsg':'SVK.SVK','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Slovakia locator'}
	options['iszoom']=True
	return options

def poland_options():
	options={'gsg':'POL.POL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Poland locator'}
	return options

def ireland_options():
	options={'gsg':'IRL.IRL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Ireland locator'}
	options['iszoom']=True
	return options

def unitedkingdom_options():
	options={'gsg':'GB1.GBR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'United Kingdom locator'}
	options['moredots_10m']=[(4,False,[ 52] ) ]
	options['zoomdots_10m']=[(8,False,[ 52] ) ]
	options['iszoom']=True
	return options

def greece_options():
	options={'gsg':'GRC.GRC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Greece locator'}
	options['iszoom']=True
	options['zoomscale']=4
	return options

def zambia_options():
	options={'gsg':'ZMB.ZMB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Zambia locator'}
	options['borderlakes']=['Lake Kariba','Lac Moeru']
	return options

def sierraleone_options():
	options={'gsg':'SLE.SLE','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Sierra Leone locator'}
	return options

def guinea_options():
	options={'gsg':'GIN.GIN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Guinea locator'}
	return options

def liberia_options():
	options={'gsg':'LBR.LBR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Liberia locator'}
	return options

def centralafricanrepublic_options():
	options={'gsg':'CAF.CAF','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Central African Republic locator'}
	return options

def sudan_options():
	options={'gsg':'SDN.SDN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Sudan locator'}
	return options

def sudan_disputed_options():
	options=sudan_options()
	options['disputed']=['Abyei']
	return options

def djibouti_options():
	options={'gsg':'DJI.DJI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Djibouti locator'}
	options['iszoom']=True
	options['zoomscale']=4
	return options

def eritrea_options():
	options={'gsg':'ERI.ERI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Eritrea locator'}
	return options

def austria_options():
	options={'gsg':'AUT.AUT','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Austria locator'}
	options['iszoom']=True
	return options

def iraq_options():
	options={'gsg':'IRQ.IRQ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Iraq locator'}
	return options

def italy_options():
	options={'gsg':'ITA.ITA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Italy locator'}
	options['moredots_10m']=[ (4,False,[3]),(6,False,[18,24]) ] # 18,24
	return options

def switzerland_options():
	options={'gsg':'CHE.CHE','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Switzerland locator'}
	options['iszoom']=True
	options['zoomscale']=4
	return options

def iran_options():
	options={'gsg':'IRN.IRN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Iran locator'}
	return options

def netherlands_options():
	options={'gsg':'NL1.NLD','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Netherlands locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['centerindices_10m']=[0]
	options['moredots_10m']=[ (8,True,[2,3,11]) , (25,True,[0]) ]
	options['tripelboxes_10m']=[ [0], [2,3,11] ]
	return options

def liechtenstein_options():
	options={'gsg':'LIE.LIE','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Liechtenstein locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=16
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def ivorycoast_options():
	options={'gsg':'CIV.CIV','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Ivory Coast locator'}
	return options

def republicofserbia_options():
	options={'gsg':'SRB.SRB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Republic of Serbia locator'}
	return options

def mali_options():
	options={'gsg':'MLI.MLI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Mali locator'}
	return options

def senegal_options():
	options={'gsg':'SEN.SEN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Senegal locator'}
	options['iszoom']=True
	options['zoomscale']=4
	return options

def nigeria_options():
	options={'gsg':'NGA.NGA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Nigeria locator'}
	return options

def benin_options():
	options={'gsg':'BEN.BEN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Benin locator'}
	return options

def angola_options():
	options={'gsg':'AGO.AGO','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Angola locator'}
	return options

def croatia_options():
	options={'gsg':'HRV.HRV','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Croatia locator'}
	options['iszoom']=True
	return options

def slovenia_options():
	options={'gsg':'SVN.SVN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Slovenia locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def qatar_options():
	options={'gsg':'QAT.QAT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Qatar locator'}
	options['iszoom']=True
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def saudiarabia_options():
	options={'gsg':'SAU.SAU','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,'title':'Saudi Arabia locator'}
	return options

def botswana_options():
	options={'gsg':'BWA.BWA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Botswana locator'}
	return options

def zimbabwe_options():
	options={'gsg':'ZWE.ZWE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Zimbabwe locator'}
	options['borderlakes']=['Lake Kariba']
	return options

def bulgaria_options():
	options={'gsg':'BGR.BGR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Bulgaria locator'}
	return options

def thailand_options():
	options={'gsg':'THA.THA','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':160,'title':'Thailand locator'}
	return options

def sanmarino_options():
	options={'gsg':'SMR.SMR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'San Marino locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['moredots_10m']=[ (25,True,[0]) ]
	options['zoomdots_10m']=[ (15,False,[0]) ]
	return options

def haiti_options():
	options={'gsg':'HTI.HTI','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Haiti locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,2,[0]) ]
	return options

def dominicanrepublic_options():
	options={'gsg':'DOM.DOM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Dominican Republic locator'}
	options['iszoom']=True
	options['zoomscale']=4
	return options

def chad_options():
	options={'gsg':'TCD.TCD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Chad locator'}
	return options

def kuwait_options():
	options={'gsg':'KWT.KWT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-22,'title':'Kuwait locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def elsalvador_options():
	options={'gsg':'SLV.SLV','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-150,'title':'El Salvador locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,2,[0]) ]
	return options

def guatemala_options():
	options={'gsg':'GTM.GTM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Guatemala locator'}
	return options

def easttimor_options():
	options={'gsg':'TLS.TLS','isinsetleft':True,'lonlabel_lat':-25,'latlabel_lon':90,'title':'East Timor locator'}
	options['istopinsets']=True
	options['iszoom']=True
	options['iszoom34']=True
	options['zoomscale']=4
	options['centerdot']=(40,3)
	return options

def brunei_options():
	options={'gsg':'BRN.BRN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,'title':'Brunei locator'}
	options['istopinsets']=True
	options['iszoom']=True
	options['iszoom34']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def monaco_options():
	options={'gsg':'MCO.MCO','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Monaco locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=64
	options['moredots_10m']=[ (15,4,[0]) ]
	return options

def algeria_options():
	options={'gsg':'DZA.DZA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Algeria locator'}
	return options

def mozambique_options():
	options={'gsg':'MOZ.MOZ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Mozambique locator'}
	options['borderlakes']=['Lake Malawi']
	return options

def eswatini_options():
	options={'gsg':'SWZ.SWZ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'eSwatini locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def burundi_options():
	options={'gsg':'BDI.BDI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Burundi locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots_10m']=[ (20,False,[0]) ]
	return options

def rwanda_options():
	options={'gsg':'RWA.RWA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Rwanda locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots_10m']=[ (20,False,[0]) ]
	options['borderlakes']=['Lake Kivu']
	return options

def myanmar_options():
	options={'gsg':'MMR.MMR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Myanmar locator'}
	options['smalldots']=[29,30]
	return options

def bangladesh_options():
	options={'gsg':'BGD.BGD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':50,'title':'Bangladesh locator'}
	return options

def andorra_options():
	options={'gsg':'AND.AND','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Andorra locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['moredots_10m']=[ (15,3,[0]) ]
	return options

def afghanistan_options():
	options={'gsg':'AFG.AFG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Afghanistan locator'}
	return options

def montenegro_options():
	options={'gsg':'MNE.MNE','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Montenegro locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def bosniaandherzegovina_options():
	options={'gsg':'BIH.BIH','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Bosnia and Herzegovina locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def uganda_options():
	options={'gsg':'UGA.UGA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Uganda locator'}
	options['borderlakes']=['Lake Edward','Lake Albert','Lake Victoria']
	return options

def usnavalbaseguantanamobay_options():
	options={'gsg':'CUB.USG','isinsetleft':True,'lonlabel_lat':5,'latlabel_lon':-30,'title':'US Naval Base Guantanamo Bay locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=20
	options['moredots_10m']=[ (20,4,[0]) ]
	return options

def cuba_options():
	options={'gsg':'CUB.CUB','isinsetleft':True,'lonlabel_lat':5,'latlabel_lon':-30,'title':'Cuba locator'}
	return options

def honduras_options():
	options={'gsg':'HND.HND','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Honduras locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['smalldots']=[6]
	return options

def ecuador_options():
	options={'gsg':'ECU.ECU','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Ecuador locator'}
	
	options['moredots_10m']=[ (20,False,[7]) ]
	return options

def colombia_options():
	options={'gsg':'COL.COL','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Colombia locator'}
	options['smalldots']=[5,6,7,10]
	return options

def paraguay_options():
	options={'gsg':'PRY.PRY','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Paraguay locator'}
	options['borderlakes']=['Itaipú Reservoir']
	return options

def portugal_options():
	options={'gsg':'PRT.PRT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Portugal locator'}
#	options['smalldots']=[2,3,5,6,7,8,9,10,11,12,13,14,15]
	options['moredots_10m']=[(4,False,(2,3,5,6,7,8,9,10,11,12,13,14,15))]
	options['euromapdots_50m']= [('PRT.PRT',24,False,[0]), ('PRT.PRT',82,False,[4]) ]
#	options['ispartlabels']=True
	return options

def moldova_options():
	options={'gsg':'MDA.MDA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Moldova locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	return options

def moldova_disputed_options():
	options=moldova_options()
	options['disputed']=['Transnistria']
	return options

def turkmenistan_options():
	options={'gsg':'TKM.TKM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Turkmenistan locator'}
	options['borderlakes']=['Sarygamysh Köli']
	return options

def jordan_options():
	options={'gsg':'JOR.JOR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Jordan locator'}
	options['iszoom']=True
	options['iszoom34']=True
	options['borderlakes']=['Dead Sea','_deadseasouth']
	return options

def nepal_options():
	options={'gsg':'NPL.NPL','isinsetleft':True,'lonlabel_lat':-5,'latlabel_lon':50,'title':'Nepal locator'}
	return options

def lesotho_options():
	options={'gsg':'LSO.LSO','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,'title':'Lesotho locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	return options

def cameroon_options():
	options={'gsg':'CMR.CMR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Cameroon locator'}
	return options

def gabon_options():
	options={'gsg':'GAB.GAB','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Gabon locator'}
	return options

def niger_options():
	options={'gsg':'NER.NER','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Niger locator'}
	return options

def burkinafaso_options():
	options={'gsg':'BFA.BFA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Burkina Faso locator'}
	return options

def togo_options():
	options={'gsg':'TGO.TGO','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Togo locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	return options

def ghana_options():
	options={'gsg':'GHA.GHA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Ghana locator'}
	return options

def guineabissau_options():
	options={'gsg':'GNB.GNB','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Guinea-Bissau locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots_10m']=[ (20,False,[0]) ]
	return options

def gibraltar_options():
	options={'gsg':'GB1.GIB','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Gibraltar locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=64
	options['iszoom34']=False
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def unitedstatesofamerica_options():
	options={'gsg':'US1.USA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-45,'title':'United States of America locator'}
	options['lon']=-110
	options['smalldots']=[272,273,274,275,276]
	options['tripelboxes_10m']=[ [0], [85,199], [232] ]
#	options['ispartlabels']=True
	options['borderlakes']=['Lake Superior','Lake Ontario','Lake Erie','Lake Huron','Lake of the Woods','Upper Red Lake',
			'Rainy Lake','Lake Saint Clair']
	return options

def canada_options():
	options={'gsg':'CAN.CAN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Canada locator'}
#	options['ispartlabels']=True
	options['borderlakes']=['Lake Superior','Lake Ontario','Lake Erie','Lake Huron','Lake of the Woods','Upper Red Lake',
			'Rainy Lake','Lake Saint Clair']
	return options

def mexico_options():
	options={'gsg':'MEX.MEX','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-150,'title':'Mexico locator'}
	options['smalldots']=[1,2,3,32,34,36]
	return options

def belize_options():
	options={'gsg':'BLZ.BLZ','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Belize locator'}
	options['moredots_10m']=[ (30,2,[0]) ]
	options['iszoom']=True
	options['iszoom34']=True
	return options

def panama_options():
	options={'gsg':'PAN.PAN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Panama locator'}
	return options

def venezuela_options():
	options={'gsg':'VEN.VEN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Venezuela locator'}
	options['smalldots']=[ 20 ]
	return options

def papuanewguinea_options():
	options={'gsg':'PNG.PNG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Papua New Guinea locator'}
	return options

def egypt_options():
	options={'gsg':'EGY.EGY','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Egypt locator'}
	return options

def yemen_options():
	options={'gsg':'YEM.YEM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Yemen locator'}
	return options

def mauritania_options():
	options={'gsg':'MRT.MRT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Mauritania locator'}
	return options

def equatorialguinea_options():
	options={'gsg':'GNQ.GNQ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Equatorial Guinea locator'}
	options['iszoom']=True
	options['iszoom34']=True
	options['moredots_10m']=[ (20,2,[0]),(4,False,[1]) ]
	options['zoomdots_10m']=[ (8,False,[1]) ]
	return options

def gambia_options():
	options={'gsg':'GMB.GMB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Gambia locator'}
	options['moredots_10m']=[ (25,2,[0]) ]
	options['iszoom']=True
	options['zoomscale']=5
	return options

def hongkongsar_options():
	options={'gsg':'CH1.HKG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':175,'title':'Hong Kong S.A.R. locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def vatican_options():
	options={'gsg':'VAT.VAT','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Vatican locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=False
	options['moredots_10m']=[ (10,True,[0]) ]
	options['zoomdots_10m']=[ (15,False,[0]) ]
	return options

def northerncyprus_options():
	options={'gsg':'CYN.CYN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Northern Cyprus locator'}
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=False
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def cyprusnomansarea_options():
	options={'gsg':'CNM.CNM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Cyprus No Mans Area locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=20
	options['iszoom34']=False
	options['moredots_10m']=[ (20,3,[0]) ]
	options['issubland']=False
	return options

def siachenglacier_options():
	options={'gsg':'KAS.KAS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Siachen Glacier locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=False
	options['moredots_10m']=[ (20,2,[0]) ]
	return options

def baykonurcosmodrome_options():
	options={'gsg':'KAZ.KAB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Baykonur Cosmodrome locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots_10m']=[ (20,2,[0]) ]
	return options

def akrotirisovereignbasearea_options():
	options={'gsg':'GB1.WSB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Akrotiri Sovereign Base Area locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=16
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def antarctica_options():
	options={'gsg':'ATA.ATA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Antarctica locator'}
	options['istopinsets']=True
	return options

def australia_options():
	options={'gsg':'AU1.AUS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Australia locator'}
	options['smalldots']=[ 12, 33 ]
	return options

def greenland_options():
	options={'gsg':'DN1.GRL','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Greenland locator'}
	return options

def fiji_options():
	options={'gsg':'FJI.FJI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':150,'title':'Fiji locator'}
	options['iszoom']=True
	options['iszoom34']=True
	options['zoomscale']=2.5
#	options['ispartlabels']=True
	options['centerindices_10m']=[20]
	options['tripelboxes_10m']=[ [0],[24] ]
	options['smalldots']=[ 34,35,36,37 ]
	options['zoomdots_10m']=[ (10,False,[34,35]) ]
	options['centerdot']=(55,2)
	return options

def newzealand_options():
	options={'gsg':'NZ1.NZL','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':-150,'title':'New Zealand locator'}
	options['centerindices_10m']=[17]
	options['tripelboxes_10m']=[ [7],[17] ]
	options['smalldots']=[ 1,2,3,4,5,6,7,8]
	return options

def newcaledonia_options():
	options={'gsg':'FR1.NCL','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-150,'title':'New Caledonia locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots_10m']=[ (4,False,[10]) ]
	options['centerdot']=(40,2)
#	options['ispartlabels']=True
	return options

def madagascar_options():
	options={'gsg':'MDG.MDG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Madagascar locator'}
	return options

def philippines_options():
	options={'gsg':'PHL.PHL','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':180,'title':'Philippines locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	return options

def srilanka_options():
	options={'gsg':'LKA.LKA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,'title':'Sri Lanka locator'}
	return options

def curacao_options():
	options={'gsg':'NL1.CUW','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Curaçao locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def aruba_options():
	options={'gsg':'NL1.ABW','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Aruba locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def thebahamas_options():
	options={'gsg':'BHS.BHS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'The Bahamas locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=False
#	options['moredots_10m']=[ (50,False,[8]) ]
	options['centerdot']=(50,3)
	return options

def turksandcaicosislands_options():
	options={'gsg':'GB1.TCA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Turks and Caicos Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=False
#	options['moredots_10m']=[ (20,True,[8]) ]
	options['centerdot']=(20,3)
	return options

def taiwan_options():
	options={'gsg':'TWN.TWN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Taiwan locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['moredots_10m']=[ (4,False,[2]), (20,3,[0]) ]
	return options

def japan_options():
	options={'gsg':'JPN.JPN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Japan locator'}
	options['smalldots_10m']=[ 60,80, 14, 62, 12, 59, 61, 54, 84, 66, 67, 16]
	return options

def japan_disputed_options():
	options=japan_options()
	options['disputed_border']=['Kuril Is.']
	return options

def saintpierreandmiquelon_options():
	options={'gsg':'FR1.SPM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Saint Pierre and Miquelon locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=16
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(25,4)
	return options

def iceland_options():
	options={'gsg':'ISL.ISL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-60,'title':'Iceland locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	return options

def pitcairnislands_options():
	options={'gsg':'GB1.PCN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Pitcairn Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
#	options['moredots_10m']=[ (10,True,[0,1,2,3]) ]
	options['centerdot']=(30,3)
#	options['ispartlabels']=True
	options['iszoom']=True
	options['zoomscale']=5
	options['zoomdots_10m']=[ (15,False,[0,1,2,3]) ]
	options['iszoom34']=True
	return options

def frenchpolynesia_options():
	options={'gsg':'FR1.PYF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'French Polynesia locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
#	options['moredots_10m']=[ (100,True,[87]) ]
	options['centerdot']=(110,2)
	options['iszoom']=True
	options['zoomscale']=2
	if False:
		zds=[]
		for i in range(88): zds.append(i)
		options['zoomdots_10m']=[ (5,False,zds) ]
	return options

def frenchsouthernandantarcticlands_options():
	options={'gsg':'FR1.ATF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'French Southern and Antarctic Lands locator'}
	options['moredots_10m']=[ (12,3,[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]) ]
	return options

def seychelles_options():
	options={'gsg':'SYC.SYC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Seychelles locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	dots=[]
	for i in range(26): dots.append(i)
	options['moredots_10m']=[ (12,2,dots) ]
	options['zoomdots_10m']=[ (10,False,dots) ]
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=False
	
	return options

def kiribati_options():
	options={'gsg':'KIR.KIR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,'title':'Kiribati locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['centerindices_10m']=[26]
	options['tripelboxes_10m']=[ [0],[1,29,34] ]
	dots=[]
	for i in range(35): dots.append(i)
	options['moredots_10m']=[ (8,False,dots) ]
	return options

def marshallislands_options():
	options={'gsg':'MHL.MHL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Marshall Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	dots=[]
	for i in range(22): dots.append(i)
	options['moredots_10m']=[ (8,False,dots) ]
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['zoomdots_10m']=[ (5,False,dots) ]
	return options

def trinidadandtobago_options():
	options={'gsg':'TTO.TTO','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Trinidad and Tobago locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def grenada_options():
	options={'gsg':'GRD.GRD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Grenada locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['moredots_10m']=[ (30,3,[0]) ]
	return options

def saintvincentandthegrenadines_options():
	options={'gsg':'VCT.VCT','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Vincent and the Grenadines locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def barbados_options():
	options={'gsg':'BRB.BRB','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Barbados locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def saintlucia_options():
	options={'gsg':'LCA.LCA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Lucia locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
#	options['ispartlabels']=True
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def dominica_options():
	options={'gsg':'DMA.DMA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Dominica locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def unitedstatesminoroutlyingislands_options():
	options={'gsg':'US1.UMI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-130,'title':'United States Minor Outlying Islands locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['tripelboxes_10m']=[ [5],[10],[0,1,2,3,4,  6,7,8,9,  11,12] ]
	options['lon']=-120
	
	dots=[]
	for i in range(13): dots.append(i)
	options['moredots_10m']=[ (20,True,dots) ]
	return options

def montserrat_options():
	options={'gsg':'GB1.MSR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Montserrat locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['zoomdots_10m']=[ (15,False,[0]) ]
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def antiguaandbarbuda_options():
	options={'gsg':'ATG.ATG','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Antigua and Barbuda locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['zoomdots_10m']=[ (10,False,[0,1]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def saintkittsandnevis_options():
	options={'gsg':'KNA.KNA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Kitts and Nevis locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['zoomdots_10m']=[ (25,False,[0]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def unitedstatesvirginislands_options():
	options={'gsg':'US1.VIR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'United States Virgin Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=16
	options['iszoom34']=False
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def saintbarthelemy_options():
	options={'gsg':'FR1.BLM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Saint Barthelemy locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def puertorico_options():
	options={'gsg':'US1.PRI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Puerto Rico locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['zoomdots_10m']=[ (10,False,[0,1,2]) ]
#	options['moredots_10m']=[ (30,True,[3]) ]
	options['centerdot']=(30,3)
	return options

def anguilla_options():
	options={'gsg':'GB1.AIA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Anguilla locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['zoomdots_10m']=[ (4,False,[0,1]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def britishvirginislands_options():
	options={'gsg':'GB1.VGB','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'British Virgin Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=16
	options['iszoom34']=True
#	options['zoomdots_10m']=[ (4,False,[0,1,2,3,4,5]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def jamaica_options():
	options={'gsg':'JAM.JAM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Jamaica locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	return options

def caymanislands_options():
	options={'gsg':'GB1.CYM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Cayman Islands locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def bermuda_options():
	options={'gsg':'GB1.BMU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Bermuda locator'}
	options['presence']=['10m','50m'] 
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['zoomm']='10m'
	options['moredots_10m']=[ (15,4,[0]) ]
	return options

def heardislandandmcdonaldislands_options():
	options={'gsg':'AU1.HMD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,'title':'Heard Island and McDonald Islands locator'}
	options['presence']=['10m','50m'] 
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,True)
	return options

def sainthelena_options():
	options={'gsg':'GB1.SHN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Saint Helena locator'}
	options['presence']=['10m','50m'] 
	options['moredots_10m']=[ (10,3,[0,1,2,3]) ]
	return options

def mauritius_options():
	options={'gsg':'MUS.MUS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Mauritius locator'}
	options['presence']=['10m','50m'] 
	options['moredots_10m']=[ (10,3,[0,1,2]) ]
	return options

def comoros_options():
	options={'gsg':'COM.COM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Comoros locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	return options

def saotomeandprincipe_options():
	options={'gsg':'STP.STP','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'São Tomé and Principe locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def caboverde_options():
	options={'gsg':'CPV.CPV','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,'title':'Cabo Verde locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
#	options['moredots_10m']=[ (30,True,[5]) ]
	options['centerdot']=(30,3)
	return options

def malta_options():
	options={'gsg':'MLT.MLT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Malta locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots_10m']=[ (30,4,[0]) ]
	options['euromapdots_50m']= [('MLT.MLT',24,False,[0]) ]
#	options['ispartlabels']=True
	return options

def jersey_options():
	options={'gsg':'GB1.JEY','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Jersey locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
	options['moredots_10m']=[ (30,3,[0]) ]
	return options

def guernsey_options():
	options={'gsg':'GB1.GGY','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Guernsey locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	return options

def isleofman_options():
	options={'gsg':'GB1.IMN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Isle of Man locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=10
	options['iszoom34']=True
	options['moredots_10m']=[ (20,4,[0]) ]
	return options

def aland_options():
	options={'gsg':'FI1.ALD','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Aland locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=10
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,True)
	return options

def faroeislands_options():
	options={'gsg':'DN1.FRO','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Faroe Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,True)
	return options

def indianoceanterritories_options():
	options={'gsg':'AU1.IOA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Indian Ocean Territories locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['moredots_10m']=[ (10,True,[0,2]) ]
	return options

def britishindianoceanterritory_options():
	options={'gsg':'GB1.IOT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'British Indian Ocean Territory locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
#	options['moredots_10m']=[ (40,False,[5]) ]
	options['centerdot']=(40,3)
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	return options

def singapore_options():
	options={'gsg':'SGP.SGP','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Singapore locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['moredots_10m']=[ (20,True,[0]) ]
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	return options

def norfolkisland_options():
	options={'gsg':'AU1.NFK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Norfolk Island locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=64
	options['iszoom34']=True
	options['moredots_10m']=[ (20,True,[0]) ]
	return options

def cookislands_options():
	options={'gsg':'NZ1.COK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Cook Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['moredots_10m']=[ (10,2,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	options['zoomdots_10m']=[ (5,False,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	return options

def tonga_options():
	options={'gsg':'TON.TON','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Tonga locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['centerdot']=(40,3)
#	options['moredots_10m']=[ (40,False,[0]) ]
	options['zoomdots_10m']=[ (5,False,[0,1,2,3,4,5,6,7,8,9]) ]
	return options

def wallisandfutuna_options():
	options={'gsg':'FR1.WLF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Wallis and Futuna locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['moredots_10m']=[ (10,3,[0,1]) ]
	return options

def samoa_options():
	options={'gsg':'WSM.WSM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Samoa locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['centerdot']=(20,True)
	return options

def solomonislands_options():
	options={'gsg':'SLB.SLB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Solomon Islands locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(70,3)
	return options

def tuvalu_options():
	options={'gsg':'TUV.TUV','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Tuvalu locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=5
	options['iszoom34']=True
	options['centerdot']=(30,3)
	return options

def maldives_options():
	options={'gsg':'MDV.MDV','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Maldives locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(45,3)
	return options

def nauru_options():
	options={'gsg':'NRU.NRU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Nauru locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots_10m']=[ (15,False,[0]) ]
	return options

def federatedstatesofmicronesia_options():
	options={'gsg':'FSM.FSM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Federated States of Micronesia locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	dots=[]
	for i in range(20): dots.append(i)
	options['moredots_10m']=[ (7,2,dots) ]
	return options

def southgeorgiaandtheislands_options():
	options={'gsg':'GB1.SGS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':0,'title':'South Georgia and the Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(50,4)
	return options

def falklandislands_options():
	options={'gsg':'GB1.FLK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,'title':'Falkland Islands locator'}
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['centerdot']=(25,True)
	return options

def vanuatu_options():
	options={'gsg':'VUT.VUT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Vanuatu locator'}
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(40,3)
	return options

def niue_options():
	options={'gsg':'NZ1.NIU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Niue locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (15,False,[0]) ]
	return options

def americansamoa_options():
	options={'gsg':'US1.ASM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'American Samoa locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(30,3)
	options['zoomdots_10m']=[ (10,False,[0,1,2,3,4]) ]
	return options

def palau_options():
	options={'gsg':'PLW.PLW','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Palau locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(40,3)
	options['zoomdots_10m']=[ (8,False,[0,1,2,3,4,5,6,7,8]) ]
	return options

def guam_options():
	options={'gsg':'US1.GUM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Guam locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(30,3)
	options['zoomdots_10m']=[ (7,False,[0]) ]
	return options

def northernmarianaislands_options():
	options={'gsg':'US1.MNP','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,'title':'Northern Mariana Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(40,3)
	options['zoomdots_10m']=[ (4,False,[0,1,2,3,4,5,6,7,8,9,10,11]) ]
	return options

def bahrain_options():
	options={'gsg':'BHR.BHR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,'title':'Bahrain locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=8
	options['iszoom34']=True
	options['centerdot']=(20,True)
	return options

def coralseaislands_options():
	options={'gsg':'AU1.CSI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Coral Sea Islands locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	return options

def spratlyislands_options():
	options={'gsg':'PGA.PGA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':175,'title':'Spratly Islands locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=4
	options['iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots_10m']=[ (4,False,[0,1,2,3,4,5,6,7,8,9,10,11]) ]
	return options

def clippertonisland_options():
	options={'gsg':'FR1.CLP','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,'title':'Clipperton Island locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	return options

def macaosar_options():
	options={'gsg':'CH1.MAC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,'title':'Macao S.A.R locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=32
	options['iszoom34']=True
	options['centerdot']=(20,True)
	return options

def ashmoreandcartierislands_options():
	options={'gsg':'AU1.ATC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,'title':'Ashmore and Cartier Islands locator'}
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	return options

def bajonuevobank_options():
	options={'gsg':'BJN.BJN','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Bajo Nuevo Bank (Petrel Is.) locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	return options

def serranillabank_options():
	options={'gsg':'SER.SER','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-30,'title':'Serranilla Bank locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	return options

def scarboroughreef_options():
	options={'gsg':'SCR.SCR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':180,'title':'Scarborough Reef locator'}
	options['presence']=['10m']
	options['isfullhighlight']=True
#	options['ispartlabels']=True
	options['issubland']=False
	options['iszoom']=True
	options['zoomscale']=2
	options['iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	return options

def addregionoptions(dest):
#	dest.append( ('x',scarboroughreef_options) )

	dest.append( ('indonesia',indonesia_options) )
	dest.append( ('malaysia',malaysia_options) )
	dest.append( ('chile',chile_options) )
	dest.append( ('bolivia',bolivia_options) )
	dest.append( ('peru',peru_options) )
	dest.append( ('argentina',argentina_options) )
	dest.append( ('dhekelia',dhekelia_options) )
	dest.append( ('cyprus',cyprus_options) )
	dest.append( ('cyprus_disputed',cyprus_disputed_options) )
	dest.append( ('cyprusfull',cyprusfull_options) )
	dest.append( ('india',india_options) )
	dest.append( ('india_disputed',india_disputed_options) )
	dest.append( ('china',china_options) )
	dest.append( ('china_disputed',china_disputed_options) )

	dest.append( ('israel',israel_options) )
	dest.append( ('israel_disputed',israel_disputed_options) )
	dest.append( ('palestine',palestine_options) )
	dest.append( ('lebanon', lebanon_options) )
	dest.append( ('lebanon_disputed', lebanon_disputed_options) )
	dest.append( ('ethiopia', ethiopia_options) )
	dest.append( ('southsudan', southsudan_options) )
	dest.append( ('southsudan_disputed', southsudan_disputed_options) )
	dest.append( ('somalia', somalia_options) )
	dest.append( ('somalia_disputed', somalia_disputed_options) )
	dest.append( ('kenya', kenya_options) )
	dest.append( ('kenya_disputed', kenya_disputed_options) )
	dest.append( ('pakistan', pakistan_options) )
	dest.append( ('pakistan_disputed', pakistan_disputed_options) )
	dest.append( ('malawi', malawi_options) )
	dest.append( ('unitedrepublicoftanzania', unitedrepublicoftanzania_options) )
	dest.append( ('syria', syria_options) )
	dest.append( ('somaliland', somaliland_options) )
	dest.append( ('france', france_options) )
	dest.append( ('france_disputed', france_disputed_options) )
	dest.append( ('suriname', suriname_options) )
	dest.append( ('suriname_disputed', suriname_disputed_options) )
	dest.append( ('guyana', guyana_options) )
	dest.append( ('guyana_disputed', guyana_disputed_options) )
	dest.append( ('southkorea', southkorea_options) )
	dest.append( ('northkorea', northkorea_options) )
	dest.append( ('morocco', morocco_options) )
	dest.append( ('morocco_disputed', morocco_disputed_options) )
	dest.append( ('westernsahara', westernsahara_options) )
	dest.append( ('westernsahara_disputed', westernsahara_disputed_options) )
	dest.append( ('costarica', costarica_options) )
	dest.append( ('nicaragua', nicaragua_options) )
	dest.append( ('republicofthecongo', republicofthecongo_options) )
	dest.append( ('democraticrepublicofthecongo', democraticrepublicofthecongo_options) )
	dest.append( ('bhutan', bhutan_options) )
	dest.append( ('ukraine', ukraine_options) )
	dest.append( ('ukraine_disputed', ukraine_disputed_options) )
	dest.append( ('belarus', belarus_options) )
	dest.append( ('namibia', namibia_options) )
	dest.append( ('southafrica', southafrica_options) )
	dest.append( ('saintmartin', saintmartin_options) )
	dest.append( ('sintmaarten', sintmaarten_options) )
	dest.append( ('oman', oman_options) )
	dest.append( ('uzbekistan', uzbekistan_options) )
	dest.append( ('kazakhstan', kazakhstan_options) )
	dest.append( ('tajikistan', tajikistan_options) )
	dest.append( ('lithuania', lithuania_options) )

	dest.append( ('brazil',brazil_options) )
	dest.append( ('uruguay', uruguay_options) )
	dest.append( ('mongolia', mongolia_options) )
	dest.append( ('russia', russia_options) )
	dest.append( ('russia_disputed', russia_disputed_options) )
	dest.append( ('czechia', czechia_options) )
	dest.append( ('germany', germany_options) )
	dest.append( ('estonia', estonia_options) )
	dest.append( ('latvia', latvia_options) )
	dest.append( ('norway', norway_options) )
	dest.append( ('sweden', sweden_options) )
	dest.append( ('finland', finland_options) )
	dest.append( ('vietnam',vietnam_options) )
	dest.append( ('cambodia', cambodia_options) )
	dest.append( ('luxembourg', luxembourg_options) )
	dest.append( ('unitedarabemirates', unitedarabemirates_options) )
	dest.append( ('belgium', belgium_options) )
	dest.append( ('georgia', georgia_options) )
	dest.append( ('georgia_disputed', georgia_disputed_options) )
	dest.append( ('macedonia', macedonia_options) )
	dest.append( ('albania', albania_options) )
	dest.append( ('azerbaijan', azerbaijan_options) )
	dest.append( ('azerbaijan_disputed', azerbaijan_disputed_options) )
	dest.append( ('kosovo', kosovo_options) )
	dest.append( ('turkey', turkey_options) )
	dest.append( ('spain', spain_options) )
	dest.append( ('laos',laos_options) )
	dest.append( ('kyrgyzstan', kyrgyzstan_options) )
	dest.append( ('armenia', armenia_options) )
	dest.append( ('denmark', denmark_options) )
	dest.append( ('libya', libya_options) )
	dest.append( ('tunisia', tunisia_options) )
	dest.append( ('romania', romania_options) )
	dest.append( ('hungary', hungary_options) )
	dest.append( ('slovakia', slovakia_options) )
	dest.append( ('poland', poland_options) )
	dest.append( ('ireland', ireland_options) )
	dest.append( ('unitedkingdom', unitedkingdom_options) )
	dest.append( ('greece', greece_options) )
	dest.append( ('zambia', zambia_options) )
	dest.append( ('sierraleone', sierraleone_options) )
	dest.append( ('guinea', guinea_options) )
	dest.append( ('liberia', liberia_options) )
	dest.append( ('centralafricanrepublic', centralafricanrepublic_options) )
	dest.append( ('sudan', sudan_options) )
	dest.append( ('sudan_disputed', sudan_disputed_options) )
	dest.append( ('djibouti', djibouti_options) )
	dest.append( ('eritrea', eritrea_options) )
	dest.append( ('austria', austria_options) )
	dest.append( ('iraq', iraq_options) )
	dest.append( ('italy', italy_options) )
	dest.append( ('switzerland', switzerland_options) )
	dest.append( ('iran', iran_options) )
	dest.append( ('netherlands', netherlands_options) )
	dest.append( ('liechtenstein', liechtenstein_options) )
	dest.append( ('ivorycoast', ivorycoast_options) )
	dest.append( ('republicofserbia', republicofserbia_options) )
	dest.append( ('mali', mali_options) )
	dest.append( ('senegal', senegal_options) )
	dest.append( ('nigeria', nigeria_options) )
	dest.append( ('benin', benin_options) )
	dest.append( ('angola', angola_options) )
	dest.append( ('croatia', croatia_options) )
	dest.append( ('slovenia', slovenia_options) )
	dest.append( ('qatar', qatar_options) )
	dest.append( ('saudiarabia', saudiarabia_options) )
	dest.append( ('botswana', botswana_options) )
	dest.append( ('zimbabwe', zimbabwe_options) )
	dest.append( ('bulgaria', bulgaria_options) )
	dest.append( ('thailand', thailand_options) )
	dest.append( ('sanmarino', sanmarino_options) )
	dest.append( ('haiti', haiti_options) )
	dest.append( ('dominicanrepublic', dominicanrepublic_options) )
	dest.append( ('chad', chad_options) )
	dest.append( ('kuwait', kuwait_options) )
	dest.append( ('elsalvador', elsalvador_options) )
	dest.append( ('guatemala', guatemala_options) )
	dest.append( ('easttimor', easttimor_options) )
	dest.append( ('brunei', brunei_options) )
	dest.append( ('monaco', monaco_options) )
	dest.append( ('algeria', algeria_options) )
	dest.append( ('mozambique', mozambique_options) )
	dest.append( ('eswatini', eswatini_options) )
	dest.append( ('burundi', burundi_options) )
	dest.append( ('rwanda', rwanda_options) )
	dest.append( ('myanmar', myanmar_options) )
	dest.append( ('bangladesh', bangladesh_options) )
	dest.append( ('andorra', andorra_options) )
	dest.append( ('afghanistan', afghanistan_options) )
	dest.append( ('montenegro', montenegro_options) )
	dest.append( ('bosniaandherzegovina', bosniaandherzegovina_options) )
	dest.append( ('uganda', uganda_options) )
	dest.append( ('usnavalbaseguantanamobay', usnavalbaseguantanamobay_options) )
	dest.append( ('cuba', cuba_options) )
	dest.append( ('honduras', honduras_options) )
	dest.append( ('ecuador', ecuador_options) )
	dest.append( ('colombia', colombia_options) )
	dest.append( ('paraguay', paraguay_options) )
	dest.append( ('portugal', portugal_options) )
	dest.append( ('moldova', moldova_options) )
	dest.append( ('moldova_disputed', moldova_disputed_options) )
	dest.append( ('turkmenistan', turkmenistan_options) )
	dest.append( ('jordan', jordan_options) )
	dest.append( ('nepal', nepal_options) )
	dest.append( ('lesotho', lesotho_options) )
	dest.append( ('cameroon', cameroon_options) )
	dest.append( ('gabon', gabon_options) )
	dest.append( ('niger', niger_options) )
	dest.append( ('burkinafaso', burkinafaso_options) )
	dest.append( ('togo', togo_options) )
	dest.append( ('ghana', ghana_options) )
	dest.append( ('guineabissau', guineabissau_options) )
	dest.append( ('gibraltar', gibraltar_options) )
	dest.append( ('unitedstatesofamerica', unitedstatesofamerica_options) )
	dest.append( ('canada', canada_options) )
	dest.append( ('mexico', mexico_options) )
	dest.append( ('belize', belize_options) )
	dest.append( ('panama', panama_options) )
	dest.append( ('venezuela', venezuela_options) )
	dest.append( ('papuanewguinea', papuanewguinea_options) )
	dest.append( ('egypt', egypt_options) )
	dest.append( ('yemen', yemen_options) )
	dest.append( ('mauritania', mauritania_options) )
	dest.append( ('equatorialguinea', equatorialguinea_options) )
	dest.append( ('gambia', gambia_options) )
	dest.append( ('hongkongsar', hongkongsar_options) )
	dest.append( ('vatican', vatican_options) )
	dest.append( ('northerncyprus', northerncyprus_options) )
	dest.append( ('cyprusnomansarea', cyprusnomansarea_options) )
	dest.append( ('siachenglacier', siachenglacier_options) )
	dest.append( ('baykonurcosmodrome', baykonurcosmodrome_options) )
	dest.append( ('akrotirisovereignbasearea', akrotirisovereignbasearea_options) )
	dest.append( ('antarctica', antarctica_options) )
	dest.append( ('australia', australia_options) )
	dest.append( ('greenland', greenland_options) )
	dest.append( ('fiji', fiji_options) )
	dest.append( ('newzealand', newzealand_options) )
	dest.append( ('newcaledonia', newcaledonia_options) )
	dest.append( ('madagascar', madagascar_options) )
	dest.append( ('philippines', philippines_options) )
	dest.append( ('srilanka', srilanka_options) )
	dest.append( ('curacao', curacao_options) )
	dest.append( ('aruba', aruba_options) )
	dest.append( ('thebahamas', thebahamas_options) )
	dest.append( ('turksandcaicosislands', turksandcaicosislands_options) )
	dest.append( ('taiwan', taiwan_options) )
	dest.append( ('japan', japan_options) )
	dest.append( ('japan_disputed', japan_disputed_options) )
	dest.append( ('saintpierreandmiquelon', saintpierreandmiquelon_options) )
	dest.append( ('iceland', iceland_options) )
	dest.append( ('pitcairnislands', pitcairnislands_options) )
	dest.append( ('frenchpolynesia', frenchpolynesia_options) )
	dest.append( ('frenchsouthernandantarcticlands', frenchsouthernandantarcticlands_options) )
	dest.append( ('seychelles', seychelles_options) )
	dest.append( ('kiribati', kiribati_options) )
	dest.append( ('marshallislands', marshallislands_options) )
	dest.append( ('trinidadandtobago', trinidadandtobago_options) )
	dest.append( ('grenada', grenada_options) )
	dest.append( ('saintvincentandthegrenadines', saintvincentandthegrenadines_options) )
	dest.append( ('barbados', barbados_options) )
	dest.append( ('saintlucia', saintlucia_options) )
	dest.append( ('dominica', dominica_options) )
	dest.append( ('unitedstatesminoroutlyingislands', unitedstatesminoroutlyingislands_options) )
	dest.append( ('montserrat', montserrat_options) )
	dest.append( ('antiguaandbarbuda', antiguaandbarbuda_options) )
	dest.append( ('saintkittsandnevis', saintkittsandnevis_options) )
	dest.append( ('unitedstatesvirginislands', unitedstatesvirginislands_options) )
	dest.append( ('saintbarthelemy', saintbarthelemy_options) )
	dest.append( ('puertorico', puertorico_options) )
	dest.append( ('anguilla', anguilla_options) )
	dest.append( ('britishvirginislands', britishvirginislands_options) )
	dest.append( ('jamaica', jamaica_options) )
	dest.append( ('caymanislands', caymanislands_options) )
	dest.append( ('bermuda', bermuda_options) )
	dest.append( ('heardislandandmcdonaldislands', heardislandandmcdonaldislands_options) )
	dest.append( ('sainthelena', sainthelena_options) )
	dest.append( ('mauritius', mauritius_options) )
	dest.append( ('comoros', comoros_options) )
	dest.append( ('saotomeandprincipe', saotomeandprincipe_options) )
	dest.append( ('caboverde', caboverde_options) )
	dest.append( ('malta', malta_options) )
	dest.append( ('jersey', jersey_options) )
	dest.append( ('guernsey', guernsey_options) )
	dest.append( ('isleofman', isleofman_options) )
	dest.append( ('aland', aland_options) )
	dest.append( ('faroeislands', faroeislands_options) )
	dest.append( ('indianoceanterritories', indianoceanterritories_options) )
	dest.append( ('britishindianoceanterritory', britishindianoceanterritory_options) )
	dest.append( ('singapore', singapore_options) )
	dest.append( ('norfolkisland', norfolkisland_options) )
	dest.append( ('cookislands', cookislands_options) )
	dest.append( ('tonga', tonga_options) )
	dest.append( ('wallisandfutuna', wallisandfutuna_options) )
	dest.append( ('samoa', samoa_options) )
	dest.append( ('solomonislands', solomonislands_options) )
	dest.append( ('tuvalu', tuvalu_options) )
	dest.append( ('maldives', maldives_options) )
	dest.append( ('nauru', nauru_options) )
	dest.append( ('federatedstatesofmicronesia', federatedstatesofmicronesia_options) )
	dest.append( ('southgeorgiaandtheislands', southgeorgiaandtheislands_options) )
	dest.append( ('falklandislands', falklandislands_options) )
	dest.append( ('vanuatu', vanuatu_options) )
	dest.append( ('niue', niue_options) )
	dest.append( ('americansamoa', americansamoa_options) )
	dest.append( ('palau', palau_options) )
	dest.append( ('guam', guam_options) )
	dest.append( ('northernmarianaislands', northernmarianaislands_options) )
	dest.append( ('bahrain', bahrain_options) )
	dest.append( ('coralseaislands', coralseaislands_options) )
	dest.append( ('spratlyislands', spratlyislands_options) )
	dest.append( ('clippertonisland', clippertonisland_options) )
	dest.append( ('macaosar', macaosar_options) )
	dest.append( ('ashmoreandcartierislands', ashmoreandcartierislands_options) )
	dest.append( ('bajonuevobank', bajonuevobank_options) )
	dest.append( ('serranillabank', serranillabank_options) )
	dest.append( ('scarboroughreef', scarboroughreef_options) )


def runparams(params):
	global isverbose_global
	options={}
	overrides={}
	output=Output()
	regionoptions=[]
	addregionoptions(regionoptions)
	overrides['cmdline']='./pythonshp.py '+' '.join(params)
	locatormap_overrides={}
	areamap_overrides={}

	for param in params:
		if param=='check':
			install.print()
			if isverbose_global: install.printlog()
			isverbose_global=True
		elif param=='verbose':
			isverbose_global=True
		elif param=='publicdomain':
			overrides['copyright']='COPYRIGHT: THIS SVG FILE IS RELEASED INTO THE PUBLIC DOMAIN'
		elif param=='list':
			regionoptions.sort()
			for l in regionoptions: print('%s'%l[0])
		elif param=='wiki1':
			locatormap_overrides['width']=1000
			locatormap_overrides['height']=1000
			locatormap_overrides['labelfont']='14px sans'
			locatormap_overrides['spherem']='50m'
			locatormap_overrides['zoomm']='50m'
			areamap_overrides['width']=1000
			areamap_overrides['height']=1000
			areamap_overrides['spherem']='50m'
		elif param=='notripel':
			locatormap_overrides['istripelinset']=False
		elif param=='bg':
			overrides['bgcolor']='#b4b4b4'
		elif param=='locatormap':
			for n in overrides: options[n]=overrides[n]
			for n in locatormap_overrides: options[n]=locatormap_overrides[n]
			locatormap(output,options)
		elif param=='euromap':
			for n in overrides: options[n]=overrides[n]
			for n in areamap_overrides: options[n]=areamap_overrides[n]
			euromap(output,options)
		elif param=='admin0dbf_test': admin0dbf_test()
		elif param=='lakesdbf_test': lakesdbf_test()
		elif param=='lakesintersection_test': lakesintersection_test()
		elif param=='borderlakes_test': borderlakes_test()
		elif param=='disputeddbf_test': disputeddbf_test()
		elif param=='disputed_test': disputed_test()
		elif param=='admin1dbf_test': admin1dbf_test()
		elif param=='sphere_test': sphere_test()
		elif param=='sphere2_test': sphere2_test()
		elif param=='sphere3_test': sphere3_test()
		elif param=='sphere4_test': sphere4_test()
		elif param=='ocean_test': ocean_test()
		elif param=='land_test': land_test()
		elif param=='lonlat_test': lonlat_test()
		elif param=='lonlat2_test': lonlat2_test()
		elif param=='zoom_test': zoom_test()
		elif param=='tripel_test': tripel_test()
		elif param=='webmercator_test': webmercator_test()
		elif param=='province_test': province_test()
		elif param=='admin0info_test': admin0info_test()
		elif param=='admin0parts_test': admin0parts_test()
		elif param=='worldcompress_test': worldcompress_test()
		elif param=='ccw_test': ccw_test()
		elif param=='version' or param=='--version':
			print('Version 1.0.0')
		elif param=='help' or param=='--help':
			print('Usage: ./pythonshp.py command1 command2 command3 ...')
			print('Commands:')
			print('\tverbose          : print more status messages')
			print('\tcheck            : show file locations and enable verbose messages')
			print('\tpublicdomain     : add PD copyright notice in output')
			print('\twiki1            : set defaults for wikipedia, set 1')
			print('\tbg               : print background color (instead of transparency)')
			print('\tnotripel         : disable Winkel Tripel inset')
			print('\tlist             : list known location commands')
			print('\tlocatormap       : print locator map svg')
			print('\teuromap          : print EU map svg')
			print('Example 1: "./pythonshp.py verbose check"')
			print('2: "./pythonshp.py check publicdomain wiki1 laos locatormap > laos.svg"')
			print('3: "./pythonshp.py verbose wiki1 laos locatormap | inkscape -e laos.png -"')
		else:
			for l in regionoptions:
				if param==l[0]:
					options=l[1]()
					break
			else:
				print('Unknown command "%s"'%param,file=sys.stderr)
				return

if len(sys.argv)<2: runparams(['help'])
else: runparams(sys.argv[1:])

if debug_global!=0: print('debug: %d'%debug_global,file=sys.stderr)
