import logging, pam

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from swat.lib.base import BaseController, render
from swat.lib.helpers import swat_messages

from pylons.i18n.translation import _

log = logging.getLogger(__name__)

class AuthenticationController(BaseController):
    """ Controller that handles the authentication component of SWAT. Uses
    repoze.who with the friendlyform plugin
    
    http://code.gustavonarea.net/repoze.who-friendlyform/
    http://docs.repoze.org/who/
    
    """
    __allow_usernames = ('root', 'ric')
    __reason = ''

    def login(self):
        """ Shows the Login Screen to the user """
        return render('/default/base/login-screen.mako')
    
    def logout(self):
        """ Sends the user to the Login screen. The unsetting of cookies is
        handled by the repoze.who middleware
        
        """
        redirect_to(controller = 'authentication', action = 'login')
        
    def authenticate(self, environ, identity):
        """ Performs the custom authentication. This method is required by
        repoze and we are sent here by it.
        
        Keyword arguments
        environ -- WSGI environment (request.environ)
        identify -- credentials entered by the user
        
        In case of sucess it returns the username of the user that attempted
        to login otherwise None
        
        TODO: Add i18n here
        BUG: Can't add i18n because for some reason the pylons imports don't
        work here. Maybe I'm using repoze.who wrong?
        
        """
        username = identity['login']
        password = identity['password']
        
        len_username = len(username)
        len_password = len(password)        
        
        if len_username == 0:
            swat_messages.add('Username cannot be empty', 'critical')
            
        if len_password == 0:
            swat_messages.add('Password cannot be empty', 'critical')

        if self.__perform_authentication(username, password, environ):
            swat_messages.add('Authentication successful!')
            log.info("login attempt sucessful by " + username)
            
            return username
        
        log.warning("failed login attempt by " + username)
        swat_messages.add('Authentication failed' + ' -- ' + self.__reason, 'critical')
        
        return None
    
    def __perform_authentication(self, username, password, environ):
        import param
        from samba import credentials
        
        auth_success = False
        
        lp = param.LoadParm()
        lp.load_default()
        
        creds = credentials.Credentials()
        creds.set_username(username)
        creds.set_password(password)
        creds.set_domain("")
        
        if "REMOTE_HOST" in environ:
            creds.set_workstation(environ['REMOTE_HOST']);
        else:
            creds.set_workstation("")
        
        # TODO: Probably not the best way to do this :)
        if "rpc" in lp.get("server services"):
            auth_success = self.__auth_rpc(lp, creds)
            log.info("using rpc authentication")
        else:
            auth_success =  self.__auth_samr(lp, creds)
            log.info("using samr authentication")
            
        return auth_success
    
    def __auth_rpc(self, lp, credentials):
        from samba.dcerpc.echo import rpcecho
        from pylons.i18n.translation import _
        
        auth_success = False

        try:
            conn = rpcecho("ncalrpc:", lp, credentials)
        except Exception, msg:
            self.__reason = msg[1]
        else:
            auth_success = True
            
        return auth_success

    def __auth_samr(self, lp, credentials):
        pass
        
    def do(self):
        """ Stub. Required by repoze.who to be the login_handler_path. I can't
        set this to login otherwise it would just send me to the login method
        
        """
        pass
