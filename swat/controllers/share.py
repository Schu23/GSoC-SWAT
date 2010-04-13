#
# Share Management Controller file for SWAT
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# 
import logging
import param, shares

from formencode import variabledecode
from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from swat.lib.base import BaseController, render

from pylons.templating import render_mako_def
from pylons.i18n.translation import _
from swat.lib.helpers import ControllerConfiguration, DashboardConfiguration, \
BreadcrumbTrail, SwatMessages, ParamConfiguration, filter_list

log = logging.getLogger(__name__)

class ShareController(BaseController):
    """ Share Management controller Will handle all operations concerning
    Shares in SWAT.
    
    """
    
    __supported_backends = ('classic', 'ldb')
    __allowed = ('index', 'add', 'edit', 'add_assistant')

    def __init__(self):
        """ Initialization. Load the controller's configuration, builds the
        breadcrumb trail based on that information and load the backend
        information
        
        There are a few operations that don't require this initialization e.g.
        save, apply, cancel; they always redirect somewhere. therefore, there
        is a list of allowed operations that is checked to see if it's ok to
        load the configuration
        
        """
        me = request.environ['pylons.routes_dict']['controller']
        action = request.environ['pylons.routes_dict']['action']
        
        log.debug("Supported Backends: " + str(self.__supported_backends))
        log.debug("Controller: " + me)
        log.debug("Action: " + action)
        
        if action in self.__allowed:
            c.config = ControllerConfiguration(me, action)
            
            c.breadcrumb = BreadcrumbTrail(c.config)
            c.breadcrumb.build()
            
        c.samba_lp = param.LoadParm()
        c.samba_lp.load_default()
        
        log.debug("Configured backend is: " + c.samba_lp.get("share backend") + " so the Class Name will be " + c.samba_lp.get("share backend").title())

        if c.samba_lp.get("share backend") in self.__supported_backends:
            self.__backend = "ShareBackend" + c.samba_lp.get("share backend").title()
    
    def index(self):        
        """ Point of entry. Loads the Share List Template """
        c.current_page = int(request.params.get("page", 1))
        c.per_page =  int(request.params.get("per_page", 10))
        c.filter_name = request.params.get("filter_shares", "")
        c.share_list = []
        
        if c.samba_lp.get("share backend") in self.__supported_backends:
            backend = globals()["ShareBackend" + c.samba_lp.get("share backend").title()](c.samba_lp, {})
    
            if len(c.filter_name) > 0:
                c.share_list = filter_list(backend.get_share_list(), c.filter_name)            
                c.breadcrumb.add(_("Filtered By") + " " + c.filter_name, request.environ['pylons.routes_dict']['controller'], request.environ['pylons.routes_dict']['action'])
            else:
                c.share_list = backend.get_share_list()
        else:
            log.error("Error saving because the backend (" + c.samba_lp.get("share backend") + ") is unsupported")
            
            message = _("Your chosen backend is not yet supported")
            SwatMessages.add(message, "critical")
        
        return render('/default/derived/share.mako')
        
    def add(self):
        """ Add a New Share. Loads the Share Edition Template. It's the same as
        calling the edit template but with an empty share name
        
        """
        return self.edit('', True)
    
    def add_assistant(self):
        log.error("Not implemented")
        pass
    
    def edit(self, name, is_new=False):
        """ Edit a share. Loads the Share Edition Template.
        
        Keyword arguments:
        name -- the share name to load the information from
        
        """
        log.debug("Editing share " + name)
        log.debug("Is the Share New? " + str(is_new))
        
        backend = globals()["ShareBackend" + c.samba_lp.get("share backend").title()](c.samba_lp, {})

        if c.samba_lp.get("share backend") in self.__supported_backends:
            if name not in backend.get_share_list() and not is_new:
                log.warning("Share " + name + " doesn't exist in the chosen backend")
                SwatMessages.add(_("Can't edit a Share that doesn't exist"), "warning")
                redirect_to(controller='share', action='index')
            else:
                c.p = ParamConfiguration('share-parameters')
                c.share_name = name
    
                return render('/default/derived/edit-share.mako')
        else:
            log.error("Error saving because the backend (" + c.samba_lp.get("share backend") + ") is unsupported")
            
            message = _("Your chosen backend is not yet supported")
            SwatMessages.add(message, "critical")
            
            redirect_to(controller='share', action='index')
        
    def save(self):
        """ Save a Share. We enter here either from the 'edit' or 'add' """
        backend = None
        is_new = False
                
        if request.params.get("task", "edit") == "add":
            is_new = True
        
        log.debug("Task is: " + request.params.get("task", "edit"))    
        log.debug("Is the share we are saving new? " + str(is_new))
        
        if c.samba_lp.get("share backend") in self.__supported_backends:
            backend = globals()[self.__backend](c.samba_lp, request.params)
            stored = backend.store(is_new)
            
            if stored:
                message = _("Share Information was Saved")
                SwatMessages.add(message)
            else:
                SwatMessages.add(backend.get_error_message(), backend.get_error_type())
        else:
            log.error("Error saving because the backend (" + c.samba_lp.get("share backend") + ") is unsupported")
            
            message = _("Your chosen backend is not yet supported")
            SwatMessages.add(message, "critical")

        if request.environ['pylons.routes_dict']['action'] == "save":
            redirect_to(controller='share', action='index')
        elif stored:
            redirect_to(controller='share', action='edit', name=request.params.get("name", ""))
        elif is_new :
            redirect_to(controller='share', action='add')
        else:
            redirect_to(controller='share', action='edit', name=request.params.get("old_name", ""))

    def apply(self):
        """ Apply changes done to a Share. This action is merely an alias for
        the save action but it redirects to the Share's edit page instead.
        
        """
        self.save()
    
    def cancel(self, name=''):
        """ Cancel the current editing/addition of the current Share """
        if request.params.get("task", "edit") == "add":
            message = _("Cancelled New Share. No Share was added!")
        elif request.params.get("task", "edit") == "edit":
            message = _("Cancelled Share editing. No changes were saved!")
        
        SwatMessages.add(message, "warning")
        redirect_to(controller='share', action='index')
        
    def path(self):
        """ Returns the contents of the selected folder. Usually called via
        AJAX using the Popup that allows the user to select a path
        
        """
        path = request.params.get('path', '/')
        log.debug("We want the folders in: " + path)
        
        return render_mako_def('/default/component/popups.mako', 'select_path', \
                               current=path)
        
    def users_groups(self):
        """ Returns the HTML containing a list of the System's Users and Groups.
        Usually called via AJAX using the Popup that allows the user to select
        Users and Groups.
        
        """
        already_selected = request.params.get('as', '')
        log.debug("These are selected: " + already_selected)
        
        if len(already_selected) > 0:
            already_selected = already_selected.split(',')
        
        return render_mako_def('/default/component/popups.mako', \
                               'select_user_group', \
                               already_selected=already_selected)
        
    def remove(self, name=''):
        """ Deletes a Share from the current Backend
        
        Keyword arguments:
        name -- the name of the share to be deleted
        
        """        
        if len(name) == 0:
            name = variabledecode.variable_decode(request.params).get("name")

        if not isinstance(name, list):
            name = [name]
            
        log.info(str(len(name)) + " share names passed to the server to be deleted")
  
        if c.samba_lp.get("share backend") in self.__supported_backends:
            backend = globals()[self.__backend](c.samba_lp, {})
            
            #
            #   TODO: Handle multiple deletion errors
            #
            for n in name:
                deleted = backend.delete(n)
                log.info("Deleted " + n + " :: success: " + str(deleted))
            
            message = ""
            type = "cool"
            
            if deleted:
                message = _("Share Deleted Sucessfuly")
            else:
                message = backend.get_error_message()
                type = backend.get_error_type()
                
                log.warning(message)
            
            SwatMessages.add(message, type)
        else:
            log.error("Error removing because the backend (" + c.samba_lp.get("share backend") + ") is unsupported")
            message = _("Your chosen backend is not yet supported")
            SwatMessages.add(message, "critical")
        
        redirect_to(controller='share', action='index')
    
    def copy(self, name=''):
        """ Clones the chosen Share
        
        Keyword arguments:
        name -- the name of the share to be duplicated
        
        """
        if len(name) == 0:
            name = variabledecode.variable_decode(request.params).get("name")

        if not isinstance(name, list):
            name = [name]
            
        log.info(str(len(name)) + " share names passed to the server to be copied")
        
        if c.samba_lp.get("share backend") in self.__supported_backends:
            backend = globals()[self.__backend](c.samba_lp, {})

            #
            #   TODO: Handle multiple deletion errors
            #
            for n in name:
                copied = backend.copy(n)
                log.info("Copied " + n + " :: success: " + str(copied))
        
            message = ""
            type = "cool"
            
            if copied:
                message = _("Share Duplicated Sucessfuly")
            else:
                message = backend.get_error_message()
                type = backend.get_error_type()
                
                log.warning(message)

            SwatMessages.add(message, type)
        else:
            log.error("Error copying because the backend (" + c.samba_lp.get("share backend") + ") is unsupported")
            message = _("Your chosen backend is not yet supported")
            SwatMessages.add(message, "critical")
            
        redirect_to(controller='share', action='index')
    
    def toggle(self, name=''):
        """ Toggles a Share's state (enabled/disabled).
        
        At the moment it is disabled because I'm not sure how I can implement
        this sucessfuly.
        
        Keyword arguments:
        name -- the name of the share to be toggled
        
        """
        if c.samba_lp.get("share backend") in self.__supported_backends:
            backend = globals()[self.__backend](c.samba_lp, {'name':name})
            toggled = backend.toggle()
            
            if toggled:
                message = _("Share Toggled successfuly")
                SwatMessages.add(message)
            else:
                SwatMessages.add(backend.get_error_message(), backend.get_error_type())
        else:
            message = _("Your chosen backend is not yet supported")
            SwatMessages.add(message, "critical")
        
        redirect_to(controller='share', action='index')
        
