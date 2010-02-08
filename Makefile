
all:
	echo Nothing to build

install:
	install -m655 -D smartpen-browser.glade $(DESTDIR)/usr/share/smartpen-browser/smartpen-browser.glade
