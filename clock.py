#!/usr/bin/env python3

USE_GEVENT = False

import datetime
import os
import random
import re
import ssl
import socket
import subprocess
import sys
import threading
import time

# apt install python3-bottle
import bottle

if USE_GEVENT and os.name != 'nt':
	# apt install python3-gevent

	import gevent
	import gevent.ssl
	import gevent.monkey; gevent.monkey.patch_all()

# apt install python3-numpy

import numpy

# The apt package for pillow is too old, so use pip
# pip3 install pillow
# [or] pip3 install --break-system-packages pillow

import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageEnhance

# pip3 install adafruit_blinka_raspberry_pi5_piomatter
# [or] pip3 install --break-system-packages adafruit_blinka_raspberry_pi5_piomatter

import adafruit_blinka_raspberry_pi5_piomatter as piomatter


next_times = [ 800, 915, 930, 1045, 1100, 1215, 1230, 1345, 1400, 
	       1515, 1630, 1730, 1900, 2000 ]

countdown_name = "countdown"

p_width = 64
t_width = p_width * 2

height = 32

fnt_l = None
fnt_m = None
fnt_s = None

ALLOW_ADDRS = []
OUR_ID = 1

global_mode = 1
last_global_mode = [-1, -1]

active_countdown = None
pause_countdown = None
countdown_timer = None
show_sec = 0

last_display_change = 0

def decrement_countdown():
	global active_countdown
	global pause_countdown
	global show_sec

	while True:

		if active_countdown is not None and pause_countdown is None:
			active_countdown -= 1

			# Only display "STOP" for 5 minutes
			if active_countdown < -5 * 60:
				active_countdown = None

		if pause_countdown is not None:
			now = time.time()

			# Safety feature - Paused timer - stop after 30 minutes

			if now - pause_countdown > 30 * 60:
				pause_countdown = None
				active_countdown = None

		# Show sec rotates 0..11 and can be used to display multiple items

		show_sec -= 1
		if show_sec < 0:
			show_sec = 11
		
		time.sleep(1) # This will drift, unfortunately


def find_fonts():
	global fnt_l
	global fnt_m
	global fnt_s


	fnt_l = PIL.ImageFont.load("fonts/100dpi/timB18.pil")
	fnt_m = PIL.ImageFont.load("fonts/75dpi/helvR08.pil")
	fnt_s = PIL.ImageFont.load("fonts/75dpi/courR08.pil")


	return (fnt_l, fnt_m, fnt_s) 

def load_next_times():
	global next_times

	if os.path.isfile("etc/next-times.txt"):
		next_times = []
		f = open("etc/next-times.txt")

		for line in f:
			line = line.strip()

			# Add if a valid number
			if line.isdigit():
				next_times.append(int(line))
		
		next_times.sort()
		f.close()

		print("Loaded", len(next_times), "next times")
		print(next_times)

def get_next_time():
	now = datetime.datetime.now().astimezone()
	hh = now.hour
	mm = now.minute

	hhmm = hh * 100 + mm

	v = 0
	for i in range(len(next_times)):
		if next_times[i] < hhmm:
			v = i + 1

	if v >= len(next_times):
		v = 0

	if v < len(next_times):
		hh = next_times[v] // 100
		mm = next_times[v] % 100
	else:
		hh = 23
		mm = 59

	s =  str(hh).zfill(2) + ":" + str(mm).zfill(2)
	
	return s

def get_local_time():
	now = datetime.datetime.now().astimezone()
	hh = now.hour
	mm = now.minute

	ampm_s = "AM"

	if hh >= 12:
		ampm_s = "PM"

	if hh > 12:
		hh = hh - 12

	if hh == 0:
		hh = 12	

	#time_s = str(hh).rjust(2) + ":" + str(mm).zfill(2)
	time_s = str(hh) + ":" + str(mm).zfill(2)
	tz_s = now.tzname()

	return (time_s, ampm_s, tz_s, 'yellow', 'rgb(0,0,128)')


