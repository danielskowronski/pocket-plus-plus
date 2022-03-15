#!python3
import os
import sys
import yaml
import json
from termcolor import colored
import cherrypy
from cherrys import cherrys # replace with `import cherrys` when https://github.com/3kwa/cherrys/pull/2 is merged; aletrnatively create new pip package
import pocket
from pprint import pprint
from influxdb import InfluxDBClient

_app_cfg = None
cherrypy.lib.sessions.RedisSession = cherrys.RedisSession


def debugPrint(msg):
    if not _app_cfg['debug']:
        return
    print(colored('[DEBUG] %s' % msg, 'cyan'))


def errorDisplay(title, exception_instance):
    return '<h1 style="color: red">ERROR in %s</h1><pre>%s</pre' % (title, str(exception_instance))


def redirect(url):
    return '<script>window.location.replace("%s")</script>' % url


if len(sys.argv) == 4:
    _master_rt = sys.argv[1]
    _master_at = sys.argv[2]
    _master_un = sys.argv[3]
    _master_tokens = True
else:
    _master_tokens = False


def getSessionItemOrEmpty(name):
    if _master_tokens and name == 'request_token':
        return _master_rt
    if _master_tokens and name == 'access_token':
        return _master_at
    if _master_tokens and name == 'username':
        return _master_un

    try:
        x = cherrypy.session[name]
    except:
        x = ''

    return x


def processStatistics(articles_data):
    time = 0
    words = 0
    articles = 0

    for article in articles_data.values():
        try:
            time += int(article['time_to_read'])
        except:
            pass

        try:
            words += int(article['word_count'])
        except:
            pass

        articles += 1

    return time, words, articles


def storeStatsToInfluxDB(username, time, words, articles):
    if _influx_cfg['enabled'] != True:
        return

    debugPrint('Storing stats to InfluxDB: series=%s minutes=%d words=%d articles=%d' % (
        username, time, words, articles))

    client = InfluxDBClient(_influx_cfg['host'], _influx_cfg['port'],
                            _influx_cfg['user'], _influx_cfg['pass'], _influx_cfg['db'])
    status = client.write_points([{
        "measurement": username,
        "fields": {"minutes": time, "words": words, "articles": articles}}])
    debugPrint('Response from InfluxDB: %s' % (status))
    return True


class PocketPlusPlus(object):
    #
    # AUTH TO POCKET
    #
    @cherrypy.expose
    def callback(self, *args):
        try:
            user_credentials = pocket.Pocket.get_credentials(
                consumer_key=_app_cfg['consumer_key'], code=cherrypy.session['request_token'])
        except Exception as e:
            return errorDisplay('received credentials validation', e)

        access_token = user_credentials['access_token']
        cherrypy.session['access_token'] = access_token

        username = user_credentials['username']
        cherrypy.session['username'] = username

        cherrypy.session.save()

        debugPrint('ACCESS_TOKEN= %s' % (access_token))
        debugPrint('USERNAME= %s' % (username))

        return redirect('/')

    @cherrypy.expose
    def login(self):
        try:
            request_token = pocket.Pocket.get_request_token(
                consumer_key=_app_cfg['consumer_key'], redirect_uri=_app_cfg['redirect_uri'])
        except Exception as e:
            return errorDisplay('session credentials validation', e)

        cherrypy.session['request_token'] = request_token
        cherrypy.session.save()

        try:
            auth_url = pocket.Pocket.get_auth_url(
                code=request_token, redirect_uri=_app_cfg['redirect_uri'])
        except Exception as e:
            return errorDisplay('auth url generation', e)

        debugPrint('REQUEST_TOKEN= %s' % (request_token))

        return redirect(auth_url)

    @cherrypy.expose
    def logout(self):
        cherrypy.session.delete()
        return redirect('/')

    #
    # ajax for views
    #
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def verify(self):
        status = {'authenticated': False}

        at = getSessionItemOrEmpty('access_token')
        if at != '':
            try:
                pocket_instance = pocket.Pocket(_app_cfg['consumer_key'], at)
                resp = pocket_instance.get(state='unread', count=1)
            except pocket.AuthException:
                status = {'authenticated': False}
            else:
                status = {'authenticated': True}

        return status

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def articles(self):
        at = getSessionItemOrEmpty('access_token')
        pocket_instance = pocket.Pocket(_app_cfg['consumer_key'], at)
        articles_data = pocket_instance.get(
            state='unread', detail=True)[0]['list']

        username = getSessionItemOrEmpty('username')
        time, words, count = processStatistics(articles_data)
        storeStatsToInfluxDB(username, time, words, count)

        return articles_data

    #
    # views
    #
    @cherrypy.expose
    def index(self):
        return open('index.html')


if __name__ == '__main__':
    stream = open('config.yml', 'r')
    loadedFile = yaml.load(stream, Loader=yaml.SafeLoader)
    _app_cfg = loadedFile['app_cfg']
    _influx_cfg = loadedFile['influx_cfg']
    _redis_cfg = loadedFile['redis_cfg']
    storage_type = 'ram'
    if _redis_cfg['enabled']:
        storage_type = 'redis'

    debugPrint('Config loaded')

    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.sessions.storage_type': storage_type,
            'tools.sessions.timeout': 40320,  # time in minutes; 28 days

            'tools.sessions.host': _redis_cfg['host'],
            'tools.sessions.port': _redis_cfg['port'],
            'tools.sessions.ssl': _redis_cfg['ssl'],
            'tools.sessions.tls_skip_verify': _redis_cfg['tls_skip_verify'],

            'tools.sessions.is_sentinel': _redis_cfg['is_sentinel'],
            'tools.sessions.sentinel_pass': _redis_cfg['sentinel_pass'],
            'tools.sessions.sentinel_service': _redis_cfg['sentinel_service'],

            'tools.sessions.db': _redis_cfg['db'],
            'tools.sessions.prefix': _redis_cfg['prefix'],
            'tools.sessions.user': _redis_cfg['user'],
            'tools.sessions.password': _redis_cfg['pass'],

            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.abspath(os.getcwd())+'/static/'
        }
    }
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(PocketPlusPlus(), '/', conf)
