#!/usr/bin/python3

#  * github.com/sanjayrao77
#  * xtcviewer.py - program to view XTC/XTCH ebooks
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


import struct
import sys
import time
import tkinter as tk
from tkinter import filedialog
import zlib

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

def offreadn(file,count,offset):
	if offset!=file.seek(offset): raise ValueError
	return file.read(count)

class HeaderXtc():
	def __init__(self,ba):
		(self.mark,self.version,self.pagecount,self.readdirection,self.hasmetadata,self.hasthumbnails,
				self.haschapters,self.currentpage,self.metadataoffset,self.indexoffset,self.dataoffset,
				self.thumboffset,self.chapteroffset)=struct.unpack('<IHH4BI5Q',ba[:56])
		if self.mark==0x00435458: self.format='xtc'
		elif self.mark==0x48435458: self.format='xtch'
		else: raise ValueError

class MetadataXtc():
	def __init__(self,ba):
		self.title=ba[0:128].rstrip(b'\x00').decode()
		self.author=ba[128:192].rstrip(b'\x00').decode()
		self.publisher=ba[192:224].rstrip(b'\x00').decode()
		self.language=ba[224:240].rstrip(b'\x00').decode()
		(self.createtime,self.coverpage,self.chaptercount)=struct.unpack('<IHH',ba[240:248])

class EntryIndexXtc():
	def __init__(self,ba):
		(self.offset,self.size,self.width,self.height)=struct.unpack('<QIHH',ba[:16])

class IndexXtc():
	def __init__(self,ba,count):
		self.count=count
		self.entries=[]
		for off in range(0,16*count,16):
			self.entries.append(EntryIndexXtc(ba[off:]))
	def fetch(self,idx): return self.entries[idx]

class ChapterXtc():
	def __init__(self,ba):
		self.chaptername=ba[0:80].rstrip(b'\x00').decode()
		(self.startpage,self.endpage)=struct.unpack('<HH',ba[80:84])

class ChaptersXtc():
	def __init__(self,ba,count):
		self.count=count
		self.entries=[]
		for off in range(0,96*count,96):
			self.entries.append(ChapterXtc(ba[off:]))

class ImageXtc():
	def frombytes(ba):
		compression=ba[9]
		if ba[:4]==b'XTG\x00':
			if not compression: return Xtg(ba)
			elif compression==122: return ZlibXtg(ba) # z
			elif compression==114: return RleXtg(ba) # r
			else: raise ValueError
		if ba[:4]==b'XTH\x00':
			if not compression: return Xth(ba)
			elif compression==122: return ZlibXth(ba) # z
			elif compression==114: return RleXth(ba) # r
			else: raise ValueError
	def __init__(self,ba):
		self.magic=ba[0:4]
		(self.width,self.height,self.colormode,self.compression,self.datasize)=struct.unpack('<HHBBI',ba[4:14])
		self.md5part=ba[14:22]
	def rotate_top5(self):
		header=('P5\n%s %s\n255\n'%(self.height,self.width)).encode()
		offset=len(header)
		ba=bytearray(offset+self.width*self.height)
		ba[:offset]=header
		self.rotate_topixels(ba,offset)
		return ba

class Xtg(ImageXtc):
	def __init__(self,ba):
		super().__init__(ba)
		self.rows=[]
		offset=22
		wb=(self.width+7)>>3
		for _ in range(self.height):
			self.rows.append(ba[offset:offset+wb])
			offset+=wb
	def rotate_topixels(self,ba,baoffset):
		w=self.width
		if w&7: raise ValueError
		x=(w>>3)-1
		bit=1
		while True:
			for row in self.rows:
				ba[baoffset]=255 if row[x]&bit else 0
				baoffset+=1
			bit<<=1
			if bit==256:
				if not x: break
				x-=1
				bit=1

class ZlibXtg(Xtg):
	def __init__(self,ba):
		ImageXtc.__init__(self,ba)
		self.rows=[]
		cursor=22
		for _ in range(self.height):
			n=ba[cursor] ; cursor+=1
			self.rows.append(zlib.decompress(ba[cursor:cursor+n]))
			cursor+=n

