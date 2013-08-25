# Copyright 2013 Noah Davis <noah@tty72.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
"""
Simple module to parse AAMVA 2011 driver's license data
as returned from conformant magnetic stripe.

Usage:
import aamva2011
l = aamva2011.License.from_string(<ASCII string as read from stripe>)
print l.values
print l.first_name
"""

import sys
import re

class ParseError(Exception):
    pass

class License(object):
    # Regexes to parse AAMVA defined track data
    _track_re = re.compile('(?P<track1>[^\?]*\?)'
                           '(?P<track2>[^\?]*\?)'
                           '(?P<track3>[^\?]*\?)')
    _track1_std = re.compile('%(?P<state>[A-Z]{2})'
                             '(?P<city>[^\^]{0,13})\^?'
                             '(?P<name>[^\^]{0,35})\^?'
                             '(?P<address>[^\^^\?]*)\^?'
                             '\?.*')
    _track2_std = re.compile(';(?P<iin>6[0-9]{5})'
                             '(?P<dlid>[^=]{0,13})=?'
                             '(?P<expiration>[0-9]{4})'
                             '(?P<birthdate>[0-9]{8})'
                             '(?P<dlid_over>[^=]{0,5})'
                             '\?.*')
    _track3_std = re.compile('#(?P<cds_version>[0-9])'
                             '(?P<jurisdiction_version>[0-9])'
                             '(?P<postal_code>[ 0-9A-Z]{11})'
                             '(?P<class>[ 0-9A-Z]{2})'
                             '(?P<restrictions>[ 0-9A-Z]{10})'
                             '(?P<endorsements>[ 0-9A-Z]{4})'
                             '(?P<sex>[12])'
                             '(?P<height>[ 0-9]{3})'
                             '(?P<weight>[ 0-9]{3})'
                             '(?P<hair_color>[ A-Z]{3})'
                             '(?P<eye_color>[ A-Z]{3})'
                             '(?P<discretionary>.{37})'
                             '\?.*')

    def __init__(self, string):
        if string[0]=='%':
            self.parse_aamva(string)
        else:
            self.parse_string(string)

    def parse_string(self, string):
        raise NotImplemented('Cooked data input')

    def split_tracks(self, string):
        m = self._track_re.match(string)
        if not m:
            raise ParseError('Does not appear to be an AAMVA string: %s'%string)
        return m.groupdict()

    def populate_self(self, values):
        for k,v in values.items():
            setattr(self, k, v)

    def parse_aamva(self, string):
        values={}
        tracks = self.split_tracks(string)
        tm = self._track1_std.match(tracks['track1'])
        if not tm:
            raise ParseError('Could not parse track 1: %s'%tracks['track1'])
        values.update(tm.groupdict())
        tm = self._track2_std.match(tracks['track2'])
        if not tm:
            raise ParseError('Could not parse track 2: %s'%tracks['track2'])
        values.update(tm.groupdict())
        tm = self._track3_std.match(tracks['track3'])
        if not tm:
            raise ParseError('Could not parse track 3: %s'%tracks['track3'])
        values.update(tm.groupdict())
        values = self.normalize(values)
        values = self.parse_discretionary(values)
        self.populate_self(values)
        self.values = values

    def normalize(self, values):
        """ Parse out the subfields of the name field and delete the name field.
        Subclasses may do additional field clean-up here.
        values - Dictionary containing all parsed fields
        RETURN - Modified dictionary with normalized data """
        l, f, m = values['name'].rstrip('$').split('$')
        values.update({'first_name':f, 'middle_name':m, 'last_name':l})
        del values['name']
        return values

    def parse_discretionary(self, values):
        """ Stub for subclasses to parse data from discretionary field of track 3
        values - Dictionary containing all parsed fields
        RETURN - Modified dictionary with parsed data """
        return values

    @classmethod
    def from_string(cls, string):
        """ Parse a string containing combined track data in AAMVA format,
            or [FUTURE] some other defined format .
            For AAMVA strings, may return a subclass based on the value of 
            the STATE field.
        """
        if string[0]=='%':
            state = string[1:3]
            for child in cls.__subclasses__():
                try:
                    if state in child.statelist:
                        return child(string)
                except AttributeError:
                    pass
        else:
            for child in cls.__subclasses__():
                try:
                    if child.string_match.match(string):
                        return child(string)
                except AttributeError:
                    pass
        return cls(string)

class License_OH(License):
    # statelist - defines a list of states this subclass will manage.
    # Used to manage states with unique conformance to the
    # 2011 AAMVA DL/ID Card Design Standard
    statelist = ['OH']
    
    def normalize(self, values):
        """ Convert first four digits of DL/ID field to alpha pair
            as per Ohio convention """
        # Don't forget to call super
        values = super(License_OH, self).normalize(values)
        # First four digits are XXYY where XX and YY are the ordinal value
        # representing the desired letter: 01 = A, 02 = B ... 18 = R, etc...
        dlid = values['dlid']
        c1 = int(dlid[0:2])
        c2 = int(dlid[2:4])
        rem = dlid[4:]
        values['dlid'] = chr(64+c1)+chr(64+c2)+rem
        return values
        
