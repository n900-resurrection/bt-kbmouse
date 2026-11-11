# bt-kbmouse: service and settings GUI for a Bluetooth keyboard with a TrackPoint (Python 3 + hildonlite). Targets and conventions: ../../mk/app.mk
override APP     := bt-kbmouse
VERSION ?= 0.1
DEPS    := hildonlite
RUN_CMD := /usr/bin/bt-kbmouse
ICON_OUT := icons/64.png
include ../../mk/app.mk
