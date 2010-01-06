import os;
import uuid;
import stat;

class Session:
    IN_SUFFIX = "-in";
    OUT_SUFFIX = "-out";
    
    CLIENT = 1;
    MONITOR = 2;
    
    def __init__( self, home, id=None ):
        self.home = home;
        
        if id:
            self.role = self.CLIENT;
            self.id = id;
        else:
            self.role = self.MONITOR;
            self.id = str( uuid.uuid1() );
        
        self.state_file = self.home.get_state( self.id );
        self.fifo_in = self.home.get_fifo( self.id + self.IN_SUFFIX );
        self.fifo_out = self.home.get_fifo( self.id + self.OUT_SUFFIX );
    
    def create( self ):
        if self.state_file.exists():
            return False;
        
        if self.fifo_in.exists():
            return False;
        
        if self.fifo_out.exists():
            return False;
        
        try:
          self.state_file.create();
          self.fifo_in.create();
          self.fifo_out.create();
        except Exception, e:
          self.state_file.destroy();
          self.fifo_in.destroy();
          self.fifo_out.destroy();
          raise e;
    
    def destroy( self ):
        self.fifo_in.destroy();
        self.fifo_out.destroy();
        self.state_file.destroy();
    
    def send( self, message ):
        """
        Determine which channel to send through depending on role.
        """
        if self.role == self.CLIENT:
            return self.send_in( message );
        elif self.role == self.MONITOR:
            return self.send_out( message );
    
    def recv( self ):
        """
        Determine which channel to send through depending on role.
        """
        if self.role == self.CLIENT:
            return self.recv_out();
        elif self.role == self.MONITOR:
            return self.recv_in();
        
        raise Exception("Invalid Role");
    
    def send_in( self, message ):
        # this is blocking until a consumer is available
        f = self.fifo_in.open( "w" );
        
        if not f:
            return False;
        
        try:
            f.write( message );
        finally:
            f.close();
        
        return True;
    
    def recv_in( self ):
        # this is blocking until a producer is available
        f = self.fifo_in.open( "r" );
        
        if not f:
            return None;
        
        try:
            return f.read();
        finally:
            f.close();
    
    def send_out( self, message ):
        # this is blocking until a consumer is available
        f = self.fifo_out.open( "w" );
        
        if not f:
            return False;
        
        try:
            f.write( message );
        finally:
            f.close();
        
        return True;

    def recv_out( self ):
        # this is blocking until a producer is available
        f = self.fifo_out.open( "r" );

        if not f:
            return None;
        
        try:
            return f.read();
        finally:
            f.close();

class File:
    def __init__( self, path ):
        self.path = path;
    
    def valid( self ):
        """
        Check that the path exists and is an actual fifo.
        """
        return self.exists();
    
    def exists( self ):
        return os.path.exists( self.path );

    def islink( self ):
        return os.path.islink( self.path );

    def readlink( self ):
        return os.readlink( self.path );
    
    def create( self ):
        open( self.path, "w" ).close();
    
    def destroy( self ):
        if self.exists():
            os.unlink( self.path );
    
    def open( self, mode ):
        """
        Validate that the fifo already exists.

        Returns None if unable to verify existing fifo prior to opening.
        """
        
        if not self.exists():
            return None;
        
        return open( self.path, mode );

class Fifo(File):
    def valid( self ):
        """
        Check that the path exists and is an actual fifo.
        """
        return self.exists() and stat.S_ISFIFO( os.stat( self.path ).st_mode );
    
    def create( self ):
        os.mkfifo( self.path );

class WorkDir:
    IO="io"
    RUNNING="running"
    LOGS="logs"
    INIT="init"
    
    def __init__( self, home, printer ):
        self.home = home
        self.printer = printer;
        
        if not os.path.isdir(self.home):
            raise ForkExecException("%s: is not a directory"%(self.home))
        
        self._validate_home();
    
    def _validate_home(self):
        check = [self.IO, self.RUNNING, self.LOGS, self.INIT];

        for c in check:
            path = self.get_path( c );
            
            try:
                if not os.path.isdir( path ):
                    self.printer.info( "Creating directory:", path )
                    os.mkdir( path );
            except OSError, e:
                raise ForkExecException("%s: %s"%( path, str(e)) );
    
    def get_path( self, *parts ):
        return os.path.join( self.home, *parts );
    
    def get_fifo( self, fifoname ):
        return Fifo( self.get_path( self.IO, fifoname ) );
    
    def get_state( self, id ):
        return self.get_file( self.RUNNING, id );
    
    def get_init( self, init ):
        return self.get_file( self.INIT, init );
    
    def get_file( self, *parts ):
        return File( self.get_path( *parts ) )

    def select_file( self, dir, hint = None ):
        """
        Select a subset of entries from a directory, if any starts with hint.
        If there is a perfect match, only return that one no matter what.
        """
        result = list();
        
        dir = self.get_path( dir );
        
        for f in os.listdir( dir ):
            if not hint:
                result.append(f);
                continue;
            
            if f == hint:
                return [ f ];
            
            if f.startswith( hint ):
                result.append( f );
                continue;
        
        return result;
    
    def select_runs(self, id_hint=None):
        return self.select_file( self.RUNNING );
    
    def select_inits( self, id_hint=None ):
        return self.select_file( self.INIT );
    
    def open_log(self, logname):
        path = self.get_path(self.LOGS, logname);
        
        try:
            return open( path, "a" );
        except OSError, e:
            raise ForkExecException( "%s: %s"%( path, str(e) ) );
