#!python3
import os, sys
import yaml, json
from termcolor import colored
import cherrypy
import pocket
from pprint import pprint

_app_cfg=None

def debugPrint(msg):
    if not _app_cfg['debug']:
        return
    print(colored('[DEBUG] %s'%msg, 'cyan'))

def errorDisplay(title, exception_instance):
    return '<h1 style="color: red">ERROR in %s</h1><pre>%s</pre' % (title, str(exception_instance))

def redirect(url):
	return '<script>window.location.replace("%s")</script>' % url

if len(sys.argv)==3:
    _master_rt=sys.argv[1]
    _master_at=sys.argv[2]
    _master_tokens=True
else:
    _master_tokens=False

def getSessionItemOrEmpty(name):
    if _master_tokens and name=='request_token':
        return _master_rt
    if _master_tokens and name=='access_token':
        return _master_at

    try:
        x=cherrypy.session[name]
    except:
        x=''

    return x


class PocketPlusPlus(object):
    #
    # AUTH TO POCKET
    #
    @cherrypy.expose
    def callback(self,*args):
        try:
            user_credentials = pocket.Pocket.get_credentials(consumer_key=_app_cfg['consumer_key'], code=cherrypy.session['request_token'])
        except Exception as e:
            return errorDisplay('received credentials validation', e)

        access_token = user_credentials['access_token']
        cherrypy.session['access_token']=access_token
        cherrypy.session.save()

        debugPrint('ACCESS_TOKEN=%s'%(access_token))
        
        return redirect('/')

    @cherrypy.expose    
    def login(self):
        try:
            request_token = pocket.Pocket.get_request_token(consumer_key=_app_cfg['consumer_key'], redirect_uri=_app_cfg['redirect_uri'])
        except Exception as e:
            return errorDisplay('session credentials validation', e)

        cherrypy.session['request_token']=request_token
        cherrypy.session.save()

        try:
            auth_url = pocket.Pocket.get_auth_url(code=request_token, redirect_uri=_app_cfg['redirect_uri'])
        except Exception as e:
            return errorDisplay('auth url generation', e)  

        debugPrint('REQUEST_TOKEN= %s'%(request_token))

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
        status={'authenticated': False}

        at=getSessionItemOrEmpty('access_token')
        if at!='':
            try: 
                pocket_instance = pocket.Pocket(_app_cfg['consumer_key'], at)
                resp=pocket_instance.get(state='unread',count=1)
            except pocket.AuthException:
                status={'authenticated': False}
            else:
                status={'authenticated': True}

        return status

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def articles(self):
        at=getSessionItemOrEmpty('access_token')
        pocket_instance = pocket.Pocket(_app_cfg['consumer_key'], at)
        articles=pocket_instance.get(state='unread',detail=True)[0]['list']

        return articles

    #
    # views
    #
    @cherrypy.expose
    def index(self):
        return open('index.html')

if __name__ == '__main__':
    stream = open('config.yml', 'r')
    _app_cfg = yaml.load(stream, Loader=yaml.SafeLoader)['app_cfg']

    debugPrint('Config loaded')

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
