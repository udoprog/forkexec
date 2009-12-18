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
import pickle
import time
import uuid
import subprocess
import stat

try:
    import setproctitle
except ImportError, e:
    print str(e);
    print "Please install setproctitle using:"
    print "    easy_install setproctitle"
    print "or other applicable method"
    sys.exit(1);

from forkexec.monitor import Monitor
from forkexec.daemonize import Daemon
import forkexec.commands as commands

RUN="run"
LOGS="logs"
INIT="init"
CMD_LIST=["list", "ls"]
CMD_START=["spawn", "start", "run", "x"]
CMD_STOP=["shutdown", "stop", "s"]
CMD_CHECK=["check", "c"]
CMD_CLEAN=["clean"]
CMD_PID=["pid", "p"]
CMD_DEFAULT=CMD_LIST

MAXFD=1024

class ForkExecException(Exception):
    pass;

class HomeDir:
    def __init__(self, home):
        self.home = home

        if not os.path.isdir(self.home):
            raise ForkExecException("%s: is not a directory"%(self.home))
        
        self._validate_home();
    
    def _validate_home(self):
        try:
            if not os.path.isdir(self.run()):
                os.mkdir(self.run());
        except OSError, e:
            raise ForkExecException("%s: %s"%(self.run(), str(e)));
        
        try:
            if not os.path.isdir(self.inits()):
                os.mkdir(self.inits());
        except OSError, e:
            raise ForkExecException("%s: %s"%(self.inits(), str(e)));
        
        try:
            if not os.path.isdir(self.logs()):
                os.mkdir(self.logs());
        except OSError, e:
            raise ForkExecException("%s: %s"%(self.logs(), str(e)));
    
    def path(self, *dir):
        return os.path.join(self.home, *dir);
    
    def run(self, *parts):
        return self.path(RUN, *parts);
    
    def logs(self, *parts):
        return self.path(LOGS, *parts);
    
    def inits(self, *parts):
        return self.path(INIT, *parts);
    
    def open_log(self, logname):
        path = self.logs(logname);
        
        try:
            return open(path, "a");
        except OSError, e:
            raise ForkExecException("%s: %s"%(path, str(e)));
    
    def exec_init(self, initname):
        path = self.inits(initname);
        
        try:
            os.execv(path, [path]);
        except OSError, e:
            raise ForkExecException("%s: %s"%(path, str(e)));

    def open_fifo(self, fifoname, mode="r"):
        """
        Open the main fifo for this monitor.
        """

        path = self.run(fifoname);

        if not self._isfifo(path):
            raise ForkExecException("%s: is not a fifo"%(path));
        
        try:
            return open(path, mode);
        except OSError, e:
            raise ForkExecException("%s: %s"%(path, str(e)));

    def _isfifo(self, path):
        try:
            return stat.S_ISFIFO(os.stat(path).st_mode);
        except:
            return False;
    
    def validate_fifo(self, fifoname):
        path = self.run(fifoname);
        
        try:
            if not os.path.exists(path):
                os.mkfifo(path);
            
            if not self._isfifo(path):
                os.unlink(path);
                os.mkfifo(path);
            
        except OSError, e:
            raise ForkExecException("%s: %s"%(path, str(e)));

    def validate_alias(self, fifo, alias):
        # if alias is applicable, create run-link
        if alias:
            path_from = self.run(fifo);
            path = self.run(alias)
            
            if os.path.islink(path):
                os.unlink(path);
            
            if os.path.exists(path_from):
                os.symlink(path_from, path);

    def delete_fifo(self, fifoname):
        """
        Delete a specific fifo in the home directory.
        """
        path = self.run(fifoname);
        
        if os.path.exists(path):
            os.unlink(path);

    def delete_alias(self, alias):
        """
        Delete a specific 'alias' in the home directory.
        """
        if not alias:
            return;
        
        path = self.run(alias);
        
        if os.path.islink(path):
            os.unlink(path);
    
    def exists(self, id):
        return os.path.exists(self.run(id));
    
    def clean(self, id):
        if self.exists(id):
            self.delete_fifo(id);

