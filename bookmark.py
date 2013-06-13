#!/usr/bin/python

import cherrypy
import sqlite3
import json
import os
import urllib2
from time import time
from re import findall, DOTALL, IGNORECASE
#from cherrypy.process.plugins import Daemonizer


_cwd = os.path.abspath(os.path.dirname(__file__))
_template_dir = os.path.join(_cwd, 'templates')


class Bookmark(object):

    @cherrypy.expose
    def index(self):
        _header = self.getHeader()
        _footer = self.getFooter()
        return _header + open(os.path.join(_template_dir, 'index.html')).read() + _footer

    def getHeader(self):
        return open(os.path.join(_template_dir, 'header.html')).read()

    def getFooter(self):
        return open(os.path.join(_template_dir, 'footer.html')).read()

    @cherrypy.expose
    def tags(self, entry):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row

        _tag = entry.strip()
        if not _tag.startswith('tags:'):
            return json.dumps({})
        terms = _tag.split(':')
        if len(terms) < 2:
            return json.dumps({})
        _tags = [i.strip() for i in terms[1].split(',')]
        _cur = _dbh.cursor()
        b = '?,' * len(_tags)
        query = '(%s)' % (b.rstrip(','),)
        cmd = '''SELECT url,title,bookmark_id,date_added from bookmark,tags,bookmark_tags ''' +\
            '''where tags.id=bookmark_tags.tag_id and bookmark.id=bookmark_tags.bookmark_id ''' +\
            '''and tag_id IN (SELECT id from tags where name IN %s)''' % query
        cherrypy.log.error('query = %s' % (cmd,))
        cherrypy.log.error('params = %s' % str(tuple(_tags)))
        try:
            sth = _cur.execute(cmd, tuple(_tags))
        except Exception, e:
            cherrypy.log.error('sqlite3 cmd failed: %s' % e)
            return json.dumps({})
        b = {}
        bookmarks = []
        for i in sth.fetchall():
            if i['url'] is None:
                continue
            key = i['bookmark_id']
            b.setdefault(key, {}).update({'date_added': i['date_added'], 'title': i['title'], 'url': i['url']})

        for i in b:
            b[i].update({'tags': self.find_tags(b[i]['url'])})
            bookmarks.append(b[i])
        cherrypy.log.error('bookmarks dict is %s' % repr(bookmarks))
        return json.dumps(bookmarks)

    @cherrypy.expose
    def post(self, entry, tags, title=None):
        _url = entry.strip()
        if len(tags.strip()) < 1:
            return json.dumps({'status': 'OK', 'columns': []})

        _tags = [i.strip() for i in tags.strip().split(',') if len(i.strip()) > 1]

        if len(_tags) < 1:
            return json.dumps({'status': 'OK', 'columns': [], 'message': 'Not tags found'})

