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

class MonitorCommand:
    def __init__(self, id=None):
        self.id = id;

    def setid(self, id):
        self.id = id;

    def getid(self):
        return self.id;
    
    id = property(getid, setid);

class Touch(MonitorCommand):
    FILENAME="touch";

class Shutdown(MonitorCommand):
    pass;

class PollPid(MonitorCommand):
    pass;

class ResponsePid:
    def __init__(self, pid):
        self.pid = pid;

class Ping(MonitorCommand):
    pass;

class Pong:
    pass;
