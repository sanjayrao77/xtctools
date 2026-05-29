#!/usr/bin/python3

#  * github.com/sanjayrao77
#  * xtchbuilder.py - program to convert screenshots to XTC-format ebooks
#  * Copyright (C) 2026 Sanjay Rao
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

import base64
import json
import os
import struct
import sys
import time
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import zlib

class PNM():
	def fromfile(filename):
		f=open(filename,'rb')
		data=f.read()
		idx1=data.find(b'\n')
		if idx1<0: raise ValueError
		magic=data[:idx1]
		if magic not in (b'P5',b'P6'): raise ValueError
		data2=data[idx1+1:]
		idx2=data2.find(b'\n')
		data3=data2[idx2+1:]
		idx3=data3.find(b'\n')
		if data3[:idx3]!=b'255': raise ValueError
		dims=data2[:idx2].decode()
		(w,h)=dims.split(' ')
		pixels=data3[idx3+1:]
		return PNM(magic,int(w),int(h),pixels)
	def __init__(self,magic,width,height,data): (self.magic,self.width,self.height,self.data)=(magic,width,height,data)

class PGM():
	def fromp5(filename):
		pnm=PNM.fromfile(filename)
		cursor=0
		rows=[]
		pixels=pnm.data
		for y in range(pnm.height):
			row=pixels[cursor:cursor+pnm.width]
			cursor+=pnm.width
			rows.append(row)
		return PGM(pnm.width,pnm.height,rows)
	def __init__(self,width,height,rows): (self.width,self.height,self.rows)=(width,height,rows)
	def tobytes(self):
		ba=bytearray(('P5\n%s %s\n255\n'%(self.width,self.height)).encode())
		for row in self.rows: ba.extend(row)
		return bytes(ba)
	def clone(self):
		pgm=PGM(self.width,self.height,[])
		pgm.rows.extend(self.rows)
		return pgm
	def counter_rotate(self):
		outrows=[]
		for _ in range(self.width): outrows.append(bytearray())
		for row in self.rows:
			for i,outrow in enumerate(reversed(outrows)): outrow.append(row[i])
		out=PGM(self.height,self.width,outrows)
		return out
	def reverse(self):
		for i,r in enumerate(self.rows):
			r=bytearray(r)
			r.reverse()
			self.rows[i]=r
		self.rows.reverse()

class PPM():
	def fromp5(filename):
		pnm=PNM.fromfile(filename)
		incursor=0
		rows=[]
		pixels=pnm.data
		for y in range(pnm.height):
			row=bytearray(pnm.width*3)
			outcursor=0
			for _ in range(pnm.width):
				row[outcursor:outcursor+3]=(pixels[incursor:incursor+1]*3)
				incursor+=1
				outcursor+=3
			rows.append(row)
		return PPM(pnm.width,pnm.height,rows)
	def __init__(self,width,height,rows): (self.width,self.height,self.rows)=(width,height,rows)
	def hline(self,y,thickness):
		if y<0: return
		if y>=self.height-1: return
		green=b'\x00\xff\x00'*self.width
		while True:
			self.rows[y]=green
			y+=1
			if y==self.height: break
			thickness-=1
			if not thickness: break
	def top_crop(self,y,thickness):
		if y<=0: return
		if y>=self.height-1: return
		red=b'\xff\x00\x00'*self.width
		while True:
			y-=1
			self.rows[y]=bytearray(red)
			if not y: break
			thickness-=1
			if not thickness: break
	def bottom_crop(self,y,thickness):
		if y<=0: return
		if y>=self.height-1: return
		red=b'\xff\x00\x00'*self.width
		y=self.height-1-y
		while True:
			y+=1
			self.rows[y]=bytearray(red)
			if y==self.height-1: break
			thickness-=1
			if not thickness: break
	def left_crop(self,x,thickness):
		if x<=0: return
		if x>=self.width-1: return
		x1=x-thickness
		if x1<0: x1=0
		red=b'\xff\x00\x00'*(x-x1)
		x1=x1*3
		x=x*3
		for row in self.rows: row[x1:x]=red
	def right_crop(self,x,thickness):
		if x<=0: return
		if x>=self.width-1: return
		x=self.width-x
		x1=x+thickness
		if x1>self.width: x1=self.width
		red=b'\xff\x00\x00'*(x1-x)
		x=x*3
		x1=x1*3
		for row in self.rows: row[x:x1]=red
	def tobytes(self):
		ba=bytearray(('P6\n%s %s\n255\n'%(self.width,self.height)).encode())
		for row in self.rows: ba.extend(row)
		return bytes(ba)
	def clone(self):
		ppm=PPM(self.width,self.height,[])
		for row in self.rows: ppm.rows.append(bytearray(row))
		return ppm