### remove bookmark first, this may be an EDIT bookmark call
        self.deleteBookmark(_url)
        _bookmark_id = self.insert_bookmark(_url, title)
        _tag_ids = self.insert_tags(_tags)
        if len(_tag_ids) < 1:
            return json.dumps({'status': 'FAILED', 'message': 'No tag specified'})

        _ids = self.insert_bookmark_tags(_bookmark_id, _tag_ids)
        return json.dumps({'status': 'OK', 'columns': _ids})

    @cherrypy.expose
    def remove(self, entry):
        self.deleteBookmark(entry.strip())

    @cherrypy.expose
    def url(self, entry):
        _san_entry = entry.strip().strip('\'"')
        return json.dumps(self.find_tags(_san_entry))

    @cherrypy.expose
    def toptags(self):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row
        _cur = _dbh.cursor()

        cmd = '''SELECT name, count(tag_id) as count from tags JOIN bookmark_tags ON ''' +\
            '''tag_id=tags.id group by name order by count desc'''
        sth = _cur.execute(cmd)
        return json.dumps([{'name': i['name'], 'count': i['count']} for i in sth.fetchall()])

    def find_tags(self, bookmark):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row
        _cur = _dbh.cursor()

        cmd = '''SELECT tags.name FROM tags,bookmark as bk,bookmark_tags as b_t ''' +\
            '''WHERE tags.id=b_t.tag_id and bk.id=b_t.bookmark_id and bk.url ="''' + bookmark + '''" and tags.id IN (SELECT tag_id FROM bookmark_tags)'''
        sth = _cur.execute(cmd)
        result = [i[0] for i in sth.fetchall()]
        cherrypy.log.error('url %s tagged with %s' % (bookmark, result))
        return result

    def insert_tags(self, names):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row
        _cur = _dbh.cursor()
        _ret = []
        for name in names:
            sth = _cur.execute('SELECT id from tags where name = ?', (name,))
            result = [i[0] for i in sth.fetchall()]
            if len(result) > 0:
                _ret.append(result[0])
                continue
            sth = _cur.execute('INSERT INTO tags values (NULL, ?)', (name,))
            _ret.append(sth.lastrowid)
        _dbh.commit()
        _cur.close()
        return _ret

    def insert_bookmark_tags(self, bookmark_ids, tag_ids):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row
        _cur = _dbh.cursor()
        _ret = []
        _ts = int(time())
        for bk_id in bookmark_ids:
            for tag_id in tag_ids:
                try:
                    sth = _cur.execute('INSERT into bookmark_tags values (NULL, ?, ?, ?)', (tag_id, bk_id, _ts))
                    cherrypy.log.error('INSERT into bookmark_tags %s, %s, %s' % (tag_id, bk_id, _ts))
                except Exception:
                    continue
                _ret.append(sth.lastrowid)

        _dbh.commit()
        _cur.close()
        return _ret

    def insert_bookmark(self, url, title):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row

        _cur = _dbh.cursor()
        cherrypy.log.error('insert_bookmark called with url %s' % url)
        sth = _cur.execute('SELECT id from bookmark where url = ?', (url,))
        result = [i[0] for i in sth.fetchall()]
        if len(result) > 1:
            cherrypy.log.error('Unexpected error in insert_bookmark. SELECT returned %d results.Expected 1 response' % len(result))
        if len(result) > 0:
            return [result[0]]
        _title = title or self.findTitle(url)
#        sth = _cur.execute('INSERT INTO bookmark VALUES (NULL, ?, ?)', (url.decode('utf-8'), _title.decode('utf-8')))
        sth = _cur.execute('INSERT INTO bookmark VALUES (NULL, ?, ?)', (url, _title))
        _dbh.commit()
        _cur.close()
        return [sth.lastrowid]

    def findTitle(self, url):

        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64)')]
        try:
            c = opener.open(url).read()
        except Exception, e:
            cherrypy.log.error('%s Exception in finding title for url %s' % (e, url))
            return url
        _title = findall(r'<title[^>]*>(.+?)</title>', c, DOTALL | IGNORECASE)
        if len(_title) == 0:
            return url
        _title = _title[0].strip()
        return _title

    def deleteBookmark(self, url):
        _dbh = sqlite3.connect(os.path.join(_cwd, 'db', 'bookmarks.db'))
        _dbh.row_factory = sqlite3.Row

        _cur = _dbh.cursor()
        cherrypy.log.error('deleting bookmark %s' % url)
        try:
            _cur.execute('pragma foreign_keys=ON')
            _cur.execute('delete from bookmark where url=?', (url,))
        except Exception, e:
            cherrypy.log.error('%s exception on deleting %s' % (e, url))
        _dbh.commit()
        _cur.close()
        _dbh.close()


def main():
    app_config = {
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(_template_dir, 'css'),
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(_template_dir, 'js'),
        },
        '/img': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(_template_dir, 'img')
        },
    }
    cherrypy.config.update({
        'server.socket_port': 8080,
        'server.socket_host': '0.0.0.0',
        'environment': 'production',
        'engine.autoreload_on': True,
        'log.error_file': '/tmp/error.log',
        'log.access_file': '/tmp/access.log',
        'tools.trailing_slash.on': True,
    })
    cherrypy.tree.mount(Bookmark(), '/', config=app_config)
    cherrypy.engine.start()
    cherrypy.server.start()

cherrypy.config.update('bookmark.conf')
#cherrypy.tree.mount(Bookmark(), '/')
#cherrypy.server.start()
#cherrypy.engine.start()
#print 'Daemonizing application ...'
#Daemonizer(cherrypy.engine).subscribe()
cherrypy.quickstart(Bookmark(), '/', config='bookmark.conf')
#main()
#if __name__ == '__main__':
