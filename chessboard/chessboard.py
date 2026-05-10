#!/usr/bin/python3

#  * github.com/sanjayrao77
#  * chessboard.py - program to draw chessboards in xth format
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
import struct
import sys
import zlib

class Xth():
	@classmethod
	def writetofile(parent,fb,fout):
		xth=parent(fb.width,fb.height)
		xth.loadfb(fb)
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
	def loadfb(self,fb):
		width=fb.width
		if len(fb.rows)!=fb.height: raise ValueError('PGM should have %s rows but it has %s instead'%(self.height,len(pgm.rows)))
		b1bits=(1,1,0,1,0)
		b2bits=(1,1,1,0,0)
		for row in fb.rows:
			ba1=bytearray()
			self.plane1.append(ba1)
			ba2=bytearray()
			self.plane2.append(ba2)
			for x in range(0,width,8):
				s=row[x:x+8]
				b1=0
				b2=0
				c=s[0]
				b1=b1bits[c]<<7
				b2=b2bits[c]<<7
				c=s[1]
				b1|=b1bits[c]<<6
				b2|=b2bits[c]<<6
				c=s[2]
				b1|=b1bits[c]<<5
				b2|=b2bits[c]<<5
				c=s[3]
				b1|=b1bits[c]<<4
				b2|=b2bits[c]<<4
				c=s[4]
				b1|=b1bits[c]<<3
				b2|=b2bits[c]<<3
				c=s[5]
				b1|=b1bits[c]<<2
				b2|=b2bits[c]<<2
				c=s[6]
				b1|=b1bits[c]<<1
				b2|=b2bits[c]<<1
				c=s[7]
				b1|=b1bits[c]
				b2|=b2bits[c]
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

class FB():
	def frombytes(width,height,data):
		data=base64.decodebytes(data)
		data=zlib.decompress(data)
		rows=[]
		for y in range(height):
			rows.append(data[y*width:(y+1)*width])
		return FB(width,height,rows)
	def white(width,height):
		rows=[]
		one=b'\x04'*width
		for _ in range(height): rows.append(bytearray(one))
		return FB(width,height,rows)
	def __init__(self,width,height,rows): (self.width,self.height,self.rows)=(width,height,rows)
	def fillsquare(self,x,y,side,color):
		one=color*side
		for row in self.rows[y:y+side]: row[x:x+side]=one
	def draw(self,dest,xoff,yoff):
		for y in range(self.height):
			inrow=self.rows[y]
			outrow=dest.rows[yoff+y]
			for x,c in enumerate(inrow):
				if not c: continue
				outrow[xoff+x]=c
	def clockwise(self):
		(w,h,inrows)=(self.width,self.height,self.rows)
		outrows=[]
		for x in range(w):
			outrow=bytearray()
			outrows.append(outrow)
			for r in reversed(inrows): outrow.append(r[x])
		return FB(self.height,self.width,outrows)
	def counterclockwise(self):
		(w,h,inrows)=(self.width,self.height,self.rows)
		outrows=[]
		for x in reversed(range(w)):
			outrow=bytearray()
			outrows.append(outrow)
			for r in inrows: outrow.append(r[x])
		return FB(self.height,self.width,outrows)