class RleXtg(Xtg):
	def __init__(self,ba):
		raw=bytearray(ba[:22])
		raw.extend(RLE.decode(ba[22:]))
		super().__init__(raw)

class Xth(ImageXtc):
	def __init__(self,ba):
		super().__init__(ba)
		self.plane1=[]
		self.plane2=[]
		hb=(self.height+7)>>3
		offset1=22
		offset2=offset1+self.width*hb
		for x in range(self.width):
			nextoffset1=offset1+hb
			nextoffset2=offset2+hb
			self.plane1.append(ba[offset1:nextoffset1])
			self.plane2.append(ba[offset2:nextoffset2])
			offset1=nextoffset1
			offset2=nextoffset2
	def topixels(self,ba,baoffset):
		width=self.width
		height=self.height
		if height&7: raise ValueError
		width2=width*2
		width3=width*3
		width4=width*4
		width5=width*5
		width6=width*6
		width7=width*7
		width8=width*8
		cilimit=height>>3
		x=0
		rx=width-1
		colors=(255,83,166,0)
		while True:
			col1=self.plane1[rx]
			col2=self.plane2[rx]
			rowoff=baoffset+x
			ci=0
			while True:
				b1=col1[ci]
				b2=col2[ci]
				ba[rowoff]=colors[((b1&128)>>6)|((b2&128)>>7)]
				ba[rowoff+width]=colors[((b1&64)>>5)|((b2&64)>>6)]
				ba[rowoff+width2]=colors[((b1&32)>>4)|((b2&32)>>5)]
				ba[rowoff+width3]=colors[((b1&16)>>3)|((b2&16)>>4)]
				ba[rowoff+width4]=colors[((b1&8)>>2)|((b2&8)>>3)]
				ba[rowoff+width5]=colors[((b1&4)>>1)|((b2&4)>>2)]
				ba[rowoff+width6]=colors[((b1&2))|((b2&2)>>1)]
				ba[rowoff+width7]=colors[((b1&1)<<1)|(b2&1)]
				ci+=1
				if ci==cilimit: break
				rowoff+=width8
			x+=1
			if x==width: break
			rx-=1
	def rotate_topixels(self,ba,baoffset):
		width=self.width
		height=self.height
		if height&7: raise ValueError
		colors=(255,83,166,0)
		colnum=0
		rownumlimit=height>>3
		width8=width*8
		offset=baoffset
		while True:
			col1=self.plane1[colnum]
			col2=self.plane2[colnum]
			rownum=0
			while True:
				b1=col1[rownum]
				b2=col2[rownum]
				eight=(colors[((b1&128)>>6)|((b2&128)>>7)], colors[((b1&64)>>5)|((b2&64)>>6)], colors[((b1&32)>>4)|((b2&32)>>5)], colors[((b1&16)>>3)|((b2&16)>>4)], colors[((b1&8)>>2)|((b2&8)>>3)], colors[((b1&4)>>1)|((b2&4)>>2)], colors[((b1&2))|((b2&2)>>1)], colors[((b1&1)<<1)|(b2&1)])
				nextoffset=offset+8
				ba[offset:nextoffset]=eight
				offset=nextoffset
				rownum+=1
				if rownum==rownumlimit: break
			colnum+=1
			if colnum==width: break
	def top5(self):
		header=('P5\n%s %s\n255\n'%(self.width,self.height)).encode()
		offset=len(header)
		ba=bytearray(offset+self.width*self.height)
		ba[:offset]=header
		self.topixels(ba,offset)
		return ba

class ZlibXth(Xth):
	def __init__(self,ba):
		ImageXtc.__init__(self,ba)
		self.plane1=[]
		self.plane2=[]
		cursor=22
		for _ in range(self.width):
			n=ba[cursor] ; cursor+=1
			self.plane1.append(zlib.decompress(ba[cursor:cursor+n]))
			cursor+=n
		for _ in range(self.width):
			n=ba[cursor] ; cursor+=1
			self.plane2.append(zlib.decompress(ba[cursor:cursor+n]))
			cursor+=n

class RleXth(Xth):
	def __init__(self,ba):
		raw=bytearray(ba[:22])
		raw.extend(RLE.decode(ba[22:]))
		super().__init__(raw)

