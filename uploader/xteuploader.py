#!/usr/bin/python3

#  * github.com/sanjayrao77
#  * xteuploader.py - program to upload files to XTEINK devices
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


import requests
import json
import sys
import io
import socket
import urllib
import base64

class HTTPReply():
	def __init__(self,status_code,replyheaders,content): (self.status_code,self.replyheaders,self.content)=(status_code,replyheaders,content)

def postfile(basicauth,hostname,uri,filename,fin):
	fin.seek(0,2)
	filesize=fin.tell()
	fin.seek(0)
	s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	addrs=socket.getaddrinfo(hostname,80,family=socket.AF_INET,type=socket.SOCK_STREAM)
	if not addrs: raise ValueError
	addr=addrs[0][4]
	print('Connecting to',addr)
	s.connect(addr)
	request1lines=[]
	request1lines.append('--76a9ef5fc9c1a0bcdcb0bb35488bf645')
	request1lines.append('Content-Disposition: form-data; name="data"; filename="'+filename+'"')
#	request1lines.append('Content-Type: text/plain')
	request1lines.extend(('',''))
	request1='\r\n'.join(request1lines).encode()
	request3='\r\n--76a9ef5fc9c1a0bcdcb0bb35488bf645--\r\n'.encode()
	postsize=len(request1)+filesize+len(request3)
	requestheaders=[]
	requestheaders.append('POST '+urllib.parse.quote(uri)+' HTTP/1.0')
	requestheaders.append('Host: '+hostname)
	if basicauth:
		b64=base64.standard_b64encode(basicauth.encode()).decode()
		requestheaders.append('Authorization: Basic '+b64)
	requestheaders.append('Content-Type: multipart/form-data; boundary=76a9ef5fc9c1a0bcdcb0bb35488bf645')
	requestheaders.append('Content-Length: '+str(postsize))
	requestheaders.append('Connection: close')
	requestheaders.extend(('',''))
	request0='\r\n'.join(requestheaders).encode()
	s.sendall(request0)
	s.sendall(request1)
	written=0
	while True:
		d=fin.read(64*1024)
		if not d: break
		written+=len(d)
		s.sendall(d)
		print('Sent %s bytes (%s%%)\r'%(written,int((100*written)/filesize)),end='')
	print()
	s.sendall(request3)
	fullreply=bytearray()
	while True:
		d=s.recv(1024)
		if not d: break
		print('Received',len(d),'byte reply')
		fullreply.extend(d)
		print('fullreply',fullreply)
	fullreply=fullreply.decode()
	lines=fullreply.split('\r\n')
	if not len(lines): raise ValueError
	statusline=lines.pop(0)
	replyheaders=[]
	if True:
		if not statusline.startswith('HTTP'): raise ValueError
		a=statusline.split(' ')
		status=int(a[1])
	while True:
		line=lines.pop(0)
		if not line: break
		replyheaders.append(line)
	httpreply='\r\n'.join(lines)
	return HTTPReply(status,replyheaders,httpreply)

def putvariable(basicauth,hostname,uri,varname,varvalue):
	s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	addrs=socket.getaddrinfo(hostname,80,family=socket.AF_INET,type=socket.SOCK_STREAM)
	if not addrs: raise ValueError
	addr=addrs[0][4]
	print('Connecting to',addr)
	s.connect(addr)
	postlines=[]
	postlines.append('--76a9ef5fc9c1a0bcdcb0bb35488bf645')
	postlines.append('Content-Disposition: form-data; name="'+varname+'"')
	postlines.append('')
	postlines.append(varvalue)
	postlines.append('--76a9ef5fc9c1a0bcdcb0bb35488bf645--')
	post='\r\n'.join(postlines).encode()
	requestheaders=[]
	requestheaders.append('PUT '+urllib.parse.quote(uri)+' HTTP/1.0')
	requestheaders.append('Host: '+hostname)
	if basicauth:
		b64=base64.standard_b64encode(basicauth.encode()).decode()
		requestheaders.append('Authorization: Basic '+b64)
	requestheaders.append('Content-Type: multipart/form-data; boundary=76a9ef5fc9c1a0bcdcb0bb35488bf645')
	requestheaders.append('Content-Length: '+str(len(post)))
	requestheaders.append('Connection: close')
	requestheaders.extend(('',''))
	request='\r\n'.join(requestheaders).encode()
	s.sendall(request)
	s.sendall(post)
	fullreply=bytearray()
	while True:
		d=s.recv(1024)
		if not d: break
		print('Received',len(d),'byte reply')
		fullreply.extend(d)
		print('fullreply',fullreply)
	fullreply=fullreply.decode()
	lines=fullreply.split('\r\n')
	if not len(lines): raise ValueError
	statusline=lines.pop(0)
	replyheaders=[]
	if True:
		if not statusline.startswith('HTTP'): raise ValueError
		a=statusline.split(' ')
		status=int(a[1])
	while True:
		line=lines.pop(0)
		if not line: break
		replyheaders.append(line)
	httpreply='\r\n'.join(lines)
	return HTTPReply(status,replyheaders,httpreply)