pieces={}
pieces['p']=FB.frombytes(54,54,b'eJztlEsOhDAMQ2ni+595gELVD02dLEYjDV7zZCdO2bZXfyzsijBuDghgx+eSkviw/eN0yklpptRHSabkG16BuY7V6WVFY2dPxYvFUJaRK2MhTUVKYnrHu0Mq56U1RS6/mspRdJSKJey2wVLSBGQpNFZ0zdVLcUDNHTIY0N8hgQFjX0tsgChshIjlozuMch4W1lbFlvaUb51xYmUf4/NUq8mmVqaZWtT07xHzmo5lvugoZekXqFcfMOYHNQ==')
pieces['n']=FB.frombytes(54,54,b'eJztlN0OwyAIhcvP+z/zRLe1hQNqsoslGxdtYvw8BwSP4x9fFrqzt8X1v0gx23ZVph2KiI1iog2xRpGoyvitcn0/NyX7ymp2nboELykqkw+ZYl5qxARTfSXl5UrK6g5Mlpj5U9PbwXRIwdTy3MwaYynDcqmGJVDmEVVhKpbkMxHL8inFgJRfAWWMUuyXosUoBe4gUgAKB3mLoW1trALlLba7kqsjUXR/gbrn0a2g+gSts5fG8KJbB9Qdgg3mqX4wy1ko2GChiHayVfGZMR6YWHoV0XfCyZSB7higFlDS9loqTR6ddGj8hYXK7FLFUOdU7q+kivejoIqnqqBy6PNUGRlVYin00/EAWUUH7g==')
pieces['b']=FB.frombytes(54,54,b'eJztlEkWwzAIQ2PE/c9cxw4eyICcRTetdsnjPybhbfuLkGa9gpYx1TeYKlLCIpWzpKzFZDlcUpJVCrUtrJVo1BKk+mKIJU2ZIY8dzC6e0zrAKiExPXZl4rAGiTSMgVp0LzKmkGaKsKOlEuRYQLhk1pUtmeusF9grjEv8JoV5xcYH3sfgpsFVAeX9RHoK6rIJc5z19nGAUr6EMCLUiXo8SmATf1+nYTAUZop5gffmnaj7ulJEYRyFDSTcF9Q1Bn7LlpBemIpbMwJrXE/icSKnqDLyZ9AV1d2LB67WPwo3v/iO7pKdrqPkufgrbtxw5dS3d/7ll5AjYosSMT+pD/s6CmU=')
pieces['r']=FB.frombytes(54,54,b'eJztlckOgCAMRCnT//9mKYkEoYvcXHinRvPspKaQ0uZX8ElX8uWxaoEEcCv7Gr6V5buZxjqwCAWisY4snWdY7GBajGxj/a/UBj5jS1VTU8KTxDPieU6x9IDb2tZXLdZPAUTrpfdyF8xoFTQzNjnYZmMWwTzWrZrfsfQbjOX6cI5eebuUzkn5AgshmnWD2doUDimzCMQ=')
pieces['q']=FB.frombytes(54,54,b'eJztlklyxDAIRc1w/zPHWPCFBuROqrJJhY1sxBOj1X1d//J7ovoj6HMMtipEop/xZttMlIm4PSn4iiLYwpfxtKUQF8FWRRQ86WAWUFgoRzA9GxWOXUmYncZz5uZr4i3WnmGOXBkPvKiQdVSp7+BguO8nRoURAyhBYdA5Xcz8PUWBLnkNcvRjB1C7MEa/NDnlEbKQcfKzh9l4knHvCyUxE9Sc2WrWqlHfG58HC8MW0wEqJqOPaMZGH9pW3ficErMYw/pxcTvtNNOSVsyHW90V5ry6fkOJb1NbKa+uXr8yOKG275Q45S5n6hqccFA8uFygKwyaeXshoaRc0wLFt8ggpqkpsU/eBLbOQ7ujbr3HtRMW2d5vWiNUFSNqf4D2d6I3h3gSL2d1kWpkHjXJb+Xte28W9eB9KcYYVzld9JnqGb1TOZchx0OAT6eX1PjpcF2N02zUVA0Vk3G9DUcV4inAOsS6WyaHiSq98bn0G5Ll/b8DRrd9yTr/aL2h3wD+inwBLpsKhA==')
pieces['k']=FB.frombytes(54,54,b'eJztlUsSAyEIRGPj/c+cEXBUZFBTlazSlc0Qn9jg5/X663si+oQCfkUR65TKGcj5PNvvfGXK1+8UUh1DRKfYBSClq4hbtdfJS6Z0idp3tKomFApjbAFRoyjEZDQAmnO1sAPxwDr29jWGJyg1kX5WWmUxGiCZl0dhCJtOjHNqHchCZQ3jAs3/YslMxUsIqWSsblI0pzLU7IuTTSGaaugscZHK9uuBWrXZpR62VL8YlIsNiCG2plt22OZl71ZP3hGVEdLdsstLQsg1oGEHuk+Y17mnQ8lY1wCwWsmDW04qMhpjW8+ZhFKCnakrCYZUrVnXBPfwm1y2FrUeIcWDOmNEacMXbmNFtSBrX8ZYnSamHGOLZ0Lr3ifTVPFT1m7oZmvn+cuOVkwFtzbFX6I3yF4K2w==')
pieces['P']=FB.frombytes(54,54,b'eJztk8ESAyEIQ1fg/7+54jqOVmED01uXM28CIVzXW39cwixRhksrzkAxTLRfRNnAlFS7W5VCOFWbb6riEYpvimNURiu1l1pIXQo2UaGhBWM0zGh2YDPK8KIPCYkNK0KGLFKw+dNWeQqMR27CnBu8jMjgZ0qZxeBw9E/uSihEaw4JwVrnnENETcp+r0dsgyCMNgj4FvkKxoiHJ7aeCj2aHObrMzoUnaX8MJ63etqMLSkVy1Fm8s213MXMtdyPzlJe/ZYityzqrQ9SXgkp')
pieces['N']=FB.frombytes(54,54,b'eJztlusOwjAIhcfl/Z9ZaLe4wYFuiT9MlMTNmH49BwqN2/aP7wg93qLtukswkQyGiG5jSiKO2UOfUGoyarB/nlBqLnm82NhbGPt6sdX+NNz4u9QpZC/PwqFoDF7pKXGCLBaHwHQkFeUabNYdmOyw4c97AkSNyZSCqdmOlZQMCkJaNRiP9SCp3SMUQ0e1FuPKWiemKwiKxQb0zSOVGhJISfwpW8xS4AyixSwllMsTLaa2ZZIsHyk7Kz478rbL5xcTo0se/hXXJ2m9e2kOLzr1UI6zm/0eRQ0WqJm5sB7jju+CUI65s1dxHz/clbGIPo08L94ayt1h9tjBkVPV/3DG/GAbpWoyD7cF1FHNUEtJFffvpKiian8dBYZ6TbVXVUPV0OepLurKSxMP/rn8ULwA9AQRHg==')
pieces['B']=FB.frombytes(54,54,b'eJztltsagjAMg1nS939mKdvKDugCF95o7lR+07XpPrbtL0EEeJexdMjuUcgU7lrBDDfNdopm/Ar17FwbH/TQipX3RIfy85lVMWbG5ZyWEIdoRRQxL88aSUWeEKljjPKCXtdo0YighDhWq327dh7UzFAc6pTLh0WyEAWeFe4lLqj0iHrmhX7ElV9QbNLUpGrRwzFPYji67BYnIb/HFqOAPFZMCX3sceyzAOVFDonrPPVeMWtCL0c+35+DtK2ctWwi21bUhiwpS8PBoDSxXrtn37UL2IYxf2b8LiMbi8bUf7ELenTwAUzRGrn+CZzp7f+ME4RutEiXX7WYJVn2tsBUfKajTiUizlLlXe2WGvPbzlVf59msn/lFvQANswi9')
pieces['R']=FB.frombytes(54,54,b'eJztlcEOhDAIRGHg/795i67GrMz06sbOiQRfoFOhZkuvEvwrM/d7DEIhS6gv9/AaQ1PhgEf+xhNq5I/oGs+oXs+gXIhSjqACu688Db9rXEH2lFl4tF1iJBizY60kNH6fvkGX0KIW9QQqGUWHqzSGr50vOSnJhjlUMfSlqhjZGpsXfNsIP4gX2kXmoHCx3gFFVb7pbsPE6gWaLkUdcbY/oDBVQ80h9oK9Xh+tpQ4n')
pieces['Q']=FB.frombytes(54,54,b'eJztVkuWhDAIlM/9zzxQAWJMsHszm3nDJooUUBWMXte//ZqpiH4dqxGqZKYPZweyUEYIsyozfDzxDchiSfySRFXIr4QM/wZTC1BBBcczUGx4PaEsUgo1+hLnJdlroCxsoo0NRwRJNiMB8raFIhPfGHo2wa0tI8CdnFeGx0Pnms7BPHqwJ5GNZBCcrsGaqhZlLX9CQVHCZUtltORVCzuaiUM5TzyCTc0oz7TsnFW6dYEr3yVUnXBvdZkyczBrxvB1mw1OlN3KY9ssSWXGs5yNQSaqTylKfARDJ8Nj9Wih0NfhU/ZhGDae01GomgyuEb0TW2vIWGWvuaLAo6JRYvAPtNSernIoJk4xALitFdOpmxgx2QYDyrZd72u4n2IMOZAcYZwoDnCUfKJ0KSKJkqXk9mpWwAjnZalUT9QVKDHjxdwTqA2Et5BgFRv46d1R9nrzyHk0S7CLUXK82PF04w8wOjQYR2gKcreQszlIDRbMk/39rj19TZBGDzlKkdS4I3VS/YSajIDqSzmxG5eFY/9RYX8uGzUfEWp55QCf9eiKvU9Hh5J3VNPiW4P5CT2I0e6WW7dj2o4GhqOTHv8IO1K4/ic6IEJovM05wPzNX87Y1zw0PvzX/C37AT4PD4s=')
pieces['K']=FB.frombytes(54,54,b'eJztVkESgzAIVOD/b64sxIQEk+pMe2k5VZplWSDotv3tcybyBMX8LRTB7qJEmJ8o+54u4X3nuxnKDrsHUxDRXRjSQ5JvcVixDyo6fgo5mVz3QJighQ4WUIFMGveFlGJcUdy4RxhbPPbIJyq4e5VcDpazRVd0R5imJ9XIHwvarU+SAsji4hQH9xGkRcWYBtMuR5DmEBPs/jdJXSh0YopCI3rfGkUjVYcadYEscbW6Nk5TTKhCwyQRkXm6oeIRljjSkWpyweDp/E1BGA8fWdqD0TnI2XqE3yBkLMpoz3Dn99pv2NADmm8eaSaPYbXkdL13rG5RGGRNl5VeBT+rylwVnHNUqVnTBVrsU8nmUeqGm+tqhNFbuvgUplYKstbVCfMwC1QibPGa8LXZkjnV/FUmVMtQizIZjJNvnPkVxoBafLNH3wG/Zi/dzAwi')
pieces['white']=FB.frombytes(108,20,b'eJztVMuSwzAIM4///+ZFCBuncTt72HYvZSatUWSERZIx/inc/XNaYnOl71bdtCS03G4M+7MWWitD71oH6Pdh2GxwLGwLLVO1SkxEFacjhF42aJls5sgWrRacgqO5yVaYJTiPSWihlmh66JqF4w9QVs61FSQllvpxiSnKOFOnR1E0LrVkI/FsVgW8BaGFyW5zd0inFhWwQat58FGTRa3YWAU7CJGxpF+0Ym/ELFzQmIrXZnCDzFixZUu/4BhQjduBAT5rZexaTFprXLRs9HloIYNbAogxVBt3rf1ROp5rHM+FCz5OHlmcn46j1kZtLd+aeNBSpny+OKp+T4R4w61VTsfPfIeRoBLeCDtq5U12I8JRxoCqgHIGPeGlZUn2dLsf8Kwnsrp90OJ8jHfST9ed/izqW7x/kg/Qk10vkW984xI/rZoFyg==')
pieces['black']=FB.frombytes(108,20,b'eJztVAluxCAMxPb8/831DSTsSm2qVqqKlASfYzMOY/zgAu671XpQfnkx1Y74gEXyS1jysMlPYIGeYjFYn8SCqODpTStwLJSG3GY+3aGIh1eODBvCIWDzZtIMZBU7FrGwCTA1e1+qw4KFDljCNYw6TBOJ2y0TuwLp7C6cZ9hCJFMsdF50gnm2LkmUKRkmFhSFB2h5B1/2Tr5gLmXVLzdLgRVuRbN/pQwZpjuLgrelvw0y9Y4FO48Ni+bIYKmxsXgtYmIFjp8xdY4NK6jZsJQIWbGufb3A0seFOeZ14GmtynlU1+bPV77GaPsNizPISAvusGLpxHrt2ZeNW/ALyTlMf7faIJgPTlgR1oMcJChfOfTsIyvta+PbxEWJ3YRQ+fS5XrDgRkQTUozTbG69YOf+dO2G7u2FfDd+7/39v/7k+gAtjgWF')

