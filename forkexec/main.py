from forkexec.monitor import Monitor
from forkexec.daemonize import Daemon

import forkexec.commands as commands

LIST="list"
START="start"
STOP="stop"
RESTART="restart"
CHECK="check"
CLEAN="clean"
ALIAS="alias"
INFO="info"

class ConsolePrinter:
    def info(self, *texts):
        print ' '.join([str(s) for s in texts]);

    def error(self, *texts):
        self.info(*texts);
    
    def format(self, text, *args):
        result = list();
        
        i = 0;
        l = 0;
        h = 0;
        
        for c in text:
            if c == '?':
                result.append(text[l:h]);
                if i < len(args):
                    result.append(str(args[i]));
                    i += 1;
                else:
                    result.append("<none>");
                
                l = h + 1;
            
            h += 1;
        
        result.append(text[l:h]);
        self.info(''.join(result));

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


def get_time(seconds):
    hours = None;
    minutes = None;
    
    if seconds < 120.0:
        pass;
    elif seconds < 3600.0:
        minutes = int(seconds / 60.0);
        seconds = seconds % 60;
    else:
        hours   = int(seconds / 3600.0);
        minutes = int(seconds / 60.0) % 60;
        seconds = seconds % 60;
    
    parts = list();
    
    if hours:
        if hours <= 1:
            parts.append( "%d hour"%( hours ) );
        else:
            parts.append( "%d hours"%( hours ) );
    
    if minutes:
        if minutes <= 1:
            parts.append( "%d minute"%( minutes ) );
        else:
            parts.append( "%d minutes"%( minutes ) );
    
    parts.append( "%.2f seconds"%( seconds ) );
    
    return ", ".join( parts );

def print_help(p):
    p.info( "Author: John-John Tedro <johnjohn.tedro@gmail.com>" )
    p.info( "License: GPLv3" )
    p.info( "" )
    p.info( "Usage: fex <command>" )
    p.info( "" )
    p.info( "Valid <command>s are:" )
    p.info( "    start <process> <id> [alias] - start a new process" )
    p.info( "    stop <id>                    - kill a running process" )
    p.info( "    restart <id>                 - restart a running process" )
    p.info( "    alias <id> <alias>           - set the alias of a running process" )
    p.info( "    ls                           - list running processes and their aliases" )
    p.info( "    info <id>                    - display info about a running process" )
    p.info( "" )
    p.info( "<id> can always be substituted for <alias>, if the process has any" )
    p.info( "<id> can also be just the first letters of a long id if there is only a single match" );
    p.info( "<process> must be an executable under $FE_HOME/init/<process>" )
    p.info( "" )
    p.info( "Many of the commands have shorter and/or alternative versions:" )
    p.info( "    start - x" )
    p.info( "    stop  - shutdown, s" )
    p.info( "    restart - <none>" )
    p.info( "" )
    
def c_start(p, h, args):
    import os;

    if len(args) > 0:
        id = args.pop();
    else:
        return 1;
    
    if len(args) > 0:
        alias = args.pop();
    else:
        alias = None;
    
    if not h.isinit(id):
        p.error( "" );
        p.format( "?: ?", h.inits(id), "File does not exist, create it if you want to run the specific process" );
        return 1;
    
    p.info( "Starting:", id )
    MonitorDaemon(h, [id, alias], daemonize=True).start();

def c_check(p, h, args):
    if len(args) > 0:
        id = args.pop();
    else:
        return 1;
    
    m = Monitor(h, id);
    
    if not m.send(commands.Touch()):
        p.info( "Unable to touch, cleaning id:", id )
        h.clean(id);

def c_stop(p, h, args):
    i=0;
    while len(args) > 0:
        i += 1;
        id = args.pop();

        if not h.exists(id):
            p.info( "Does not exist (ignoring):", id )
            continue;
        
        p.info( "Shutting down:", id )
        m = Monitor(h, id);
        if not m.send(commands.Shutdown(commands.Shutdown.KILL)):
            p.info( "Unable to shutdown, cleaning id:", id )
            h.clean(id);
    
    if i == 0:
        p.info( "No processes stopped" )

def c_restart(p, h, args):
    i=0;
    while len(args) > 0:
        i += 1;
        id = args.pop();

        if not h.exists(id):
            p.info( "Does not exist (ignoring):", id )
            continue;
        
        p.info( "Restarting:", id )
        m = Monitor(h, id);
        if not m.send(commands.Restart()):
            p.info( "Unable to restart, cleaning id:", id )
            h.clean(id);
    
    if i == 0:
        p.info( "No processes restarted" )

def c_info(p, h, args):
    if len(args) > 0:
        id = args.pop();
    else:
        return 1;
    
    r = h.select_runs(id);
    
    if len(r) == 0:
        p.error( "No matching run fifos" );
        return;
    
    id = r[0];
    
    m = Monitor(h, id);
    result = m.communicate(commands.Info());
    
    if result:
        p.format("init:    ?", h.inits( result.init ) );
        p.format("pid:     ?", result.pid );
        p.format("running: ?", get_time( result.started ) );
    else:
        p.info( "Unable to get info" )

def c_list(p, h, args):
    import os;

    id = None;
    
    if len(args) > 0:
        id = args.pop();
    
    r = h.select_runs(id);
    
    for f in r:
        path = h.run(f);
        
        if os.path.islink(path):
            p.format( "? -> ?", f, os.path.basename( os.readlink(path) ) )
        else:
            p.info( f )
    
    if len(r) == 0:
        p.info( "No running processes" )

def c_clean(p, h, args):
    if len(args) > 0:
        r = h.select_runs(args.pop());
    else:
        r = h.select_runs();
    
    for f in r:
        m = Monitor( h, f );
        result = m.communicate( commands.Ping() );
        
        if result and isinstance( result, commands.Pong ):
            p.info( "Got Pong:", f )
            continue;
        
        p.info( "Timeout, removing:", f )
        h.clean(f);
    
    if len(r) == 0:
        p.info( "Nothing to clean" )

def c_alias(p, h, args):
    if len(args) < 2:
        return;

    id = args.pop();
    alias = args.pop();
    
    r = h.select_runs(id);
    
    if len(r) == 0:
        p.info( "Id does not match any existing:", id )
        return;

    if len(r) != 1:
        p.info( "Id matches too many:", id )
        
        for i in r:
            p.format( "(?)?", id, i[len(id):] )
        
        return;
    
    id = r.pop();
    
    m = Monitor( h, id );
    
    if m.send(commands.Alias(alias)):
        p.info( "Alias command sent:", id )
    else:
        p.info( "Unable to set alias:", id )

COMMANDS={
  LIST: c_list,
  START: c_start,
  STOP: c_stop,
  RESTART: c_restart,
  CHECK: c_check,
  CLEAN: c_clean,
  ALIAS: c_alias,
  INFO: c_info
};