""" ShareBackend """
class ShareBackend(object):
    """ """
    def __init__(self):
        #   Errors
        self.__error = {}
        self.__error['message'] = ""
        self.__error['type'] = "critical"

    def _clean_params(self, params):
        """ Copies all parameters starting with 'share_' in the current request
        object to a clean dictionary.
        
        All parameters submited through the form related to the share always
        use the prefix. This is so I can distinguish them from other random
        parameters that may be around.
        
        Keyword arguments:
        params -- contains the request.params object from Pylons
        
        """
        clean_params = {}
        
        for param in params:
            if param.startswith('share_'):
                value = params.get(param)
                new_param = param[6:].replace('_', ' ')

                clean_params[new_param] = value

        return clean_params
        
    def _set_share_name(self, name):
        """ Sets the current share name to the name passed as parameter. This
        is useful for situations where we want to handle multiple shares at the
        same time without instantiating the backend class.
        
        As an example it's used in the delete, 
        
        Keyword arguments
        name -- the share name
        
        """
        self._share_name = name
    
    def has_error(self):
        return len(self.__error['message']) == 0
    
    def _set_error(self, message, type='critical'):
        """ Sets the error message to indicate what has failed with the operation
        that was being done using this Backend
        
        Keyword arguments:
        message -- the error message
        type -- the type of error
        
        """
        self.__error['message'] = message
        self.__error['type'] = type

    def get_error_message(self):
        """ Gets the current error message """
        return self.__error['message']
    
    def get_error_type(self):
        """ Gets the current error type """
        return self.__error['type'] or 'critical'