class Row():
	validchars={
		'q':('q',1), 'k':('k',1), 'b':('b',1), 'n':('n',1), 'r':('r',1), 'p':('p',1),
		'Q':('Q',1), 'K':('K',1), 'B':('B',1), 'N':('N',1), 'R':('R',1), 'P':('P',1),
		'1':(' ',1), '2':(' ',2), '3':(' ',3), '4':(' ',4), '5':(' ',5), '6':(' ',6), '7':(' ',7), '8':(' ',8) }
	def __init__(self):
		self.tiles=[' ',' ',' ',' ',' ',' ',' ',' ']
	def addpieces(self,text):
		i=0
		for c in text:
			p=Row.validchars[c]
			self.tiles[i]=p[0]
			i+=p[1]
		if i!=8: raise ValueError('missing tile')

class Board():
	def __init__(self,tilesize,flip=False):
		self.tilesize=tilesize
		self.flip=flip
		self.rows=[]
		for i in range(8): self.rows.append(Row())
	def addpieces(self,pieces):
		if self.flip:
			for i in range(8):
				text=list(pieces[i])
				text.reverse()
				text=''.join(text)
				self.rows[7-i].addpieces(text)
		else:
			for i in range(8):
				self.rows[i].addpieces(pieces[i])
	def draw(self,fb,txoff,tyoff):
		for y in range(8):
			row=self.rows[y]
			for x in range(8):
				xoff=self.tilesize*x
				yoff=self.tilesize*y
				if (x+y)&1: fb.fillsquare(xoff,yoff,self.tilesize,b'\x03')
				c=row.tiles[x]
				if c==' ': continue
				p=pieces[c]
				p.draw(fb,xoff+txoff,yoff+tyoff)