class Xtc():
	def __init__(self):
		self.filename=None
		self.file=None
		self.header=None
		self.metadata=None
		self.pageindex=None
		self.thumbindex=None
		self.chapters=None
		self.lastpage=None
	def loadheader(self):
		ba=offreadn(self.file,56,0)
		self.header=HeaderXtc(ba)
		self.lastpage=self.header.pagecount-1
	def loadmetadata(self):
		if not self.header.hasmetadata: return
		ba=offreadn(self.file,256,self.header.metadataoffset)
		self.metadata=MetadataXtc(ba)
	def loadpageindex(self):
		ba=offreadn(self.file,self.header.pagecount*16,self.header.indexoffset)
		self.pageindex=IndexXtc(ba,self.header.pagecount)
	def loadthumbindex(self):
		if not self.header.hasthumbnails: return
		ba=offreadn(self.file,self.header.pagecount*16,self.header.thumboffset)
		self.thumbindex=IndexXtc(ba,self.header.pagecount)
	def loadchapters(self):
		if not self.header.haschapters: return
		if not self.metadata: raise ValueError
		ba=offreadn(self.file,self.metadata.chaptercount*96,self.header.chapteroffset)
		self.chapters=ChaptersXtc(ba,self.metadata.chaptercount)
	def loadfile(self,name):
		f=open(name,'rb')
		self.file=f
		self.loadheader()
		self.loadmetadata()
		self.loadpageindex()
		self.loadthumbindex()
		self.loadchapters()
	def fetchpagebytes(self,idx):
		entry=self.pageindex.fetch(idx)
		print('reading from offset',entry.offset,'size',entry.size)
		ba=offreadn(self.file,entry.size,entry.offset)
		return ba
	def fetchpage(self,idx):
		ba=self.fetchpagebytes(idx)
		image=ImageXtc.frombytes(ba)
		return image