def display_countdown():
	if active_countdown is not None:
		m = active_countdown // 60
		s = active_countdown % 60

	if active_countdown is None or active_countdown <= 0:
		if show_sec % 3 == 2 and active_countdown < -5:
			s = ""
		else:
			s = "STOP"

		color = 'red'

	elif m == 0:
		s = str(s) + "s"
		color = 'red'

	#elif m < 5:
	#	s = str(m) + "m"
	#	color = 'orange'

	else:
		if m > 90:
			hh = m // 60
			mm = m % 60

			if mm > 9:
				s = str(hh) + "h" + str(mm).zfill(2) # + "m"
			else:
				s = str(hh) + "h" + str(mm) + "m"

		else:
			s = str(m) + ":" + str(s).zfill(2)

		color = 'green'

		if m < 5:
			color = 'orange'

	if pause_countdown is None:
		s2 = countdown_name
	else:
		s2 = "paused"
		color = 'gray'

	return (s, "", s2, color, 'firebrick')


def is_auth(id):
	# https://stackoverflow.com/questions/31405812/how-to-get-client-ip-address-using-python-bottle-framework
	client_ip = bottle.request.environ.get('HTTP_X_FORWARDED_FOR') or \
		    bottle.request.environ.get('REMOTE_ADDR')

	return id == OUR_ID or client_ip in ALLOW_ADDRS

@bottle.get("/timer/<id:int>/show")
def show_countdown(id):
	if not is_auth(id):
		return ""

	s = "No Countdown"

	if active_countdown is not None:
		m = active_countdown // 60
		s = active_countdown % 60

		if active_countdown <= 0:
			s = "STOP / TIMES UP"
		elif m < 60:
			s = str(m) + ":" + str(s).zfill(2)
		else:
			hh = m // 60
			mm = m % 60

			s = str(hh) + ":" + str(mm).zfill(2) + ":" + \
			    str(s).zfill(2)
			

		if pause_countdown is not None:
			s = s + " (paused)"

	return s

@bottle.get("/timer/<id:int>/set/<num_seconds:int>")
def set_countdown(id, num_seconds):
	global active_countdown
	global countdown_name

	if not is_auth(id):
		return ""

	if num_seconds is None: 
		active_countdown = None

	else:
		num_seconds = int(num_seconds)
		countdown_name = "countdown"

		if num_seconds <= 0:
			active_countdown = None
		else:
			active_countdown = num_seconds

	return show_countdown(id)

@bottle.get("/timer/<id:int>/add/<num_seconds:int>")
def add_countdown(id, num_seconds):
	global active_countdown
	
	if not is_auth(id):
		return ""

	if num_seconds is None:
		active_countdown = None

	else:
		num_seconds = int(num_seconds)

		if num_seconds > 0:
			if active_countdown is None:
				active_countdown = num_seconds
			else:	
				active_countdown += num_seconds
		else:
			if active_countdown is None:
				pass
			else:	
				active_countdown += num_seconds


	return show_countdown(id)


@bottle.get("/timer/<id:int>/stop")
def countdown_stop(id):
	global active_countdown
	global pause_countdown

	if not is_auth(id):
		return ""

	active_countdown = None
	pause_countdown = None

	return show_countdown(id)

@bottle.get("/timer/<id:int>/pause")
def countdown_pause(id):
	global pause_countdown

	if not is_auth(id):
		return ""

	if active_countdown is not None and pause_countdown is None:
		pause_countdown = time.time()

	return show_countdown(id)


@bottle.get("/timer/<id:int>/resume")
def countdown_pause(id):
	global pause_countdown

	if not is_auth(id):
		return ""

	if active_countdown is not None and pause_countdown is not None:
		pause_countdown = None


	return show_countdown(id)

@bottle.get("/timer/<id:int>/off")
def clock_off(id, local=False):
	global global_mode

	if not local and not is_auth(id):
		return ""
	
	global_mode = 0
	
	return "OFF"

@bottle.get("/timer/<id:int>/on")
def clock_on(id, local=False):
	global global_mode

	if not local and not is_auth(id):
		return ""
	
	global_mode = 1
	
	return "ON"

@bottle.get("/timer/<id:int>/logo")
def clock_logos(id):
	global global_mode

	if not is_auth(id):
		return ""
	
	global_mode = 2
	
	return "LOGOS"


def missing_or_old(filename):
    result = False

    if os.path.isfile(filename):
        mtime = os.path.getmtime(filename)
        now = time.time()

        diff_time = now - mtime
        #print("Diff time", filename, diff_time)

        # Older than 3/4 of a year?
        if diff_time > (60 * 60 * 24 * 274):
            result = True
    else:
        result = True

    return result

 