class Puzzle():
	def __init__(self,fen):
		self.fen=fen
		a=self.fen.split(' ')
		self.pieces=a[0].split('/')
		if a[1]=='w': self.iswhite=True
		elif a[1]=='b': self.iswhite=False
		else: raise ValueError('bad w/b: %s'%a[1])
	def addtoboard(self,board):
		board.addpieces(self.pieces)
	def draw(self,fb,xoff,yoff):
		if self.iswhite: pieces['white'].draw(fb,xoff,yoff)
		else: pieces['black'].draw(fb,xoff,yoff)

(width,height)=(792,528)
islandscape=True
fen='4k3/p2q1p2/1pQp2rp/6p1/1B6/3n4/PP3PPP/2R3K1 w - -'
outfilename='/tmp/chess.xth'

args=sys.argv[1:]
if not args:
	print('Usage: chessboard.py (--x3|--x4) (--landscape|--portrait) (FEN) (OUTPUTFILENAME.xth)')
	exit()
for arg in args:
	if arg=='--x3': (width,height)=(792,528)
	elif arg=='--x4': (width,height)=(800,480)
	elif arg=='--landscape': islandscape=True
	elif arg=='--portrait': islandscape=False
	elif arg=='--help':
		print('Usage: chessboard.py (--x3|--x4) (--landscape|--portrait) (FEN) (OUTPUTFILENAME.xth)')
		exit()
	else:
		if arg.endswith('.xth'): outfilename=arg
		else:
			a=arg.split('/')
			if len(a)!=8: raise ValueError
			if fen: raise ValueError
			fen=arg

puzzle=Puzzle(fen)
print('Saving',fen,'to',outfilename)
fout=open(outfilename,'wb')
if islandscape:
	fb=FB.white(width,height)
	board=Board(height>>3)
	puzzle.addtoboard(board)
	board.draw(fb,5,5)
	puzzle.draw(fb,height,10)
	Xth.writetofile(fb,fout)
else:
	fb=FB.white(height,width)
	board=Board(height>>3)
	puzzle.addtoboard(board)
	board.draw(fb,5,6)
	puzzle.draw(fb,10,height)
	Xth.writetofile(fb.counterclockwise(),fout)
fout.close()
