const $ = id => document.getElementById(id);
let state, editing = null, method = 'invite', selected = {locations: new Set(), services: new Set()};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, body, verb = 'POST') {
  const r = await fetch('/api/' + path, body === undefined ? {} : {method: verb, headers: {'Content-Type':'application/json','X-ZZZS-Request':'1'}, body:JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok) throw Error(data.error || 'Request failed');
  return data;
}
function notice(s) { $('notice').textContent=s; $('notice').hidden=false; setTimeout(()=>$('notice').hidden=true,7000); }
const fmt = s => s ? new Date(s).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}) : 'Not yet';
async function load() {
  try {
    state = await api('state');
    $('app-version').textContent='v'+state.version.replace(/^(\d+\.\d+)\.0$/,'$1');
    const active = state.users.filter(u=>u.enabled).length;
    $('total-users').textContent=state.users.length;
    $('nav-count').textContent=state.users.length;
    $('list-count').textContent=state.users.length;
    $('active-users').textContent=`${active} active · ${state.users.length-active} paused`;
    $('total-doctors').textContent=state.catalog.total.toLocaleString();
    $('check-hour').textContent=state.settings.hour;
    $('refresh').disabled=state.checking;
    $('refresh').textContent=state.checking?'Refreshing…':'↻ Refresh data';
    const issue=state.settings.last_error || state.settings.poll_error;
    $('data-status').classList.toggle('error',!!issue);
    $('data-status').textContent=issue ? 'Attention: '+issue : `Last successful refresh: ${fmt(state.settings.last_success)} · ZZZS data: ${[...new Set(Object.values(state.dates))].join(', ') || 'Waiting for first download'}`;
    $('bot-state').textContent=state.bot_configured?(state.settings.poll_error?`Bot token saved · ${state.settings.poll_error}`:state.settings.bot_username?`Connected · @${state.settings.bot_username}`:'Bot token saved · verifying connection…'):'No Telegram bot configured';
    if(document.activeElement!==$('hour')) $('hour').value=state.settings.hour;
    renderUsers();
    $('events').innerHTML=state.events.length?state.events.map(e=>`<div class="event"><time>${esc(fmt(e.at))}</time><div><b>${esc(e.kind)}</b><p>${esc(e.message)}</p></div></div>`).join(''):'<div class="event">No activity yet.</div>';
  } catch(e) {notice(e.message);}
}
function renderUsers() {
  const q=$('search').value.toLowerCase();
  const users=state.users.filter(u=>[u.alias,u.username,u.chat_id].join(' ').toLowerCase().includes(q));
  $('empty').hidden=users.length>0;
  $('users').innerHTML=users.map(u=>{
    const f=u.filters,loc=f.locations||[],svc=f.services||[];
    const tags=[...loc.slice(0,2),...(loc.length>2?[`+${loc.length-2} locations`]:[]),...(svc.length?[`${svc.length} practice types`]:['All practice types'])];
    if(!loc.length)tags.unshift('All locations');
    return `<tr><td><div class="identity"><span class="avatar">${esc((u.alias||u.username||'TG').slice(0,2).toUpperCase())}</span><div><b>${esc(u.alias||u.username||'Telegram subscriber')}</b><small>${esc(u.username?'@'+u.username:u.chat_id)}</small></div></div></td><td><div class="pills">${tags.map(t=>`<span class="pill">${esc(t)}</span>`).join('')}</div></td><td><span class="count">${u.matches}</span><span class="cell-small">matching doctors</span></td><td><span class="status ${u.enabled?'':'paused'}">${u.enabled?'● Active':'Ⅱ Paused'}</span><span class="cell-small">${u.mode==='daily'?'Daily summary':'Changes only'}</span><span class="cell-small">Last sent: ${esc(fmt(u.last_sent))}</span>${u.status?.startsWith('Telegram')?`<span class="cell-small">${esc(u.status)}</span>`:''}</td><td><button class="edit" data-id="${esc(u.chat_id)}">Manage</button></td></tr>`;
  }).join('');
  $('users').querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>openEditor(state.users.find(u=>u.chat_id===b.dataset.id)));
}
function setMethod(m) {
  method=m;
  $('join-method').querySelectorAll('button').forEach(b=>b.classList.toggle('selected',b.dataset.method===m));
  $('chat-field').hidden=m!=='manual'; $('invite-help').hidden=m!=='invite';
  $('save').textContent=editing?'Save changes':m==='invite'?'Create invitation':'Add subscriber';
}
function openEditor(u) {
  editing=u||null; $('user-form').reset(); $('dialog-error').textContent=''; $('dialog-feedback').textContent=''; $('preview').replaceChildren(); $('invite-result').hidden=true; $('copy').textContent='Copy link';
  $('editor-title').textContent=u?'Manage subscriber':'Add subscriber';
  $('alias').value=u?.alias||''; $('chat-id').value=u?.chat_id||''; $('chat-id').readOnly=!!u;
  $('mode').value=u?.mode||'changes'; $('enabled').checked=u?!!u.enabled:true;
  $('accepting').checked=u?.filters.accepting_only!==false;
  const f=u?.filters||{};
  selected={locations:new Set(f.locations||[]),services:new Set(f.services||[])};
  [...$('sources').options].forEach(o=>o.selected=(f.sources||[]).includes(o.value));
  $('location-search').value=''; $('service-search').value='';
  $('join-method').hidden=!!u; $('delete').hidden=!u;
  $('send-now').hidden=!u; $('send-help').hidden=!u;
  $('test-notification-area').hidden=!u;
  setMethod(u?'manual':'invite'); checklist('locations'); checklist('services'); $('editor').showModal();
}
function checklist(key) {
  const query=$(key==='locations'?'location-search':'service-search').value.toLowerCase();
  const values=[...new Set([...(state.catalog[key]||[]),...selected[key]])].sort();
  $(key).innerHTML=values.filter(s=>s.toLowerCase().includes(query)).map(s=>`<label><input type="checkbox" value="${esc(s)}" ${selected[key].has(s)?'checked':''}>${esc(s)}</label>`).join('')||'<p class="help">No options found. Refresh the source data first.</p>';
  $(key).querySelectorAll('input').forEach(i=>i.onchange=()=>i.checked?selected[key].add(i.value):selected[key].delete(i.value));
}
function filters() { return {locations:[...selected.locations],services:[...selected.services],sources:[...$('sources').selectedOptions].map(o=>o.value),accepting_only:$('accepting').checked}; }
$('add').onclick=()=>openEditor();
$('search').oninput=()=>state&&renderUsers();
$('location-search').oninput=()=>checklist('locations');
$('service-search').oninput=()=>checklist('services');
document.querySelectorAll('.close').forEach(b=>b.onclick=()=>$('editor').close());
$('join-method').querySelectorAll('button').forEach(b=>b.onclick=()=>setMethod(b.dataset.method));
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.tab').forEach(t=>t.hidden=t.id!==b.dataset.tab);
  document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n===b));
  $('crumb').textContent=b.dataset.tab[0].toUpperCase()+b.dataset.tab.slice(1);
});
$('user-form').onsubmit=async e=>{
  e.preventDefault(); $('save').disabled=true; $('dialog-error').textContent='';
  try {
    const b={alias:$('alias').value,chat_id:$('chat-id').value,filters:filters(),mode:$('mode').value,enabled:$('enabled').checked};
    if(!editing&&method==='invite'){
      const r=await api('invites',b); $('invite-url').value=r.url; $('invite-result').hidden=false; $('copy').textContent='Copy link'; $('save').textContent='Create another invitation';
      $('invite-heading').focus({preventScroll:true});
      $('invite-result').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
    }else{await api('users',b); $('editor').close();notice('Subscriber saved. Filter changes start with a fresh baseline.');await load();}
  }catch(e){$('dialog-error').textContent=e.message;}finally{$('save').disabled=false;}
};
$('send-now').onclick=async()=>{
  if(!editing||!$('user-form').reportValidity())return;
  $('send-now').disabled=true; $('send-test').disabled=true; $('save').disabled=true; $('delete').disabled=true;
  $('send-now').textContent='Sending…'; $('dialog-error').textContent=''; $('dialog-feedback').textContent='';
  try{
    const uid=editing.chat_id;
    await api('users',{chat_id:uid,alias:$('alias').value,filters:filters(),mode:$('mode').value,enabled:$('enabled').checked});
    const r=await api('users/'+encodeURIComponent(uid)+'/send',{});
    $('dialog-feedback').textContent=`Sent to Telegram: ${r.count} matching doctors.`;
    await load();
  }catch(e){$('dialog-error').textContent=e.message;}
  finally{$('send-now').disabled=false;$('send-test').disabled=false;$('save').disabled=false;$('delete').disabled=false;$('send-now').textContent='Send now';}
};
$('send-test').onclick=async()=>{
  if(!editing)return;
  const uid=editing.chat_id;
  $('send-test').disabled=true;$('send-now').disabled=true;$('save').disabled=true;$('delete').disabled=true;
  $('send-test').textContent='Sending test…';$('dialog-error').textContent='';$('dialog-feedback').textContent='';
  try{
    await api('users/'+encodeURIComponent(uid)+'/test',{});
    $('dialog-feedback').textContent='Test notification sent: fictional green-plus and red-minus examples.';
  }catch(e){$('dialog-error').textContent=e.message;}
  finally{$('send-test').disabled=false;$('send-now').disabled=false;$('save').disabled=false;$('delete').disabled=false;$('send-test').textContent='Send test notification';}
};
$('delete').onclick=async()=>{
  if(!confirm('Remove this subscriber and stop their notifications?'))return;
  try{await api('users/'+encodeURIComponent(editing.chat_id),{},'DELETE');$('editor').close();notice('Subscriber removed.');load();}catch(e){$('dialog-error').textContent=e.message;}
};
$('copy').onclick=async()=>{
  try{await navigator.clipboard.writeText($('invite-url').value);$('copy').textContent='Copied';}catch{ $('invite-url').select();document.execCommand('copy');$('copy').textContent='Copied'; }
};
$('preview-button').onclick=async()=>{
  try{const r=await api('preview',{filters:filters()});$('preview').innerHTML=`<b>${r.count} matching doctors${r.count>100?' · first 100 shown':''}</b>`+r.doctors.map(d=>`<p><b>${esc(d.name)}</b><br>${esc(d.service)} · ${esc(d.location)}<br>${esc(d.provider)} · ${esc(d.address)}</p>`).join('');}catch(e){$('dialog-error').textContent=e.message;}
};
$('refresh').onclick=async()=>{try{await api('check',{});notice('Refreshing ZZZS data. No notifications will be sent.');load();}catch(e){notice(e.message);}};
$('settings-form').onsubmit=async e=>{
  e.preventDefault();const b=e.submitter;b.disabled=true;
  try{const r=await api('settings',{hour:$('hour').value,bot_token:$('bot-token').value});$('bot-token').value='';notice(r.warning||'Settings saved.');load();}catch(e){notice(e.message);}finally{b.disabled=false;}
};
load();setInterval(load,12000);
