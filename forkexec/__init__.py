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
from forkexec.workdir import WorkDir

MAXFD=1024

class ForkExecException(Exception):
    pass;

def main():
    FE_HOME = os.environ.get("FE_HOME", None);
    p = m.ConsolePrinter();
    
    if not FE_HOME:
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
        h = WorkDir( FE_HOME, p );
    except ForkExecException, e:
        print( str(e) )
        sys.exit(1);
    
    # try to match command with alias.
    for k, aliases in m.NAMES.items():
        if command in aliases:
            return m.COMMANDS[k]( p, h, args );
    
    m.print_help( p );
    return 1;
