(function(){
  const $ = sel => document.querySelector(sel);
  const out = $('#out');
  const tokIn = $('#tok');
  const save = $('#saveTok');
  const lp = $('#lp');
  const copyLP = $('#copyLP');

  // token persistence
  const KEY='pa_phone_token';
  tokIn.value = localStorage.getItem(KEY)||'';
  save.onclick = ()=>{ localStorage.setItem(KEY, tokIn.value||''); };

  function log(s){ out.textContent = (out.textContent? out.textContent + "\n":"") + s; }

  function renderOptions(){
    fetch('/phone/options').then(r=>r.json()).then(o=>{
      const list = $('#options'); list.innerHTML='';
      (o.options||[]).forEach(it=>{
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.textContent = `${it.key}) ${it.label}`;
        btn.onclick = ()=>{
          const tok = localStorage.getItem(KEY)||'';
          fetch('/phone/approve',{method:'POST', headers:{
            'Content-Type':'application/json',
            'X-Phone-Token': tok
          }, body: JSON.stringify({choice: it.key, phrase: it.phrase})})
          .then(r=>r.json()).then(j=>{ log(JSON.stringify(j)); })
          .catch(e=>log('ERR '+e.message));
        };
        li.appendChild(btn);
        const span = document.createElement('span');
        span.style.marginLeft='8px';
        span.textContent = ` say: ${it.phrase}`;
        li.appendChild(span);
        list.appendChild(li);
      });
    }).catch(e=>log('Options error: '+e.message));
  }

  function pollLatestPack(){
    fetch('/phone/latest_pack').then(r=>r.json()).then(j=>{
      lp.textContent = j.latest_pack || '—';
    }).catch(e=>{ lp.textContent = '—'; });
  }
  copyLP.onclick = ()=>{
    navigator.clipboard.writeText(lp.textContent||'').catch(()=>{});
  };

  renderOptions();
  pollLatestPack();
  setInterval(pollLatestPack, 5000);
})();