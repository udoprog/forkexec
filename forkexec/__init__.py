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
import time
import uuid
import subprocess
import stat

try:
    import setproctitle
except ImportError, e:
    print( str(e) )
    print( "Please install setproctitle using:" )
    print( "    easy_install setproctitle" )
    print( "or other applicable method" )
    sys.exit(1);

import forkexec.main as m

RUN="run"
LOGS="logs"
INIT="init"

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
                print( "Creating run directory:", self.run() )
                os.mkdir(self.run());
        except OSError, e:
            raise ForkExecException("%s: %s"%(self.run(), str(e)));
        
        try:
            if not os.path.isdir(self.inits()):
                print( "Creating init directory:", self.inits() )
                os.mkdir(self.inits());
        except OSError, e:
            raise ForkExecException("%s: %s"%(self.inits(), str(e)));
        
        try:
            if not os.path.isdir(self.logs()):
                print( "Creating logs directory:", self.logs() )
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
    
    def isinit(self, id):
        path = self.inits( id );
        
        if not os.path.isfile( path ):
            return False;
        
        return True;

    def isrun(self, id):
        return self.isrun_p( self.run(id) );
    
    def isrun_p(self, path):
        if not os.path.exists( path ):
            return False;
        
        return stat.S_ISFIFO( os.stat(path).st_mode );
    
    def open_log(self, logname):
        path = self.logs(logname);
        
        try:
            return open(path, "a");
        except OSError, e:
            raise ForkExecException("%s: %s"%(path, str(e)));
    
    def open_fifo(self, fifoname, mode="r"):
        """
        Open the main fifo for this monitor.
        """
        
        path = self.run( fifoname );
        
        if not self.isrun_p( path ):
            return None;
        
        try:
            return open( path, mode );
        except OSError, e:
            return None;
    
    def validate_fifo(self, fifoname):
        path = self.run(fifoname);
        
        try:
            if not os.path.exists(path):
                os.mkfifo(path);
            
            if not self.isrun_p(path):
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
            
            if self.exists(path_from):
                os.symlink(path_from, path);

    def _delete_run(self, id):
        """
        Delete a specific fifo in the home directory.
        """
        os.unlink(self.run(id));

    def delete_alias(self, alias):
        """
        Delete a specific 'alias' in the home directory.
        """
        if not alias:
            return;
        
        if self.exists(alias):
            self._delete_run(alias);
            return True;
    
    def exists(self, id):
        path = self.run(id);
        return os.path.exists(path) or os.path.islink(path);
    
    def clean(self, id):
        if self.exists(id):
            self._delete_run(id);
            return True;
        
        return False;

    def select_runs(self, id_hint=None):
        """
        Select a subset of run entries from directory, if any starts with id_hint.
        If there is a perfect match, only return that one no matter what.
        """
        if not id_hint:
            return os.listdir(self.run());
        
        result = list();
        
        for f in os.listdir(self.run()):
            if f == id_hint:
                return [f];
        
            if f.startswith(id_hint):
                result.append(f);
        
        return result;

def main():
    home = os.environ.get("FE_HOME", None);
    p = m.ConsolePrinter();
    
    if not home:
        p.error( "You must set environment variable 'FE_HOME' before you can use forkexec" )
        sys.exit(1);
    
    # reverse and copy the arguments for simpler handling.
    args = list(sys.argv[1:]);
    args.reverse();
    
    if len(args) > 0:
        command = args.pop().lower();
    else:
        command = None;
    
    try:
        h = HomeDir(home);
    except ForkExecException, e:
        print( str(e) )
        sys.exit(1);

    for k, aliases in m.NAMES.items():
        if command in aliases:
            return m.COMMANDS[k](p, h, args);
    
    m.print_help(p);
    return 1;
