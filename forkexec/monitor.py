#
#    This file is part of forkexec
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# author: John-John Tedro <johnjohn.tedro@gmail.com>
#

import os
import setproctitle
import subprocess
import datetime;
import pickle

from forkexec.commands import *

class Monitor:
    """
    Internal monitor class for handling the process state.
    """
    
    def __init__(self, home, id, init=None, alias=None):
        self.pid = None;
        
        self.home = home;
        self.id = id;
        self.alias = alias;
        self.init = init;
        
        self.sp = None;
        
        self.setproctitle();
        
        self.log_fd = self.open_log();

    def open_log(self):
        bestname = self.id;
        
        if self.alias:
            bestname = self.alias;
        
        return self.home.open_log( "%s.log"%( bestname ) )
    
    def log(self, *items):
        d_now = str( datetime.datetime.now() );
        
        self.log_fd.write( "%s %s: %s\n"%( self.id, d_now, " ".join(items) ) );
        self.log_fd.flush();
    
    def run(self):
        """
        Wait for all child processes to die.
        """
        self.running = True;
        self._prepare_channels();

        self.log("Monitor Running");

        while self.running:
            f = self.home.open_fifo(self.id, "r");
            
            try:
                c = pickle.loads( f.read() );
                self._handle_reception(c);
            except Exception, e:
                self.log( "Exc:", str(e) );
            finally:
                f.close();
        
        self.log("Monitor Shutting Down");
    
    def _prepare_channels(self):
        self.home.validate_fifo(self.id);
        
        if self.alias:
            self.log("Creating alias:", self.alias);
            self.home.validate_alias(self.id, self.alias);
    
    def shutdown(self):
        if self.sp:
          self.sp.terminate();
          self.sp.wait();
        
        fifo = self.home.run(self.id);
        
        self.home.delete_fifo(self.id);

        if self.alias:
            self.home.delete_alias(self.alias);
    
    def _handle_reception(self, c):
        if not isinstance(c, MonitorCommand):
            self.log("Received Garbled message");
            return;
        
        if isinstance(c, Touch):
            self.log("Got touch command");
            self._cmd_touch()
        
        if isinstance(c, PollPid):
            self.log("Got pid command");
            self._cmd_pollpid(c)
        
        if isinstance(c, Shutdown):
            self.log("Got command to shut down");
            self.running = False;
    
    def _cmd_touch(self):
        import datetime
        tp = self.home.path(Touch.FILENAME)
        
        ft = open(tp, "a");
        ft.write("touched at %s by %s\n"%(datetime.datetime.now(), self.id));
        ft.close();

    def _cmd_pollpid(self, c):
        f = self.home.open_fifo(c.id, "w");
        f.write(pickle.dumps(ResponsePid(self.pid)));
        f.close();
    
    def send(self, cmd):
        f = self.home.open_fifo(self.id, "w");
        f.write(pickle.dumps(cmd));
        f.close();
    
    def spawn(self):
        """
        Spawn a child whereas the happy monitor will keep running having the child's pid in posession.
        """

        if not os.path.exists(self.home.inits(self.init)):
            self.log("Init does not exist:", self.init);
            return False;
        
        sp = subprocess.Popen(self.home.inits(self.init))
        self.pid = sp.pid;
        self.sp = sp;
        return True
    
    def setproctitle(self):
        """
        set the process title for the monitor process.
        """
        setproctitle.setproctitle( "forkexec: Monitor Process (%s)"%(str(self.id)) );
