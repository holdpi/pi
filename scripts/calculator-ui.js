// Pure economic engine is shared with the documentation and arithmetic checks.
(() => {
  const byId = id => document.getElementById(id);
  const holdings = byId('calc-holdings'), pills = byId('calc-hold');
  if (!holdings || !pills) return;
  let cycle = '24h';
  const fmt = n => n.toLocaleString('en-US',{maximumFractionDigits:6}) + ' BNB';
  const set = (id, value) => { const e=byId(id); if(e) e.textContent=value; };
  const recalc = () => {
    const p = PIEconomics.calculate({
      holdings:holdings.value,
      days:pills.querySelector('.is-on')?.dataset.days || 0,
      volume:byId('calc-vol').value,
      buyFraction:byId('calc-buys').value/100,
      averageSellBps:byId('calc-average-sell').value*100,
      otherWeight:byId('calc-other-weight').value,
      conversionLoss:byId('calc-conversion').value/100
    });
    const divisor = cycle === '15m' ? 96 : 1;
    set('out-time',p.days+'d'); set('out-mult','×'+p.weight.toFixed(1));
    set('out-selltax',(p.sellBps/100).toFixed(2)+'%');
    set('out-share',(p.share*100).toFixed(4)+'%');
    set('out-pool-label',cycle==='15m'?'HOLDER_POOL / ROUND':'HOLDER_POOL / DAY');
    set('out-pay-label',cycle==='15m'?'YOUR_SHARE / ROUND':'YOUR_SHARE / DAY');
    set('out-pool',fmt(p.holderPool/divisor)); set('out-pay',fmt(p.payout/divisor));
    set('out-weekly',fmt(p.buyback)); set('out-monthly',fmt(p.liquidity));
    set('out-year',fmt(p.operations));
  };
  for (const group of [pills,byId('calc-cycle')]) group.addEventListener('click',e=>{
    const button=e.target.closest('button'); if(!button) return;
    group.querySelectorAll('button').forEach(b=>{b.classList.remove('is-on');b.setAttribute('aria-pressed','false');});
    button.classList.add('is-on');button.setAttribute('aria-pressed','true');
    if(group.id==='calc-cycle') cycle=button.dataset.cycle;
    recalc();
  });
  for (const id of ['calc-holdings','calc-vol','calc-buys','calc-average-sell','calc-other-weight','calc-conversion'])
    byId(id).addEventListener('input',recalc);
  recalc();
})();
