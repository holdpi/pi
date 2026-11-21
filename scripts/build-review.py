"""Export a self-contained, credential-free frontend and contract review package."""
from pathlib import Path
import hashlib, json, shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'website'; REVIEW=WEB/'review'; REVIEW.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
def export(source,destination,viewer=False):
 destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
 records.append({'path':str(source.relative_to(ROOT)),'url':'/'+str(destination.relative_to(WEB)),'sha256':sha(destination),'bytes':destination.stat().st_size,'viewer':viewer})
# Deliberate allowlist: no work directory, credentials, preview tokens or local paths.
sources=[ROOT/'contracts/src/PiToken.sol',ROOT/'contracts/src/PiRewards.sol',ROOT/'contracts/src/PiTreasury.sol']
sources+=sorted(p for p in (ROOT/'contracts/src').rglob('*.sol') if p not in sources)
sources+=sorted((ROOT/'contracts/vendor').rglob('*.sol'))
sources+=sorted((ROOT/'contracts/test').glob('*.cjs'))
sources+=[ROOT/'contracts/hardhat.config.cjs',ROOT/'README.md']
sources+=sorted((ROOT/'docs').glob('*.md'))
for p in sources:export(p,REVIEW/'source'/p.relative_to(ROOT),True)
export(ROOT/'outputs/contract-verification.json',REVIEW/'contract-verification.json')
spec_path=ROOT/'src/pi-bnb-v2-spec.json'
if not spec_path.exists():spec_path=REVIEW/'economic-spec.json'
spec=json.loads(spec_path.read_text())
for key in ['authority','before_contract_release']:spec.pop(key,None)
spec['status']='Economic specification implemented in the accompanying review contracts. No public deployment or production approval.'
spec['chain_and_asset']['supply_policy']='1 billion initial PI in this implementation, no team mint. Sale allocation and curve pricing remain launch configuration.'
spec['calibration']['reason_for_5_percent_buy']='Selected project buy tax. Higher per-unit fee receipts also create greater entry friction.'
spec['calibration'].pop('scenarios',None)
(REVIEW/'economic-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
builds=list((ROOT/'contracts/artifacts/build-info').glob('*.json'))
if not builds:raise SystemExit('Compile contracts before packaging.')
build=json.loads(max(builds,key=lambda p:p.stat().st_mtime).read_text())
(REVIEW/'compiler-input.json').write_text(json.dumps(build['input'],indent=2)+'\n')
compiled=[]
for p in sorted((ROOT/'contracts/src').glob('*.sol')):
 name=p.stem;artifact=ROOT/f'contracts/artifacts/src/{name}.sol/{name}.json'
 if not artifact.exists():raise SystemExit(f'Missing artifact: {name}')
 a=json.loads(artifact.read_text());abi=REVIEW/f'abi/{name}.json';abi.parent.mkdir(exist_ok=True);abi.write_text(json.dumps(a['abi'],indent=2)+'\n')
 compiled.append({'contract':name,'source':str(p.relative_to(ROOT)),'source_sha256':sha(p),'abi_url':'/review/abi/'+abi.name,'runtime_bytes':len(a['deployedBytecode'][2:])//2,'creation_bytecode_sha256':hashlib.sha256(bytes.fromhex(a['bytecode'][2:])).hexdigest()})
for extra in [REVIEW/'economic-spec.json', REVIEW/'compiler-input.json', *sorted((REVIEW/'abi').glob('*.json'))]:
 records.append({'path':str(extra.relative_to(ROOT)),'url':'/'+str(extra.relative_to(WEB)),'sha256':sha(extra),'bytes':extra.stat().st_size,'viewer':False})
manifest={'version':'0.2.0','status':'Review source; not independently audited or deployed','upstream_commit':'8ca5554df22ad511126d8547c212fa161ecf19ee','compiler':build['solcLongVersion'],'compiler_settings':build['input']['settings'],'files':records,'contracts':compiled}
manifest['compiler_settings'].pop('outputSelection',None)
(REVIEW/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
include=[ROOT/'README.md',ROOT/'.gitignore']
for folder in ['website','assets/original-site','contracts/src','contracts/vendor','contracts/test','tests','scripts','docs']:
 include.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and not p.is_symlink() and p.suffix not in ['.zip','.pyc'] and '__pycache__' not in p.parts and p != REVIEW/'download.json')
include.extend(ROOT/'contracts'/n for n in ['package.json','package-lock.json','hardhat.config.cjs'])
include.append(ROOT/'outputs/contract-verification.json')
archive=REVIEW/'holdpi-bnb-review.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(set(include)):z.write(p,Path('holdpi-bnb-review')/p.relative_to(ROOT))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 names=z.namelist()
 assert not any('/node_modules/' in n or n.endswith('.key') or n.endswith('.env') for n in names)
receipt={'file':'holdpi-bnb-review.zip','sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(names),'source_files':len(sources),'contracts':len(compiled)}
(REVIEW/'download.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
