#!/usr/bin/python

import gtk
import pysmartpen
import xml.dom.minidom
import zipfile
import parsestf
import tempfile
import cairo
import os
import threading
import thread
import gobject
import subprocess

gobject.threads_init()

class ImagePopup(gtk.Menu):
    def __init__(self, view_cb, pdf_cb):
        super(gtk.Menu, self).__init__()

        mi = gtk.MenuItem('View Full Size...')
        mi.connect('activate', view_cb)
        mi.show()
        self.append(mi)
        mi = gtk.MenuItem('Export as PDF...')
        mi.connect('activate', pdf_cb)
        mi.show()
        self.append(mi)

class Parser(parsestf.STFParser):
    def __init__(self, stream):
        super(Parser, self).__init__(stream)
        self.last_force=0

    def handle_stroke_end(self, time):
        self.ctx.stroke()
        self.last_force = 0

    def handle_point(self, x, y, f, time):
        ctx = self.ctx
        if f:
            if self.last_force:
                ctx.line_to(x, y)
            else:
                ctx.move_to(x, y)
        self.last_force = 1

    def parse(self, ctx):
        self.ctx = ctx
        super(Parser, self).parse()


class Notebook(object):
    def __init__(self, pen, guid, title, pages, builder):
        self.guid = guid
        self.title = title
        self.pen = pen
        self.pages = pages
        self.is_rendered = False
        self.status_bar = builder.get_object('statusbar1')
        self.progress_bar = builder.get_object('progressbar1')
        self.builder = builder

        ls = gtk.ListStore(str, gtk.gdk.Pixbuf, str, str)
        self.ls = ls

        # XXX: cleanup temp dir
        self.tmpdir = tempfile.mkdtemp()

        self.work_queue = []
        self.work_queue_lock = threading.Lock()
        self.work_queue_sem = threading.Semaphore(0)
        args = tuple()
        self.thread = thread.start_new_thread(self.worker_thread, args)

        iv = gtk.IconView(ls)
        iv.connect('item-activated', self.page_activated)
        iv.connect('button-press-event', self.page_popup)
        iv.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("gray"))
        iv.set_text_column(0)
        iv.set_pixbuf_column(1)
        iv.show()

        sw = gtk.ScrolledWindow()
        sw.props.hscrollbar_policy = "never"
        sw.add(iv)
        sw.show()

        self.contents = sw

    def page_popup(self, iv, event):
        if event.button != 3:
            return None

        x = event.x
        y = event.y
        path = iv.get_path_at_pos(x, y)
        iv.set_cursor(path)

        def view_cb(*args):
            self._page_activated(path)

        def pdf_cb(*args):
            dlg = gtk.FileChooserDialog(title="Save As...",
                    action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                             gtk.STOCK_SAVE,gtk.RESPONSE_OK))
            filter = gtk.FileFilter()
            filter.set_name("PDF")
            filter.add_pattern("*.pdf")
            dlg.add_filter(filter)
            resp = dlg.run()
            filename = dlg.get_filename()
            dlg.destroy()

            if resp != gtk.RESPONSE_OK:
                return

            print filename

            fd, tmpfile = tempfile.mkstemp()
            self.pen.get_guid(tmpfile, self.guid, 0)
            z = zipfile.ZipFile(tmpfile, "r")
            name = self.ls[path][3]
            f = z.open(name)
            p = Parser(f)
            surface = cairo.PDFSurface(filename, 4963,6278)
            ctx = cairo.Context(surface)
            ctx.set_source_rgb(255,255,255)
            ctx.paint()
            ctx.set_source_rgb(0,0,0)
            try:
                p.parse(ctx)
            except Exception, e:
                print "Parse error"
                print e
            os.unlink(tmpfile)
            print "Done"

        popup = ImagePopup(view_cb, pdf_cb)
        popup.popup(None, None, None, event.button, event.time)
        return True

    def page_activated(self, iv, path):
        self._page_activated(path)

    def _page_activated(self, path):
        fn = self.ls[path][2]
        subprocess.call(["gnome-open", fn])

    def worker_thread(self):
        tmpdir = self.tmpdir

        def make_progress():
            if self.progress_bar:
                frac = self.progress_bar.get_fraction()
                frac *= self.progress_bar.props.discrete_blocks
                frac += 1
                frac /= float(self.progress_bar.props.discrete_blocks)
                self.progress_bar.set_fraction(frac)

        while True:
            self.work_queue_sem.acquire()
            self.work_queue_lock.acquire()
            work = self.work_queue.pop(0)
            self.work_queue_lock.release()

            i, f, name = work
            if i is None and f is None and name is None:
                break

            if self.status_bar:
                ctx = self.status_bar.get_context_id("THREAD")
                self.status_bar.push(ctx, "Rendering page %d..." % i)

            p = Parser(f)

            # XXX: get dimension from pen data
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 4963, 6278)
            ctx = cairo.Context(surface)
            ctx.set_source_rgb(255, 255, 255)
            ctx.paint()
            ctx.set_source_rgb(0,0,0)
            make_progress()
            try:
                p.parse(ctx)
            except Exception, e:
                print "Parse error"
                print e
            make_progress()
            fn = os.path.join(tmpdir, "page%d" % i)
            surface.write_to_png(fn)
            make_progress()
            img = gtk.gdk.pixbuf_new_from_file(fn)
            img = img.scale_simple(img.props.width / 20,
                                   img.props.height / 20,
                                   "bilinear")
            make_progress()
            self.ls.append(["Page %d" % i, img, fn, name])
            make_progress()
            if self.status_bar:
                ctx = self.status_bar.get_context_id("THREAD")
                self.status_bar.pop(ctx)

        if self.progress_bar:
            self.progress_bar.set_fraction(0.0)

    def add(self, notebook):
        tab = gtk.Label(self.title)
        tab.show()
        notebook.append_page(self.contents, tab)

    def render(self):
        if self.is_rendered is True:
            return

        fd, tmpfile = tempfile.mkstemp()
        self.pen.get_guid(tmpfile, self.guid, 0)
        z = zipfile.ZipFile(tmpfile, "r")

        i = 0
        for name in z.namelist():
            if not name.startswith('data/'):
                continue
            i += 1
            f = z.open(name)
            self.work_queue_lock.acquire()
            self.work_queue.append([i, f, name])
            self.work_queue_sem.release()
            self.work_queue_lock.release()

        if self.progress_bar:
            self.progress_bar.props.discrete_blocks = i * 5

        self.work_queue_lock.acquire()
        self.work_queue.append([None, None, None])
        self.work_queue_sem.release()
        self.work_queue_lock.release()
        self.is_rendered = True
        os.unlink(tmpfile)

