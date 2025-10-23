**SOC Clock**

This is a small digital clock that displays time in both local time and UTC time on two (or one) AdaFruit Matrix Portals, such as https://www.adafruit.com/product/4745

The clock was designed to support a Security Operations Center classroom (for in a Cybersecurity program) (hence it's name).

The clock has a web backend and can switch into countdown mode where the UTC clock is replaced with a countdown (e.g. if running a SOC scenario).

Needs the following Python modules:
* Pillow
* adafruit_blinka_raspberry_pi5_piomatter
* numpy (required for above)
* Bottle (for the web server)
* (Optionally) Gevent (for https over bottle)

You may also want fonts (I normally just grab a few of the X11 fonts in both 75dpi and 100dpi versions).  These go in a fonts/ directory

Finally, you will need to create the following files:
* etc/allow-addrs.txt  - A list of IP addresses that don't need a pin to access the webpage
* etc/our-id.txt - The PIN for web access (for IPs not in the allow-addrs.txt file)
* etc/next-times.txt - A list of times for next periods (in the form hhmm) used as a default for countdowns