def create_button(title, partial_url, width=1):
	s = "<button onclick=\""

	s += "pressButton('" + "/timer/" + str(OUR_ID) + "/" 
	s += partial_url + "')\""

	s += " class=\"button\""
	s += " style=\"width: " + str(6 * width) + "em;\""

	s += ">" + title + "</button>\n\n"

	return s


def handle_timer_post():
	global countdown_name

	newval = bottle.request.forms.get('newval')
	untilval = bottle.request.forms.get('until')
	newname = bottle.request.forms.get('newname')

	print("Newval: ", newval)
	print("Until: ", untilval)

	if newval is not None:
		m = re.search(r"^\s*(\d+)\s*:(\d+)\s*(:\s*(\d+)\s*)?", 
			      newval)

		if m is not None:
			g1 = m.group(1)
			g2 = m.group(2)
			g4 = m.group(4)

			if g4 is None:
				t = int(g1) * 60 + int(g2)
			else:
				t = int(g1) * 3600 + int(g2) * 60 + int(g4)

			set_countdown(OUR_ID, t)

	elif untilval is not None:
		m = re.search(r"^\s*(\d+)\s*:(\d+)\s*(:\s*(\d+)\s*)?", 
			      untilval)

		if m is not None:
			print("Until")

			g1 = m.group(1)
			g2 = m.group(2)
			g4 = m.group(4)

			if g4 is None:
				t = int(g1) * 3600 + int(g2) * 60
			else:
				t = int(g1) * 3600 + int(g2) * 60 + int(g4)

			now = datetime.datetime.now().astimezone()
			hh = now.hour
			mm = now.minute
			ss = now.second

			now_in_sec = hh * 3600 + mm * 60 + ss

			print("target", t, "now", now_in_sec)

			if t > now_in_sec:
				t = t - now_in_sec
				set_countdown(OUR_ID, t)

	elif newname is not None:
		print("Newname", newname)
		countdown_name = newname

@bottle.get("/timer/<id:int>/menu")
@bottle.post("/timer/<id:int>/menu")
def web_menu(id):
	if not is_auth(id):
		return ""

	handle_timer_post()
	
	s = "<fieldset><legend>Set Timer</legend>"
	s += create_button("5m", "set/300")
	s += create_button("10m", "set/600")
	s += create_button("15m", "set/900")
	s += create_button("30m", "set/1800")
	s += create_button("1h", "set/3600")

	s += "<br />"
	s += "<br />"

	s += "<div class=\"horizontal\">\n"
	s += "<div class=\"hblock\">\n"

	s += "<label>Manually Set Timer<br />\n"
	s += "<span class=\"extratext\">(hh:mm:ss or mm:ss)</span>:</label>\n"

	s += "<form method=\"post\" " + \
	     "action=\"/timer/" + str(OUR_ID) + "/menu\" " + \
	     "enctype=\"multipart/form-data\">"

	s += "<input type=\"text\" value=\"00:05:00\" " + \
	     "name=\"newval\" width=\"15em\" />"
	s += "<input type=\"submit\" value=\"Set\" />"
	s += "</form>"

	s += "</div><div class=\"hblock\">\n"
	#s += "<br />"

	s += "\n"

	s += "<label>Countdown Until<br />"
	s += "<span class=\"extratext\">(hh:mm:ss hh:mm)</span>:</label>\n"

	s += "<form method=\"post\" " + \
	     "action=\"/timer/" + str(OUR_ID) + "/menu\" " + \
	     "enctype=\"multipart/form-data\">"

	s += "<input type=\"time\" value=\"" + get_next_time() + "\" " + \
	     "name=\"until\" />"
	s += "<input type=\"submit\" value=\"Set\" />"
	s += "</form>"

	s += "</div><div class=\"hblock\">\n"

	s += "<label>Rename Timer<br />\n"
	s += "<span class=\"extratext\">(only when running)</span>:</label>\n"

	s += "<form method=\"post\" " + \
	     "action=\"/timer/" + str(OUR_ID) + "/menu\" " + \
	     "enctype=\"multipart/form-data\">"

	s += "<input type=\"text\" value=\"" + countdown_name + "\" " + \
	     "name=\"newname\" />"
	s += "<input type=\"submit\" value=\"Set\" />"
	s += "</form>"

	s += "</div></div>\n"

	s += "</fieldset>\n"
	s += "<br />"

	s += "<fieldset><legend>Adjust Timer</legend>"
	s += create_button("+10m", "add/600")
	s += create_button("+1m", "add/60")
	s += create_button("-1m", "add/-60")
	s += create_button("-10m", "add/-600")

	s += "</fieldset>"
	s += "<br />"

	s += "<fieldset><legend>Timer Controls</legend>"
	s += create_button("Stop", "stop", 4)

	s += "<br />"

	s += create_button("Pause", "pause", 2)
	s += create_button("Resume", "resume", 2)

	s += "</fieldset>"

	s += "<br />"

	s += "<fieldset><legend>Display Controls</legend>"
	s += create_button("Display Off", "off", 2)
	s += create_button("Display Time", "on", 2)
	s += create_button("Display Logos", "logo", 2)

	s += "</fieldset>"
	s += "<br />"

	return bottle.template("html/menu.html", 
			       main=s, 
			       init_status=show_countdown(id))