""" ShareBackendLdb """
class ShareBackendLdb(ShareBackend):
    """ """
    def __init__(self, lp, params):
        super(ShareBackendLdb, self).__init__()
        
        self.__lp = lp
    
    """ """
    def get_share_list(self):
        
        import ldb
        
        return []

""" ShareBackendClassic """
class ShareBackendClassic(ShareBackend):
    """ Handles operations regarding the Classic Backend method to store share
    information. The classic method stores shares in the smb.conf file
    
    TODO move params and lp to the Base class
    
    """
    def __init__(self, lp, params):
        """ Constructor. Loads the smb.conf contents into a List to be used
        by each of the operations allowed by this backend
        
        Keyword arguments
        smbconf -- last smb.conf file loaded by the param module
        params -- request parameters passed by the share information form
        
        """
        super(ShareBackendClassic, self).__init__()
        
        self.__lp = lp
        self.__smbconf = self.__lp.configfile
        
        #   Important values
        self._share_name = params.get("name")
        self.__share_old_name = params.get("old_name")
        
        #   Cleanup names from the 'share_' form into the valid Samba name
        self.__params = self._clean_params(params)
        
        self.__smbconf_content = []
        self.__share_list = shares.SharesContainer(self.__lp)

        self.__load_smb_conf_content()
        
    def get_share_list(self):
        return self.__share_list.keys()
        
    def __share_name_exists(self, name):
        """ Checks if a Share exists in the ShareContainer object
        
        Keyword arguments:
        name -- the name of the share to check
        
        """
        if name not in self.__share_list:
            log.warning("Share " + name + " doesn't exist")
            return False
        
        return True
        
    def __load_smb_conf_content(self):
        """ Loads the smb.conf into a List using readlines()
        
        Returns a boolean value indicating if the file's content was loaded or
        not.
        
        """
        file_exists = False
        
        try:
            stream = open(self.__smbconf, 'r')
        except IOError:
            file_exists = False
        else:
            file_exists = True
            
        if file_exists:
            self.__smbconf_content = stream.readlines()
            stream.close()

        return file_exists
    
    def __section_exists(self, name):
        """ Checks if a section exists in the loaded smb.conf file. Also reloads
        the contents of the backend so we can always check against an updated
        copy without reloading LoadParm.
        
        I think it's better to reload param.LoadParm but I'll keep it like this
        for now :)
        
        Keyword arguments:
        name -- the share name
        
        Returns a Boolean value indicating if the section exists or not
        
        """
        self.__load_smb_conf_content()
        
        exists = False
        position = -1
        
        try:
            position = self.__smbconf_content.index('[' + name + ']\n')
            exists = True
        except ValueError:
            self._set_error("Share doesn't exist!", "critical")
            position = -1
        
        return exists
        
    def __get_section_position(self, name):
        """ Gets the position (in terms of line numbers) of where the section
        we are handling starts and ends.
        
        Keyword arguments
        name -- the name of the current section. normally the share name we are
        taking care of
        
        Returns a dictionary containing the start and end line numbers.
        
        """
        import re
        
        position = {}
        position['start'] = -1
        position['end'] = -1
        
        try:
            position['start'] = self.__smbconf_content.index('[' + name + ']\n')
        except ValueError:
            self._set_error("Share doesn't exist!", "critical")
            position['start'] = -1
            
            return position
        
        line_number = position['start'] + 1

        for line in self.__smbconf_content[line_number:]:
            m = re.search("\[(.+)\]", line)
            
            if m is not None:
                position['end'] = line_number - 1
                break
            
            line_number = line_number + 1
            
        if position['end'] == -1:
            position['end'] = len(self.__smbconf_content)

        return position
    
    def store(self, is_new=False, name=''):
        """ Store a Share, either from an edit or add.
        
        Breaks down the current smb.conf to find the chosen section (if editing)
        and recreates that section with the new values. Maintains comments that
        may be around that section.
        
        If we are adding a new share it's just added to the end of the file
        
        Keyword arguments:
        is_new -- indicates if it's a new share (or not)
        
        Returns a boolean value indicating if the share was stored correctly
        
        """
        if len(name) > 0:
            self._set_share_name(name)
            
        stored = False
        section = []
        
        if len(self._share_name) == 0:
            self._set_error(_("Can't create Share with an empty name"), "critical")
        else:
            if not is_new:
                
                if self.__share_name_exists(self.__share_old_name):
                    pos = self.__get_section_position(self.__share_old_name)
                    section = self.__smbconf_content[pos['start']:pos['end']]
                    
                    before = self.__smbconf_content[0:pos['start']]
                    after = self.__smbconf_content[pos['end']:]
                else:
                    #
                    #   Have to break it here to avoid "tricks" downstairs :P
                    #
                    self._set_error(_("You are trying to save a Share\
                                    that doesn't exist"), "critical")
                    return False
            else:
                before = self.__smbconf_content
                after = []
            
            new_section = self.__recreate_section(self._share_name, section)
            
            if self.__save_smbconf([before, new_section, after]):
                if self.__section_exists(self._share_name):
                    stored = True
                else:
                    self._set_error(_("Could not add/edit that Share. No idea why..."), "warning")

        return stored
    
    def delete(self, name=''):
        """ Deletes a share from the backend
        
        Returns a boolean value indicating if the Share was deleted sucessfuly
        
        """
        if len(name) > 0:
            self._set_share_name(name)
        
        deleted = False
        
        if self.__share_name_exists(self._share_name):
            pos = self.__get_section_position(self._share_name)
            
            if pos['start'] == -1:
                return deleted
    
            before = self.__smbconf_content[0:pos['start']]
            after = self.__smbconf_content[pos['end']:]
            
            if self.__save_smbconf([before, after]):
                if self.__section_exists(self._share_name):
                    self._set_error(_("Could not delete that Share.\
                                     The Share is still in the Backend.\
                                     No idea why..."), "critical")
                else:
                    deleted = True
        else:
            self._set_error(_("Can't delete a Share that doesn't exist!"), "warning")
        
        return deleted
    
    def copy(self, name=''):
        """ Copies a Share.
        
        Returns a boolean value indicating if the Share was copied sucessfuly
        
        BUG: Can't repeat the same share twice due to name conflict. If you try
        to copy 'test' once it will create 'copy of test'. If you try copy again
        it will fail because 'copy of test' already exists.
        
        """
        if len(name) > 0:
            self._set_share_name(name)

        new_name = _("copy of") + " " + self._share_name
        copied = False

        if not self.__share_name_exists(new_name):
            if self.__share_name_exists(self._share_name):
                pos = self.__get_section_position(self._share_name)
                section = self.__smbconf_content[pos['start']:pos['end']]
                
                new_section = self.__recreate_section(new_name, section)
            
                before = self.__smbconf_content[0:pos['start']]
                after = self.__smbconf_content[pos['end']:]
    
                if self.__save_smbconf([before, section, new_section, after]):
                    if self.__section_exists(new_name):
                        copied = True
                    else:
                        self._set_error(_("Could not copy that Share. No idea why..."), "warning")
            else:
                self._set_error(_("Did not duplicate Share because the original doesn't exist!"), "critical")
        
        else:
            self._set_error(_("Did not duplicate Share because the copy already exists!"), "critical")
        
        return copied
    
    def toggle(self, name=''):
        self._set_error("Toggle Not Implemented", "warning")
        return False
    
    def __recreate_section(self, name, section):
        """ Recreate the section we are editing/adding with the new values
        
        Keyword arguments:
        name -- the name of the section
        section -- split list of the smb.conf contents containing just the
        information from the chosen section. to obtain the section "coordinates"
        call self.__get_section_position(name)
        
        Returns the new section to write to the backend
        
        """
        import re
        
        if len(section) > 0 and self.__share_old_name:
            new_section = []
            new_section.append(section[0].replace(self.__share_old_name, \
                                                  name))
        else:
            new_section = ['\n[' + name + ']\n']
        
        #   Scan the current section in search for existing values. I could
        #   just dump the content of params but this will keep other things
        #   that the user might have written to the file; a comment on a param
        #   for example
        #
        for line in section[1:]:
            line_param = re.search("(.+)=(.+)", line)
            
            if line_param is not None:
                param = line_param.group(1).strip()
                value = line_param.group(2).strip()

                if param in self.__params:
                    if len(self.__params[param]) > 0:
                        line = "\t" + param + " = " + self.__params[param] + "\n"
                        del self.__params[param]
                    else:
                        line = ""
                else:
                    line = "\t" + param + " = " + value + "\n"
            
            new_section.append(line)
            
        #   Now we dump the params file.
        #   With the already handled key=>values deleted we can safely add all
        #   of the available parameters from the POST
        #
        #   TODO: Should we still write values if they are equal to the
        #   default? This would keep smb.conf cleaner.
        #
        for param, value in self.__params.items():
            if len(value) > 0:
                line = "\t" + param + " = " + value + "\n"
                new_section.append(line)

        return new_section
    
    def __save_smbconf(self, what):
        """ Saves the changes made to smb.conf
        
        Keyword arguments:
        what -- the stuff we are going to write to the backend
        
        """
        import shutil
        import os
        
        written = False
        abort = False
        stream = None
        
        try:
            stream = open(self.__smbconf + ".new", 'w')
            
            if len(what) > 0:
                
                for area in what:
                    for line in area:
                        try:
                            stream.write(line)
                        except UnicodeEncodeError, msg:
                            log.fatal("Can't write line; " + line + "; " + str(msg))
                            self._set_error(_("Could not write data into the backend.") + " -- " + str(msg), "critical")
                            abort = True
                            break
                        except Exception, msg:
                            log.fatal("Can't write line; " + line + "; " + str(msg))
                            self._set_error(_("Could not write data into the backend.") + " -- " + str(msg), "critical")
                            abort = True
                            break
                    
                    if abort:
                        break
                    
                if abort:
                    log.warning("Did not write anything to the temporary file;")
                else:
                    try:
                        shutil.move(self.__smbconf, self.__smbconf + ".old")
                        shutil.move(self.__smbconf + ".new", self.__smbconf)
                    except IOError, msg:
                        log.fatal("Can't replace old smb.conf; " + str(msg))
                        self._set_error(_("Could not replace old backend configuration with new one") + " -- " + str(msg), "critical")
                    except Exception, msg:
                        log.fatal("Can't replace old smb.conf; " + str(msg))
                        self._set_error(_("Could not replace old backend configuration with new one") + " -- " + str(msg), "critical")
                    else:
                        written = True
                    
                    try:    
                        os.remove(self.__smbconf + ".new")
                    except:
                        log.warning("could not remove temporary save file")
            else:
                log.info("Nothing to write. Won't touch smb.conf")
                self._set_error(_("Nothing to write. Won't touch smb.conf") + " -- " + str(msg), "warning")
        except IOError, msg:
            log.fatal("can't write changes to temporary file; " + str(msg))
            self._set_error(_("Can't write changes to temporay file. Writing aborted!") + " -- " + str(msg), "critical")

        return written