class PNG():
	def parsechunk(bs):
		(c,)=struct.unpack('>I',bs[:4])
		key=bs[4:8]
		if not c: return (key,b'',bs[12:])
		if key==b'IDAT': return (key,zlib.decompress(bs[8:8+c]),bs[12+c:])
		return (key,bs[8:8+c],bs[12+c:])
	def __init__(self,filename):
		self.filename=filename
		self.width=None
		self.height=None
		self.rows=[]
	def toppm(self):
		if self.rows: return PPM(self.width,self.height,self.rows)
		f=open(self.filename,'rb')
		data=f.read()
		if data[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError
		(key,value,tail)=PNG.parsechunk(data[8:])
		if key!=b'IHDR': raise ValueError('Unexpected PNG chunk')
		(self.width,self.height,bits,colortype,u1,u2,u3)=struct.unpack('>2I5B',value)
		if bits!=8: raise ValueError('Unsupport PNG format')
		if colortype: raise ValueError('Unsupported PNG format')
		swp1=self.width+1
		stride=self.width*3
		while tail:
			(key,value,tail)=PNG.parsechunk(tail)
			if key==b'IDAT':
				off=0
				for i in range(self.height):
					if value[off]!=0: raise ValueError('Unsupported PNG compression')
					row=bytearray(stride)
					cursor=0
					for off in range(off+1,off+swp1): # enumerate(value[off+1:off+swp1]) is slightly faster
						v=value[off]
						row[cursor]=v ; cursor+=1
						row[cursor]=v ; cursor+=1
						row[cursor]=v ; cursor+=1
					off+=1
					self.rows.append(row)
		return PPM(self.width,self.height,self.rows)
	def topgm(self):
		f=open(self.filename,'rb')
		data=f.read()
		if data[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError
		(key,value,tail)=PNG.parsechunk(data[8:])
		if key!=b'IHDR': raise ValueError('Unexpected PNG chunk')
		(self.width,self.height,bits,colortype,u1,u2,u3)=struct.unpack('>2I5B',value)
		if bits!=8: raise ValueError('Unsupport PNG format')
		if colortype: raise ValueError('Unsupported PNG format')
		rows=[]
		swp1=self.width+1
		while tail:
			(key,value,tail)=PNG.parsechunk(tail)
			if key==b'IDAT':
				mv=memoryview(value)
				off=0
				for _ in range(self.height):
					if mv[off]!=0: raise ValueError('Unsupported PNG compression')
					rows.append(mv[off+1:off+swp1])
					off+=swp1
		return PGM(self.width,self.height,rows)

class Cap():
	def __init__(self,index,ent,capdefaults):
		self.index=index
		self.ent=ent
		self.capdefaults=capdefaults
		self.top_crop=None
		self.bottom_crop=None
		self.left_crop=None
		self.right_crop=None
		self.fullscreen_mode=None

		self.hline=None
		self.previous=None
		self.next=None
	def loadconfig(self,d):
		for k in ('top_crop','bottom_crop','left_crop','right_crop','fullscreen_mode'):
			if k in d: setattr(self,k,d[k])
	def get_top_crop(self): return self.top_crop if self.top_crop!=None else self.capdefaults.top_crop
	def get_bottom_crop(self): return self.bottom_crop if self.bottom_crop!=None else self.capdefaults.bottom_crop
	def get_left_crop(self): return self.left_crop if self.left_crop!=None else self.capdefaults.left_crop
	def get_right_crop(self): return self.right_crop if self.right_crop!=None else self.capdefaults.right_crop
	def get_fullscreen_mode(self): return self.fullscreen_mode if self.fullscreen_mode!=None else self.capdefaults.fullscreen_mode
	def getbareppm(self):
		if self.ent.path.endswith('.png'):
			png=PNG(self.ent.path)
			return png.toppm()
#		elif self.ent.path.endswith('.pgm'):
		else:
			return PPM.fromp5(self.ent.path)
	def getbarepgm(self):
		if self.ent.path.endswith('.png'):
			png=PNG(self.ent.path)
			return png.topgm()
#		elif self.ent.path.endswith('.pgm'):
		else:
			return PGM.fromp5(self.ent.path)
	def getdimensions(self,bareppm):
		if not bareppm: bareppm=self.getbareppm()
		return (bareppm.width,bareppm.height,bareppm)
	def getdata(self,bareppm):
		if not bareppm: bareppm=self.getbareppm()
		return (bareppm.width,bareppm.height,bareppm.tobytes(),bareppm)
	def hline_getdata(self,thickness,bareppm):
		if not bareppm: bareppm=self.getbareppm()
		ppm=bareppm.clone()
		if self.hline!=None:
			ppm.hline(self.hline,thickness)
		return (ppm.width,ppm.height,ppm.tobytes(),bareppm)
	def cropmarks_getdata(self,thickness,bareppm):
		if not bareppm: bareppm=self.getbareppm()
		ppm=bareppm.clone()
		topcrop=self.get_top_crop()
		bottomcrop=self.get_bottom_crop()
		leftcrop=self.get_left_crop()
		rightcrop=self.get_right_crop()
		if topcrop+bottomcrop<ppm.height:
			ppm.top_crop(topcrop,thickness)
			ppm.bottom_crop(bottomcrop,thickness)
		if leftcrop+rightcrop<ppm.width:
			ppm.left_crop(leftcrop,thickness)
			ppm.right_crop(rightcrop,thickness)
		return (ppm.width,ppm.height,ppm.tobytes(),bareppm)
	def getpgm(self):
		pgm=self.getbarepgm()
		topcrop=self.get_top_crop()
		bottomcrop=self.get_bottom_crop()
		vcrop=topcrop+bottomcrop
		if vcrop>=pgm.height:
			topcrop=0
			bottomcrop=0
		else:
			pgm.height-=vcrop
		pgm.rows=pgm.rows[topcrop:]
		if bottomcrop: pgm.rows=pgm.rows[:-bottomcrop]
		leftcrop=self.get_left_crop()
		rightcrop=self.get_right_crop()
		hcrop=leftcrop+rightcrop
		if hcrop>=pgm.width:
			leftcrop=0
			rightcrop=0
		else:
			pgm.width-=hcrop
		for i,r in enumerate(pgm.rows):
			if rightcrop:
				pgm.rows[i]=r[leftcrop:-rightcrop]
			else:
				pgm.rows[i]=r[leftcrop:]
		return (pgm,topcrop,bottomcrop,leftcrop,rightcrop)

class CapDefaults():
	def __init__(self):
		self.top_crop=0
		self.bottom_crop=0
		self.left_crop=0
		self.right_crop=0
		self.fullscreen_mode=0

class Caps():
	def __init__(self,path,capdefaults):
		self.path=path
		self.filelist=[]
		self.byindex={}
		self.sorted_byindex=[]
		self.capdefaults=capdefaults
		if path:
			entries=os.scandir(path)
			for ent in entries:
				if not ent.is_file(): continue
				if not ent.name.startswith('cap'): continue
				if ent.name.endswith('.png') or ent.name.endswith('.pgm'): self.filelist.append(ent)
	def prunefilelist(self,limit):
		a=[]
		for f in self.filelist:
			if f.name.startswith('cap-'): a.append(f) ; continue
			idx=int(f.name[3:-4])
			if idx<limit: a.append(f)
		self.filelist=a
		print('pruned filelist, limit:%s'%limit)
	def count(self): return len(self.filelist)
	def loadconfig(self,index,d):
		if index not in self.byindex: raise ValueError('Cap %s is in config file but not in input directory'%index)
		cap=self.byindex[index]
		cap.loadconfig(d)
	def isdowngrade(self,index,name):
		if index not in self.byindex: return False
		if name.endswith('.pgm'): return False
		return True
	def loadbyindex(self):
		if self.byindex: return
		for ent in self.filelist:
			if ent.name in ('cap-cover.png','cap-cover.pgm'):
				if self.isdowngrade(0,ent.name): continue
				cap=Cap(0,ent,self.capdefaults)
				cap.top_crop=0
				cap.bottom_crop=0
				cap.left_crop=0
				cap.right_crop=0
				cap.fullscreen_mode=2
				self.byindex[0]=cap
				continue
			idx=int(ent.name[3:-4])
			if self.isdowngrade(idx,ent.name): continue
			self.byindex[idx]=Cap(idx,ent,self.capdefaults)
		self.sorted_byindex=list(self.byindex.keys())
		self.sorted_byindex.sort()
		for i,cap in enumerate(self.sorted_byindex[1:]): self.byindex[cap].previous=self.byindex[self.sorted_byindex[i]]
		for i,cap in enumerate(self.sorted_byindex[:-1]): self.byindex[cap].next=self.byindex[self.sorted_byindex[i+1]]
	def getfirstcap(self):
		self.loadbyindex()
		return self.byindex[self.sorted_byindex[0]]
	def getlastcap(self):
		return self.byindex[self.sorted_byindex[-1]]
	def getnextcap(self,cap): return cap.next
	def getpreviouscap(self,cap): return cap.previous
	def findnearest(self,idx):
		if idx in self.byindex: return self.byindex[idx]
		for i in self.sorted_byindex:
			if idx<i: return self.byindex[i]
		return self.byindex[self.sorted_byindex[-1]]

class StepInfo():
	def __init__(self,text,command): (self.text,self.command,self.stringvar)=(text,command,tk.StringVar())

class CapView():
	def __init__(self,app):
		self.app=app
		self.capindex_field=tk.StringVar()
		self.cap=None
		self.iscrops=False
		self.ppm=None
		self.step4=None
		self.step6=None
		self.pageimage=None
		self.label_cap=None
		self.width=None
		self.height=None
	def redrawcap(self):
		if self.step4:
			(width,height,self.ppm)=self.cap.getdimensions(self.ppm)
			scale=self.app.getscale(width,height)
			(width,height,self.pagedata,self.ppm)=self.cap.cropmarks_getdata(scale,self.ppm)
		elif self.step6:
			(width,height,self.ppm)=self.cap.getdimensions(self.ppm)
			scale=self.app.getscale(width,height)
			(width,height,self.pagedata,self.ppm)=self.cap.hline_getdata(scale,self.ppm)
		else:
			(width,height,self.pagedata,self.ppm)=self.cap.getdata(self.ppm)
		scale=self.app.getscale(width,height)
		self.width=int(width/scale)
		self.height=int(height/scale)
		self.pageimage=tk.PhotoImage(data=self.pagedata).subsample(scale,scale)
		self.label_cap['image']=self.pageimage
	def jumptocap(self,cap):
		if self.cap.index==cap.index: return
		self.ppm=None
		self.cap.hline=None
		if self.step4: self.app.savecapfields()
		self.cap=cap
		self.capindex_field.set(str(self.cap.index))
		if self.step4: self.app.setcapfields(self.step4,self)
		self.redrawcap()
	def usercap(self,reason):
		try:
			val=int(self.capindex_field.get())
		except ValueError: return True
		if reason in ('focusout','return'):
			cap=self.app.caps.findnearest(val)
			self.jumptocap(cap)
		return True
	def firstcap(self):
		cap=self.app.caps.getfirstcap()
		self.jumptocap(cap)
	def previouscap(self):
		prevcap=self.app.caps.getpreviouscap(self.cap)
		if not prevcap: return
		self.jumptocap(prevcap)
	def nextcap(self):
		nextcap=self.app.caps.getnextcap(self.cap)
		if not nextcap: return
		self.jumptocap(nextcap)
	def lastcap(self):
		cap=self.app.caps.getlastcap()
		self.jumptocap(cap)
	def onclick(self,ev):
		if self.step6:
			step=self.step6
			step.capindex_field.set(str(self.cap.index))
			offset=int((ev.y/self.height)*self.ppm.height)
			step.offset_field.set(str(offset))
			self.cap.hline=offset
			self.redrawcap()
	def create_widgets(self,master):
		self.capindex_field.set(str(self.cap.index))

		frame=tk.Frame(master,bg='white')
		frame2=tk.Frame(frame,bg='white')
		button=tk.Button(frame2,text='|<',bg='white',command=self.firstcap)
		button.pack(side='left')
		button=tk.Button(frame2,text='<',bg='white',command=self.previouscap)
		button.pack(side='left')
		rusercap=master.register(self.usercap)
		entry=tk.Entry(frame2,textvariable=self.capindex_field,width=5,bg='white',validate='all',validatecommand=(rusercap,'%V'))
		entry.pack(side='left')
		entry.bind('<Return>',lambda _: self.usercap('return'))
		button=tk.Button(frame2,text='>',bg='white',command=self.nextcap)
		button.pack(side='left')
		button=tk.Button(frame2,text='>|',bg='white',command=self.lastcap)
		button.pack(side='left')
		frame2.pack()
		frame.pack(fill='x')

		mainframe=tk.Frame(master,bg='white')
		self.label_cap=tk.Label(mainframe,image=self.pageimage)
		self.label_cap.pack()
		self.label_cap.bind('<Button-1>',self.onclick)
		mainframe.pack(side='left',fill='y')

		self.redrawcap()

class Chapter():
	def __init__(self,text,cap,offset):
		(self.text,self.cap,self.offset)=(text,cap,offset)
		self.uid=-1
		self.page=None
	def resetforbuild(self): self.page=None
	def findregion(self,regionsbycap):
		if self.cap.index not in regionsbycap: raise ValueError('Couldn\'t find region for chapter "%s". Missing region for (%s:%s)?'%(self.text,self.cap.index,self.offset))
		a=regionsbycap[self.cap.index]
		if len(a)==1: return a[0]
		for r in a:
			if r.hasoriginaloffset(self.offset): return r
		raise ValueError('Couldn\t find region for chapter "%s". Missing region for (%s:%s)?'%(self.text,self.cap.index,self.offset))

class Chapters():
	def __init__(self):
		self.nextuid=1
		self.list=[]
		self.byuid={}
	def resetforbuild(self):
		for ch in self.list: ch.resetforbuild()
	def add(self,uid,ch):
		if uid<0:
			uid=self.nextuid
			self.nextuid+=1
			ch.uid=uid
			self.list.append(ch)
			self.byuid[uid]=ch
		else:
			d=self.byuid[uid]
			(d.text,d.cap,d.offset)=(ch.text,ch.cap,ch.offset)
	def loadconfig(self,caps,text,d):
		if 'cap' not in d: raise ValueError
		cap=caps.byindex[d['cap']]
		offset=d.get('offset',0)
		ch=Chapter(text,cap,offset)
		self.add(-1,ch)
	def delete(self,uid):
		for idx,ch in enumerate(self.list):
			if ch.uid==uid:
				self.list.pop(idx)
				break
	def findregions(self,regions):
		if not self.list: return
		regionsbycap={}
		for r in regions:
			cap=r.resizecap.cap
			a=regionsbycap.get(cap.index,None)
			if a==None: regionsbycap[cap.index]=[r]
			else: a.append(r)
		for ch in self.list:
			r=ch.findregion(regionsbycap)
			r.addchapter(ch)
	def fixpages(self,pages):
		pagecount=len(pages)
		for i,p in enumerate(pages):
			p.position_book=i
			p.pagecount_book=pagecount
		ch=None
		idx=0
		for p in pages:
			if p.chapter:
				ch=p.chapter
				idx=0
			else:
				p.chapter=ch
				idx+=1
			p.position_chapter=idx
		ch=-1
		count=0
		for p in reversed(pages):
			if p.chapter!=ch:
				ch=p.chapter
				count=p.position_chapter+1
			p.pagecount_chapter=count

class ScaleImage():
	def __init__(self,inwidth,inheight,outwidth,outheight):
		(self.inwidth,self.inheight,self.outwidth,self.outheight)=(inwidth,inheight,outwidth,outheight)
		self.outrow=bytearray(outwidth)
		self.wrow=[0]*outwidth
		self.slop=inheight
	def addrow(self,inrow):
		wrow=self.wrow
		ih=self.inheight
		ow=self.outwidth
		oh=self.outheight
		ret=[]
		slip=self.outheight
		slop=self.slop
		while True:
			if 0==slop:
				onerow=bytearray(ow)
				for i,wp in enumerate(wrow): onerow[i]=int(wp/ih)&255
				ret.append(onerow)
				slop=self.inheight
				wrow=[0]*ow
			if 0==slip:
				break
			if slip>slop:
				for i,p in enumerate(inrow): wrow[i]+=p*slop
				slip-=slop
				slop=0
			else:
				for i,p in enumerate(inrow): wrow[i]+=p*slip
				slop-=slip
				slip=0
		self.slop=slop
		self.wrow=wrow
		return ret
	def scalerow(self,inrow):
		iw=self.inwidth
		ow=self.outwidth
		ret=self.outrow
		slop=iw
		slip=ow
		p=inrow[0]
		wp=0
		inx=0
		outx=0
		while True:
			if 0==slop:
				ret[outx]=int(wp/iw)&255
				outx+=1
				if outx==ow: break
				slop=iw
				wp=0
			if 0==slip:
				inx+=1
				p=inrow[inx]
				slip=ow
			if slip>slop:
				wp+=p*slop
				slip-=slop
				slop=0
			else:
				wp+=p*slip
				slop-=slip
				slip=0
		return ret
	def scalepgm(self,pgm):
		pgm2=PGM(self.outwidth,self.outheight,[])
		for r in pgm.rows:
			sr=self.scalerow(r)
			rows=self.addrow(sr)
			if rows:
				pgm2.rows.extend(rows)
		return pgm2
	def tofile_scalepgm(self,pgm,fout):
		header='P5\n%s %s\n255\n'%(self.outwidth,self.outheight)
		fout.write(header.encode())
		pgm2=PGM(self.outwidth,self.outheight,[])
		for r in pgm.rows:
			sr=self.scalerow(r)
			rows=self.addrow(sr)
			for row in rows: fout.write(row)
	def counterscalepgm(self,pgm):
		pgm2=PGM(self.outheight,self.outwidth,[])
		for _ in range(self.outwidth): pgm2.rows.append(bytearray(self.outheight))
		y=0
		for r in pgm.rows:
			sr=self.scalerow(r)
			rows=self.addrow(sr)
			for row in rows:
				for i,p in enumerate(reversed(row)):
					pgm2.rows[i][y]=p
				y+=1
		return pgm2

class ResizeCap():
	def __init__(self,cap,inwidth,inheight,outwidth,outheight,bg):
		self.cap=cap
		(self.inwidth,self.inheight,self.outwidth,self.outheight,self.bg)=(inwidth,inheight,outwidth,outheight,bg)
		self.isrotate=False # rotate output clockwise
		self.padleft=0
		self.padright=0
		self.padtop=0
		self.padbottom=0
		self.trimleft=0
		self.trimright=0
		self.trimtop=0
		self.trimbottom=0
		self.scalewidth=inwidth
		self.scaleheight=inheight
		if self.outheight!=None:
			inportrait=True if inheight > inwidth else False
			outportrait=True if self.outheight > self.outwidth else False
			if inportrait!=outportrait:
				self.isrotate=True
				(self.outheight,self.outwidth)=(self.outwidth,self.outheight)
			isscale=False
			if inwidth>self.outwidth:
				if inwidth-self.outwidth>0.01*inwidth: isscale=True
			elif inwidth!=self.outwidth: 
				if self.outwidth-inwidth>0.05*inwidth: isscale=True
			if inheight>self.outheight:
				if inheight-self.outheight>0.01*inheight: isscale=True
			elif inheight!=self.outheight:
				if self.outheight-inheight>0.05*inheight: isscale=True
			if isscale:
				xscale=self.outwidth/inwidth
				yscale=self.outheight/inheight
				if xscale>yscale:
					self.scalewidth=int(inwidth*yscale)
					self.scaleheight=self.outheight
				else:
					self.scalewidth=self.outwidth
					self.scaleheight=int(inheight*xscale)
		else: # if self.outheight==None:
			if inwidth>self.outwidth:
				if inwidth-self.outwidth<=0.01*inwidth: # 800 -> 792 is a trim rather than a scale
					self.outheight=inheight
				else:
					self.scalewidth=self.outwidth
					self.scaleheight=int(self.outwidth*(inheight/inwidth))
					self.outheight=self.scaleheight
			elif inwidth==self.outwidth: self.outheight=inheight
			else:
				if self.outwidth-inwidth<=0.05*inwidth: # 5% increase is a pad rather than a scale
					self.outheight=inheight
				else:
					self.scalewidth=self.outwidth
					self.scaleheight=int(self.outwidth*(inheight/inwidth))
					self.outheight=self.scaleheight
		if self.scalewidth>self.outwidth:
			self.trimleft=(self.scalewidth-self.outwidth)>>1
			self.trimright=self.scalewidth-self.outwidth-self.trimleft
		elif self.scalewidth!=self.outwidth:
			self.padleft=(self.outwidth-self.scalewidth)>>1
			self.padright=self.outwidth-self.scalewidth-self.padleft
		if self.scaleheight>self.outheight:
			self.trimtop=(self.scaleheight-self.outheight)>>1
			self.trimbottom=self.scaleheight-self.outheight-self.trimtop
		elif self.scaleheight!=self.outheight:
			self.padtop=(self.outheight-self.scaleheight)>>1
			self.padbottom=self.outheight-self.scaleheight-self.padtop
	def makepgm(self,inpgm):
		if self.inwidth!=self.scalewidth or self.inheight!=self.scaleheight:
			si=ScaleImage(self.inwidth,self.inheight,self.scalewidth,self.scaleheight)
			outpgm=si.scalepgm(inpgm)
		else:
			outpgm=inpgm.clone()
		if self.trimtop or self.trimbottom:
			outpgm.height-=self.trimtop+self.trimbottom
			outpgm.rows=outpgm.rows[self.trimtop:self.trimtop+outpgm.height]
		if self.trimleft or self.trimright:
			outpgm.width-=self.trimleft+self.trimright
			limit=self.trimleft+outpgm.width
			for i,r in enumerate(outpgm.rows): outpgm.rows[i]=r[self.trimleft:limit]
		if self.padleft or self.padright:
			outpgm.width+=self.padleft+self.padright
			left=self.bg*self.padleft
			right=self.bg*self.padright
			for i,r in enumerate(outpgm.rows): outpgm.rows[i]=left+r+right
		if self.padtop or self.padbottom:
			r=self.bg*outpgm.width
			for _ in range(self.padtop): outpgm.rows.insert(0,r)
			for _ in range(self.padbottom): outpgm.rows.append(r)
			outpgm.height+=self.padtop+self.padbottom
		if self.isrotate:
			outpgm=outpgm.counter_rotate()
		return outpgm
	def getoutputoffset(self,offset):
		if self.isrotate: raise ValueError
		offset=int((offset*self.scaleheight)/self.inheight)
		offset-=self.trimtop
		offset+=self.padtop
		return offset

class Page():
	def __init__(self,fillheight,isstatus):
		self.isstatus=isstatus
		self.regions=[]
		self.fill=0
		self.fillleft=fillheight
		self.isblank=True
		self.index=None
		self.chapterstarts=[]
		self.chapter=None
		self.position_book=None
		self.pagecount_book=None
		self.position_chapter=None
		self.pagecount_chapter=None
		self.chunkoffset=None
		self.chunksize=None
	def addregion(self,region):
		self.fill+=region.height
		self.fillleft-=region.height
		self.regions.append(region)
		if region.chapters:
			self.isblank=False
			self.chapterstarts.extend(region.chapters)
			self.chapter=region.chapters[-1]
			self.chapter.page=self
		else:
			self.isblank=self.isblank and region.isblank
		region.page=self
	def drawstatus(self,pgm,height,textlength):
		if textlength>pgm.width: raise ValueError
		if self.pagecount_chapter==None:
			w=int(((self.position_book+1)*(pgm.width-textlength))/self.pagecount_book)
			row=(b'\x00'*w)+(b'\xff'*(pgm.width-w))
		else:
			pwmtl=pgm.width-textlength
			hw1=pwmtl>>1
			hw2=pwmtl-hw1
			w1=int(((self.position_chapter+1)*hw1)/self.pagecount_chapter)
			w2=int(((self.position_book+1)*hw2)/self.pagecount_book)
			row=(b'\x00'*w1)+(b'\xff'*(hw1-w1))+(b'\x00'*w2)+(b'\xff'*(hw2-w2+textlength))
		for _ in range(height): pgm.rows.append(bytearray(row))
		pgm.height+=height

class RLE():
	def encode(data):
		ba=bytearray()
		runval=None
		runlength=0
		nonrunlength=0
		cursor=0
		for idx,d in enumerate(data):
			if d==runval:
				runlength+=1
				if runlength==128:
					if nonrunlength:
						ba.append(nonrunlength)
						ba.extend(data[cursor:cursor+nonrunlength])
					ba.append(255) # 128|(128-1)
					ba.append(runval)
					cursor+=nonrunlength+128
					nonrunlength=0
					runlength=0
					runval=None
				continue
			if runlength>2:
				if nonrunlength:
					ba.append(nonrunlength)
					ba.extend(data[cursor:cursor+nonrunlength])
				ba.append(128|(runlength-1))
				ba.append(runval)
				cursor+=nonrunlength+runlength
				nonrunlength=0
				runlength=1
				runval=d
				continue
			nonrunlength+=runlength
			if nonrunlength>=127:
				ba.append(127)
				ba.extend(data[cursor:cursor+127])
				cursor+=127
				nonrunlength-=127
			runlength=1
			runval=d

		if runlength==1 and nonrunlength!=127:
			nonrunlength+=1
			runlength=0
		if nonrunlength:
			ba.append(nonrunlength)
			ba.extend(data[cursor:cursor+nonrunlength])
		if runlength:
			ba.append(128|(runlength-1))
			ba.append(runval)
			
		return ba
	def decode(data):
		ba=bytearray()
		ba1=bytearray(1)
		idx=0
		size=len(data)
		while idx!=size:
			d=data[idx]
			idx+=1
			if d&128:
				v=(d&127)+1
				if idx==size: raise ValueError
				ba1[0]=data[idx]
				idx+=1
				ba.extend(ba1*v)
				continue
			if idx+d>size: raise ValueError
			ba.extend(data[idx:idx+d])
			idx+=d
		return ba

class Xtg():
	@classmethod
	def writetofile(parent,pgm,fout):
		xtg=parent(pgm.width,pgm.height)
		xtg.loadpgm(pgm)
		data=xtg.tobytes()
		fout.write(data)
		return len(data)
	def __init__(self,width,height):
		self.width=width
		self.height=height
		self.rows=[]
		hb=(height+7)>>3
		self.hbytes=hb
		for _ in range(self.width): self.rows.append(bytearray(hb))
	def loadpgm(self,img):
		width=img.width
		height=img.height
		rows=[]
		if height&7: raise ValueError
#		else:
#		height=((img.height-1)|7)+1
#		blank=b'\xff'*width
#		for _ in range(height-img.height): rows.append(blank)
		rows.extend(img.rows)
		for inx in range(width):
			iny=height-1
			outrow=self.rows[inx]
			outx=0
			while True:
				c=rows[iny][inx]&128 ; iny-=1
				c|=(rows[iny][inx]&128)>>1 ; iny-=1
				c|=(rows[iny][inx]&128)>>2 ; iny-=1
				c|=(rows[iny][inx]&128)>>3 ; iny-=1
				c|=(rows[iny][inx]&128)>>4 ; iny-=1
				c|=(rows[iny][inx]&128)>>5 ; iny-=1
				c|=(rows[iny][inx]&128)>>6 ; iny-=1
				c|=(rows[iny][inx]&128)>>7 ; iny-=1
				outrow[outx]=c ; outx+=1
				if 0>iny: break
	def tobytes(self):
		bytesize=self.width*self.hbytes
		data=bytearray(22)
		data[0:4]=b'XTG\x00'
		data[4:14]=struct.pack('<HHxxI',self.height,self.width,bytesize)
		for row in self.rows: data.extend(row)
		return data

class ZlibXtg(Xtg):
	def tobytes(self):
		data=bytearray(22)
		for row in self.rows:
			packet=zlib.compress(row,9)
#			if len(packet)>255: raise ValueError
			data.append(len(packet))
			data.extend(packet)
		bytesize=len(data)
		data[0:4]=b'XTG\x00'
		data[4:14]=struct.pack('<HHxxI',self.height,self.width,bytesize)
		data[9]=122 # z
		return data

class RLEXtg(Xtg):
	def tobytes(self):
		data=bytearray(22)
		for row in self.rows: data.extend(RLE.encode(row))
		bytesize=len(data)
		data[0:4]=b'XTG\x00'
		data[4:14]=struct.pack('<HHxxI',self.height,self.width,bytesize)
		data[9]=114 # r
		return data

class Xth():
	whiterow792=b'\xff'*792
	whiterow99=b'\x00'*99
	whiterow800=b'\xff'*800
	whiterow100=b'\x00'*100
	@classmethod
	def writetofile(parent,pgm,fout):
		xth=parent(pgm.width,pgm.height)
		xth.loadpgm(pgm)
		data=xth.tobytes()
		fout.write(data)
		return len(data)
	def __init__(self,width,height):
		self.width=width
		self.height=height
		self.plane1=[]
		self.plane2=[]
		if width&7: raise ValueError('unsupported')
		wb=width>>3
	def loadpgm(self,pgm):
		width=pgm.width
		if width==800:
			whiterowlong=Xth.whiterow800
			whiterowshort=Xth.whiterow100
		elif width==792:
			whiterowlong=Xth.whiterow792
			whiterowshort=Xth.whiterow99
		if len(pgm.rows)!=self.height: raise ValueError('PGM should have %s rows but it has %s instead'%(self.height,len(pgm.rows)))
		for row in pgm.rows:
			if row==whiterowlong:
				self.plane1.append(whiterowshort)
				self.plane2.append(whiterowshort)
				continue
			ba1=bytearray()
			self.plane1.append(ba1)
			ba2=bytearray()
			self.plane2.append(ba2)
			for x in range(0,width,8):
				b1=0
				b2=0
				(c0,c1,c2,c3,c4,c5,c6,c7)=row[x:x+8]
				if c0>192: pass
				elif c0<64: b1=128 ; b2=128
				elif c0>128: b1=128
				else: b2=128
				if c1>192: pass
				elif c1<64: b1|=64 ; b2|=64
				elif c1>128: b1|=64
				else: b2|=64
				if c2>192: pass
				elif c2<64: b1|=32 ; b2|=32
				elif c2>128: b1|=32
				else: b2|=32
				if c3>192: pass
				elif c3<64: b1|=16 ; b2|=16
				elif c3>128: b1|=16
				else: b2|=16
				if c4>192: pass
				elif c4<64: b1|=8 ; b2|=8
				elif c4>128: b1|=8
				else: b2|=8
				if c5>192: pass
				elif c5<64: b1|=4 ; b2|=4
				elif c5>128: b1|=4
				else: b2|=4
				if c6>192: pass
				elif c6<64: b1|=2 ; b2|=2
				elif c6>128: b1|=2
				else: b2|=2
				if c7>192: pass
				elif c7<64: b1|=1 ; b2|=1
				elif c7>128: b1|=1
				else: b2|=1
				ba1.append(b1)
				ba2.append(b2)
	def tobytes(self):
		data=bytearray(22)
		for col in self.plane1: data.extend(col)
		for col in self.plane2: data.extend(col)
		bytesize=len(data)
		data[0:4]=b'XTH\x00'
		data[4:14]=struct.pack('<HHxxI',self.height,self.width,bytesize)
		return data

class ZlibXth(Xth):
	def tobytes(self):
		data=bytearray(22)
		for col in self.plane1:
			packet=zlib.compress(col,9)
#			if len(packet)>255: raise ValueError
			data.append(len(packet))
			data.extend(packet)
		for col in self.plane2:
			packet=zlib.compress(col,9)
#			if len(packet)>255: raise ValueError
			data.append(len(packet))
			data.extend(packet)
		bytesize=len(data)
		data[0:4]=b'XTH\x00'
		data[4:14]=struct.pack('<HHxxI',self.height,self.width,bytesize)
		data[9]=122 # z
		return data

class RLEXth(Xth):
	def tobytes(self):
		data=bytearray(22)
		for col in self.plane1: data.extend(RLE.encode(col))
		for col in self.plane2: data.extend(RLE.encode(col))
		bytesize=len(data)
		data[0:4]=b'XTH\x00'
		data[4:14]=struct.pack('<HHxxI',self.height,self.width,bytesize)
		data[9]=114 # r
		return data

class CapRegion():
	def __init__(self,isblank,height,resizecap,isfullpage,offset,blankrow,isstatus):
		(self.isblank,self.height,self.resizecap,self.isfullpage,self.offset,self.blankrow,self.isstatus)=(isblank,height,resizecap,isfullpage,offset,blankrow,isstatus)
		self.ispagestart=False
		self.ispageend=False
		self.ispagejoin=False # isblank end + isblank start
		self.isnewpagestart=False
		self.chapters=[]
		self.page=None
	def hasoriginaloffset(self,origoff):
		if self.isfullpage: return True
		topcrop=self.resizecap.cap.get_top_crop()
		origoff-=topcrop
		if origoff<0: origoff=0
		newoff=self.resizecap.getoutputoffset(origoff)
		if newoff<self.offset or newoff>self.offset+self.height: return False
		return True
	def addchapter(self,ch):
		self.isnewpagestart=True
		self.chapters.append(ch)
	def clone(self,offset,height):
		ret=CapRegion(self.isblank,height,self.resizecap,self.isfullpage,offset,self.blankrow,self.isstatus)
		(ret.ispagestart,ret.ispageend,ret.ispagejoin,ret.isnewpagestart)=(self.ispagestart,self.ispageend,self.ispagejoin,self.isnewpagestart)
		return ret
	def augment(self,cappgm,pagepgm):
		if self.isblank:
			for _ in range(self.height): pagepgm.rows.append(bytearray(self.blankrow))
		else:
			for i in range(self.offset,self.offset+self.height): pagepgm.rows.append(bytearray(cappgm.rows[i]))
		pagepgm.height+=self.height

class BlankCapRegion(CapRegion):
	def __init__(self,height,resizecap,offset,blankrow):
		super().__init__(True,height,resizecap,False,offset,blankrow,True)

class FullCapRegion(CapRegion):
	def __init__(self,height,resizecap,isstatus):
		super().__init__(False,height,resizecap,True,0,None,isstatus)

class TearCapRegion(CapRegion):
	def __init__(self,height,resizecap,offset):
		super().__init__(False,height,resizecap,False,offset,None,True)

class CapRegions():
	def __init__(self):
		self.prelist=[]
		self.list=[]
	def finish(self,halflinespacing):
		if not self.prelist: return
		region=self.prelist[0]
		region.ispagestart=True
		lastregion=region
		lastcap=region.resizecap.cap
		self.list.append(region)
		for region in self.prelist[1:]:
			cap=region.resizecap.cap
			if cap!=lastcap:
				if lastregion.isblank and region.isblank and lastregion.blankrow==region.blankrow:
					lastregion.ispagejoin=True
					lastregion.height+=region.height # merge
					continue
				lastregion.ispageend=True
				region.ispagestart=True
			else:
				if lastregion.isblank and not region.isblank and lastregion.height<halflinespacing and len(self.list)>1:
					twoago=self.list[-2]
					if twoago.resizecap.cap==cap and not twoago.isblank:
						twoago.height+=lastregion.height+region.height # merge all three
						self.list.pop()
						lastregion=twoago
						continue
			self.list.append(region)
			lastregion=region
			lastcap=cap
		lastregion.ispageend=True					
	def add(self,region): self.prelist.append(region)
	def findprevioustear(self,index):
		for cap in reversed(self.list[:index]):
			if cap.isblank: continue
			if cap.isfullpage: return None
			return cap
	def findnexttear(self,index):
		for cap in self.list[index+1:]:
			if cap.isblank: continue
			if cap.isfullpage: return None
			return cap

class Font19():
	def zdbsb(a): return zlib.decompress(base64.standard_b64decode(a))
	CHAR_0=zdbsb(b'eJxdjkESwCAMAl/JJ/nkVkHTTjngyhgMgJeIrMgHvW1xE3JJUPbEcuN9qDP08Ts/zOXWqlX6VRHqD55NOjSxYr7+3Z8JeQCaW5ln')
	CHAR_1=zdbsb(b'eJz7/x8IVv2HglWhoaFwBoQJpFatgomCJZAUDywzFAZW/V8FA/8Becymrw==')
	CHAR_2=zdbsb(b'eJydjjEOADAIAl/JJ/kkpWIahw5NbzrUECWJRgUCox4nIGsnHR583qM70nxRfuv+s8CAgwUD/rBQ')
	CHAR_3=zdbsb(b'eJyFj8ENACAIA6d0yVuyWhvRmBj74QqkoiQxJIsW2blATKZuqfRgNi9MpjZTG5zuzuTHfoDm22dQnZ8N9/KvDgA7r1E=')
	CHAR_4=zdbsb(b'eJxtz8ENACAIA8Apu2SXRFoFfNCHnoQoRjhkVAj0AePUZiDK2stZLvuKa6r8bF6/Rm/ZrehhLR1y6j3oP/Ruf+wAFXuuUg==')
	CHAR_5=zdbsb(b'eJyFjsENADAIAqdkSZakVYmpD1NeF0IAiZYkwuLD10/DSuPPVZjcNZ7CjK4dXLiRsQP6LMf9GAPqxAHMmaz+')
	CHAR_6=zdbsb(b'eJxdjtEVwDAIAqdkSZakKsU28SNBHqdKXawaIUx1w/5f344uWXolD5umrZGZ/ToLIewEuOQ3MndsKIugHyvTNJhdG53zHzHfplo=')
	CHAR_7=zdbsb(b'eJxbtQoBQnGA/zCwKnQVnI0iHEpYGKtOHMLUMXAVjAkAls+38w==')
	CHAR_8=zdbsb(b'eJxlTcERwCAMmpIlWZJqQK6ePBQCIZLEBQ2IAU33fARw3HK9nM0sgTwWMS++fyJxxsy+Z93ir4FjNJMrLTKcPAUf0QegtQ==')
	CHAR_9=zdbsb(b'eJxVj1sSACAIAk/pJbkkKT7zo5yFYCJJ+FBjOcgVRJ9S405ReuMQdlfGcDv+eSwHukvuv6gyuZEH28HYnklu6rC+9QAUfaav')
	CHAR_SPACE=b'\xff'*19*3
	charlookup={'0':CHAR_0,'1':CHAR_1,'2':CHAR_2,'3':CHAR_3,'4':CHAR_4,'5':CHAR_5,'6':CHAR_6,'7':CHAR_7, '8':CHAR_8,'9':CHAR_9,' ':CHAR_SPACE}
	def getstringlength(text):
		ret=0
		for c in text:
			bmp=Font19.charlookup[c]
			ret+=len(bmp)
		return int(ret/19)
	def drawchar(pgm,c,x,y):
		bmp=Font19.charlookup[c]
		width=int(len(bmp)/19)
		xpw=x+width
		cursor=0
		for y in range(y,y+19):
			row=pgm.rows[y]
			for i in range(width):
				row[x+i]=min(row[x+i],bmp[cursor+i])
			cursor+=width
		return width
	def drawstring(pgm,text,x,y):
		for c in text:
			x+=Font19.drawchar(pgm,c,x,y)

class Builder():
	def __init__(self):
		self.encoder=None
		self.outputdir=None
		self.caps=None
		self.caplimit=None
		self.chapters=None
		self.vars={}
		self.outputfilename=None
		self.fout=None
		self.fileoffset=None
		self.pagewidth=None
		self.pageheight=None
		self.toppad_status=None
		self.bottompad_status=None
		self.height_status=None
		self.fillheight=None
		self.bg=b'\xff'
		self.pageoverlap=None
		self.linespacing=None
		self.bottommargin=None
		self.topmargin=None
		self.issinister=False
		self.capregions=CapRegions()
		self.pages=[]
		self.pagecount=None
		self.pageindex=0
		self.capindex=0
		self.cap=None
		self.cappgm=None
		self.rcap=None
		self.rcappgm=None
		self.page=None
		self.pagepgm=None
		self.regionindex=None
		self.headersize=None
	def start(self,outputdir,caps,chapters,d):
		(self.outputdir,self.caps,self.chapters,self.vars)=(outputdir,caps,chapters,d)

		self.chapters.resetforbuild()
		if self.vars['bitdepth']==1: extension='xtc'
		elif self.vars['bitdepth']==2: extension='xtch'
		else: raise ValueError
		if self.vars['resolution']=='528x792': xtcformat='x3'
		elif self.vars['resolution']=='480x800': xtcformat='x4'
		else: raise ValueError
		if self.vars['compression'] in (None,'none'): pass
		elif self.vars['compression']=='rle': xtcformat+='-rle'
		elif self.vars['compression']=='zlib': xtcformat+='-zlib'
		else: raise ValueError
		if self.vars['sinister'] in (None,'false'): pass
		elif self.vars['sinister']=='true':
			self.issinister=True
			xtcformat+='-lefty'
		else: raise ValueError
		if self.vars['filenameformat']=='authortitle':
			self.outputfilename=self.outputdir+'%s - %s.%s.%s'%(self.vars['author_book'],self.vars['title_book'],xtcformat,extension)
		elif self.vars['filenameformat']=='title':
			self.outputfilename=self.outputdir+'%s.%s.%s'%(self.vars['title_book'],xtcformat,extension)
		elif self.vars['filenameformat']=='basic':
			self.outputfilename=self.outputdir+'output_%s.%s'%(xtcformat,extension)
		else: raise ValueError('unknown filenameformat: %s'%self.vars['filenameformat'])
		print('writing to',self.outputfilename)
		self.fout=open(self.outputfilename,'wb')
		self.caplimit=len(self.caps.sorted_byindex)
		if self.vars['resolution']=='528x792': (self.pagewidth,self.pageheight)=(792,528)
		elif self.vars['resolution']=='480x800': (self.pagewidth,self.pageheight)=(800,480)
		else: raise ValueError
		self.bottommargin=self.vars['bottommargin']
		self.topmargin=self.vars['topmargin']
		if self.topmargin*2>=self.pageheight: raise ValueError # avoids an inf loop
		if not self.vars['pagedecorations']:
			self.fillheight=self.pageheight-self.bottommargin-self.topmargin
			self.toppad_status=0
			self.bottompad_status=0
			self.height_status=0
		else:
			self.toppad_status=self.vars['toppad_status']
			self.bottompad_status=self.vars['bottompad_status']
			self.height_status=3
			self.fillheight=self.pageheight-(self.topmargin+self.toppad_status+self.bottompad_status+self.height_status)
		self.pageoverlap=self.vars['pageoverlap']
		if self.pageoverlap*2 >= self.pageheight: raise ValueError # avoids an inf loop if overlap is too large
		self.linespacing=self.vars['linespacing']
		self.bgrow=self.bg*self.pagewidth
		if self.vars['bitdepth']==1:
			if self.vars['compression']=='zlib': self.encoder=ZlibXtg
			elif self.vars['compression']=='rle': self.encoder=RLEXtg
			elif self.vars['compression'] in (None,'none'): self.encoder=Xtg
			else: raise ValueError
		elif self.vars['bitdepth']==2:
			if self.vars['compression']=='zlib': self.encoder=ZlibXth
			elif self.vars['compression']=='rle': self.encoder=RLEXth
			elif self.vars['compression'] in (None,'none'): self.encoder=Xth
			else: raise ValueError
		else: raise ValueError
	def prunepages(self):
		a=[]
		for p in self.pages:
			if p.isblank: continue
			a.append(p)
		self.pages=a
		self.pagecount=len(a)
		self.chapters.fixpages(a)
	def step_walkpages(self):
		if self.pageindex==self.pagecount:
			self.writeheaders()
			self.fout.close()
			self.fout=None
			return (True,None,None)
		if not self.page or self.page.index!=self.pageindex:
			self.page=self.pages[self.pageindex]
			self.page.index=self.pageindex
			self.pagepgm=PGM(self.pagewidth,0,[])
			self.regionindex=0
		if self.regionindex==len(self.page.regions):
			if self.pagepgm.height<self.fillheight:
				for _ in range(self.pagepgm.height,self.fillheight): self.pagepgm.rows.append(bytearray(self.bgrow))
				self.pagepgm.height=self.fillheight
			if self.topmargin and self.pagepgm.height+self.topmargin<=self.pageheight:
				for _ in range(self.topmargin): self.pagepgm.rows.insert(0,bytearray(self.bgrow))
				self.pagepgm.height+=self.topmargin
			if self.page.isstatus and self.height_status:
				textlen=0
				pagestr='  %s   '%(self.page.position_book+1)
				textlen=Font19.getstringlength(pagestr)
				for _ in range(self.toppad_status): self.pagepgm.rows.append(bytearray(self.bgrow))
				self.pagepgm.height+=self.toppad_status
				self.page.drawstatus(self.pagepgm,self.height_status,textlen)
				for _ in range(self.bottompad_status): self.pagepgm.rows.append(bytearray(self.bgrow))
				self.pagepgm.height+=self.bottompad_status
				Font19.drawstring(self.pagepgm,pagestr,self.pagepgm.width-textlen,self.pagepgm.height-self.bottompad_status-19)
			if self.issinister: self.pagepgm.reverse()
			size=self.encoder.writetofile(self.pagepgm,self.fout)
			self.page.chunkoffset=self.fileoffset
			self.page.chunksize=size
			self.fileoffset+=size
			self.pageindex+=1
			return (False,None,self.pagepgm)
		region=self.page.regions[self.regionindex]
		if self.cap!=region.resizecap.cap:
			rc=region.resizecap
			self.cap=rc.cap
			(cappgm,_,_,_,_)=self.cap.getpgm()
			self.cappgm=rc.makepgm(cappgm)
			return (False,cappgm,None)
		region.augment(self.cappgm,self.pagepgm)
		self.regionindex+=1
		return (False,None,None)
	def countheaders(self):
		count=56 # XTC/XTCH
		count+=256 # metadata
		count+=len(self.chapters.list)*96
		count+=self.pagecount*16
		self.headersize=count
	def writeheaders(self):
		if self.fout.seek(0): raise ValueError
		if self.vars['bitdepth']==2: magic=0x48435458 # xtch
		else: magic=0x00435458 # xtc
		version=1
		pagecount=self.pagecount
		readdirection=0
		hasmetadata=1
		hasthumbnails=0
		haschapters=1 if len(self.chapters.list) else 0
		currentpage=1
		metadataoffset=56
		chapteroffset=metadataoffset+256 if haschapters else 0
		indexoffset=metadataoffset+256+len(self.chapters.list)*96
		dataoffset=indexoffset+self.pagecount*16
		thumboffset=0
		xtc=struct.pack('<IHH4BI5Q',magic,version,pagecount,readdirection,hasmetadata,hasthumbnails,haschapters,currentpage,
				metadataoffset,indexoffset,dataoffset,thumboffset,chapteroffset)
		if len(xtc)!=56: raise ValueError
		self.fout.write(xtc)
		metadata=bytearray(256)
		s=self.vars['title_book'].encode()[:128]
		metadata[0:len(s)]=s
		s=self.vars['author_book'].encode()[:64]
		metadata[128:128+len(s)]=s
		s=self.vars['publisher_book'].encode()[:32]
		metadata[192:192+len(s)]=s
		s=self.vars['language_book'].encode()[:16]
		metadata[224:224+len(s)]=s
		metadata[240:248]=struct.pack('<IHH',int(time.time()),0,len(self.chapters.list))
		if len(metadata)!=256: raise ValueError
		self.fout.write(metadata)
		for ch in self.chapters.list:
			ba=bytearray(96)
			s=ch.text.encode()[:80]
			ba[:len(s)]=s
			ba[80:84]=struct.pack('<HH',ch.page.position_book+1,ch.page.position_book+ch.page.pagecount_chapter)
			self.fout.write(ba)
		for p in self.pages:
			entry=struct.pack('<QIHH',p.chunkoffset,p.chunksize,self.pageheight,self.pagewidth)
			self.fout.write(entry)
		print('wrote headers')
	def buildpages(self):
		self.chapters.findregions(self.capregions.list)
		for region in self.capregions.list:
			if not region.isblank: continue
			if region.ispagejoin or region.ispagestart or region.ispageend:
				region.height=self.linespacing
		lineheight=self.pageoverlap
		exs=self.vars['excessivespace']
		exc=self.vars['excessivecut']
		if exs and exc and exs>=exc:
			if lineheight>exs:
				for region in self.capregions.list:
					if not region.isblank: continue
					if region.height>lineheight: region.height=self.linespacing
					elif region.height>exs: region.height-=exc
			else:
				for region in self.capregions.list:
					if not region.isblank: continue
					if region.height>exs: region.height-=exc
		else:
			for region in self.capregions.list:
				if not region.isblank: continue
				if region.height>lineheight: region.height=self.linespacing
		pageoverlapx2=self.pageoverlap*2
		fillheightd2=self.fillheight>>1
		page=None
		capregionindex=0
		capregionlimit=len(self.capregions.list)
		capregion=None
		regionoffset=None
		regionleft=None
		while True:
			if capregionindex==capregionlimit: break
			if not capregion:
				capregion=self.capregions.list[capregionindex]
				if capregion.isnewpagestart: page=None
				regionoffset=capregion.offset
				regionleft=capregion.height
			if not regionleft:
				capregion=None ; capregionindex+=1
				continue
			if capregion.isfullpage:
				page=Page(self.pageheight,capregion.isstatus)
				page.addregion(capregion)
				self.pages.append(page)
				page=None
				capregion=None ; capregionindex+=1
				continue
			if not page or not page.fillleft:
				page=Page(self.fillheight,True)
				self.pages.append(page)
				if capregion.isblank:
					capregion=None ; capregionindex+=1
					continue
			if regionleft<=page.fillleft:
				page.addregion(capregion)
				capregion=None ; capregionindex+=1
				continue
			if page.fillleft<=self.pageoverlap:
				page=None
				continue
			if capregion.isblank:
				page=None
				capregion=None ; capregionindex+=1
				continue
			if page.fill:
				if regionleft<=pageoverlapx2: # a small convenience
					page=None
					continue
				if regionleft>fillheightd2: # try to start in-line illustrations on a new page
					lastregion=self.capregions.findprevioustear(capregionindex)
					nextregion=self.capregions.findnexttear(capregionindex)
					if lastregion and nextregion and lastregion.height<pageoverlapx2 and nextregion.height<pageoverlapx2:
						page=None
						continue
			region=capregion.clone(regionoffset,page.fillleft)
			shift=page.fillleft-self.pageoverlap
			capregion=capregion.clone(regionoffset+shift,capregion.height-shift)
			regionoffset+=shift
			regionleft-=shift
			page.addregion(region)
			page=None
			
	def step_walkcaps(self):
		if self.capindex==self.caplimit:
			self.capregions.finish(self.linespacing>>1)
			self.buildpages()
			self.prunepages()
			self.countheaders()
			self.fout.write(b'\x00'*self.headersize)
			self.fileoffset=self.headersize
			print('pagecount',self.pagecount)
			return True
		if not self.cap or self.cap.index!=self.caps.sorted_byindex[self.capindex]:
			self.cap=self.caps.byindex[self.caps.sorted_byindex[self.capindex]]
			self.rcap=None
			self.rcappgm=None
		cap=self.cap
		if not self.rcap:
			if cap.fullscreen_mode==1: # omit
				print('omitting %s'%self.capindex)
				self.capindex+=1
				return
			if cap.fullscreen_mode==2: # full scale
				(cappgm,topcrop,bottomcrop,leftcrop,rightcrop)=cap.getpgm()
				rc=ResizeCap(cap,cappgm.width,cappgm.height,self.pagewidth,self.pageheight,self.bg)
				region=FullCapRegion(self.pageheight,rc,False)
				self.capregions.add(region)
				self.capindex+=1
				return cappgm
			if cap.fullscreen_mode==3: # full scale with status
				(cappgm,topcrop,bottomcrop,leftcrop,rightcrop)=cap.getpgm()
				rc=ResizeCap(cap,cappgm.width,cappgm.height,self.pagewidth,self.fillheight,self.bg)
				region=FullCapRegion(self.fillheight,rc,True)
				self.capregions.add(region)
				self.capindex+=1
				return cappgm
#			if cap.fullscreen_mode: raise ValueError
			(cappgm,topcrop,bottomcrop,leftcrop,rightcrop)=cap.getpgm()
			self.cappgm=cappgm
			self.rcap=ResizeCap(cap,cappgm.width,cappgm.height,self.pagewidth,None,self.bg)
			if not self.rcap.outheight:
				self.capindex+=1
				return
			return

		if not self.rcappgm:
			self.rcappgm=self.rcap.makepgm(self.cappgm)
			return self.rcappgm

		pgm=self.rcappgm
		start=0
		cursor=0
		while True:
			one=bytes(pgm.rows[cursor][:1])*pgm.width
			for cursor in range(cursor,pgm.height):
				if one!=pgm.rows[cursor]: break
			else:
				region=BlankCapRegion(cursor-start,self.rcap,start,one)
				self.capregions.add(region)
				self.capindex+=1
				return
			blankheight=cursor-start
			if blankheight:
				region=BlankCapRegion(blankheight,self.rcap,start,one)
				self.capregions.add(region)
				start=cursor
				continue
			cursor+=1
			for cursor in range(cursor,pgm.height):
				one=bytes(pgm.rows[cursor][:1])*pgm.width
				if one==pgm.rows[cursor]: break
			else:
				region=TearCapRegion(cursor-start,self.rcap,start)
				self.capregions.add(region)
				self.capindex+=1
				return
			region=TearCapRegion(cursor-start,self.rcap,start)
			self.capregions.add(region)
			start=cursor
			cursor+=1

class ChapterSearch():
	def __init__(self,margin,cap):
		self.margin=margin
		self.cap=cap
	def step(self):
		self.cap=self.cap.next
		if not self.cap: return (True,None)
		pgm=self.cap.getbarepgm()
		crop=self.cap.get_top_crop()
		rows=pgm.rows[crop:]
		one=bytes(rows[0][:1])*pgm.width
		count=0
		for row in rows:
			if row!=one: break
			count+=1
		if count>=self.margin:
			print('Chapter search found cap %s with margin %s'%(self.cap.index,count))
			return (True,self.cap)
		return (False,self.cap)
		

class CLIBuild():
	CFGFILENAME='xtchbuild.cfg'
	def __init__(self,configfile,inputdir,outputdir):
		(self.configurationfile,self.inputdir,self.outputdir)=(configfile,inputdir,outputdir)
		self.title_book=''
		self.author_book=''
		self.publisher_book=''
		self.language_book=''
		self.filenameformat=None
		self.pagedecorations=None
		self.toppad_status=1
		self.bottompad_status=4
		self.capdefaults=CapDefaults()
		self.pageoverlap=48
		self.linespacing=16
		self.excessivespace=None
		self.excessivecut=None
		self.bottommargin=4
		self.topmargin=8
		self.resolution='528x792'
		self.compression=None
		self.sinister=None
		self.bitdepth=2
		self.chaptermargin=100
		self.caps=None
		self.chapters=Chapters()
		self.builder=None
	def setinputdir(self,inputdir):
		self.inputdir=inputdir
		self.caps=Caps(self.inputdir,self.capdefaults)
	def loadconfigfile(self,fn):
		print('using config file',fn)
		self.configurationfile=fn
		f=open(fn,'r')
		if not self.inputdir:
			while True:
				l=f.readline()
				if not l: break
				d=json.loads(l)
				(record,key,value)=(d['record'],d['key'],d['value'])
				if record=='global' and key=='inputdir':
					self.setinputdir(value)
					break
			if f.seek(0): raise ValueError

		self.caps.loadbyindex()
		while True:
			l=f.readline()
			if not l: break
			d=json.loads(l)
			(record,key,value)=(d['record'],d['key'],d['value'])
			if record=='global':
				if key=='inputdir': pass
				elif key=='outputdir': self.outputdir=self.outputdir or value
				elif key=='title_book': self.title_book=value
				elif key=='author_book': self.author_book=value
				elif key=='publisher_book': self.publisher_book=value
				elif key=='language_book': self.language_book=value
				elif key=='filenameformat':
					if value in ('authortitle','basic','title'): self.filenameformat=value
					else: raise ValueError
				elif key=='pagedecorations':
					if value in (0,1): self.pagedecorations=value
					else: raise ValueError
				elif key=='toppad_status': self.toppad_status=value
				elif key=='bottompad_status': self.bottompad_status=value
				elif key=='top_crop': self.capdefaults.top_crop=value
				elif key=='bottom_crop': self.capdefaults.bottom_crop=value
				elif key=='left_crop': self.capdefaults.left_crop=value
				elif key=='right_crop': self.capdefaults.right_crop=value
				elif key=='fullscreen_mode': self.capdefaults.fullscreen_mode=value
				elif key=='pageoverlap': self.pageoverlap=value
				elif key=='bottommargin': self.bottommargin=value
				elif key=='topmargin': self.topmargin=value
				elif key=='linespacing': self.linespacing=value
				elif key=='excessivespace': self.excessivespace=value
				elif key=='excessivecut': self.excessivecut=value
				elif key=='resolution':
					if value in ('528x792','480x800'): self.resolution=value
					else: raise ValueError
				elif key=='compression':
					if value in ('none','rle','zlib'): self.compression=value
					else: raise ValueError
				elif key=='bitdepth':
					if value in (1,2): self.bitdepth=value
					else: raise ValueError
				elif key=='sinister':
					if value in ('true','false'): self.sinister=value
					else: raise ValueError
				elif key=='chaptermargin': self.chaptermargin=value
				else: raise ValueError
			elif record=='cap': self.caps.loadconfig(key,value)
			elif record=='chapter': self.chapters.loadconfig(self.caps,key,value)
			else: raise ValueError
	def lookforconfig(self):
		if self.inputdir:
			path=self.inputdir+CLIBuild.CFGFILENAME
			if os.path.isfile(path): return self.loadconfigfile(path)
		if self.outputdir:
			path=self.outputdir+CLIBuild.CFGFILENAME
			if os.path.isfile(path): return self.loadconfigfile(path)
	def makebuilder(self):
		self.builder=Builder()
		d={}
		names=('title_book','author_book','publisher_book','language_book','filenameformat','pagedecorations',
				'toppad_status','bottompad_status','capdefaults','pageoverlap','bottommargin','topmargin','linespacing',
				'excessivespace','excessivecut',
				'resolution','bitdepth','compression','sinister')
		for n in names: d[n]=getattr(self,n)
		self.builder.start(self.outputdir,self.caps,self.chapters,d)
	def start(self,caplimit=None):
		if self.inputdir:
			self.setinputdir(self.inputdir)
			if caplimit: self.caps.prunefilelist(caplimit)
		if self.configurationfile: self.loadconfigfile(self.configurationfile)
		else: self.lookforconfig()
		if not self.configurationfile: raise ValueError
		if not self.inputdir: raise ValueError
		if not self.outputdir: raise ValueError
		self.makebuilder()
	def walkcaps(self):
		capcount=0
		while True:
			ret=self.builder.step_walkcaps()
			if ret==True: break
			if ret!=None:
				print('\rCaps: %s '%(self.builder.capindex),end='',flush=True)
	def walkpages(self):
		capcount=0
		pagecount=0
		while True:
			(isdone,cappgm,pagepgm)=self.builder.step_walkpages()
			if isdone:
				print()
				print('Builder is finished')
				break
			if cappgm: capcount+=1
			if pagepgm: pagecount+=1
			print('\rCaps: %s, Pages: %s '%(capcount,pagecount),end='',flush=True)

class Application(tk.Frame):
	def __init__(self,master=None,inputdir=None,outputdir=None,configfile=None,imagewidth=400,imageheight=600):
		super().__init__(master)
		self.master=master
		self.imagewidth=imagewidth
		self.imageheight=imageheight
		CLIBuild.__init__(self,configfile,None,outputdir)
		self.capview=CapView(self)
		self.isbusy=False
		self.isbuilding=False
		self.issearching=False
		self.isstop=False
		self.chaptersearch=None
		self.steps={}
		steplist=((0,'Step 1. Select directories',self.step0_command), (1,'Step 2. Enter book info',self.step1_command),
(2,'Step 3. Select filename format',self.step2_command), (3,'Step 4. Select page decorations',self.step3_command),
(9,'Step 5. Input page defaults',self.step9_command), (4,'Step 6. Format input pages',self.step4_command),
(5,'Step 7. Review page spacing',self.step5_command), (6,'Step 8. Edit chapters',self.step6_command),
(7,'Step 9. Select output format',self.step7_command), (8,'Step 10. Build XTC file',self.step8_command))
		for (i,text,command) in steplist: self.steps[i]=StepInfo(text,command)
		self.pack()
		self.create_widgets()
		self.setinputdir(inputdir)
		if self.configurationfile: self.loadconfigfile(self.configurationfile)
		else: self.lookforconfig()
		for s in self.steps.values(): s.command(isrefresh=True)

	def setinputdir(self,inputdir):
		CLIBuild.setinputdir(self,inputdir)
	def loadconfigfile(self,fn): CLIBuild.loadconfigfile(self,fn)
	def lookforconfig(self): CLIBuild.lookforconfig(self)
	def saveconfig(self):
		if not self.configurationfile: return
		savefilename=self.configurationfile+'.new'
		tempfilename=self.configurationfile+'.temp'
		print('saving configuration to',savefilename)
		if False:
			print('not saving configuration')
			return
		f=open(savefilename,'w')
		globalnames=('inputdir','outputdir','title_book','author_book','publisher_book','language_book','filenameformat',
				'pagedecorations','toppad_status','bottompad_status','pageoverlap','bottommargin','topmargin','linespacing',
				'excessivespace','excessivecut',
				'resolution','bitdepth','compression','sinister','chaptermargin')
		capdefnames=('top_crop','bottom_crop','left_crop','right_crop','fullscreen_mode')
		for n in globalnames:
			v=getattr(self,n)
			if v==None: continue
			f.write(json.dumps({'record':'global','key':n,'value':v})) ; f.write('\n')
		for n in capdefnames:
			v=getattr(self.capdefaults,n)
			if not v: continue
			f.write(json.dumps({'record':'global','key':n,'value':v})) ; f.write('\n')
		capnames=('top_crop','bottom_crop','left_crop','right_crop','fullscreen_mode')
		for idx in self.caps.sorted_byindex:
			cap=self.caps.byindex[idx]
			d={}
			for n in capnames:
				v=getattr(cap,n)
				if v!=None: d[n]=v
			if not d: continue
			f.write(json.dumps({'record':'cap','key':idx,'value':d})) ; f.write('\n')
		for ch in self.chapters.list:
			f.write(json.dumps({'record':'chapter','key':ch.text,'value':{'cap':ch.cap.index,'offset':ch.offset}})) ; f.write('\n')
		f.close()

		isexists=os.path.isfile(self.configurationfile)
		if isexists: os.rename(self.configurationfile,tempfilename)
		os.rename(savefilename,self.configurationfile)
		if isexists: os.unlink(tempfilename)
	def setcapfields(self,step,capview):
		step.croptop_field.set('' if capview.cap.top_crop==None else str(capview.cap.top_crop))
		step.cropbottom_field.set('' if capview.cap.bottom_crop==None else str(capview.cap.bottom_crop))
		step.cropleft_field.set('' if capview.cap.left_crop==None else str(capview.cap.left_crop))
		step.cropright_field.set('' if capview.cap.right_crop==None else str(capview.cap.right_crop))
		step.full_radio.set('0' if capview.cap.fullscreen_mode==None else str(capview.cap.fullscreen_mode))
	def create_widgets(self):
		frame=tk.Frame(self)
		label=tk.Label(frame,text='XTC Builder')
		label.grid(row=0,column=0,sticky='news')
		button=tk.Button(frame,text='Quit',fg='red',command=self.quit)
		button.grid(row=0,column=1,sticky='news')
		frame.pack(fill='x')
		frame.columnconfigure(0,weight=1)

		self.frame_body=tk.Frame(self)

		self.frame_left=tk.Frame(self.frame_body)
		self.frame_right=tk.Frame(self.frame_body,bg='white')

		for i,v in self.steps.items():
			frame=tk.Frame(self.frame_left)
			label=tk.Label(frame,text=v.text,anchor='w',justify='left',wraplength=200)
			label.pack(side='left')
			button=tk.Button(frame,text='>',command=v.command)
			button.pack(side='right')
			frame.pack(fill='x')
			label=tk.Label(self.frame_left,textvariable=v.stringvar,anchor='e',justify='right')
			label.pack(fill='x')

		self.frame_left.pack(side='left',fill='y',padx='5')
		self.frame_right.pack(side='left',fill='y',padx='5')
		self.frame_body.pack(fill='x')

	def quit(self):
		print("quit called, exiting")
		self.master.destroy()
	def steptitle(self,title):
		label=tk.Label(self.frame_right,text=title)
		label.pack(fill='x')
		w=tk.Frame(self.frame_right,bg='black',height=1)
		w.pack(fill='x')
	def stepsave(self,command):
		button=tk.Button(self.frame_right,text='Save and continue',command=command)
		button.pack(fill='x',pady=(40,10),padx=10)
		frame=tk.Frame(self.frame_right,bg='black',height=1)
		frame.pack(side='bottom',fill='x',pady=1)
	def inputdir_pick(self):
		step=self.steps[0]
		path=filedialog.askdirectory(title='Select input directory')
		if not path: return
		if not path.endswith('/') and not path.endswith('\\'): path=path+'/'
		caps=Caps(path,None)
		step.inputdir=path
		step.inputq.set('Select input directory:\n%s\nCapture files found: %s'%(step.inputdir,caps.count()))
	def outputdir_pick(self):
		step=self.steps[0]
		path=filedialog.askdirectory(title='Select output directory')
		if not path: return
		if not path.endswith('/') and not path.endswith('\\'): path=path+'/'
		step.outputdir=path
		step.outputq.set('Select output directory:\n%s'%(step.outputdir))
	def saveiodirs(self):
		step=self.steps[0]
		self.outputdir=step.outputdir
		self.setinputdir(step.inputdir)
		self.lookforconfig()
		if not self.configurationfile:
			self.configurationfile=self.outputdir+CLIBuild.CFGFILENAME
		self.saveconfig()
		step.command(isrefresh=True)
		self.step1_command()
	def step0_command(self,isrefresh=False):
		t=[]
		if self.inputdir and self.outputdir:
			t.append('input: ')
			t.append(self.inputdir)
			if t: t.append('\n')
			t.append('output: ')
			t.append(self.outputdir)
		self.steps[0].stringvar.set(''.join(t))
		if isrefresh: return
		if self.isbusy: return

		step=self.steps[0]
		step.inputdir=None
		step.outputdir=None
		step.inputq=tk.StringVar(value='Select input directory:')
		step.outputq=tk.StringVar(value='Select output directory:')
		step.capcount_text=tk.StringVar()
		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Select Directories')

		label=tk.Label(self.frame_right,textvariable=step.inputq,bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0))
		button=tk.Button(self.frame_right,text='Pick',command=self.inputdir_pick)
		button.pack(fill='x',padx=10)
		label=tk.Label(self.frame_right,textvariable=step.outputq,bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0))
		button=tk.Button(self.frame_right,text='Pick',command=self.outputdir_pick)
		button.pack(fill='x',padx=10)

		self.stepsave(self.saveiodirs)
	def savebookinfo(self):
		step=self.steps[1]
		self.title_book=step.title_field.get()
		self.author_book=step.author_field.get()
		self.publisher_book=step.publisher_field.get()
		self.language_book=step.language_field.get()
		self.saveconfig()
		step.command(isrefresh=True)
		self.step2_command()
	def step1_command(self,isrefresh=False):
		text=''
		if self.title_book and self.author_book: text='Ok'
		self.steps[1].stringvar.set(text)
		if isrefresh: return
		if self.isbusy: return

		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Book Info')

		step=self.steps[1]
		step.title_field=tk.StringVar(value=self.title_book)
		step.author_field=tk.StringVar(value=self.author_book)
		step.publisher_field=tk.StringVar(value=self.publisher_book)
		step.language_field=tk.StringVar(value=self.language_book)
		label=tk.Label(self.frame_right,text='Book title (128 letters)',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(20,0))
		entry=tk.Entry(self.frame_right,textvariable=step.title_field,width=32,bg='white')
		entry.pack(fill='x',padx=10)
		label=tk.Label(self.frame_right,text='Book author (64 letters)',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		entry=tk.Entry(self.frame_right,textvariable=step.author_field,width=32,bg='white')
		entry.pack(fill='x',padx=10)
		label=tk.Label(self.frame_right,text='Book publisher (32 letters)',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		entry=tk.Entry(self.frame_right,textvariable=step.publisher_field,width=32,bg='white')
		entry.pack(fill='x',padx=10)
		label=tk.Label(self.frame_right,text='Book language (16 letters, e.g. "en-US")',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		entry=tk.Entry(self.frame_right,textvariable=step.language_field,width=16,bg='white')
		entry.pack(fill='x',padx=10)

		self.stepsave(self.savebookinfo)
	def savefilenameformat(self):
		step=self.steps[2]
		text=step.radio.get()
		self.filenameformat=text
		self.saveconfig()
		step.command(isrefresh=True)
		self.step3_command()
	def step2_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return

		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Filename Format')

		step=self.steps[2]
		step.radio=tk.StringVar(value=self.filenameformat or 'basic')
		label=tk.Label(self.frame_right,text='Filename format for XTC output files:',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(20,0))

		frame=tk.Frame(self.frame_right,bg='white')
		text='AUTHOR - TITLE.FORMAT.xtc/xtch'
		if self.author_book and self.title_book:
			text='%s - %s.FORMAT.xtc/xtch'%(self.author_book,self.title_book)
		radio=tk.Radiobutton(frame,value='authortitle',variable=step.radio,text=text,bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		frame=tk.Frame(self.frame_right,bg='white')
		text='TITLE.FORMAT.xtc/xtch'
		if self.title_book:
			text='%s.FORMAT.xtc/xtch'%(self.title_book)
		radio=tk.Radiobutton(frame,value='title',variable=step.radio,text=text,bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='basic',variable=step.radio,text='output_FORMAT.xtc/xtch',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		self.stepsave(self.savefilenameformat)
	def savedecorations(self):
		step=self.steps[3]
		try:
			self.pagedecorations=int(step.radio.get())
			self.toppad_status=int(step.top_field.get())
			self.bottompad_status=int(step.bottom_field.get())
			self.bottommargin=int(step.bottommargin_field.get())
			self.topmargin=int(step.topmargin_field.get())
		except ValueError: return
		self.saveconfig()
		step.command(isrefresh=True)
		self.step9_command()
	def step3_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return

		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Page Decorations')

		step=self.steps[3]
		step.radio=tk.StringVar(value=str(self.pagedecorations) if self.pagedecorations else '0')
		step.top_field=tk.StringVar(value=str(self.toppad_status) if self.toppad_status!=None else '')
		step.bottom_field=tk.StringVar(value=str(self.bottompad_status) if self.bottompad_status!=None else '')
		step.bottommargin_field=tk.StringVar(value=str(self.bottommargin) if self.bottommargin!=None else '')
		step.topmargin_field=tk.StringVar(value=str(self.topmargin) if self.topmargin!=None else '')
		label=tk.Label(self.frame_right,text='Status line:',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(20,0))

		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='0',variable=step.radio,bg='white',text='No status line',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='1',variable=step.radio,bg='white',text='Progress bar on bottom',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Padding above status line, in display pixels',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.top_field,width=2)
		entry.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Padding below status line, in display pixels',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.bottom_field,width=2)
		entry.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Top padding, in case the top bezel overlaps the screen',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.topmargin_field,width=2)
		entry.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Bottom padding, on pages without a status line',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10,pady=(10,0))
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.bottommargin_field,width=2)
		entry.pack(side='left')
		frame.pack(fill='x',padx=10)

		self.stepsave(self.savedecorations)
	def getscale(self,width,height):
		xscale=max(1,int((width+self.imagewidth-1)/self.imagewidth))
		yscale=max(1,int((height+self.imageheight-1)/self.imageheight))
		scale=max(xscale,yscale)
		return scale
	def usercrop(self,reason):
		step=self.steps[4]
		if reason not in ('focusout','return'): return True
		ischange=False
		try:
			top=int(step.croptop_global.get())
			bottom=int(step.cropbottom_global.get())
			left=int(step.cropleft_global.get())
			right=int(step.cropright_global.get())
		except ValueError: return True
		if top!=self.capdefaults.top_crop:
			self.capdefaults.top_crop=top
			if step.croptop_field.get()=='': ischange=True
		if bottom!=self.capdefaults.bottom_crop:
			self.capdefaults.bottom_crop=bottom
			if step.cropbottom_field.get()=='': ischange=True
		if left!=self.capdefaults.left_crop:
			self.capdefaults.left_crop=left
			if step.cropleft_field.get()=='': ischange=True
		if right!=self.capdefaults.right_crop:
			self.capdefaults.right_crop=right
			if step.cropright_field.get()=='': ischange=True

		cap=step.capview.cap
		try:
			top=step.croptop_field.get()
			top=None if top=='' else int(top)
			bottom=step.cropbottom_field.get()
			bottom=None if bottom=='' else int(bottom)
			left=step.cropleft_field.get()
			left=None if left=='' else int(left)
			right=step.cropright_field.get()
			right=None if right=='' else int(right)
			fullscreen_mode=int(step.full_radio.get())
		except ValueError: return True
		if top!=cap.top_crop:
			if top!=cap.get_top_crop(): ischange=True
			cap.top_crop=top
		if bottom!=cap.bottom_crop:
			if bottom!=cap.get_bottom_crop(): ischange=True
			cap.bottom_crop=bottom
		if left!=cap.left_crop:
			if left!=cap.get_left_crop(): ischange=True
			cap.left_crop=left
		if right!=cap.right_crop:
			if right!=cap.get_right_crop(): ischange=True
			cap.right_crop=right
		if cap.fullscreen_mode!=None or fullscreen_mode:
			cap.fullscreen_mode=fullscreen_mode


		if ischange: step.capview.redrawcap()
		return True
	def savecapfields(self): self.usercrop('focusout')
	def savestep4(self):
		step=self.steps[4]
		self.savecapfields()
		self.saveconfig()
		step.command(isrefresh=True)
		self.step5_command()
	def step4_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return
		if not self.caps or not self.caps.count(): return self.step0_command()

		for w in self.frame_right.winfo_children(): w.destroy()

		self.steptitle('Format Input Pages')

		step=self.steps[4]
		capview=self.capview
		capview.step4=step
		capview.step6=None
		capview.cap=self.caps.getfirstcap()
		capview.ppm=None

		step.capview=capview
		step.croptop_field=tk.StringVar()
		step.cropbottom_field=tk.StringVar()
		step.cropleft_field=tk.StringVar()
		step.cropright_field=tk.StringVar()
		step.full_radio=tk.StringVar()
		self.setcapfields(step,capview)
		step.croptop_global=tk.StringVar(value=str(self.capdefaults.top_crop))
		step.cropbottom_global=tk.StringVar(value=str(self.capdefaults.bottom_crop))
		step.cropleft_global=tk.StringVar(value=str(self.capdefaults.left_crop))
		step.cropright_global=tk.StringVar(value=str(self.capdefaults.right_crop))
		rusercrop=self.master.register(self.usercrop)

		capview.create_widgets(self.frame_right)

		mainframe=tk.Frame(self.frame_right,bg='white')
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='0',variable=step.full_radio,text='Split page to fit reader screen',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='2',variable=step.full_radio,text='Scale full page to fit full reader screen',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='3',variable=step.full_radio,text='Scale page and keep progress bar',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='1',variable=step.full_radio,text='Omit this page',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')

		label=tk.Label(mainframe,text='Global crop values',bg='white',anchor='w')
		label.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		label=tk.Label(frame,text='Top ',bg='white')
		label.grid(row=0,column=0,sticky='news')
		entry=tk.Entry(frame,textvariable=step.croptop_global,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=0,column=1,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		label=tk.Label(frame,text='Bottom ',bg='white')
		label.grid(row=0,column=2,sticky='news',padx=(20,0))
		entry=tk.Entry(frame,textvariable=step.cropbottom_global,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=0,column=3,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		label=tk.Label(frame,text='Left ',bg='white')
		label.grid(row=1,column=0,sticky='news')
		entry=tk.Entry(frame,textvariable=step.cropleft_global,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=1,column=1,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		label=tk.Label(frame,text='Right ',bg='white')
		label.grid(row=1,column=2,sticky='news',padx=(20,0))
		entry=tk.Entry(frame,textvariable=step.cropright_global,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=1,column=3,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		frame.pack(fill='x',padx=10)

		label=tk.Label(mainframe,text='Crop this page override',bg='white',anchor='w')
		label.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		label=tk.Label(frame,text='Top ',bg='white')
		label.grid(row=0,column=0,sticky='news')
		entry=tk.Entry(frame,textvariable=step.croptop_field,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=0,column=1,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		label=tk.Label(frame,text='Bottom ',bg='white')
		label.grid(row=0,column=2,sticky='news',padx=(20,0))
		entry=tk.Entry(frame,textvariable=step.cropbottom_field,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=0,column=3,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		label=tk.Label(frame,text='Left ',bg='white')
		label.grid(row=1,column=0,sticky='news')
		entry=tk.Entry(frame,textvariable=step.cropleft_field,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=1,column=1,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		label=tk.Label(frame,text='Right ',bg='white')
		label.grid(row=1,column=2,sticky='news',padx=(20,0))
		entry=tk.Entry(frame,textvariable=step.cropright_field,width=3,bg='white',validate='all',validatecommand=(rusercrop,'%V'))
		entry.grid(row=1,column=3,sticky='news')
		entry.bind('<Return>',lambda _: self.usercrop('return'))
		frame.pack(fill='x',padx=10)

		button=tk.Button(mainframe,text='Save and continue',command=self.savestep4)
		button.pack(fill='x',pady=(40,10),padx=10)
		frame=tk.Frame(mainframe,bg='black',height=1)
		frame.pack(side='bottom',fill='x',pady=1)

		mainframe.pack(side='left',fill='y')
	def savetearinginfo(self):
		step=self.steps[5]
		try:
			self.pageoverlap=int(step.pageoverlap_field.get())
			self.linespacing=int(step.linespacing_field.get())
			self.excessivespace=int(step.excessivespace_field.get())
			self.excessivecut=int(step.excessivecut_field.get())
			self.chaptermargin=int(step.chaptermargin_field.get())
		except ValueError: return
		self.saveconfig()
		step.command(isrefresh=True)
		self.step6_command()
	def step5_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return

		step=self.steps[5]
		step.pageoverlap_field=tk.StringVar(value=str(self.pageoverlap))
		step.linespacing_field=tk.StringVar(value=str(self.linespacing))
		step.excessivespace_field=tk.StringVar(value=str(self.excessivespace or 0))
		step.excessivecut_field=tk.StringVar(value=str(self.excessivecut or 0))
		step.chaptermargin_field=tk.StringVar(value=str(self.chaptermargin))
		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Review Page Spacing')

		label=tk.Label(self.frame_right,text='How many pixels tall is each line, in input page pixels?',bg='white',wraplength=400,justify='left',anchor='w')
		label.pack(fill='x',pady=(20,0),padx=10)
		label=tk.Label(self.frame_right,text='When an input page is split across multiple reader pages, this many pixels will be duplicated on both reader pages. It\'s also used for finding line breaks.',bg='white',wraplength=400,justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.pageoverlap_field,width=3)
		entry.pack(side='left',pady=(10,0))
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='How many pixels tall should be placed between lines (linespacing), in output page pixels?',bg='white',wraplength=400,justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.linespacing_field,width=3)
		entry.pack(side='left',pady=(10,0))
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='How many consecutive blank rows in the input pages are too many?',bg='white',wraplength=400,justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.excessivespace_field,width=3)
		entry.pack(side='left',pady=(10,0))
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='How many blank rows should be removed if there are too many?',bg='white',wraplength=400,justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.excessivecut_field,width=3)
		entry.pack(side='left',pady=(10,0))
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='How many blank rows (after cropping) at the top of a page should trigger the chapter search? This will not affect the output file.',bg='white',wraplength=400,justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		entry=tk.Entry(frame,textvariable=step.chaptermargin_field,width=3)
		entry.pack(side='left',pady=(10,0))
		frame.pack(fill='x',padx=10)

		self.stepsave(self.savetearinginfo)
	def event_chapterselect(self,ev):
		self.master.after(1,self.chapterselect)
		self.master.update_idletasks()
	def chapterselect(self,a=None):
		step=self.steps[6]
		if a==None:
			sel=step.listbox.curselection()
			if not sel: return
			(idx,)=sel
			a=step.listbox.get(idx)
		idx=a.find(':')
		if idx<0:
			step.save_button.set('Add chapter')
			step.text_field.set('')
			step.capindex_field.set('')
			step.offset_field.set('')
			step.chapteruid=-1
			return
		idx=int(a[:idx])-1
		ch=self.chapters.list[idx]
		step.save_button.set('Update chapter')
		step.text_field.set(ch.text)
		step.capindex_field.set(ch.cap.index)
		step.offset_field.set(ch.offset)
		step.chapteruid=ch.uid
		self.capview.capindex_field.set(str(ch.cap.index))
		self.capview.usercap('return')
	def drawchapterlist(self):
		step=self.steps[6]
		step.listbox.delete(0,tk.END)
		step.listbox.insert(tk.END,'Add new chapter')
		for i,ch in enumerate(self.chapters.list):
			step.listbox.insert(tk.END,'%s: %s'%(i+1,ch.text[:20]))
	def addchapter(self):
		step=self.steps[6]
		uid=step.chapteruid
		capindex=step.capindex_field.get()
		if capindex=='': return
		try: capindex=int(capindex)
		except ValueError: return
		if capindex not in self.caps.byindex: return
		cap=self.caps.byindex[capindex]
		offset=step.offset_field.get()
		try: offset=0 if offset=='' else int(offset)
		except ValueError: return
		text=step.text_field.get()
		if not text: return
		self.chapters.add(uid,Chapter(text,cap,offset))
		step.text_field.set('')
		if uid<0 and text.startswith('Chapter ') and text[8:].isdigit():
			n=int(text[8:])+1
			step.text_field.set('Chapter '+str(n))
		step.capindex_field.set('')
		step.offset_field.set('')
		step.chapteruid=-1
		self.drawchapterlist()
	def deletechapter(self):
		step=self.steps[6]
		if step.chapteruid<0:
			step.text_field.set('')
			step.capindex_field.set('')
			step.offset_field.set('')
			return
		self.chapters.delete(step.chapteruid)
		self.drawchapterlist()
		self.chapterselect('')
	def savestep6(self):
		step=self.steps[6]
		self.saveconfig()
		step.command(isrefresh=True)
		self.step7_command()
	def step_chaptersearch(self):
		step=self.steps[6]
		if self.isstop:
			self.issearching=False
			self.isbusy=False
			self.isstop=False
			step.stop_button['state']='disabled'
			step.start_button['state']='normal'
			return
		(isdone,cap)=self.chaptersearch.step()
		if cap:
			self.capview.capindex_field.set(str(cap.index))
		if isdone==True:
			self.issearching=False
			self.isbusy=False
			self.isstop=False
			self.capview.usercap('return')
			step.stop_button['state']='disabled'
			step.start_button['state']='normal'
			return
		self.master.after(1,self.step_chaptersearch)
	def start_chaptersearch(self):
		if self.isbusy: return
		step=self.steps[6]
		step.stop_button['state']='normal'
		step.start_button['state']='disabled'
		self.isbusy=True
		self.issearching=True
		self.chaptersearch=ChapterSearch(self.chaptermargin,self.capview.cap)
		self.master.after(1,self.step_chaptersearch)
	def stop_chaptersearch(self):
		if not self.issearching: return
		step=self.steps[6]
		self.isstop=True
		step.stop_button['state']='disabled'
	def step6_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return
		if not self.caps or not self.caps.count(): return self.step0_command()

		for w in self.frame_right.winfo_children(): w.destroy()

		self.steptitle('Edit Chapters')

		step=self.steps[6]
		capview=self.capview
		capview.step4=None
		capview.step6=step
		capview.cap=self.caps.getfirstcap()
		capview.ppm=None

		step.capview=capview
		step.save_button=tk.StringVar()
		step.text_field=tk.StringVar()
		step.capindex_field=tk.StringVar()
		step.offset_field=tk.StringVar(value='0')
		step.chapteruid=-1

		capview.create_widgets(self.frame_right)

		mainframe=tk.Frame(self.frame_right,bg='white')

		label=tk.Label(mainframe,text='Select a chapter to edit it',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(20,0),padx=10)

		frame=tk.Frame(mainframe,bg='white')
		chapterframe=tk.Frame(frame,bg='white')
		chapterframe.pack(side='left',fill='x',pady=(0,10))
		rframe=tk.Frame(frame,bg='white')
		button=tk.Button(rframe,text='Delete chapter',command=self.deletechapter)
		button.pack(padx=5)
		rframe.pack(side='left',fill='y')
		frame.pack(fill='x',padx=10)

		scrollbar=tk.Scrollbar(chapterframe,orient='vertical')
		scrollbar.pack(side='right',fill='y')
		step.listbox=tk.Listbox(chapterframe,height=5,yscrollcommand=scrollbar.set)
		step.listbox.pack(side='left',fill='x')
		step.listbox.bind('<<ListboxSelect>>',self.event_chapterselect)
		scrollbar.config(command=step.listbox.yview)
		self.drawchapterlist()

		frame=tk.Frame(mainframe,bg='white')
		step.start_button=tk.Button(frame,text='Start chapter search',command=self.start_chaptersearch)
		step.start_button.pack(side='left',padx=5)
		step.stop_button=tk.Button(frame,text='Stop chapter search',command=self.stop_chaptersearch,state='disabled')
		step.stop_button.pack(side='left',padx=5)
		frame.pack(fill='x',padx=10)

		label=tk.Label(mainframe,text='Chapter text (80 letters)',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		entry=tk.Entry(mainframe,textvariable=step.text_field,width=32,bg='white')
		entry.pack(fill='x',padx=10)

		label=tk.Label(mainframe,text='Capture page index',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		entry=tk.Entry(mainframe,textvariable=step.capindex_field,width=4,bg='white')
		entry.pack(fill='x',padx=10)

		label=tk.Label(mainframe,text='Page offset',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		label=tk.Label(mainframe,text='You can click on the preview image to select offset.',bg='white',justify='left',anchor='w')
		label.pack(fill='x',padx=10)
		entry=tk.Entry(mainframe,textvariable=step.offset_field,width=4,bg='white')
		entry.pack(fill='x',padx=10)

		button=tk.Button(mainframe,textvariable=step.save_button,command=self.addchapter)
		button.pack(fill='x',pady=10,padx=10)

		button=tk.Button(mainframe,text='Save and continue',command=self.savestep6)
		button.pack(fill='x',pady=(40,10),padx=10)
		frame=tk.Frame(mainframe,bg='black',height=1)
		frame.pack(side='bottom',fill='x',pady=1)
		mainframe.pack(side='left',fill='y')

		step.capview=capview
		self.chapterselect('')
	def saveoutputformat(self):
		step=self.steps[7]
		self.bitdepth=int(step.bitdepth_radio.get())
		self.resolution=step.resolution_radio.get()
		self.compression=step.compression_radio.get()
		self.sinister=step.sinister_radio.get()
		self.saveconfig()
		step.command(isrefresh=True)
		self.step8_command()
	def step7_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return
		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Output Format')

		step=self.steps[7]
		step.bitdepth_radio=tk.StringVar(value=str(self.bitdepth))
		step.resolution_radio=tk.StringVar(value=self.resolution)
		step.compression_radio=tk.StringVar(value=self.compression or 'none')
		step.sinister_radio=tk.StringVar(value=self.sinister or 'false')

		label=tk.Label(self.frame_right,text='Bit depth for XTC file:',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(20,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='1',variable=step.bitdepth_radio,text='1-bit black and white',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='2',variable=step.bitdepth_radio,text='2-bit greyscale',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Display of reader:',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='528x792',variable=step.resolution_radio,text='X3: 528x792',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='480x800',variable=step.resolution_radio,text='X4: 480x800',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Display orientation:',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='false',variable=step.sinister_radio,text='Front buttons on right',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='true',variable=step.sinister_radio,text='Front buttons on left',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		label=tk.Label(self.frame_right,text='Page compression:',bg='white',justify='left',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='none',variable=step.compression_radio,text='None (for stock firmware)',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='rle',variable=step.compression_radio,text='RLE (not for stock firmware)',fg='red',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)
		frame=tk.Frame(self.frame_right,bg='white')
		radio=tk.Radiobutton(frame,value='zlib',variable=step.compression_radio,text='zlib (not for stock firmware)',fg='red',bg='white',highlightthickness=0)
		radio.pack(side='left')
		frame.pack(fill='x',padx=10)

		self.stepsave(self.saveoutputformat)
	def finishbuild(self):
		self.isbuilding=False
		self.isbusy=False
		self.isstop=False
		self.start_button['state']='normal'
		self.stop_button['state']='disabled'
		print('finishbuild')
	def stepbuild(self):
		step=self.steps[8]
		if self.isstop:
			self.isbuilding=False
			self.isbusy=False
			self.isstop=False
			self.start_button['state']='normal'
			self.stop_button['state']='disabled'
			return
		cappgm=None
		pagepgm=None
		if self.iswalkcaps:
			ret=self.builder.step_walkcaps()
			if ret==True:
				self.iswalkcaps=False
				self.iswalkpages=True
			else:
				cappgm=ret
		if self.iswalkpages:
			(isdone,cappgm,pagepgm)=self.builder.step_walkpages()
			if isdone==True:
				self.finishbuild()
				return
		if cappgm:
			step.capdata=cappgm.tobytes()
			if False:
				print('writing /tmp/cap.pgm')
				f=open('/tmp/cap.pgm','wb')
				f.write(step.capdata)
			scale=self.getscale(cappgm.width,cappgm.height)
			step.capimage=tk.PhotoImage(data=step.capdata).subsample(scale,scale)
			step.cap_label['image']=step.capimage
			self.master.update_idletasks()
		if pagepgm:
			step.pagedata=pagepgm.tobytes()
			if False:
				print('writing /tmp/page.pgm')
				f=open('/tmp/page.pgm','wb')
				f.write(step.pagedata)
				raise ValueError
			scale=self.getscale(pagepgm.width,pagepgm.height)
			step.pageimage=tk.PhotoImage(data=step.pagedata).subsample(scale,scale)
			step.page_label['image']=step.pageimage
			self.master.update_idletasks()
		self.master.after(1,self.stepbuild)
	def startbuild(self):
		step=self.steps[8]
		if self.isbusy: return
		self.isbuilding=True
		self.isbusy=True
		self.iswalkcaps=True
		self.iswalkpages=False
		self.start_button['state']='disabled'
		self.stop_button['state']='normal'
		CLIBuild.makebuilder(self)
		self.master.after(0,self.stepbuild)
	def stopbuild(self):
		self.isstop=True
	def step8_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return
		if not self.caps or not self.caps.count(): return self.step0_command()

		for w in self.frame_right.winfo_children(): w.destroy()
		step=self.steps[8]
		self.steptitle('Build')

		frame=tk.Frame(self.frame_right,bg='white')
		button=tk.Button(frame,text='Start',command=self.startbuild)
		button.pack()
		self.start_button=button
		frame.pack(pady=(20,0),padx=10,fill='x')
		frame=tk.Frame(self.frame_right,bg='white')
		button=tk.Button(frame,text='Stop',state='disabled',command=self.stopbuild)
		button.pack()
		self.stop_button=button
		frame.pack(pady=10,padx=10,fill='x')

		frame=tk.Frame(self.frame_right,bg='white')
		subframe=tk.Frame(frame,bg='white')
		label=tk.Label(subframe,text='input preview',bg='white')
		label.pack()
		step.cap_label=label
		subframe.pack(side='left',fill='y')

		subframe=tk.Frame(frame,bg='white')
		label=tk.Label(frame,text='output preview',bg='white')
		label.pack()
		step.page_label=label
		subframe.pack(side='left',fill='y')
		frame.pack(fill='x')
	def savestep9(self):
		step=self.steps[9]
		try:
			top=int(step.croptop_global.get())
			bottom=int(step.cropbottom_global.get())
			left=int(step.cropleft_global.get())
			right=int(step.cropright_global.get())
			fullscreen_mode=int(step.fullscreen_mode_global.get())
		except ValueError: return
		self.capdefaults.top_crop=top
		self.capdefaults.bottom_crop=bottom
		self.capdefaults.left_crop=left
		self.capdefaults.right_crop=right
		self.capdefaults.fullscreen_mode=fullscreen_mode
		
		self.saveconfig()
		step.command(isrefresh=True)
		self.step4_command()
	def step9_command(self,isrefresh=False):
		if isrefresh: return
		if self.isbusy: return

		step=self.steps[9]
		step.croptop_global=tk.StringVar(value=str(self.capdefaults.top_crop))
		step.cropbottom_global=tk.StringVar(value=str(self.capdefaults.bottom_crop))
		step.cropleft_global=tk.StringVar(value=str(self.capdefaults.left_crop))
		step.cropright_global=tk.StringVar(value=str(self.capdefaults.right_crop))
		step.fullscreen_mode_global=tk.StringVar(value=str(self.capdefaults.fullscreen_mode))
		for w in self.frame_right.winfo_children(): w.destroy()
		self.steptitle('Input page defaults')

		mainframe=self.frame_right
		label=tk.Label(mainframe,text='These choices set the default behavior for all pages. Individual pages can be configured to override these defaults in Step 6.',bg='white',wraplength=200)
		label.pack(fill='x',pady=(20,0),padx=10)
		label=tk.Label(mainframe,text='Global scaling option',bg='white',anchor='w')
		label.pack(fill='x',pady=(10,0),padx=10)
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='0',variable=step.fullscreen_mode_global,text='Split page to fit reader screen',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='2',variable=step.fullscreen_mode_global,text='Scale full page to fit full reader screen',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')
		frame=tk.Frame(mainframe,bg='white')
		radio=tk.Radiobutton(frame,value='3',variable=step.fullscreen_mode_global,text='Scale page and keep progress bar',bg='white',highlightthickness=0)
		radio.pack(side='left',fill='x',padx=10)
		frame.pack(fill='x')

		label=tk.Label(mainframe,text='Global crop values',bg='white',anchor='w')
		label.pack(fill='x',pady=(20,0),padx=10)
		label=tk.Label(mainframe,text='After these crops, pages will be auto-cropped on top and bottom to remove whitespace. These top and bottom crops allow you to remove unwanted header or footer decorations that auto-cropping won\'t remove.',bg='white',anchor='w',wraplength=400,justify='left')
		label.pack(fill='x',pady=(0,0),padx=10)
		label=tk.Label(mainframe,text='Units are in input pixels and these can also be visually modified in the next step.',bg='white',anchor='w',wraplength=400,justify='left')
		label.pack(fill='x',pady=(0,0),padx=10)
		frame=tk.Frame(mainframe,bg='white')
		label=tk.Label(frame,text='Top ',bg='white')
		label.grid(row=0,column=0,sticky='news')
		entry=tk.Entry(frame,textvariable=step.croptop_global,width=3,bg='white')
		entry.grid(row=0,column=1,sticky='news')
		label=tk.Label(frame,text='Bottom ',bg='white')
		label.grid(row=0,column=2,sticky='news',padx=(20,0))
		entry=tk.Entry(frame,textvariable=step.cropbottom_global,width=3,bg='white')
		entry.grid(row=0,column=3,sticky='news')
		label=tk.Label(frame,text='Left ',bg='white')
		label.grid(row=1,column=0,sticky='news')
		entry=tk.Entry(frame,textvariable=step.cropleft_global,width=3,bg='white')
		entry.grid(row=1,column=1,sticky='news')
		label=tk.Label(frame,text='Right ',bg='white')
		label.grid(row=1,column=2,sticky='news',padx=(20,0))
		entry=tk.Entry(frame,textvariable=step.cropright_global,width=3,bg='white')
		entry.grid(row=1,column=3,sticky='news')
		frame.pack(fill='x',padx=20)

		self.stepsave(self.savestep9)

outputdir=None
inputdir=None
configfile=None
isclibuild=False
imagewidth=400
imageheight=600
caplimit=None
args=sys.argv[1:]
for arg in args:
	if arg.startswith('--outputdir='):
		outputdir=arg[12:]
		if not outputdir.endswith('/') and not outputdir.endswith('\\'): raise ValueError
	elif arg.startswith('--inputdir='):
		inputdir=arg[11:]
		if not inputdir.endswith('/') and not inputdir.endswith('\\'): raise ValueError
	elif arg.startswith('--config='):
		configfile=arg[9:]
	elif arg.startswith('--width='):
		imagewidth=int(arg[8:])
	elif arg.startswith('--height='):
		imageheight=int(arg[9:])
	elif arg.startswith('--caplimit='):
		caplimit=int(arg[11:])
		if not isclibuild: raise ValueError
		if not inputdir: raise ValueError
	elif arg=='--clibuild': isclibuild=True
	else: raise ValueError('Unknown argument: %s'%arg)

if isclibuild:
	clibuild=CLIBuild(configfile,inputdir,outputdir)
	clibuild.start(caplimit=caplimit)
	clibuild.walkcaps()
	clibuild.walkpages()
else:
	root=tk.Tk()
	root.title('XTC Builder')
	app=Application(master=root,inputdir=inputdir,outputdir=outputdir,configfile=configfile,imagewidth=imagewidth,imageheight=imageheight)
	app.mainloop()
