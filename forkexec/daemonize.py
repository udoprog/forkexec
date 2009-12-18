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
# Daemonize code based on:
# http://code.activestate.com/recipes/278731/
# written by Chad J. Schroeder
#

import sys
import os
import uuid
import pickle

class ChildState(object):
    """
    This handles the state passed on to the parent (or childless ; )) process.
    
    As soon as this state is passed to the parent the child will detach itself.
    """
    def __init__(self, id, pid):
        self.id = id;
        self.pid = pid;

class Daemon:
    def __init__(self, home, args, daemonize=True):
        self.home = home;
        self.args = args;
        self.parent = False;
        self.state = None;
        self.daemonize = daemonize;
        self.id = None;
    
    def start(self):
        self.id = str(uuid.uuid1());
        
        if self.daemonize:
            self.createDaemon(self.home);
            
            if self.parent:
                return self.state;
        
        self.run();
    
    def createDaemon(self, home):
        pr, pw = os.pipe();
        
        p=os.fork()
        
        if p != 0:
            os.close(pw);
            
            fr = os.fdopen(pr, "r");
            self.state = pickle.loads(fr.read());
            self.parent = True;
            fr.close();
            os.wait();
            return;
        
        os.close(pr);
        
        os.setsid();

        p = os.fork();

        if p != 0:
            sys.exit(0);
        
        # report the current pid to the parent process.
        fw = os.fdopen(pw, "w");
        self.state = ChildState(self.id, os.getpid())
        
        fw.write(pickle.dumps(self.state));
        fw.close();
        
        import resource
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        
        if (maxfd == resource.RLIM_INFINITY):
           maxfd = MAXFD
        
        # Iterate through and close all file descriptors.
        for fd in range(0, maxfd):
          try:
             os.close(fd)
          except OSError:
             pass
    
    def run(self):
        sys.exit(100);