class SmartpenBrowser(object):
    def pen_connect(self, *args):
        try:
            self.pen.connect()
        except:
            dlg = gtk.MessageDialog(self.window, 0, "error", gtk.BUTTONS_OK,
                    "Failed to connect to the pen.  Check permissions")
            dlg.run()
            dlg.destroy()
            return

        self.connected = True

        changes = self.pen.get_changelist()
        dom = xml.dom.minidom.parseString(changes)
        cl = dom.getElementsByTagName('changelist')[0]

        notebooks = []
        tabs = self.builder.get_object('notebook1')
        tabs.connect('switch-page', self.switch_page, notebooks)

        lsps = {}
        for elm in cl.getElementsByTagName('lsp'):
            guid = elm.getAttribute('guid')
            if not guid:
                continue

            if guid not in lsps:
                lsps[guid] = {}
                lsps[guid]['pages'] = []

            title = elm.getAttribute('title')
            lsps[guid]['title'] = title

            for p in elm.getElementsByTagName('page'):
                addr = p.getAttribute('pageaddress')
                lsps[guid]['pages'].insert(0, addr)

        for guid, value in lsps.items():
            nb = Notebook(self.pen, guid, value['title'], value['pages'],
                    self.builder)
            notebooks.append(nb)
            nb.add(tabs)
        pass

    def switch_page(self, notebook, page, page_num, notebooks):
        while gtk.events_pending():
            gtk.main_iteration()
        notebooks[page_num].render()

    def pen_disconnect(self, *args):
        self.pen.disconnect()
        self.connected = False

    def pen_info(self, *args):
        info = self.pen.get_info()
        dom = xml.dom.minidom.parseString(info)
        info = dom.getElementsByTagName('peninfo')[0]
        penid = info.getAttribute('penid')

        elem = info.getElementsByTagName('battery')[0]
        voltage = elem.getAttribute('voltage')
        battlevel = elem.getAttribute('level')

        elem = info.getElementsByTagName('memory')[0]
        totalmem = elem.getAttribute('totalbytes')
        freemem = elem.getAttribute('freebytes')

        elem = info.getElementsByTagName('version')[0]
        swrev = elem.getAttribute('swrev')

        freemem = int(freemem)
        totalmem = int(totalmem)

        label = self.builder.get_object('penid')
        label.props.label = penid
        label = self.builder.get_object('battery')
        label.props.label = battlevel
        label = self.builder.get_object('memory')
        label.props.label = "%dk / %dk" % ((totalmem - freemem)/1024,
                totalmem / 1024)
        label = self.builder.get_object('version')
        label.props.label = swrev

        dlg = self.builder.get_object('infowin')
        dlg.run()
        dlg.hide()

    def about(self, *args):
        dlg = self.builder.get_object('aboutwin')
        dlg.run()
        dlg.hide()

    def quit(self, *args):
        if self.connected is True:
            self.pen.disconnect()
        gtk.main_quit()

    def __init__(self):
        builder = gtk.Builder()
        builder.add_from_file("smartpen-browser.glade")
        self.builder = builder
        self.connected = False

        cbs = {
                'on_connect_clicked': self.pen_connect,
                'on_disconnect_clicked': self.pen_disconnect,
                'on_info_clicked': self.pen_info,
                'on_quit_clicked': self.quit,
        }
        builder.connect_signals(cbs)

        pen = pysmartpen.Smartpen()
        self.pen = pen

        window = builder.get_object("window1")
        self.window = window
        window.connect('delete-event', self.quit)
        window.set_size_request(640, 480)
        window.show_all()

        mi = builder.get_object("about-mi")
        mi.connect('activate', self.about)

if __name__ == "__main__":
    x = SmartpenBrowser()
    gtk.main()
