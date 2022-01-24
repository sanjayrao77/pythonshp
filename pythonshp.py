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
import io
import base64
try:
	import zlib
except ImportError:
	zlib=None
try:
	import zipfile
except ImportError:
	zipfile=None

version_global='1.0.5'
isverbose_global=False
ispartlabeltop_global=True
debug_global=0

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
CUTOUT_CCWTYPE=4
IGNORE_CCWTYPE=5
def ccwtype_tostring(c):
	if c==NONE_CCWTYPE: return 'NONE'
	if c==REVERSE_CCWTYPE: return 'REVERSE'
	if c==HOLE_CCWTYPE: return 'HOLE'
	if c==CW_CCWTYPE: return 'CW'
	if c==CUTOUT_CCWTYPE: return 'CUTOUT'
	if c==IGNORE_CCWTYPE: return 'IGNORE'
	return 'UNK'

M_PI=math.pi
M_PI_2=math.pi/2.0
M_PI_4=math.pi/4.0
M_3PI_2=math.pi+M_PI_2

LAND_SPHERE_CSS='sl'
OVERLAP_SPHERE_CSS='so'
BORDER_SPHERE_CSS='sb'
PATCH_LAND_SPHERE_CSS='sp'
HIGH_LAND_SPHERE_CSS='sh'
PATCH_HIGH_LAND_SPHERE_CSS='sq'
HIGH_BORDER_SPHERE_CSS='si'
AREA_LAND_SPHERE_CSS='al'
AREA_BORDER_SPHERE_CSS='ab'
PATCH_AREA_LAND_SPHERE_CSS='ap'
AREA_LAKELINE_SPHERE_CSS='ai'
DISPUTED_LAND_SPHERE_CSS='dl'
PATCH_DISPUTED_LAND_SPHERE_CSS='dp'
DISPUTED_BORDER_SPHERE_CSS='db'
DISPUTED_LAND_ZOOM_CSS='dz'
DISPUTED_BORDER_ZOOM_CSS='dy'
PATCH_DISPUTED_LAND_ZOOM_CSS='dx'
LAND_ZOOM_CSS='zl'
PATCH_LAND_ZOOM_CSS='zp'
HIGH_LAND_ZOOM_CSS='zh'
PATCH_HIGH_LAND_ZOOM_CSS='zq'
HIGH_LAKELINE_ZOOM_CSS='zi'
BORDER_ZOOM_CSS='zb'
WATER_ZOOM_CSS='zw'
PATCH_WATER_ZOOM_CSS='zr'
LAND_TRIPEL_CSS='tl'
PATCH_LAND_TRIPEL_CSS='tp'
HIGH_LAND_TRIPEL_CSS='th'
PATCH_HIGH_LAND_TRIPEL_CSS='tq'
BACK_TRIPEL_CSS='tb'
OCEAN_TRIPEL_CSS='to'
COAST_TRIPEL_CSS='tc'
GRID_SPHERE_CSS='sg'
GRID_TRIPEL_CSS='tg'
SHADOW_FONT_CSS='fs'
TEXT_FONT_CSS='ft'
ONE_DISPUTED_CIRCLE_CSS='d1'
ONE_CIRCLE_CSS='c1'
TWO_CIRCLE_CSS='c2'
THREE_CIRCLE_CSS='c3'
FOUR_CIRCLE_CSS='c4'
SHADOW_ONE_CIRCLE_CSS='w1'
SHADOW_TWO_CIRCLE_CSS='w2'
SHADOW_THREE_CIRCLE_CSS='w3'
SHADOW_FOUR_CIRCLE_CSS='w4'
WATER_SPHERE_CSS='sw'
PATCH_WATER_SPHERE_CSS='sr'
HYPSOCUT_SPHERE_CSS='hc'

def getshadow_circle_css(class1):
	if class1==ONE_CIRCLE_CSS: return SHADOW_ONE_CIRCLE_CSS
	if class1==TWO_CIRCLE_CSS: return SHADOW_TWO_CIRCLE_CSS
	if class1==THREE_CIRCLE_CSS: return SHADOW_THREE_CIRCLE_CSS
	if class1==FOUR_CIRCLE_CSS: return SHADOW_FOUR_CIRCLE_CSS
	raise ValueError

def uint32_big(buff,offset): return struct.unpack(">I",buff[offset:offset+4])[0]
def uint32_little(buff,offset): return struct.unpack("<I",buff[offset:offset+4])[0]
def uint16_little(buff,offset): return struct.unpack("<H",buff[offset:offset+2])[0]
def getdouble(buff,offset): return struct.unpack('d',buff[offset:offset+8])[0]

def shapename(typenum):
	if typenum==POLYGON_TYPE_SHP: return "polygon"
	if typenum==POLYLINE_TYPE_SHP: return "polyline"
	if typenum==POINT_TYPE_SHP: return "point"
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
		self.lines=[]
		self.csscounts={}
		self.path=None
	def countcss(self,cssclass):
		cs=cssclass.split(' ')
		for c in cs:
			self.csscounts[c]=self.csscounts.get(c,0)+1
	def flush(self):
		self.path_flush()
	def setfile(self,outf):
		self.file=outf
	def rawprint(self,s):
		self.lines.append(s)
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
		self.countcss(cssclass)
		self.path=OutputPath(cssclass)
	def addtopath(self,dstring):
		self.path.addd(dstring)
	def path_flush(self):
		if not self.path: return
		self.path.write(self)
		self.path=None
	def prepend(self,output):
		self.lines[0:0]=output.lines
#		for c in output.csscounts: self.csscounts[c]=self.csscounts.get(c,0)+output.csscounts[c] # untested, unused
	def writeto(self,file):
		for l in self.lines: print(l,end='',file=file)
		

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
	def getcenter(self):
		return ((self.maxx+self.minx)/2,(self.maxy+self.miny)/2)
	def getpseudoradius(self):
		(ax,ay)=self.getcenter()
		return FlatPoint.distance(ax,ay,self.minx,self.miny)
	def isintersects(self,two):
		if self.minx>two.maxx: return False
		if self.maxx<two.minx: return False
		if self.miny>two.maxy: return False
		if self.maxy<two.miny: return False
		return True
	def print(self): print(str(self))
# be careful crossing coordinate system boundaries
	def add(self,x,y):
		if not self.isset: self.set(x,y,x,y)
		else:
			if x<self.minx: self.minx=x
			elif x>self.maxx: self.maxx=x
			if y<self.miny: self.miny=y
			elif y>self.maxy: self.maxy=y
	def addmbr(self,mbr):
		if not self.isset:
			(self.isset, self.minx, self.miny, self.maxx, self.maxy) = (mbr.isset, mbr.minx, mbr.miny, mbr.maxx, mbr.maxy)
		elif mbr.isset:
			if self.minx>mbr.minx: self.minx=mbr.minx
			if self.miny>mbr.miny: self.miny=mbr.miny
			if self.maxx<mbr.maxx: self.maxx=mbr.maxx
			if self.maxy<mbr.maxy: self.maxy=mbr.maxy

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
	def print(self,file=sys.stdout):
		print('( %.12f,%.12f )'%(self.lon,self.lat),file=file)
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

class PngCompress():
	@staticmethod
	def create(width,height,rows,isfast=False,palette=None,transtable=None):
		bio=io.BytesIO()
		bio.write(b'\x89PNG\r\n\x1a\n')
		if palette:
			Bpp=1
			PngCompress.writechunk(bio,b'IHDR',struct.pack('>2I5B',width,height,8,3,0,0,0))
			PngCompress.writechunk(bio,b'PLTE',palette)
			if transtable: PngCompress.writechunk(bio,b'tRNS',transtable)
		else:
			Bpp=int(len(rows[0])/width)
			if Bpp==4: colortype=6 # rgba
			elif Bpp==3: colortype=2 # rgb
			elif Bpp==2: colortype=4 # greyscale+alpha
			elif Bpp==1: colortype=0 # greyscale
			else: raise ValueError
			PngCompress.writechunk(bio,b'IHDR',struct.pack('>2I5B',width,height,8,colortype,0,0,0))
		if isfast: PngCompress.write_simple(bio,rows,3)
		else: PngCompress.write_small(bio,rows,width,Bpp)
		PngCompress.writechunk(bio,b'IEND',b'')
		return bio.getvalue()
	@staticmethod
	def writechunk(bio,key,value):
		bio.write(struct.pack('>I',len(value)))
		bio.write(key)
		bio.write(value)
		bio.write(struct.pack('>I',zlib.crc32(value,zlib.crc32(key))))
	@staticmethod
	def write_simple(bio,rows,complevel): # complevel, 3:fast, 6:medium, 9: smallest
		ba=bytearray()
		for row in rows:
			ba.append(0)
			ba.extend(row)
		PngCompress.writechunk(bio,b'IDAT',zlib.compress(ba,complevel))
	@staticmethod
	def paethpredictor(a,b,c): # PaethPredictor is lifted from PNG spec, presumably this is free as it's required for all readers
		# a:left, b:above, c:upperleft
		p=a+b-c
		pa=abs(p-a)
		pb=abs(p-b)
		pc=abs(p-c)
		# return nearest of a,b,c, breaking ties in order a,b,c
		if pa<=pb and pa<=pc: return a
		if pb<=pc: return b
		return c
	@staticmethod
	def getcompsize(zco,line):
		z=zco.copy()
		return len(z.compress(line))+len(z.flush())
	@staticmethod
	def write_small(bio,rows,width,Bpp):
		zco=zlib.compressobj(level=9,memLevel=9)
		zba=bytearray()
		widthxB=width*Bpp
		ba=bytearray(1+widthxB)
		tba=bytearray(1+widthxB)
		urow=[0]*widthxB
		for row in rows:
			ba[0]=0
			ba[1:]=row
			bal=PngCompress.getcompsize(zco,ba)
			if True:
				tba[0]=1 # Left
				tba[1:1+Bpp]=row[0:Bpp]
				for i in range(Bpp,widthxB): tba[i+1]=(row[i]-row[i-Bpp])%256
				tbal=PngCompress.getcompsize(zco,tba)
				if tbal<bal: ba,tba,bal=(tba,ba,tbal)
			if True:
				tba[0]=2 # Up
				for i in range(widthxB): tba[i+1]=(row[i]-urow[i])%256
				tbal=PngCompress.getcompsize(zco,tba)
				if tbal<bal: ba,tba,bal=(tba,ba,tbal)
			if True:
				tba[0]=3 # Left + Up
				for i in range(Bpp): tba[i+1]=(row[i]-(urow[i]>>1))%256
				for i in range(Bpp,widthxB): tba[i+1]=(row[i]-((row[i-Bpp]+urow[i])>>1))%256
				tbal=PngCompress.getcompsize(zco,tba)
				if tbal<bal: ba,tba,bal=(tba,ba,tbal)
			if True:
				tba[0]=4 # Paeth
				for i in range(Bpp): tba[i+1]=(row[i]-PngCompress.paethpredictor(0,urow[i],0))%256
				for i in range(Bpp,widthxB): tba[i+1]=(row[i]-PngCompress.paethpredictor(row[i-Bpp],urow[i],urow[i-Bpp]))%256
				tbal=PngCompress.getcompsize(zco,tba)
				if tbal<bal: ba,tba,bal=(tba,ba,tbal)
			zba.extend(zco.compress(ba))
			urow=row
		zba.extend(zco.flush())
		PngCompress.writechunk(bio,b'IDAT',zba)

class Palette():
	@staticmethod
	def ddistance(a,b):
		dr=a[0]-b[0]
		dg=a[1]-b[1]
		db=a[2]-b[2]
		return dr*dr+dg*dg+db*db
	def __init__(self):
		self.colors=[]
		self.raw=None
		self.cache={}
	def loaddefaults(self):
		m='eNoFwftP2ggAAGD/vv12JrtLdpu7XVyce6rZzi2euBlFDVMBBQGBYltKX0BbaKFQsBYRKRWYVhRXJKADH8wHZG7ecsm+r6ur684oPDClM70f7DVYJifG3k4tdS+Ahsnh'\
'PuN4jyl810Lft67es20MWxd6XBgwq+tZlq3GD3+4cw/cG4+d6Ucu5TdYnrbrAfPsn2DxrxW5F0KeAlKvpzAITs84LMsWYx/s1jvnTDZLv0cedy2+gix/Q8qbFfeA16TzOC0O4x'\
'CEduOFUdA0DJseIupjbx6z6kegpSew6rEbfsdLoyD+Dgob3MxLb+E5yr7wrc8BRB9aHEDkfnxnhDBP+KAhbEePmZ+R6gwGzKF2nd9hQYB5FHgRKNGA0QM7DBg5RS7PYQgMLxLg'\
'4ge8+I9/798gMREAZ0j0FVXGYWCQPngW3n1Dq0Oh3CRjtxJBHRNxEgCIIXF4fowu2cjI63BlOWCfoLcc5NoCFXrH7k+z4DzjNzOojlu30oHZUMznh5YYKIY67DQWwl1+0sXitn'\
'kWAijMwGVG+QoZSI4IZRO3v8Qz07GqIa4uCniM9q5S3vFk3cNTYEQC+AgSJWBO0Se1WeEzwCd8UToYIWXKGWF9TARJM2485iWiMSDhT7ArmzQ6ufYFTCKrHE7HuY+p2oJU52O8'\
'W9Rs6RIh7poz1YCokFIqLQSp1XJQitMSKyYp02bzE0/xIqfySDhF8sm9sKjaM01hLagITF4gnJlaUfBmk0RKJJy5sxWlEc3UwlkNztf3UmQxHdpO++PZkibRiWwllYt6i+epza'\
'qS5RKKvL/BSVtrmHpRykW3lfWt/FaqeCznj4N7rdhuNVL6Wv4k1gqirNazu6esdi1obf7wa/7gUqpeauXKUVkpa9s7lXPtc+NAa23UO/vVRqNSOj6sbH65OaxVykfXueaPar2z'\
'0/heOOkcN74fntw0m9f1s3br9OLk7Ge99bN1fnN6dXvUvu1cfbtqX150bjrt/398++8XjhcUpA=='
		z=base64.standard_b64decode(m)
		raw=zlib.decompress(z)
		self.raw=raw
		for i in range(0,len(raw),3):
			self.colors.append(raw[i:i+3])
	def findclosest(self,rgb):
		bi=0
		bv=200000
		for i in range(1,len(self.colors)):
			v=Palette.ddistance(rgb,self.colors[i])
			if v<bv:
				bv=v
				bi=i
		return bi
	def getindex(self,rgba):
		if not rgba[3]: return 0
		rgb=tuple(rgba[0:3])
		i=self.cache.get(rgb,0)
		if i: return i
		i=self.findclosest(rgb)
		self.cache[rgb]=i
		return i
		

class FlatImage():
	def __init__(self,width,height,fillpixel):
		self.Bpp=len(fillpixel)
		self.width=width
		self.height=height
		self.rows=[]
		for i in range(height): self.rows.append(fillpixel*width)
		self.palette=None
		self.transtable=None
	def setpixel(self,x,y,pixel):
		self.rows[y][x*self.Bpp:(x+1)*self.Bpp]=pixel
	def getpixel4(self,x,y):
		if y>=0 and y<self.height and x>=0 and x<self.width: return self.rows[y][x*4:x*4+4]
	def getpng(self,isfast=False):
		return PngCompress.create(self.width,self.height,self.rows,isfast,palette=self.palette,transtable=self.transtable)
	def indexcolors(self,palette):
		self.palette=palette.raw
		haszero=False
		for row in self.rows:
			for i in range(len(row),0,-4):
				idx=palette.getindex(row[i-4:i])
				if not idx: haszero=True
				row[i-4:i]=(idx,)
		if haszero: self.transtable=b'\x00' # we're flattening to on/off transparency
	def checkforholes(self):
		ishole=False
		isnonhole=False
		for row in self.rows:
			for i in range(3,len(row),4):
				if row[i]==0:
					if isnonhole: return (True,True)
					ishole=True
				else:
					if ishole: return (True,True)
					isnonhole=True
		return (ishole,isnonhole)
	def interpolateone(self,x,y):
		mp=RGBMultiPoint()
		xys=((x-1,y-1),(x,y-1),(x+1,y-1),(x-1,y),(x+1,y),(x-1,y+1),(x,y+1),(x+1,y+1))
		for xy in xys:
			p=self.getpixel4(xy[0],xy[1])
			if p and p[3]: mp.addrgb(p[0],p[1],p[2])
		if not mp.count: return None
		p=mp.getrgb()
		return (p[0],p[1],p[2],255)
	def interpolate(self):
		while True:
			rowsdbl=[]
			needsmore=False
			for row in self.rows: rowsdbl.append(row[:])
			for j,row in enumerate(rowsdbl):
				for i in range(self.width):
					i4=i<<2
					if row[i4+3]!=0: continue
					p=self.interpolateone(i,j)
					if not p: needsmore=True
					else: row[i4:i4+4]=p
			self.rows=rowsdbl
			if not needsmore: break

class RGBMultiPoint():
	def __init__(self):
		(self.r,self.g,self.b,self.count)=(0,0,0,0)
	def addrgb(self,r,g,b):
		self.r+=r
		self.g+=g
		self.b+=b
		self.count+=1
	def getrgb(self):
		if not self.count: return (0,0,0)
		return (int(self.r/self.count),int(self.g/self.count),int(self.b/self.count))

class RGBMultiPoints():
	def __init__(self,width,height):
		self.rows=[]
		for i in range(height): self.addrow(width)
	def addrow(self,width):
		row=[]
		for i in range(width): row.append(RGBMultiPoint())
		self.rows.append(row)
	def setpixel(self,x,y,rgb):
		if y<0: raise ValueError
		mp=self.rows[y][x]
		mp.addrgb(rgb[0],rgb[1],rgb[2])
	def setrgba(self,rgba):
		for j,row in enumerate(self.rows):
			for i,mp in enumerate(row):
				if not mp.count: continue
				(r,g,b)=mp.getrgb()
				rgba.setpixel(i,j,(r,g,b,255))

class HypsoSphere():
	@staticmethod
	def readheader(f):
		r=[]
		fuse=3
		while True:
			b=f.read(1)
			r.append(b[0])
			if b==b'\n':
				fuse-=1
				if not fuse: break
		return bytes(r)
	def __init__(self,filename):
		self.filename=filename
		self.f=open(filename,'rb')
		header=HypsoSphere.readheader(self.f)
		self.offset=len(header)
		sheader=header.decode()
		lines=sheader.split('\n')
		if lines[0]=='P6': self.isgrayscale=False
		elif lines[0]=='P5': self.isgrayscale=True
		else: raise ValueError
		wh=lines[1].split(' ')
		self.width=int(wh[0])
		self.height=int(wh[1])
		if int(lines[2])!=255: raise ValueError
		self.dzr=1
		self.dzt=1
		self.dzw=2
		self.dzh=2
	def setcenter(self,lon,lat):
		crx=-(lon*M_PI)/180.0
		cry=-(lat*M_PI)/180.0
		self.crx=crx
		self.rot_a=math.cos(crx)
		self.rot_c=math.sin(crx)
		self.rot_e=math.cos(cry)
		self.rot_f=math.sin(cry)
	def setzoom(self,dzr,dzt,dzw,dzh):
		(self.dzr,self.dzt,self.dzw,self.dzh)=(dzr,dzt,dzw,dzh)
	def draw(self,rgba):
		destw=rgba.width
		destwm1=destw-1
		desth=rgba.height
		desthm1=desth-1
		(a,c,e,f)=(self.rot_a,self.rot_c,self.rot_e,self.rot_f)
		(dzr,dzt,dzw,dzh)=(self.dzr,self.dzt,self.dzw,self.dzh)
		multipoints=RGBMultiPoints(destw,desth)
		sclookup=[]
		for ui in range(self.width):
			rlon=((2*ui+1)*M_PI)/self.width - M_PI
			rlon+=self.crx
			sclookup.append( (math.cos(rlon), math.sin(rlon)) )
		pnm=self.f
		stride=self.width if self.isgrayscale else 3*self.width
		for uj in range(self.height):
			if isverbose_global:
				if not uj%100: print('HypsoSphere: reading line %d of %d\r'%(uj,self.height),file=sys.stderr,flush=True,end='')
			rlat=M_PI_2 - ((uj+0.5)*M_PI)/self.height
			r=math.cos(rlat)
			z=math.sin(rlat)
			rgbs=pnm.read(stride)
			for ui in range(self.width):
				sc=sclookup[ui]
				y=r*sc[1]
				if abs(y)>dzr: continue
				x=r*sc[0]
				x2=x*e-z*f
				if x2<0: continue
				z2=x*f+z*e
				if abs(z2)>dzt: continue
				ux=int(0.5+((y+dzr)*destwm1)/dzw)
				uy=int(0.5+((dzt-z2)*desthm1)/dzh)
				if self.isgrayscale: multipoints.setpixel(ux,uy,3*rgbs[ui])
				else: multipoints.setpixel(ux,uy,rgbs[ui*3:ui*3+3])
		if isverbose_global:
			print('HypsoSphere: reading line %d of %d'%(self.height,self.height),file=sys.stderr)
			print('Flattening multipoints',file=sys.stderr)
		multipoints.setrgba(rgba)

class Hypso():
	def __init__(self,width,height,cachedir=None,cachename=None):
		self.width=width
		self.height=height
		self.image=None
		self.pngdata=None
		if cachedir and cachename!=None:
			if not os.access(cachedir,os.X_OK):
				print('Cache directory not found: %s'%cachedir,file=sys.stderr)
				raise ValueError
			self.cachebase=cachedir+'/hypsocache'+cachename
		else:
			self.cachebase='hypsocache'
	def loadsphere(self,sphere):
		self.image=FlatImage(self.width,self.height,[0,0,0,0])
		sphere.draw(self.image)
	def loadraw(self,filename):
		try:
			f=open(filename,"rb")
		except FileNotFoundError:
			if isverbose_global: print('Checked cache for %s'%filename,file=sys.stderr)
			return False
		if isverbose_global: print('Loading raw image from %s'%filename,file=sys.stderr)
		self.image=FlatImage(self.width,self.height,[0,0,0,0])
		for j in range(self.height):
			for i in range(self.width):
				p=f.read(4)
				self.image.setpixel(i,j,p)
		f.close()
		return True
	def loadpng(self,filename):
		try:
			f=open(filename,"rb")
		except FileNotFoundError:
			if isverbose_global: print('Checked cache for %s'%filename,file=sys.stderr)
			return False
		if isverbose_global: print('Loading png image from %s'%filename,file=sys.stderr)
		self.pngdata=f.read()
		f.close()
		self.haspng=True
		return True
	def getraw(self):
		bio=io.BytesIO()
		for row in self.image.rows: bio.write(bytes(row))
		return bio.getvalue()
	def saveraw(self,filename):
		if isverbose_global: print('Saving rgba image to %s'%filename,file=sys.stderr)
		f=open(filename,"wb")
		f.write(self.getraw())
		f.close()
	def getpng(self,ismime=True,isfast=False):
		if not self.pngdata: 
			self.pngdata=self.image.getpng(isfast)
		if not ismime: return self.pngdata
		return base64.standard_b64encode(self.pngdata).decode()
	def savepng(self,filename):
		if isverbose_global: print('Saving png image to %s'%filename,file=sys.stderr)
		f=open(filename,"wb")
		f.write(self.getpng(ismime=False))
		f.close()
	def removealpha(self):
		for row in self.image.rows:
			for i in range(len(row)-1,0,-4):
				del row[i]
	def cornercut(self,corner,left,top):
		if corner==0:
			xoff=int((self.width*(left+1))/2)
			yoff=int((self.height*(1-top))/2)
			for j in range(yoff,self.height):
				row=self.image.rows[j]
				for i in range(xoff*4,self.width*4,4):
					row[i:i+4]=(0,0,0,0)
		else: raise ValueError # TODO
	def indexcolors(self,palette): self.image.indexcolors(palette)
	def loadraw_cache(self): return self.loadraw(self.cachebase+'.raw')
	def loadpng_cache(self): return self.loadpng(self.cachebase+'.png')
	def saveraw_cache(self,isverbose=False):
		fn=self.cachebase+'.raw'
		if isverbose and not isverbose_global: print('Saving rgba to %s'%fn,file=sys.stderr)
		return self.saveraw(fn)
	def savepng_cache(self,isverbose=False):
		fn=self.cachebase+'.png'
		if isverbose and not isverbose_global: print('Saving png to %s'%fn,file=sys.stderr)
		return self.savepng(fn)
	def interpolate(self):
		(ishole,isnonhole)=self.image.checkforholes()
		if not ishole: return # nothing to do
		if not isnonhole: return # nothing we can do
		if isverbose_global: print('Interpolating image to fill holes',file=sys.stderr)
		self.image.interpolate()

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
	def makelinefrompoints(points,index,partindex,draworder):
		pl=Polyline(index,partindex)
		pl.points=points
		return ShapePlus.makefrompolyline(pl,draworder)
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
			ret.draworder=0
		elif ret.type==NULL_TYPE_SHP:
			pass
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
	def print(self,prefix='',file=sys.stdout):
		print('%snumber: %d, shape: %s, parts: %d, points: %d'%(prefix,self.number,shapename(self.type),self.partscount,self.pointscount),
				file=file)
		if True:
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
				if True:
					for l in range(j,k):
						p=self.pointlist[l]
						p.print(file=file)
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
		if partindices==-1:
			for p in self.pointlist: mbr.add(p.lon,p.lat)
		else:
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
		return mbr.getcenter()

class Shp(): # don't try to extend shp, just store data as literally as possible
	def __init__(self,filename=None,installfile=None):
		if installfile:
			self.filename=installfile.filename
		else:
			self.filename=filename
		self.shapes=[]
		self.installfile=installfile
		self.bynickname={}
	def printinfo(self):
		if self.installfile: f=self.installfile.open()
		else: f=open(self.filename,"rb")
		header=f.read(100)
		filecode=uint32_big(header,0)
		bytes_filelength=2*uint32_big(header,24)
		version=uint32_little(header,28)
		print('filecode: 0x%x' % filecode)
		print('bytes_filelength: %d'%bytes_filelength)
		print('version: %d'%version)
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
		if self.installfile: f=self.installfile.open()
		else: f=open(self.filename,"rb")
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

class FlatRectangle():
	def __init__(self,bottomleft,topright):
		self.bottomleft=bottomleft
		self.topright=topright
	def getcenter(self):
		return ((self.bottomleft.ux+self.topright.ux)/2,(self.bottomleft.uy+self.topright.uy)/2)
	def getradius(self):
		(ax,ay)=self.getcenter()
		return FlatPoint.distance(ax,ay,self.bottomleft.ux,self.bottomleft.uy)

class SphereRectangle():
	@staticmethod
	def makefrommbr(mbr,rotation):
		sr=SphereRectangle()
		sr.bottomleft=SpherePoint.makefromlonlat(mbr.minx,mbr.miny,rotation)
		sr.topright=SpherePoint.makefromlonlat(mbr.maxx,mbr.maxy,rotation)
		return sr
	def __str__(self):
		return 'bottomleft: %s, topright: %s'%(self.bottomleft,self.topright)
	def flatten(self,width,height,right,top):
		return FlatRectangle( self.bottomleft.flatten(width,height,right,top), self.topright.flatten(width,height,right,top))

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
	def makefromdll(dll,rotation):
		return SpherePoint.makefromlonlat(dll.lon,dll.lat,rotation)
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
	def flatten(self,width,height,right=1,top=1):
		rightx2=right*2
		topx2=top*2
		ux=int(0.5+((self.y+right)*(width-1))/rightx2)
		uy=int(0.5+((top-self.z)*(height-1))/topx2)
		return FlatPoint(ux,uy,NONE_PATCHTYPE)
	def flattenf(self,width,height,right=1,top=1):
		rightx2=right*2
		topx2=top*2
		ux=((self.y+right)*(width-1))/rightx2
		uy=((top-self.z)*(height-1))/topx2
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
	def getmbr(self):
		mbr=Mbr()
		for p in self.points: mbr.add(p.ux,p.uy)
		return mbr

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
	@staticmethod
	def makefromzoom(zoom,width,height,splitlimit):
		right=1/zoom
		bzc=BoxZoomCleave(right,right,width,height,splitlimit)
		return bzc
	def __init__(self,right,top,width,height,splitlimit,shift=None):
		self.right=right
		self.top=top
		self.shift=shift
		self.width=width
		self.height=height
		self.splitlimit=splitlimit
	def __str__(self):
		return 'BoxZoomCleave(right:%f,top:%f,width:%d,height:%d)'%(self.right,self.top,self.width,self.height)
	def cleave(self,onesphere):
		if self.right!=1:
			self.isz=False
			self.ishigh=True
			self.val=self.right
			onesphere.cleave(self)
			self.isz=False
			self.ishigh=False
			self.val=-self.right
			onesphere.cleave(self)
		if self.top!=1:
			self.isz=True
			self.ishigh=True
			self.val=self.top
			onesphere.cleave(self)
			self.isz=True
			self.ishigh=False
			self.val=-self.top
			onesphere.cleave(self)
	def flatten(self,sphereshape):
		flatshape=sphereshape.flatten(self.width,self.height,self.splitlimit,self.right,self.top)
		if self.shift: flatshape.shift(self.shift)
		return flatshape
	def flattenpoint(self,spherepoint):
		flatpoint=spherepoint.flatten(self.width,self.height,self.right,self.top)
		if self.shift: flatpoint.shift(self.shift)
		return flatpoint
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

class AutoCenter():
	def __init__(self):
		self.miny=None
		self.maxy=None
		self.gaps=[]
		self.leftgap=None
		self.rightgap=None
	def addmbr(self,mbr):
		l=mbr.minx
		h=mbr.maxx
		if self.miny==None:
			self.miny=mbr.miny
			self.maxy=mbr.maxy
			if l==-180.0:
				if h==180.0: return
				self.gaps.append([h,180.0])
			elif h==180.0:
				self.gaps.append([-180.0,l])
			else:
				self.leftgap=l
				self.rightgap=h
			return
		for i in range(len(self.gaps)-1,-1,-1):
			g=self.gaps[i]
			if h<=g[0] or g[1]<=l: continue
			if l<=g[0] and g[1]<=h:
				del self.gaps[i]
				continue
			if g[0]<=l and h<=g[1]:
				if g[0]==l:
					g[0]=h
				elif h==g[1]:
					g[1]=l
				else:
					self.gaps.append([h,g[1]])
					g[1]=l
				continue
			if l<g[1]: g[1]=l
			elif g[0]<h: g[0]=h
		if self.leftgap!=None and l<self.leftgap:
			if h<self.leftgap:
				self.gaps.append([h,self.leftgap])
			if l==-180.0: self.leftgap=None
			else: self.leftgap=l
		if self.rightgap!=None and h>self.rightgap:
			if self.rightgap<l:
				self.gaps.append([self.rightgap,l])
			if h==180.0: self.rightgap=None
			else: self.rightgap=h
	def getcenter(self):
		lat=(self.miny+self.maxy)/2
		biggest=0
		lon=0
		if self.leftgap:
			if not self.rightgap:
				self.gaps.append([-180.0,self.leftgap])
				self.leftgap=None
		elif self.rightgap:
			self.gaps.append([self.rightgap,180.0])
			self.rightgap=None
		for g in self.gaps:
			r=g[1]-g[0]
			if r<biggest: continue
			biggest=r
			lon=(g[1]+g[0])/2+180
		if self.leftgap and self.rightgap:
			r=360-self.rightgap+self.leftgap
			if r>biggest:
				lon=(self.rightgap+self.leftgap)/2
		if lon>180: lon-=360
		return (lon,lat)

class AutoZoom():
	def __init__(self):
		self.shapes=[]
		self.spherembr=None
		self.center=None
		self.rotation=None
		self.zoomfactor=None
		self.width=None
		self.height=None
	def addshape(self,shape):
		self.shapes.append(shape)
	def getcenter(self):
		ac=AutoCenter()
		for s in self.shapes:
			for p in range(s.partscount):
				ac.addmbr(s.getmbr((p,)))
		self.center=ac.getcenter()
#		print('autocenter',self.center,file=sys.stderr)
		return self.center
	def getspherembr(self):
		(lon,lat)=self.getcenter()
		rotation=SphereRotation()
		rotation.set_deglonlat(lon,lat)
		self.rotation=rotation
		hc=HemiCleave()
		mbr=Mbr()
		for s in self.shapes:
			pluses=ShapePlus.make(s)
			for oneplus in pluses:
				onesphere=SphereShape(oneplus,rotation)
				hc.cleave(onesphere)
				if onesphere.type==NULL_TYPE_SHP: continue
				mbr.addmbr(onesphere.getmbr())
		self.spherembr=mbr
		return mbr
	def getzoomfactor(self):
		factors=(1.4,1.5625,2,2.5,3.125,4,5,6.25,8,10,12.5,16,20,25,32,40,50,64,80,100,128,160,200,256)
		mbr=self.getspherembr()
		works=1
		for x in factors:
			l=1/x
			l=l*0.99 # gives us a little margin
			if mbr.maxx>l: break
			if mbr.maxy>l: break
			if mbr.minx<-l: break
			if mbr.miny<-l: break
			works=x
		self.zoomfactor=works
		if isverbose_global: print('AutoZoom factor',works,file=sys.stderr)
		return works
	def getboxzoomcleave(self,width,splitlimit,isautotrim):
		scale=self.getzoomfactor()
		if scale==1: boxd=1
		else: boxd=1/scale
		boxw=boxd
		boxh=boxd
		height=width
		if isautotrim and scale!=1: # scale 1 isn't compatible yet, may never be
			smbr=self.spherembr
			dx=min(boxd-smbr.maxx,boxd+smbr.minx)
			dy=min(boxd-smbr.maxy,boxd+smbr.miny)
			if dx>dy:
				boxw=boxd-dx+dy
				width=int(boxw*width/boxd)
			else:
				boxh=boxd-dy+dx
				height=int(boxh*height/boxd)
			self.width=width
			self.height=height
		bzc=BoxZoomCleave(boxw,boxh,width,height,splitlimit)
		return bzc

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
	def reduce(self,isforce):
#		print('Reducing points: ',self.points,file=sys.stderr) #cdebug
		if self.isclosed:
			while True:
				if len(self.points)>1 and self.points[0]==self.points[-1]:
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
					k-=j
				i+=1

		if not isforce:
			if len(self.points)<2: self.points=[]

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
	def write(self,output,isforce=False):
		found=0
		for fragment in self.fragments:
			if not fragment.isreduced:
				fragment.reduce(isforce)
				fragment.isreduced=True
			found+=len(fragment.points)
		if not found: return
		output.newpath(self.cssclass)
		for fragment in self.fragments:
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
			if len(points)<2:
				output.addtopath('h1') # isforce, forces drawing of the pixel
			elif fragment.isclosed:
				output.addtopath('Z')
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
		elif self.type==POINT_TYPE_SHP:
			self.point.print(file=file)
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
	def cutout_printsvg(self,output,cssclass):
		svg=SvgPath(cssclass)
		for pg in self.polygons:
			p=pg.points[0]
			svg.moveto(p.ux,p.uy)
			for j in range(1,len(pg.points)):
				p=pg.points[j]
				svg.lineto(p.ux,p.uy)
			svg.closepath()
		svg.write(output)
	def path_printsvg(self,output,cssclass,cssreverse,isforcedpixel):
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
			if pg.ccwtype==IGNORE_CCWTYPE: continue
			if cssreverse and pg.ccwtype==REVERSE_CCWTYPE:
				hasreverse=True
				continue
			p=pg.points[0]
			svg.moveto(p.ux,p.uy)
			for j in range(1,len(pg.points)):
				p=pg.points[j]
				svg.lineto(p.ux,p.uy)
			svg.closepath()
		svg.write(output,isforce=isforcedpixel)
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
			svg.write(output,isforce=isforcedpixel)
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
	def polygon_printsvg(self,output,cssfull,csspatch,cssreverse,cssreversepatch,isforcedpixel):
		if True:
			self.path_printsvg(output,cssfull,cssreverse,isforcedpixel)
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
	def point_printsvg(self,output,cssclass,point=None):
		if not point: point=self.point
		output.countcss(cssclass)
		output.print('<circle class="%s" cx="%d" cy="%d" r="4"/>'%(cssclass,point.ux,point.uy))
	def pixel_printsvg(self,output,cssclass,point=None):
		if not point: point=self.point
		output.countcss(cssclass)
		output.print('<rect class="%s" x="%d.5" y="%d.5" width="1" height="1"/>'%(cssclass,point.ux-1,point.uy-1))
	def printsvg(self,output,cssline='line',cssfull='full',csspatch='patch',csspoint='point',cssforcepixel=None,
			cssreverse=None,cssreversepatch=None,
			isforcedpixel=False):
		if self.type==POLYGON_TYPE_SHP:
			if cssforcepixel:
				others=0
				for pg in self.polygons:
					mbr=pg.getmbr()
					r=mbr.getpseudoradius()
					if r<2:
						(ux,uy)=mbr.getcenter()
						ux=int(0.5+ux)
						uy=int(0.5+uy)
						p=FlatPoint(ux,uy,0)
						self.pixel_printsvg(output,cssforcepixel,p)
					else:
						others+=1
				if others:
					self.polygon_printsvg(output,cssfull,csspatch,cssreverse,cssreversepatch,isforcedpixel)
			else:
				self.polygon_printsvg(output,cssfull,csspatch,cssreverse,cssreversepatch,isforcedpixel)
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
	def flatten(self,width,height,splitlimit,right,top):
		r=FlatPolygon(self.polygon.iscw,self.polygon.index,self.polygon.partindex,self.polygon.ccwtype)
		rightx2=right*2
		topx2=top*2
		for p in self.points:
			p.ux=int(0.5+((p.y+right)*(width))/rightx2) # for <path>, we extend to the edge (no width-1)
			p.uy=int(0.5+((top-p.z)*(height))/topx2)
		i=0
		fuse=20000 # 1000 is too few for ocean.110m on a sphere
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
					n.ux=int(0.5+((n.y+right)*(width))/rightx2)
					n.uy=int(0.5+((top-n.z)*(height))/topx2)
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
	def getmbr(self):
		mbr=Mbr()
		for p in self.points: mbr.add(p.y,p.z)
		return mbr

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
		pg=self.polygon
		r=FlatPolygon(pg.iscw,pg.index,pg.partindex,pg.ccwtype)
		for p in self.points:
			(ux,uy)=tripel(p.lon,p.lat)
			ux=int(0.5+ux*widthm1)
			uy=int(0.5+heightm1-uy*heightm1)
			r.addpoint(ux,uy,NONE_PATCHTYPE)
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
	def flatten(self,width,height,right,top):
		r=FlatPolyline()
		rightx2=right*2
		topx2=top*2
		for p in self.points:
			ux=int(0.5+((p.y+right)*(width))/rightx2) # for <path>, we extend to the edge (no width-1)
			uy=int(0.5+((top-p.z)*(height))/topx2)
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
	def getmbr(self):
		mbr=Mbr()
		for p in self.points: mbr.add(p.y,p.z)
		return mbr

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
	def flatten(self,width,height,splitlimit=4,right=1,top=1):
		r=FlatShape()
		if self.type==POLYGON_TYPE_SHP:
			r.setpolygon()
			for x in self.polygons: r.addpolygon(x.flatten(width,height,splitlimit,right,top))
		elif self.type==POLYLINE_TYPE_SHP:
			r.setpolyline()
			for x in self.polylines: r.addpolyline(x.flatten(width,height,right,top))
		elif self.type==POINT_TYPE_SHP:
			r.setpoint(self.point.flatten(width,height,right,top))
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
	def getmbr(self):
		mbr=Mbr()
		if self.type==POLYGON_TYPE_SHP:
			for pg in self.polygons: mbr.addmbr(pg.getmbr())
		elif self.type==POLYLINE_TYPE_SHP:
			for pl in self.polylines: mbr.addmbr(pl.getmbr())
		elif self.type==POINT_TYPE_SHP:
			mbr.add(self.point.y,self.point.z)
		else: raise ValueError
		return mbr
			

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
	hc=HemiCleave()
	oneplus=ShapePlus.makefromdll(dll,0)
	onesphere=SphereShape(oneplus,rotation)
	hc.cleave(onesphere)
	if boxzoomcleave: boxzoomcleave.cleave(onesphere)
	if onesphere.type!=NULL_TYPE_SHP:
		if boxzoomcleave:
			flatshape=boxzoomcleave.flatten(onesphere)
		else:
			flatshape=onesphere.flatten(width,height)
		flatshape.printsvg(output,csspoint=csscircle)

def text_sphere_print_svg(output,dll,text,rotation,width,height,cssfont=TEXT_FONT_CSS,cssfontshadow=SHADOW_FONT_CSS,boxzoomcleave=None):
	hc=HemiCleave()
	oneplus=ShapePlus.makefromdll(dll,0)
	onesphere=SphereShape(oneplus,rotation)
	hc.cleave(onesphere)
	if boxzoomcleave: boxzoomcleave.cleave(onesphere)
	if onesphere.type!=NULL_TYPE_SHP:
		if boxzoomcleave:
			flatshape=boxzoomcleave.flatten(onesphere)
		else:
			flatshape=onesphere.flatten(width,height)
		p=flatshape.point
		output.countcss(cssfont)
		output.countcss(cssfontshadow)
		output.print('<text x="%d" y="%d" class="%s">%s</text>'%(p.ux,p.uy,cssfontshadow,text))
		output.print('<text x="%d" y="%d" class="%s">%s</text>'%(p.ux,p.uy,cssfont,text))
		return True

def pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit,cssline=None,cssfull=None,csspatch=None,
		cssreverse=None,cssreversepatch=None,
		boxzoomcleave=None, cornercleave=None):
	hc=HemiCleave()

	for oneplus in pluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if cornercleave: cornercleave.cleave(onesphere)
		if boxzoomcleave: boxzoomcleave.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			if boxzoomcleave:
				flatshape=boxzoomcleave.flatten(onesphere)
			else:
				flatshape=onesphere.flatten(width,height,splitlimit)
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

def cutout_sphere_print_svg(output,shapes,draworder,rotation,width,height,splitlimit,cssfull=None,boxzoomcleave=None, cornercleave=None):
	fullflat=FlatShape()
	fullflat.setpolygon()
	fpg=FlatPolygon(False,0,0,CUTOUT_CCWTYPE)
	fpg.addpoint(-2,-2,0) # want to keep border outside viewbox
	fpg.addpoint(-2,height+2,0)
	fpg.addpoint(width+2,height+2,0)
	fpg.addpoint(width+2,-2,0)
	fullflat.addpolygon(fpg)

	if isinstance(shapes,list):
		pluses=[]
		if draworder==-1:
			for one in shapes:
				pluses.extend(ShapePlus.make(one))
		else:
			for one in shapes:
				(has,_)=one.hasdraworder(draworder)
				if not has: continue
				pluses.extend(ShapePlus.make(one))
			for i in range(len(pluses)-1,-1,-1):
				if pluses[i].draworder!=draworder: del pluses[i]
	else:
		pluses=ShapePlus.make(shapes) # shapes is assumed to be just a shape

	hc=HemiCleave()
	for oneplus in pluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if cornercleave: cornercleave.cleave(onesphere)
		if boxzoomcleave: boxzoomcleave.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			if boxzoomcleave:
				flatshape=boxzoomcleave.flatten(onesphere)
			else:
				flatshape=onesphere.flatten(width,height,splitlimit)
			for pg in flatshape.polygons: fullflat.addpolygon(pg)
	fullflat.cutout_printsvg(output,cssfull)
	for pg in fullflat.polygons:
		mbr=pg.getmbr()
		r=mbr.getpseudoradius()
		if r<4:
			(ux,uy)=mbr.getcenter()
			p=FlatPoint(ux,uy,0)
			FlatShape.pixel_printsvg(None,output,cssfull,p)

def one_sphere_print_svg(output,one,draworder,rotation,width,height,splitlimit,cssline=None,cssfull=None,csspatch=None,
		cssforcepixel=None,
		cssreverse=None,cssreversepatch=None,
		boxzoomcleave=None, cornercleave=None,
		isforcedpixel=False,
		islabels=False):
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
				if boxzoomcleave:
					flatshape=boxzoomcleave.flatten(onesphere)
				else:
					flatshape=onesphere.flatten(width,height,splitlimit)
				flatshape.printsvg(output,
						cssline=cssline,cssfull=cssfull,csspatch=csspatch,cssforcepixel=cssforcepixel,
						cssreverse=cssreverse,cssreversepatch=cssreversepatch,isforcedpixel=isforcedpixel)
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
					if boxzoomcleave:
						flatshape=boxzoomcleave.flatten(onesphere)
					else:
						flatshape=onesphere.flatten(width,height,splitlimit)
					flatshape.printsvg(output,
							cssline=cssline,cssfull=cssfull,csspatch=csspatch,cssforcepixel=cssforcepixel,
							cssreverse=cssreverse,cssreversepatch=cssreversepatch,isforcedpixel=isforcedpixel)
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
def print_rectwater_svg(output,width,height,fill="#5685a2"):
	output.print('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>'%(width,height,fill))
def print_squarewater_svg(output,length,fill="#5685a2"):
	print_rectwater_svg(output,length,length,fill)
def print_rectangle_svg(output,xoff,yoff,w,h,fill,opacity):
	output.print('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="%.1f"/>'%(xoff,yoff,w,h,fill,opacity))
def print_hypso_svg(output,width,height,hypso,isfast=False,isgradients=False):
	output.print0('<image x="0" y="0" width="%d" height="%d" xlink:href="data:image/png;base64,'%(width,height))
	if isverbose_global: print('Compressing png (isfast:%s)'%isfast,file=sys.stderr)
	b=hypso.getpng(isfast=isfast,ismime=True)
	output.print0(b)
	output.print('" />')
	if isgradients:
		radius=width/2
		rs='%.1f' % (radius)
		output.countcss('url(#sungradient)')
		output.print('<circle cx="%s" cy="%s" r="%s" fill="url(#sungradient)"/>' % (rs,rs,rs))

def print_header_svg(output,width,height,opts,labelfont='14px sans',comments=None,isgradients=False,ishypso=None):
	half=int(width/2)
	output.print('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
	output.print('<svg xmlns:svg="http://www.w3.org/2000/svg" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="%d" width="%d">' % (height,width))
	output.print('<!-- made with pythonshp (GPL): github.com/sanjayrao77/pythonshp , underlying data may come from naturalearthdata.com -->')
	if comments!=None:
		for comment in comments:
			print_comment_svg(output,comment)

	if ishypso:
		if 'url(#sungradient)' in opts:
			output.print('<defs>')
			output.print('	<radialGradient id="sungradient" cx="%d" cy="%d" r="%d" fx="%d" fy="%d" gradientUnits="userSpaceOnUse">'%(half,half,half,half,half))
			output.print('		<stop offset="0%" stop-color="#000000" stop-opacity="0.00"/>')
			output.print('		<stop offset="11%" stop-color="#000000" stop-opacity="0.03"/>')
			output.print('		<stop offset="22%" stop-color="#000000" stop-opacity="0.07"/>')
			output.print('		<stop offset="31%" stop-color="#000000" stop-opacity="0.10"/>')
			output.print('		<stop offset="41%" stop-color="#000000" stop-opacity="0.14"/>')
			output.print('		<stop offset="51%" stop-color="#000000" stop-opacity="0.17"/>')
			output.print('		<stop offset="59%" stop-color="#000000" stop-opacity="0.20"/>')
			output.print('		<stop offset="67%" stop-color="#000000" stop-opacity="0.23"/>')
			output.print('		<stop offset="75%" stop-color="#000000" stop-opacity="0.27"/>')
			output.print('		<stop offset="81%" stop-color="#000000" stop-opacity="0.30"/>')
			output.print('		<stop offset="87%" stop-color="#000000" stop-opacity="0.33"/>')
			output.print('		<stop offset="92%" stop-color="#000000" stop-opacity="0.37"/>')
			output.print('		<stop offset="95%" stop-color="#000000" stop-opacity="0.40"/>')
			output.print('		<stop offset="98%" stop-color="#000000" stop-opacity="0.43"/>')
			output.print('		<stop offset="100%" stop-color="#000000" stop-opacity="0.50"/>')
			output.print('	</radialGradient>')
			output.print('</defs>')
	else:
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

	css=[]

	if not ishypso:
		if not isgradients:
			if LAND_SPHERE_CSS in opts: css.append('.sl {fill:#aaaaaa;stroke:#888888}')
			if PATCH_LAND_SPHERE_CSS in opts: css.append('.sp {stroke:#aaaaaa;fill-opacity:0}')
			if BORDER_SPHERE_CSS in opts: css.append('.sb {stroke:#888888;fill-opacity:0}')
			if WATER_SPHERE_CSS in opts: css.append('.sw {fill:#5685a2;stroke-opacity:0}')
			if PATCH_WATER_SPHERE_CSS in opts: css.append('.sr {stroke:#5685a2;fill-opacity:0}')
		else:
			if LAND_SPHERE_CSS in opts: css.append('.sl {fill:url(#landgradient);stroke:url(#bordergradient)}')
			if PATCH_LAND_SPHERE_CSS in opts: css.append('.sp {stroke:url(#landgradient);fill-opacity:0}')
			if BORDER_SPHERE_CSS in opts: css.append('.sb {stroke:url(#bordergradient);fill-opacity:0}')
			if WATER_SPHERE_CSS in opts: css.append('.sw {fill:url(#watergradient);stroke:url(#watergradient);stroke-opacity:0.8}')
			if PATCH_WATER_SPHERE_CSS in opts: css.append('.sr {stroke:url(#watergradient);fill-opacity:0}')
		if HIGH_BORDER_SPHERE_CSS in opts: css.append('.si {stroke:%s;fill-opacity:0;stroke-opacity:0.3}'%highlight_b)
		if HIGH_LAND_SPHERE_CSS in opts: css.append('.sh {fill:%s;stroke:%s}'%(highlight,highlight_b))
		if PATCH_HIGH_LAND_SPHERE_CSS in opts: css.append('.sq {stroke:%s;fill-opacity:0}'%highlight)

		# halflight areas
	# 7aaa58
	# aaaa11
		if AREA_LAND_SPHERE_CSS in opts: css.append('.al {fill:#aaaa11;stroke:#707070}')
		if PATCH_AREA_LAND_SPHERE_CSS in opts: css.append('.ap {stroke:#aaaa11;fill-opacity:0}')
		if AREA_BORDER_SPHERE_CSS in opts: css.append('.ab {stroke:#707070;fill-opacity:0}')
		if AREA_LAKELINE_SPHERE_CSS in opts: css.append('.ai {stroke:#707070;fill-opacity:0;stroke-opacity:0.3}')

		# disputed and breakaway areas
		if DISPUTED_LAND_SPHERE_CSS in opts: css.append('.dl {fill:#11dd11;stroke:#08cc08;stroke-dasharray:1 1}')
		# disputed border
		if DISPUTED_BORDER_SPHERE_CSS in opts: css.append('.db {fill:#11dd11;stroke:#11dd11;stroke-opacity:1}')
		if PATCH_DISPUTED_LAND_SPHERE_CSS in opts: css.append('.dp {stroke:#11dd11;fill-opacity:0}')
		# sphere lon/lat grid
		if GRID_SPHERE_CSS in opts: css.append('.sg {stroke:#000000;fill-opacity:0.0;stroke-opacity:0.2}')

	else: # hypso
		if HYPSOCUT_SPHERE_CSS in opts:
			if not isgradients:
				css.append('.hc {stroke:#ffffff;fill:#000000;fill-opacity:0.35}')
				if LAND_SPHERE_CSS in opts: css.append('.sl {stroke:#ffffff;fill:#000000;fill-opacity:0.25;stroke-opacity:0.5}')
				if BORDER_SPHERE_CSS in opts: css.append('.sb {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.5}')
			else:
				css.append('.hc {stroke:#ffffff;fill:#000000;fill-opacity:0.2}')
				if LAND_SPHERE_CSS in opts: css.append('.sl {stroke:#ffffff;fill:#000000;fill-opacity:0.1;stroke-opacity:0.3}')
				if BORDER_SPHERE_CSS in opts: css.append('.sb {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.3}')
			if HIGH_LAND_SPHERE_CSS in opts: css.append('.sh {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.8}')
		else:
			if LAND_SPHERE_CSS in opts: css.append('.sl {stroke:#ffffff;stroke-opacity:0.7;fill:#000000;fill-opacity:0.5}')
			if BORDER_SPHERE_CSS in opts: css.append('.sb {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.7}')
			if HIGH_LAND_SPHERE_CSS in opts: css.append('.sh {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.8}')
		if PATCH_LAND_SPHERE_CSS in opts: css.append('.sp {stroke:#ffffff;fill-opacity:0;stroke-dasharray:3 3}')
		if WATER_SPHERE_CSS in opts: css.append('.sw {fill:#5685a2;stroke-opacity:0}')
		if PATCH_WATER_SPHERE_CSS in opts: css.append('.sr {stroke:#5685a2;fill-opacity:0}')
		if HIGH_BORDER_SPHERE_CSS in opts: css.append('.si {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.5}')
		if PATCH_HIGH_LAND_SPHERE_CSS in opts: css.append('.sq {stroke:#ffffff;fill-opacity:0;stroke-dasharray:3 3}')

		# halflight areas
	# 7aaa58
	# aaaa11
		if AREA_LAND_SPHERE_CSS in opts: css.append('.al {stroke:#000000;fill-opacity:0}')
		if PATCH_AREA_LAND_SPHERE_CSS in opts: css.append('.ap {stroke:#ffffff;fill-opacity:0;stroke-dasharray:3 3}')
		if AREA_BORDER_SPHERE_CSS in opts: css.append('.ab {stroke:#000000;fill-opacity:0}')
		if AREA_LAKELINE_SPHERE_CSS in opts: css.append('.ai {stroke:#707070;fill-opacity:0;stroke-opacity:0.8}')

		# disputed and breakaway areas
		if DISPUTED_LAND_SPHERE_CSS in opts: css.append('.dl {fill:#11dd11;stroke:#11dd11}')
		# disputed border
		if DISPUTED_BORDER_SPHERE_CSS in opts: css.append('.db {fill:#11dd11;stroke:#11dd11}')
		if PATCH_DISPUTED_LAND_SPHERE_CSS in opts: css.append('.dp {stroke:#11dd11;fill-opacity:0}')
		# sphere lon/lat grid
		if GRID_SPHERE_CSS in opts: css.append('.sg {stroke:#ffffff;fill-opacity:0.0;stroke-opacity:0.3}')

	# disputed zoom land
	if DISPUTED_LAND_ZOOM_CSS in opts: css.append('.dz {fill:#11dd11;stroke:#11dd11;stroke-dasharray:2 2}')
	# zoom border
	if DISPUTED_BORDER_ZOOM_CSS in opts: css.append('.dy {fill:#11dd11;stroke:#11dd11;stroke-opacity:1}')
	# zoom patch
	if PATCH_DISPUTED_LAND_ZOOM_CSS in opts: css.append('.dx {stroke:#11dd11;stroke-dasharray:3 3;fill-opacity:0}')

	# font lon/lat shadow
	if SHADOW_FONT_CSS in opts: css.append('.fs {font:%s;stroke:#ffffff;stroke-width:2px;stroke-opacity:0.8;text-anchor:middle}'%labelfont)
#	if SHADOW_FONT_CSS in opts: css.append('.fs { font:%s;fill:none;fill-opacity:1;stroke:#ffffff;stroke-width:2px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:0.9;text-anchor:middle }'%labelfont)
	# font lon/lat text
	if TEXT_FONT_CSS in opts: css.append('.ft {font:%s;fill:#000000;fill-opacity:1;stroke-opacity:0;text-anchor:middle}'%labelfont) 

	# for mercator, this should probably be updated
	if COAST_TRIPEL_CSS in opts: css.append('.tc {stroke:black;fill-opacity:0}')
	# tripel ocean
	if OCEAN_TRIPEL_CSS in opts:
		css.append('.to {fill:#eeeeee;stroke:black}')
		if BACK_TRIPEL_CSS in opts: css.append('.tb {fill:#aaaaaa;stroke:black;stroke-width:2}') # tripel background
	# tripel land
	if LAND_TRIPEL_CSS in opts:
		css.append('.tl {fill:#aaaaaa;stroke:black}')
		if ishypso:
			if isgradients:
				if BACK_TRIPEL_CSS in opts: css.append('.tb {fill:#bbbbbb;stroke:black;stroke-width:2}') # tripel background
			else:
				if BACK_TRIPEL_CSS in opts: css.append('.tb {fill:#cccccc;stroke:black;stroke-width:2}') # tripel background # TODO
		else:
			if BACK_TRIPEL_CSS in opts: css.append('.tb {fill:#eeeeee;stroke:black;stroke-width:2}') # tripel background

	# tripel lon/lat
	if GRID_TRIPEL_CSS in opts: css.append('.tg {stroke:black;stroke-opacity:0.2;fill-opacity:0}')
	if 'tl1' in opts: css.append('.tl1 {fill:#dddddd;stroke:#444444}')
	# tripel patch
	if PATCH_LAND_TRIPEL_CSS in opts: css.append('.tp {stroke:#dddddd;fill-opacity:0}')
	if 'tp1' in opts: css.append('.tp1 {stroke:#dddddd;fill-opacity:0}')
	# trip highlight
	if HIGH_LAND_TRIPEL_CSS in opts: css.append('.th {fill:%s;stroke:%s}'%(highlight,highlight_tb))
	if PATCH_HIGH_LAND_TRIPEL_CSS in opts: css.append('.tq {stroke:%s;fill-opacity:0}'%highlight)

	if ishypso:
		# zoom land
		if LAND_ZOOM_CSS in opts: css.append('.zl {fill:#cccccc;stroke:#444444}')
		# zoom patch
		if PATCH_LAND_ZOOM_CSS in opts: css.append('.zp {stroke:#cccccc;stroke-dasharray:3 3;fill-opacity:0}')
	else:
		# zoom land
		if LAND_ZOOM_CSS in opts: css.append('.zl {fill:#dddddd;stroke:#444444}')
		# zoom patch
		if PATCH_LAND_ZOOM_CSS in opts: css.append('.zp {stroke:#dddddd;stroke-dasharray:3 3;fill-opacity:0}')
	# zoom border
	if BORDER_ZOOM_CSS in opts: css.append('.zb {stroke:#444444;fill-opacity:0}')
	if 'debugzp' in opts: css.append('.debugzp {stroke:#00ff00;stroke-dasharray:3 3;stroke-width:2;fill-opacity:0}')
	# zoom highlight
	if HIGH_LAND_ZOOM_CSS in opts: css.append('.zh {fill:%s;stroke:%s}'%(highlight,highlight_bz))
	# zoom highlight patch
	if PATCH_HIGH_LAND_ZOOM_CSS in opts: css.append('.zq {stroke:%s;stroke-dasharray:3 3;fill-opacity:0}'%highlight)
#	if WATER_ZOOM_CSS in opts: css.append('.zw {fill:#5685a2;stroke-opacity:0}')
	if HIGH_LAKELINE_ZOOM_CSS in opts: css.append('.zi {stroke:%s;fill-opacity:0;stroke-opacity:0.5}'%(highlight_bz))
# 0x64a8d2 * 0.9 + 0.1 * 0xdddddd = 0x70add3

	if ishypso:
		if WATER_ZOOM_CSS in opts: css.append('.zw {fill:#5685a2;fill-opacity:0.9;stroke-opacity:0.9}')
		if PATCH_WATER_ZOOM_CSS in opts: css.append('.zr {stroke:#5685a2;stroke-dasharray:3 3;fill-opacity:0}')
	else:
		if WATER_ZOOM_CSS in opts: css.append('.zw {fill:#64a8d2;fill-opacity:0.9;stroke-opacity:0.9}')
		if PATCH_WATER_ZOOM_CSS in opts: css.append('.zr {stroke:#5685a2;stroke-dasharray:3 3;fill-opacity:0}')

	if 'debugl' in opts: css.append('.debugl {stroke:#00ff00;fill-opacity:0;stroke-width:1}')
	if 'debuggreen' in opts: css.append('.debuggreen {stroke:#00ff00;fill:#005500}')
	if 'debugred' in opts: css.append('.debugred {stroke:#ff0000;fill:#550000}')
	if 'debugredline' in opts: css.append('.debugredline {stroke:#ff0000;fill-opacity:0}')

	if OVERLAP_SPHERE_CSS in opts:css.append('.so {stroke:#ff0000;fill-opacity:0.25;fill:#ff0000}')

	if ONE_DISPUTED_CIRCLE_CSS in opts: css.append('.d1 {stroke:#11dd11;fill-opacity:0}')

	if width==500: # circles
		if ONE_CIRCLE_CSS in opts: css.append('.c1 {stroke:%s;fill-opacity:0}'%highlight)
		if TWO_CIRCLE_CSS in opts: css.append('.c2 {stroke:%s;fill-opacity:0}'%highlight)
		if THREE_CIRCLE_CSS in opts: css.append('.c3 {stroke:%s;fill-opacity:0;stroke-width:1.5}'%highlight)
		if FOUR_CIRCLE_CSS in opts: css.append('.c4 {stroke:%s;fill-opacity:0;stroke-width:2}'%highlight)
		if SHADOW_ONE_CIRCLE_CSS in opts: css.append('.w1 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6}')
		if SHADOW_TWO_CIRCLE_CSS in opts: css.append('.w2 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6}')
		if SHADOW_THREE_CIRCLE_CSS in opts: css.append('.w3 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:1.5}')
		if SHADOW_FOUR_CIRCLE_CSS in opts: css.append('.w4 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:2}')
	else:
		if ONE_CIRCLE_CSS in opts: css.append('.c1 {stroke:%s;fill-opacity:0}'%highlight)
		if TWO_CIRCLE_CSS in opts: css.append('.c2 {stroke:%s;fill-opacity:0;stroke-width:2}'%highlight)
		if THREE_CIRCLE_CSS in opts: css.append('.c3 {stroke:%s;fill-opacity:0;stroke-width:3}'%highlight)
		if FOUR_CIRCLE_CSS in opts: css.append('.c4 {stroke:%s;fill-opacity:0;stroke-width:4}'%highlight)
		if SHADOW_ONE_CIRCLE_CSS in opts: css.append('.w1 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6}')
		if SHADOW_TWO_CIRCLE_CSS in opts: css.append('.w2 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:2}')
		if SHADOW_THREE_CIRCLE_CSS in opts: css.append('.w3 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:3}')
		if SHADOW_FOUR_CIRCLE_CSS in opts: css.append('.w4 {stroke:#ffffff;fill-opacity:0;stroke-opacity:0.6;stroke-width:4}')

	css.sort()
	for c in css: output.print(c)
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
				flatshape.printsvg(output,cssline=GRID_SPHERE_CSS)
	for deg in lons:
		one=ShapePolyline.makelon(0,0,deg)
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onesphere=SphereShape(oneplus,rotation)
			hc.cleave(onesphere)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height,splitlimit)
				flatshape.printsvg(output,cssline=GRID_SPHERE_CSS)

def arcs_lonlat_print_svg(output,rotation,width,height):
	lats=[-60.0,-30.0,0.0,30.0,60.0]
	lons=[-180,-150,-120,-90,-60,-30,0,30,60,90,120,150]
	for deg in lats:
		e=SphereLatitude(rotation.dlat,deg)
		fe=e.flatten(width,height)
		fe.printsvg(output,GRID_SPHERE_CSS)
	for deg in lons:
		e=SphereLongitude.make(rotation,deg)
		if e==None:
#			print('deg:%d rotation.dlon:%f skipped'%(deg,rotation.dlon),file=sys.stderr)
			continue
#		print('deg:%d rotation.dlon:%f not skipped'%(deg,rotation.dlon),file=sys.stderr)
		fe=e.flatten(width,height)
		fe.printsvg(output,GRID_SPHERE_CSS)

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
				flatshape.printsvg(output,cssline=GRID_TRIPEL_CSS)
	for deg in lons:
		one=ShapePolyline.makelon(0,0,deg)
		pluses=ShapePlus.make(one)
		for oneplus in pluses:
			onewt=TripelShape(oneplus)
			if onewt.type!=NULL_TYPE_SHP:
				flatshape=onewt.flatten(width,height)
				flatshape.shift(shift)
				flatshape.printsvg(output,cssline=GRID_TRIPEL_CSS)

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
	def __str__(self):
		return 'PartCircle(%f,%f,%f)'%(self.x,self.y,self.r)

def findcircle_part_shape(shape,partindex,rotation,width_in,height_in,boxzoomcleave=None,threshhold=0):
	width=width_in
	height=height_in
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
		if boxzoomcleave:
			boxzoomcleave.cleave(onesphere)
			if onesphere.type==NULL_TYPE_SHP: continue
			flatshape=boxzoomcleave.flatten(onesphere)
		else:
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

	ax=int(0.5+ax)
	ay=int(0.5+ay)
	r=int(0.5+math.sqrt(r2))

	if threshhold and r>threshhold: return None
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

def print_zoomdots_svg(output,shape,zoomdots,sds,cssclass1,cssclass2,rotation,width,height,boxzoomcleave,threshhold=0):
	circles=[]
	if zoomdots==-1: zoomdots=range(shape.partscount)
	for dot in zoomdots:
		fc=findcircle_part_shape(shape,dot,rotation,width,height,boxzoomcleave,threshhold)
		if fc==None: continue
		circles.append(fc)
	trimcircles(circles,sds)
	for p in circles:
		if not p.isactive:
			if isverbose_global: print('Skipping zoomdot %d'%(p.name),file=sys.stderr)
			continue
		radius=p.r
		radius+=sds
		output.countcss(cssclass1)
		output.countcss(cssclass2)
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius+1))
		if radius>10:
			output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius-1))
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,p.x,p.y,radius))

def print_flatdot_svg(output,ux,uy,radius,cssclass1,cssclass2):
	output.countcss(cssclass1)
	output.countcss(cssclass2)
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,ux,uy,radius+1))
	if radius>10:
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,ux,uy,radius-1))
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,ux,uy,radius))

def print_centerdot_svg(output,lon,lat,radius,cssclass1,cssclass2,rotation,width,height,boxzoomcleave=None):
	sp=SpherePoint.makefromdll(DegLonLat(lon,lat),rotation)
	if boxzoomcleave:
		fp=boxzoomcleave.flattenpoint(sp)
	else:
		fp=sp.flatten(width,height)
	output.countcss(cssclass1)
	output.countcss(cssclass2)
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,fp.ux,fp.uy,radius+1))
	if radius>10:
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,fp.ux,fp.uy,radius-1))
	output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,fp.ux,fp.uy,radius))

def print_smalldots_svg(output,shape,smalldots,sds,cssclass1,cssclass2,rotation,width,height,threshhold=0):
	circles=[]
	if smalldots==-1: smalldots=range(shape.partscount)
	for dot in smalldots:
		fc=findcircle_part_shape(shape,dot,rotation,width,height,None,threshhold)
		if fc==None: continue
		circles.append(fc)
	trimcircles(circles,sds)
	for p in circles:
		if not p.isactive:
			if isverbose_global: print('Skipping smalldot %d'%(p.name),file=sys.stderr)
			continue
		radius=p.r
		radius+=sds
		output.countcss(cssclass1)
		output.countcss(cssclass2)
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius+1))
		if radius>10:
			output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass2,p.x,p.y,radius-1))
		output.print('<circle class="%s" cx="%d" cy="%d" r="%d"/>'%(cssclass1,p.x,p.y,radius))
	
def combo_print_svg(output,options,full_admin0,sphere_admin0,zoom_admin0,labels):
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
	isusacan=False

	if 'gsg' in options and options['gsg'] in ('US1.USA','CAN.CAN'): isusacan=True

	if True: #cdebug
		sphere_wc=WorldCompress(sphere_admin0,-1)
		sphere_wc.addcontinents('sphere',isusacan)
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
		if not options['zoomlon']: options['zoomlon']=lon
		if not options['zoomlat']: options['zoomlat']=lat
	rotation2=SphereRotation()
	rotation2.set_deglonlat(options['zoomlon'],options['zoomlat'])

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

	if options['hypso']:
		hypso=Hypso(options['hypsodim'],options['hypsodim'],'./hypsocache',options['hypsocache'])
		if options['hypsocache']==None or not hypso.loadpng_cache():
			if options['hypsocache']==None or not hypso.loadraw_cache():
				hs=HypsoSphere(install.getfilename(options['hypso']+'.pnm',['10m']))
				hs.setcenter(rotation.dlon,rotation.dlat)
				hypso.loadsphere(hs)
				if options['hypsocache']!=None:
					hypso.saveraw_cache(True)
			if cornercleave: hypso.cornercut(cornercleave.corner,cornercleave.xval,cornercleave.yval)
			p=Palette()
			p.loaddefaults()
			if isverbose_global: print('Indexing colors',file=sys.stderr)
			hypso.indexcolors(p)
			if options['hypsocache']!=None:
				hypso.savepng_cache(True)
		print_hypso_svg(output,width,height,hypso,isfast=False,isgradients=True)
	else: # not hypso
		if options['bgcolor']: print_rectangle_svg(output,0,0,width,height,options['bgcolor'],1.0)
		if options['isroundwater']:
			if width==height: print_roundwater_svg(output,width)

	if isverbose_global: print('Drawing admin0 sphere shapes',file=sys.stderr)

	if True: #cdebug
		sphere_wc.removeoverlaps(sphere_admin0.shapes,2) # remove draworder 2 (highlights) from border polylines
#		if options['isdisputed']: # TODO check if we can remove this?
#			sphere_wc.removeoverlaps(sphere_admin0.disputed.shapes,1)
			
		if options['iszoom'] and options['spherem']!=options['zoomm']:
			zoom_wc.removeoverlaps(sphere_admin0.shapes,2) # remove draworder 2 (highlights) from border polylines
#			if options['isdisputed']: # TODO potential remove
#				zoom_wc.removeoverlaps(zoom_admin0.disputed.shapes,1)

		pluses=sphere_wc.getpluses(isnegatives=False,isoverlaps=False)
		negatives=sphere_wc.getnegatives()

		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit,
				cornercleave=cornercleave, cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)
		for one in sphere_admin0.shapes:
				one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit, cornercleave=cornercleave,
						cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)
		pluses_sphere_print_svg(output,negatives,rotation,width,height,splitlimit,
				cornercleave=cornercleave, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS)

	if False:
		for one in sphere_admin0.shapes:
#			if one.nickname!='TZA.TZA': continue #cdebug
#			print('drawing %s %d'%(one.nickname,one.draworder),file=sys.stderr) #cdebug
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,
					cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,cssreverse=WATER_SPHERE_CSS,cssreversepatch=PATCH_WATER_SPHERE_CSS,cornercleave=cornercleave)
		for one in sphere_admin0.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull=AREA_LAND_SPHERE_CSS,csspatch=PATCH_AREA_LAND_SPHERE_CSS,
					cornercleave=cornercleave) # halflights

	if options['hypso'] and options['hypsocutout']:
		if options['isfullhighlight']:
			cutout_sphere_print_svg(output,full_admin0.shapes,2,rotation,width,height,splitlimit,cssfull=HYPSOCUT_SPHERE_CSS,
					cornercleave=cornercleave)
		else:
			cutout_sphere_print_svg(output,sphere_admin0.shapes,2,rotation,width,height,splitlimit,cssfull=HYPSOCUT_SPHERE_CSS,
					cornercleave=cornercleave)
	else:
		if options['isfullhighlight']:
			for one in full_admin0.shapes: # highlights
				one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,
						csspatch=PATCH_HIGH_LAND_SPHERE_CSS, cssforcepixel=HIGH_LAND_SPHERE_CSS,islabels=options['ispartlabels'])
		else:
			for one in sphere_admin0.shapes: # highlights
				one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,
						csspatch=PATCH_HIGH_LAND_SPHERE_CSS,islabels=options['ispartlabels'])

	if options['isfullpartlabels']:
		for one in full_admin0.shapes: # highlights
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,
					csspatch=PATCH_HIGH_LAND_SPHERE_CSS,islabels=True)

	if options['islakes'] and not options['hypso']:
		if isverbose_global: print('Drawing lakes sphere shapes',file=sys.stderr)
		pluses=sphere_admin0.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS)

	if options['isdisputed']:
		for one in sphere_admin0.disputed.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull=DISPUTED_LAND_SPHERE_CSS,
					csspatch=PATCH_DISPUTED_LAND_SPHERE_CSS, cssforcepixel=DISPUTED_BORDER_SPHERE_CSS)
		for one in sphere_admin0.disputed.shapes:
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=DISPUTED_BORDER_SPHERE_CSS,
					csspatch=PATCH_DISPUTED_LAND_SPHERE_CSS, cssforcepixel=DISPUTED_BORDER_SPHERE_CSS)


	pluses=sphere_wc.getpluses(ispositives=False,isoverlaps=True)
	pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssline=BORDER_SPHERE_CSS)

	borderlakeshapes=None
	zoom_borderlakeshapes=None
	if options['islakes']:
		if isverbose_global: print('Drawing border lakes (%s)'%options['spherem'],file=sys.stderr)
		sasi=ShpAdminShapeIntersection()
		sasi.addfromshapes(sphere_admin0.shapes,2)
		if options['isdisputed']: sasi.addfromshapes(sphere_admin0.disputed.shapes,1)
		for l in sphere_admin0.lakes.shapes:
			sasi.setinside(l)
		borderlakeshapes=sasi.exportlines()
		if options['iszoom']:
			if options['spherem']==options['zoomm']:
				zoom_borderlakeshapes=borderlakeshapes
			else:
				if isverbose_global: print('Drawing border lakes (%s)'%options['zoomm'],file=sys.stderr)
				sasi=ShpAdminShapeIntersection()
				sasi.addfromshapes(zoom_admin0.shapes,2)
				if options['isdisputed']: sasi.addfromshapes(zoom_admin0.disputed.shapes,1)
				for l in zoom_admin0.lakes.shapes:
					sasi.setinside(l)
				zoom_borderlakeshapes=sasi.exportlines()

		for plus in borderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=HIGH_BORDER_SPHERE_CSS)

	if 'moredots' in options: # [ (r0,isw0,[partindex00,partindex01]), ... , (rn,iswn,[partindexn0..partindexnm]) ]
		for moredots in options['moredots']:
			shape=full_admin0.shapes[full_index]
			sds=int((moredots[0]*width)/1000)
			isw=moredots[1]
			smalldots=moredots[2]
			cssclass=ONE_CIRCLE_CSS
			if isinstance(isw,bool) and isw: cssclass=FOUR_CIRCLE_CSS
			elif isw==1: cssclass=ONE_CIRCLE_CSS
			elif isw==2: cssclass=TWO_CIRCLE_CSS
			elif isw==3: cssclass=THREE_CIRCLE_CSS
			elif isw==4: cssclass=FOUR_CIRCLE_CSS
			cssclass2=getshadow_circle_css(cssclass)
			print_smalldots_svg(output,shape,smalldots,sds,cssclass,cssclass2,rotation,width,height)

	if 'centerdot' in options: # (r0,isw0)
		r=int((options['centerdot'][0]*width)/1000)
		isw=options['centerdot'][1]
		cssclass=ONE_CIRCLE_CSS
		if isinstance(isw,bool) and isw: cssclass=FOUR_CIRCLE_CSS
		elif isw==1: cssclass=ONE_CIRCLE_CSS
		elif isw==2: cssclass=TWO_CIRCLE_CSS
		elif isw==3: cssclass=THREE_CIRCLE_CSS
		elif isw==4: cssclass=FOUR_CIRCLE_CSS
		cssclass2=getshadow_circle_css(cssclass)
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
			flatshape.printsvg(output,cssfull=BACK_TRIPEL_CSS)
#		print_rectangle_svg(output,int(insetshift.xoff),int(insetshift.yoff+insetheight*0.025),insetwidth,int(insetheight*0.7),'#000000',0.3)

		if True:
			land=Shp(installfile=install.getinstallfile('land.shp',['110m']))
			land.loadshapes()
			for one in land.shapes:
				one_inset_tripel_print_svg(output,land,one,0,insetwidth,insetheight,None,LAND_TRIPEL_CSS,None,insetshift)

		for one in full_admin0.shapes: # highlights
			one_inset_tripel_print_svg(output,full_admin0,one,2,insetwidth,insetheight,None,HIGH_LAND_TRIPEL_CSS,PATCH_HIGH_LAND_TRIPEL_CSS,insetshift)

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
		if options['istopinsets']:
			yoff=0
			xmargin=0
			ymargin=0
			print_rectangle_svg(output,xoff-cutmargin-3,0,zwidth+cutmargin+3,zheight+cutmargin+3,'#ffffff',1.0)
			print_rectangle_svg(output,xoff-cutmargin,3,zwidth+2,zheight+2,'#000000',1.0)
			print_rectangle_svg(output,xoff-margin,margin,zwidth,zheight,'#70add3',1.0)
		else:
			yoff=height-zheight
			xmargin=0
			ymargin=0
			print_rectangle_svg(output,xoff-cutmargin-3,yoff-cutmargin-3,zwidth+cutmargin+3,zheight+cutmargin+3,'#ffffff',1.0)
			print_rectangle_svg(output,xoff-cutmargin,yoff-cutmargin,zwidth+2,zheight+2,'#000000',1.0)
			print_rectangle_svg(output,xoff-margin,yoff-margin,zwidth,zheight,'#70add3',1.0)

		scale=options['zoom']
		boxd=coeff/scale
		zoomshift=Shift(xoff-xmargin,yoff-ymargin)
		bzc=BoxZoomCleave(boxd,boxd,zwidth,zheight,splitlimit,zoomshift)
		if zoom_index!=-1:
			for partindex in zoom_partindices:
				zoom_admin0.setdraworder(zoom_index,partindex,2)

		pluses=zoom_wc.getpluses(isnegatives=False,isoverlaps=False)
		negatives=zoom_wc.getnegatives()

		pluses_sphere_print_svg(output,pluses,rotation2,width,height,splitlimit,
				boxzoomcleave=bzc, cssfull=LAND_ZOOM_CSS,csspatch=PATCH_LAND_ZOOM_CSS)
		for one in zoom_admin0.shapes:
				one_sphere_print_svg(output,one,0,rotation2,width,height,splitlimit,
						boxzoomcleave=bzc, cssfull=LAND_ZOOM_CSS,csspatch=PATCH_LAND_ZOOM_CSS)
		pluses_sphere_print_svg(output,negatives,rotation2,width,height,splitlimit,
				boxzoomcleave=bzc, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS)

		for one in full_admin0.shapes: # highlights
			one_sphere_print_svg(output,one,2,rotation2,width,height,splitlimit,cssfull=HIGH_LAND_ZOOM_CSS,csspatch=PATCH_HIGH_LAND_ZOOM_CSS,
					cssforcepixel=HIGH_LAND_ZOOM_CSS, boxzoomcleave=bzc)

		if options['iszoomlakes']:
			if isverbose_global: print('Drawing zoom lakes',file=sys.stderr)
			pluses=zoom_admin0.getlakes()
			pluses_sphere_print_svg(output,pluses,rotation2,width,height,splitlimit, cssfull=WATER_ZOOM_CSS,csspatch=PATCH_WATER_ZOOM_CSS,boxzoomcleave=bzc)

		pluses=zoom_wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation2,width,height,splitlimit, cssline=BORDER_ZOOM_CSS,boxzoomcleave=bzc)

		if zoom_borderlakeshapes:
			for plus in zoom_borderlakeshapes:
				if plus.type!=POLYLINE_TYPE_SHP: continue
				oneplus_sphere_print_svg(output,plus,rotation2,width,height,splitlimit,cssline=HIGH_LAKELINE_ZOOM_CSS,boxzoomcleave=bzc)

		if options['isdisputed']:
			for one in zoom_admin0.disputed.shapes:
				one_sphere_print_svg(output,one,1,rotation2,width,height,splitlimit,cssfull=DISPUTED_LAND_ZOOM_CSS,csspatch=PATCH_DISPUTED_LAND_ZOOM_CSS,
						cssforcepixel=options['zoomdisputedcssforce'], boxzoomcleave=bzc)
			for one in zoom_admin0.disputed.shapes:
				one_sphere_print_svg(output,one,2,rotation2,width,height,splitlimit,cssfull=DISPUTED_BORDER_ZOOM_CSS,csspatch=PATCH_DISPUTED_LAND_ZOOM_CSS,
						cssforcepixel=options['zoomdisputedbordercssforce'], boxzoomcleave=bzc)


		if 'zoomdots' in options: # [ (r0,isw0,[partindex00,partindex01]), ... , (rn,iswn,[partindexn0..partindexnm]) ]
			for zoomdots in options['zoomdots']:
				shape=full_admin0.shapes[full_index]
				sds=int((zoomdots[0]*width)/1000)
				isw=zoomdots[1]
				dots=zoomdots[2]
				cssclass=ONE_CIRCLE_CSS
				if isinstance(isw,bool) and isw: cssclass=FOUR_CIRCLE_CSS
				elif isw==1: cssclass=ONE_CIRCLE_CSS
				elif isw==2: cssclass=TWO_CIRCLE_CSS
				elif isw==3: cssclass=THREE_CIRCLE_CSS
				elif isw==4: cssclass=FOUR_CIRCLE_CSS
				cssclass2=getshadow_circle_css(cssclass)
				print_zoomdots_svg(output,shape,dots,sds,cssclass,cssclass2,rotation2,width,height,bzc)

	if labels:
		labels.printsvg(output,rotation,width,height,None)

	print_footer_svg(output)
	if True:
		o=Output()
		ishypso=True if options['hypso'] else False
		print_header_svg(o,width,height,output.csscounts,options['labelfont'],[options['copyright'],options['comment']],isgradients=True,
				ishypso=ishypso)
		output.prepend(o)

class FieldDbf():
	def __init__(self,buff32,offset):
		for i in range(12):
			if buff32[i]==0: break
		self.name=buff32[0:i].decode() # utf8 is fine
		self.type=buff32[11]
		self.length=buff32[16]
		self.offset=offset

class Dbf():
	def __init__(self,filename=None,installfile=None):
		self.installfile=installfile
		if installfile:
			self.filename=installfile.filename
			self.f=installfile.open()
		else:
			self.filename=filename
			self.f=open(filename,"rb")
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
		if f.type!=67 and f.type!=78: raise ValueError # C=67 N=78
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
				onerecord[sf]=recorddata[f.offset:f.offset+f.length].decode().rstrip(' \t\x00\ufeff').lstrip(' \t\ufeff')
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
	def open(self):
#		print('Install.open(%s)'%self.filename,file=sys.stderr)
		if not self.isfound: raise ValueError
		if not self.filename.endswith('zip'): return open(self.filename,'rb')
		if not zipfile:
			print('%s was found only as a zip file, but zipfile module isn\'t loaded'%self.filename,file=sys.stderr)
			raise ValueError
		zf=zipfile.ZipFile(self.filename)
		namelist=zf.namelist()
		for fn in self.filenames:
			if fn not in namelist: continue
			return zf.open(fn)
		print('Couldn\'t find',self.filenames,'in',namelist,file=sys.stderr)
		raise ValueError

class Install():
	def __init__(self):
		self.filenames_10m={}
		self.filenames_50m={}
		self.filenames_110m={}
		self.addfile('admin0-lakes.shp','10m','admin', ['ne_10m_admin_0_countries_lakes.shp','ne_10m_admin_0_countries_lakes.zip'])
		self.addfile('admin0-lakes.shp','50m','admin', ['ne_50m_admin_0_countries_lakes.shp','ne_50m_admin_0_countries_lakes.zip'])
		self.addfile('admin0-lakes.shp','110m','admin', ['ne_110m_admin_0_countries_lakes.shp','ne_110m_admin_0_countries_lakes.zip'])

		self.addfile('admin0-nolakes.shp','10m','admin', ['ne_10m_admin_0_countries.shp', 'ne_10m_admin_0_countries.zip'])
		self.addfile('admin0-nolakes.shp','50m','admin', ['ne_50m_admin_0_countries.shp', 'ne_50m_admin_0_countries.zip'])
		self.addfile('admin0-nolakes.shp','110m','admin', ['ne_110m_admin_0_countries.shp', 'ne_110m_admin_0_countries.zip'])

		self.addfile('admin0-lakes.dbf','10m','admin', ['ne_10m_admin_0_countries_lakes.dbf','ne_10m_admin_0_countries_lakes.zip'])
		self.addfile('admin0-lakes.dbf','50m','admin', ['ne_50m_admin_0_countries_lakes.dbf','ne_50m_admin_0_countries_lakes.zip'])
		self.addfile('admin0-lakes.dbf','110m','admin', ['ne_110m_admin_0_countries_lakes.dbf','ne_110m_admin_0_countries_lakes.zip'])

		self.addfile('admin0-nolakes.dbf','10m','admin', ['ne_10m_admin_0_countries.dbf','ne_10m_admin_0_countries.zip'])
		self.addfile('admin0-nolakes.dbf','50m','admin', ['ne_50m_admin_0_countries.dbf','ne_50m_admin_0_countries.zip'])
		self.addfile('admin0-nolakes.dbf','110m','admin', ['ne_110m_admin_0_countries.dbf','ne_110m_admin_0_countries.zip'])

		self.addfile('admin1-lakes.shp','10m','admin', ['ne_10m_admin_1_states_provinces_lakes.shp','ne_10m_admin_1_states_provinces_lakes.zip'])
		self.addfile('admin1-lakes.shp','50m','admin', ['ne_50m_admin_1_states_provinces_lakes.shp','ne_50m_admin_1_states_provinces_lakes.zip'])
		self.addfile('admin1-lakes.shp','110m','admin', ['ne_110m_admin_1_states_provinces_lakes.shp','ne_110m_admin_1_states_provinces_lakes.zip'])

		self.addfile('admin1-nolakes.shp','10m','admin', ['ne_10m_admin_1_states_provinces.shp','ne_10m_admin_1_states_provinces.zip'])
		self.addfile('admin1-nolakes.shp','50m','admin', ['ne_50m_admin_1_states_provinces.shp','ne_50m_admin_1_states_provinces.zip'])
		self.addfile('admin1-nolakes.shp','110m','admin', ['ne_110m_admin_1_states_provinces.shp','ne_110m_admin_1_states_provinces.zip'])

		self.addfile('admin1-lakes.dbf','10m','admin', ['ne_10m_admin_1_states_provinces_lakes.dbf','ne_10m_admin_1_states_provinces_lakes.zip'])
		self.addfile('admin1-lakes.dbf','50m','admin', ['ne_50m_admin_1_states_provinces_lakes.dbf','ne_50m_admin_1_states_provinces_lakes.zip'])
		self.addfile('admin1-lakes.dbf','110m','admin', ['ne_110m_admin_1_states_provinces_lakes.dbf','ne_110m_admin_1_states_provinces_lakes.zip'])

		self.addfile('admin1-nolakes.dbf','10m','admin', ['ne_10m_admin_1_states_provinces.dbf','ne_10m_admin_1_states_provinces.zip'])
		self.addfile('admin1-nolakes.dbf','50m','admin', ['ne_50m_admin_1_states_provinces.dbf','ne_50m_admin_1_states_provinces.zip'])
		self.addfile('admin1-nolakes.dbf','110m','admin', ['ne_110m_admin_1_states_provinces.dbf','ne_110m_admin_1_states_provinces.zip'])

		self.addfile('admin1-lines.shp','10m','admin', ['ne_10m_admin_1_states_provinces_lines.shp','ne_10m_admin_1_states_provinces_lines.zip'])
		self.addfile('admin1-lines.shp','50m','admin', ['ne_50m_admin_1_states_provinces_lines.shp','ne_50m_admin_1_states_provinces_lines.zip'])
		self.addfile('admin1-lines.shp','110m','admin', ['ne_110m_admin_1_states_provinces_lines.shp','ne_110m_admin_1_states_provinces_lines.zip'])

		self.addfile('admin1-lines.dbf','10m','admin', ['ne_10m_admin_1_states_provinces_lines.dbf','ne_10m_admin_1_states_provinces_lines.zip'])
		self.addfile('admin1-lines.dbf','50m','admin', ['ne_50m_admin_1_states_provinces_lines.dbf','ne_50m_admin_1_states_provinces_lines.zip'])
		self.addfile('admin1-lines.dbf','110m','admin', ['ne_110m_admin_1_states_provinces_lines.dbf','ne_110m_admin_1_states_provinces_lines.zip'])

		self.addfile('lakes.shp','10m','lakes', [ 'ne_10m_lakes.shp','ne_10m_lakes.zip' ])
		self.addfile('lakes.shp','50m','lakes', [ 'ne_50m_lakes.shp','ne_50m_lakes.zip' ])
		self.addfile('lakes.shp','110m','lakes', [ 'ne_110m_lakes.shp','ne_110m_lakes.zip' ])

		self.addfile('lakes.dbf','10m','lakes', [ 'ne_10m_lakes.dbf','ne_10m_lakes.zip' ])
		self.addfile('lakes.dbf','50m','lakes', [ 'ne_50m_lakes.dbf','ne_50m_lakes.zip' ])
		self.addfile('lakes.dbf','110m','lakes', [ 'ne_110m_lakes.dbf','ne_110m_lakes.zip' ])

		self.addfile('ocean.shp','10m','ocean', [ 'ne_10m_ocean.shp','ne_10m_ocean.zip' ])
		self.addfile('ocean.shp','50m','ocean', [ 'ne_50m_ocean.shp' ,'ne_50m_ocean.zip'])
		self.addfile('ocean.shp','110m','ocean', [ 'ne_110m_ocean.shp' ,'ne_110m_ocean.zip'])

		self.addfile('coast.shp','10m','coast', [ 'ne_10m_coastline.shp','ne_10m_coastline.zip' ])
		self.addfile('coast.shp','50m','coast', [ 'ne_50m_coastline.shp' ,'ne_50m_coastline.zip'])
		self.addfile('coast.shp','110m','coast', [ 'ne_110m_coastline.shp' ,'ne_110m_coastline.zip'])

		self.addfile('land.shp','10m','land', [ 'ne_10m_land.shp','ne_10m_land.zip' ])
		self.addfile('land.shp','50m','land', [ 'ne_50m_land.shp' ,'ne_50m_land.zip'])
		self.addfile('land.shp','110m','land', [ 'ne_110m_land.shp' ,'ne_110m_land.zip'])

		self.addfile('admin0-disputed.shp','10m','admin', [ 'ne_10m_admin_0_disputed_areas.shp','ne_10m_admin_0_disputed_areas.zip' ])
		self.addfile('admin0-disputed.shp','50m','admin', [ 'ne_50m_admin_0_breakaway_disputed_areas.shp',
				'ne_50m_admin_0_breakaway_disputed_areas.zip' ])
		self.addfile('admin0-disputed.shp','110m','admin', [ 'ne_110m_admin_0_breakaway_disputed_areas.shp',
				'ne_110m_admin_0_breakaway_disputed_areas.zip' ])

		self.addfile('admin0-disputed.dbf','10m','admin', [ 'ne_10m_admin_0_disputed_areas.dbf','ne_10m_admin_0_disputed_areas.zip' ])
		self.addfile('admin0-disputed.dbf','50m','admin', [ 'ne_50m_admin_0_breakaway_disputed_areas.dbf',
				'ne_50m_admin_0_breakaway_disputed_areas.zip' ])
		self.addfile('admin0-disputed.dbf','110m','admin', [ 'ne_110m_admin_0_breakaway_disputed_areas.dbf',
				'ne_110m_admin_0_breakaway_disputed_areas.zip' ])

		self.addfile('populated_places.dbf','10m','cultural',[ 'ne_10m_populated_places.dbf', 'ne_10m_populated_places_simple.dbf',
				'ne_10m_populated_places.zip', 'ne_10m_populated_places_simple.zip' ])

		self.addfile('hypso-sr_w.pnm','50m','hypso', [ 'hyp_50m_sr_w.pnm','hyp_50m_sr_w.zip' ])
		self.addfile('hypso-lr_sr_ob_dr.pnm','10m','hypso', [ 'hyp_lr_sr_ob_dr.pnm','hyp_lr_sr_ob_dr.zip',
				'hyp_hr_sr_ob_dr.pnm','hyp_hr_sr_ob_dr.zip' ]) # hr can fill in for lr
		self.addfile('hypso-hr_sr_ob_dr.pnm','10m','hypso', [ 'hyp_hr_sr_ob_dr.pnm','hyp_hr_sr_ob_dr.zip' ])


	def addfile(self,nickname,scale,dclass,filenames):
		f=InstallFile(nickname,scale,dclass,filenames)
		f.findfile()
		if scale=='10m': self.filenames_10m[nickname]=f
		elif scale=='50m': self.filenames_50m[nickname]=f
		elif scale=='110m': self.filenames_110m[nickname]=f
		else: raise ValueError

	def getinstallfile(self,nicknames,scales=None,failok=False):
		if not isinstance(nicknames,list):
			if nicknames=='admin0.shp': return self.getinstallfile(['admin0-lakes.shp','admin0-nolakes.shp'],scales,failok)
			if nicknames=='admin1.shp': return self.getinstallfile(['admin1-lakes.shp','admin1-nolakes.shp'],scales,failok)
			if nicknames=='admin0.dbf': return self.getinstallfile(['admin0-lakes.dbf','admin0-nolakes.dbf'],scales,failok)
			if nicknames=='admin1.dbf': return self.getinstallfile(['admin1-lakes.dbf','admin1-nolakes.dbf'],scales,failok)
			return self.getinstallfile([nicknames],scales,failok)
		if scales==None: scales=['10m','50m','110m']
		for nickname in nicknames:
			for scale in scales:
				if scale=='10m': f=self.filenames_10m.get(nickname,None)
				elif scale=='50m': f=self.filenames_50m.get(nickname,None)
				elif scale=='110m': f=self.filenames_110m.get(nickname,None)
				else: raise ValueError("Unsupported scale: "+str(scale))
				if f and f.isfound: return f
		if not failok: raise ValueError("Couldn't find base file for %s (%s)"%(nicknames,str(scales)))
		return None
	def getfilename(self,nickname,scales=None):
		f=self.getinstallfile(nickname,scales)
		if not f: raise ValueError("Couldn't find base file for %s (%s)"%(nickname,str(scales)))
		return f.filename
	def print(self,n=None,scales=None):
		if n:
			if scales==None: scales=['10m','50m','110m']
			isfound=False
			for scale in scales:
				f=self.getinstallfile(n,[scale],failok=True)
				if f and f.isfound:
					isfound=True
					print('Found file %s (%s) -> %s'%(n,f.scale,f.filename),file=sys.stdout)
			if not isfound: print('File not found: %s -> ?'%n,file=sys.stdout)
			return
		self.print('admin0-lakes.shp')
		self.print('admin0-nolakes.shp')
		self.print('admin0.dbf')
		self.print('admin0-disputed.shp')
		self.print('admin0-disputed.dbf')
		self.print('admin1-lakes.shp')
		self.print('admin1-nolakes.shp')
		self.print('admin1.dbf')
		self.print('admin1-lines.shp')
		self.print('admin1-lines.dbf')
		self.print('lakes.shp')
		self.print('lakes.dbf')
		self.print('coast.shp')
		self.print('ocean.shp')
		self.print('land.shp')
		self.print('populated_places.dbf')
		self.print('hypso-sr_w.pnm')
		self.print('hypso-lr_sr_ob_dr.pnm')
		self.print('hypso-hr_sr_ob_dr.pnm')
	def printlog(self):
		for d in [self.filenames_10m,self.filenames_50m,self.filenames_110m]:
			for n in d:
				f=d[n]
				for l in f.log: print(l,file=sys.stdout)


# isverbose_global=True
install=Install()

def admin0dbf_test(): # admin0 test
	scale='10m'
	scale='50m'
	admin0dbf=Dbf(installfile=install.getinstallfile('admin0-nolakes.dbf',[scale]))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.selectcfield('NAME','name')
	admin0dbf.print()
	admin0dbf.loadrecords()
	for i in range(len(admin0dbf.records)):
		print(i,': ',admin0dbf.records[i])

def russiafix_test(): # test merging russia's -180deg tail to her 180deg main
	scale='50m'
	scale='10m'

	admin=ShpAdmin('admin0-nolakes.shp',[scale])
	rus=admin.bynickname['RUS.RUS']
	print('Before fix')
	rus.print()
	if True:
		print('During fix')
		admin.fixrussia(isdebug=True)
		print('After fix')
		rus.print()

def lakesdbf_test(): # lakes test
	scale='50m'
	bynickname={}
	lakesdbf=Dbf(installfile=install.getinstallfile('lakes.dbf',[scale]))
	lakesdbf.selectcfield('name','name')
	lakesdbf.loadrecords()
	if True:
		lakesdbf.print()
		for i in range(len(lakesdbf.records)):
			print(i,': ',lakesdbf.records[i])

	lakesshp=Shp(installfile=install.getinstallfile('lakes.shp',[scale]))
	lakesshp.loadshapes()

	for i in range(len(lakesdbf.records)):
		nickname=lakesdbf.records[i]['name']
		bynickname[nickname]=lakesshp.shapes[i]

	l=bynickname['Lake Michigan']
	mbr=l.getmbr(-1)
	print('Lake Michigan: %s'%str(mbr))

	for i in range(len(lakesdbf.records)):
		l=lakesshp.shapes[i]
		mbr=l.getmbr(-1)
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
		l=admin0.lakes.bynickname[n]
		sasi.setinside(l)

	exportpluses=sasi.exportlines()

	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	rotation.set_deglonlat(-84,23)
	print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,BORDER_SPHERE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,'debugl',FOUR_CIRCLE_CSS],isgradients=True)
	print_roundwater_svg(output,width)

	one_sphere_print_svg(output,admin0.bynickname['US1.USA'],-1,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)
	one_sphere_print_svg(output,admin0.bynickname['CAN.CAN'],-1,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)

	lakepluses=admin0.getlakes()
	pluses_sphere_print_svg(output,lakepluses,rotation,width,height,8, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS)

	for plus in exportpluses:
		if plus.type!=POLYLINE_TYPE_SHP: continue
		oneplus_sphere_print_svg(output,plus,rotation,width,height,8,cssline='debugl')

	if False:
		dll=DegLonLat(-95,49)
		dll_sphere_print_svg(output,dll,rotation,width,height,FOUR_CIRCLE_CSS)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def disputeddbf_test(): # disputed admin0 test
	scale='50m'
	scale='10m'
	dbf=Dbf(installfile=install.getinstallfile('admin0-disputed.dbf',[scale]))
	dbf.selectcfield('BRK_NAME','name')
	dbf.selectcfield('SOV_A3','sov3')
	dbf.selectcfield('ADM0_A3','adm3')
	dbf.loadrecords()
	for i in range(len(dbf.records)):
		r=dbf.records[i]
		print("%d:\t\"%s.%s.%s\""%(i, r['sov3'], r['adm3'], r['name']))

def admin1dbf_test(): # admin1 test
	admin1dbf=Dbf(installfile=install.getinstallfile('admin1-nolakes.dbf'))
	admin1dbf.print()
	admin1dbf.selectcfield('sov_a3','sov3')
	admin1dbf.selectcfield('adm0_a3','adm3')
	admin1dbf.selectcfield('name','name')
	admin1dbf.selectcfield('type_en','type')
	admin1dbf.loadrecords()
	for i in range(len(admin1dbf.records)):
		r=admin1dbf.records[i]
		print("%d:\t%s\t%s.%s\t%s"%(i,r['type'],r['sov3'],r['adm3'],r['name']))

def admin1linesdbf_test():
	admin1dbf=Dbf(installfile=install.getinstallfile('admin1-lines.dbf'))
	admin1dbf.print()
	admin1dbf.selectcfield('SOV_A3','sov3')
	admin1dbf.selectcfield('ADM0_A3','adm3')
	admin1dbf.selectcfield('NAME','name')
	admin1dbf.loadrecords()
	for i in range(len(admin1dbf.records)):
		r=admin1dbf.records[i]
		print("%d:\t%s.%s.%s"%(i,r['sov3'],r['adm3'],r['name']))

def populateddbf_test(): # populated_places test
	dbf=Dbf(installfile=install.getinstallfile('populated_places.dbf'))
	dbf.print()
	dbf.selectcfield('adm0_a3','sg')
	dbf.selectcfield('adm0name','admin0name')
	dbf.selectcfield('adm1name','admin1name')
	dbf.selectcfield('name','name')
	dbf.selectcfield('longitude','lon')
	dbf.selectcfield('latitude','lat')
	dbf.selectcfield('pop_max','pop')
	dbf.selectcfield('featurecla','feature')
	dbf.loadrecords()
	for i,r in enumerate(dbf.records):
#		print("%d:\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(i,r['sg'],r['admin0name'],r['admin1name'],r['name'],r['lon'],r['lat'],r['pop']))
		label=Options.collapsename(r['sg'])+'.'+Options.collapsename(r['admin1name'])+'.'+Options.collapsename(r['name'])
		print("%d:\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(i,label,r['admin0name'],r['name'],r['lon'],r['lat'],r['feature'],r['pop']))


def webmercator_test(): # webmercator test
	output=Output()
	admin0=Shp(installfile=install.getinstallfile('admin0.shp',['110m']))
	admin0.loadshapes()
	coast=Shp(installfile=install.getinstallfile('coast.shp'))
	coast.loadshapes()
	width=1000
	height=1000
	print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,COAST_TRIPEL_CSS])

	wmc=WebMercatorCleave(True)

	if True:
		for shape in admin0.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewm=WebMercatorShape(oneplus)
				wmc.cleave(onewm)
				if onewm.type!=NULL_TYPE_SHP:
					flatshape=onewm.flatten(width,height)
					flatshape.printsvg(output,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)
	if True:
		for shape in coast.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewm=WebMercatorShape(oneplus)
				wmc.cleave(onewm)
				if onewm.type!=NULL_TYPE_SHP:
					flatshape=onewm.flatten(width,height)
					flatshape.printsvg(output,cssline=COAST_TRIPEL_CSS)
	print_footer_svg(output)
	output.writeto(sys.stdout)

def ocean_test(): # ocean shp test
	output=Output()
	width=1630
	height=990
	print_header_svg(output,width,height,[BACK_TRIPEL_CSS,OCEAN_TRIPEL_CSS,GRID_TRIPEL_CSS,'debuggreen'])
#	print_rectangle_svg(output,0,0,width,height,'#5685a2',1.0)
	insetshift=Shift(5,5)
	insetwidth=1600
	insetheight=1600
	oneplus=ShapePlus.makeflatbox(True)
	onewt=TripelShape(oneplus)
	flatshape=onewt.flatten(insetwidth,insetheight)
	flatshape.shift(insetshift)
	flatshape.printsvg(output,cssfull=BACK_TRIPEL_CSS)
	if True:
		ocean=Shp(installfile=install.getinstallfile('ocean.shp'))
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
	output.writeto(sys.stdout)

def land_test(): # land shp test
	output=Output()
	width=1630
	height=990
	print_header_svg(output,width,height,[BACK_TRIPEL_CSS,OCEAN_TRIPEL_CSS,GRID_TRIPEL_CSS,'debuggreen'])
#	print_rectangle_svg(output,0,0,width,height,'#5685a2',1.0)
	insetshift=Shift(5,5)
	insetwidth=1600
	insetheight=1600

	land=Shp(installfile=install.getinstallfile('land.shp',['110m']))
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
	flatshape.printsvg(output,cssfull=BACK_TRIPEL_CSS)
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
	output.writeto(sys.stdout)

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
	def isin2(self,pmlonlat,qmlonlat):
		a=self.index.get(pmlonlat,None)
		if not a: return False
		if qmlonlat in a: return True
		return False
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
					'MNG.MNG','RUS.RUS','KA1.KAZ','NPL.NPL','BTN.BTN','IND.IND','PAK.PAK',
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
					'MNG.MNG','RUS.RUS','KA1.KAZ','NPL.NPL','BTN.BTN','IND.IND','PAK.PAK',
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
	def addnorthamerica(self,isusacan):
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
			set1=('CRI.CRI','NIC.NIC','HND.HND','GTM.GTM','BLZ.BLZ','SLV.SLV','MEX.MEX')
			self.startblob('PAN.PAN')
			for gsg in set1: self.addtoblob(gsg)
			if not isusacan:
				set2=('US1.USA','CAN.CAN','US1.USA')
				for gsg in set2: self.addtoblob(gsg)
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
	def addcontinents(self,label='',isusacan=False):
		if self.shp.installfile.scale=='10m':
			if isverbose_global: print('Not making worldcompress for 10m: %s'%label,file=sys.stderr)
			return
		if len(label): label+=' '
		if isverbose_global: print('Creating %sblobs: '%label,end='',file=sys.stderr,flush=True)
		if isverbose_global: print('Europe ',end='',file=sys.stderr,flush=True)
		self.addeurope()
		if isverbose_global: print('North America ',end='',file=sys.stderr,flush=True)
		self.addnorthamerica(isusacan)
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
	admin0.fixegypt()
	admin0.setccwtypes()
	admin0.loadlakes()

	rotation.set_deglonlat(60,20)

	wc=WorldCompress(admin0,-1)
	wc.addcontinents('worldcompress_test')

#	admin0.setdraworder(admin0.bynickname['NAM.NAM'].index,-1,2)
	wc.removeoverlaps(admin0.shapes,2)
#	admin0.setdraworder(admin0.bynickname['NAM.NAM'].index,-1,0)

	print_header_svg(output,width,height,[BORDER_SPHERE_CSS,LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl',HIGH_LAND_SPHERE_CSS,PATCH_HIGH_LAND_SPHERE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS],isgradients=True)

	pluses=wc.getpluses(isnegatives=False,isoverlaps=False)
	pluses_sphere_print_svg(output,pluses,rotation,width,height,4, cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)

	if False:
		negatives=wc.getnegatives()
		pluses_sphere_print_svg(output,negatives,rotation,width,height,4, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS)

	if False:
		pluses=admin0.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,4, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS)

	if False:
		pluses=wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,4, cssline=BORDER_SPHERE_CSS)

	if False:
		for one in admin0.shapes: one_sphere_print_svg(output,one,0,rotation,width,height,4,cssfull=HIGH_LAND_SPHERE_CSS,csspatch=PATCH_HIGH_LAND_SPHERE_CSS)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def png_test():
	if not zlib:
		print('zlib not found, this feature requires zlib')
		return
	(width,height)=(500,500)

	hypso=Hypso(width,height,'./hypsocache','')
	if not hypso.loadpng_cache():
		if not hypso.loadraw_cache():
			hs=HypsoSphere(install.getfilename('hypso-lr_sr_ob_dr.pnm',['10m']))
#			hs=HypsoSphere('ned/10m-hypso/hypso_ht_sr_ob_dr_6000_3000.pnm')
			hs.setcenter(-110,47)
#			hs.setzoom(.25,.25,.5,.5)
			hypso.loadsphere(hs)
			hypso.saveraw_cache(True)
		else:
#			hypso.removealpha()
			p=Palette()
			p.loaddefaults()
			print('Indexing colors',file=sys.stderr)
			hypso.indexcolors(p)
		hypso.savepng_cache(True)

	if False:
		print('Making png and writing to /tmp/out.png',file=sys.stderr)
		b=hypso.getpng(ismime=False)
		f=open('/tmp/out.png','wb')
		f.write(b)
		f.close()
	else:
		print('Making png and writing to /tmp/out.svg',file=sys.stderr)
		b=hypso.getpng(ismime=True)
		f=open('/tmp/out.svg','w')
		print('<?xml version="1.0" encoding="UTF-8" standalone="no"?>',file=f)
		print('<svg xmlns:svg="http://www.w3.org/2000/svg" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="%d" width="%d">' % (height,width),file=f)
		print('<image x="0" y="0" width="%d" height="%d" xlink:href="data:image/png;base64,'%(width,height),end='',file=f)
		f.write(b)
		print('" />',file=f)
		print('</svg>',file=f)
		f.close()

def ccw_test():
	ifile=install.getinstallfile('admin0.shp',['10m'])
	admin0=Shp(installfile=ifile)
	admin0.loadshapes()
	admin0dbf=Dbf(installfile=install.getinstallfile('admin0.dbf',['10m']))
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
	print_header_svg(output,width,height,[BACK_TRIPEL_CSS,OCEAN_TRIPEL_CSS,GRID_TRIPEL_CSS])
#	print_rectangle_svg(output,0,0,width,height,'#5685a2',1.0)
	insetshift=Shift(5,5)
	insetwidth=400
	insetheight=400
	oneplus=ShapePlus.makeflatbox(True)
	onewt=TripelShape(oneplus)
	flatshape=onewt.flatten(insetwidth,insetheight)
	flatshape.shift(insetshift)
	flatshape.printsvg(output,cssfull=BACK_TRIPEL_CSS)
	if True:
		ocean=Shp(installfile=install.getinstallfile('ocean.shp'))
		ocean.loadshapes()
		for shape in ocean.shapes:
			pluses=ShapePlus.make(shape)
			for oneplus in pluses:
				onewt=TripelShape(oneplus)
				if onewt.type!=NULL_TYPE_SHP:
					flatshape=onewt.flatten(insetwidth,insetheight)
					flatshape.shift(insetshift)
					flatshape.printsvg(output,cssfull=OCEAN_TRIPEL_CSS)
	tripel_lonlat_print_svg(output,insetwidth,insetheight,insetshift)
	if False:
		oneplus=ShapePlus.makeflatbox(False)
		onewt=TripelShape(oneplus)
		flatshape=onewt.flatten(insetwidth,insetheight)
		flatshape.shift(insetshift)
		flatshape.printsvg(output)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def zoom_test(): # zoom test
	output=Output()
	width=1000
	height=1000
	admin0=ShpAdmin('admin0-nolakes.shp',['50m'])
	index=admin0.bynickname['LAO.LAO'].index
	partindex=-1
	scale=2
	boxd=1/(2*scale)
	shift=Shift(int(width/4),int(height/4))
	bzc=BoxZoomCleave(boxd,boxd,int(width/2),int(height/2),4,shift)
	(lon,lat)=admin0.getcenter(index,[0])
	sr=SphereRotation()
	sr.set_deglonlat(lon,lat)
	print_header_svg(output,width,height,[LAND_ZOOM_CSS,'debugzp'])
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
				flatshape=bzc.flatten(onesphere)
				flatshape.printsvg(output,cssfull=LAND_ZOOM_CSS,csspatch='debugzp')
	print_footer_svg(output)
	output.writeto(sys.stdout)

def province_test(): # look at admin1 shapes, replaced with admin1_test
	output=Output()
	width=1000
	height=1000
	admin0=Shp(installfile=install.getinstallfile('admin0.shp',['10m']))
	admin0.loadshapes()
	admin1=Shp(installfile=install.getinstallfile('admin1.shp',['10m']))
	admin1.loadshapes()
	admin1dbf=Dbf(installfile=install.getinstallfile('admin1.dbf',['10m']))
	admin1dbf.selectcfield('sov_a3','sov3')
	admin1dbf.selectcfield('adm0_a3','adm3')
	admin1dbf.loadrecords()
	print_header_svg(output,width,height,[LAND_TRIPEL_CSS,PATCH_LAND_TRIPEL_CSS,'tl1','tp1'])
	wmc=WebMercatorCleave(False)
	for shape in admin0.shapes:
		pluses=ShapePlus.make(shape)
		for oneplus in pluses:
			onewm=WebMercatorShape(oneplus)
			wmc.cleave(onewm)
			if onewm.type!=NULL_TYPE_SHP:
				flatshape=onewm.flatten(width,height)
				flatshape.printsvg(output,cssfull=LAND_TRIPEL_CSS,csspatch=PATCH_LAND_TRIPEL_CSS)
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
	output.writeto(sys.stdout)

def admin0info_test():
	admin0=Shp(installfile=install.getinstallfile('admin0.shp',['10m']))
	admin0.printinfo()

def admin0parts_test():
	scales=['110m']
	scales=['50m']
	scales=['10m']

	gsgs=['RUS.RUS']
	gsgs=['TTO.TTO']
	gsgs=['ATA.ATA']
	gsgs=['CYP.CYP','CYN.CYN']
	gsgs=['EGY.EGY']

	sfi=install.getinstallfile('admin0-nolakes.shp',scales)
	print('shp filename: %s'%sfi.filename)
	admin0=Shp(installfile=sfi)
	admin0.loadshapes()
	dfi=install.getinstallfile('admin0-nolakes.dbf',[sfi.scale])
	print('dbf filename: %s'%dfi.filename)
	admin0dbf=Dbf(installfile=dfi)
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
			output.countcss(SHADOW_FONT_CSS)
			output.countcss(TEXT_FONT_CSS)
			output.print('<text x="0" y="0" class="fs" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux+xoff,fp1.uy+yoff,textangle,s))
			output.print('<text x="0" y="0" class="ft" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp1.ux+xoff,fp1.uy+yoff,textangle,s))
			xoff+=fontstep
	output.countcss(SHADOW_FONT_CSS)
	output.countcss(TEXT_FONT_CSS)
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
			output.countcss(SHADOW_FONT_CSS)
			output.countcss(TEXT_FONT_CSS)
			output.print('<text x="0" y="0" class="fs" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux+xoff,fp2.uy+yoff,textangle,s))
			output.print('<text x="0" y="0" class="ft" transform="translate(%d,%d) rotate(%u)">%s</text>'%(fp2.ux+xoff,fp2.uy+yoff,textangle,s))
			yoff+=fontstep
	else:
		output.countcss(SHADOW_FONT_CSS)
		output.countcss(TEXT_FONT_CSS)
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
	rotation.set_deglonlat(0,0) # some rotations will break on Antarctica w/o antarctica fix, see sphere2_test
	scale='50m'
	admin0=Shp(installfile=install.getinstallfile('admin0-nolakes.shp',[scale]))
#	admin0=Shp('ned/10m-admin/ne_10m_admin_1_states_provinces_lines.shp')
	admin0.loadshapes()

	print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl',FOUR_CIRCLE_CSS],isgradients=True)
	print_roundwater_svg(output,width)

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,cssline='debugl')

	dll=DegLonLat(0,0)
	dll_sphere_print_svg(output,dll,rotation,width,height,FOUR_CIRCLE_CSS)

	print_footer_svg(output)
	output.writeto(sys.stdout)

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
		elif self.type==NULL_TYPE_SHP:
			pass
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
	def print(self,prefix='',file=sys.stdout): return Shape.print(self,prefix=prefix,file=file)
	def getmbr(self,partindices): return Shape.getmbr(self,partindices)
	def getcenter(self,partindices): return Shape.getcenter(self,partindices)
	def setdraworder(self,partidx,draworder): return Shape.setdraworder(self,partidx,draworder)
	def hasdraworder(self,draworder): return Shape.hasdraworder(self,draworder)
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
	def fixrussia(self,partindex,tailpartindex,istrimhead=False,istrimtail=False,isfix10mpoint=False,isdebug=False):
		tailpoints=self.extractpart(tailpartindex)
		tailpg=Polygon.makefrompoints(tailpoints,True,self.index,tailpartindex)
		tailminus=WorldMinus(tailpg,nickname='Russia tail')
		fixcount=0

		i=0
		while i<len(tailminus.points):
			p=tailminus.points[i]
			if p.mlonlat[0]<=-1799999000:
				fixcount+=1
				if isfix10mpoint:
					if p.mlonlat[1]==689823698:
						p.mlonlat=(0,689810503)
						if isdebug: print('Found 10mpoint')
				if istrimtail:
# 50m nolakes: Deleting point from tail: (-180.000000,65.311963) .. (-180.000000,68.738672)
					if p.mlonlat[1] > 650672363 and p.mlonlat[1] < 689834472:
						if isdebug: print('Deleting point from tail: %s'%tailminus.points[i].dll)
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
						if isdebug: print('Deleting point from head: %s'%tailminus.points[i].dll)
						del mainminus.points[i]
						continue
				i+=1

		if isverbose_global and fixcount: print('Fixed %d points in fixrussia'%fixcount,file=sys.stderr)

		blob=WorldBlob(mainminus)
		if not blob.addtoblob_minus(tailminus): raise ValueError
		points=[]
		for p in blob.blob.points:
			points.append(p.dll)
		self.replacepart(partindex,points)
		self.replacepart(tailpartindex,[])
	@staticmethod
	def findpointsmatch(haystack,needle):
		lh=len(haystack)
		for i,_ in enumerate(haystack):
			for j,n in enumerate(needle):
				p=haystack[(i+j)%lh]
				if abs(p.lon-n[0])>0.000001 or abs(p.lat-n[1])>0.000001: break
			else:
				return i
		return -1
	def fixegypt(self,partindex):
		points=self.extractpart(partindex)
		cut=( ( 35.429207016000,22.978330157000 ), ( 35.212087686000,22.786263058000 ), ( 35.345755761060,22.901639312789 ),
				( 35.486665384665,23.023266145732 ), ( 35.621087106000,23.139292914000 ) )
		i=ShpAdminShape.findpointsmatch(points,cut)
		if i<0: raise ValueError
		del points[i:i+len(cut)] # this doesn't handle wrap-around cases
		self.replacepart(partindex,points)
		if isverbose_global: print('Fixed %d points in fixegypt'%len(cut),file=sys.stderr)

class ShpAdminShapeIntersection():
	def __init__(self):
		self.pointslist=[]
		self.mbr=Mbr()
	def addpolygon(self,pg):
		if not pg.iscw: return # all polygons are CW
		points=[]
		for p in pg.points:
			self.mbr.add(p.lon,p.lat)
			points.append(p.clone())
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
		if not self.mbr.isset: return
		mbr=shape.mbr
		if not self.mbr.isintersects(mbr): return
		pluses=ShapePlus.make(shape)
#		mbr=shape.getmbr([-1])
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

class ShpAdminPart():
	def __init__(self,filenickname,scales):
		self.filename=filenickname
		self.installfile=install.getinstallfile(filenickname,scales)
		if not self.installfile:
			print('Couldn\'t find %s file (%s)'%(filenickname,str(scales)),file=sys.stderr)
			raise ValueError
		self.scale=self.installfile.scale
		self.shp=Shp(installfile=self.installfile)
		if isverbose_global: print('Loading %s shape data (%s)'%(filenickname,self.scale),file=sys.stderr)
		self.shp.loadshapes()
		self.shapes=[]
		self.bynickname={}
		self.dbfname=self.installfile.nickname[:-3]+'dbf'
		self.dbf=Dbf(installfile=install.getinstallfile(self.dbfname,[self.scale]))
	def bynickname2(self,nick):
		for s in self.shapes:
			if s.nickname.startswith(nick): return s
		return None
	def addshape(self,shape,nickname):
		sas=ShpAdminShape(shape,nickname)
		if nickname:
#			if nickname in self.bynickname: print('Duplicate nickname:',nickname,file=sys.stderr)
			self.bynickname[nickname]=sas
		self.shapes.append(sas)
	def loadnicktrips(self,nicktrips):
		for np in nicktrips:
			sas=self.shapes[np[0]]
			if np[2] and np[2]!=sas.nickname:
				print('Skipping dbf rename (mismatch): %s!=%s'%(np,sas.nickname),file=sys.stderr)
				continue
			sas.nickname=np[1]
			self.bynickname[np[1]]=sas
	def loaddbf(self,fields):
		for f in fields: self.dbf.selectcfield(f[0],f[1])
		self.dbf.loadrecords()
		for i in range(self.dbf.numrecords):
			r=self.dbf.records[i]
			vals=[]
			for f in fields: vals.append(r[f[1]])
			nickname='.'.join(vals)
			self.addshape(self.shp.shapes[i],nickname)
	def loadadmin0dbf(self):
		if isverbose_global: print('Loading admin0 data (%s,%s)'%(self.dbfname,self.scale),file=sys.stderr)
		self.loaddbf( ( ('SOV_A3','sov3') , ('ADM0_A3','adm3') ) )
	def loadlakesdbf(self):
		if isverbose_global: print('Loading lakes data (%s,%s)'%(self.dbfname,self.scale),file=sys.stderr)
		self.loaddbf( ( ('name','name'), ) )
		nicktrips=[]
		if self.scale=='50m':
			if self.dbf.numrecords==275:
				nicktrips=((266,'_deadseasouth',None),) # this was for version 4.1
			elif self.dbf.numrecords==412:
				nicktrips=((264,'_deadseasouth','Dead Sea'),) # for version 5.0
			else:
				print('Unrecognized lakes, %d records at scale %s'%(self.dbf.numrecords,self.scale),file=sys.stderr)
		self.loadnicktrips(nicktrips)
	def loaddisputeddbf(self):
		if isverbose_global: print('Loading disputed dbf data (%s,%s)'%(self.dbfname,self.scale),file=sys.stderr)
		self.loaddbf( ( ('SOV_A3','sov3'), ('ADM0_A3','adm3'), ('BRK_NAME','name') ) )
	def loadadmin1dbf(self):
		if isverbose_global: print('Loading admin1 dbf data (%s,%s)'%(self.dbfname,self.scale),file=sys.stderr)
		self.loaddbf( ( ('sov_a3','sov3'), ('adm0_a3','adm3'), ('name','name'),('type_en','type') ) )
	def loadadmin1linesdbf(self):
		if isverbose_global: print('Loading admin1 lines data (%s,%s)'%(self.dbfname,self.scale),file=sys.stderr)
		self.loaddbf( ( ('SOV_A3','sov3'), ('ADM0_A3','adm3'), ('NAME','name') ) )

class ShpAdminLines():
	def __init__(self,shapes,prefix):
		self.lines=[]
		self.minus=None
		self.isreduced=False
		self.skipped=0
		for shape in shapes:
			if shape.type!=POLYLINE_TYPE_SHP: continue
			if not shape.nickname.startswith(prefix): continue
			for i in range(shape.partscount):
				j=shape.partlist[i+1] if i+1!=shape.partscount else shape.pointscount
				self.lines.append(shape.pointlist[shape.partlist[i]:j])
		if isverbose_global: print('Added %d lines'%(len(self.lines)),file=sys.stderr)
	def addpolygons(self,shapes,draworder):
		if not self.minus:
			self.minus=WorldMinus(None)
			self.minus.buildindex()
		for shape in shapes:
			for i in range(len(shape.draworderlist)):
				if draworder!=None and shape.draworderlist[i]!=draworder: continue
				start=shape.partlist[i]
				limit=shape.partlist[i+1] if i+1!=shape.partscount else shape.pointscount
				mpoints=[]
				for j in range(start,limit):
					p=shape.pointlist[j]
					mpoints.append(MinusPoint(p,shape.index))
				self.minus.addtoindex2(mpoints)
	def reducelines(self):
		self.isreduced=True
		if not self.minus: return
		lines=self.lines
		self.lines=[]
		for line in lines:
			points=[]
			for i in range(len(line)-1):
				p=line[i]
				q=line[i+1]
				pmlonlat=MinusPoint.getmlonlat(p)
				qmlonlat=MinusPoint.getmlonlat(q)
				if self.minus.isin2(pmlonlat,qmlonlat) or self.minus.isin2(qmlonlat,pmlonlat):
					self.skipped+=1
					if len(points):
						points.append(p)
						self.lines.append(points)
						points=[]
				else:
					if not len(points): points.append(p)
					points.append(q)
			if len(points): self.lines.append(points)
	def exportlines(self):
		if not self.isreduced: self.reducelines()
		if isverbose_global: print('Removed %d line segments'%self.skipped,file=sys.stderr)
		ret=[]
		for line in self.lines:
			ret.append(ShapePlus.makelinefrompoints(line,0,0,0))
		return ret
		

class ShpAdmin():
	def __init__(self,filename,scales):
		self.admin0=ShpAdminPart(filename,scales)
		self.admin0.loadadmin0dbf()
		self.scale=self.admin0.scale
		self.installfile=self.admin0.installfile
		self.shapes=self.admin0.shapes
		self.bynickname=self.admin0.bynickname
		self.islakesloaded=False
		self.isdisputedloaded=False
		self.isadmin1loaded=False
		self.isadmin1linesloaded=False
	def loadlakes(self):
		if self.islakesloaded: return
		self.lakes=ShpAdminPart('lakes.shp',[self.scale])
		self.lakes.loadlakesdbf()
		self.islakesloaded=True
	def loaddisputed(self,is10m=True):
		scale=self.scale
		if is10m: scale='10m'
		if self.isdisputedloaded: return
		self.disputed=ShpAdminPart('admin0-disputed.shp',[scale])
		self.disputed.loaddisputeddbf()
		self.isdisputedloaded=True
	def loadadmin1(self):
		if self.isadmin1loaded: return
		self.admin1=ShpAdminPart('admin1-nolakes.shp',[self.scale])
		self.admin1.loadadmin1dbf()
		self.isadmin1loaded=True
	def loadadmin1lines(self):
		if self.isadmin1linesloaded: return
		self.admin1lines=ShpAdminPart('admin1-lines.shp',[self.scale])
		self.admin1lines.loadadmin1linesdbf()
		self.isadmin1linesloaded=True
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
				canada=self.admin0.bynickname['CAN.CAN']
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
	def fixrussia(self,isdebug=False):
		rus=self.bynickname['RUS.RUS']
		if self.installfile.scale=='50m':
			if rus.partscount!=101: raise ValueError
			rus.fixrussia(18,17,istrimtail=True,isdebug=isdebug)
			rus.ccwtypes[18]=CW_CCWTYPE
		elif self.installfile.scale=='10m':
			if rus.partscount!=214: raise ValueError
			rus.fixrussia(0,3,isfix10mpoint=True,isdebug=isdebug) # 0,3 is for nolakes, lakes is probably 0,5
			rus.ccwtypes[0]=CW_CCWTYPE
		else: raise ValueError
	def fixegypt(self):
		egy=self.bynickname['EGY.EGY']
		if self.installfile.scale=='10m':
			if egy.partscount!=10: raise ValueError
			egy.fixegypt(0)
			for i in (1,2): egy.ccwtypes[i]=IGNORE_CCWTYPE
	def makecyprusfull(self):
		nickname='cyprusfull'
		names=['CYP.CYP','CNM.CNM','CYN.CYN']
		sc=ShapeCompress(-1)
		for n in names:
			if not n in self.bynickname: continue
			sc.addshape(self.bynickname[n])
		shape=sc.exportshape()
		self.admin0.addshape(shape,nickname)
	def getlakes(self):
		self.loadlakes()
		ret=[]
		for shape in self.lakes.shapes:
			pluses=ShapePlus.make(shape)
			for plus in pluses: ret.append(plus)
		return ret
	def selectdisputed(self,names,draworder):
		self.loaddisputed()
		for n in names:
			shape=self.disputed.bynickname[n]
			shape.setdraworder(-1,draworder)
	
def sphere2_test(): # test ShpAdmin
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='10m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.fixegypt()
	admin0.setccwtypes()

	if False:
		gsg='GB1.GIB'
		(lon,lat)=admin0.bynickname[gsg].getcenter([-1])
		rotation.set_deglonlat(lon,lat)
#	admin0.bynickname[gsg].setdraworder(-1,1)
	else:
		(lon,lat)=(-5.348580,36.125810)
		(lon,lat)=(-63.078786,18.077765)

	rotation.set_deglonlat(lon,lat)
	print('Center set to %f,%f'%(lon,lat),file=sys.stderr)

	scale=128
	if scale==1:
		bzc=None
	else:
		boxd=1/scale
		bzc=BoxZoomCleave(boxd,boxd,width,height,8)

	cc=CornerCleave(0,0.1,-0.1)
	cc=None

	if scale==1:
		print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl',FOUR_CIRCLE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,BORDER_SPHERE_CSS,HIGH_LAND_SPHERE_CSS,PATCH_HIGH_LAND_SPHERE_CSS],isgradients=True)
		print_roundwater_svg(output,width)
	else:
		print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl',FOUR_CIRCLE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,BORDER_SPHERE_CSS,HIGH_LAND_SPHERE_CSS,PATCH_HIGH_LAND_SPHERE_CSS])
		print_squarewater_svg(output,width)

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
				boxzoomcleave=bzc,cornercleave=cc)
	for one in admin0.shapes:
		one_sphere_print_svg(output,one,1,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
				boxzoomcleave=bzc,cornercleave=cc,islabels=True)

	if True:
		dll=DegLonLat( 35.212087686000,22.786263058000 )
		dll_sphere_print_svg(output,dll,rotation,width,height,FOUR_CIRCLE_CSS,boxzoomcleave=bzc)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def disputed_test(): # find disputed shapes
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'
	scale='10m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.fixegypt()
	admin0.setccwtypes()
	admin0.loaddisputed(is10m=False)

	names=[
		"IND.IND.Jammu and Kashmir", # india and pakistan and china, kashmir
		"CH1.CHN.Aksai Chin", # india and china
"IS1.ISR.Israel", # israel ?
		"IS1.PSX.Gaza", # egypt israel, border
		"IS1.PSX.West Bank", # israel palestine
		"KEN.KEN.Ilemi Triangle", # kenya and south sudan
		"IND.IND.Arunachal Pradesh", # india and china
		"IS1.ISR.Golan Heights", # israel and lebanon
		"SYR.SYR.UNDOF Zone", # syria israel, border
		"SOL.SOL.Somaliland", # somaliland and somalia
		"FR1.FRA.Lawa Headwaters", # suriname and france
		"GUY.GUY.Courantyne Headwaters", # guyana and suriname
		"KOR.KOR.Korean Demilitarized Zone (south)", # northkorea southkorea, border
		"PRK.PRK.Korean Demilitarized Zone (north)", # northkorea southkorea, border-ish (is this a dupe?)
		"MAR.MAR.W. Sahara", # w sahara and morocco
		"SAH.SAH.W. Sahara", # morocco wsahara, this is usa's version of wsahara
		"GEO.B35.Abkhazia", # georgia separatists
		"GEO.B37.South Ossetia", # georgia separatists
		"KOS.KOS.Kosovo", # kosovo serbia
		"ESP.ESP.Ceuta", # morocco spain, border
		"GUY.GUY.West of Essequibo River", # venezuela guyana
		"AZE.AZE.Artsakh", # azerbaijan separatists, aka Nagorno-Karabakh
		"HRV.HRV.Dragonja River", # croatia slovenia, border
		"CH1.CHN.Shaksam Valley", # india pakistan and china
		"PAK.PAK.Gilgit-Baltistan", # pakistan india china, north of kashmir, aka Northern Areas
		"ESP.ESP.Melilla", # morocco spain, border
		"CU1.USG.Guantanamo Bay USNB", # cuba usa, border
		"IND.IND.Near Om Parvat", # india nepal, border
		"BRI.BRI.Brazilian Island", # brazil uruguay, border
		"ESP.ESP.Olivenza", # portugal spain, border
		"MDA.MDA.Transnistria", # moldova separatists
		"UKR.UKR.Donbass", # ukraine separatists
		"GB1.GIB.Gibraltar", # spain uk, border
		"SDN.SDN.Abyei", # sudan and southsudan
		"IND.IND.Demchok", # kashmir and china, border, redundant
		"IND.IND.Samdu Valleys", # india and china, border
		"IND.IND.Tirpani Valleys", # india and china, border
		"IND.IND.Bara Hotii Valleys", # india and china, border
		"CYN.CYN.N. Cyprus", # cyprus, northcyprus separatists
		"CNM.CNM.Cyprus U.N. Buffer Zone", # cyprus northcyprus
		"KAS.KAS.Siachen Glacier", # pakistan and india
		"KA1.KAB.Baykonur", # kazakhstan russia, dispute appears over?
		"BLZ.BLZ.Belize", # guatemala belize
		"SPI.SPI.Southern Patagonian Ice Field", # chile argentina, border
		"BTN.BTN.Bhutan (northwest valleys)", # china bhutan
		"BTN.BTN.Bhutan (Chumbi salient)", # china bhutan
		"RUS.RUS.Crimea", # ukraine and russia
		"IS1.ISR.Shebaa Farms", # lebanon syria israel, border
		"SDS.SDS.Ilemi Triange", # kenya southsudan, border
		"BRA.BRA.Corner of Artigas", # brazil uruguay, border
		"BRT.BRT.Bir Tawil", # egypt sudan, both sides claim it's the other's
		"EGY.EGY.Halayib Triangle", # egypt sudan
		"SRB.SRB.Vukovar Island", # serbia croatia, border
		"SRB.SRB.Šarengrad Island", # serbia croatia, border
		"IS1.ISR.East Jerusalem", # israel palestine, border
		"IS1.ISR.No Man's Land (Fort Latrun)", # israel palestine, border
		"PAK.PAK.Azad Kashmir", # pakistan india, border-ish
		"IS1.ISR.No Man's Land (Jerusalem)", # israel palestine, border
		"IS1.ISR.Mount Scopus", # israel palestine, border
		"IND.IND.Junagadh and Manavadar", # pakistan india
		"TWN.TWN.Taiwan", # taiwan china
		"EGY.EGY.Tiran and Sanafir Is.", # saudiarabia egypt, border
		"FR1.ATF.Juan De Nova I.", # france madagascar, border
		"FR1.FRA.Mayotte", # comoros france, border
		"GB1.IOT.Diego Garcia NSF", # mauritius seychelles uk, border
		"RUS.RUS.Kuril Is.", # japan and russia
		"GB1.IOT.Br. Indian Ocean Ter.", # mauritius seychelles uk, border
		"GB1.SGS.S. Sandwich Is.", # argentina uk, border
		"GB1.SGS.S. Georgia", # argentina uk, border-ish
		"GB1.FLK.Falkland Is.", # uk argentina
		"CH1.CHN.Paracel Is.", # vietnam china taiwan, border
		"FR1.ATF.Europa Island", # france madagascar, border
		"US1.ASM.Swains Island", # americansamoa newzealand, border
		"PGA.PGA.Spratly Is.", # china malaysia philippines taiwan vietnam brunei, border
		"VEN.VEN.Bird Island", # barbados dominica saintkitsandnevis saintlucia saintvincent venezuela, border (only claim non-EEZ) (aves i.)
		"US1.UMI.Wake Atoll", # usa marshallislands, border
		"KOR.KOR.Korean islands under UN jurisdiction", # northkorea southkorea, border (aka northwest islands)
		"GB1.GBR.Rockall I.", # ireland uk, border, ireland only claims uk doesn't have EEZ
		"US1.UMI.Navassa I.", # usa haiti, border
		"FR1.ATF.Bassas da India", # france madagascar, border
		"FR1.ATF.Tromelin I.", # mauritius france, border
		"FR1.ATF.Glorioso Is.", # france madagascar, border
		"JPN.JPN.Pinnacle Is.", # china taiwan japan, border (senkaku)
		"IRN.IRN.Abu Musa I.", # iran uae, border
		"BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", # colombia honduras nicaragua jamaica usa, border
		"SER.SER.Serranilla Bank", # colombia honduras nicaragua jamaica usa, border
		"BLZ.BLZ.Sapodilla Cayes", # honduras belize, border
		"DN1.GRL.Hans Island", # denmark canada, border
		"KOR.KOR.Dokdo", # japan southkorea, border (liancourt)
		"GAB.GAB.Mbane Island", # gabon equatorialguinea, border
		"ESP.ESP.Peñón de Vélez de la Gomera", # morocco spain, border
		"ESP.ESP.Penon de Alhucemas", # morocco spain, border
		"ESP.ESP.Islas Chafarinas", # morocco spain, border
		"ESP.ESP.Isla del Perejil", # morocco spain, border
		"FR1.NCL.Matthew and Hunter Is.", # vanuatu france, border
		"SCR.SCR.Scarborough Reef", # china philippines taiwan, border
		"ERI.ERI.Doumera Island" # djibouti eritrea, border
		]
	name=names[48]

	if False:
		oldnames=[
			"AZE.AZE.Nagorno-Karabakh", # azerbaijan separatists, renamed to Artsakh
			"PAK.PAK.Northern Areas", # pakistan and india and china, north of kashmir, renamed to Gilgit-Baltistan
			"CHL.CHL.Atacama corridor", # chile bolivia (exists in v4, not in v5? why?)
		]
	scale=4
	print('Inspecting %s'%name,file=sys.stderr)

	disputed=admin0.disputed.bynickname[name]

	(lon,lat)=disputed.getcenter([-1])
	rotation.set_deglonlat(lon,lat)
	if scale==1:
		bzc=None
		print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl','debuggreen',FOUR_CIRCLE_CSS,SHADOW_FOUR_CIRCLE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,BORDER_SPHERE_CSS],isgradients=True)
		print_roundwater_svg(output,width)
	else:
		boxd=1/scale
		bzc=BoxZoomCleave(boxd,boxd,width,height,8)
		print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl','debuggreen',FOUR_CIRCLE_CSS,SHADOW_FOUR_CIRCLE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,BORDER_SPHERE_CSS])

	if True:
		for one in admin0.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)

	print_centerdot_svg(output,lon,lat,20,FOUR_CIRCLE_CSS,SHADOW_FOUR_CIRCLE_CSS,rotation,width,height,boxzoomcleave=bzc)
	one_sphere_print_svg(output,disputed,0,rotation,width,height,8,cssfull='debuggreen',csspatch=PATCH_LAND_SPHERE_CSS,
			boxzoomcleave=bzc)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def borderlakes_test(): # find lakes that intersect with borders # this is obsolete, we now just check all lakes every run
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'

	admin0=ShpAdmin('admin0-nolakes.shp',[scale])
	admin0.fixantarctica()
	admin0.fixrussia()
	admin0.fixegypt()
	admin0.setccwtypes()
	admin0.loadlakes()

	(lon,lat)=admin0.bynickname['IS1.ISR'].getcenter([-1])
	rotation.set_deglonlat(lon,lat)

	scale=32
	if scale==1:
		bzc=None
	else:
		boxd=1/scale
		bzc=BoxZoomCleave(boxd,boxd,width,height,8)
	cc=None

	if scale==1:
		print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl',FOUR_CIRCLE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,BORDER_SPHERE_CSS,TEXT_FONT_CSS,SHADOW_FONT_CSS],isgradients=True)
		print_roundwater_svg(output,width)
	else:
		print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,'debugl',FOUR_CIRCLE_CSS,WATER_SPHERE_CSS,PATCH_WATER_SPHERE_CSS,BORDER_SPHERE_CSS,TEXT_FONT_CSS,SHADOW_FONT_CSS])

	for one in admin0.shapes:
		one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
				boxzoomcleave=bzc,cornercleave=cc)

	pluses=admin0.getlakes()
	for plus in pluses:
		plus.shape
		oneplus_sphere_print_svg(output,plus,rotation,width,height,4, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,
				boxzoomcleave=bzc,cornercleave=cc)
		p=plus.polygons[0].points[0]
		if text_sphere_print_svg(output,p,str(plus.shape.index),rotation,width,height,cssfont=TEXT_FONT_CSS,cssfontshadow=SHADOW_FONT_CSS, boxzoomcleave=bzc):
			print('%d:"%s" '%(plus.shape.index,plus.shape.nickname),file=sys.stderr)
			if scale!=1:
				q=p.clone()
				q.lat-=2/scale
				text_sphere_print_svg(output,q,plus.shape.nickname,rotation,width,height,cssfont=TEXT_FONT_CSS,cssfontshadow=SHADOW_FONT_CSS, boxzoomcleave=bzc)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def admin1_test(): # look at admin1 shapes
	output=Output()
	width=1000
	height=1000
	rotation=SphereRotation()
	scale='50m'
	scale='10m'

	admin=ShpAdmin('admin0-nolakes.shp',[scale])
	admin.fixantarctica()
	admin.fixrussia()
	admin.fixegypt()
	admin.setccwtypes()
	admin.loadadmin1()

	if True:
		gsg='BHR.BHR'
		scale=80
		shape0=admin.admin0.bynickname[gsg]
#		shape0=admin.admin1.bynickname['KIR.KIR..']
		admin1name=gsg

	for s in admin.admin1.shapes:
		if s.nickname.startswith(gsg): print(s.nickname,file=sys.stderr)

	shape1=None
	shape2=None
	if False:
		shape1=admin.admin1.shapes[36] # row 38 is Karonga, not Chitipa
		shape2=admin.admin1.shapes[336] # row 338 is Chitipa, correctly
	if False:
		shape1=admin.admin1.shapes[2250] # Cork County
		shape2=admin.admin1.shapes[2251] # Cork City
	if False:
		shape2=admin.admin1.bynickname['BLR.BLR.Minsk.Municipality']
		shape1=admin.admin1.bynickname['BLR.BLR.City of Minsk.Region']
	if False:
		shape1=admin.admin1.bynickname['FR1.WLF.`Uvea.']
		shape1=admin.admin1.bynickname['FR1.WLF.Sigave.']
		shape1=admin.admin1.bynickname['FR1.WLF.Alo.']

	for s in admin.admin1.shapes:
		if not shape0: shape0=s
		if s.nickname.startswith(admin1name): s.setdraworder(-1,1)

	(lon,lat)=shape0.getcenter([-1])
	rotation.set_deglonlat(lon,lat)

	boxd=1/scale
	bzc=BoxZoomCleave(boxd,boxd,width,height,8)

	print_rectwater_svg(output,width,height)

	if True:
		for one in admin.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,8,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)

	if True:
		for one in admin.admin1.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,8,cssfull=OVERLAP_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)

#	print_centerdot_svg(output,lon,lat,20,FOUR_CIRCLE_CSS,SHADOW_FOUR_CIRCLE_CSS,rotation,width,height,boxzoomcleave=bzc)
	if shape1:
		one_sphere_print_svg(output,shape1,1,rotation,width,height,8,cssfull='debuggreen',csspatch=PATCH_LAND_SPHERE_CSS,
				boxzoomcleave=bzc)
	if shape2:
		one_sphere_print_svg(output,shape2,1,rotation,width,height,8,cssfull='debugred',csspatch=PATCH_LAND_SPHERE_CSS,
				boxzoomcleave=bzc)

	print_footer_svg(output)
	if True:
		o=Output()
		print_header_svg(o,width,height,output.csscounts,isgradients=False,ishypso=False)
		output.prepend(o)
	output.writeto(sys.stdout)

def sphere3_test(): # test merging ShapePlus to reduce border drawing, this is obsolete by WorldCompress and worldcompress_test
	output=Output()
	width=500
	height=500
	lat_center=0
	lon_center=0
	rotation=SphereRotation()

	admin0=Shp(installfile=install.getinstallfile('admin0.shp'))
	admin0.loadshapes()
	admin0dbf=Dbf(installfile=install.getinstallfile('admin0.dbf'))
	admin0dbf.selectcfield('SOV_A3','sov3')
	admin0dbf.selectcfield('ADM0_A3','adm3')
	admin0dbf.loadrecords()
	indices=[]
	gsgs=['ZAF.ZAF','SWZ.SWZ','MOZ.MOZ','TZA.TZA','KEN.KEN','BWA.BWA','ZWE.ZWE']

	# indices.append(admin0dbf.query1({'sov3':'NAM','adm3':'NAM'}))
	for gsg in gsgs:
		(grp,subgrp)=gsg.split('.')
		indices.append(admin0dbf.query1({'sov3':grp,'adm3':subgrp}))

	print_header_svg(output,width,height,[LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,BORDER_SPHERE_CSS])
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
			flatshape.printsvg(output,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)
	if False:
		for onepl in allextracts:
			oneplus=ShapePlus.makefrompolyline(onepl,0)
			onesphere=SphereShape(oneplus,rotation)
			hc.cleave(onesphere)
			if onesphere.type!=NULL_TYPE_SHP:
				flatshape=onesphere.flatten(width,height,8)
				flatshape.printsvg(output,cssline=BORDER_SPHERE_CSS)
	print_footer_svg(output)
	output.writeto(sys.stdout)

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
	groups.append(['KA1.KAZ','UZB.UZB','ARM.ARM','KGZ.KGZ','TJK.TJK','TKM.TKM','AZE.AZE','GEO.GEO'])
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

	admin0=Shp(installfile=install.getinstallfile('admin0.shp',['10m']))
	admin0.loadshapes()
	admin0dbf=Dbf(installfile=install.getinstallfile('admin0.dbf',['10m']))
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

	print_header_svg(output,width,height,[BORDER_SPHERE_CSS,LAND_SPHERE_CSS,PATCH_LAND_SPHERE_CSS,HIGH_BORDER_SPHERE_CSS,HIGH_LAND_SPHERE_CSS,PATCH_HIGH_LAND_SPHERE_CSS],isgradients=True)
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
				flatshape.printsvg(output,cssline=BORDER_SPHERE_CSS,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS)
	for oneplus in hpluses:
		onesphere=SphereShape(oneplus,rotation)
		hc.cleave(onesphere)
		if onesphere.type!=NULL_TYPE_SHP:
			flatshape=onesphere.flatten(width,height,8)
			flatshape.printsvg(output,cssline=HIGH_BORDER_SPHERE_CSS,cssfull=HIGH_LAND_SPHERE_CSS,csspatch=PATCH_HIGH_LAND_SPHERE_CSS)

	print_footer_svg(output)
	output.writeto(sys.stdout)

def lonlat_test(): # test lon/lat text labels
	output=Output()
	width=1000
	height=1000
	lat_center=-20
	lon_center=25

	rotation=SphereRotation()
	rotation.set_deglonlat(lon_center,lat_center)
	print_header_svg(output,width,height,[TEXT_FONT_CSS,SHADOW_FONT_CSS,GRID_SPHERE_CSS],isgradients=True)
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
	output.writeto(sys.stdout)

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
			output.countcss(cssclass)
			output.print('<path class="%s" d="M%d,%dL%d,%dZ"/>'%(cssclass,x1,y1,x2,y2))
			return

		if False:
			output.print('<polyline style="stroke:purple;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.left.ux,self.left.uy, self.right.ux,self.right.uy))
			output.print('<polyline style="stroke:cyan;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.top.ux,self.top.uy, self.bottom.ux,self.bottom.uy))
		if self.tiltdeg>=0:
			if self.londeg>90:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))
			else:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))
		else:
			if self.londeg>90:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))
			else:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, %.8f, 0 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry,rotdeg, x2,y2 ))

class SphereLongitude():
	@staticmethod
	def make(rotation_in,londeg):
		deg=londeg-rotation_in.dlon+90
		while deg<=0: deg+=360
		while deg>=360: deg-=360
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
			output.countcss(cssclass)
			output.print('<path class="%s" d="M%d,%dL%d,%dZ"/>'%(cssclass,x1,y1,x2,y2))
			return
		if False:
			output.print('<polyline style="stroke:purple;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.left.ux,self.left.uy, self.right.ux,self.right.uy))
			output.print('<polyline style="stroke:cyan;fill-opacity:0" points="%d,%d %d,%d"/>'%
					(self.top.ux,self.top.uy, self.bottom.ux,self.bottom.uy))
		if self.tiltdeg>0:
			if self.latdeg>0:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 1 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))
			else:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 0 0, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))
		else:
			if self.latdeg>0:
				output.countcss(cssclass)
				output.print('<path class="%s" d="M %.4f %.4f A %.4f %.4f, 0, 0 1, %.4f %.4f"/>'%
						(cssclass,x1,y1, rx,ry, x2,y2 ))
			else:
				output.countcss(cssclass)
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
	print_header_svg(output,width,height,[GRID_SPHERE_CSS],isgradients=True)
	print_roundwater_svg(output,width)
#	for i in range(8): lon=i*45+10
	for lon in [ 0, -30, -60, -90, 30, 60 ]:
		lon+=10
		rotation=SphereRotation()
		rotation.set_deglonlat(lon,23)
		c=SphereCircle(rotation)
		fc=c.flatten(width,height)
		fc.printsvg(output,GRID_SPHERE_CSS)
	for lon in [ 0, -30, -60, -90, 30, 60 ]:
		lon+=10
		rotation=SphereRotation()
		rotation.set_deglonlat(lon,23)
		e=SphereLongitude.make(rotation,0) # 0 is untested, we changed how this works
		if e==None: continue
		fe=e.flatten(width,height)
		fe.printsvg(output,GRID_SPHERE_CSS)
	print_footer_svg(output)
	output.writeto(sys.stdout)
	

def dicttostr(label,d):
	isfirst=True
	names=[]
	for n in d: names.append(n)
	names.sort()
	a=[]
	a.append(label+' : {')
	for n in names:
		a.append('\t\''+str(n)+'\' : \''+str(d[n])+'\'')
	a.append('}')
	return '\n'.join(a)

def loaddbf_locatormap(shp):
	dbf=Dbf(installfile=install.getinstallfile('admin0.dbf',[shp.installfile.scale]))
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
	shp=Shp(installfile=ifile)
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

def locatormap(output,overrides,labels):
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
	options['zoom']=2
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
#	options['borderlakes']=None
	options['isdisputed']=False
	options['zoomlon']=None
	options['zoomlat']=None
	options['zoomdisputedcssforce']=DISPUTED_BORDER_ZOOM_CSS
	options['zoomdisputedbordercssforce']=DISPUTED_BORDER_ZOOM_CSS
	options['bgcolor']=None
	options['hypso']=None
	options['hypsocache']=None
	options['hypsocutout']=True
	options['hypsodim']=options['width']

	publicfilter=('cmdline','title','comment','version')

	if True:
		pub={}
		for n in overrides:
			if n not in publicfilter: continue
			pub[n]=overrides[n]
		options['comment']=dicttostr('vars',pub)
	for n in overrides: options[n]=overrides[n]

	full_admin0=ShpAdmin('admin0-nolakes.shp',[options['fullm']])

	sphere_admin0=ShpAdmin('admin0-nolakes.shp',[options['spherem']])
	sphere_admin0.fixantarctica()
	sphere_admin0.fixrussia()
	sphere_admin0.fixegypt()
	sphere_admin0.setccwtypes()
	sphere_admin0.loadlakes()

	if options['zoomm']==options['spherem']:
		zoom_admin0=sphere_admin0
	else:
		zoom_admin0=ShpAdmin('admin0-nolakes.shp',[options['zoomm']])
		zoom_admin0.fixantarctica()
		zoom_admin0.fixrussia()
		zoom_admin0.fixegypt()
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
		print('error: full_index=%d'%(full_index),file=sys.stderr)
		print('No location specified or given location isn\'t global?',file=sys.stderr)
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

	combo_print_svg(output,options,full_admin0,sphere_admin0,zoom_admin0,labels)

def euromap(output,overrides,labels):
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
#	options['borderlakes']=None
	options['ispartlabels']=False
	options['euromapdots_50m']=None
	allowedoverrides=['comment','copyright','width','height','islakes','spherem','splitlimit','labelfont','gsgs',
			'ispartlabels','euromapdots_50m']
	publicfilter=('cmdline','title','comment','version')

	if 'gsg' in overrides: options['gsgs']=[overrides['gsg']]

	if True:
		pub={}
		for n in overrides:
			if n not in publicfilter: continue
			pub[n]=overrides[n]
		options['comment']=dicttostr('vars',pub)

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
	admin0.fixegypt()
	admin0.makecyprusfull()
	admin0.setccwtypes()
	if options['islakes']: admin0.loadlakes()

	(lon,lat)=admin0.bynickname['DEU.DEU'].getcenter([-1])
	rotation.set_deglonlat(lon-6,lat)

	zoomscale=2
	boxd=1/zoomscale
	bzc=BoxZoomCleave(boxd,boxd,width,height,splitlimit)

	cc=None

# Austria Belgium Bulgaria Croatia Cyprus(whole) Czech Denmark Estonia Finland France
# Germany Greece Hungary Ireland Italy Latvia Lithuania Luxembourg Malta Netherlands Poland Portugal
# Romania Slovakia Slovenia Spain Sweden

	eugsgs=['AUT.AUT','BEL.BEL','BGR.BGR','HRV.HRV','cyprusfull','CZE.CZE','DN1.DNK','EST.EST','FI1.FIN','FR1.FRA',
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

	if options['gsgs']:
		for gsg in options['gsgs']:
			if gsg in admin0.bynickname: admin0.bynickname[gsg].setdraworder(-1,3)
			else: print('Skipping gsg:%s, not found in %s'%(gsg,options['spherem']),file=sys.stderr)

	eu_wc.removeoverlaps(admin0.shapes,3) # remove draworder 3 (highlights) from border polylines

	euborderlakeshapes=[]
	if 'EST.EST' not in options['gsgs']: 
		sasi=ShpAdminShapeIntersection()
		pluses=eu_wc.getpluses(isnegatives=False,isoverlaps=False)
		for plus in pluses:
			sasi.addfromplus(plus)
		for l in admin0.lakes.shapes:
			sasi.setinside(l)
		euborderlakeshapes=sasi.exportlines()

	gsgborderlakeshapes=[]
	if options['islakes']:
		sasi=ShpAdminShapeIntersection()
		sasi.addfromshapes(admin0.shapes,3)
		for l in admin0.lakes.shapes:
			sasi.setinside(l)
		gsgborderlakeshapes=sasi.exportlines()

#	print_header_svg(output,width,height,css,options['labelfont'],[options['copyright'],options['comment']])
	print_squarewater_svg(output,width)

	if True: # draw plain background countries
		for one in admin0.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc,cornercleave=cc)

	if True: # draw worldcompress continents
		pluses=other_wc.getpluses(isnegatives=False,isoverlaps=False)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,boxzoomcleave=bzc)

		pluses=eu_wc.getpluses(isnegatives=False,isoverlaps=False)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=AREA_LAND_SPHERE_CSS,csspatch=PATCH_AREA_LAND_SPHERE_CSS,boxzoomcleave=bzc)

	if True: # draw andorra, switzerland, halflights and highlights
		for one in admin0.shapes:
			one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc,cornercleave=cc)

		for one in admin0.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull=AREA_LAND_SPHERE_CSS,csspatch=PATCH_AREA_LAND_SPHERE_CSS,
					boxzoomcleave=bzc,cornercleave=cc)

		for one in admin0.shapes:
			one_sphere_print_svg(output,one,3,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,csspatch=PATCH_HIGH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc,cornercleave=cc,islabels=options['ispartlabels'])

	if True: # draw continent ccws
		negatives=eu_wc.getnegatives()
		pluses_sphere_print_svg(output,negatives,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,boxzoomcleave=bzc)
		negatives=other_wc.getnegatives()
		pluses_sphere_print_svg(output,negatives,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,boxzoomcleave=bzc)

	if True: # draw lakes
		pluses=admin0.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,boxzoomcleave=bzc)

	if True: # draw continent borders, intersections with highlights already removed
		pluses=other_wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssline=BORDER_SPHERE_CSS,boxzoomcleave=bzc)
		pluses=eu_wc.getpluses(ispositives=False,isoverlaps=True)
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssline=AREA_BORDER_SPHERE_CSS,boxzoomcleave=bzc)

	if True: # draw highlight intersections with lakes over lakes
		for plus in euborderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=BORDER_SPHERE_CSS,boxzoomcleave=bzc)
		for plus in gsgborderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=HIGH_BORDER_SPHERE_CSS,boxzoomcleave=bzc)

	if moredots:
		for dots in moredots:
			gsg=dots[0]
			shape=admin0.bynickname[gsg]
			sds=int((dots[1]*width)/1000)
			isw=dots[2]
			smalldots=dots[3]
			cssclass=ONE_CIRCLE_CSS # only c1/w1 are included in css above
			if isinstance(isw,bool) and isw: cssclass=FOUR_CIRCLE_CSS
			elif isw==1: cssclass=ONE_CIRCLE_CSS
			elif isw==2: cssclass=TWO_CIRCLE_CSS
			elif isw==3: cssclass=THREE_CIRCLE_CSS
			elif isw==4: cssclass=FOUR_CIRCLE_CSS
			cssclass2=getshadow_circle_css(cssclass)
			print_zoomdots_svg(output,shape,smalldots,sds,cssclass,cssclass2,rotation,width,height,boxzoomcleave=bzc)

	if labels:
		labels.printsvg(output,rotation,width,height,bzc)

	print_footer_svg(output)
	if True:
		o=Output()
		print_header_svg(o,width,height,output.csscounts,options['labelfont'],[options['copyright'],options['comment']])
		output.prepend(o)

def countrymap(output,overrides,labels):
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
#	options['borderlakes']=None
	options['ispartlabels']=False
	options['countrymapdots_10m']=None
	options['centerindices_10m']=None
	options['zoom']=1
	options['lon']=None
	options['lat']=None
	options['admin1']=None
	options['disputed']=None
	options['disputed_border']=None
	options['admin1dot']=None
	options['admin1dots']=0
	options['bgcolor']=None
	options['hypso']=None
	options['hypsocache']=None
	options['hypsofast']=None
	options['hypsocutout']=True
	options['hypsodim']=options['width']
	options['disputed_circles']=None
	options['disputed_labels']=[]
	options['isdisputed_labels']=True
	allowedoverrides=['comment','copyright','width','height','islakes','spherem','splitlimit','labelfont','gsg','gsgs',
			'ispartlabels','countrymapdots_10m','zoom','centerindices_10m','lon','lat','admin1','admin1dot','admin1dots',
			'disputed','disputed_border','bgcolor','hypso','hypsocache','hypsofast','hypsocutout','hypsodim','disputed_circles',
			'disputed_labels','isdisputed_labels']
	publicfilter=('cmdline','title','comment','version','isdisputed_labels')

	if overrides.get('zoom',1)>=4: # TODO tweak this, 8x is good at hr
		if 'hypso_high' in overrides: overrides['hypso']=overrides['hypso_high']

	if 'countrymapcenterindices_10m' in overrides:
		overrides['centerindices_10m']=overrides['countrymapcenterindices_10m']

	if 'gsg' in overrides: options['gsgs']=[overrides['gsg']]
	if True:
		pub={}
		for n in overrides:
			if n not in publicfilter: continue
			pub[n]=overrides[n]
		options['comment']=dicttostr('vars',pub)

	for n in overrides:
		 if n in allowedoverrides: options[n]=overrides[n]

	if options['hypso']:
		if not zlib:
			print('hypso feature requires zlib dependency and it wasn\'t found, quitting',file=sys.stderr)
			return
		options['islakes']=False

	width=options['width']
	height=options['height']
	splitlimit=options['splitlimit']
	rotation=SphereRotation()
	zoomscale=options['zoom']
	moredots=options['countrymapdots_10m']
	admin1=options['admin1']

	admin=ShpAdmin('admin0-nolakes.shp',[options['spherem']])
	admin.fixantarctica()
	admin.fixrussia()
	admin.fixegypt()
	admin.setccwtypes()
#	admin.loadlakes()

	if options['disputed']: admin.selectdisputed(options['disputed'],1)
	if options['disputed_border']: admin.selectdisputed(options['disputed_border'],2)
	if admin1!=None:
		admin.loadadmin1()
		admin.loadadmin1lines()

	if options['centerindices_10m']:
		if isverbose_global: print('Looking for custom center: %s'%str(options['centerindices_10m']),file=sys.stderr)
		(lon,lat)=admin.bynickname[options['gsg']].getcenter(options['centerindices_10m'])
	else:
		(lon,lat)=admin.bynickname[options['gsg']].getcenter([-1])
	if options['lon']!=None: lon=options['lon']
	if options['lat']!=None: lat=options['lat']
	if isverbose_global: print('Centering on %f,%f'%(lon,lat),file=sys.stderr)
	rotation.set_deglonlat(lon,lat)

	bzc=None
	cc=None
	if zoomscale!=1:
		boxd=1/zoomscale
		bzc=BoxZoomCleave(boxd,boxd,width,height,splitlimit)

	if options['hypso']:
		isgradients=(zoomscale==1)
#		print_header_svg(output,width,height,css,options['labelfont'],[options['copyright'],options['comment']], hypso=True,isgradients=isgradients)
		hypso=Hypso(options['hypsodim'],options['hypsodim'],'./hypsocache',options['hypsocache'])
		if options['hypsocache']==None or not hypso.loadpng_cache():
			if options['hypsocache']==None or not hypso.loadraw_cache():
				hs=HypsoSphere(install.getfilename(options['hypso']+'.pnm',['10m']))
				hs.setcenter(lon,lat)
				if bzc:
					hs.setzoom(bzc.right,bzc.top,bzc.right*2,bzc.top*2)
				hypso.loadsphere(hs)
				if options['hypsocache']!=None:
					hypso.saveraw_cache(True)
			if bzc: hypso.interpolate()
			p=Palette()
			p.loaddefaults()
			if isverbose_global: print('Indexing colors',file=sys.stderr)
			hypso.indexcolors(p)
			if options['hypsocache']!=None:
				hypso.savepng_cache(True)
		print_hypso_svg(output,width,height,hypso,options['hypsofast'],isgradients=isgradients)
	else: # not hypso
		if zoomscale==1:
#			print_header_svg(output,width,height,css,options['labelfont'],[options['copyright'],options['comment']],isgradients=True)
			if options['bgcolor']: print_rectangle_svg(output,0,0,width,height,options['bgcolor'],1.0)
			print_roundwater_svg(output,width)
		else:
#			print_header_svg(output,width,height,css,options['labelfont'],[options['copyright'],options['comment']])
			print_squarewater_svg(output,width)

	for gsg in options['gsgs']:
		admin.setdraworder(admin.bynickname[gsg].index,-1,2)
	if len(options['gsgs'])==1:
		admin0shape=admin.admin0.bynickname[options['gsgs'][0]]

	admin1shape=None
	if admin1!=None:
		admin1lines=ShpAdminLines(admin.admin1lines.shapes,options['gsg'])
		if admin1:
			admin1shape=admin.admin1.bynickname2(admin1)
			if not admin1shape:
				print('Couldn\'t find admin1 nickname %s in database'%admin1,file=sys.stderr)
				raise ValueError
			admin1shape.setdraworder(-1,3)
			admin1lines.addpolygons([admin1shape],None)
			admin1lines.reducelines()

	if True: # draw plain background countries
		for one in admin.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc,cornercleave=cc)
		if admin1==None:
			if options['hypso'] and options['hypsocutout']:
				cutout_sphere_print_svg(output,admin0shape,-1,rotation,width,height,splitlimit,cssfull=HYPSOCUT_SPHERE_CSS,
						boxzoomcleave=bzc,cornercleave=cc)
			else:
				for one in admin.shapes:
					one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,csspatch=PATCH_HIGH_LAND_SPHERE_CSS,
							boxzoomcleave=bzc,cornercleave=cc)
		else:
			if options['hypso'] and options['hypsocutout']:
				for plus in admin1lines.exportlines():
					oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=AREA_BORDER_SPHERE_CSS,
							boxzoomcleave=bzc,cornercleave=cc)
				if admin1shape:
					cutout_sphere_print_svg(output,admin1shape,-1,rotation,width,height,splitlimit,cssfull=HYPSOCUT_SPHERE_CSS,
							boxzoomcleave=bzc,cornercleave=cc)
			else:
				for one in admin.shapes:
					one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=AREA_LAND_SPHERE_CSS,
							csspatch=PATCH_AREA_LAND_SPHERE_CSS, boxzoomcleave=bzc,cornercleave=cc)
				for plus in admin1lines.exportlines():
					oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=AREA_BORDER_SPHERE_CSS,
							boxzoomcleave=bzc,cornercleave=cc)
				if admin1shape:
					one_sphere_print_svg(output,admin1shape,3,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,
							csspatch=PATCH_HIGH_LAND_SPHERE_CSS, boxzoomcleave=bzc,cornercleave=cc)
		if admin1shape and options['admin1dots']:
			print_zoomdots_svg(output,admin1shape,-1,options['admin1dots'],ONE_CIRCLE_CSS,SHADOW_ONE_CIRCLE_CSS,rotation,width,height,bzc,
					threshhold=10)

	if options['islakes']:
		if isverbose_global: print('Drawing lakes sphere shapes',file=sys.stderr)
		pluses=admin.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,
				boxzoomcleave=bzc,cornercleave=cc)

	if options['islakes']:
		if isverbose_global: print('Finding admin0 border lakes (%s)'%options['spherem'],file=sys.stderr)
		sasi=ShpAdminShapeIntersection()
		sasi.addfromshapes(admin.shapes,2)
		for l in admin.lakes.shapes:
			sasi.setinside(l)
		borderlakeshapes=sasi.exportlines()
		if admin1shape:
			if isverbose_global: print('Finding admin1 border lakes (%s)'%options['spherem'],file=sys.stderr)
			sasi=ShpAdminShapeIntersection()
			sasi.addfromshapes(admin.admin1.shapes,3)
			for l in admin.lakes.shapes:
				sasi.setinside(l)
			admin1_borderlakeshapes=sasi.exportlines()
			for plus in borderlakeshapes:
				if plus.type!=POLYLINE_TYPE_SHP: continue
				oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=AREA_LAKELINE_SPHERE_CSS,boxzoomcleave=bzc)
			for plus in admin1_borderlakeshapes:
				if plus.type!=POLYLINE_TYPE_SHP: continue
				oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=HIGH_BORDER_SPHERE_CSS,boxzoomcleave=bzc)
		else:
			for plus in borderlakeshapes:
				if plus.type!=POLYLINE_TYPE_SHP: continue
				oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=HIGH_BORDER_SPHERE_CSS,boxzoomcleave=bzc)

	if True:
		if options['disputed'] or options['disputed_border']:
			for one in admin.disputed.shapes:
				one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull=DISPUTED_LAND_SPHERE_CSS,
						csspatch=PATCH_DISPUTED_LAND_SPHERE_CSS,cssforcepixel=DISPUTED_LAND_SPHERE_CSS,boxzoomcleave=bzc,cornercleave=cc)
				one_sphere_print_svg(output,one,2,rotation,width,height,splitlimit,cssfull=DISPUTED_LAND_SPHERE_CSS,
						csspatch=PATCH_DISPUTED_LAND_SPHERE_CSS,cssforcepixel=DISPUTED_BORDER_SPHERE_CSS,boxzoomcleave=bzc,cornercleave=cc)
			if options['isdisputed_labels']:
				if not labels: labels=LabelMaker()
				for dl in options['disputed_labels']:
					s=admin.disputed.bynickname[dl[0]]
					labels.addlabelshape(s,rotation,width,height,bzc,dl[2],dl[3],dl[4],dl[1],dl[5],dl[6],dl[7],dl[8],dl[9])
				
	if moredots:
		shape=admin.bynickname[gsg]
		for dots in moredots:
			sds=int((dots[0]*width*4)/1000)
			isw=dots[1]
			smalldots=dots[2]
			cssclass=ONE_CIRCLE_CSS
			if isinstance(isw,bool) and isw: cssclass=FOUR_CIRCLE_CSS
			elif isw==1: cssclass=ONE_CIRCLE_CSS
			elif isw==2: cssclass=TWO_CIRCLE_CSS
			elif isw==3: cssclass=THREE_CIRCLE_CSS
			elif isw==4: cssclass=FOUR_CIRCLE_CSS
			cssclass2=getshadow_circle_css(cssclass)
			print_zoomdots_svg(output,shape,smalldots,sds,cssclass,cssclass2,rotation,width,height,boxzoomcleave=bzc)

	if options.get('disputed_circles',0):
		sds=int((options['disputed_circles']*width)/1000)
		for s in admin.disputed.shapes:
			(has,_)=s.hasdraworder(2)
			if not has: continue
			mbr=s.getmbr(-1)
			sr=SphereRectangle.makefrommbr(mbr,rotation)
			if bzc: f=sr.flatten(width,height,bzc.right,bzc.top)
			else: f=sr.flatten(width,height,1,1)
			(cx,cy)=f.getcenter()	
			r=f.getradius()+sds+0.5
			print_flatdot_svg(output,cx,cy,int(r),ONE_DISPUTED_CIRCLE_CSS,SHADOW_ONE_CIRCLE_CSS)

	if options['admin1dot']:
		mbr=admin1shape.getmbr(-1)
		sr=SphereRectangle.makefrommbr(mbr,rotation)
		if bzc: f=sr.flatten(width,height,bzc.right,bzc.top)
		else: f=sr.flatten(width,height,1,1)
		(cx,cy)=f.getcenter()	
		r=f.getradius()
		r+=(options['admin1dot']*width)/1000
		print_flatdot_svg(output,cx,cy,int(r),ONE_CIRCLE_CSS,SHADOW_ONE_CIRCLE_CSS)
		
	if labels:
		labels.printsvg(output,rotation,width,height,bzc)

	print_footer_svg(output)
	if True:
		o=Output()
		ishypso=True if options['hypso'] else False
		isgradients=True if zoomscale==1 else False
		print_header_svg(o,width,height,output.csscounts,options['labelfont'],[options['copyright'],options['comment']],
				ishypso=ishypso, isgradients=isgradients)
		output.prepend(o)

class Options():
	@staticmethod
	def collapsename(name):
		Accents=('İ',)  # this can be converted to multiple chars with .lower(), easiest to just convert them first
		Nocents=('i',)
		accents=('é','á','ó','í','ñ','ú','è','ô','ç','š','ø','ä','ö','ậ','ắ','à','đ','ế','ệ','ê','ì','ị','ớ','ò','ồ','ð','ư','ạ','ằ','ẵ','ả','â','ề','ĩ','ơ','ọ','ừ','ũ','ộ','ã','ă','å','ā','č','ĭ','ï','ň','ŏ','õ','ř','ü','ý','ž','ë','ş','ğ','ə','ı','œ','æ','ć','ł','ź','ś','ę', 'ū','ī','ḩ','ţ','î','û','ō','ż','ġ','ħ','ċ','ș','ṭ','ḷ','ṇ','ḍ','ĕ')
		nocents=('e','a','o','i','n','u','e','o','c','s','o','a','o','a','a','a','d','e','e','e','i','i','o','o','o','d','u','a','a','a','a','a','e','i','o','o','u','u','o','a','a','a','a','c','i','i','n','o','o','r','u','y','z','e','s','g','e','i','o','a','c','l','z','s','e',
'u','i','h','t','i','u','o','z','g','h','c','s','t','l','n','d','e')
		ellipses=(' ','\'','-',',','.','–','`','/','\\')
		terms=('(','[')
		a=list(name)
		n=len(a)
		i=0
		while i<n:
			if a[i] in ellipses:
				del a[i]
				n-=1
				continue
			if a[i] in terms:
				del a[i:]
				n=i
				continue
			if a[i] in Accents: a[i]=Nocents[Accents.index(a[i])]
			a[i]=a[i].lower()
			if a[i] in accents: a[i]=nocents[accents.index(a[i])]
			i+=1
		return ''.join(a)
	def __init__(self):
		self.admin1dbf=None
		self.root=None
	def basic(self,param,name,gsg=None,isadmin1=False,isdisputed=False,extra=None):
		if param=='/': return name
		ret=[]
		if param==name+'/':
			if isdisputed: ret.append(name+'/_disputed')
			if extra:
				for e in extra: ret.append(name+'/'+e)
			if isadmin1:
				self.appendadmin1(ret,gsg,name+'/')
		if ret==[]: ret=None
		return ret
	def handle(self,options,param):
		if not '/' in param: return
		parts=param.split('/')
		admin1=parts[1]
		if admin1=='_admin1':
			options['admin1']=''
			return
		a1type=None
		if '_' in admin1:
			a=admin1.split('_')
			admin1=a[0]
			a1type=a[1]
		dbf=self.admin1dbf
		if not dbf: dbf=self.loadadmin1dbf()
		gsg=options['gsg']
		for i in range(dbf.numrecords):
			r=dbf.records[i]
			rgsg=r['sov3']+'.'+r['adm3']
			if rgsg!=gsg: continue
			name=r['name']
			if not name: name='_blank_'+str(i)
			if Options.collapsename(name)!=admin1: continue
			t=r['type']
			if a1type:
				if Options.collapsename(t)!=a1type: continue
			options['admin1']=gsg+'.'+name+'.'+t
			options['countrymapdots_10m']=[]
			break
		else:
			options['isnotfound']=True
	def loadadmin1dbf(self):
		dbf=Dbf(installfile=install.getinstallfile('admin1-nolakes.dbf',['10m']))
		dbf.selectcfield('sov_a3','sov3')
		dbf.selectcfield('adm0_a3','adm3')
		dbf.selectcfield('name','name')
		dbf.selectcfield('type_en','type')
		dbf.loadrecords()
		fixes=((3141,'MEX','MEX','','islaperez'), # 3139 for v4
				(36,'MWI','MWI','Chitipa','Karonga'), # typo in v5
				)
		for f in fixes:
			r=dbf.records[f[0]]
			if f[1:4]!=(r['sov3'],r['adm3'],r['name']): raise ValueError
			r['name']=f[4]
		self.admin1dbf=dbf
		return dbf
	def loadroot(self):
		root={}
		for g in globals():
			if g.startswith('_'): continue
			if not g.endswith('_options'): continue
			f=globals().get(g)
			l=f('/')
			if isinstance(l,str): l=(l,)
			for n in l: root[n]=f
		self.root=root
		return root
	def appendadmin1(self,dest,gsg,prefix):
		dbf=self.admin1dbf
		if not dbf: dbf=self.loadadmin1dbf()
		isfound=False
		shortnames={}
		for i in range(dbf.numrecords):
			r=dbf.records[i]
			rgsg=r['sov3']+'.'+r['adm3']
			if rgsg!=gsg: continue
			name=r['name']
			if not name: name='_blank_'+str(i)
			shortnames[name]=shortnames.get(name,0)+1

		for i in range(dbf.numrecords):
			r=dbf.records[i]
			rgsg=r['sov3']+'.'+r['adm3']
			if rgsg!=gsg: continue
			name=r['name']
			if not name: name='_blank_'+str(i)
			if shortnames[name]==1:
				dest.append(prefix+Options.collapsename(name))
			else:
				t=r['type']
				dest.append(prefix+Options.collapsename(name)+'_'+Options.collapsename(t))
			isfound=True
		if isfound: dest.append(prefix+'_admin1')
	def listoptionpath2(self,matches):
		more=[]
		for n,f in matches:
			ns=n+'/'
			r=f(ns)
			if not r: continue
			more.append((ns,f))
		for m in more: matches.append(m)
		return matches
	@staticmethod
	def splitpath(path):
		parts=path.split('/')
		i=0
		n=len(parts)-1
		while i<n:
			if parts[i]=='':
				del parts[i]
				n-=1
				continue
			i+=1
		fpath='/'.join(parts)
		return (fpath,parts[0])
	def listoptionpath(self,path):
		if not path.endswith('/'): return None
		root=self.root
		if not root: root=self.loadroot()
		if path=='/':
			dest=[]
			for n in root: dest.append((n,root[n]))
			return self.listoptionpath2(dest)
		(fpath,basedir)=Options.splitpath(path)
		f=root[basedir]
		if not f: return None
		a=f(fpath)
		if not a: return None
		ret=[]
		for m in a: ret.append((m,f))
		return ret
	def getoptions(self,path):
		if path.endswith('/'): return None
		root=self.root
		if not root: root=self.loadroot()
		(fpath,basedir)=Options.splitpath(path)
		if basedir not in root: return None
		f=root[basedir]
		return f(fpath)
	def isvalidpath(self,path):
		if self.listoptionpath(path): return True
		opts=self.getoptions(path)
		if not opts: return False
		if 'isnotfound' in opts: return False
		return True
	def listall(self):
		r=[]
		a=self.listoptionpath('/')
		while a!=[]:
			n,f=a.pop()
			if not n.endswith('/'): r.append(n)
			else:
				d=f(n)
				for e in d: a.append((e,f))
		return r

options_global=Options()

class Label():
	def __init__(self,dlon,dlat,text,font,fontoffx,fontoffy,lineoffx,lineoffy,gap,shadow,rotation,hidden,anchor):
		(self.dlon,self.dlat,self.text,self.font,self.fontoffx,self.fontoffy,self.lineoffx,self.lineoffy,self.gap,self.shadow,self.rotation,self.hidden,self.anchor)=(dlon,dlat,text,font,fontoffx,fontoffy,lineoffx,lineoffy,gap,shadow,rotation,hidden,anchor)
#		print('debug',self.dlon,self.dlat,self.text,file=sys.stderr)

class UrlDecoding():
	@staticmethod
	def unhex(a,b):
		d={'0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
				'a':10,'A':10,'b':11,'B':11,'c':12,'C':12,'d':13,'D':13,'e':14,'E':14,'f':15,'F':15}
		return (d[a]<<4)+d[b]
	@staticmethod
	def unescape(v):
		a=v.split('%')
		b=[]
		b.append(a[0])
		last=bytearray()
		for i in range(1,len(a)):
			o=a[i]
			c=UrlDecoding.unhex(o[0],o[1])
			last.append(c)
			o=o[2:]
			if len(o):
				b.append(last)
				last=bytearray()
				b.append(o)
		if len(last): b.append(last)
		for i,o in enumerate(b):
			if isinstance(o,bytearray): b[i]=o.decode()
		return ''.join(b)

class LabelMaker():
	def reset(self):
		self.fontoffsetx='+0'
		self.fontoffsety='+0'
		self.lineoffsetx=0
		self.lineoffsety=0
		self.linegap=10
		self.dlon=0
		self.dlat=0
		self.font='42px sans'
		self.shadow=0
		self.rotation=0
		self.hidden=7
		self.anchor=0
	def __init__(self):
		self.reset()
		self.labels=[]
		self.commands=[]
		self.populateddbf=None
	def addlabel(self,t):
		self.labels.append(Label(self.dlon,self.dlat,t,self.font,self.fontoffsetx,self.fontoffsety,self.lineoffsetx,self.lineoffsety,
				self.linegap,self.shadow,self.rotation,self.hidden,self.anchor))
	def addlabelshape(self,shape,rotation,width,height,bzc,font,angle,anchor,text,offx,offy,gap,lx,ly):
		mbr=shape.getmbr(-1)
		sr=SphereRectangle.makefrommbr(mbr,rotation)
		if bzc: f=sr.flatten(width,height,bzc.right,bzc.top)
		else: f=sr.flatten(width,height,1,1)
		if gap<0: r=-gap-2
		elif gap==0: r=0
		else: r=int(f.getradius()+0.5+(gap*width/1000))
		(cx,cy)=mbr.getcenter()	
		h=6 if font else 4
		self.labels.append(Label(cx,cy,text,font,offx,offy,lx,ly,r,1,angle,h,anchor))
	def runcommand(self,n,v):
		if n=='g':
			self.linegap=int(v)
		elif n=='loc':
			(lon,lat)=v.split(',')
			self.dlon=float(lon)
			self.dlat=float(lat)
		elif n=='f':
			self.font=v
		elif n=='fx':
			self.fontoffsetx=v
		elif n=='fy':
			self.fontoffsety=v
		elif n=='lx':
			self.lineoffsetx=int(v)
		elif n=='ly':
			self.lineoffsety=int(v)
		elif n=='t':
			self.addlabel(v)
		elif n=='pp':
			self.populatedplace(v)
		elif n=='s':
			self.shadow=int(v)
		elif n=='r':
			self.rotation=int(v)
		elif n=='h':
			self.hidden=int(v)
		elif n=='reset':
			self.reset()
		elif n=='h':
			self.hidden=int(v)
		elif n=='a':
			self.anchor=int(a)
		elif n=='':
			pass
		else:
			print('Unknown label command',n,file=sys.stderr)
			raise ValueError
	def populatedplace(self,name):
		if not self.populateddbf:
			dbf=Dbf(installfile=install.getinstallfile('populated_places.dbf'))
			dbf.selectcfield('adm0_a3','sg')
			dbf.selectcfield('adm1name','admin1name')
			dbf.selectcfield('name','name')
			dbf.selectcfield('longitude','lon')
			dbf.selectcfield('latitude','lat')
			dbf.loadrecords()
			self.populateddbf=dbf
		iscollapse=name[0].islower()
		for i,r in enumerate(self.populateddbf.records):
			rsg=r['sg']
			radmin1name=r['admin1name']
			rname=r['name']
			if iscollapse:
				rsg=Options.collapsename(rsg)
				radmin1name=Options.collapsename(radmin1name)
				rname=Options.collapsename(rname)
			if rname==name or rsg+'.'+rname==name or rsg+'.'+radmin1name+'.'+rname==name:
				self.dlon=float(r['lon'])
				self.dlat=float(r['lat'])
				self.addlabel(r['name'])
	def addcommand(self,t):
		a=t.split('&')
		for o in a:
			if '=' in o:
				(n,v)=o.split('=')
				v=UrlDecoding.unescape(v)
			else: (n,v)=(o,'')
			self.commands.append((n,v))
			self.runcommand(n,v)
	def debug(self):
		for i,c in self.commands:
			print(i,c)
	def printsvg(self,output,rotation,width,height,bzc):
		hc=HemiCleave()
		for l in self.labels:
			dll=DegLonLat(l.dlon,l.dlat)
			plus=ShapePlus.makefromdll(dll,0)
			sphere=SphereShape(plus,rotation)
			hc.cleave(sphere)
			if bzc: bzc.cleave(sphere)
			if sphere.type==NULL_TYPE_SHP: continue
			if bzc:
				flat=bzc.flatten(sphere)
			else:
				flat=sphere.flatten(width,height)
			ux=flat.point.ux
			uy=flat.point.uy

			if l.fontoffx[0].isdigit(): ux2=int(l.fontoffx)
			else: ux2=ux+int(l.fontoffx)

			if l.fontoffy[0].isdigit(): uy2=int(l.fontoffy)
			else: uy2=uy+int(l.fontoffy)

			ux3=ux2+l.lineoffx
			uy3=uy2+l.lineoffy

			if l.hidden&4:
				if l.gap>0:
					a=getangle(ux,uy,ux3,uy3)
					ux4=ux+l.gap*math.cos(a)
					uy4=uy+l.gap*math.sin(a)
					if ux3!=ux4 or uy3!=uy4:
						output.print('<line style="stroke-dasharray:10 3" x1="%d" y1="%d" x2="%d" y2="%d" stroke-opacity="0.8" stroke="#333333"/>'%(ux4,uy4,ux3,uy3))
				elif l.gap==0 :
					if ux!=ux3 or uy!=uy3:
						output.print('<line style="stroke-dasharray:10 3" x1="%d" y1="%d" x2="%d" y2="%d" stroke-opacity="0.8" stroke="#333333"/>'%(ux,uy,ux3,uy3))

			if l.hidden&1:
	# from gradmaker, ff1f1f - ff2a2a - ff3c3c - ff5a5a
				output.print('<circle cx="%d" cy="%d" r="4" fill="#ff2a2a" stroke="#ff1f1f"/>'%(ux,uy))
				output.print('<circle cx="%d" cy="%d" r="2" fill="#ff5a5a" stroke="#ff3c3c"/>'%(ux,uy))

			if l.hidden&2:
				if l.rotation:
					output.print('<text x="0" y="0" style="font:%s;text-anchor:middle" stroke="#ffffff" stroke-width="2" stroke-opacity="0.5" transform="translate(%d,%d) rotate(%d)">%s</text>'%(l.font,ux2+1,uy2+1,l.rotation,l.text))
					output.print('<text x="0" y="0" style="font:%s;text-anchor:middle" transform="translate(%d,%d) rotate(%d)" fill="#000000">%s</text>'%(l.font,ux2,uy2,l.rotation,l.text))
				else:
					anchor=''
					if not l.anchor: anchor=';text-anchor:middle'
					elif l.anchor>0: anchor=';text-anchor:end'
					if l.shadow==0:
						output.print('<text style="font:%s%s" fill="#ffffff" fill-opacity="0.5" x="%d" y="%d">%s</text>'%(l.font,anchor,ux2+1,uy2+1,l.text))
					elif l.shadow==1:
						output.print('<text style="font:%s%s" stroke="#ffffff" stroke-width="2" stroke-opacity="0.5" x="%d" y="%d">%s</text>'%(l.font,anchor,ux2+1,uy2+1,l.text))
					output.print('<text style="font:%s%s" fill="#000000" x="%d" y="%d">%s</text>'%(l.font,anchor,ux2,uy2,l.text))

class UserOptionsPart():
	def __init__(self):
		self.d={}
	def setnv(self,n,v):
		self.d[n]=v
	def addnv(self,n,v):
		simpstrs=('labelfont','spherem','zoomm','hypso','hypso_high','cmdline','version','comment','copyright','title','hypsocache','gsg','landm','spherem')
		simpints=('hypsodim','index','full_index','zoom_index')
		simpbools=('istripelinset','isinsetleft','iszoom','iszoom34','hypsofast','islakes','hypsocutout','isdisputed_labels','isadmin0','isadmin1','island')
		simpfloats=('lon','lat','zoom')
		if n=='width':
			if not v: v=self.d['height']
			self.d['width']=int(v)
		elif n=='height':
			if not v: v=self.d['width']
			self.d['height']=int(v)
		elif n=='bgcolor':
			if not v: v='#b4b4b4'
			self.d[n]=v
		elif n=='center':
			a=v.split(',')
			self.addnv('lon',a[0])
			self.addnv('lat',a[1])
		elif n=='hypso' and not v:
			self.addnv('hypso','hypso-lr_sr_ob_dr')
			self.addnv('hypso_high','hypso-hr_sr_ob_dr')
		elif n in simpstrs:
			self.d[n]=v
		elif n in simpints:
			self.d[n]=int(v)
		elif n in simpfloats:
			self.d[n]=float(v)
		elif n in simpbools:
			self.d[n]=v in ('1','True','Yes','Y','true','yes','y')
		else:
			print('Unknown user option: %s'%n,file=sys.stderr)
			raise ValueError
	def export(self):
		return self.d

class UserOptions():
	def reset(self):
		self.locatormap=UserOptionsPart()
		self.countrymap=UserOptionsPart()
		self.maximap=UserOptionsPart()
		self.euromap=UserOptionsPart()
		self.pointmap=UserOptionsPart()
	def __init__(self):
		self.reset()
	def addstring(self,t):
		a=t.split('&')
		for o in a:
			if '=' in o:
				(n,v)=o.split('=')
				v=UrlDecoding.unescape(v)
			else: (n,v)=(o,'')
			self.addnv(n,v)
	def addnv(self,n,v):
		if n.startswith('locatormap/'): self.locatormap.addnv(n[11:],v)
		elif n.startswith('countrymap/'): self.countrymap.addnv(n[11:],v)
		elif n.startswith('maximap/'): self.maximap.addnv(n[8:],v)
		elif n.startswith('euromap/'): self.euromap.addnv(n[8:],v)
		elif n.startswith('pointmap/'): self.pointmap.addnv(n[9:],v)
		else:
			self.locatormap.addnv(n,v)
			self.countrymap.addnv(n,v)
			self.maximap.addnv(n,v)
			self.euromap.addnv(n,v)
			self.pointmap.addnv(n,v)
	def addoptions(self,options):
		for n in options:
			v=options[n]
			if n.startswith('locatormap/'): self.locatormap.setnv(n[11:],v)
			elif n.startswith('countrymap/'): self.countrymap.setnv(n[11:],v)
			elif n.startswith('maximap/'): self.maximap.setnv(n[8:],v)
			elif n.startswith('euromap/'): self.euromap.setnv(n[8:],v)
			elif n.startswith('pointmap/'): self.pointmap.setnv(n[9:],v)
			else:
				self.locatormap.setnv(n,v)
				self.countrymap.setnv(n,v)
				self.maximap.setnv(n,v)
				self.euromap.setnv(n,v)
				self.pointmap.setnv(n,v)
	def export(self,n):
		if n=='locatormap': return self.locatormap.export()
		if n=='countrymap': return self.countrymap.export()
		if n=='maximap': return self.maximap.export()
		if n=='euromap': return self.euromap.export()
		if n=='pointmap': return self.pointmap.export()
		raise ValueError

def pointmap(output,overrides,labels):
	options={}
	options['comment']=''
	options['copyright']=''
	options['width']=1000
	options['height']=1000
	options['bgcolor']=None
	options['islakes']=True
	options['spherem']='10m'
	options['landm']='110m'
	options['splitlimit']=4
	options['labelfont']='24px sans'
	options['hypso']=None
	options['hypsocache']=None
	options['hypsodim']=options['width']
	options['isadmin0']=False
	options['isadmin1']=True
	options['island']=False
	options['zoom']=2
	options['lon']=0
	options['lat']=0
	allowedoverrides=('comment','copyright','width','height','bgcolor','islakes','spherem','splitlimit','labelfont',
			'hypso','hypsocache','hypsodim', 'isadmin0', 'isadmin1', 'zoom','lon','lat','island','landm','spherem')
	publicfilter=('cmdline','title','comment','version')

	if 'hypso_high' in overrides: overrides['hypso']=overrides['hypso_high']

	if True:
		pub={}
		for n in overrides:
			if n not in publicfilter: continue
			pub[n]=overrides[n]
		options['comment']=dicttostr('vars',pub)

	for n in overrides:
		 if n in allowedoverrides: options[n]=overrides[n]

	width=options['width']
	height=options['height']
	splitlimit=options['splitlimit']
	zoomscale=options['zoom']

	admin=ShpAdmin('admin0-nolakes.shp',[options['spherem']])
	admin.fixantarctica()
	admin.fixrussia()
	admin.fixegypt()
	admin.setccwtypes()
	if options['islakes']: admin.loadlakes()

	if options['isadmin1']: admin.loadadmin1()

	bzc=BoxZoomCleave.makefromzoom(zoomscale,width,height,splitlimit)
	rotation=SphereRotation()
	rotation.set_deglonlat(options['lon'],options['lat'])

	if options['hypso']:
		hypso=Hypso(options['hypsodim'],options['hypsodim'],'./hypsocache',options['hypsocache'])
		if options['hypsocache']==None or not hypso.loadpng_cache():
			if options['hypsocache']==None or not hypso.loadraw_cache():
				hs=HypsoSphere(install.getfilename(options['hypso']+'.pnm',['10m']))
				hs.setcenter(rotation.dlon,rotation.dlat)
				if bzc:
					hs.setzoom(bzc.right,bzc.top,bzc.right*2,bzc.top*2)
				hypso.loadsphere(hs)
				if options['hypsocache']!=None:
					hypso.saveraw_cache(True)
			if bzc: hypso.interpolate()
			p=Palette()
			p.loaddefaults()
			if isverbose_global: print('Indexing colors',file=sys.stderr)
			hypso.indexcolors(p)
			if options['hypsocache']!=None:
				hypso.savepng_cache(True)
		print_hypso_svg(output,width,height,hypso,isfast=False,isgradients=False)
	else: # not hypso
		if zoomscale==1:
			if options['bgcolor']: print_rectangle_svg(output,0,0,width,height,options['bgcolor'],1.0)
			print_roundwater_svg(output,width)
		else:
			print_rectwater_svg(output,width,height)

	if options['isadmin0']:
		cssfull=LAND_SPHERE_CSS
		if options['hypso']: cssfull=BORDER_SPHERE_CSS
		for one in admin.admin0.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull=cssfull,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)

	if options['isadmin1']:
		cssfull=LAND_SPHERE_CSS
		if options['hypso']: cssfull=BORDER_SPHERE_CSS
		for one in admin.admin1.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull=cssfull,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)

	if options['island']:
		cssfull=LAND_SPHERE_CSS
		if options['hypso']: cssfull=BORDER_SPHERE_CSS
		ifile=install.getinstallfile('land.shp',[options['landm']])
		shp=Shp(installfile=ifile)
		shp.loadshapes()
		for one in shp.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull=cssfull,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)
		

	if True and options['islakes'] and not options['hypso']:
		if isverbose_global: print('Drawing lakes sphere shapes',file=sys.stderr)
		pluses=admin.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,
				boxzoomcleave=bzc)

	if labels:
		labels.printsvg(output,rotation,width,height,bzc)

	print_footer_svg(output)
	if True:
		o=Output()
		ishypso=True if options['hypso'] else False
		isgradients=True if zoomscale==1 else False
		print_header_svg(o,width,height,output.csscounts,options['labelfont'],[options['copyright'],options['comment']],
				ishypso=ishypso, isgradients=isgradients)
		output.prepend(o)

def maximap(output,overrides,labels):
	options={}
	options['comment']=''
	options['copyright']=''
	options['width']=1000
	options['height']=1000
	options['bgcolor']=None
	options['islakes']=True
	options['spherem']='10m'
	options['splitlimit']=4
	options['labelfont']='24px sans'
	options['gsg']=None
	options['admin1']=None
	options['isautotrim']=True
	options['hypso']=None
	options['hypsocache']=None
	options['hypsofast']=None
	options['hypsodim']=options['width']
	allowedoverrides=('comment','copyright','width','height','bgcolor','islakes','spherem','splitlimit','labelfont','gsg','admin1',
			'hypso','hypsocache','hypsofast','hypsodim')
	publicfilter=('cmdline','title','comment','version','gsg','admin1')

	if 'hypso_high' in overrides: overrides['hypso']=overrides['hypso_high']

	if True:
		pub={}
		for n in overrides:
			if n not in publicfilter: continue
			pub[n]=overrides[n]
		options['comment']=dicttostr('vars',pub)

	for n in overrides:
		 if n in allowedoverrides: options[n]=overrides[n]

	width=options['width']
	height=options['height']
	splitlimit=options['splitlimit']
	hypsoscale=options['hypsodim']/width

	admin=ShpAdmin('admin0-nolakes.shp',[options['spherem']])
	admin.fixantarctica()
	admin.fixrussia()
	admin.fixegypt()
	admin.setccwtypes()
	if options['islakes']: admin.loadlakes()

	if options['admin1']:
		gsg=options['gsg']
		admin.loadadmin1()
		mshape=admin.admin1.bynickname2(options['admin1'])
		shape0=admin.admin0.bynickname2(gsg)
		for s in admin.admin1.shapes:
			if not s.nickname.startswith(gsg): continue
			s.setdraworder(-1,1)
		shape0.setdraworder(-1,3)
		mshape.setdraworder(-1,3)
	elif options['gsg']:
		mshape=admin.bynickname[options['gsg']]
		mshape.setdraworder(-1,3)
	if not mshape: raise ValueError

	az=AutoZoom()
	az.addshape(mshape)
	if True and options['isautotrim']:
		bzc=az.getboxzoomcleave(width,splitlimit,True)
		width=az.width
		height=az.height
	else:
		bzc=az.getboxzoomcleave(width,splitlimit,False)
	if False:
		print('center',az.center,file=sys.stderr)
		print('spherembr',az.spherembr,file=sys.stderr)
	rotation=az.rotation
	zoomscale=az.zoomfactor

	if options['hypso']:
		hypso=Hypso(int(hypsoscale*width),int(hypsoscale*height),'./hypsocache',options['hypsocache'])
		if options['hypsocache']==None or not hypso.loadpng_cache():
			if options['hypsocache']==None or not hypso.loadraw_cache():
				hs=HypsoSphere(install.getfilename(options['hypso']+'.pnm',['10m']))
				hs.setcenter(rotation.dlon,rotation.dlat)
				if bzc:
					hs.setzoom(bzc.right,bzc.top,bzc.right*2,bzc.top*2)
				hypso.loadsphere(hs)
				if options['hypsocache']!=None:
					hypso.saveraw_cache(True)
			if bzc: hypso.interpolate()
			p=Palette()
			p.loaddefaults()
			if isverbose_global: print('Indexing colors',file=sys.stderr)
			hypso.indexcolors(p)
			if options['hypsocache']!=None:
				hypso.savepng_cache(True)
		print_hypso_svg(output,width,height,hypso,isfast=False,isgradients=False)
	else: # not hypso
		if zoomscale==1:
			if options['bgcolor']: print_rectangle_svg(output,0,0,width,height,options['bgcolor'],1.0)
			print_roundwater_svg(output,width)
		else:
			print_rectwater_svg(output,width,height)

	if True: # draw plain background countries
		for one in admin.shapes:
			one_sphere_print_svg(output,one,0,rotation,width,height,splitlimit,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)
	if True:
		for one in admin.admin1.shapes:
			one_sphere_print_svg(output,one,1,rotation,width,height,splitlimit,cssfull=LAND_SPHERE_CSS,csspatch=PATCH_LAND_SPHERE_CSS,
					boxzoomcleave=bzc)
	if True:
		one_sphere_print_svg(output,mshape,3,rotation,width,height,splitlimit,cssfull=HIGH_LAND_SPHERE_CSS,
				csspatch=PATCH_HIGH_LAND_SPHERE_CSS, boxzoomcleave=bzc)

	if True and options['islakes'] and not options['hypso']:
		if isverbose_global: print('Drawing lakes sphere shapes',file=sys.stderr)
		pluses=admin.getlakes()
		pluses_sphere_print_svg(output,pluses,rotation,width,height,splitlimit, cssfull=WATER_SPHERE_CSS,csspatch=PATCH_WATER_SPHERE_CSS,
				boxzoomcleave=bzc)
		sasi=ShpAdminShapeIntersection()
		sasi.addfromshapes((mshape,),3)
		for l in admin.lakes.shapes:
			sasi.setinside(l)
		borderlakeshapes=sasi.exportlines()
		for plus in borderlakeshapes:
			if plus.type!=POLYLINE_TYPE_SHP: continue
			oneplus_sphere_print_svg(output,plus,rotation,width,height,splitlimit,cssline=HIGH_BORDER_SPHERE_CSS,boxzoomcleave=bzc)

	if labels:
		labels.printsvg(output,rotation,width,height,bzc)

	print_footer_svg(output)
	if True:
		o=Output()
		ishypso=True if options['hypso'] else False
		isgradients=True if zoomscale==1 else False
		print_header_svg(o,width,height,output.csscounts,options['labelfont'],[options['copyright'],options['comment']],
				ishypso=ishypso, isgradients=isgradients)
		output.prepend(o)


def indonesia_options(param):
	if param.endswith('/'): return options_global.basic(param,'indonesia','IDN.IDN',isadmin1=True)
	options={'gsg':'IDN.IDN','isinsetleft':True,'lonlabel_lat':40,'latlabel_lon':175,}
	options['locatormap/title']='Indonesia locator'
	options['countrymap/title']='Indonesia countrymap'
	options['countrymap/zoom']=2

	options_global.handle(options,param)
	return options

def malaysia_options(param):
	if param.endswith('/'): return options_global.basic(param,'malaysia','MYS.MYS',isadmin1=True,isdisputed=True)
	options={'gsg':'MYS.MYS','isinsetleft':True,'lonlabel_lat':-17,'latlabel_lon':170,}
	options['locatormap/title']='Malaysia locator'
	options['countrymap/title']='Malaysia countrymap'
	options['countrymap/zoom']=4
	if param=='malaysia/_disputed':
		options['disputed_border']=[ "PGA.PGA.Spratly Is.", ]
		options['disputed_labels']=[ ("PGA.PGA.Spratly Is.", "Spratly Islands", '24px sans',0,0,'+0','-100',-1,0,0), ]
		options['disputed_circles']=25
	else: options_global.handle(options,param)
	return options

def chile_options(param):
	if param.endswith('/'): return options_global.basic(param,'chile','CHL.CHL',isadmin1=True,isdisputed=True)
	options={'gsg':'CHL.CHL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,}
	options['locatormap/title']='Chile locator'
	options['countrymap/title']='Chile countrymap'
	options['moredots_10m']=[(4,False,[2,3,4,5,6,7])]
	options['countrymap/zoom']=2.5
	options['countrymapdots_10m']=[(4,False,[2,3,4,5,6,7])]
	if param=='chile/_disputed':
		options['moredots_10m']=[]
#		options['disputed']=[ "CHL.CHL.Atacama corridor", ]
		options['disputed_border']=[ "SPI.SPI.Southern Patagonian Ice Field", ]
		options['disputed_labels']=[ ( "SPI.SPI.Southern Patagonian Ice Field", "Southern Patagonian Ice Field", 
				'24px sans',0,1,'-100','+0',20,0,-5), ]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
	else: options_global.handle(options,param)
	return options

def bolivia_options(param):
	if param.endswith('/'): return options_global.basic(param,'bolivia','BOL.BOL',isadmin1=True,isdisputed=False)
	options={'gsg':'BOL.BOL','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Bolivia locator'
	options['countrymap/title']='Bolivia countrymap'
#	options['borderlakes']=['Lago Titicaca']
	options['countrymap/zoom']=5
	if param=='bolivia/_disputed': # nothing right now
#		options['disputed']=[ "CHL.CHL.Atacama corridor",]
		pass
	else: options_global.handle(options,param)
	return options

def peru_options(param):
	if param.endswith('/'): return options_global.basic(param,'peru','PER.PER',isadmin1=True)
	options={'gsg':'PER.PER','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Peru locator'
	options['countrymap/title']='Peru countrymap'
#	options['borderlakes']=['Lago Titicaca']
	options['countrymap/zoom']=4
	options_global.handle(options,param)
	return options

def argentina_options(param):
	if param.endswith('/'): return options_global.basic(param,'argentina','ARG.ARG',isadmin1=True,isdisputed=True)
	options={'gsg':'ARG.ARG','isinsetleft':True,'lonlabel_lat':20,'latlabel_lon':-30,}
	options['locatormap/title']='Argentina locator'
	options['countrymap/title']='Argentina countrymap'
	options['countrymap/zoom']=2.5
	if param=='argentina/_disputed':
		options['countrymap/zoom']=2
		options['disputed']=[ "GB1.FLK.Falkland Is.", "GB1.SGS.S. Georgia", "GB1.SGS.S. Sandwich Is.", ]
		options['disputed_border']=[ "SPI.SPI.Southern Patagonian Ice Field", ]
		options['disputed_labels']=[ 
				( "GB1.FLK.Falkland Is.", "Falkland Islands", '24px sans',0,-1,'+0','-25',-1,0,0), 
				( "GB1.SGS.S. Georgia", "South Georgia", '24px sans',0,1,'-25','+10',-1,0,0), 
				( "GB1.SGS.S. Sandwich Is.", "South Sandwich Islands", '24px sans',0,1,'-25','+10',-1,0,0), 
				( "SPI.SPI.Southern Patagonian Ice Field", "Southern Patagonian Ice Field", '24px sans',0,1,'+0','-15',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def dhekelia_options(param):
	if param.endswith('/'): return options_global.basic(param,'dhekelia')
	options={'gsg':'GB1.ESB','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Dhekelia locator'
	options['countrymap/title']='Dhekelia countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=50
	options['countrymap/lon']=33.4
	options['zoomm']='10m'
	return options

def cyprus_options(param):
	if param.endswith('/'): return options_global.basic(param,'cyprus','CYP.CYP',isadmin1=True,isdisputed=True)
	options={'gsg':'CYP.CYP','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Cyprus locator'
	options['countrymap/title']='Cyprus countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_10m']=[ (30,3,[2]) ]
	options['countrymap/zoom']=50
	options['countrymap/lon']=33.4
	if param=='cyprus/_disputed':
		options['moredots_10m']=[]
		options['disputed']=[ 'CYN.CYN.N. Cyprus', "CNM.CNM.Cyprus U.N. Buffer Zone", ]
		options['disputed_labels']=[ ( 'CYN.CYN.N. Cyprus', 'Northern Cyprus', '24px sans',0,-1,'-50','-100',-12,0,0),
				("CNM.CNM.Cyprus U.N. Buffer Zone", "Cyprus U.N. Buffer Zone", '24px sans',0,-1,'+50','+100',0,0,-20),]
	else: options_global.handle(options,param)
	return options

def cyprusfull_options(param): # this is a manufactured region for european union maps
	if param.endswith('/'): return options_global.basic(param,'cyprusfull')
	options={'gsgs':['cyprusfull'],'isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Cyprusfull locator'
	options['countrymap/title']='Cyprusfull countrymap'
	options['euromap/title']='Cyprus euromap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_50m']=[ (30,3,[0]) ]
	options['euromapdots_50m']= [('cyprusfull',24,False,[0]) ]
#	options['ispartlabels']=True
	return options

def india_options(param):
	if param.endswith('/'): return options_global.basic(param,'india','IND.IND',isadmin1=True,isdisputed=True)
	options={'gsg':'IND.IND','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':55,}
	options['locatormap/title']='India locator'
	options['countrymap/title']='India countrymap'
	options['moredots_10m']=[ (4,False,[2,3,4,5,6,7,8,9,17]), (45,False,[21]) ]
#	options['ispartlabels']=True
	options['countrymap/zoom']=3.125
	options['countrymapdots_10m']=[ (4,False,[2,3,4,5,6,7,8,9,17]) ]
	if param=='india/_disputed':
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		options['locatormap/iszoom']=True
		options['locatormap/zoom']=6.25
		options['zoomlon']=79.5
		options['zoomlat']=31.5
		d=[]
		db=[]
		d.append('IND.IND.Arunachal Pradesh') # india and china
		db.append('IND.IND.Tirpani Valleys') # india and china, border
		db.append('IND.IND.Bara Hotii Valleys') # india and china, border
		db.append('IND.IND.Demchok') # kashmir and china, border, redundant
		db.append('IND.IND.Samdu Valleys') # india and china, border
		d.append('IND.IND.Jammu and Kashmir') # india and pakistan and china, kashmir
		d.append('CH1.CHN.Shaksam Valley') # india pakistan and china
		d.append('CH1.CHN.Aksai Chin') # india and china
		d.append("PAK.PAK.Gilgit-Baltistan") # pakistan india china, north of kashmir, aka Northern Areas
		d.append('KAS.KAS.Siachen Glacier') # pakistan and india
		db.append( "IND.IND.Near Om Parvat") # india nepal, border
		db.append("PAK.PAK.Azad Kashmir") # pakistan india, border-ish
		d.append("IND.IND.Junagadh and Manavadar") # pakistan india
		options['disputed']=d
		options['disputed_border']=db
		options['disputed_labels']=[
				('IND.IND.Arunachal Pradesh', 'Arunachal Pradesh', '24px sans',-45,0,'+90','+125',0,0,0),
				('KAS.KAS.Siachen Glacier', 'Siachen Glacier', '24px sans',0,-1,'490','60',-5,0,-5),
				('CH1.CHN.Aksai Chin', 'Aksai Chin', '24px sans',0,-1,'500','90',-5,0,-5),
				('IND.IND.Jammu and Kashmir', 'Jammu and Kashmir', '24px sans',0,-1,'510','120',-5,0,-5),
				('IND.IND.Demchok', 'Demchok', '24px sans',0,-1,'520','150',-5,0,-5),
				('IND.IND.Samdu Valleys', 'Samdu Valleys', '24px sans',0,-1,'530','180',-5,0,-5),
				('IND.IND.Tirpani Valleys', 'Tirpani Valleys', '24px sans',0,-1,'540','210',-5,0,-5),
				('IND.IND.Bara Hotii Valleys', 'Bara Hotii Valleys', '24px sans',0,-1,'550','240',-5,0,-5),
				("IND.IND.Near Om Parvat", "Near Om Parvat", '24px sans',0,-1,'560','270',-5,0,-5),
				('CH1.CHN.Shaksam Valley', 'Shaksam Valley', '24px sans',0,0,'-10','-55',-5,0,0),
				("PAK.PAK.Gilgit-Baltistan", "Gilgit-Baltistan", '24px sans',0,1,'-100','+0',-5,0,-5),
				("PAK.PAK.Azad Kashmir", "Azad Kashmir", '24px sans',0,1,'-100','+0',-15,0,-5),
				("IND.IND.Junagadh and Manavadar", "Junagadh and Manavadar", '24px sans',67.5,0,'-60','+75',-5,0,0), ]
	elif param=='india/andamanandnicobar':
		options_global.handle(options,param)
		options['admin1dot']=90
	elif param=='india/chandigarh':
		options_global.handle(options,param)
		options['admin1dot']=20
	elif param=='india/dadraandnagarhavelianddamananddiu':
		options_global.handle(options,param)
		options['admin1dot']=40
	elif param=='india/lakshadweep':
		options_global.handle(options,param)
		options['admin1dot']=60
	elif param=='india/puducherry':
		options_global.handle(options,param)
		options['admin1dots']=15
	else: options_global.handle(options,param)
	return options

def china_options(param):
	if param.endswith('/'): return options_global.basic(param,'china','CH1.CHN',isadmin1=True,isdisputed=True)
	options={'gsg':'CH1.CHN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':165,}
	options['locatormap/title']='China locator'
	options['countrymap/title']='China countrymap'
	options['moredots_10m']=[ (4,False,[32,33,42,43,44,45,69]) ]
#	options['ispartlabels']=True
	options['countrymap/zoom']=2
	options['countrymapdots_10m']=[ (4,False,[32,33,42,43,44,45,69]) ]
	if param=='china/_disputed':
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		db=[]
		d=[]
		d.append('IND.IND.Arunachal Pradesh') # india and china
		db.append('IND.IND.Tirpani Valleys') # india and china, border
		db.append('IND.IND.Bara Hotii Valleys') # india and china, border
		db.append('IND.IND.Demchok') # kashmir and china, border, redundant
		db.append('IND.IND.Samdu Valleys') # india and china, border
		d.append('IND.IND.Jammu and Kashmir') # india and pakistan and china, kashmir
		d.append('CH1.CHN.Shaksam Valley') # india pakistan and china
		d.append('CH1.CHN.Aksai Chin') # india and china
		d.append("PAK.PAK.Gilgit-Baltistan") # pakistan india china, north of kashmir, aka Northern Areas
		d.append("BTN.BTN.Bhutan (Chumbi salient)") # china bhutan
		d.append("BTN.BTN.Bhutan (northwest valleys)") # china bhutan
		db.append("CH1.CHN.Paracel Is.") # vietnam china taiwan, border
		db.append("JPN.JPN.Pinnacle Is.") # china taiwan japan, border (senkaku)
		db.append("PGA.PGA.Spratly Is.") # china malaysia philippines taiwan vietnam brunei, border
		db.append("SCR.SCR.Scarborough Reef") # china philippines taiwan, border
		d.append("TWN.TWN.Taiwan") # taiwan china
		options['disputed']=d
		options['disputed_border']=db

		options['disputed_labels']=[
("PAK.PAK.Gilgit-Baltistan", "Gilgit-Baltistan", '24px sans',0,-1,'200','350',0,0,-5),
('CH1.CHN.Shaksam Valley', 'Shaksam Valley', '24px sans',0,-1,'210','380',0,0,-5),
('IND.IND.Jammu and Kashmir', 'Jammu and Kashmir', '24px sans',0,-1,'220','410',0,0,-5),
('CH1.CHN.Aksai Chin', 'Aksai Chin', '24px sans',0,-1,'230','440',0,0,-5),
('IND.IND.Demchok', 'Demchok', '24px sans',0,-1,'240','470',0,0,-5),
('IND.IND.Samdu Valleys', 'Samdu Valleys', '24px sans',0,-1,'250','500',-5,0,-5),
('IND.IND.Tirpani Valleys', 'Tirpani Valleys', '24px sans',0,-1,'260','530',-5,0,-5),
('IND.IND.Bara Hotii Valleys', 'Bara Hotii Valleys', '24px sans',0,-1,'270','560',-5,0,-5),

("BTN.BTN.Bhutan (Chumbi salient)", "Chumbi Salient", '24px sans',0,1,'250','650',-5,0,-5),
("BTN.BTN.Bhutan (northwest valleys)", "Northwest Valleys", '24px sans',0,1,'260','680',-5,0,-5),
('IND.IND.Arunachal Pradesh', 'Arunachal Pradesh', '24px sans',0,1,'270','710',0,0,-5),

("JPN.JPN.Pinnacle Is.", "Pinnacle Islands", '24px sans',0,0,'+30','-40',0,0,0),
("TWN.TWN.Taiwan", "Taiwan",'24px sans',0,-1,'-20','+70',-1,0,0),
("CH1.CHN.Paracel Is.", "Paracel Islands", '24px sans',0,1,'-50','-10',-15,0,-5),
("SCR.SCR.Scarborough Reef", "Scarborough Reef", '24px sans',0,1,'-50','+40',-10,0,-5),
("PGA.PGA.Spratly Is.", "Spratly Islands", '24px sans',0,0,'+0','+60',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def israel_options(param):
	if param.endswith('/'): return options_global.basic(param,'israel','IS1.ISR',isdisputed=True)
	options={'gsg':'IS1.ISR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Israel locator'
	options['countrymap/title']='Israel countrymap'
	options['issubland']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_10m']=[ (30,True,[0]) ]
#	options['borderlakes']=['Dead Sea','_deadseasouth']
	options['countrymap/zoom']=20
	if param=='israel/_disputed':
		options['moredots_10m']=[]
		options['disputed']=['IS1.ISR.Golan Heights', "IS1.PSX.West Bank", ]
# "IS1.ISR.Israel", ]
		options['disputed_border']=[ "IS1.ISR.Shebaa Farms", "IS1.PSX.Gaza", "SYR.SYR.UNDOF Zone", "IS1.ISR.East Jerusalem", 
				"IS1.ISR.No Man's Land (Fort Latrun)", "IS1.ISR.No Man's Land (Jerusalem)", "IS1.ISR.Mount Scopus", ]
		options['disputed_labels']=[
				("IS1.ISR.Shebaa Farms", "Shebaa Farms", '24px sans',0,0,'-30','-50',-5,0,-5),
				("SYR.SYR.UNDOF Zone", "UNDOF Zone", '24px sans',0,-1,'700','200',-5,0,-5),
				('IS1.ISR.Golan Heights', 'Golan Heights', '24px sans',0,-1,'700','300',-5,0,-5),


				("IS1.PSX.West Bank", "West Bank", '24px sans',0,-1,'600','400',-5,0,-5),
				("IS1.ISR.Mount Scopus", "Mount Scopus", '24px sans',0,-1,'600','500',-5,0,-5),
				("IS1.ISR.No Man's Land (Jerusalem)", "No Man's Land (Jerusalem)", '24px sans',0,-1,'600','600',-5,0,-5),

				("IS1.ISR.East Jerusalem", "East Jerusalem", '24px sans',0,1,'-10','+140',-5,0,-5),

#				("IS1.ISR.Israel", "Israel", '24px sans',0,0,'+0','+0',-1,0,0),
				("IS1.ISR.No Man's Land (Fort Latrun)", "No Man's Land (Fort Latrun)", '24px sans',0,1,'-50','-50',-5,0,-5),
				("IS1.PSX.Gaza", "Gaza", '24px sans',0,1,'-50','-50',-5,0,-5),]
	return options

def palestine_options(param):
	if param.endswith('/'): return options_global.basic(param,'palestine','IS1.PSX',isdisputed=True)
	options={'gsg':'IS1.PSX','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Palestine locator'
	options['countrymap/title']='Palestine countrymap'
	options['issubland']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_10m']=[ (30,True,[1]) ]
#	options['borderlakes']=['Dead Sea']
	options['countrymap/zoom']=20
	if param=='palestine/_disputed':
		options['moredots_10m']=[]
		options['disputed']=[ "IS1.PSX.West Bank", ]
		options['disputed_border']=[ "IS1.ISR.East Jerusalem", "IS1.ISR.No Man's Land (Fort Latrun)", "IS1.ISR.No Man's Land (Jerusalem)", 
				"IS1.ISR.Mount Scopus", ]
		options['disputed_labels']=[
				("IS1.ISR.No Man's Land (Fort Latrun)", "No Man's Land (Fort Latrun)", '24px sans',0,1,'-100','-10',-5,0,-5),
				("IS1.ISR.East Jerusalem", "East Jerusalem", '24px sans',0,1,'-120','+30',-5,0,-5),
				("IS1.PSX.West Bank", "West Bank", '24px sans',0,-1,'620','450',-5,0,-5),
				("IS1.ISR.Mount Scopus", "Mount Scopus", '24px sans',0,-1,'620','480',-5,0,-5),
				("IS1.ISR.No Man's Land (Jerusalem)", "No Man's Land (Jerusalem)", '24px sans',0,-1,'620','510',-5,0,-5),
				]
	return options

def lebanon_options(param):
	if param.endswith('/'): return options_global.basic(param,'lebanon','LBN.LBN',isadmin1=True,isdisputed=True)
	options={'gsg':'LBN.LBN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Lebanon locator'
	options['countrymap/title']='Lebanon countrymap'
	options['issubland']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_10m']=[ (30,True,[0]) ]
	options['countrymap/zoom']=20
	if param=='lebanon/_disputed':
		options['moredots_10m']=[]
		options['disputed']=['IS1.ISR.Golan Heights']
		options['disputed_border']=[ "IS1.ISR.Shebaa Farms", ]
		options['disputed_labels']=[
				('IS1.ISR.Golan Heights', 'Golan Heights', '24px sans',0,-1,'+50','-10',-5,0,-5),
				("IS1.ISR.Shebaa Farms", "Shebaa Farms", '24px sans',0,-1,'+50','-10',-5,0,-5), ]
	else: options_global.handle(options,param)
	return options

def ethiopia_options(param):
	if param.endswith('/'): return options_global.basic(param,'ethiopia','ETH.ETH',isadmin1=True)
	options={'gsg':'ETH.ETH','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':-25,}
	options['locatormap/title']='Ethiopia locator'
	options['countrymap/title']='Ethiopia countrymap'
#	options['borderlakes']=['Lake Turkana']
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def southsudan_options(param):
	if param.endswith('/'): return options_global.basic(param,'southsudan','SDS.SDS',isadmin1=True,isdisputed=True)
	options={'gsg':'SDS.SDS','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='South Sudan locator'
	options['countrymap/title']='South Sudan countrymap'
	options['countrymap/zoom']=8
	if param=='southsudan/_disputed':
		options['isinsetleft']=True
		options['locatormap/iszoom']=True
		options['locatormap/zoom']=2.5
		options['disputed']=['SDN.SDN.Abyei', 'KEN.KEN.Ilemi Triangle', ]
		options['disputed_border']=["SDS.SDS.Ilemi Triange", ]
		options['disputed_labels']=[
				('SDN.SDN.Abyei', 'Abyei', '24px sans',0,0,'+0','-50',-1,0,0),
				('KEN.KEN.Ilemi Triangle', 'Ilemi Triangle', '24px sans',0,0,'+10','+80',-20,0,-30),
				("SDS.SDS.Ilemi Triange", "Ilemi Triangle", None ,0,0,'-10','+70',-10,0,-30),
	]
	else: options_global.handle(options,param)
	return options

def somalia_options(param):
	if param.endswith('/'): return options_global.basic(param,'somalia','SOM.SOM',isadmin1=True,isdisputed=True)
	options={'gsg':'SOM.SOM','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,}
	options['locatormap/title']='Somalia locator'
	options['countrymap/title']='Somalia countrymap'
	options['countrymap/zoom']=5
	if param=='somalia/_disputed':
		options['disputed']=['SOL.SOL.Somaliland']
		options['disputed_labels']=[ ('SOL.SOL.Somaliland', 'Somaliland', '24px sans',0,0,'+0','+0',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def kenya_options(param):
	if param.endswith('/'): return options_global.basic(param,'kenya','KEN.KEN',isadmin1=True,isdisputed=True)
	options={'gsg':'KEN.KEN','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,}
	options['locatormap/title']='Kenya locator'
	options['countrymap/title']='Kenya countrymap'
#	options['borderlakes']=['Lake Victoria','Lake Turkana']
	options['countrymap/zoom']=8
	if param=='kenya/_disputed':
		options['disputed']=['KEN.KEN.Ilemi Triangle', ]
		options['disputed_border']=["SDS.SDS.Ilemi Triange", ]
		options['disputed_labels']=[
('KEN.KEN.Ilemi Triangle', 'Ilemi Triangle', '24px sans',0,0,'+30','-50',-20,0,0),
("SDS.SDS.Ilemi Triange", "Ilemi Triangle", None ,0,0,'-10','-60',-10,0,0), ]
	else: options_global.handle(options,param)
	return options

def pakistan_options(param):
	if param.endswith('/'): return options_global.basic(param,'pakistan','PAK.PAK',isadmin1=True,isdisputed=True)
	options={'gsg':'PAK.PAK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Pakistan locator'
	options['countrymap/title']='Pakistan countrymap'
	options['countrymap/zoom']=5
	if param=='pakistan/_disputed':
		d=[]
		db=[]
		d.append('IND.IND.Jammu and Kashmir') # india and pakistan and china, kashmir
		d.append('CH1.CHN.Shaksam Valley') # india pakistan and china
		d.append("PAK.PAK.Gilgit-Baltistan") # pakistan india china, north of kashmir, aka Northern Areas
		d.append('KAS.KAS.Siachen Glacier') # pakistan and india
		db.append("PAK.PAK.Azad Kashmir") # pakistan india, border-ish
		d.append("IND.IND.Junagadh and Manavadar") # pakistan india
		options['disputed']=d
		options['disputed_border']=db
		options['disputed_labels']=[
				('CH1.CHN.Shaksam Valley', 'Shaksam Valley', '24px sans',0,-1,'-20','-50',-5,0,0),
				("PAK.PAK.Gilgit-Baltistan", "Gilgit-Baltistan", '24px sans',0,1,'-100','-50',-5,0,0),
				('KAS.KAS.Siachen Glacier', 'Siachen Glacier', '24px sans',0,-1,'-10','-30',-5,0,0),

				('IND.IND.Jammu and Kashmir', 'Jammu and Kashmir', '24px sans',0,0,'+80','+110',-5,0,0),
				("PAK.PAK.Azad Kashmir", "Azad Kashmir", '24px sans',0,1,'-125','-30',-25,0,-5),

				("IND.IND.Junagadh and Manavadar", "Junagadh and Manavadar", '24px sans',0,0,'+30','-50',-5,0,0),
		]
	else: options_global.handle(options,param)
	return options

def malawi_options(param):
	if param.endswith('/'): return options_global.basic(param,'malawi','MWI.MWI',isadmin1=True)
	options={'gsg':'MWI.MWI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Malawi locator'
	options['countrymap/title']='Malawi countrymap'
	options['locatormap/iszoom']=False
#	options['borderlakes']=['Lake Malawi']
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def unitedrepublicoftanzania_options(param):
	if param.endswith('/'): return options_global.basic(param,'unitedrepublicoftanzania',isadmin1=True)
	options={'gsg':'TZA.TZA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='United Republic of Tanzania locator'
	options['countrymap/title']='United Republic of Tanzania countrymap'
#	options['borderlakes']=['Lake Victoria','Lake Malawi']
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def syria_options(param):
	if param.endswith('/'): return options_global.basic(param,'syria','SYR.SYR',isadmin1=True,isdisputed=True)
	options={'gsg':'SYR.SYR','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Syria locator'
	options['countrymap/title']='Syria countrymap'
	options['countrymap/zoom']=10
	if param=='syria/_disputed':
		options['disputed_border']=[ "IS1.ISR.Shebaa Farms", "SYR.SYR.UNDOF Zone", ]
		options['disputed_labels']=[
				("IS1.ISR.Shebaa Farms", "Shebaa Farms", '24px sans',0,1,'-50','-10',-5,0,-5),
				("SYR.SYR.UNDOF Zone", "UNDOF Zone", '24px sans',0,1,'-50','+10',-5,0,-5), ]
	else: options_global.handle(options,param)
	return options

def somaliland_options(param):
	if param.endswith('/'): return options_global.basic(param,'somaliland')
	options={'gsg':'SOL.SOL','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Somaliland locator'
	options['countrymap/title']='Somaliland countrymap'
	options['countrymap/zoom']=10
	return options

def france_options(param):
	if param.endswith('/'): return options_global.basic(param,'france','FR1.FRA',isadmin1=True,extra=('_disputed1','_disputed2'))
	options={'gsg':'FR1.FRA','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='France locator'
	options['countrymap/title']='France countrymap'
	options['euromap/title']='France euromap'
	options['locatormap/iszoom']=False
	options['issubland']=False
	options['moredots_10m']=[ (4,False,[3,4,5,6,7,19,20,8,9,10]) ]
	europarts_10m=[1,11,12,13,14,15,16,17,18,21]
	options['tripelboxes']=[[0],[3,4,5,6,7,19,20],[8,9,10],europarts_10m]
	options['centerindices_10m']=europarts_10m
	options['countrymap/zoom']=8
	if param=='france/_disputed1':
		options['countrymap/zoom']=1
		options['countrymap/lon']=-115
		options['countrymap/lat']=-15
		options['disputed_circles']=20
		options['disputed_border']=[ "FR1.NCL.Matthew and Hunter Is.", 'FR1.FRA.Lawa Headwaters']
		options['disputed_labels']=[
				('FR1.FRA.Lawa Headwaters','Lawa Headwaters', '24px sans',0,1,'-20','+40',-1,0,0),
				("FR1.NCL.Matthew and Hunter Is.", "Matthew and Hunter Is.", '24px sans',0,-1,'+30','+0',-1,0,0), ]
	elif param=='france/_disputed2':
		options['countrymap/zoom']=4
		options['countrymap/lon']=50
		options['countrymap/lat']=-20
		options['disputed_circles']=20
		options['disputed_border']=[ "FR1.ATF.Bassas da India", "FR1.ATF.Europa Island", "FR1.ATF.Glorioso Is.", 
				"FR1.ATF.Juan De Nova I.", "FR1.ATF.Tromelin I.", "FR1.FRA.Mayotte",]
		options['disputed_labels']=[
				("FR1.ATF.Glorioso Is.", "Glorioso Is.", '24px sans',0,0,'+0','-35',-1,0,0),
				("FR1.FRA.Mayotte", "Mayotte", '24px sans',0,0,'+0','+50',-1,0,0),
				("FR1.ATF.Tromelin I.", "Tromelin I.", '24px sans',0,0,'+0','-35',-1,0,0),
				("FR1.ATF.Juan De Nova I.", "Juan De Nova I.", '24px sans',0,0,'+0','+50',-1,0,0),
				("FR1.ATF.Bassas da India", "Bassas da India", '24px sans',0,0,'+0','-35',-1,0,0),
				("FR1.ATF.Europa Island", "Europa Island", '24px sans',0,0,'+0','+50',-1,0,0),
		]
	else: options_global.handle(options,param)
	return options

def suriname_options(param):
	if param.endswith('/'): return options_global.basic(param,'suriname','SUR.SUR',isadmin1=True,isdisputed=True)
	options={'gsg':'SUR.SUR','isinsetleft':False,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Suriname locator'
	options['countrymap/title']='Suriname countrymap'
	options['countrymap/zoom']=16
	if param=='suriname/_disputed':
		options['disputed']=['FR1.FRA.Lawa Headwaters','GUY.GUY.Courantyne Headwaters']
		options['disputed_labels']=[
				('FR1.FRA.Lawa Headwaters', 'Lawa Headwaters', '24px sans',0,0,'+0','+110',-1,0,0),
				('GUY.GUY.Courantyne Headwaters', 'Courantyne Headwaters', '24px sans',0,0,'+0','+170',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def guyana_options(param):
	if param.endswith('/'): return options_global.basic(param,'guyana','GUY.GUY',isadmin1=True,isdisputed=True)
	options={'gsg':'GUY.GUY','isinsetleft':False,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Guyana locator'
	options['countrymap/title']='Guyana countrymap'
	options['countrymap/zoom']=10
	if param=='guyana/_disputed':
		options['disputed']=['GUY.GUY.Courantyne Headwaters', "GUY.GUY.West of Essequibo River", ]
		options['disputed_labels']=[
				('GUY.GUY.Courantyne Headwaters', 'Courantyne Headwaters', '24px sans',0,-1,'+55','+0',-1,0,0),
				("GUY.GUY.West of Essequibo River", "West of Essequibo River", '24px sans',0,1,'-40','+0',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def southkorea_options(param):
	if param.endswith('/'): return options_global.basic(param,'southkorea','KOR.KOR',isadmin1=True,isdisputed=True)
	options={'gsg':'KOR.KOR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='South Korea locator'
	options['countrymap/title']='South Korea countrymap'
	options['countrymap/zoom']=16
	if param=='southkorea/_disputed':
		options['disputed_circles']=20
		options['disputed']=[ "KOR.KOR.Korean Demilitarized Zone (south)", "PRK.PRK.Korean Demilitarized Zone (north)", ]
		options['disputed_border']=[ "KOR.KOR.Dokdo", "KOR.KOR.Korean islands under UN jurisdiction", ]
		options['disputed_labels']=[
				("KOR.KOR.Korean Demilitarized Zone (south)", "Korean Demilitarized Zone (south)", '24px sans',0,0,'+0','+0',-1,0,0),
				("PRK.PRK.Korean Demilitarized Zone (north)", "Korean Demilitarized Zone (north)", '24px sans',0,0,'+0','-30',-1,0,0),
				("KOR.KOR.Dokdo", "Dokdo", '24px sans',0,0,'+0','+50',-1,0,0),
				("KOR.KOR.Korean islands under UN jurisdiction", "Korean islands under UN jurisdiction", '24px sans',0,0,'+0','+50',-1,0,0),
				]
	else: options_global.handle(options,param)
	return options

def northkorea_options(param):
	if param.endswith('/'): return options_global.basic(param,'northkorea','PRK.PRK',isadmin1=True,isdisputed=True)
	options={'gsg':'PRK.PRK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='North Korea locator'
	options['countrymap/title']='North Korea countrymap'
	options['countrymap/zoom']=16
	if param=='northkorea/_disputed':
		options['disputed']=[ "KOR.KOR.Korean Demilitarized Zone (south)", "PRK.PRK.Korean Demilitarized Zone (north)", ]
		options['disputed_border']=[ "KOR.KOR.Korean islands under UN jurisdiction", ]
		options['disputed_labels']=[
				("KOR.KOR.Korean Demilitarized Zone (south)", "Korean Demilitarized Zone (south)", '24px sans',0,0,'+0','+0',-1,0,0),
				("PRK.PRK.Korean Demilitarized Zone (north)", "Korean Demilitarized Zone (north)", '24px sans',0,0,'+0','-30',-1,0,0),
				("KOR.KOR.Korean islands under UN jurisdiction", "Korean islands under UN jurisdiction", '24px sans',0,0,'+0','+50',-1,0,0),
		]
		options['disputed_circles']=20
	else: options_global.handle(options,param)
	return options

def morocco_options(param):
	if param.endswith('/'): return options_global.basic(param,'morocco','MAR.MAR',isadmin1=True,isdisputed=True)
	options={'gsg':'MAR.MAR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Morocco locator'
	options['countrymap/title']='Morocco countrymap'
	options['countrymap/zoom']=5
	if param=='morocco/_disputed':
		options['disputed']=['MAR.MAR.W. Sahara']
	#	"SAH.SAH.W. Sahara", # morocco wsahara, this is usa's version of wsahara
		options['disputed_border']=[ "ESP.ESP.Ceuta", "ESP.ESP.Isla del Perejil", "ESP.ESP.Islas Chafarinas", 
				"ESP.ESP.Melilla", "ESP.ESP.Penon de Alhucemas", "ESP.ESP.Peñón de Vélez de la Gomera", ]
		options['disputed_labels']=[
				("ESP.ESP.Ceuta", "Ceuta", '24px sans',0,1,'400','200',-5,0,-5),
				("ESP.ESP.Isla del Perejil", "Isla del Perejil", '24px sans',0,1,'410','250',-5,0,-5),
				("ESP.ESP.Peñón de Vélez de la Gomera", "Peñón de Vélez de la Gomera", '24px sans',0,1,'420','300',-5,0,-5),
				("ESP.ESP.Penon de Alhucemas", "Peñón de Alhucemas", '24px sans',0,1,'430','350',-5,0,-5),
				("ESP.ESP.Melilla", "Melilla", '24px sans',0,1,'440','400',-5,0,-5),
				("ESP.ESP.Islas Chafarinas", "Islas Chafarinas", '24px sans',0,1,'450','450',-5,0,-5),
				('MAR.MAR.W. Sahara', 'Western Sahara', '24px sans',0,0,'+130','+0',-1,0,0),
				]
	else: options_global.handle(options,param)
	return options

def westernsahara_options(param):
	if param.endswith('/'): return options_global.basic(param,'westernsahara','SAH.SAH',isdisputed=True)
	options={'gsg':'SAH.SAH','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Western Sahara locator'
	options['countrymap/title']='Western Sahara countrymap'
	options['countrymap/zoom']=10
	if 'disputed' in param:
		options['disputed']=['MAR.MAR.W. Sahara']
		options['disputed_labels']=[ ('MAR.MAR.W. Sahara', 'Western Sahara','24px sans',0,1,'-180','-30',-1,0,0), ]
	#	"SAH.SAH.W. Sahara", # morocco wsahara, this is usa's version of wsahara
	return options

def costarica_options(param):
	if param.endswith('/'): return options_global.basic(param,'costarica','CRI.CRI',isadmin1=True)
	options={'gsg':'CRI.CRI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Costa Rica locator'
	options['countrymap/title']='Costa Rica countrymap'
	options['moredots_10m']=[ (4,False,[2]) ]
	options['countrymap/zoom']=16
	options['countrymapdots_10m']=[ (4,False,[2]) ]
	options_global.handle(options,param)
	return options

def nicaragua_options(param):
	if param.endswith('/'): return options_global.basic(param,'nicaragua','NIC.NIC',isadmin1=True,isdisputed=True)
	options={'gsg':'NIC.NIC','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Nicaragua locator'
	options['countrymap/title']='Nicaragua countrymap'
	options['countrymap/zoom']=16
	if param=='nicaragua/_disputed':
		options['countrymap/zoom']=4
		options['disputed_border']=[ "BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "SER.SER.Serranilla Bank", ]
		options['disputed_labels']=[
				("BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "Bajo Nuevo Bank", '24px sans',0,1,'+0','-40',-1,0,-5),
				("SER.SER.Serranilla Bank", "Serranilla Bank", '24px sans',0,-1,'+0','+50',-1,0,-5), ]
		options['disputed_circles']=20
	else: options_global.handle(options,param)
	return options

def republicofthecongo_options(param):
	if param.endswith('/'): return options_global.basic(param,'republicofthecongo','COG.COG',isadmin1=True)
	options={'gsg':'COG.COG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Republic of the Congo locator'
	options['countrymap/title']='Republic of the Congo countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def democraticrepublicofthecongo_options(param):
	if param.endswith('/'): return options_global.basic(param,'democraticrepublicofthecongo','COD.COD',isadmin1=True)
	options={'gsg':'COD.COD','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Democratic Republic of the Congo locator'
	options['countrymap/title']='Democratic Republic of the Congo countrymap'
#	options['borderlakes']=['Lac Moeru','Lake Kivu','Lake Edward','Lake Albert']
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def bhutan_options(param):
	if param.endswith('/'): return options_global.basic(param,'bhutan','BTN.BTN',isadmin1=True,isdisputed=True)
	options={'gsg':'BTN.BTN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Bhutan locator'
	options['countrymap/title']='Bhutan countrymap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	if param=='bhutan/_disputed':
		options['disputed']=[ "BTN.BTN.Bhutan (Chumbi salient)", "BTN.BTN.Bhutan (northwest valleys)", ]
		options['disputed_labels']=[
				("BTN.BTN.Bhutan (Chumbi salient)", "Chumbi Salient", '24px sans',0,-1,'+20','+15',-1,0,0),
				("BTN.BTN.Bhutan (northwest valleys)", "Northwest Valleys", '24px sans',0,0,'+0','-30',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def ukraine_options(param):
	if param.endswith('/'): return options_global.basic(param,'ukraine','UKR.UKR',isadmin1=True,isdisputed=True)
	options={'gsg':'UKR.UKR','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Ukraine locator'
	options['countrymap/title']='Ukraine countrymap'
	options['countrymap/zoom']=8
	if param=='ukraine/_disputed':
		options['disputed']=['RUS.RUS.Crimea','UKR.UKR.Donbass']
		options['disputed_labels']=[
				('RUS.RUS.Crimea', 'Crimea', '24px sans',0,0,'+50','+60',-1,0,0),
				('UKR.UKR.Donbass', 'Donbass', '24px sans',0,-1,'+15','+25',-1,0,0),]
		options['locatormap/iszoom']=True
		options['locatormap/iszoom34']=True
	else: options_global.handle(options,param)
	return options

def belarus_options(param):
	if param.endswith('/'): return options_global.basic(param,'belarus','BLR.BLR',isadmin1=True)
	options={'gsg':'BLR.BLR','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Belarus locator'
	options['countrymap/title']='Belarus countrymap'
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def namibia_options(param):
	if param.endswith('/'): return options_global.basic(param,'namibia','NAM.NAM',isadmin1=True)
	options={'gsg':'NAM.NAM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Namibia locator'
	options['countrymap/title']='Namibia countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def southafrica_options(param):
	if param.endswith('/'): return options_global.basic(param,'southafrica','ZAF.ZAF',isadmin1=True)
	options={'gsg':'ZAF.ZAF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='South Africa locator'
	options['countrymap/title']='South Africa countrymap'
	options['moredots_10m']=[ (4,True,[2,3]) ]
	options['countrymap/zoom']=4
	options['countrymapdots_10m']=[ (12,True,[2,3]) ]
	options_global.handle(options,param)
	return options

def saintmartin_options(param):
	if param.endswith('/'): return options_global.basic(param,'saintmartin')
	options={'gsg':'FR1.MAF','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Martin locator'
	options['countrymap/title']='Saint Martin countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=64
	options['zoomm']='10m'
#	options['countrymapdots_10m']=[ (20,3,[0]) ]
	return options

def sintmaarten_options(param):
	if param.endswith('/'): return options_global.basic(param,'sintmaarten')
	options={'gsg':'NL1.SXM','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Sint Maarten locator'
	options['countrymap/title']='Sint Maarten countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=64
	options['zoomm']='10m'
	return options

def oman_options(param):
	if param.endswith('/'): return options_global.basic(param,'oman','OMN.OMN',isadmin1=True)
	options={'gsg':'OMN.OMN','isinsetleft':False,'lonlabel_lat':-10,'latlabel_lon':50,}
	options['locatormap/title']='Oman locator'
	options['countrymap/title']='Oman countrymap'
#	options['ispartlabels']=True
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def uzbekistan_options(param):
	if param.endswith('/'): return options_global.basic(param,'uzbekistan','UZB.UZB',isadmin1=True)
	options={'gsg':'UZB.UZB','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Uzbekistan locator'
	options['countrymap/title']='Uzbekistan countrymap'
#	options['borderlakes']=['Aral Sea','Sarygamysh Köli']
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def kazakhstan_options(param):
	if param.endswith('/'): return options_global.basic(param,'kazakhstan','KA1.KAZ',isadmin1=True)
	options={'gsg':'KA1.KAZ','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Kazakhstan locator'
	options['countrymap/title']='Kazakhstan countrymap'
	options['countrymap/zoom']=4
#	"KA1.KAB.Baykonur", # kazakhstan russia, dispute appears over?
	options_global.handle(options,param)
	return options

def tajikistan_options(param):
	if param.endswith('/'): return options_global.basic(param,'tajikistan','TJK.TJK',isadmin1=True)
	options={'gsg':'TJK.TJK','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Tajikistan locator'
	options['countrymap/title']='Tajikistan countrymap'
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def lithuania_options(param):
	if param.endswith('/'): return options_global.basic(param,'lithuania','LTU.LTU',isadmin1=True)
	options={'gsg':'LTU.LTU','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Lithuania locator'
	options['countrymap/title']='Lithuania countrymap'
	options['euromap/title']='Lithuania euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=25
	options_global.handle(options,param)
	return options

def brazil_options(param):
	if param.endswith('/'): return options_global.basic(param,'brazil','BRA.BRA',isadmin1=True,isdisputed=True)
	options={'gsg':'BRA.BRA','isinsetleft':False,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Brazil locator'
	options['countrymap/title']='Brazil countrymap'
	options['moredots_10m']=[ (6,False,[27,28,36]) ]
#	options['borderlakes']=['Itaipú Reservoir']
	options['countrymap/zoom']=2.5
	options['countrymapdots_10m']=[ (6,False,[27,28,36]) ]
	if param=='brazil/_disputed':
		options['disputed_border']=[ "BRI.BRI.Brazilian Island", "BRA.BRA.Corner of Artigas", ]
		options['disputed_labels']=[
			("BRI.BRI.Brazilian Island", "Brazilian Island", '24px sans',0,0,'+0','-20',-1,0,0),
			("BRA.BRA.Corner of Artigas", "Corner of Artigas", '24px sans',0,0,'+0','+35',-1,0,0),]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
	else: options_global.handle(options,param)
	return options

def uruguay_options(param):
	if param.endswith('/'): return options_global.basic(param,'uruguay','URY.URY',isadmin1=True,isdisputed=True)
	options={'gsg':'URY.URY','isinsetleft':False,'lonlabel_lat':20,'latlabel_lon':-30,}
	options['locatormap/title']='Uruguay locator'
	options['countrymap/title']='Uruguay countrymap'
	options['countrymap/zoom']=16
	if param=='uruguay/_disputed':
		options['disputed_circles']=10
		options['disputed_border']=[ "BRI.BRI.Brazilian Island", ]
		options['disputed']=["BRA.BRA.Corner of Artigas", ]
		options['disputed_labels']=[
			("BRI.BRI.Brazilian Island", "Brazilian Island", '24px sans',0,0,'+0','-20',-1,0,0),
			("BRA.BRA.Corner of Artigas", "Corner of Artigas", '24px sans',0,0,'+0','+35',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def mongolia_options(param):
	if param.endswith('/'): return options_global.basic(param,'mongolia','MNG.MNG',isadmin1=True)
	options={'gsg':'MNG.MNG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Mongolia locator'
	options['countrymap/title']='Mongolia countrymap'
	options['countrymap/zoom']=4
	options_global.handle(options,param)
	return options

def russia_options(param):
	if param.endswith('/'): return options_global.basic(param,'russia','RUS.RUS',isadmin1=True,isdisputed=True)
	options={'gsg':'RUS.RUS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-178,}
	options['locatormap/title']='Russia locator'
	options['countrymap/title']='Russia countrymap'
	options['lon']=109
	options['moredots_10m']=[ (4,False,[137]) ]
	options['tripelboxes_10m']=[ [0,1,2], [70] ]
#	options['ispartlabels']=True
#	options['borderlakes']=['Pskoyskoye Ozero', 'Lake Peipus','Aral Sea']
	options['countrymap/zoom']=1.4
	options['countrymap/lon']=100
	if param=='russia/_disputed':
		options['disputed_circles']=20
		options['moredots_10m']=[]
	#	"KA1.KAB.Baykonur", # kazakhstan russia, dispute appears over?
		options['disputed_border']=['RUS.RUS.Kuril Is.',
				'RUS.RUS.Crimea'] # Crimea is best handled as a border even though it isn't
		options['disputed_labels']=[
				('RUS.RUS.Kuril Is.', 'Kuril Islands', '24px sans',0,0,'+10','+65',-1,0,0),
				('RUS.RUS.Crimea', 'Crimea', '24px sans',0,0,'+0','-45',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def czechia_options(param):
	if param.endswith('/'): return options_global.basic(param,'czechia','CZE.CZE',isadmin1=True)
	options={'gsg':'CZE.CZE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Czechia locator'
	options['countrymap/title']='Czechia countrymap'
	options['euromap/title']='Czechia euromap'
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def germany_options(param):
	if param.endswith('/'): return options_global.basic(param,'germany','DEU.DEU',isadmin1=True)
	options={'gsg':'DEU.DEU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Germany locator'
	options['countrymap/title']='Germany countrymap'
	options['euromap/title']='Germany euromap'
	options['countrymap/zoom']=12.5
	options_global.handle(options,param)
	return options

def estonia_options(param):
	if param.endswith('/'): return options_global.basic(param,'estonia','EST.EST',isadmin1=True)
	options={'gsg':'EST.EST','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Estonia locator'
	options['countrymap/title']='Estonia countrymap'
	options['euromap/title']='Estonia euromap'
	options['locatormap/iszoom']=True
	options['centerdot']=(25,True)
#	options['borderlakes']=['Pskoyskoye Ozero', 'Lake Peipus']
	options['countrymap/zoom']=25
	options_global.handle(options,param)
	return options

def latvia_options(param):
	if param.endswith('/'): return options_global.basic(param,'latvia','LVA.LVA',isadmin1=True)
	options={'gsg':'LVA.LVA','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Latvia locator'
	options['countrymap/title']='Latvia countrymap'
	options['euromap/title']='Latvia euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def norway_options(param):
	if param.endswith('/'): return options_global.basic(param,'norway','NOR.NOR',isadmin1=True)
	options={'gsg':'NOR.NOR','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Norway locator'
	options['countrymap/title']='Norway countrymap'
	options['centerindices_10m']=[0,96]
	options['moredots_10m']=[ (4,False,[74,97]) ]
	options['zoomdots_10m']=[ (10,False,[74,97]) ]
	options['locatormap/iszoom']=True
	options['tripelboxes_10m']=[ [0,1,2,86],[97] ]
	options['countrymap/zoom']=4
	options['countrymapdots_10m']=[ (10,False,[74]) ]
	options_global.handle(options,param)
	return options

def sweden_options(param):
	if param.endswith('/'): return options_global.basic(param,'sweden','SWE.SWE',isadmin1=True)
	options={'gsg':'SWE.SWE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Sweden locator'
	options['countrymap/title']='Sweden countrymap'
	options['euromap/title']='Sweden euromap'
	options['countrymap/zoom']=6.25
	options_global.handle(options,param)
	return options

def finland_options(param):
	if param.endswith('/'): return options_global.basic(param,'finland','FI1.FIN',isadmin1=True)
	options={'gsg':'FI1.FIN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Finland locator'
	options['countrymap/title']='Finland countrymap'
	options['euromap/title']='Finland euromap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def vietnam_options(param):
	if param.endswith('/'): return options_global.basic(param,'vietnam','VNM.VNM',isadmin1=True,isdisputed=True)
	options={'gsg':'VNM.VNM','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':165,}
	options['locatormap/title']='Vietnam locator'
	options['countrymap/title']='Vietnam countrymap'
	options['countrymap/zoom']=6.25
	if param=='vietnam/_disputed':
		options['countrymap/zoom']=4
		options['disputed_circles']=20
		options['disputed_border']=[ "CH1.CHN.Paracel Is.", "PGA.PGA.Spratly Is.", ]
		options['disputed_labels']=[
				("CH1.CHN.Paracel Is.", "Paracel Islands", '24px sans',0,0,'+0','-60',-1,0,0),
				("PGA.PGA.Spratly Is.", "Spratly Islands", '24px sans',0,0,'+0','+110',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def cambodia_options(param):
	if param.endswith('/'): return options_global.basic(param,'cambodia','KHM.KHM',isadmin1=True)
	options={'gsg':'KHM.KHM','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':160,}
	options['locatormap/title']='Cambodia locator'
	options['countrymap/title']='Cambodia countrymap'
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def luxembourg_options(param):
	if param.endswith('/'): return options_global.basic(param,'luxembourg','LUX.LUX',isadmin1=True)
	options={'gsg':'LUX.LUX','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Luxembourg locator'
	options['countrymap/title']='Luxembourg countrymap'
	options['euromap/title']='Luxembourg euromap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['moredots_10m']=[ (30,True,[0]) ]
	options['euromapdots_50m']= [('LUX.LUX',24,False,[0]) ]
	options['countrymap/zoom']=80
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def unitedarabemirates_options(param):
	if param.endswith('/'): return options_global.basic(param,'unitedarabemirates','ARE.ARE',isadmin1=True,isdisputed=True)
	options={'gsg':'ARE.ARE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='United Arab Emirates locator'
	options['countrymap/title']='United Arab Emirates countrymap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	if param=='unitedarabemirates/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "IRN.IRN.Abu Musa I.", ]
		options['disputed_labels']=[ ("IRN.IRN.Abu Musa I.", "Abu Musa Island", '24px sans',0,0,'+0','-40',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def belgium_options(param):
	if param.endswith('/'): return options_global.basic(param,'belgium','BEL.BEL',isadmin1=True)
	options={'gsg':'BEL.BEL','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Belgium locator'
	options['countrymap/title']='Belgium countrymap'
	options['euromap/title']='Belgium euromap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_10m']=[ (25,True,[0]) ]
	options['countrymap/zoom']=40
	options_global.handle(options,param)
	return options

def georgia_options(param):
	if param.endswith('/'): return options_global.basic(param,'georgia','GEO.GEO',isdisputed=True)
	options={'gsg':'GEO.GEO','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,}
	options['locatormap/title']='Georgia locator'
	options['countrymap/title']='Georgia countrymap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=16
	if 'disputed' in param:
		options['disputed']=['GEO.B35.Abkhazia','GEO.B37.South Ossetia']
		options['disputed_labels']=[
				('GEO.B35.Abkhazia', 'Abkhazia', '24px sans',0,0,'+0','-85',-1,0,0),
				('GEO.B37.South Ossetia', 'South Ossetia', '24px sans',0,0,'+0','+75',-1,0,0),]
	return options

def northmacedonia_options(param):
	if param.endswith('/'): return options_global.basic(param,'northmacedonia','MKD.MKD',isadmin1=True)
	options={'gsg':'MKD.MKD','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Macedonia locator'
	options['countrymap/title']='Macedonia countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def albania_options(param):
	if param.endswith('/'): return options_global.basic(param,'albania','ALB.ALB',isadmin1=True)
	options={'gsg':'ALB.ALB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Albania locator'
	options['countrymap/title']='Albania countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def azerbaijan_options(param):
	if param.endswith('/'): return options_global.basic(param,'azerbaijan','AZE.AZE',isadmin1=True,isdisputed=True)
	options={'gsg':'AZE.AZE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Azerbaijan locator'
	options['countrymap/title']='Azerbaijan countrymap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	if param=='azerbaijan/_disputed':
		options['disputed']=[ "AZE.AZE.Artsakh", ]
		options['disputed_labels']=[ ("AZE.AZE.Artsakh", "Artsakh", '24px sans',0,-1,'+30','+0',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def kosovo_options(param):
	if param.endswith('/'): return options_global.basic(param,'kosovo','KOS.KOS',isadmin1=True,isdisputed=True)
	options={'gsg':'KOS.KOS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Kosovo locator'
	options['countrymap/title']='Kosovo countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=32
	if param=='kosovo/_disputed':
		options['disputed']=["KOS.KOS.Kosovo", ]
	else: options_global.handle(options,param)
	return options

def turkey_options(param):
	if param.endswith('/'): return options_global.basic(param,'turkey','TUR.TUR',isadmin1=True)
	options={'gsg':'TUR.TUR','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Turkey locator'
	options['countrymap/title']='Turkey countrymap'
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def spain_options(param):
	if param.endswith('/'): return options_global.basic(param,'spain','ESP.ESP',isadmin1=True,isdisputed=True)
	options={'gsg':'ESP.ESP','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Spain locator'
	options['countrymap/title']='Spain countrymap'
	options['euromap/title']='Spain euromap'
	options['moredots_10m']=[(10,False,[1]),(24,False,[5])]
	options['euromapdots_50m']=[('ESP.ESP',56,False,[5])]
#	options['ispartlabels']=True
	options['countrymap/zoom']=5
	if param=='spain/_disputed':
		options['countrymap/zoom']=12.5
		options['moredots_10m']=[]
		options['disputed_circles']=10
		options['disputed']=[ "ESP.ESP.Olivenza", ]
		options['disputed_border']=[ "ESP.ESP.Ceuta", "ESP.ESP.Isla del Perejil", "ESP.ESP.Islas Chafarinas", 
				"ESP.ESP.Melilla", "ESP.ESP.Penon de Alhucemas", "ESP.ESP.Peñón de Vélez de la Gomera", "GB1.GIB.Gibraltar", ]
		options['disputed_labels']=[ ("ESP.ESP.Olivenza",'Olivenza','24px sans',0,-1,'+25','+0',-1,0,0),
				("ESP.ESP.Ceuta", "Ceuta",'24px sans',0,1,'-75','+50',10,0,-5),
				("ESP.ESP.Isla del Perejil", "Isla del Perejil",'24px sans',0,1,'-125','+0',10,0,-5),
				("ESP.ESP.Islas Chafarinas", "Islas Chafarinas",'24px sans',0,1,'-150','+175',10,0,-5),
				("ESP.ESP.Melilla", "Melilla",'24px sans',0,1,'-125','+125',10,0,-5),
				("ESP.ESP.Penon de Alhucemas", "Peñón de Alhucemas",'24px sans',0,1,'-150','+100',10,0,-5),
				("ESP.ESP.Peñón de Vélez de la Gomera", "Peñón de Vélez de la Gomera",'24px sans',0,1,'-125','+25',10,0,-5),
				("GB1.GIB.Gibraltar", "Gibraltar",'24px sans',0,1,'-125','-25',10,0,-5), ]
	else: options_global.handle(options,param)
	return options

def laos_options(param):
	if param.endswith('/'): return options_global.basic(param,'laos','LAO.LAO',isadmin1=True)
	options={'gsg':'LAO.LAO','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':165,}
	options['locatormap/title']='Laos locator'
	options['countrymap/title']='Laos countrymap'
	options['locatormap/iszoom']=False
#	options['halflightgsgs']=['VNM.VNM','KHM.KHM','MMR.MMR','THA.THA']
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def kyrgyzstan_options(param):
	if param.endswith('/'): return options_global.basic(param,'kyrgyzstan','KGZ.KGZ',isadmin1=True)
	options={'gsg':'KGZ.KGZ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Kyrgyzstan locator'
	options['countrymap/title']='Kyrgyzstan countrymap'
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def armenia_options(param):
	if param.endswith('/'): return options_global.basic(param,'armenia','ARM.ARM',isadmin1=True)
	options={'gsg':'ARM.ARM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,}
	options['locatormap/title']='Armenia locator'
	options['countrymap/title']='Armenia countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def denmark_options(param):
	if param.endswith('/'): return options_global.basic(param,'denmark','DN1.DNK',isadmin1=True,isdisputed=True)
	options={'gsg':'DN1.DNK','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Denmark locator'
	options['countrymap/title']='Denmark countrymap'
	options['euromap/title']='Denmark euromap'
	options['moredots_10m']=[ (4,False,[6]),(25,True,[0]) ]
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
#	options['ispartlabels']=True
	options['countrymap/zoom']=20
	if param=='denmark/_disputed':
		options['countrymap/zoom']=1.5625
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "DN1.GRL.Hans Island", ]
		options['disputed_labels']=[ ("DN1.GRL.Hans Island", "Hans Island", '24px sans',0,0,'+0','+40',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def libya_options(param):
	if param.endswith('/'): return options_global.basic(param,'libya','LBY.LBY',isadmin1=True)
	options={'gsg':'LBY.LBY','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Libya locator'
	options['countrymap/title']='Libya countrymap'
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def tunisia_options(param):
	if param.endswith('/'): return options_global.basic(param,'tunisia','TUN.TUN',isadmin1=True)
	options={'gsg':'TUN.TUN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Tunisia locator'
	options['countrymap/title']='Tunisia countrymap'
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def romania_options(param):
	if param.endswith('/'): return options_global.basic(param,'romania','ROU.ROU',isadmin1=True)
	options={'gsg':'ROU.ROU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Romania locator'
	options['countrymap/title']='Romania countrymap'
	options['euromap/title']='Romania euromap'
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def hungary_options(param):
	if param.endswith('/'): return options_global.basic(param,'hungary','HUN.HUN',isadmin1=True)
	options={'gsg':'HUN.HUN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Hungary locator'
	options['countrymap/title']='Hungary countrymap'
	options['euromap/title']='Hungary euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def slovakia_options(param):
	if param.endswith('/'): return options_global.basic(param,'slovakia','SVK.SVK',isadmin1=True)
	options={'gsg':'SVK.SVK','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Slovakia locator'
	options['countrymap/title']='Slovakia countrymap'
	options['euromap/title']='Slovakia euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def poland_options(param):
	if param.endswith('/'): return options_global.basic(param,'poland','POL.POL',isadmin1=True)
	options={'gsg':'POL.POL','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Poland locator'
	options['countrymap/title']='Poland countrymap'
	options['euromap/title']='Poland euromap'
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def ireland_options(param):
	if param.endswith('/'): return options_global.basic(param,'ireland','IRL.IRL',isadmin1=True)
	options={'gsg':'IRL.IRL','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Ireland locator'
	options['countrymap/title']='Ireland countrymap'
	options['euromap/title']='Ireland euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def unitedkingdom_options(param):
	if param.endswith('/'): return options_global.basic(param,'unitedkingdom','GB1.GBR',isadmin1=True,extra=('_disputed1','_disputed2'))
	options={'gsg':'GB1.GBR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='United Kingdom locator'
	options['countrymap/title']='United Kingdom countrymap'
	options['moredots_10m']=[(4,False,[ 52] ) ]
	options['zoomdots_10m']=[(8,False,[ 52] ) ]
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=8
	if param=='unitedkingdom/_disputed1':
		options['countrymap/zoom']=1
		options['countrymap/lon']=-30
		options['countrymap/lat']=0
		options['moredots_10m']=[]
		options['zoomdots_10m']=[]
		options['disputed_circles']=20
		options['disputed']=[ "GB1.FLK.Falkland Is.", ]
		options['disputed_border']=[ "GB1.GBR.Rockall I.", "GB1.GIB.Gibraltar", ]
		options['disputed_labels']=[
				("GB1.GBR.Rockall I.", "Rockall Island", '24px sans',0,1,'-30','+30',-1,0,0),
				("GB1.GIB.Gibraltar", "Gibraltar", '24px sans',0,1,'-30','+30',-1,0,0),
				("GB1.FLK.Falkland Is.", "Falkland Islands", '24px sans',0,-1,'+20','+0',-1,0,0),
				]
	elif param=='unitedkingdom/_disputed2':
		options['countrymap/zoom']=1
		options['countrymap/lon']=30
		options['countrymap/lat']=-45
		options['moredots_10m']=[]
		options['zoomdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "GB1.IOT.Br. Indian Ocean Ter.", 
				"GB1.IOT.Diego Garcia NSF", "GB1.SGS.S. Georgia", "GB1.SGS.S. Sandwich Is.", ]
		options['disputed_labels']=[
				("GB1.IOT.Br. Indian Ocean Ter.", "British Indian Ocean Territories", '24px sans',0,1,'+50','-35',-1,0,0),
				("GB1.IOT.Diego Garcia NSF", "Diego Garcia NSF", '24px sans',0,0,'+0','+45',-1,0,0),
				("GB1.SGS.S. Sandwich Is.", "South Sandwich Islands", '24px sans',0,0,'+0','-45',-1,0,0),
				("GB1.SGS.S. Georgia", "South Georgia", '24px sans',0,0,'+0','+65',-1,0,0),
				]
	else: options_global.handle(options,param)
	return options

def greece_options(param):
	if param.endswith('/'): return options_global.basic(param,'greece','GRC.GRC',isadmin1=True)
	options={'gsg':'GRC.GRC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Greece locator'
	options['countrymap/title']='Greece countrymap'
	options['euromap/title']='Greece euromap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def zambia_options(param):
	if param.endswith('/'): return options_global.basic(param,'zambia','ZMB.ZMB',isadmin1=True)
	options={'gsg':'ZMB.ZMB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Zambia locator'
	options['countrymap/title']='Zambia countrymap'
#	options['borderlakes']=['Lake Kariba','Lac Moeru']
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def sierraleone_options(param):
	if param.endswith('/'): return options_global.basic(param,'sierraleone','SLE.SLE',isadmin1=True)
	options={'gsg':'SLE.SLE','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Sierra Leone locator'
	options['countrymap/title']='Sierra Leone countrymap'
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def guinea_options(param):
	if param.endswith('/'): return options_global.basic(param,'guinea','GIN.GIN',isadmin1=True)
	options={'gsg':'GIN.GIN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Guinea locator'
	options['countrymap/title']='Guinea countrymap'
	options['countrymap/zoom']=12.5
	options_global.handle(options,param)
	return options

def liberia_options(param):
	if param.endswith('/'): return options_global.basic(param,'liberia','LBR.LBR',isadmin1=True)
	options={'gsg':'LBR.LBR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Liberia locator'
	options['countrymap/title']='Liberia countrymap'
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def centralafricanrepublic_options(param):
	if param.endswith('/'): return options_global.basic(param,'centralafricanrepublic','CAF.CAF',isadmin1=True)
	options={'gsg':'CAF.CAF','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Central African Republic locator'
	options['countrymap/title']='Central African Republic countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def sudan_options(param):
	if param.endswith('/'): return options_global.basic(param,'sudan','SDN.SDN',isadmin1=True,isdisputed=True)
	options={'gsg':'SDN.SDN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Sudan locator'
	options['countrymap/title']='Sudan countrymap'
	options['countrymap/zoom']=5
	if param=='sudan/_disputed':
		options['disputed']=['SDN.SDN.Abyei', "BRT.BRT.Bir Tawil", "EGY.EGY.Halayib Triangle", ]
		options['disputed_labels']=[
				('SDN.SDN.Abyei', 'Abyei', '24px sans',0,0,'+0','+45',-1,0,0),
				("BRT.BRT.Bir Tawil", "Bir Tawil", '24px sans',0,0,'+0','+35',-1,0,0),
				("EGY.EGY.Halayib Triangle", "Halayib Triangle", '24px sans',0,0,'+0','-35',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def djibouti_options(param):
	if param.endswith('/'): return options_global.basic(param,'djibouti','DJI.DJI',isadmin1=True,isdisputed=True)
	options={'gsg':'DJI.DJI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Djibouti locator'
	options['countrymap/title']='Djibouti countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['countrymap/zoom']=32
	if param=='djibouti/_disputed':
		options['disputed_circles']=20
		options['disputed_border']= [ "ERI.ERI.Doumera Island" ]
		options['disputed_labels']=[ ("ERI.ERI.Doumera Island", "Doumera Island", '24px sans',0,0,'+0','-35',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def eritrea_options(param):
	if param.endswith('/'): return options_global.basic(param,'eritrea','ERI.ERI',isadmin1=True,isdisputed=True)
	options={'gsg':'ERI.ERI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Eritrea locator'
	options['countrymap/title']='Eritrea countrymap'
	options['countrymap/zoom']=12.5
	if param=='eritrea/_disputed':
		options['disputed_circles']=20
		options['disputed_border']= [ "ERI.ERI.Doumera Island" ]
		options['disputed_labels']=[ ("ERI.ERI.Doumera Island", "Doumera Island", '24px sans',0,0,'+20','+70',25,0,-20), ]
	else: options_global.handle(options,param)
	return options

def austria_options(param):
	if param.endswith('/'): return options_global.basic(param,'austria','AUT.AUT',isadmin1=True)
	options={'gsg':'AUT.AUT','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Austria locator'
	options['countrymap/title']='Austria countrymap'
	options['euromap/title']='Austria euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def iraq_options(param):
	if param.endswith('/'): return options_global.basic(param,'iraq','IRQ.IRQ',isadmin1=True)
	options={'gsg':'IRQ.IRQ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,}
	options['locatormap/title']='Iraq locator'
	options['countrymap/title']='Iraq countrymap'
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def italy_options(param):
	if param.endswith('/'): return options_global.basic(param,'italy','ITA.ITA',isadmin1=True)
	options={'gsg':'ITA.ITA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Italy locator'
	options['countrymap/title']='Italy countrymap'
	options['euromap/title']='Italy euromap'
	options['moredots_10m']=[ (4,False,[3]),(6,False,[18,24]) ] # 18,24
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def switzerland_options(param):
	if param.endswith('/'): return options_global.basic(param,'switzerland','CHE.CHE',isadmin1=True)
	options={'gsg':'CHE.CHE','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Switzerland locator'
	options['countrymap/title']='Switzerland countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def iran_options(param):
	if param.endswith('/'): return options_global.basic(param,'iran','IRN.IRN',isadmin1=True,isdisputed=True)
	options={'gsg':'IRN.IRN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Iran locator'
	options['countrymap/title']='Iran countrymap'
	options['countrymap/zoom']=6.25
	if param=='iran/_disputed':
		options['locatormap/iszoom']=True
		options['locatormap/zoom']=2.5
		options['disputed_circles']=20
		options['disputed_border']=[ "IRN.IRN.Abu Musa I.", ]
		options['disputed_labels']=[ ("IRN.IRN.Abu Musa I.", "Abu Musa Island", '24px sans',0,0,'+0','+45',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def netherlands_options(param):
	if param.endswith('/'): return options_global.basic(param,'netherlands','NL1.NLD',isadmin1=True)
	options={'gsg':'NL1.NLD','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Netherlands locator'
	options['countrymap/title']='Netherlands countrymap'
	options['euromap/title']='Netherlands euromap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['centerindices_10m']=[0]
	options['moredots_10m']=[ (8,True,[2,3,11]) , (25,True,[0]) ]
	options['tripelboxes_10m']=[ [0], [2,3,11] ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def liechtenstein_options(param):
	if param.endswith('/'): return options_global.basic(param,'liechtenstein','LIE.LIE',isadmin1=True)
	options={'gsg':'LIE.LIE','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Liechtenstein locator'
	options['countrymap/title']='Liechtenstein countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=400
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def ivorycoast_options(param):
	if param.endswith('/'): return options_global.basic(param,'ivorycoast','CIV.CIV',isadmin1=True)
	options={'gsg':'CIV.CIV','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Ivory Coast locator'
	options['countrymap/title']='Ivory Coast countrymap'
	options['countrymap/zoom']=12.5
	options_global.handle(options,param)
	return options

def republicofserbia_options(param):
	if param.endswith('/'): return options_global.basic(param,'republicofserbia','SRB.SRB',isadmin1=True,isdisputed=True)
	options={'gsg':'SRB.SRB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Republic of Serbia locator'
	options['countrymap/title']='Republic of Serbia countrymap'
	options['countrymap/zoom']=25
	if param=='republicofserbia/_disputed':
		options['countrymap/zoom']=20
		options['disputed_circles']=20
		options['disputed']=["KOS.KOS.Kosovo", ]
		options['disputed_border']=[ "SRB.SRB.Vukovar Island", "SRB.SRB.Šarengrad Island", ]
		options['disputed_labels']=[
				("KOS.KOS.Kosovo", "Kosovo", '24px sans',0,0,'+0','+0',0,0,0),
				("SRB.SRB.Vukovar Island", "Vukovar Island", '24px sans',0,0,'+0','-45',-1,0,0),
				("SRB.SRB.Šarengrad Island", "Šarengrad Island", '24px sans',0,0,'+0','+50',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def mali_options(param):
	if param.endswith('/'): return options_global.basic(param,'mali','MLI.MLI',isadmin1=True)
	options={'gsg':'MLI.MLI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Mali locator'
	options['countrymap/title']='Mali countrymap'
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def senegal_options(param):
	if param.endswith('/'): return options_global.basic(param,'senegal','SEN.SEN',isadmin1=True)
	options={'gsg':'SEN.SEN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Senegal locator'
	options['countrymap/title']='Senegal countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def nigeria_options(param):
	if param.endswith('/'): return options_global.basic(param,'nigeria','NGA.NGA',isadmin1=True)
	options={'gsg':'NGA.NGA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Nigeria locator'
	options['countrymap/title']='Nigeria countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def benin_options(param):
	if param.endswith('/'): return options_global.basic(param,'benin','BEN.BEN',isadmin1=True)
	options={'gsg':'BEN.BEN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Benin locator'
	options['countrymap/title']='Benin countrymap'
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def angola_options(param):
	if param.endswith('/'): return options_global.basic(param,'angola','AGO.AGO',isadmin1=True)
	options={'gsg':'AGO.AGO','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Angola locator'
	options['countrymap/title']='Angola countrymap'
	options['countrymap/zoom']=6.25
	options_global.handle(options,param)
	return options

def croatia_options(param):
	if param.endswith('/'): return options_global.basic(param,'croatia','HRV.HRV',isadmin1=True,isdisputed=True)
	options={'gsg':'HRV.HRV','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Croatia locator'
	options['countrymap/title']='Croatia countrymap'
	options['euromap/title']='Croatia euromap'
	options['locatormap/iszoom']=True
	options['countrymap/zoom']=20
	if param=='croatia/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "HRV.HRV.Dragonja River", "SRB.SRB.Vukovar Island", "SRB.SRB.Šarengrad Island", ]
		options['disputed_labels']=[
				("HRV.HRV.Dragonja River", "Dragonja River", '24px sans',0,-1,'+20','-40',-25,0,0),
				("SRB.SRB.Vukovar Island", "Vukovar Island", '24px sans',0,-1,'+5','-75',-25,0,0),
				("SRB.SRB.Šarengrad Island", "Šarengrad Island", '24px sans',0,0,'+20','+100',-25,0,0),]
	else: options_global.handle(options,param)
	return options

def slovenia_options(param):
	if param.endswith('/'): return options_global.basic(param,'slovenia','SVN.SVN',isadmin1=True,isdisputed=True)
	options={'gsg':'SVN.SVN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Slovenia locator'
	options['countrymap/title']='Slovenia countrymap'
	options['euromap/title']='Slovenia euromap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=40
	if param=='slovenia/_disputed':
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "HRV.HRV.Dragonja River", ]
		options['disputed_labels']=[ ("HRV.HRV.Dragonja River", "Dragonja River", '24px sans',0,0,'+0','+50',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def qatar_options(param):
	if param.endswith('/'): return options_global.basic(param,'qatar','QAT.QAT',isadmin1=True)
	options={'gsg':'QAT.QAT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Qatar locator'
	options['countrymap/title']='Qatar countrymap'
	options['locatormap/iszoom']=True
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=40
	options_global.handle(options,param)
	return options

def saudiarabia_options(param):
	if param.endswith('/'): return options_global.basic(param,'saudiarabia','SAU.SAU',isadmin1=True,isdisputed=True)
	options={'gsg':'SAU.SAU','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Saudi Arabia locator'
	options['countrymap/title']='Saudi Arabia countrymap'
	options['countrymap/zoom']=5
	if param=='saudiarabia/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "EGY.EGY.Tiran and Sanafir Is.", ]
		options['disputed_labels']=[ ("EGY.EGY.Tiran and Sanafir Is.", "Tiran and Sanafir Islands", '24px sans',0,-1,'+40','+20',20,0,-5), ]
	else: options_global.handle(options,param)
	return options

def botswana_options(param):
	if param.endswith('/'): return options_global.basic(param,'botswana','BWA.BWA',isadmin1=True)
	options={'gsg':'BWA.BWA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Botswana locator'
	options['countrymap/title']='Botswana countrymap'
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def zimbabwe_options(param):
	if param.endswith('/'): return options_global.basic(param,'zimbabwe','ZWE.ZWE',isadmin1=True)
	options={'gsg':'ZWE.ZWE','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Zimbabwe locator'
	options['countrymap/title']='Zimbabwe countrymap'
#	options['borderlakes']=['Lake Kariba']
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def bulgaria_options(param):
	if param.endswith('/'): return options_global.basic(param,'bulgaria','BGR.BGR',isadmin1=True)
	options={'gsg':'BGR.BGR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Bulgaria locator'
	options['countrymap/title']='Bulgaria countrymap'
	options['euromap/title']='Bulgaria euromap'
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def thailand_options(param):
	if param.endswith('/'): return options_global.basic(param,'thailand','THA.THA',isadmin1=True)
	options={'gsg':'THA.THA','isinsetleft':True,'lonlabel_lat':32,'latlabel_lon':160,}
	options['locatormap/title']='Thailand locator'
	options['countrymap/title']='Thailand countrymap'
	options['countrymap/zoom']=6.25
	options_global.handle(options,param)
	return options

def sanmarino_options(param):
	if param.endswith('/'): return options_global.basic(param,'sanmarino','SMR.SMR',isadmin1=True)
	options={'gsg':'SMR.SMR','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='San Marino locator'
	options['countrymap/title']='San Marino countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['moredots_10m']=[ (25,True,[0]) ]
	options['zoomdots_10m']=[ (15,False,[0]) ]
	options['countrymap/zoom']=512
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def haiti_options(param):
	if param.endswith('/'): return options_global.basic(param,'haiti','HTI.HTI',isadmin1=True,isdisputed=True)
	options={'gsg':'HTI.HTI','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Haiti locator'
	options['countrymap/title']='Haiti countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,2,[0]) ]
	options['countrymap/zoom']=32
	if param=='haiti/_disputed':
		options['countrymap/zoom']=16
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "US1.UMI.Navassa I.", ]
		options['disputed_labels']=[ ("US1.UMI.Navassa I.", "Navassa Island", '24px sans',0,0,'+0','+45',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def dominicanrepublic_options(param):
	if param.endswith('/'): return options_global.basic(param,'dominicanrepublic','DOM.DOM',isadmin1=True)
	options={'gsg':'DOM.DOM','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Dominican Republic locator'
	options['countrymap/title']='Dominican Republic countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['countrymap/zoom']=25
	options_global.handle(options,param)
	return options

def chad_options(param):
	if param.endswith('/'): return options_global.basic(param,'chad','TCD.TCD',isadmin1=True)
	options={'gsg':'TCD.TCD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Chad locator'
	options['countrymap/title']='Chad countrymap'
	options['countrymap/zoom']=6.25
	options_global.handle(options,param)
	return options

def kuwait_options(param):
	if param.endswith('/'): return options_global.basic(param,'kuwait','KWT.KWT',isadmin1=True)
	options={'gsg':'KWT.KWT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-22,}
	options['locatormap/title']='Kuwait locator'
	options['countrymap/title']='Kuwait countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=40
	options_global.handle(options,param)
	return options

def elsalvador_options(param):
	if param.endswith('/'): return options_global.basic(param,'elsalvador','SLV.SLV',isadmin1=True)
	options={'gsg':'SLV.SLV','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-150,}
	options['locatormap/title']='El Salvador locator'
	options['countrymap/title']='El Salvador countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,2,[0]) ]
	options['countrymap/zoom']=40
	options_global.handle(options,param)
	return options

def guatemala_options(param):
	if param.endswith('/'): return options_global.basic(param,'guatemala','GTM.GTM',isadmin1=True,isdisputed=True)
	options={'gsg':'GTM.GTM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Guatemala locator'
	options['countrymap/title']='Guatemala countrymap'
	options['countrymap/zoom']=16
	if param=='guatemala/_disputed':
		options['disputed_border']=[ "BLZ.BLZ.Belize", ]
		options['disputed_labels']=[ ("BLZ.BLZ.Belize", "Belize", '24px sans',0,1,'-20','+50',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def timorleste_options(param):
	if param.endswith('/'): return options_global.basic(param,'timorleste','TLS.TLS',isadmin1=True)
	options={'gsg':'TLS.TLS','isinsetleft':True,'lonlabel_lat':-25,'latlabel_lon':90,}
	options['locatormap/title']='Timor-Leste locator'
	options['countrymap/title']='Timor-Leste countrymap'
	options['istopinsets']=True
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['locatormap/zoom']=4
	options['centerdot']=(40,3)
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def brunei_options(param):
	if param.endswith('/'): return options_global.basic(param,'brunei','BRN.BRN',isadmin1=True,isdisputed=True)
	options={'gsg':'BRN.BRN','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,}
	options['locatormap/title']='Brunei locator'
	options['countrymap/title']='Brunei countrymap'
	options['istopinsets']=True
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=40
	if param=='brunei/_disputed':
		options['countrymap/zoom']=8
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "PGA.PGA.Spratly Is.", ]
		options['disputed_labels']=[ ("PGA.PGA.Spratly Is.", "Spratly Islands", '24px sans',0,0,'+0','+180',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def monaco_options(param):
	if param.endswith('/'): return options_global.basic(param,'monaco')
	options={'gsg':'MCO.MCO','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Monaco locator'
	options['countrymap/title']='Monaco countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=64
	options['moredots_10m']=[ (15,4,[0]) ]
	options['countrymap/zoom']=512
	options['zoomm']='10m'
	return options

def algeria_options(param):
	if param.endswith('/'): return options_global.basic(param,'algeria','DZA.DZA',isadmin1=True)
	options={'gsg':'DZA.DZA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Algeria locator'
	options['countrymap/title']='Algeria countrymap'
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def mozambique_options(param):
	if param.endswith('/'): return options_global.basic(param,'mozambique','MOZ.MOZ',isadmin1=True)
	options={'gsg':'MOZ.MOZ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Mozambique locator'
	options['countrymap/title']='Mozambique countrymap'
#	options['borderlakes']=['Lake Malawi']
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def eswatini_options(param):
	if param.endswith('/'): return options_global.basic(param,'eswatini','SWZ.SWZ',isadmin1=True)
	options={'gsg':'SWZ.SWZ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='eSwatini locator'
	options['countrymap/title']='eSwatini countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def burundi_options(param):
	if param.endswith('/'): return options_global.basic(param,'burundi','BDI.BDI',isadmin1=True)
	options={'gsg':'BDI.BDI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Burundi locator'
	options['countrymap/title']='Burundi countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,False,[0]) ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def rwanda_options(param):
	if param.endswith('/'): return options_global.basic(param,'rwanda','RWA.RWA',isadmin1=True)
	options={'gsg':'RWA.RWA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Rwanda locator'
	options['countrymap/title']='Rwanda countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,False,[0]) ]
#	options['borderlakes']=['Lake Kivu']
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def myanmar_options(param):
	if param.endswith('/'): return options_global.basic(param,'myanmar','MMR.MMR',isadmin1=True)
	options={'gsg':'MMR.MMR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':50,}
	options['locatormap/title']='Myanmar locator'
	options['countrymap/title']='Myanmar countrymap'
	options['moredots_10m']=[(4,False,[29,30]),]
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def bangladesh_options(param):
	if param.endswith('/'): return options_global.basic(param,'bangladesh','BGD.BGD',isadmin1=True)
	options={'gsg':'BGD.BGD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':50,}
	options['locatormap/title']='Bangladesh locator'
	options['countrymap/title']='Bangladesh countrymap'
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def andorra_options(param):
	if param.endswith('/'): return options_global.basic(param,'andorra','AND.AND',isadmin1=True)
	options={'gsg':'AND.AND','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Andorra locator'
	options['countrymap/title']='Andorra countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['moredots_10m']=[ (15,3,[0]) ]
	options['countrymap/zoom']=256
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def afghanistan_options(param):
	if param.endswith('/'): return options_global.basic(param,'afghanistan','AFG.AFG',isadmin1=True)
	options={'gsg':'AFG.AFG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Afghanistan locator'
	options['countrymap/title']='Afghanistan countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def montenegro_options(param):
	if param.endswith('/'): return options_global.basic(param,'montenegro','MNE.MNE',isadmin1=True)
	options={'gsg':'MNE.MNE','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Montenegro locator'
	options['countrymap/title']='Montenegro countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=40
	options_global.handle(options,param)
	return options

def bosniaandherzegovina_options(param):
	if param.endswith('/'): return options_global.basic(param,'bosniaandherzegovina','BIH.BIH',isadmin1=True)
	options={'gsg':'BIH.BIH','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Bosnia and Herzegovina locator'
	options['countrymap/title']='Bosnia and Herzegovina countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def uganda_options(param):
	if param.endswith('/'): return options_global.basic(param,'uganda','UGA.UGA',isadmin1=True)
	options={'gsg':'UGA.UGA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Uganda locator'
	options['countrymap/title']='Uganda countrymap'
#	options['borderlakes']=['Lake Edward','Lake Albert','Lake Victoria']
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def usnavalbaseguantanamobay_options(param):
	if param.endswith('/'): return options_global.basic(param,'usnavalbaseguantanamobay')
	options={'gsg':'CU1.USG','isinsetleft':True,'lonlabel_lat':5,'latlabel_lon':-30,}
	options['locatormap/title']='US Naval Base Guantanamo Bay locator'
	options['countrymap/title']='US Naval Base Guantanamo Bay countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=20
	options['moredots_10m']=[ (20,4,[0]) ]
	options['countrymap/zoom']=400
	options['zoomm']='10m'
	return options

def cuba_options(param):
	if param.endswith('/'): return options_global.basic(param,'cuba','CU1.CUB',isadmin1=True,isdisputed=True)
	options={'gsg':'CU1.CUB','isinsetleft':True,'lonlabel_lat':5,'latlabel_lon':-30,}
	options['locatormap/title']='Cuba locator'
	options['countrymap/title']='Cuba countrymap'
	options['countrymap/zoom']=8
	if param=='cuba/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "CU1.USG.Guantanamo Bay USNB", ]
		options['disputed_labels']=[ ("CU1.USG.Guantanamo Bay USNB", "Guantanamo Bay USNB", '24px sans',0,0,'+0','+45',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def honduras_options(param):
	if param.endswith('/'): return options_global.basic(param,'honduras','HND.HND',isadmin1=True,isdisputed=True)
	options={'gsg':'HND.HND','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Honduras locator'
	options['countrymap/title']='Honduras countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[(4,False,[6]),]
	options['countrymap/zoom']=10
	if param=='honduras/_disputed':
		options['countrymap/zoom']=6.25
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['locatormap/zoom']=2.5
		options['locatormap/iszoom34']=False
		options['disputed_border']=[ "BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "BLZ.BLZ.Sapodilla Cayes", "SER.SER.Serranilla Bank", ]
		options['disputed_labels']=[
				("BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "Bajo Nuevo Bank", '24px sans',0,0,'-50','-70',25,0,0),
				("BLZ.BLZ.Sapodilla Cayes", "Sapodilla Cayes", '24px sans',0,-1,'+40','-60',25,0,0),
				("SER.SER.Serranilla Bank", "Serranilla Bank", '24px sans',0,0,'-20','+80',25,0,-20),]
	else: options_global.handle(options,param)
	return options

def ecuador_options(param):
	if param.endswith('/'): return options_global.basic(param,'ecuador','ECU.ECU',isadmin1=True)
	options={'gsg':'ECU.ECU','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Ecuador locator'
	options['countrymap/title']='Ecuador countrymap'
	options['moredots_10m']=[ (20,False,[7]) ]
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def colombia_options(param):
	if param.endswith('/'): return options_global.basic(param,'colombia','COL.COL',isadmin1=True,isdisputed=True)
	options={'gsg':'COL.COL','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Colombia locator'
	options['countrymap/title']='Colombia countrymap'
	options['moredots_10m']=[(4,False,[5,6,7,10]),]
	options['countrymap/zoom']=5
	options['countrymapdots_10m']=[(4,False,[5,6,7,10])]
	if param=='colombia/_disputed':
		options['countrymap/zoom']=4
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "SER.SER.Serranilla Bank", ]
		options['disputed_labels']=[
				("BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "Bajo Nuevo Bank", '24px sans',0,0,'-50','-40',25,0,0),
				("SER.SER.Serranilla Bank", "Serranilla Bank", '24px sans',0,0,'+20','+80',25,0,-20),]
	else: options_global.handle(options,param)
	return options

def paraguay_options(param):
	if param.endswith('/'): return options_global.basic(param,'paraguay','PRY.PRY',isadmin1=True)
	options={'gsg':'PRY.PRY','isinsetleft':True,'lonlabel_lat':20,'latlabel_lon':-30,}
	options['locatormap/title']='Paraguay locator'
	options['countrymap/title']='Paraguay countrymap'
#	options['borderlakes']=['Itaipú Reservoir']
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def brazilianisland_options(param):
	if param.endswith('/'): return options_global.basic(param,'brazilianisland')
	options={'gsg':'BRI.BRI','isinsetleft':True,'lonlabel_lat':20,'latlabel_lon':-30,}
	options['locatormap/title']='Brazilian Island locator'
	options['countrymap/title']='Brazilian Island countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['locatormap/zoom']=64
	options['centerdot']=(20,3)
	options['countrymap/zoom']=512
	options['zoomm']='10m'
#	options['isfullpartlabels'] = True
	return options

def portugal_options(param):
	if param.endswith('/'): return options_global.basic(param,'portugal','PRT.PRT',isadmin1=True,isdisputed=True)
	options={'gsg':'PRT.PRT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Portugal locator'
	options['countrymap/title']='Portugal countrymap'
	options['euromap/title']='Portugal euromap'
#	options['smalldots']=[2,3,5,6,7,8,9,10,11,12,13,14,15]
	options['moredots_10m']=[(4,False,(2,3,5,6,7,8,9,10,11,12,13,14,15))]
	options['euromapdots_50m']= [('PRT.PRT',24,False,[0]), ('PRT.PRT',82,False,[4]) ]
#	options['ispartlabels']=True
	options['countrymap/zoom']=5
	if param=='portugal/_disputed':
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['locatormap/iszoom']=True
		options['locatormap/zoom']=2
		options['disputed_border']=[ "ESP.ESP.Olivenza", ]
		options['disputed_labels']=[ ("ESP.ESP.Olivenza", "Olivenza", '24px sans',0,1,'-50','+110',25,0,-5), ]
	else: options_global.handle(options,param)
	return options

def moldova_options(param):
	if param.endswith('/'): return options_global.basic(param,'moldova','MDA.MDA',isadmin1=True,isdisputed=True)
	options={'gsg':'MDA.MDA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Moldova locator'
	options['countrymap/title']='Moldova countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=32
	if param=='moldova/_disputed':
		options['locatormap/zoom']=8
		options['locatormap/iszoom34']=False
		options['disputed']=['MDA.MDA.Transnistria']
		options['disputed_labels']=[ ('MDA.MDA.Transnistria', 'Transnistria', '24px sans',0,-1,'+40','-5',-1,0,0), ]
		options['zoomm']='10m'
	else: options_global.handle(options,param)
	return options

def turkmenistan_options(param):
	if param.endswith('/'): return options_global.basic(param,'turkmenistan','TKM.TKM',isadmin1=True)
	options={'gsg':'TKM.TKM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Turkmenistan locator'
	options['countrymap/title']='Turkmenistan countrymap'
#	options['borderlakes']=['Sarygamysh Köli']
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def jordan_options(param):
	if param.endswith('/'): return options_global.basic(param,'jordan','JOR.JOR',isadmin1=True)
	options={'gsg':'JOR.JOR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Jordan locator'
	options['countrymap/title']='Jordan countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
#	options['borderlakes']=['Dead Sea','_deadseasouth']
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def nepal_options(param):
	if param.endswith('/'): return options_global.basic(param,'nepal','NPL.NPL',isadmin1=True,isdisputed=True)
	options={'gsg':'NPL.NPL','isinsetleft':True,'lonlabel_lat':-5,'latlabel_lon':50,}
	options['locatormap/title']='Nepal locator'
	options['countrymap/title']='Nepal countrymap'
	options['countrymap/zoom']=10
	if param=='nepal/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "IND.IND.Near Om Parvat", ]
		options['disputed_labels']=[ ("IND.IND.Near Om Parvat", "Near Om Parvat", '24px sans',0,1,'-40','+0',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def lesotho_options(param):
	if param.endswith('/'): return options_global.basic(param,'lesotho','LSO.LSO',isadmin1=True)
	options={'gsg':'LSO.LSO','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-25,}
	options['locatormap/title']='Lesotho locator'
	options['countrymap/title']='Lesotho countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def cameroon_options(param):
	if param.endswith('/'): return options_global.basic(param,'cameroon','CMR.CMR',isadmin1=True)
	options={'gsg':'CMR.CMR','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Cameroon locator'
	options['countrymap/title']='Cameroon countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def gabon_options(param):
	if param.endswith('/'): return options_global.basic(param,'gabon','GAB.GAB',isadmin1=True,isdisputed=True)
	options={'gsg':'GAB.GAB','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Gabon locator'
	options['countrymap/title']='Gabon countrymap'
	options['countrymap/zoom']=12.5
	if param=='gabon/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "GAB.GAB.Mbane Island", ]
		options['disputed_labels']=[ ("GAB.GAB.Mbane Island", "Mbane Island", '24px sans',0,1,'-40','+0',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def niger_options(param):
	if param.endswith('/'): return options_global.basic(param,'niger','NER.NER',isadmin1=True)
	options={'gsg':'NER.NER','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Niger locator'
	options['countrymap/title']='Niger countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def burkinafaso_options(param):
	if param.endswith('/'): return options_global.basic(param,'burkinafaso','BFA.BFA',isadmin1=True)
	options={'gsg':'BFA.BFA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Burkina Faso locator'
	options['countrymap/title']='Burkina Faso countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def togo_options(param):
	if param.endswith('/'): return options_global.basic(param,'togo','TGO.TGO',isadmin1=True)
	options={'gsg':'TGO.TGO','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Togo locator'
	options['countrymap/title']='Togo countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def ghana_options(param):
	if param.endswith('/'): return options_global.basic(param,'ghana','GHA.GHA',isadmin1=True)
	options={'gsg':'GHA.GHA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Ghana locator'
	options['countrymap/title']='Ghana countrymap'
	options['countrymap/zoom']=12.5
	options_global.handle(options,param)
	return options

def guineabissau_options(param):
	if param.endswith('/'): return options_global.basic(param,'guineabissau','GNB.GNB',isadmin1=True)
	options={'gsg':'GNB.GNB','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Guinea-Bissau locator'
	options['countrymap/title']='Guinea-Bissau countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,False,[0]) ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def gibraltar_options(param):
	if param.endswith('/'): return options_global.basic(param,'gibraltar')
	options={'gsg':'GB1.GIB','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Gibraltar locator'
	options['countrymap/title']='Gibraltar countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=64
	options['locatormap/iszoom34']=False
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=512
	options['zoomm']='10m'
	return options

def unitedstatesofamerica_options(param):
	if param.endswith('/'): return options_global.basic(param,'unitedstatesofamerica','US1.USA',isadmin1=True,
			extra=('_disputed1','_disputed2'))
	options={'gsg':'US1.USA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-45,}
	options['locatormap/title']='United States of America locator'
	options['countrymap/title']='United States of America countrymap'
	options['lon']=-110
	options['moredots_10m']=[(4,False,[272,273,274,275,276]),]
	options['tripelboxes_10m']=[ [0], [85,199], [232] ]
#	options['ispartlabels']=True
#	options['borderlakes']=['Lake Superior','Lake Ontario','Lake Erie','Lake Huron','Lake of the Woods','Upper Red Lake',
#			'Rainy Lake','Lake Saint Clair']
	options['countrymap/zoom']=1.4
	options['countrymap/lon']=-115
	if param=='unitedstatesofamerica/_disputed1':
		options['countrymap/zoom']=3.125
		options['countrymap/lon']=-85
		options['countrymap/lat']=25
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "CU1.USG.Guantanamo Bay USNB", 
				"SER.SER.Serranilla Bank", "US1.UMI.Navassa I.", ]
		options['disputed_labels']=[
				("CU1.USG.Guantanamo Bay USNB", "Guantanamo Bay USNB", '24px sans',0,0,'+0','-40',-1,0,0),
				("US1.UMI.Navassa I.", "Navassa Island", '24px sans',0,1,'-40','-5',-25,0,-5),
				("BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "Bajo Nuevo Bank", '24px sans',0,1,'-40','+0',-1,0,0),
				("SER.SER.Serranilla Bank", "Serranilla Bank", '24px sans',0,-1,'+30','+0',-1,0,0),]
	elif param=='unitedstatesofamerica/_disputed2':
		options['countrymap/zoom']=1.5625
		options['countrymap/lon']=-170
		options['countrymap/lat']=30
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "US1.UMI.Wake Atoll", ]
		options['disputed_labels']=[ ("US1.UMI.Wake Atoll", "Wake Atoll", '24px sans',0,0,'+0','-35',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def canada_options(param):
	if param.endswith('/'): return options_global.basic(param,'canada','CAN.CAN',isadmin1=True,isdisputed=True)
	options={'gsg':'CAN.CAN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Canada locator'
	options['countrymap/title']='Canada countrymap'
#	options['ispartlabels']=True
#	options['borderlakes']=['Lake Superior','Lake Ontario','Lake Erie','Lake Huron','Lake of the Woods','Upper Red Lake',
#			'Rainy Lake','Lake Saint Clair']
	options['countrymap/zoom']=2
	options['countrymap/lon']=-90
	if param=='canada/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "DN1.GRL.Hans Island", ]
		options['disputed_labels']=[ ("DN1.GRL.Hans Island", "Hans Island", '24px sans',0,-1,'+25','+0',-1,0,0), ]
	elif param=='canada/princeedwardisland':
		options_global.handle(options,param)
		options['admin1dot']=80
	else: options_global.handle(options,param)
	return options

def mexico_options(param):
	if param.endswith('/'): return options_global.basic(param,'mexico','MEX.MEX',isadmin1=True,isdisputed=False)
	options={'gsg':'MEX.MEX','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-150,}
	options['locatormap/title']='Mexico locator'
	options['countrymap/title']='Mexico countrymap'
	options['moredots_10m']=[(4,False,[1,2,3,32,34,36]),]
	options['countrymap/zoom']=3.5
	if param=='mexico/islaperez':
		options['admin1']='MEX.MEX..' # blank
		options['admin1dot']=20
	else: options_global.handle(options,param)
	return options

def belize_options(param):
	if param.endswith('/'): return options_global.basic(param,'belize','BLZ.BLZ',isadmin1=True,isdisputed=True)
	options={'gsg':'BLZ.BLZ','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Belize locator'
	options['countrymap/title']='Belize countrymap'
	options['moredots_10m']=[ (30,2,[0]) ]
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=32
	if param=='belize/_disputed':
		options['moredots_10m']=[]
		options['locatormap/iszoom34']=False
		options['locatormap/zoom']=8
		options['disputed']=[ "BLZ.BLZ.Belize", ]
		options['disputed_border']=[ "BLZ.BLZ.Sapodilla Cayes", ]
		options['disputed_labels']=[
				("BLZ.BLZ.Belize", "Belize", '24px sans',0,1,'+0','+0',-1,0,0),
				("BLZ.BLZ.Sapodilla Cayes", "Sapodilla Cayes", '24px sans',0,-1,'+50','+0',-1,0,0), ]
		options['zoomm']='10m'
	else: options_global.handle(options,param)
	return options

def panama_options(param):
	if param.endswith('/'): return options_global.basic(param,'panama','PAN.PAN',isadmin1=True)
	options={'gsg':'PAN.PAN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Panama locator'
	options['countrymap/title']='Panama countrymap'
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def venezuela_options(param):
	if param.endswith('/'): return options_global.basic(param,'venezuela','VEN.VEN',isadmin1=True,isdisputed=True)
	options={'gsg':'VEN.VEN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Venezuela locator'
	options['countrymap/title']='Venezuela countrymap'
	options['moredots_10m']=[(4,False,[ 20 ]),]
	options['countrymap/zoom']=6.25
	options['countrymapdots_10m']=[(4,False,[ 20 ])]
	if param=='venezuela/_disputed':
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed']=[ "GUY.GUY.West of Essequibo River", ]
		options['disputed_border']=[ "VEN.VEN.Bird Island", ]
		options['disputed_labels']=[
				("GUY.GUY.West of Essequibo River", "West of Essequibo River", '24px sans',85,0,'+15','+0',-1,0,0),
				("VEN.VEN.Bird Island", "Bird Island", '24px sans',0,0,'+0','+40',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def papuanewguinea_options(param):
	if param.endswith('/'): return options_global.basic(param,'papuanewguinea','PNG.PNG',isadmin1=True)
	options={'gsg':'PNG.PNG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Papua New Guinea locator'
	options['countrymap/title']='Papua New Guinea countrymap'
	options['countrymap/zoom']=6.25
	options_global.handle(options,param)
	return options

def egypt_options(param):
	if param.endswith('/'): return options_global.basic(param,'egypt','EGY.EGY',isadmin1=True,isdisputed=True)
	options={'gsg':'EGY.EGY','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Egypt locator'
	options['countrymap/title']='Egypt countrymap'
	options['countrymap/zoom']=8
	if param=='egypt/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "EGY.EGY.Tiran and Sanafir Is.", "IS1.PSX.Gaza", ]
		options['disputed']=[ "BRT.BRT.Bir Tawil", "EGY.EGY.Halayib Triangle", ]
		options['disputed_labels']=[
				("EGY.EGY.Tiran and Sanafir Is.", "Tiran and Sanafir Islands", '24px sans',0,0,'+0','+50',-1,0,0),
				("IS1.PSX.Gaza", "Gaza", '24px sans',0,0,'+0','-40',-1,0,0),
				("BRT.BRT.Bir Tawil", "Bir Tawil", '24px sans',0,0,'+0','+40',-1,0,0),
				("EGY.EGY.Halayib Triangle", "Halayib Triangle", '24px sans',0,0,'+0','-50',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def yemen_options(param):
	if param.endswith('/'): return options_global.basic(param,'yemen','YEM.YEM',isadmin1=True)
	options={'gsg':'YEM.YEM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Yemen locator'
	options['countrymap/title']='Yemen countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def mauritania_options(param):
	if param.endswith('/'): return options_global.basic(param,'mauritania','MRT.MRT',isadmin1=True)
	options={'gsg':'MRT.MRT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Mauritania locator'
	options['countrymap/title']='Mauritania countrymap'
	options['countrymap/zoom']=6.25
	options_global.handle(options,param)
	return options

def equatorialguinea_options(param):
	if param.endswith('/'): return options_global.basic(param,'equatorialguinea','GNQ.GNQ',isadmin1=True,isdisputed=True)
	options={'gsg':'GNQ.GNQ','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Equatorial Guinea locator'
	options['countrymap/title']='Equatorial Guinea countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,2,[0]),(4,False,[1]) ]
	options['zoomdots_10m']=[ (8,False,[1]) ]
	options['countrymap/zoom']=12.5
	options['countrymapdots_10m']=[ (4,False,[1]) ]
	if param=='equatorialguinea/_disputed':
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "GAB.GAB.Mbane Island", ]
		options['disputed_labels']=[ ("GAB.GAB.Mbane Island", "Mbane Island", '24px sans',0,1,'-40','+0',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def gambia_options(param):
	if param.endswith('/'): return options_global.basic(param,'gambia','GMB.GMB',isadmin1=True)
	options={'gsg':'GMB.GMB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Gambia locator'
	options['countrymap/title']='Gambia countrymap'
	options['moredots_10m']=[ (25,2,[0]) ]
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['countrymap/zoom']=25
	options_global.handle(options,param)
	return options

def hongkongsar_options(param):
	if param.endswith('/'): return options_global.basic(param,'hongkongsar','CH1.HKG',isadmin1=True)
	options={'gsg':'CH1.HKG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':175,}
	options['locatormap/title']='Hong Kong S.A.R. locator'
	options['countrymap/title']='Hong Kong S.A.R. countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=10
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=100
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def vatican_options(param):
	if param.endswith('/'): return options_global.basic(param,'vatican')
	options={'gsg':'VAT.VAT','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Vatican locator'
	options['countrymap/title']='Vatican countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=False
	options['moredots_10m']=[ (10,True,[0]) ]
	options['zoomdots_10m']=[ (15,False,[0]) ]
	options['countrymap/zoom']=16
	options['countrymapdots_10m']=[ (10,False,[0]) ]
	options['zoomm']='10m'
	return options

def northerncyprus_options(param):
	if param.endswith('/'): return options_global.basic(param,'northerncyprus','CYN.CYN',isdisputed=True)
	options={'gsg':'CYN.CYN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Northern Cyprus locator'
	options['countrymap/title']='Northern Cyprus countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=False
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=50
	options['countrymap/lon']=33.4
	if 'disputed' in param:
		options['moredots_10m']=[]
		options['disputed']=['CYN.CYN.N. Cyprus', "CNM.CNM.Cyprus U.N. Buffer Zone", ]
		options['disputed_labels']=[
				('CYN.CYN.N. Cyprus', 'Northern Cyprus', '24px sans',0,0,'+0','-40',-1,0,0),
				("CNM.CNM.Cyprus U.N. Buffer Zone", "Cyprus U.N. Buffer Zone", '24px sans',0,0,'-100','+35',-1,0,0),]
	return options

def cyprusnomansarea_options(param):
	if param.endswith('/'): return options_global.basic(param,'cyprusnomansarea')
	options={'gsg':'CNM.CNM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Cyprus No Mans Area locator'
	options['countrymap/title']='Cyprus No Mans Area countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=20
	options['locatormap/iszoom34']=False
	options['moredots_10m']=[ (20,3,[0]) ]
	options['issubland']=False
	options['countrymap/zoom']=50
	options['zoomm']='10m'
	return options

def siachenglacier_options(param):
	if param.endswith('/'): return options_global.basic(param,'siachenglacier')
	options={'gsg':'KAS.KAS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Siachen Glacier locator'
	options['countrymap/title']='Siachen Glacier countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=False
	options['moredots_10m']=[ (20,2,[0]) ]
	options['countrymap/zoom']=4
	return options

def baykonurcosmodrome_options(param):
	if param.endswith('/'): return options_global.basic(param,'baykonurcosmodrome')
	options={'gsg':'KA1.KAB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Baykonur Cosmodrome locator'
	options['countrymap/title']='Baykonur Cosmodrome countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,2,[0]) ]
	options['countrymap/zoom']=4
	return options

def akrotirisovereignbasearea_options(param):
	if param.endswith('/'): return options_global.basic(param,'akrotirisovereignbasearea')
	options={'gsg':'GB1.WSB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Akrotiri Sovereign Base Area locator'
	options['countrymap/title']='Akrotiri Sovereign Base Area countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=50
	options['countrymap/lon']=33.4
	options['zoomm']='10m'
	return options

def southernpatagonianicefield_options(param):
	if param.endswith('/'): return options_global.basic(param,'southernpatagonianicefield')
	options={'gsg':'SPI.SPI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Southern Patagonian Ice Field locator'
	options['countrymap/title']='Southern Patagonian Ice Field countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['locatormap/zoom']=5
	options['centerdot']=(20,3)
	options['countrymap/zoom']=64
	return options

def birtawil_options(param):
	if param.endswith('/'): return options_global.basic(param,'birtawil')
	options={'gsg':'BRT.BRT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Bir Tawil locator'
	options['countrymap/title']='Bir Tawil countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['locatormap/zoom']=5
	options['centerdot']=(20,3)
	options['countrymap/zoom']=8
	return options

def antarctica_options(param):
	if param.endswith('/'): return options_global.basic(param,'antarctica')
	options={'gsg':'ATA.ATA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Antarctica locator'
	options['countrymap/title']='Antarctica countrymap'
	options['istopinsets']=True
	options['countrymap/zoom']=2
	options['countrymap/lon']=0
	options['countrymap/lat']=-89
	return options

def australia_options(param):
	if param.endswith('/'): return options_global.basic(param,'australia','AU1.AUS',isadmin1=True)
	options={'gsg':'AU1.AUS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Australia locator'
	options['countrymap/title']='Australia countrymap'
	options['moredots_10m']=[ (4,False,[12, 33 ]),]
	options['countrymap/zoom']=2
	options_global.handle(options,param)
	return options

def greenland_options(param):
	if param.endswith('/'): return options_global.basic(param,'greenland','DN1.GRL',isadmin1=True)
	options={'gsg':'DN1.GRL','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Greenland locator'
	options['countrymap/title']='Greenland countrymap'
	options['countrymap/zoom']=2
	options_global.handle(options,param)
	return options

def fiji_options(param):
	if param.endswith('/'): return options_global.basic(param,'fiji')
	options={'gsg':'FJI.FJI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':150,}
	options['locatormap/title']='Fiji locator'
	options['countrymap/title']='Fiji countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/iszoom34']=True
	options['locatormap/zoom']=2.5
#	options['ispartlabels']=True
	options['centerindices_10m']=[20]
	options['tripelboxes_10m']=[ [0],[24] ]
#	options['smalldots_10m']=[ 34,35,36,37 ]
	options['zoomdots_10m']=[ (10,False,[34,35]) ]
	options['centerdot']=(55,2)
	options['countrymap/zoom']=8
	return options

def newzealand_options(param):
	if param.endswith('/'): return options_global.basic(param,'newzealand','NZ1.NZ1',isadmin1=True,isdisputed=True)
	options={'gsg':'NZ1.NZL','isinsetleft':False,'lonlabel_lat':10,'latlabel_lon':-150,}
	options['locatormap/title']='New Zealand locator'
	options['countrymap/title']='New Zealand countrymap'
	options['centerindices_10m']=[17]
	options['tripelboxes_10m']=[ [7],[17] ]
	options['moredots_10m']=[ (4,False,[ 1,2,3,4,5,6,7,8]),]
	options['countrymap/zoom']=2.5
	options['countrymapdots_10m']=[[8,False,[ 6,7]]]
	options['countrymap/lat']=-30.57177
	if param=='newzealand/_disputed':
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "US1.ASM.Swains Island", ]
		options['disputed_labels']=[ ("US1.ASM.Swains Island", "Swains Island", '24px sans',0,0,'+0','+40',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def newcaledonia_options(param):
	if param.endswith('/'): return options_global.basic(param,'newcaledonia','FR1.NCL',isadmin1=True)
	options={'gsg':'FR1.NCL','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-150,}
	options['locatormap/title']='New Caledonia locator'
	options['countrymap/title']='New Caledonia countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (4,False,[10]) ]
	options['centerdot']=(40,2)
#	options['ispartlabels']=True
	options['countrymap/zoom']=12.5
	options['countrymapdots_10m']=[ (4,False,[10]) ]
	options_global.handle(options,param)
	return options

def madagascar_options(param):
	if param.endswith('/'): return options_global.basic(param,'madagascar','MDG.MDG',isadmin1=True,isdisputed=True)
	options={'gsg':'MDG.MDG','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Madagascar locator'
	options['countrymap/title']='Madagascar countrymap'
	options['countrymap/zoom']=5
	if param=='madagascar/_disputed':
		options['locatormap/iszoom']=True
		options['locatormap/zoom']=2
		options['disputed_circles']=20
		options['disputed_border']=[ "FR1.ATF.Bassas da India", "FR1.ATF.Europa Island", "FR1.ATF.Glorioso Is.", "FR1.ATF.Juan De Nova I.", ]
		options['disputed_labels']=[
				("FR1.ATF.Bassas da India", "Bassas da India", '24px sans',0,0,'+0','-30',-1,0,0),
				("FR1.ATF.Europa Island", "Europa Island", '24px sans',0,0,'+0','+45',-1,0,0),
				("FR1.ATF.Glorioso Is.", "Glorioso Island", '24px sans',0,0,'+0','-30',-1,0,0),
				("FR1.ATF.Juan De Nova I.", "Juan De Nova Island", '24px sans',-45,0,'-20','-20',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def philippines_options(param):
	if param.endswith('/'): return options_global.basic(param,'philippines','PHL.PHL',isadmin1=True,isdisputed=True)
	options={'gsg':'PHL.PHL','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':180,}
	options['locatormap/title']='Philippines locator'
	options['countrymap/title']='Philippines countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=5
	if param=='philippines/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "PGA.PGA.Spratly Is.", "SCR.SCR.Scarborough Reef", ]
		options['disputed_labels']=[
				("PGA.PGA.Spratly Is.", "Spratly Islands", '24px sans',0,-1,'+0','-115',-1,0,0),
				("SCR.SCR.Scarborough Reef", "Scarborough Reef", '24px sans',0,1,'+0','+45',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def srilanka_options(param):
	if param.endswith('/'): return options_global.basic(param,'srilanka','LKA.LKA',isadmin1=True)
	options={'gsg':'LKA.LKA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,}
	options['locatormap/title']='Sri Lanka locator'
	options['countrymap/title']='Sri Lanka countrymap'
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def curacao_options(param):
	if param.endswith('/'): return options_global.basic(param,'curacao')
	options={'gsg':'NL1.CUW','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Curaçao locator'
	options['countrymap/title']='Curaçao countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=40
	options['zoomm']='10m'
	return options

def aruba_options(param):
	if param.endswith('/'): return options_global.basic(param,'aruba')
	options={'gsg':'NL1.ABW','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Aruba locator'
	options['countrymap/title']='Aruba countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=40
	return options

def thebahamas_options(param):
	if param.endswith('/'): return options_global.basic(param,'thebahamas','BHS.BHS',isadmin1=True)
	options={'gsg':'BHS.BHS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='The Bahamas locator'
	options['countrymap/title']='The Bahamas countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=False
#	options['moredots_10m']=[ (50,False,[8]) ]
	options['centerdot']=(50,3)
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def turksandcaicosislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'turksandcaicosislands','GB1.TCA',isadmin1=True)
	options={'gsg':'GB1.TCA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Turks and Caicos Islands locator'
	options['countrymap/title']='Turks and Caicos Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=False
#	options['moredots_10m']=[ (20,True,[8]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=32
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def taiwan_options(param):
	if param.endswith('/'): return options_global.basic(param,'taiwan','TWN.TWN',isadmin1=True,isdisputed=True)
	options={'gsg':'TWN.TWN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Taiwan locator'
	options['countrymap/title']='Taiwan countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (4,False,[2]), (20,3,[0]) ]
	options['countrymap/zoom']=12.5
	if param=='taiwan/_disputed':
		options['countrymap/zoom']=4
		options['moredots_10m']=[]
		options['disputed_border']=[ "CH1.CHN.Paracel Is.", "JPN.JPN.Pinnacle Is.", "PGA.PGA.Spratly Is.", 
				"SCR.SCR.Scarborough Reef", ]
		options['disputed']=[ "TWN.TWN.Taiwan", ]
		options['disputed_labels']=[
				("JPN.JPN.Pinnacle Is.", "Pinnacle Islands", '24px sans',0,-1,'+20','-20',-1,0,0),
				("TWN.TWN.Taiwan", "Taiwan", '24px sans',0,-1,'+30','+90',-1,0,0), 
				("CH1.CHN.Paracel Is.", "Paracel Islands", '24px sans',0,1,'+0','-40',-1,0,0),
				("SCR.SCR.Scarborough Reef", "Scarborough Reef", '24px sans',0,-1,'+10','+0',-1,0,0),
				("PGA.PGA.Spratly Is.", "Spratly Islands", '24px sans',0,-1,'+40','+0',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def japan_options(param):
	if param.endswith('/'): return options_global.basic(param,'japan','JPN.JPN',isadmin1=True,isdisputed=True)
	options={'gsg':'JPN.JPN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Japan locator'
	options['countrymap/title']='Japan countrymap'
	options['moredots_10m']=[ (4,False,[ 60,80, 14, 62, 12, 59, 61, 54, 84, 66, 67, 16]), ]
	options['countrymap/zoom']=3.125
	if param=='japan/_disputed':
		options['locatormap/iszoom']=True
		options['zoomlon']=147
		options['zoomlat']=45
		options['locatormap/zoom']=6.25
		options['moredots_10m']=[]
		options['disputed_border']=['RUS.RUS.Kuril Is.', "JPN.JPN.Pinnacle Is.", "KOR.KOR.Dokdo", ]
		options['disputed_labels']=[
				('RUS.RUS.Kuril Is.', 'Kuril Islands', '24px sans',0,-1,'+30','+0',-1,0,0),
				("JPN.JPN.Pinnacle Is.", "Pinnacle Islands", '24px sans',0,0,'+0','-20',-1,0,0),
				("KOR.KOR.Dokdo", "Dokdo", '24px sans',0,0,'+0','-10',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def saintpierreandmiquelon_options(param):
	if param.endswith('/'): return options_global.basic(param,'saintpierreandmiquelon','FR1.SPM',isadmin1=True)
	options={'gsg':'FR1.SPM','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Pierre and Miquelon locator'
	options['countrymap/title']='Saint Pierre and Miquelon countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(25,4)
	options['countrymap/zoom']=64
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def iceland_options(param):
	if param.endswith('/'): return options_global.basic(param,'iceland','ISL.ISL',isadmin1=True)
	options={'gsg':'ISL.ISL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-60,}
	options['locatormap/title']='Iceland locator'
	options['countrymap/title']='Iceland countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def pitcairnislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'pitcairnislands')
	options={'gsg':'GB1.PCN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Pitcairn Islands locator'
	options['countrymap/title']='Pitcairn Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
#	options['moredots_10m']=[ (10,True,[0,1,2,3]) ]
	options['centerdot']=(30,3)
#	options['ispartlabels']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['zoomdots_10m']=[ (15,False,[0,1,2,3]) ]
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=12.5
	options['countrymapdots_10m']=[ (5,False,[0,1,2,3]) ]
	return options

def frenchpolynesia_options(param):
	if param.endswith('/'): return options_global.basic(param,'frenchpolynesia','FR1.PYF',isadmin1=True)
	options={'gsg':'FR1.PYF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='French Polynesia locator'
	options['countrymap/title']='French Polynesia countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
#	options['moredots_10m']=[ (100,True,[87]) ]
	options['centerdot']=(110,2)
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	if False:
		zds=[]
		for i in range(88): zds.append(i)
		options['zoomdots_10m']=[ (5,False,zds) ]
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def frenchsouthernandantarcticlands_options(param):
	if param.endswith('/'): return options_global.basic(param,'frenchsouthernandantarcticlands','FR1.ATF',isadmin1=True)
	options={'gsg':'FR1.ATF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='French Southern and Antarctic Lands locator'
	options['countrymap/title']='French Southern and Antarctic Lands countrymap'
	options['moredots_10m']=[ (12,3,[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]) ]
	options['countrymap/zoom']=2
	options['countrymapdots_10m']=[ (8,False,[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]) ]
	options_global.handle(options,param)
	return options

def seychelles_options(param):
	if param.endswith('/'): return options_global.basic(param,'seychelles','SYC.SYC',isadmin1=True,isdisputed=True)
	options={'gsg':'SYC.SYC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Seychelles locator'
	options['countrymap/title']='Seychelles countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	dots=[]
	for i in range(26): dots.append(i)
	options['moredots_10m']=[ (12,2,dots) ]
	options['zoomdots_10m']=[ (10,False,dots) ]
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=False
	
	options['countrymap/zoom']=8
	options['countrymapdots_10m']=[ (12,False,dots) ]
	if param=='seychelles/_disputed':
		options['moredots_10m']=[]
		options['countrymap/zoom']=2
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "GB1.IOT.Br. Indian Ocean Ter.", "GB1.IOT.Diego Garcia NSF", ]
		options['disputed_labels']=[
				("GB1.IOT.Br. Indian Ocean Ter.", "British Indian Ocean Territories", '24px sans',0,0,'+0','-45',-1,0,0),
				("GB1.IOT.Diego Garcia NSF", "Diego Garcia NSF", '24px sans',0,0,'+0','+50',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def kiribati_options(param):
	if param.endswith('/'): return options_global.basic(param,'kiribati','KIR.KIR',isadmin1=True)
	options={'gsg':'KIR.KIR','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,}
	options['locatormap/title']='Kiribati locator'
	options['countrymap/title']='Kiribati countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['centerindices_10m']=[26]
	options['tripelboxes_10m']=[ [0],[1,29,34] ]
	dots=[]
	for i in range(35): dots.append(i)
	options['moredots_10m']=[ (8,False,dots) ]
	options['countrymap/zoom']=2.5
	options['countrymap/lat']=-3.369012
	options['countrymapdots_10m']=[ (8,False,[1,32]) ]
	options_global.handle(options,param)
	return options

def marshallislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'marshallislands','MHL.MHL',isadmin1=True,isdisputed=True)
	options={'gsg':'MHL.MHL','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,}
	options['locatormap/title']='Marshall Islands locator'
	options['countrymap/title']='Marshall Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	dots=[]
	for i in range(22): dots.append(i)
	options['moredots_10m']=[ (8,False,dots) ]
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (5,False,dots) ]
	options['countrymap/zoom']=8
# countrymap is weak
	if param=='marshallislands/_disputed':
		options['countrymap/zoom']=2
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "US1.UMI.Wake Atoll", ]
		options['disputed_labels']=[ ("US1.UMI.Wake Atoll", "Wake Atoll", '24px sans',0,0,'+0','-35',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def trinidadandtobago_options(param):
	if param.endswith('/'): return options_global.basic(param,'trinidadandtobago','TTO.TTO',isadmin1=True)
	options={'gsg':'TTO.TTO','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Trinidad and Tobago locator'
	options['countrymap/title']='Trinidad and Tobago countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def grenada_options(param):
	if param.endswith('/'): return options_global.basic(param,'grenada','GRD.GRD',isadmin1=True)
	options={'gsg':'GRD.GRD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Grenada locator'
	options['countrymap/title']='Grenada countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (30,3,[0]) ]
	options['countrymap/zoom']=20
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def saintvincentandthegrenadines_options(param):
	if param.endswith('/'): return options_global.basic(param,'saintvincentandthegrenadines','VCT.VCT',isadmin1=True)
	options={'gsg':'VCT.VCT','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Vincent and the Grenadines locator'
	options['countrymap/title']='Saint Vincent and the Grenadines countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def barbados_options(param):
	if param.endswith('/'): return options_global.basic(param,'barbados','BRB.BRB',isadmin1=True)
	options={'gsg':'BRB.BRB','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Barbados locator'
	options['countrymap/title']='Barbados countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def saintlucia_options(param):
	if param.endswith('/'): return options_global.basic(param,'saintlucia','LCA.LCA',isadmin1=True)
	options={'gsg':'LCA.LCA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Lucia locator'
	options['countrymap/title']='Saint Lucia countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
#	options['ispartlabels']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def dominica_options(param):
	if param.endswith('/'): return options_global.basic(param,'dominica','DMA.DMA',isadmin1=True)
	options={'gsg':'DMA.DMA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Dominica locator'
	options['countrymap/title']='Dominica countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def unitedstatesminoroutlyingislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'unitedstatesminoroutlyingislands','US1.UMI',isadmin1=True)
	options={'gsg':'US1.UMI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-130,}
	options['locatormap/title']='United States Minor Outlying Islands locator'
	options['countrymap/title']='United States Minor Outlying Islands countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['tripelboxes_10m']=[ [5],[10],[0,1,2,3,4,  6,7,8,9,  11,12] ]
	options['lon']=-120
	
	dots=[]
	for i in range(13): dots.append(i)
	options['moredots_10m']=[ (20,True,dots) ]
	options['countrymap/zoom']=1
	options['countrymapdots_10m']=[ (10,True,dots) ]
	options['countrymap/lon']=-120
	options_global.handle(options,param)
	return options

def montserrat_options(param):
	if param.endswith('/'): return options_global.basic(param,'montserrat','GB1.MSR',isadmin1=True)
	options={'gsg':'GB1.MSR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Montserrat locator'
	options['countrymap/title']='Montserrat countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (15,False,[0]) ]
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def antiguaandbarbuda_options(param):
	if param.endswith('/'): return options_global.basic(param,'antiguaandbarbuda','ATG.ATG',isadmin1=True)
	options={'gsg':'ATG.ATG','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Antigua and Barbuda locator'
	options['countrymap/title']='Antigua and Barbuda countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (10,False,[0,1]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def saintkittsandnevis_options(param):
	if param.endswith('/'): return options_global.basic(param,'saintkittsandnevis','KNA.KNA',isadmin1=True)
	options={'gsg':'KNA.KNA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Kitts and Nevis locator'
	options['countrymap/title']='Saint Kitts and Nevis countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (25,False,[0]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=20
	options_global.handle(options,param)
	return options

def unitedstatesvirginislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'unitedstatesvirginislands','US.VIR',isadmin1=True)
	options={'gsg':'US1.VIR','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='United States Virgin Islands locator'
	options['countrymap/title']='United States Virgin Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
	options['locatormap/iszoom34']=False
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=20
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def saintbarthelemy_options(param):
	if param.endswith('/'): return options_global.basic(param,'saintbarthelemy')
	options={'gsg':'FR1.BLM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Barthelemy locator'
	options['countrymap/title']='Saint Barthelemy countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=32
	options['zoomm']='10m'
	return options

def puertorico_options(param):
	if param.endswith('/'): return options_global.basic(param,'puertorico')
	options={'gsg':'US1.PRI','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Puerto Rico locator'
	options['countrymap/title']='Puerto Rico countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (10,False,[0,1,2]) ]
#	options['moredots_10m']=[ (30,True,[3]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=10
	return options

def anguilla_options(param):
	if param.endswith('/'): return options_global.basic(param,'anguilla','GB1.AIA',isadmin1=True)
	options={'gsg':'GB1.AIA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Anguilla locator'
	options['countrymap/title']='Anguilla countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['zoomdots_10m']=[ (4,False,[0,1]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=64
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def britishvirginislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'britishvirginislands')
	options={'gsg':'GB1.VGB','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='British Virgin Islands locator'
	options['countrymap/title']='British Virgin Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=16
	options['locatormap/iszoom34']=True
#	options['zoomdots_10m']=[ (4,False,[0,1,2,3,4,5]) ]
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=40
	options['zoomm']='10m'
	return options

def jamaica_options(param):
	if param.endswith('/'): return options_global.basic(param,'jamaica','JAM.JAM',isadmin1=True,isdisputed=True)
	options={'gsg':'JAM.JAM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Jamaica locator'
	options['countrymap/title']='Jamaica countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,3,[0]) ]
	options['countrymap/zoom']=10
	if param=='jamaica/_disputed':
		options['moredots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "SER.SER.Serranilla Bank", ]
		options['disputed_labels']=[
				("BJN.BJN.Bajo Nuevo Bank (Petrel Is.)", "Bajo Nuevo Bank", '24px sans',0,1,'-30','+45',-1,0,0),
				("SER.SER.Serranilla Bank", "Serranilla Bank", '24px sans',0,-1,'+10','+45',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def caymanislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'caymanislands')
	options={'gsg':'GB1.CYM','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Cayman Islands locator'
	options['countrymap/title']='Cayman Islands countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=16
	return options

def bermuda_options(param):
	if param.endswith('/'): return options_global.basic(param,'bermuda','GB1.BMU',isadmin1=True)
	options={'gsg':'GB1.BMU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Bermuda locator'
	options['countrymap/title']='Bermuda countrymap'
	options['presence']=['10m','50m'] 
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (15,4,[0]) ]
	options['countrymap/zoom']=256
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def heardislandandmcdonaldislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'heardislandandmcdonaldislands')
	options={'gsg':'AU1.HMD','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':90,}
	options['locatormap/title']='Heard Island and McDonald Islands locator'
	options['countrymap/title']='Heard Island and McDonald Islands countrymap'
	options['presence']=['10m','50m'] 
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,True)
	options['countrymap/zoom']=200
	return options

def sainthelena_options(param):
	if param.endswith('/'): return options_global.basic(param,'sainthelena','GB1.SHN',isadmin1=True)
	options={'gsg':'GB1.SHN','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Saint Helena locator'
	options['countrymap/title']='Saint Helena countrymap'
	options['presence']=['10m','50m'] 
	options['moredots_10m']=[ (10,3,[0,1,2,3]) ]
	options['countrymap/zoom']=2.5
	options['countrymapdots_10m']=[ (10,3,[0,1,2,3]) ]
	options_global.handle(options,param)
	return options

def mauritius_options(param):
	if param.endswith('/'): return options_global.basic(param,'mauritius','MUS.MUS',isadmin1=True,isdisputed=True)
	options={'gsg':'MUS.MUS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Mauritius locator'
	options['countrymap/title']='Mauritius countrymap'
	options['presence']=['10m','50m'] 
	options['moredots_10m']=[ (10,3,[0,1,2]) ]
	options['countrymap/zoom']=5
	options['countrymapdots_10m']=[ (10,3,[0,1,2]) ]
	if param=='mauritius/_disputed':
		options['countrymap/zoom']=4
		options['moredots_10m']=[]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_border']=[ "FR1.ATF.Tromelin I.", "GB1.IOT.Br. Indian Ocean Ter.", "GB1.IOT.Diego Garcia NSF", ]
		options['disputed_labels']=[
				("GB1.IOT.Br. Indian Ocean Ter.", "British Indian Ocean Territories", '24px sans',0,1,'-60','+0',-1,0,0),
				("GB1.IOT.Diego Garcia NSF", "Diego Garcia NSF", '24px sans',0,1,'-30','+30',-1,0,0), 
				("FR1.ATF.Tromelin I.", "Tromelin Island", '24px sans',0,0,'+0','-30',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def comoros_options(param):
	if param.endswith('/'): return options_global.basic(param,'comoros','COM.COM',isadmin1=True,isdisputed=True)
	options={'gsg':'COM.COM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Comoros locator'
	options['countrymap/title']='Comoros countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (20,True,[0]) ]
	options['centerdot']=(20,3)
	options['countrymap/zoom']=16
	if param=='comoros/_disputed':
		options['disputed_border']=[ "FR1.FRA.Mayotte", ]
		options['disputed_labels']=[ ("FR1.FRA.Mayotte", "Mayotte", '24px sans',0,0,'+0','+45',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def saotomeandprincipe_options(param):
	if param.endswith('/'): return options_global.basic(param,'saotomeandprincipe','STP.STP',isadmin1=True)
	options={'gsg':'STP.STP','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='São Tomé and Principe locator'
	options['countrymap/title']='São Tomé and Principe countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def caboverde_options(param):
	if param.endswith('/'): return options_global.basic(param,'caboverde','CPV.CPV',isadmin1=True)
	options={'gsg':'CPV.CPV','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':-30,}
	options['locatormap/title']='Cabo Verde locator'
	options['countrymap/title']='Cabo Verde countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (30,True,[5]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=25
	options_global.handle(options,param)
	return options

def malta_options(param):
	if param.endswith('/'): return options_global.basic(param,'malta','MLT.MLT',isadmin1=True)
	options={'gsg':'MLT.MLT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Malta locator'
	options['countrymap/title']='Malta countrymap'
	options['euromap/title']='Malta euromap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (30,4,[0]) ]
	options['euromapdots_50m']= [('MLT.MLT',24,False,[0]) ]
#	options['ispartlabels']=True
	options['countrymap/zoom']=200
	options_global.handle(options,param)
	return options

def jersey_options(param):
	if param.endswith('/'): return options_global.basic(param,'jersey')
	options={'gsg':'GB1.JEY','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Jersey locator'
	options['countrymap/title']='Jersey countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=10
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (30,3,[0]) ]
	options['countrymap/zoom']=100
	options['zoomm']='10m'
	return options

def guernsey_options(param):
	if param.endswith('/'): return options_global.basic(param,'guernsey')
	options={'gsg':'GB1.GGY','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Guernsey locator'
	options['countrymap/title']='Guernsey countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=10
	options['locatormap/iszoom34']=True
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,3)
	options['countrymap/zoom']=100
	options['zoomm']='10m'
	return options

def isleofman_options(param):
	if param.endswith('/'): return options_global.basic(param,'isleofman')
	options={'gsg':'GB1.IMN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Isle of Man locator'
	options['countrymap/title']='Isle of Man countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=10
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,4,[0]) ]
	options['countrymap/zoom']=80
	options['zoomm']='10m'
	return options

def aland_options(param):
	if param.endswith('/'): return options_global.basic(param,'aland','FI1.ALD',isadmin1=True)
	options={'gsg':'FI1.ALD','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Aland locator'
	options['countrymap/title']='Aland countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=10
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,True)
	options['countrymap/zoom']=64
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def faroeislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'faroeislands')
	options={'gsg':'DN1.FRO','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Faroe Islands locator'
	options['countrymap/title']='Faroe Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
#	options['moredots_10m']=[ (30,True,[0]) ]
	options['centerdot']=(30,True)
	options['countrymap/zoom']=80
	return options

def indianoceanterritories_options(param):
	if param.endswith('/'): return options_global.basic(param,'indianoceanterritories','AU1.IOA',isadmin1=True)
	options={'gsg':'AU1.IOA','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Indian Ocean Territories locator'
	options['countrymap/title']='Indian Ocean Territories countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['moredots_10m']=[ (10,True,[0,2]) ]
	options['countrymap/zoom']=10
	options['countrymapdots_10m']=[ (10,True,[0,2]) ]
	options_global.handle(options,param)
	return options

def britishindianoceanterritory_options(param):
	if param.endswith('/'): return options_global.basic(param,'britishindianoceanterritory')
	options={'gsg':'GB1.IOT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='British Indian Ocean Territory locator'
	options['countrymap/title']='British Indian Ocean Territory countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
#	options['moredots_10m']=[ (40,False,[5]) ]
	options['centerdot']=(40,3)
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=32
	options['zoomm']='10m'
#	options['countrymapdots_10m']=[ (10,False,[0,1,2,3,4,5,6,7,8,9]) ]
	return options

def singapore_options(param):
	if param.endswith('/'): return options_global.basic(param,'singapore','SGP.SGP',isadmin1=True)
	options={'gsg':'SGP.SGP','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Singapore locator'
	options['countrymap/title']='Singapore countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['moredots_10m']=[ (20,True,[0]) ]
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['countrymap/zoom']=64
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def norfolkisland_options(param):
	if param.endswith('/'): return options_global.basic(param,'norfolkisland')
	options={'gsg':'AU1.NFK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Norfolk Island locator'
	options['countrymap/title']='Norfolk Island countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=64
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (20,True,[0]) ]
	options['countrymap/zoom']=512
	options['zoomm']='10m'
	return options

def cookislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'cookislands','NZ1.COK',isadmin1=True)
	options={'gsg':'NZ1.COK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Cook Islands locator'
	options['countrymap/title']='Cook Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (10,2,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	options['zoomdots_10m']=[ (5,False,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	options['countrymap/zoom']=6.25
#	options['countrymapdots_10m']=[ (5,False,[0,1,2,3,4,5,6,7,8,9,10,11,12]) ]
	options_global.handle(options,param)
	return options

def tonga_options(param):
	if param.endswith('/'): return options_global.basic(param,'tonga','TON.TON',isadmin1=True)
	options={'gsg':'TON.TON','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Tonga locator'
	options['countrymap/title']='Tonga countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['centerdot']=(40,3)
#	options['moredots_10m']=[ (40,False,[0]) ]
	options['zoomdots_10m']=[ (5,False,[0,1,2,3,4,5,6,7,8,9]) ]
	options['countrymap/zoom']=12.5
	options_global.handle(options,param)
	return options

def wallisandfutuna_options(param):
# note that half of Alo is in admin1 but not in admin0
	if param.endswith('/'): return options_global.basic(param,'wallisandfutuna','FR1.WLF',isadmin1=True)
	options={'gsg':'FR1.WLF','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Wallis and Futuna locator'
	options['countrymap/title']='Wallis and Futuna countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['moredots_10m']=[ (10,3,[0,1]) ]
	options['countrymap/zoom']=32
	options_global.handle(options,param)
	return options

def samoa_options(param):
	if param.endswith('/'): return options_global.basic(param,'samoa','WSM.WSM',isadmin1=True)
	options={'gsg':'WSM.WSM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Samoa locator'
	options['countrymap/title']='Samoa countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['countrymap/zoom']=16
	options_global.handle(options,param)
	return options

def solomonislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'solomonislands','SLB.SLB',isadmin1=True)
	options={'gsg':'SLB.SLB','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Solomon Islands locator'
	options['countrymap/title']='Solomon Islands countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(70,3)
	options['countrymap/zoom']=5
	options_global.handle(options,param)
	return options

def tuvalu_options(param):
	if param.endswith('/'): return options_global.basic(param,'tuvalu')
	options={'gsg':'TUV.TUV','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Tuvalu locator'
	options['countrymap/title']='Tuvalu countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=5
	options['locatormap/iszoom34']=True
	options['centerdot']=(30,3)
	options['countrymap/zoom']=16
	return options

def maldives_options(param):
	if param.endswith('/'): return options_global.basic(param,'maldives','MDV.MDV',isadmin1=True)
	options={'gsg':'MDV.MDV','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Maldives locator'
	options['countrymap/title']='Maldives countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(45,3)
	options['countrymap/zoom']=8
	options_global.handle(options,param)
	return options

def nauru_options(param):
	if param.endswith('/'): return options_global.basic(param,'nauru','NRU.NRU',isadmin1=True)
	options={'gsg':'NRU.NRU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Nauru locator'
	options['countrymap/title']='Nauru countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots_10m']=[ (15,False,[0]) ]
	options['countrymap/zoom']=1024
	options_global.handle(options,param)
	return options

def federatedstatesofmicronesia_options(param):
	if param.endswith('/'): return options_global.basic(param,'federatedstatesofmicronesia','FSM.FSM',isadmin1=True)
	options={'gsg':'FSM.FSM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,}
	options['locatormap/title']='Federated States of Micronesia locator'
	options['countrymap/title']='Federated States of Micronesia countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	dots=[]
	for i in range(20): dots.append(i)
	options['moredots_10m']=[ (7,2,dots) ]
	options['countrymap/zoom']=2.5
	options['countrymapdots_10m']=[ (4,2,dots) ]
	options_global.handle(options,param)
	return options

def southgeorgiaandtheislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'southgeorgiaandtheislands')
	options={'gsg':'GB1.SGS','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':0,}
	options['locatormap/title']='South Georgia and the Islands locator'
	options['countrymap/title']='South Georgia and the Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(50,4)
	options['countrymap/zoom']=12.5
	return options

def falklandislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'falklandislands')
	options={'gsg':'GB1.FLK','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':-30,}
	options['locatormap/title']='Falkland Islands locator'
	options['countrymap/title']='Falkland Islands countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['centerdot']=(25,True)
	options['countrymap/zoom']=32
	return options

def vanuatu_options(param):
	if param.endswith('/'): return options_global.basic(param,'vanuatu','VUT.VUT',isadmin1=True,isdisputed=True)
	options={'gsg':'VUT.VUT','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Vanuatu locator'
	options['countrymap/title']='Vanuatu countrymap'
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(40,3)
	options['countrymap/zoom']=8
	if param=='vanuatu/_disputed':
		options['disputed_circles']=20
		options['disputed_border']=[ "FR1.NCL.Matthew and Hunter Is.", ]
		options['disputed_labels']=[ ("FR1.NCL.Matthew and Hunter Is.", "Matthew and Hunter Islands", '24px sans',0,0,'+0','-60',-1,0,0), ]
	else: options_global.handle(options,param)
	return options

def niue_options(param):
	if param.endswith('/'): return options_global.basic(param,'niue')
	options={'gsg':'NZ1.NIU','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Niue locator'
	options['countrymap/title']='Niue countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (15,False,[0]) ]
	options['countrymap/zoom']=400
	return options

def americansamoa_options(param):
	if param.endswith('/'): return options_global.basic(param,'americansamoa','US1.ASM',isadmin1=True,isdisputed=True)
	options={'gsg':'US1.ASM','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='American Samoa locator'
	options['countrymap/title']='American Samoa countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(30,3)
	options['zoomdots_10m']=[ (10,False,[0,1,2,3,4]) ]
	options['countrymap/zoom']=20
	options['countrymapdots_10m']=[ (10,False,[2,4]) ]
	if param=='americansamoa/_disputed':
		options['zoomdots_10m']=[]
		options['disputed_border']=[ "US1.ASM.Swains Island", ]
		options['countrymapdots_10m']=[]
		options['disputed_circles']=20
		options['disputed_labels']=[ ( "US1.ASM.Swains Island", "Swains Island", '24px sans',0,-1,'+25','+0',-1,0,0),]
	else: options_global.handle(options,param)
	return options

def palau_options(param):
	if param.endswith('/'): return options_global.basic(param,'palau','PLW.PLW',isadmin1=True)
	options={'gsg':'PLW.PLW','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,}
	options['locatormap/title']='Palau locator'
	options['countrymap/title']='Palau countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(40,3)
	options['zoomdots_10m']=[ (8,False,[0,1,2,3,4,5,6,7,8]) ]
	options['countrymap/zoom']=12.5
	options['countrymapdots_10m']=[ (8,False,[4,5,7]) ]
	options_global.handle(options,param)
	return options

def guam_options(param):
	if param.endswith('/'): return options_global.basic(param,'guam')
	options={'gsg':'US1.GUM','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,}
	options['locatormap/title']='Guam locator'
	options['countrymap/title']='Guam countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(30,3)
	options['zoomdots_10m']=[ (7,False,[0]) ]
	options['countrymap/zoom']=64
	return options

def northernmarianaislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'northernmarianaislands','US1.MNP',isadmin1=True)
	options={'gsg':'US1.MNP','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':180,}
	options['locatormap/title']='Northern Mariana Islands locator'
	options['countrymap/title']='Northern Mariana Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(40,3)
	options['zoomdots_10m']=[ (4,False,[0,1,2,3,4,5,6,7,8,9,10,11]) ]
	options['countrymap/zoom']=10
	options_global.handle(options,param)
	return options

def bahrain_options(param):
	if param.endswith('/'): return options_global.basic(param,'bahrain','BHR.BHR',isadmin1=True)
	options={'gsg':'BHR.BHR','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':50,}
	options['locatormap/title']='Bahrain locator'
	options['countrymap/title']='Bahrain countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=8
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['countrymap/zoom']=80
	options['zoomm']='10m'
	options_global.handle(options,param)
	return options

def coralseaislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'coralseaislands')
	options={'gsg':'AU1.CSI','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Coral Sea Islands locator'
	options['countrymap/title']='Coral Sea Islands countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['countrymap/zoom']=4
	options['countrymapdots_10m']=[ (10,False,[0]) ]
	return options

def spratlyislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'spratlyislands')
	options={'gsg':'PGA.PGA','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':175,}
	options['locatormap/title']='Spratly Islands locator'
	options['countrymap/title']='Spratly Islands countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=4
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots_10m']=[ (4,False,[0,1,2,3,4,5,6,7,8,9,10,11]) ]
	options['countrymap/zoom']=40
	return options

def clippertonisland_options(param):
	if param.endswith('/'): return options_global.basic(param,'clippertonisland')
	options={'gsg':'FR1.CLP','isinsetleft':True,'lonlabel_lat':22,'latlabel_lon':-130,}
	options['locatormap/title']='Clipperton Island locator'
	options['countrymap/title']='Clipperton Island countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,3)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['countrymap/zoom']=4
	options['countrymapdots_10m']=[ (10,False,[0]) ]
# countrymap is weak
	return options

def macaosar_options(param):
	if param.endswith('/'): return options_global.basic(param,'macaosar')
	options={'gsg':'CH1.MAC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':90,}
	options['locatormap/title']='Macao S.A.R locator'
	options['countrymap/title']='Macao S.A.R countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=32
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['countrymap/zoom']=160
	options['zoomm']='10m'
	return options

def ashmoreandcartierislands_options(param):
	if param.endswith('/'): return options_global.basic(param,'ashmoreandcartierislands')
	options={'gsg':'AU1.ATC','isinsetleft':True,'lonlabel_lat':10,'latlabel_lon':180,}
	options['locatormap/title']='Ashmore and Cartier Islands locator'
	options['countrymap/title']='Ashmore and Cartier Islands countrymap'
	options['presence']=['10m','50m'] 
	options['isfullhighlight']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['countrymap/zoom']=1024
# countrymap is weak
	return options

def bajonuevobank_options(param):
	if param.endswith('/'): return options_global.basic(param,'bajonuevobank')
	options={'gsg':'BJN.BJN','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Bajo Nuevo Bank (Petrel Is.) locator'
	options['countrymap/title']='Bajo Nuevo Bank (Petrel Is.) countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['issubland']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['countrymap/zoom']=10
	options['countrymapdots_10m']=[ (10,False,[0]) ]
# countrymap is weak
	return options

def serranillabank_options(param):
	if param.endswith('/'): return options_global.basic(param,'serranillabank')
	options={'gsg':'SER.SER','isinsetleft':True,'lonlabel_lat':21,'latlabel_lon':-30,}
	options['locatormap/title']='Serranilla Bank locator'
	options['countrymap/title']='Serranilla Bank countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
	options['issubland']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['countrymap/zoom']=10
	options['countrymapdots_10m']=[ (10,False,[0]) ]
# countrymap is weak
	return options
# the whole thing is disputed

def scarboroughreef_options(param):
	if param.endswith('/'): return options_global.basic(param,'scarboroughreef')
	options={'gsg':'SCR.SCR','isinsetleft':True,'lonlabel_lat':-10,'latlabel_lon':180,}
	options['locatormap/title']='Scarborough Reef locator'
	options['countrymap/title']='Scarborough Reef countrymap'
	options['presence']=['10m']
	options['isfullhighlight']=True
#	options['ispartlabels']=True
	options['issubland']=False
	options['locatormap/iszoom']=True
	options['locatormap/zoom']=2
	options['locatormap/iszoom34']=True
	options['centerdot']=(20,True)
	options['zoomdots_10m']=[ (10,False,[0]) ]
	options['countrymap/zoom']=10
	options['countrymapdots_10m']=[ (10,False,[0]) ]
# countrymap is weak
	return options
# the whole thing is disputed


def runparams(params):
	global isverbose_global
	output=Output()
	labels=None
	useroptions=UserOptions()
	optionpath='/'
	haslocation=False
	useroptions.addnv('cmdline','pythonshp.py '+' '.join(params))
	useroptions.addnv('version',version_global)

	for param in params:
		if param=='check':
			install.print()
			if isverbose_global: install.printlog()
			isverbose_global=True
		elif param=='verbose':
			isverbose_global=True
		elif param=='publicdomain':
			useroptions.addnv('copyright','COPYRIGHT: THIS SVG FILE IS RELEASED INTO THE PUBLIC DOMAIN')
		elif param=='list':
			path=optionpath
			if not path.endswith('/'): path=path+'/'
			regions=options_global.listoptionpath(path)
			if regions:
				regions.sort()
				for l in regions: print(l[0])
		elif param=='listall':
			names=options_global.listall()
			names.sort()
			for n in names: print(n)
		elif param=='wiki1':
			useroptions.addnv('labelfont','14px sans')
			useroptions.addnv('width',1000)
			useroptions.addnv('height',1000)
			useroptions.locatormap.addnv('spherem','50m')
			useroptions.locatormap.addnv('zoomm','50m')
			useroptions.euromap.addnv('spherem','50m')
			useroptions.countrymap.addnv('spherem','10m')
			useroptions.maximap.addnv('spherem','10m')
			useroptions.pointmap.addnv('spherem','10m')
		elif param=='wiki2':
			useroptions.addnv('labelfont','14px sans')
			useroptions.addnv('width',1000)
			useroptions.addnv('height',1000)
			useroptions.locatormap.addnv('spherem','50m')
			useroptions.locatormap.addnv('zoomm','50m')
			useroptions.euromap.addnv('spherem','50m')
			useroptions.countrymap.addnv('spherem','10m')
			useroptions.maximap.addnv('spherem','10m')
			useroptions.pointmap.addnv('spherem','10m')
			useroptions.addnv('hypso','hypso-lr_sr_ob_dr')
			useroptions.addnv('hypso_high','hypso-hr_sr_ob_dr')
			useroptions.addnv('hypsodim',500)
			if not labels:
				labels=LabelMaker()
				labels.addcommand('s=1')
		elif param=='custom': # This is an easy place to add a custom template
			useroptions.addnv('title','Custom template')
			# add more useroptions.addnv() calls here
		elif param.startswith('labels+='):
			if not labels: labels=LabelMaker()
			labels.addcommand(param[8:])
		elif param.startswith('options+='):
			useroptions.addstring(param[9:])
		elif param in ('locatormap','euromap','countrymap','maximap','pointmap'):
			if not haslocation and param in ('locatormap','euromap','countrymap','maximap'):
				print('%s requires a location to be selected (%s)'%(param,optionpath),file=sys.stderr)
				return
			options=useroptions.export(param)
#			print('options',options,file=sys.stderr)
			if param=='locatormap':
				locatormap(output,options,labels)
			elif param=='euromap':
				euromap(output,options,labels)
			elif param=='countrymap':
				countrymap(output,options,labels)
			elif param=='maximap':
				maximap(output,options,labels)
			elif param=='pointmap':
				pointmap(output,options,labels)
			output.writeto(sys.stdout)
		elif param=='admin0dbf_test': admin0dbf_test()
		elif param=='russiafix_test': russiafix_test()
		elif param=='lakesdbf_test': lakesdbf_test()
		elif param=='lakesintersection_test': lakesintersection_test()
		elif param=='borderlakes_test': borderlakes_test()
		elif param=='disputeddbf_test': disputeddbf_test()
		elif param=='disputed_test': disputed_test()
		elif param=='admin1dbf_test': admin1dbf_test()
		elif param=='admin1linesdbf_test': admin1linesdbf_test()
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
		elif param=='admin1_test': admin1_test()
		elif param=='admin0info_test': admin0info_test()
		elif param=='admin0parts_test': admin0parts_test()
		elif param=='worldcompress_test': worldcompress_test()
		elif param=='ccw_test': ccw_test()
		elif param=='png_test': png_test()
		elif param=='populateddbf_test': populateddbf_test()
		elif param=='version' or param=='--version':
			print('Version',version_global)
		elif param=='help' or param=='--help':
			print('Usage: ./pythonshp.py command1 command2 command3 ...')
			print('Commands:')
			print('\tverbose          : print more status messages')
			print('\tcheck            : show file locations and enable verbose messages')
			print('\tlist             : list root location commands')
			print('\tlistall          : list all location commands')
			print('\tpublicdomain     : add PD copyright notice in output')
			print('\twiki1            : set defaults for wikipedia, set 1')
			print('\twiki2            : set defaults for wikipedia, set 2 (hypso)')
			print('\tlabels+          : add text labels to coordinates')
			print('\toptions+         : override default settings, see codeguide.txt')
			print('\tlocatormap       : print locator map svg')
			print('\teuromap          : print EU map svg')
			print('\tcountrymap       : print country map svg')
			print('\tmaximap					: print maximal map svg')
			print('Example 1: "./pythonshp.py verbose check"')
			print('2: "./pythonshp.py list"')
			print('3: "./pythonshp.py canada/ list"')
			print('4: "./pythonshp.py listall"')
			print('5: "./pythonshp.py check publicdomain wiki1 laos locatormap > laos.svg"')
			print('6: "./pythonshp.py verbose wiki1 spain euromap | inkscape -e spain.png -"')
		else:
			if param.startswith('/'): newpath=param
			else: newpath=optionpath+'/'+param
			if not options_global.isvalidpath(newpath):
				print('Unknown command "%s"'%param,file=sys.stderr)
				return
			else:
				if not newpath.endswith('/'):
					if not optionpath.endswith('/'):
						print('Too many locations specified. Only one is supported: (%s and %s)'%(optionpath,newpath),file=sys.stderr)
						return
					options=options_global.getoptions(newpath)
					if not options:
						print('specified location does not have %s options (%s)'%(param,newpath),file=sys.stderr)
						return
					useroptions.addoptions(options)
					haslocation=True
				optionpath=newpath

if len(sys.argv)<2: runparams(['help'])
elif len(sys.argv)==2 and (sys.argv[1]=='stdin' or sys.argv[1]=='-'):
	l=sys.stdin.read()
	a=l.split('\n')
	while a.count(''): a.remove('')
	runparams(a)
else: runparams(sys.argv[1:])

if debug_global!=0: print('debug: %d'%debug_global,file=sys.stderr)
