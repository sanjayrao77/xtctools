#!/usr/bin/python3

#  * github.com/sanjayrao77
#  * adbcapture.py - program to copy screenshots from Android devices
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

import os
import struct
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog
import zlib

class PGM():
	def __init__(self,width,height,rows): (self.width,self.height,self.rows)=(width,height,rows)
	def tobytes(self):
		ba=bytearray(('P5\n%s %s\n255\n'%(self.width,self.height)).encode())
		for row in self.rows: ba.extend(row)
		return bytes(ba)

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
		while tail:
			(key,value,tail)=PNG.parsechunk(tail)
			if key==b'IDAT':
				while value:
					if value[0]!=0: raise ValueError('Unsupported PNG compression')
					rows.append(value[1:1+self.width])
					value=value[1+self.width:]
		return PGM(self.width,self.height,rows)

class PngCompress():
	def create(fout,width,height,rows,level=6):
		fout.write(b'\x89PNG\r\n\x1a\n')
		colortype=0
		PngCompress.writechunk(fout,b'IHDR',struct.pack('>2I5B',width,height,8,colortype,0,0,0))
		PngCompress.write_simple(fout,rows,level)
		PngCompress.writechunk(fout,b'IEND',b'')
	def writechunk(fout,key,value):
		fout.write(struct.pack('>I',len(value)))
		fout.write(key)
		fout.write(value)
		fout.write(struct.pack('>I',zlib.crc32(value,zlib.crc32(key))))
	def write_simple(fout,rows,complevel): # complevel, 3:fast, 6:medium, 9: smallest
		ba=bytearray()
		for row in rows:
			ba.append(0)
			ba.extend(row)
		PngCompress.writechunk(fout,b'IDAT',zlib.compress(ba,complevel))

class ADBWrapper():
	def __init__(self):
		self.ischecked=False
		self.devices=[]
		self.width=None
		self.height=None
	def fetchdevices(self):
		self.devices=[]
		h=subprocess.run(['adb','devices'],stdout=subprocess.PIPE)
		if h.returncode: return 'ADB returned %s'%h.returncode
		data=h.stdout.decode()
		lines=data.split('\n')
		if not lines: return 'No device listed'
		if lines[0].startswith('List of devices attached'): lines=lines[1:]
		for line in lines:
			if not line: continue;
			a=line.split('\t')
			if a[1]!='device': continue
			self.devices.append(a[0])
	def checkdevice(self):
		self.ischecked=False
		err=self.fetchdevices()
		if err: return err
		if len(self.devices)!=1:
			if not len(self.devices): return 'No device listed'
			return 'Too many devices'
		self.ischecked=True
	def advance(self):
		if self.width==None: raise ValueError
		x1='%s'%int(self.width*0.95)
		x2='%s'%int(self.width*0.7)
		y='%s'%int(self.height*0.5)
		h=subprocess.run(['adb','shell','input','swipe',x1,y,x2,y],stdout=subprocess.PIPE)
		if h.returncode: raise ValueError
	def fetchcap(self):
		if self.checkdevice(): return
		h=subprocess.run(['adb','exec-out','screencap'],stdout=subprocess.PIPE)
		if h.returncode: raise ValueError
		data=h.stdout
		if len(data)<12: raise ValueError
		(width,height)=struct.unpack('<II',data[:8])
		(self.width,self.height)=(width,height)
		bitformat=data[8:12]
		if bitformat!=b'\x01\x00\x00\x00': raise ValueError
		if len(data)<width*height*4+12: raise ValueError

		rows=[]
		cursor=12
		for _ in range(height):
			row=bytearray(width)
			rows.append(row)
			for x in range(width):
				row[x]=int((data[cursor]+data[cursor+1]+data[cursor+2])/3) # rgba
				cursor+=4
		pgm=PGM(width,height,rows)

		if False:
			data=pgm.tobytes()
			f=open('/tmp/screencap.pgm','wb')
			f.write(data)
		return pgm