class XteX3():
	def __init__(self,hostname): self.hostname=hostname
	def ls(self,path):
		path=path or '/'
		if not path.startswith('/'): path='/'+path
		r=requests.get('http://%s/list?dir=%s'%(self.hostname,path))
		if r.status_code!=200: raise ValueError
		if r.content[0]!=91: # '['
			print('r.content',r.content)
			raise ValueError
		a=json.loads(r.content)
		return a
	def print_ls(self,path='/'):
		a=self.ls(path)
		a.sort(key=lambda it: (it['type'],it['name']))
		for e in a:
			if e['type']=='dir': print('directory ',e['name'])
			elif e['type']=='file': print('file %9d %s'%(int(e['size']),e['name']))
	def upload(self,infilename,outdir,outfilename,isverbose=True):
		if not outdir: outdir='/'
		elif not outdir.endswith('/'): outdir=outdir+'/'
		if not outdir.startswith('/'): outdir='/'+outdir
		if isverbose:
			fin=open(infilename,'rb')
			savefilename='%s%s'%(outdir,outfilename)
			r=postfile(None,self.hostname,'/edit',savefilename,fin)
		else:
			fin=open(infilename,'rb')
			files={'data':('%s%s'%(outdir,outfilename),fin)}
			r=requests.post('http://%s/edit'%self.hostname,files=files)
		if r.status_code!=200: raise ValueError
		print(r.content)
	def mkdir(self,outdir):
		if not outdir: raise ValueError
		elif not outdir.endswith('/'): outdir=outdir+'/'
		if not outdir.startswith('/'): outdir='/'+outdir
		r=putvariable(None,self.hostname,'/edit','path',outdir)
		if r.status_code!=200: raise ValueError
		print(r.content)

isverbose=True
ipv4=None
hostname=None
#ipv4=(192,168,1,214)
args=sys.argv[1:]

if ipv4: hostname='%s.%s.%s.%s'%ipv4

if not hostname:
	if args:
		hostname=args[0]
		args=args[1:]
	else:
		hostname=input('Please enter the IP address given by the ereader, e.g. "192.168.1.214": ')

if not args:
	print('Usage: xteuploader.py %s ls [DEVICE_DIRECTORY]'%hostname)
	print('Usage: xteuploader.py %s mkdir (DEVICE_DIRECTORY)'%hostname)
	print('Usage: xteuploader.py %s upload (FILENAME) (DEVICE_DIRECTORY)'%hostname)
	print('Usage: xteuploader.py %s upload (LOCAL_FILENAME) (DEVICE_DIRECTORY) (DEVICE_FILENAME)'%hostname)
	print('No command given, doing an "ls /"')
	args=['ls','/']

x=XteX3(hostname)

oldargs=args
args=[]
for arg in oldargs:
	if arg.startswith('--'):
		if arg=='--noverbose': isverbose=False
		else: raise ValueError('Unknown option',arg)
	else: args.append(arg)

while args:
	if args[0]=='ls':
		args=args[1:]
		if not args: rdir='/'
		else:
			rdir=args[0]
			args=args[1:]
		x.print_ls(rdir)
	elif args[0]=='mkdir':
		args=args[1:]
		if not args:
			print('Usage: xteuploader.py %s mkdir (DEVICE_DIRECTORY)'%hostname)
			break
		outdir=args[0]
		args=args[1:]
		x.mkdir(outdir)
	elif args[0]=='upload':
		if len(args)>=4:
			x.upload(args[1],args[2],args[3],isverbose=isverbose)
			args=args[4:]
		elif len(args)==3:
			a=args[1].split('/')
			x.upload(args[1],args[2],a[-1],isverbose=isverbose)
			args=args[3:]
		else:
			print('Usage: xteuploader.py %s upload (LOCAL_FILENAME) (DEVICE_DIRECTORY) (DEVICE_FILENAME)'%hostname)
	else: raise ValueError('Unrecognized command',args)
