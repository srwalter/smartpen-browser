
all:
	echo Nothing to build

install:
	install -m655 -D smartpen-browser.glade $(DESTDIR)/usr/share/smartpen-browser/smartpen-browser.glade
	install -m755 $(DESTDIR)/usr/bin/smartpen-browser
