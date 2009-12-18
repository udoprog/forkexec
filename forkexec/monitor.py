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

import sys
import os
import subprocess
import pickle
import uuid
import datetime

import setproctitle

from forkexec.commands import *

import threading
class TimeoutSender(threading.Thread):
    def __init__(self, monitor, command):
        threading.Thread.__init__(self);
        self.monitor = monitor;
        self.command = command;
        self.error = None;
    
    def run(self):
        try:
            f = self.monitor.home.open_fifo(self.monitor.id, "w");
            
            try:
                f.write(pickle.dumps(self.command));
            finally:
                f.close();
        except Exception, e:
            self.error = e;

class TimeoutReader(threading.Thread):
    def __init__(self, monitor, id):
        threading.Thread.__init__(self);
        self.monitor = monitor;
        self.result = None;
        self.error = None;
        self.id = id;
    
    def run(self):
        try:
            f = self.monitor.home.open_fifo(self.id, "r");
            
            try:
                self.result = pickle.loads(f.read());
            finally:
                f.close();
        except Exception, e:
            self.error = e;

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
        
        self.log_fd.write( "%s %s: %s\n"%( self.id, d_now, " ".join([str(i) for i in items]) ) );
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
          self.sp.kill();
          self.sp.wait();
        
        fifo = self.home.run(self.id);
        
        self.home.delete_fifo(self.id);
        
        if self.alias:
            self.home.delete_alias(self.alias);
    
    def _handle_reception(self, c):
        if not isinstance(c, MonitorCommand):
            self.log("Received Garbled message");
            return;
        
        if isinstance(c, Alias):
            self.log("Got alias command");
            self._cmd_alias(c)
        
        if isinstance(c, Touch):
            self.log("Got touch command");
            self._cmd_touch()
        
        if isinstance(c, PollPid):
            self.log("Got pid command");
            self._cmd_pollpid(c)
        
        if isinstance(c, Shutdown):
            self.log("Got command to shut down");
            self.running = False;
        
        if isinstance(c, Ping):
            self.log("Got ping");
            self._cmd_ping(c)
    
    def _cmd_alias(self, command):
        # remove old alias.
        if self.alias:
            self.home.delete_alias(self.alias);
        
        self.alias = command.alias;
        
        self.home.validate_alias(self.id, self.alias);
    
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

    def _cmd_ping(self, c):
        self.sp.poll();

        if self.sp.returncode is not None:
            self.log("Child exited with returncode:", self.sp.returncode);
            self.log("Initiating shutdown");
            self.sp = None;
            self.running = False;
        
        f = self.home.open_fifo(c.id, "w");
        
        try:
            f.write(pickle.dumps(Pong()));
        finally:
            f.close();
    
    def send(self, command, timeout=1):
        import threading;
        
        sending = TimeoutSender(self, command);
        sending.start();
        sending.join(timeout);
        
        if sending.isAlive():
            return False;
        
        if sending.error is not None:
            raise sending.error;
        
        return True;
    
    def receive(self, uid, timeout=1):
        reading = TimeoutReader(self, uid);
        reading.start();
        reading.join(timeout);
        
        if reading.isAlive():
            return None;
        
        if reading.error is not None:
            raise reading.error;
        
        return reading.result;

    def communicate(self, command, timeout=1):
        # create a temporary response channel
        if not isinstance(command, MonitorCommand):
            return None;
        
        uid = str(uuid.uuid1());
        path = self.home.run(uid)

        command.id = uid;
        
        try:
            os.mkfifo(path);
        except OSError, e:
            return None;
        
        try:
            if self.send(command, timeout):
                return self.receive(uid, timeout);
        finally:
            os.unlink(path);
        
        return None;
    
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
