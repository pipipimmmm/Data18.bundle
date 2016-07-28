# For development purposes only, not included elsewhere.
# Fair use...

import re, string
import datetime
import unicodedata
import urllib.parse
import base64, os, urllib.request
from collections import namedtuple, defaultdict

import dateutil.parser
import unicodedata
from lxml import html

def Log(s): print(s)

def unicode(s): return s

class Datetime:
  def ParseDate(date, fmt=None):
    """
      Attempts to convert the given string into a datetime object.
      
      :type date: str
      
      :rtype: `datetime <http://docs.python.org/library/datetime.html#datetime-objects>`_
    """
    if date == None or len(date) == 0:
      return None #TODO: Should we return None or throw an exception here?
    try:
      year_only = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
      if fmt != None:
        result = datetime.datetime.strptime(date, fmt)
      elif year_only.match(date):
        result = datetime.datetime.strptime(date, "%Y-%m-%d")
      else:
        result = datetime.datetime.fromtimestamp(time.mktime(email.utils.parsedate(date)))
    except:
      result = dateutil.parser.parse(date)
    return result

class Util:
  def LevenshteinDistance(first, second):
    return levenshtein_distance(first, second)

  def LevenshteinRatio(self, first, second):
    if len(first) == 0 or len(second) == 0: return 0.0
    else: return 1 - (levenshtein_distance(first, second) / float(max(len(first), len(second))))

def clean_up_string(s):
  s = unicode(s)

  # Ands.
  s = s.replace('&', 'and')

  # Pre-process the string a bit to remove punctuation.
  s = re.sub('[' + string.punctuation + ']', '', s)
  
  # Lowercase it.
  s = s.lower()
  
  # Strip leading "the/a"
  s = re.sub('^(the|a) ', '', s)
  
  # Spaces.
  s = re.sub('[ ]+', ' ', s).strip()
    
  return s

# TODO: Attribution http://www.korokithakis.net/node/87
xrange = range
def levenshtein_distance(first, second):
  first = clean_up_string(first)
  second = clean_up_string(second)
  
  if len(first) > len(second):
    first, second = second, first
  if len(second) == 0:
    return len(first)
  first_length = len(first) + 1
  second_length = len(second) + 1
  distance_matrix = [[0] * second_length for x in range(first_length)]
  for i in range(first_length):
    distance_matrix[i][0] = i
  for j in range(second_length):
    distance_matrix[0][j]=j
  for i in xrange(1, first_length):
    for j in range(1, second_length):
      deletion = distance_matrix[i-1][j] + 1
      insertion = distance_matrix[i][j-1] + 1
      substitution = distance_matrix[i-1][j-1]
      if first[i-1] != second[j-1]:
        substitution = substitution + 1
      distance_matrix[i][j] = min(insertion, deletion, substitution)
  return distance_matrix[first_length-1][second_length-1]

class String:
  def StripDiacritics(s):
    """
      Removes diacritics from a given string.
    """
    u = unicode(s).replace(u"\u00df", u"ss").replace(u"\u1e9e", u"SS")
    nkfd_form = unicodedata.normalize('NFKD', u)
    only_ascii = nkfd_form.encode('ASCII', 'ignore')
    return only_ascii.decode('ascii')

  def URLEncode(string):
    encoded = urllib.parse.urlencode({'v':string})
    return encoded[2:]

  def Unquote(s, usePlus=False):
    """
      Replace ``%xx`` escapes by their single-character equivalent. If *usePlus* is ``True``,
      plus characters are replaced with spaces.
    """
    if usePlus:
      return urllib.parse.unquote_plus(s)
    else:
      return urllib.parse.unquote(s)

def request_html(url):
    Log("requesting URL: %s" % url)

    fhash = base64.urlsafe_b64encode(url.encode('ascii')).decode('utf-8')
    fname = './.cache/%s.html' % fhash
    os.makedirs(os.path.dirname(fname), exist_ok=True)

    try:
        with open(fname, 'r') as f: data = f.read()
    except:
        data = None

    if data:
        Log("Reading from cache: %s" % fname)
    else:
        Log("Writing to cache: %s" % fname)
        data = urllib.request.urlopen(url).read()
        with open(fname, 'w') as f: f.write(data.decode('utf-8'))

    return html.document_fromstring(data)

MetadataSearchResult = namedtuple('MetadataSearchResult', ['id', 'name', 'score', 'lang', 'thumb'])

AG_AG  = namedtuple('AG_AG', ['Movies'])
Agent  = AG_AG(Movies = object)

L_Lan  = namedtuple('L_Lan', ['English'])
L_Loc  = namedtuple('L_Loc', ['Language'])
Locale = L_Loc(Language = L_Lan(English = object()))

CACHE_1DAY  = 3600 * 24
CACHE_1WEEK = CACHE_1DAY * 7

Prefs = defaultdict(lambda: None)

def parallelize(f):
    def decorated(*args, **kwargs): return f(*args, **kwargs)
    return decorated

def task(f):
    def decorated(*args, **kwargs): return f(*args, **kwargs)
    return decorated

TrailerObject = namedtuple('TrailerObject', ['url', 'thumb', 'title', 'year', 'originally_available_at'])