@bottle.get("/static/<filename>")
def static_file(filename):

	if filename == "" or "/" in filename or filename[0] == ".":
		return ""

	fullname = "html/" + filename

	if not os.path.isfile(fullname):
		return ""

	print("Sending file", fullname)
	return bottle.static_file(fullname, root=os.getcwd())

@bottle.get("/")
def redirect_main():
	if not is_auth(None):
		return ""

	bottle.redirect("/timer/0/menu")


def get_utc_time():
	now = datetime.datetime.utcnow()

	time_s = str(now.hour).zfill(2) + ":" + str(now.minute).zfill(2)
	
	return (time_s, "", "UTC", 'green', 'brown')

def center(draw, s, fnt, color, y, screen_num=0):
	(l,t,r,b) = draw.textbbox((0,y), s, font=fnt)

	x = p_width // 2 - (r-l) // 2
	y = y - (t - y)
	
	if x < 0:
		x = 0

	x = x + p_width * screen_num

	draw.text((x,y), s, fill=color, font=fnt)

	end_x = x + l - r
	end_y = y + b - t

	return (end_x, end_y)


def draw_normal_screen(draw, screen_num, mode):
	x = p_width * screen_num
	outline = 'blue'

	show_countdown = False
	if active_countdown is not None:
		if mode == 1 or global_mode == 2:
			show_countdown = True

		elif active_countdown > -60 and active_countdown < 60:
			show_countdown = True
		
	if show_countdown:
		(time_s, ampm_s, tz_s, color1, color2) = display_countdown()
		outline = 'white'

	elif mode == 1:
		if active_countdown is None or show_sec != 0:
			(time_s, ampm_s, tz_s, color1, color2) = get_local_time()
		else:
			(time_s, ampm_s, tz_s, color1, color2) = get_utc_time()

	else:
		if active_countdown:
			(time_s, ampm_s, tz_s, color1, color2) = get_local_time()
		else:
			(time_s, ampm_s, tz_s, color1, color2) = get_utc_time()

	draw.rectangle((x, 0, x+p_width-1, height-1), 
	       fill='black', outline=outline, width=1)

	center(draw, time_s, fnt_l, color1, -2, screen_num) 

	draw.rectangle((x+1,30 - 7,x+62, 30), fill=color2)

	center(draw, tz_s, fnt_m, 'white', 31-10, screen_num)

def draw_screen(image, draw, screen_num, mode):
	x = p_width * screen_num

	if global_mode == 0:
		# Do only once
		if global_mode != last_global_mode[screen_num]:
			draw.rectangle((x, 0, x+p_width-1, height-1), 
	       			fill='black', outline='black', width=1)

	elif global_mode == 2 and active_countdown is None:
		# Do only once
		if global_mode != last_global_mode[screen_num]:
			png_image = PIL.Image.open("photos/screen" + 
					   str(screen_num) + 
					   ".png")
			image.paste(png_image, 
				    (x, 0))
	else:
		draw_normal_screen(draw, screen_num, mode)

	last_global_mode[screen_num] = global_mode

def display_on_and_off():
	global last_display_change

	n = datetime.datetime.now()

	hhmm = n.hour * 100 + n.minute

	if last_display_change != hhmm:
		if hhmm == 2100:
			last_display_change = hhmm	
			clock_off(OUR_ID, local=True)

		elif hhmm == 600:
			last_display_change = hhmm	
			clock_on(OUR_ID, local=True)
			
