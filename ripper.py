import md5
import re
import urllib2
import binascii
from Crypto.Cipher import ARC4
import sys
import os
import urllib

# Used http://blog.dieweltistgarnichtso.net/sinnlose-verschlusselung-bei-myvideo-de
# to understand how to download MyVideo.de videos.

def fetch(url):
  u = urllib2.urlopen(urllib2.Request(url))
  contents = u.read()
  u.close()
  return contents

def parse_url(url):
  components = re.findall(r'myvideo\.de/watch/(\d+)/([a-zA-Z0-9_-]+)$', url)
  if len(components) != 1 or len(components[0]) != 2:
    raise Exception('Bad video URL: %s' % url)

  vid, vname = components[0]
  if not vid.isdigit():
    raise Exception('%s has non-digit characters' % vid)
  vname = os.path.basename(vname)

  return (vid, vname)

def decrypt_payload(vid, master_key, encrypted_payload):
  decrypt_key = md5.new(master_key + md5.new(vid).hexdigest()).hexdigest()
  decrypter = ARC4.new(decrypt_key)
  encrypted_payload = binascii.unhexlify(encrypted_payload)
  return decrypter.decrypt(encrypted_payload)

def fetch_encrypted_payload(vid):
  payload_url = 'http://www.myvideo.de/dynamic/get_player_video_xml.php?autorun=yes&flash_playertype=D' + \
    '&ID=%s&ds=1&_countlimit=4&domain=www.myvideo.de' % vid
  return fetch(payload_url)

def find_video_url(xmldoc):
  parts = re.findall(r"path='([^']+?)' source='([^']+?)'", xmldoc)[0]
  url = urllib.unquote_plus(parts[0] + parts[1])
  return url

def fetch_video(vurl, vid, vname):
  vid_data = fetch(vurl)
  filename = '%s-%s.flv' % (vname, vid)
  with open(filename, 'wb') as vfile:
    vfile.write(vid_data)

def download_video(url):
  vid, vname = parse_url(url)

  # Master key found via:
  #   curl -s 'http://is5.myvideo.de/de/player/mingR13p/ming.swf' | tail -c +9 | openssl zlib -d | strings | grep MASTER_KEY
  # ming.swf URL was found by loading video in Chrome, then browsing through
  # resources loaded by page.
  master_key = 'c8407a08b3c71ea418ec9dc662f2a56e40cbd6d5a114aa50fb1e1079e17f2b83'

  payload = fetch_encrypted_payload(vid)
  # Strip leading '_encxml='.
  payload = payload[8:].strip()
  decrypted = decrypt_payload(vid, master_key, payload)

  vurl = find_video_url(decrypted)
  fetch_video(vurl, vid, vname)

def main():
  for line in sys.stdin:
    line = line.strip()
    if not line or line.startswith('#'):
      continue
    print('Downloading %s' % line)
    download_video(line)

main()