class MonitorDaemon(Daemon):
    def run(self):
        import signal

        init = self.args[0];
        alias = self.args[1];
        
        self.m = Monitor(self.home, self.id, init=init, alias=alias);
        
        #signal.signal(signal.SIGHUP, self.signal_handler)

        if not self.m.spawn():
            self.m.shutdown();
            sys.exit(1);
        
        try:
            self.m.run();
        except Exception, e:
            import traceback
            self.m.log(traceback.format_exc());
        
        self.m.shutdown();
    
    #def signal_handler(self, signal, frame):
    #    self.m.shutdown();
    #    sys.exit(0);

def main():
    home = os.environ.get("FE_HOME", None);
    
    if not home:
        print "You must set environment variable 'FE_HOME' before you can use forkexec";
        sys.exit(1);

    args = list(sys.argv[1:]);
    args.reverse();
    
    if len(args) > 0:
        command = args.pop().lower();
    else:
        command = CMD_DEFAULT[0];
    
    try:
        h = HomeDir(home);
    except ForkExecException, e:
        print str(e);
        sys.exit(1);
    
    if command in CMD_START:
        cmd_start(h, args);
    elif command in CMD_STOP:
        cmd_stop(h, args);
    elif command in CMD_CHECK:
        cmd_check(h, args);
    elif command in CMD_PID:
        cmd_pid(h, args);
    elif command in CMD_LIST:
        cmd_list(h, args);
    elif command in CMD_CLEAN:
        cmd_clean(h, args);
    else:
        print "No command"
    
    sys.exit(0);

def cmd_start(h, args):
    if len(args) > 0:
        id = args.pop();
    else:
        sys.exit(1);
    
    if len(args) > 0:
        alias = args.pop();
    else:
        alias = None;

    if not os.path.isfile(h.inits(id)):
        print "%s: %s"%(h.inits(id), "does not exist, create it if you want to run the specific process")
        sys.exit(1);
    
    print "Starting:", id
    MonitorDaemon(h, [id, alias], daemonize=True).start();

def cmd_check(h, args):
    if len(args) > 0:
        id = args.pop();
    else:
        sys.exit(1);
    
    m = Monitor(h, id);
    m.send(commands.Touch());

def cmd_stop(h, args):
    i=0;
    while len(args) > 0:
        i += 1;
        id = args.pop();

        if not h.exists(id):
            print "Does not exist (ignoring):", id
            continue;
        
        print "Shutting down:", id
        m = Monitor(h, id);
        if not m.send(commands.Shutdown()):
            print "Unable to shutdown, cleaning id:", id
            h.clean(id);
    
    if i == 0:
        print "No processes stopped"

def cmd_pid(h, args):
    if len(args) > 0:
        id = args.pop();
    else:
        sys.exit(1);
    
    m = Monitor(h, id);
    r = m.communicate(commands.PollPid());
    
    if r:
        print r.pid;
    else:
        print "Unable to get pid";

def cmd_list(h, args):
    if not os.path.isdir(h.run()):
        return;
    
    i = 0;
    for f in os.listdir(h.run()):
        i += 1;
        
        path = h.run(f);
        
        if os.path.islink(path):
            print "%s -> %s"%(f, os.path.basename(os.readlink(path)))
        else:
            print f

    if i == 0:
        print "No running processes";

def cmd_clean(h, args):
    i = 0;
    for f in os.listdir(h.run()):
        i += 1;
        
        m = Monitor(h, f);
        r = m.communicate(commands.Ping());
        
        if r and isinstance(r, commands.Pong):
            print "Got Pong:", f
            continue;
        
        print "Timeout, removing:", f
        h.clean(f);
    
    if i == 0:
        print "Nothing to clean"
