"""Package the reviewed protocol source with reproducible compiler input."""
from pathlib import Path
import json,hashlib,zipfile,subprocess
root=Path(__file__).resolve().parents[2]
out=root/'website/review/protocol';out.mkdir(parents=True,exist_ok=True)
files={}
for folder,pattern in [('contracts/src','*.sol'),('contracts/vendor','*.sol'),('contracts/test','*.cjs'),('contracts/protocol','*')]:
 for p in (root/folder).rglob(pattern):
  if p.is_file():files[str(p.relative_to(root))]=p.read_bytes()
for name in ['contracts/hardhat.config.cjs','contracts/package.json','contracts/package-lock.json','website/protocol-model.js','tests/protocol-model.test.cjs','website/protocol-zip.js']:
 files[name]=(root/name).read_bytes()
files['README.md']=(root/'contracts/protocol/README.md').read_bytes()
config=json.loads(subprocess.check_output(['node','-e','const m=require("./website/protocol-model.js");process.stdout.write(JSON.stringify(m.exportConfig(m.DEFAULTS)))'],cwd=root))
files['configuration.example.json']=(json.dumps(config,indent=2)+'\n').encode()
builds=sorted((root/'contracts/artifacts/build-info').glob('*.json'),key=lambda p:p.stat().st_mtime)
sources={};build=None
for p in builds:
 build=json.loads(p.read_text());sources.update(build['input']['sources'])
for p in (root/'contracts/src').rglob('*.sol'):
 key=str(p.relative_to(root/'contracts'))
 if key not in sources or sources[key]['content']!=p.read_text():raise SystemExit('Recompile changed Solidity: '+key)
compiler={'language':'Solidity','sources':sources,'settings':build['input']['settings']}
files['compiler-input.json']=(json.dumps(compiler,indent=2)+'\n').encode()
contracts=[]
for p in sorted((root/'contracts/artifacts/src').rglob('*.json')):
 if p.name.endswith('.dbg.json'):continue
 a=json.loads(p.read_text());name=a['contractName'];files[str(p.relative_to(root))]=p.read_bytes()
 if name.startswith('Hold'):
  runtime=len(a['deployedBytecode'][2:])//2
  if runtime>24576:raise SystemExit('Runtime too large: '+name)
  contracts.append({'name':name,'runtime_bytes':runtime,'source':a['sourceName'],'abi':a['abi']})
verification=json.loads((out/'verification.json').read_text())
files['verification.json']=(json.dumps(verification,indent=2)+'\n').encode()
manifest={'version':'1.0.0-review','status':'Review source. Unregistered. No public-chain deployment.', 'upstream_commit':'8ca5554df22ad511126d8547c212fa161ecf19ee','compiler':build['solcLongVersion'],'contracts':contracts,'files':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(files.items())]}
files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
archive=root/'website/review/holdpi-protocol-review.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,data in sorted(files.items()):
  info=zipfile.ZipInfo(name,date_time=(2026,11,16,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert not any('node_modules' in p or p.endswith(('.env','.key')) for p in z.namelist())
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'README.md').write_bytes(files['README.md'])
(out/'verification.json').write_bytes(files['verification.json'])
receipt={'file':archive.name,'bytes':archive.stat().st_size,'members':len(files),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(out/'download.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
