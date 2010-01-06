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
import datetime
import time

import setproctitle

from forkexec.commands import *
from forkexec.workdir import Session

import threading

class TimeoutWorker(threading.Thread):
    def __init__(self, func, *args, **kw):
        threading.Thread.__init__(self);        
        
        self.func = func;
        self.args = args;
        self.kw = kw;
        self.exception = None;
        self.exc_info = None;
        self.ret = None;
    
    def run(self):
        import sys;
        
        try:
            self.ret = self.func(*self.args, **self.kw);
        except Exception, e:
            self.exception = e;
            self.exc_info = sys.exc_info();
        
        return;

def timeout(ms, func, *args, **kw):
    w = TimeoutWorker(func, *args, **kw);
    w.start();
    w.join(ms);
    
    if w.isAlive():
        del w;
        return None;
    
    if w.exception is not None:
        raise w.exc_info[1], None, w.exc_info[2];
    
    return w.ret;

class Monitor:
    """
    Internal monitor class for handling the process state.
    """
    
    def __init__(self, home, id=None, init=None):
        self.home = home;
        
        # if id is specified, this is a client monitor.
        self.session = Session( home, id );
        self.init = init;
        
        self.sp = None;
        self.started = time.time();
        
        self.setproctitle();
        
        #self.log_fd = sys.stdout;
        self.log_fd = self.open_log();
        #sys.stdout = LogWrapper("STDOUT", self);
        #sys.stderr = LogWrapper("STDERR", self);
    
    def open_log(self):
        bestname = self.session.id;
        return self.home.open_log( "%s.log"%( bestname ) )
    
    def log(self, *items):
        d_now = str( datetime.datetime.now() );
        
        self.log_fd.write( "%s %s: %s\n"%( self.session.id, d_now, " ".join([str(i) for i in items]) ) );
        self.log_fd.flush();
    
    def run(self):
        """
        Wait for all child processes to die.
        """
        self.running = True;
        self.session.create();
        
        self.log("Monitor Running");
        
        while self.running:
            try:
                c = MonitorCommand.from_json( self.session.recv() );
                
                if not c:
                    self.log( "Got bad command:", repr(s) );
                else:
                    self._handle_reception(c);
            except Exception, e:
                import traceback
                self.log( "Exc:", traceback.format_exc() );
            
            if not self._check_process():
                self.log("Child exited with returncode:", self.sp.returncode);
                self.log("Initiating shutdown");
                self.stop();
        
        self.session.destroy();
        self.log("Monitor Shutting Down");

    def _check_process(self):
        """
        Check that process is running.
        """
        self.sp.poll();
        
        if self.sp.returncode is not None:
            return False;
        
        return True;
    
    def stop(self):
        self.sp = None;
        self.running = False;
    
    def _handle_reception(self, c):
        if not isinstance(c, MonitorCommand):
            self.log("Received Garbled message");
            return;
        
        elif isinstance(c, Touch):
            self.log("Got touch command");
            self._cmd_touch()
        
        elif isinstance(c, Info):
            self.log("Got info command");
            self._cmd_info(c)
        
        elif isinstance(c, Shutdown):
            self.log("Got command to shut down");
            self._cmd_stop(c);
        
        elif isinstance(c, Ping):
            self.log("Got ping");
            self._cmd_ping(c)
        
        elif isinstance(c, Signal):
            self.log("Got signal");
            self._cmd_signal(c)
        
        elif isinstance(c, Restart):
            self.log("Got restart");
            self._cmd_restart(c)
    
    def remove( self ):
        """
        Remove all session related stuff.
        """
        self.session.destroy();
    
    def _cmd_stop(self, command):
        if command.type == command.KILL:
            self.log("Sending kill signal");
            self.sp.kill();
        elif command.type == command.TERM:
            self.log("Sending terminate signal");
            self.sp.terminate();
        elif command.type == command.INIT:
            self.log("Running shutdown process");
            self._stop_init();
        
        self.log("Closing file descriptors to child process");
        
        self.sp.stdin.close();
        self.sp.stdout.close();
        self.sp.stderr.close();
        
        self.log("Waiting for child process to give up and die already");
        
        self.sp.wait();
    
    def _stop_init(self):
        if not self._check_process():
            self.log.info( "Process not running, cannot stop" );
            return;
        
        # start the process that shuts down the child process.
        stop_p = subprocess.Popen([self.home.get_init(self.init).path, "stop", self.sp.pid])
        # wait for process to finish (guarantee return code)
        stop_p.wait();
    
    def _cmd_info(self, c):
        if self.send( InfoResponse(self.session.id, self.sp.pid, time.time() - self.started, self.init) ):
            self.log( "Unable to send info response" );
    
    def _cmd_restart(self, c):
        self.log("Shutting down process");
        self._cmd_stop( Shutdown() )
        
        self.log("Spawning new process");
        
        if self.spawn():
            self.started = time.time();
            self.log("Process spawned");
        else:
            self.log("Failed to spawn process");
            self.stop();
    
    def _cmd_signal(self, c):
        self.log("Sending signal to process", c.signal);
        self.sp.send_signal(c.signal);
    
    def _cmd_ping(self, c):
        if self.send( Pong() ):
            self.log( "Unable to send pong" );
    
    def send( self, command, t=1 ):
        def sender(session, command):
            return session.send( command.to_json() );
        
        return timeout( t, sender, self.session, command );
    
    def receive( self, t=1 ):
        def receiver( session ):
            return MonitorCommand.from_json( session.recv() );
        
        return timeout( t, receiver, self.session );
    
    def communicate(self, command, timeout=1):
        """
        communicate creates a temporary response channel (fifo)
        that the monitor can use to return any command.
        """
        
        if self.send(command, timeout):
            return self.receive(timeout);
        
        return None;
    
    def spawn(self):
        """
        Spawn a child whereas the happy monitor will keep running having the child's pid in posession.
        """

        if not self.home.get_init( self.init ).exists():
            self.log("Init does not exist:", self.init);
            return False;
        
        self.sp = subprocess.Popen(
          [self.home.get_init(self.init).path, "start"],
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE)
        
        # poll for new returncode.
        self.sp.poll();
        
        # this means that the process is already dead.
        if self.sp.returncode != None:
            self.stop();
            return False;
        
        return True;
    
    def setproctitle(self):
        """
        set the process title for the monitor process.
        """
        setproctitle.setproctitle( "forkexec: Monitor Process (%s)"%(str(self.session.id)) );