class Application(tk.Frame):
	def get_capend(path):
		if not path: return (1,None)
		entries=os.scandir(path)
		highest=0
		highestpath=None
		for ent in entries:
			if not ent.name.startswith('cap'): continue
			if not ent.name.endswith('.png'): continue
			if ent.name=='cap-cover.png': continue
			text=ent.name[3:-4]
			num=int(text)
			if num>highest:
				highest=num
				highestpath=ent.path
		return (highest+1,highestpath)
	def __init__(self,master,pgm,outputdir,ispreviews):
		super().__init__(master)
		self.master=master
		self.default_pgm=pgm
		self.outputdir=outputdir
		self.lastrawbytes=None
		self.isstop=False
		self.iscover=False
		self.iswalking=False
		self.ispreviews=ispreviews
		(self.capindex,self.lastcappath)=Application.get_capend(self.outputdir)
		self.capstringvar=tk.StringVar()
		self.aw=ADBWrapper()
		self.status_checkshot=tk.StringVar()
		self.status_adb=tk.StringVar()
		self.status_dir=tk.StringVar(value=self.outputdir or 'None')
		self.bannertext='ADB Screenshot Capture, status: '
		self.status_banner=tk.StringVar(value='Ready')
		self.pack()
		self.create_widgets()
		if self.lastcappath: self.setimage(PNG(self.lastcappath).topgm())
		else: self.setimage(self.default_pgm)
		self.setcapstring()

	def setcapstring(self): self.capstringvar.set('Start at cap index %s'%self.capindex)
	def setimage(self,pgm):
		xscale=int((399+pgm.width)/400)
		yscale=int((599+pgm.height)/600)
		scale=max(xscale,yscale)
		self.pagedata=pgm.tobytes()
		self.pageimage=tk.PhotoImage(data=self.pagedata).subsample(scale,scale)
		self.page_label['image']=self.pageimage
	def create_widgets(self):
		topframe=tk.Frame(self)
		label=tk.Label(topframe,text=self.bannertext)
		label.pack(side='left')
		self.label_banner=tk.Label(topframe,textvariable=self.status_banner,anchor='w',fg='black')
		self.label_banner.pack(side='left')
		topframe.pack(side='top')

		one=tk.Frame(self)
		left=tk.Frame(one)
		right=tk.Frame(one)

		self.page_label=tk.Label(left,text='.')
		self.page_label.pack(side='top')

		step=tk.Frame(right)
		label=tk.Label(step,text='Step 1: Verify ADB',anchor='w')
		label.pack(side='top',fill='x')
		label=tk.Label(step,textvariable=self.status_adb,anchor='e')
		label.pack(side='top',fill='x')
		button=tk.Button(step,text='Do it',command=self.checkadb_callback)
		button.pack(side='right')
		step.pack(side='top',fill='x')

		step=tk.Frame(right)
		label=tk.Label(step,text='Step 2: Try screenshot',anchor='w')
		label.pack(side='top',fill='x')
		button=tk.Button(step,text='Do it',command=self.checkshot_callback)
		button.pack(side='right')
		step.pack(side='top',fill='x')

		step=tk.Frame(right)
		label=tk.Label(step,text='Step 3: Test page flip',anchor='w')
		label.pack(side='top',fill='x')
		button=tk.Button(step,text='Flip',command=self.checkflip_callback)
		button.pack(side='right')
		step.pack(side='top',fill='x')

		step=tk.Frame(right)
		label=tk.Label(step,text='Step 4: Select output directory',anchor='w')
		label.pack(side='top',fill='x')
		label=tk.Label(step,textvariable=self.status_dir,anchor='e')
		label.pack(side='top',fill='x')
		button=tk.Button(step,text='Choose',command=self.pickdir_callback)
		button.pack(side='right')
		step.pack(side='top',fill='x')

		step=tk.Frame(right)
		label=tk.Label(step,text='Step 5: Capture cover page',anchor='w')
		label.pack(side='top',fill='x')
		button=tk.Button(step,text='Grab',command=self.coverpage_callback)
		button.pack(side='right')
		step.pack(side='top',fill='x')

		step=tk.Frame(right)
		label=tk.Label(step,text='Step 6: Walk through book',anchor='w')
		label.pack(side='top',fill='x')
		label=tk.Label(step,textvariable=self.capstringvar,anchor='e')
		label.pack(side='top',fill='x')
		frame=tk.Frame(step)
		self.button_start=tk.Button(frame,text='Start',command=self.walkbook_callback)
		self.button_start.pack(side='top')
		self.button_stop=tk.Button(frame,text='Stop',command=self.stopwalk_callback,state='disabled')
		self.button_stop.pack(side='top')
		frame.pack(side='right',fill='x')
		step.pack(side='top',fill='x')

		left.pack(side='left',fill='y')
		right.pack(side='left',fill='y')
		one.pack(side='top',fill='x')

		button=tk.Button(self,text="Quit",fg="red",command=self.quit)
		button.pack(side="bottom",fill='x')

	def quit(self):
		print("quit called, exiting")
		self.master.destroy()
	def setstatus(self,text):
		if text:
			self.status_banner.set(text+'...')
			self.label_banner['fg']='red'
		else:
			self.status_banner.set('Ready')
			self.label_banner['fg']='black'
		self.master.update_idletasks()
	def checkadb_callback(self):
		self.setstatus('Checking')
		err=self.aw.checkdevice()
		if not err:
			self.setstatus(None)
			self.status_adb.set('Ok')
		else:
			self.status_adb.set(err)
			self.setstatus('Failed')
	def checkshot_callback(self):
		self.setstatus('Fetching image')
		pgm=self.aw.fetchcap()
		self.setimage(pgm)
		self.setstatus('Done')
		self.setstatus(None)
	def pickdir_callback(self):
		path=filedialog.askdirectory(title='Select output directory')
		if not path: return
		if not path.endswith('/') and not path.endswith('\\'): path=path+'/'
		self.outputdir=path
		self.status_dir.set(path)
		(self.capindex,self.lastcappath)=Application.get_capend(self.outputdir)
		if self.lastcappath: self.setimage(PNG(self.lastcappath).topgm())
		else: self.setimage(self.default_pgm)
		self.setcapstring()
	def checkflip_callback(self):
		if self.aw.width==None: self.checkshot_callback()
		self.setstatus('Sending swipe')
		self.aw.advance()
		self.setstatus('Sleeping')
		time.sleep(1)
		self.checkshot_callback()
	def stopwalk(self):
		if not self.isstop: return False
		self.setstatus(None)
		self.button_stop['state']='disabled'
		self.button_start['state']='normal'
		return True
	def step1_walk(self):
		if self.stopwalk(): return
		if self.iscover:
			self.filename_step=self.outputdir+'cap-cover.png'
		else:
			self.filename_step=self.outputdir+'cap%05d.png'%self.capindex
		self.setstatus('Fetching image for '+self.filename_step)

		pgm=self.aw.fetchcap()
		rawbytes=pgm.tobytes()
		if self.lastrawbytes==rawbytes:
			self.setstatus(None)
			self.button_stop['state']='disabled'
			self.button_start['state']='normal'
			return
		self.lastrawbytes=rawbytes

		self.pgm_step=pgm
		self.master.after(0,self.step2_walk)

	def step2_walk(self):
		if self.stopwalk(): return
		pgm=self.pgm_step
		filename=self.filename_step
		self.setstatus('Saving '+filename)

		if self.iscover:
			f=open(filename,'wb')
		else:
			f=open(filename,'xb')
			self.capindex+=1
		PngCompress.create(f,pgm.width,pgm.height,pgm.rows)
		self.setcapstring()

		if self.ispreviews:
			self.master.after(0,self.step3_walk)
		else:
			self.master.after(0,self.step4_walk)

	def step3_walk(self):
