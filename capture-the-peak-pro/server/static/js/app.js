// Capture the PEAK - client
function fmt(s){
  s=Math.max(0,Math.floor(s));
  const h=String(Math.floor(s/3600)).padStart(2,'0');
  const m=String(Math.floor((s%3600)/60)).padStart(2,'0');
  const x=String(s%60).padStart(2,'0');
  return h+":"+m+":"+x;
}
// ids: array of element ids to update with the countdown
function startClock(ids){
  const src=document.getElementById('clock');
  if(!src) return;
  let left=parseInt(src.getAttribute('data-left')||'0',10);
  const wrap=src;
  function tick(){
    const t=fmt(left);
    ids.forEach(id=>{const e=document.getElementById(id); if(e) e.textContent=t;});
    // warn/dead styling on the topbar clock
    wrap.classList.toggle('warn', left<=1800 && left>0);
    wrap.classList.toggle('dead', left<=0);
    if(left<=0){ // lock: reload so server freezes the board
      clearInterval(iv);
      setTimeout(()=>location.reload(), 1500);
      return;
    }
    left--;
  }
  tick();
  const iv=setInterval(tick,1000);
}

function flash(msg,ok){
  const f=document.getElementById('flash');
  if(!f) return;
  f.textContent=msg;
  f.className='flash show '+(ok?'ok':'err');
}

async function submitFlag(){
  const inp=document.getElementById('flag');
  const v=(inp.value||'').trim();
  if(!v){flash('type a flag first',false);return;}
  const btn=document.getElementById('submit'); btn.disabled=true;
  try{
    const r=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({stage:STAGE,flag:v})});
    const d=await r.json();
    if(d.ok){
      flash(d.msg+(d.win?'  ::  YOU TOOK THE SUMMIT':''),true);
      setTimeout(()=>location.reload(),900);
    }else{
      flash(d.msg||'rejected',false); btn.disabled=false;
    }
  }catch(e){flash('network error',false); btn.disabled=false;}
}

function fmt2(s){s=Math.max(0,Math.floor(s));const m=String(Math.floor(s/60)).padStart(2,'0');const x=String(s%60).padStart(2,'0');return m+':'+x;}

async function hintReq(n,tier,force){
  const r=await fetch('/api/hint',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({stage:n,tier:tier,force:!!force})});
  return r.json();
}
function showHint(tier,d){
  const box=document.getElementById('hint'+tier);
  document.getElementById('hintbody'+tier).textContent=d.text;
  box.classList.add('taken','open');
  const c=document.getElementById('cost'+tier);
  if(c) c.textContent = d.early ? 'taken · -30%' : 'taken · free';
  if(d.worth!=null){const w=document.getElementById('worth'); if(w) w.textContent=d.worth;}
}
async function toggleHint(n,tier){
  const box=document.getElementById('hint'+tier);
  const body=document.getElementById('hintbody'+tier);
  if(box.classList.contains('taken')||body.textContent.trim()){
    box.classList.toggle('open'); return;
  }
  try{
    let d=await hintReq(n,tier,false);
    if(d.ok){ showHint(tier,d); return; }
    if(d.locked){
      if(confirm('Hint '+tier+' unlocks free in '+fmt2(d.free_in||0)+'.\nReveal it NOW for -30% on this camp? This cannot be undone.')){
        d=await hintReq(n,tier,true);
        if(d.ok){ showHint(tier,d); } else { alert(d.msg||'could not open hint'); }
      }
      return;
    }
    alert(d.msg||'could not open hint');
  }catch(e){alert('network error');}
}
// per-hint free-unlock countdowns
function startHintClocks(){
  document.querySelectorAll('.hint').forEach(box=>{
    if(box.classList.contains('taken')) return;
    let left=parseInt(box.getAttribute('data-free-in')||'0',10);
    const cd=box.querySelector('.cd');
    const cost=box.querySelector('.cost');
    if(left<=0){ return; }
    if(cd) cd.textContent=fmt2(left);
    const iv=setInterval(()=>{
      left--;
      if(left<=0){ clearInterval(iv); if(cost) cost.textContent='available · free'; return; }
      if(cd) cd.textContent=fmt2(left);
    },1000);
  });
}
