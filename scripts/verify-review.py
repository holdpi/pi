"""Verify the exported review package against its source and required frontend assets."""
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'website'
checks=[]
def check(name,ok):
 if not ok:raise AssertionError(name)
 checks.append(name)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['styles.css','gate.css','brandbook.css','favicon.png']:
 check('Recovered design preserved: '+name,sha(WEB/name)==sha(ROOT/'assets/original-site'/name))
class Links(HTMLParser):
 def __init__(self):super().__init__();self.urls=[];self.ids=set();self.text=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.add(a['id'])
  for key in ['src','href']:
   if key in a:self.urls.append(a[key])
 def handle_data(self,s):self.text.append(s)
pages = ['index.html', 'docs.html', 'brandbook.html', 'protocol.html']
for name in pages:
 p=Links();p.feed((WEB/name).read_text())
 for url in p.urls:
  u=urlsplit(url)
  if u.scheme or u.netloc or u.path.startswith('data:'):continue
  if not u.path:
   # The brandbook intentionally includes nonfunctional UI mockups.
   if u.fragment and name!='brandbook.html':check(name+' anchor '+u.fragment,u.fragment in p.ids)
   continue
  route=unquote(u.path).lstrip('/') or 'index.html'
  if not Path(route).suffix:route+='.html'
  check(name+' dependency '+route,(WEB/route).is_file())
 content=' '.join(p.text)
 for old in ['Solana','EVERY 1H','85% to holders','Auto-claim. No action needed.','your_payout = pool × your_share × your_multiplier']:
  check(name+' removes legacy claim '+old,old not in content)
 check(name+' authored copy uses no long dashes',not re.search('[\u2013\u2014]',content))
for font in re.findall(r'url\([\'\"]?([^\)\'\"]+)',(WEB/'fonts.css').read_text()):check('Local font '+font,(WEB/font).is_file())
manifest=json.loads((WEB/'review/manifest.json').read_text())
for file in manifest['files']:
 check('Export hash '+file['path'],sha(WEB/file['url'].lstrip('/'))==file['sha256'])
for c in manifest['contracts']:
 check('Compiled source hash '+c['contract'],sha(ROOT/c['source'])==c['source_sha256'])
 check('EVM size '+c['contract'],c['runtime_bytes']<24576)
report=json.loads((ROOT/'outputs/contract-verification.json').read_text())
check('Full executed fork suite passed',len(report['tests'])==24 and all(t['status']=='passed' for t in report['tests']))
archive=WEB/'review/holdpi-bnb-review.zip';download=json.loads((WEB/'review/download.json').read_text());check('Download hash',sha(archive)==download['sha256'])
with zipfile.ZipFile(archive) as z:
 check('ZIP integrity',z.testzip() is None)
 for name in z.namelist():
  check('Allowlisted member '+name,'/node_modules/' not in name and not name.endswith(('.key','.env')))
  if name.endswith(('.py','.js','.mjs','.cjs','.json','.html','.md','.sol','.txt')):
   text=z.read(name).decode('utf-8','replace')
   check('No private host paths '+name,not re.search(r'/Users/[A-Za-z0-9._-]+/|/Volumes/[A-Za-z0-9._-]+/|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY',text))
vendor_root = ROOT / 'contracts/vendor'
provenance = json.loads((vendor_root / 'PROVENANCE.json').read_text())
for file in provenance['files']:
  check('Pinned vendor hash ' + file['path'], sha(vendor_root / 'openfour' / file['path']) == file['sha256'])

protocol = WEB / 'review/protocol'
download = json.loads((protocol / 'download.json').read_text())
archive = WEB / 'review' / download['file']
check('Protocol download hash and bytes', sha(archive) == download['sha256'] and archive.stat().st_size == download['bytes'])
with zipfile.ZipFile(archive) as z:
  names = z.namelist()
  check('Protocol ZIP integrity', z.testzip() is None)
  check('Protocol ZIP member count', len(names) == len(set(names)) == download['members'])
  archived_manifest = json.loads(z.read('manifest.json'))
  check('Protocol manifest matches download', archived_manifest == json.loads((protocol / 'manifest.json').read_text()))
  files = {entry['path']: entry for entry in archived_manifest['files']}
  check('Protocol manifest covers every payload', set(files) | {'manifest.json'} == set(names))
  for name, file in files.items():
    path = PurePosixPath(name)
    check('Safe protocol member ' + name, not path.is_absolute() and '..' not in path.parts and '\\' not in name)
    payload = z.read(name)
    check('Protocol member hash ' + name, len(payload) == file['bytes'] and hashlib.sha256(payload).hexdigest() == file['sha256'])
    if name.endswith('.sol') and name.startswith(('contracts/src/', 'contracts/vendor/')):
      check('Contract source matches protocol ZIP ' + name, payload == (ROOT / name).read_bytes())
  expected = json.loads(z.read('configuration.example.json'))
  audit_config = ROOT / 'audit/default-configuration.json'
  if audit_config.is_file():
    check('Audit default matches protocol ZIP', json.loads(audit_config.read_text()) == expected)

print(json.dumps({'passed_checks':len(checks),'pages':len(pages),'solidity_components':len(manifest['contracts']),'contract_tests_in_executed_report':len(report['tests']),'status':'pass'}))