def clock_thread_func():
	global countdown_timer

	geometry = piomatter.Geometry(width=t_width, 
			      height=height, 
			      n_addr_lines=4,
                              rotation=piomatter.Orientation.Normal)

	image = PIL.Image.new('RGB', (t_width, height), color='black')

	draw = PIL.ImageDraw.Draw(image)

	framebuffer = numpy.asarray(image) + 0  # Make a mutable copy
	matrix = piomatter.PioMatter(
			     colorspace=piomatter.Colorspace.RGB888Packed,
                             pinout=piomatter.Pinout.AdafruitMatrixBonnet,
                             framebuffer=framebuffer,
                             geometry=geometry)

	(fnt_l, fnt_m, fnt_s) = find_fonts()

	d_countdown_timer = threading.Thread(target=decrement_countdown)
	d_countdown_timer.start()

	while True:
		display_on_and_off()

		draw_screen(image, draw, 0, 0)
		draw_screen(image, draw, 1, 1)

		#image.save("/tmp/t.gif")

		#enhancer = PIL.ImageEnhance.Brightness(image)
		#image = enhancer.enhance(0.8)
	
		framebuffer[:] = numpy.asarray(image)

		matrix.show()

		now = datetime.datetime.now()
		time.sleep(1)

def load_id():
	global OUR_ID

	ok = False

	if os.path.isfile("etc/our-id.txt"):
		f = open("etc/our-id.txt")
		id = f.readline().strip()

		if id.isdigit():
			OUR_ID = int(id)
			ok = True

		f.close()
	
	if not ok:
		OUR_ID = random.randint(1,99999999)
		print("No etc/our_id.txt file, using random int of", OUR_ID)

	if os.path.isfile("etc/allow-addrs.txt"):
		for line in open("etc/allow-addrs.txt"):
			line = line.strip()
			ALLOW_ADDRS.append(line)

def create_certs_if_needed():

    if not os.path.isdir("cache/ssl"):
        os.mkdir("cache/ssl")

    needed = missing_or_old("cache/ssl/server.crt")
    needed = needed or missing_or_old("cache/ssl/server.key")

    if needed:
        print("(Re)creating the .crt and .key file", file=sys.stderr)

        subprocess.run(["openssl", "req",
                        "-x509", "-nodes", "-new",
                        "-keyout","cache/ssl/server.key",
                        "-out", "cache/ssl/server.crt",
                        "-days", "3650",
                        "-subj",
                        "/C=/ST=/L=/O=/OU=web/CN=" + socket.gethostname()])

        f_out = open("cache/ssl/server.pem", "w")

        f_in = open("cache/ssl/server.crt")
        f_out.write(f_in.read())
        f_in.close()

        f_out.write("\n")

        f_in = open("cache/ssl/server.key")
        f_out.write(f_in.read())
        f_in.close()

        f_out.close()

    return needed


def main():
	os.chdir("/root/socclock")

	clock_thread = threading.Thread(target=clock_thread_func)
	clock_thread.start()

	load_id()
	load_next_times()

	# Windows doesn't appear to support gevent properly, 
	# so no TLS/SSL for you

	if os.name == 'nt' or not USE_GEVENT:
		if os.name != 'nt':
			create_certs_if_needed()

		bottle.run(host='0.0.0.0', port=8888)

	else:
		create_certs_if_needed()

		ssl._create_default_https_context = ssl._create_unverified_context

		# Ignore the SSL: SSLV3_ALERT_CERTIFICATE_UNKNOWN error
		# TODO: Find a better way of telling bottle to ignore these
		#contextlib.suppress(ssl.SSLError)

		my_ssl_context = \
			gevent.ssl.SSLContext(gevent.ssl.PROTOCOL_TLS)
			#gevent.ssl.SSLContext(gevent.ssl.PROTOCOL_TLS_SERVER)

		my_ssl_context.load_cert_chain(
			'cache/ssl/server.crt', 
			'cache/ssl/server.key')

		my_ssl_context.check_hostname = False
		my_ssl_context.verify_mode = gevent.ssl.CERT_NONE

		bottle.run(host='', port=8888,
			server='gevent',
			ssl_context=my_ssl_context)

main()
