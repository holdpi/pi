/* Developer-owned local fork only. Never a production Registry registration. */
const fs=require('node:fs');
const path=require('node:path');
const ethers=require('ethers');
async function main(){
  const [manifestFile,presetId,outputFile]=process.argv.slice(2),url=process.env.RPC_URL;
  if(!manifestFile||!presetId||!outputFile||!url)throw Error('RPC_URL=http://127.0.0.1:8545 node contracts/protocol/register-local.cjs fork-bindings.json PRESET_ID local-deployment.json');
  if(!['127.0.0.1','localhost','[::1]'].includes(new URL(url).hostname))throw Error('Only a loopback development fork is permitted.');
  const bindings=JSON.parse(fs.readFileSync(manifestFile)),provider=new ethers.JsonRpcProvider(url),chain=await provider.getNetwork();
  if(chain.chainId!==31337n)throw Error('Local chainId 31337 required.');
  const signer=await provider.getSigner(0),owner=await signer.getAddress();
  const PRESET='tuple(uint256 id,string name,string description,string version,bool active,bool createEnabled,address validator,bytes32 tokenModuleId,bytes32 vaultModuleId,bytes32 curveModuleId,bytes32 tradeModuleId,bytes32 migrateModuleId,bytes32 tokenImplId,bytes32 customDataId,address author)';
  const registry=new ethers.Contract(bindings.registry,['function owner() view returns(address)','function getPresetIds() view returns(uint256[])','function getModuleBeacon(bytes32) view returns(address)','function upsertModule(bytes32,address,uint8,tuple(bytes32 moduleId,string version,string name,string description,address author,uint16 feeShareBps),bool)','function upsertTokenImpl(bytes32,address,string)',`function upsertPreset(${PRESET})`],signer);
  if((await registry.owner()).toLowerCase()!==owner.toLowerCase())throw Error('Signer does not own this local Registry.');
  if((await registry.getPresetIds()).some(id=>id===BigInt(presetId)))throw Error('Preset ID already exists. Choose an unused ID.');
  const core=new ethers.Contract(bindings.core,['function registry() view returns(address)','function wrappedNative() view returns(address)'],provider);
  if((await core.registry()).toLowerCase()!==bindings.registry.toLowerCase())throw Error('Core and Registry do not match.');
  const quoteAsset=await core.wrappedNative();
  const router=new ethers.Contract(bindings.router,['function WETH() view returns(address)'],provider);
  if((await router.WETH()).toLowerCase()!==quoteAsset.toLowerCase())throw Error('Router wrapped native does not match.');
  const receipts=[];
  async function deploy(name,args=[]){
    const dir=name.startsWith('Hold')?'src/protocol':'src';
    const artifact=JSON.parse(fs.readFileSync(path.resolve(__dirname,`../artifacts/${dir}/${name}.sol/${name}.json`)));
    const contract=await new ethers.ContractFactory(artifact.abi,artifact.bytecode,signer).deploy(...args);await contract.waitForDeployment();receipts.push(contract.deploymentTransaction().hash);return contract;
  }
  const rewards=await deploy('HoldRewards'),treasury=await deploy('HoldTreasury'),token=await deploy('HoldToken');
  const moduleNames=['HoldTokenModule','HoldVault','HoldCurveModule','HoldTradeModule','HoldMigrateModule'],modules=[],keys=[];
  for(let i=0;i<moduleNames.length;i++){
    const contract=await deploy(moduleNames[i],i===0?[bindings.core]:[]),descriptor=await contract.descriptor(),key=ethers.keccak256(ethers.toUtf8Bytes(descriptor[1]));
    if(await registry.getModuleBeacon(key)!==ethers.ZeroAddress)throw Error('Module key exists. This script refuses to overwrite it: '+descriptor[1]);
    modules.push(contract);keys.push(key);
  }
  const validator=await deploy('HoldPresetValidator',[bindings.core,quoteAsset,bindings.router,await rewards.getAddress(),await treasury.getAddress(),presetId]);
  for(let i=0;i<modules.length;i++){
    const tx=await registry.upsertModule(keys[i],await modules[i].getAddress(),i,[keys[i],'1.0.0',moduleNames[i],'HoldPI configurable acquisition-age protocol',owner,0],true);await tx.wait();receipts.push(tx.hash);
  }
  const tokenImplId=ethers.keccak256(ethers.toUtf8Bytes('token.holdpi_configurable'));
  const ti=await registry.upsertTokenImpl(tokenImplId,await token.getAddress(),'1.0.0');await ti.wait();receipts.push(ti.hash);
  const tx=await registry.upsertPreset([presetId,'HoldPI Configurable','Per-acquisition tax decay and funded BNB rewards','1.0.0',true,true,await validator.getAddress(),...keys,tokenImplId,ethers.ZeroHash,owner]);await tx.wait();receipts.push(tx.hash);
  const result={chainId:31337,core:bindings.core,registry:bindings.registry,router:bindings.router,quoteAsset,presetId:String(presetId),caller:owner,operations:owner,rewardsImplementation:await rewards.getAddress(),treasuryImplementation:await treasury.getAddress(),validator:await validator.getAddress(),implementations:{token:await token.getAddress(),tokenModule:await modules[0].getAddress(),vault:await modules[1].getAddress(),curve:await modules[2].getAddress(),trade:await modules[3].getAddress(),migrate:await modules[4].getAddress()},requestId:String(Date.now()),validTimestamp:0,createFee:'0',signature:'',transactions:receipts};
  fs.writeFileSync(outputFile,JSON.stringify(result,null,2)+'\n');console.log('Local protocol registration written to '+path.basename(outputFile)+'. No public chain was used.');
}
if(require.main===module)main().catch(e=>{console.error(e.shortMessage||e.message);process.exitCode=1;});
