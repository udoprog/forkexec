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

import signal;

import json;

class MonitorCommand(object):
    attr_list = list();
    id = 0;
    
    def __init__(self, id=None):
        self.id = id;
    
    def get_attributes(self):
        h = dict();
        
        for a in self.attr_list:
            h[a] = getattr(self, a);
        
        h["__id__"] = self.id;
        h["__name__"] = self.__class__.__name__
        return h;
    
    def set_attributes(self, h):
        self.id = h.get("__id__", None);
        h.pop("__name__", None)
        
        for a in h.keys():
            setattr(self, a, h[a]);

    def to_json(self):
        return json.dumps(self.get_attributes());
    
    @classmethod
    def from_json(klass, json_s):
        h = json.loads(json_s);
        
        name = h.pop("__name__", None);
        
        if not name:
            return None;
        
        cls = None;
        
        for k in MonitorCommand.__subclasses__():
            if k.__name__ == name:
                cls = k;
                break;
        
        if not cls:
            return None;

        cls_i = cls();
        cls_i.set_attributes(h);
        return cls_i;


class Touch(MonitorCommand):
    FILENAME="touch";

class Shutdown(MonitorCommand):
    pass;

class Restart(MonitorCommand):
    pass;

class Alias(MonitorCommand):
    attr_list = ["alias"];
    
    def __init__(self, alias = None):
        self.alias = alias;

class Info(MonitorCommand):
    pass;

class InfoResponse(MonitorCommand):
    attr_list = ["pid", "started"];
    
    def __init__(self, pid = None, started = None):
        self.pid = pid;
        self.started = started;

class Signal(MonitorCommand):
    attr_list = ["signal"];
    
    SIGNALS={
        'TERM': signal.SIGTERM,
        'KILL': signal.SIGKILL,
        'HUP':  signal.SIGHUP
    };
    
    def __init__(self, signal=None):
        self.signal = signal;

class Ping(MonitorCommand):
    pass;

class Pong(MonitorCommand):
    pass;

if __name__ == "__main__":
    assert MonitorCommand.from_json(ResponsePid(1234).to_json()).pid == 1234;
    assert MonitorCommand.from_json(Alias("foo").to_json()).alias == "foo";