class Application(tk.Frame):
	def __init__(self,master=None,infile=None):
		super().__init__(master)
		self.master=master
		self.pagenumber=None
		self.infile=None
		self.x=None
		self.pack()
		if infile: self.loadfile(infile)
		else: self.pickfile()

	def loadfile(self,infile):
		self.pagenumber=0
		self.infile=infile
		self.x=Xtc()
		self.x.loadfile(infile)
		for w in self.winfo_children(): w.destroy()
		self.create_widgets()
		self.redrawpage()

	def redrawpage(self):
		print('fetching page',self.pagenumber)
		image=self.x.fetchpage(self.pagenumber)
		self.pgmdata=bytes(image.rotate_top5())
		self.pageimage=tk.PhotoImage(data=self.pgmdata)
		self.pageview['image']=self.pageimage
		self.pagebar.set(0.95*self.pagenumber/self.x.lastpage,0.05+0.95*self.pagenumber/self.x.lastpage)

	def event_chapterselect(self,ev):
		(idx,)=self.listbox.curselection()
		a=self.listbox.get(idx)
		self.chapterselect(a)
	def chapterselect(self,a):
		idx=a.find(':')
		if idx<0: return
		idx=int(a[:idx])-1
		ch=self.x.chapters.entries[idx]
		print('Selected chapter',ch.chaptername,'start page',ch.startpage)
		self.pagenumber=ch.startpage-1
		if self.pagenumber>self.x.lastpage: self.pagenumber=self.x.lastpage
		self.redrawpage()

	def pickfile(self):
		path=filedialog.askopenfilename(title='XTC Viewer: Select input file',
				filetypes=(('both','*.xtc*'),('xtc files','*.xtc'),('xtch files','*.xtch')))
		if not path:
			if not self.infile: self.quit()
		else: self.loadfile(path)

	def create_widgets(self):
		self.banner=tk.Frame(self)

		button=tk.Button(self.banner,text='Quit',fg='red',command=self.quit)
		button.pack(side='left')

		button=tk.Button(self.banner,text='Open file',command=self.pickfile)
		button.pack(side='left')

		self.filename = tk.Label(self.banner)
		self.filename['text']=self.infile
		self.filename.pack(side='left')

		self.banner.pack(fill='x')

		self.left=tk.Frame(self)

		label=tk.Label(self.left,text='Title',anchor='w')
		label.pack(pady=(10,0),fill='x')
		label=tk.Label(self.left,text=self.x.metadata.title,wraplength=120)
		label.pack(fill='x')
		label=tk.Label(self.left,text='Author',anchor='w')
		label.pack(pady=(10,0),fill='x')
		label=tk.Label(self.left,text=self.x.metadata.author,wraplength=120)
		label.pack(fill='x')
		label=tk.Label(self.left,text='Publisher',anchor='w')
		label.pack(pady=(10,0),fill='x')
		label=tk.Label(self.left,text=self.x.metadata.publisher,wraplength=120)
		label.pack(fill='x')
		label=tk.Label(self.left,text='Language',anchor='w')
		label.pack(pady=(10,0),fill='x')
		label=tk.Label(self.left,text=self.x.metadata.language,wraplength=120)
		label.pack(fill='x')

		label=tk.Label(self.left,text='Chapter list',anchor='w')
		label.pack(pady=(20,0),fill='x')
		frame=tk.Frame(self.left)
		scrollbar=tk.Scrollbar(frame,orient='vertical')
		scrollbar.pack(side='right',fill='y')
		self.listbox=tk.Listbox(frame,height=10,yscrollcommand=scrollbar.set)
		self.listbox.pack(side='left',fill='x')
		self.listbox.bind('<<ListboxSelect>>',self.event_chapterselect)
		scrollbar.config(command=self.listbox.yview)
		frame.pack(fill='x',padx=(10,0))
		if self.x.chapters:
			for i,ch in enumerate(self.x.chapters.entries):
				self.listbox.insert(tk.END,'%s: %s'%(i+1,ch.chaptername[:40]))

		self.left.pack(side='left',fill='y')

		self.right=tk.Frame(self)

		self.pageview=tk.Label(self.right)
		self.pageview['text']='page: '+str(self.pagenumber)
		self.pageview.pack()

		self.pagebar=tk.Scrollbar(self.right)
		self.pagebar['orient']=tk.HORIZONTAL
		self.pagebar['command']=self.scroll_callback
		self.pagebar.pack(fill='x')

		self.down=tk.Button(self.right)
		self.down['text']='Back'
		self.down['command']=self.back_callback
		self.down.pack(side='left')

		self.up=tk.Button(self.right)
		self.up['text']='Forward'
		self.up['command']=self.forward_callback
		self.up.pack(side='left')

		self.right.pack(side='left',fill='y')

	def quit(self):
		print('quit called, exiting')
		self.master.destroy()

	def forward_callback(self):
		self.pagenumber+=1
		if self.pagenumber>self.x.lastpage: self.pagenumber=self.x.lastpage
		print('page: '+str(self.pagenumber))
		self.redrawpage()

	def back_callback(self):
		self.pagenumber-=1
		if self.pagenumber<0: self.pagenumber=0
		print('page: '+str(self.pagenumber))
		self.redrawpage()

	def scroll_callback(self,a,b,c=None):
#		print('scroll command (a:%s b:%s c:%s)'%(a,b,c))
		old=self.pagenumber
		if a=='scroll':
			if c=='units':
				self.pagenumber+=int(b)
			elif c=='pages':
				self.pagenumber+=int(b)*10
			else: print('unknown scroll (a:%s b:%s c:%s)'%(a,b,c))
		elif a=='moveto':
			self.pagenumber=int(float(b)*self.x.lastpage)
		else: print('unknown scroll (a:%s b:%s c:%s)'%(a,b,c))
		if self.pagenumber<0: self.pagenumber=0
		elif self.pagenumber>self.x.lastpage: self.pagenumber=self.x.lastpage
		if old==self.pagenumber: return
		self.redrawpage()
		self.master.update_idletasks()

infile=None

args=sys.argv[1:]
for arg in args:
	if arg.startswith('-'):
		raise ValueError
	else:
		if infile: raise ValueError
		infile=arg

root=tk.Tk()
root.title('XTC Viewer')
app=Application(master=root,infile=infile)
app.mainloop()
