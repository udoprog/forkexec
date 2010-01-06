from forkexec.monitor import Monitor
from forkexec.daemonize import Daemon

import forkexec.commands as commands

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
        
        self.m = Monitor( self.home, init=init );
        
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
    p.info( "    start <process> <id> - start a new process" )
    p.info( "    stop <id>            - kill a running process" )
    p.info( "    restart <id>         - restart a running process" )
    p.info( "    ls                   - list running processes" )
    p.info( "    info <id>            - display info about a running process" )
    p.info( "" )
    p.info( "<id> can also be just the first letters of a long id if there is only a single match" );
    p.info( "<process> must be an executable under $FE_HOME/init/<process>" )
    p.info( "" )
    p.info( "Many of the commands have shorter and/or alternative versions:" )
    p.info( "    start - x" )
    p.info( "    stop  - shutdown, s" )
    p.info( "    restart - <none>" )
    p.info( "" )

def match_one_running(p, h, id):
    r = h.select_runs(id);
    
    if len(r) <= 0:
        p.info( "No match:", id );
        return None;
    
    if len(r) > 1:
        p.info( "Too many matches:", id );
    
        for i in r:
            p.format( "(?)?", id, i[len(id):] )
        
        return None;
    
    return r[0];
    
def c_start(p, h, args):
    id = None;

    if len(args) > 0:
        id = args.pop();
    
    r = h.select_inits(id);
    
    if len(r) == 0:
        p.info( "No matching init files" )
        return 1;
    
    if len(r) > 1:
        if id is not None:
          p.info( "Cannot start, please match only one init file:" )
        
        for f in r:
            p.info( f );

        return 1;
    
    match = r.pop();
    
    p.info( "Starting:", match )
    MonitorDaemon(h, [match], daemonize=True).start();

def c_stop(p, h, args):
    if len(args) == 0:
        p.info( "No processes stopped" )
        return 1;
    
    while len(args) > 0:
        id = match_one_running( p, h, args.pop() );
        
        if not id:
            continue;
        
        p.info( "Shutting down:", id )
        m = Monitor(h, id);
        if not m.send(commands.Shutdown(commands.Shutdown.KILL)):
            p.info( "Unable to shutdown, cleaning id:", id )
            h.clean(id);

def c_restart(p, h, args):
    if len(args) == 0:
        p.info( "No processes restarted" )
        return 1;

    while len(args) > 0:
        id = match_one_running( p, h, args.pop() );

        if not id:
            continue;
        
        p.info( "Restarting:", id )
        m = Monitor(h, id);
        if not m.send( commands.Restart() ):
            p.info( "Unable to restart, cleaning id:", id )
            h.clean(id);
    
def c_info(p, h, args):
    if len(args) == 0:
        return 1;
    
    id = match_one_running( p, h, args.pop() );

    if not id:
        return 1;
    
    m = Monitor(h, id);
    result = m.communicate(commands.Info());
    
    if result:
        p.format("id:      ?", result.id );
        p.format("init:    ?", h.get_init( result.init ).path );
        p.format("pid:     ?", result.pid );
        p.format("running: ?", get_time( result.started ) );
    else:
        p.info( "Unable to get info" )

def c_running(p, h, args):
    import os;
    
    id = None;

    if len(args) > 0:
        id = args.pop();
    
    r = h.select_runs(id);
    
    for f in r:
        state = h.get_state(f);
        
        if os.path.islink(state.path):
            p.format( "? -> ?", f, os.path.basename( os.readlink(state.path) ) )
        else:
            p.info( f )
    
    if len(r) == 0:
        p.info( "No running processes" )

def c_init(p, h, args):
    id = None;

    if len(args) > 0:
        id = args.pop();
    
    r = h.select_inits(id);
    
    if len(r) == 0:
        p.info( "No matching init files" )
    else:
        if id is not None:
          p.info( "Matching inits:" )
        
        for f in r:
            p.info( f );

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
        m.shutdown();
    
    if len(r) == 0:
        p.info( "Nothing to clean" )

RUNNING=0x1
INIT=0x2
START=0x3
STOP=0x5
RESTART=0x6
CHECK=0x7
CLEAN=0x8
ALIAS=0x9
INFO=0xa

COMMANDS={
  RUNNING: c_running,
  INIT: c_init,
  START: c_start,
  STOP: c_stop,
  RESTART: c_restart,
  CLEAN: c_clean,
  INFO: c_info
};

NAMES={
  RUNNING: ["ls-run", "list-run"],
  INIT: ["ls-init", "list-init"],
  START: ["start"],
  STOP: ["stop"],
  RESTART: ["restart"],
  CLEAN: ["clean"],
  INFO: ["info", "nfo"]
};
