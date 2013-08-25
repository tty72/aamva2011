aamva2011
=========

Simple Python module to parse AAMVA 2011 data (US Drivers license magnetic stripe data)

Usage - 
import aamva2011
l = aamva2011.License.from_string(<AAMVA compliant string>)
print l.values
print l.first_name
