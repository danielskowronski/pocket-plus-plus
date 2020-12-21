#!python3
import os
import cherrypy
from pocket import Pocket


class PocketPlusPlus(object):
    @cherrypy.expose
    def index(self):
        return open('index.html')


if __name__ == '__main__':
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.abspath(os.getcwd())+'/static/'
        }
    }
    cherrypy.quickstart(PocketPlusPlus(), '/', conf)