#		if self.stopwalk(): return
		filename=self.filename_step
		self.setstatus('Drawing preview of '+filename)

		pgm=self.pgm_step
		xscale=int((399+pgm.width)/400)
		yscale=int((599+pgm.height)/600)
		scale=max(xscale,yscale)
		self.pagedata=pgm.tobytes()
		self.pageimage=tk.PhotoImage(data=self.pagedata).subsample(scale,scale)
		self.page_label['image']=self.pageimage

		self.master.after(0,self.step4_walk)
	def step4_walk(self):
		if self.stopwalk(): return
		if self.iscover:
			self.setstatus(None)
			self.iswalking=False
			return
		self.setstatus('Sending swipe')

		self.aw.advance()
		self.setstatus('Sleeping')

		self.master.after(500,self.step1_walk)
	def walkbook_callback(self):
		if not self.outputdir: return
		if self.iswalking: return
		self.iswalking=True
		self.isstop=False
		self.iscover=False
		self.button_start['state']='disabled'
		self.button_stop['state']='normal'
		self.step1_walk()
	def stopwalk_callback(self):
		self.isstop=True
	def coverpage_callback(self):
		if not self.outputdir: return
		if self.iswalking: return
		self.iswalking=True
		self.iscover=True
		self.step1_walk()


outputdir=None
ispreviews=True
args=sys.argv[1:]
for arg in args:
	if arg=='--nopreviews': ispreviews=False
	elif arg.startswith('--dir='):
		outputdir=arg[6:]
		if not outputdir.endswith('/') and not outputdir.endswith('\\'): raise ValueError
	else: raise ValueError

blankpgm=PGM(400,600,[])
blankrow=b'\xff'*400
for _ in range(600): blankpgm.rows.append(blankrow)

root=tk.Tk()
root.title('ADB Capture')
app=Application(root,blankpgm,outputdir,ispreviews)
app.mainloop()
