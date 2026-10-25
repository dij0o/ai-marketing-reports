
(function(){
var S=JSON.parse(document.getElementById('state').textContent);
var FIELDS=[['leads','Leads/day',1],['intent','Lead actions/day',0],['sessions','Organic sessions/day',0],['clicks','Search clicks/day',0],['impressions','Impressions/day',0],['indexed','Pages indexed',0]];
var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

var S0=JSON.parse(JSON.stringify(S));
var F={loc:null,bots:false,open:false,bopen:false};
try{var svf=JSON.parse(localStorage.getItem('marketing-report-sample-filters-v1')||'null');if(svf){F.loc=svf.loc||null;F.bots=svf.bots===true;}}catch(e){}
function saveF(){try{localStorage.setItem('marketing-report-sample-filters-v1',JSON.stringify({loc:F.loc,bots:F.bots}));}catch(e){}}
function isBot(L,c,ch){return !!(L.botmap[c+'|'+ch]||L.botmap['*|'+ch]);}
function okRow(L,c,ch){if(F.loc&&!F.loc[c])return false;if(F.bots&&isBot(L,c,ch))return false;return true;}
function applyFilters(){var L=S0.slices;S.weeks=JSON.parse(JSON.stringify(S0.weeks));S.daily=S0.daily;S.view=null;if(!L)return;
 if(!L.botmap){L.botmap={};L.bots.forEach(function(b){L.botmap[b.country+'|'+b.channel]=1;});}
 var days={},v={sessAll:0,sessShown:0,leadAll:0,leadShown:0};function D(k){return days[k]||(days[k]={d:k,leads:0,intent:0,sessions:0,orgLeads:0,orgIntent:0});}
 L.sessions.forEach(function(r){var x=D(r[0]);v.sessAll+=r[3];if(!okRow(L,r[1],r[2]))return;v.sessShown+=r[3];if(r[2]==='Organic Search')x.sessions+=r[3];});
 L.events.forEach(function(r){var x=D(r[0]);var isL=L.leadEvents.indexOf(r[3])>=0;if(isL)v.leadAll+=r[4];if(!okRow(L,r[1],r[2]))return;if(isL){x.leads+=r[4];v.leadShown+=r[4];if(r[2]==='Organic Search')x.orgLeads+=r[4];}else{x.intent+=r[4];if(r[2]==='Organic Search')x.orgIntent+=r[4];}});
 var arr=Object.keys(days).sort().map(function(k){return days[k];});
 S.daily=arr.map(function(x){return {d:x.d,leads:x.leads,intent:x.intent,sessions:x.sessions,orgLeads:x.orgLeads};});
 S.weeks.forEach(function(w){var s=d(w.start).getTime();var ds=arr.filter(function(x){var t=d(x.d).getTime();return t>=s&&t<s+7*864e5;});if(!ds.length)return;
  var avg=function(k){return ds.reduce(function(a,x){return a+x[k];},0)/ds.length;};
  w.leads=avg('leads');w.intent=avg('intent');w.sessions=avg('sessions');w.orgLeads=avg('orgLeads');w.orgIntent=avg('orgIntent');w.days=ds.length;});
 S.view=v;}
function countries(){var L=S0.slices,m={};L.sessions.forEach(function(r){m[r[1]]=(m[r[1]]||0)+r[3];});L.events.forEach(function(r){if(!(r[1] in m))m[r[1]]=0;});return Object.keys(m).map(function(k){return [k,m[k]];}).sort(function(a,b){return b[1]-a[1];});}
function freshBar(){var F0=S0.freshness;if(!F0)return null;
 var box=el('div',{cls:'fresh',role:'group','aria-label':'Data freshness'},[el('h3',{text:'Source freshness and coverage'})]);
 var g=el('div',{cls:'fgrid'});var bad=[];
 function ft(s){return s?fmtDate(s.slice(0,10))+' '+s.slice(11,16):'never';}
 F0.sources.forEach(function(s){if(s.status==='failed')bad.push(s.name);var covers=s.covers?'covers to '+fmtDate(s.covers)+(s.partial?' (today so far)':''):'';
  g.appendChild(el('div',{cls:'fitem '+s.status},[el('i',{cls:s.status}),el('div',{},[el('b',{text:s.name+(s.status==='failed'?' — NOT REFRESHED':s.status==='warn'?' — CHECK':'')}),el('span',{text:'Pulled '+ft(s.retrieved)+(covers?' · '+covers:'')}),el('span',{cls:'note',text:s.note})])]));});
 box.appendChild(g);
 if(bad.length)box.appendChild(el('p',{cls:'fbad',text:'Not refreshed this time: '+bad.join(', ')+'. The numbers that depend on them are from the last good pull shown above, not from now.'}));
 var T=S0.today;if(T)box.appendChild(el('p',{cls:'ftoday'},[el('b',{text:'Today so far ('+fmtDate(T.d)+', partial, as of '+T.asOf.slice(11,16)+'): '}),T.sessions+' sessions ('+T.organic+' organic, '+T.paid+' paid), '+T.leads+' lead'+(T.leads===1?'':'s')+', '+T.intent+' lead action'+(T.intent===1?'':'s')+'. Not included in the weekly figures or the rolling 7 days.']));
 box.appendChild(el('p',{cls:'h2note',style:'margin-top:8px',text:'Snapshot built '+ft(F0.runAt)+'. Sources have independent cutoffs; partial days are separate from completed periods.'}));
 return box;}

function filterBar(){var L=S0.slices;if(!L)return null;var cl=countries();
 function setLoc(excl){if(excl===null){F.loc=null;}else{var o={};cl.forEach(function(c){if(excl.indexOf(c[0])<0)o[c[0]]=1;});F.loc=o;}saveF();render();}
 function onlyLoc(list){var o={};list.forEach(function(c){o[c]=1;});F.loc=o;saveF();render();}
 var key=F.loc?Object.keys(F.loc).sort().join('|'):'';
 function keyEx(ex){return cl.map(function(c){return c[0];}).filter(function(c){return ex.indexOf(c)<0;}).sort().join('|');}
 var PRE=[['All locations',F.loc===null,function(){setLoc(null);}],['UAE only',key==='United Arab Emirates',function(){onlyLoc(['United Arab Emirates']);}],['Exclude Pakistan',F.loc!==null&&key===keyEx(['Pakistan']),function(){setLoc(['Pakistan']);}],['Exclude Pakistan and India',F.loc!==null&&key===keyEx(['Pakistan','India']),function(){setLoc(['Pakistan','India']);}]];
 var grp=el('div',{cls:'fgroup'});PRE.forEach(function(p){var b=el('button',{type:'button',cls:'chipb'+(p[1]?' on':''),text:p[0]});b.addEventListener('click',p[2]);grp.appendChild(b);});
 var bot=el('input',{type:'checkbox',id:'f-bots'});bot.checked=F.bots;bot.addEventListener('change',function(){F.bots=bot.checked;saveF();render();});
 var bar=el('div',{cls:'filters',role:'group','aria-label':'Filters'},[el('span',{cls:'fl',text:'Location'}),grp,el('label',{cls:'chk'},[bot,'Exclude flagged low-engagement traffic'])]);
 var det=el('details',{cls:'fdet'});if(F.open)det.setAttribute('open','');det.addEventListener('toggle',function(){F.open=det.open;});det.appendChild(el('summary',{text:'Choose countries'}));
 var list=el('div',{cls:'clist'});cl.forEach(function(c){var cb=el('input',{type:'checkbox'});cb.checked=!F.loc||!!F.loc[c[0]];cb.addEventListener('change',function(){var o={};var boxes=list.querySelectorAll('input');cl.forEach(function(cc,i){if(boxes[i].checked)o[cc[0]]=1;});F.loc=Object.keys(o).length===cl.length?null:o;saveF();render();});list.appendChild(el('label',{},[cb,c[0],el('em',{text:c[1]?comma(c[1])+' sessions':'events only'})]));});
 det.appendChild(list);bar.appendChild(det);
 var bd=el('details',{cls:'fdet'});if(F.bopen)bd.setAttribute('open','');bd.addEventListener('toggle',function(){F.bopen=bd.open;});bd.appendChild(el('summary',{text:'What counts as bot-like?'}));
 var bl=el('ul',{cls:'botl'});L.bots.filter(function(b){return b.country!=='*';}).forEach(function(b){bl.appendChild(el('li',{text:b.country+', '+b.channel+': '+comma(b.sessions)+' sessions, '+b.engaged+' engaged ('+(b.engaged/b.sessions*100).toFixed(1)+'%)'}));});
 L.bots.filter(function(b){return b.country==='*';}).forEach(function(b){bl.appendChild(el('li',{text:'Whole channel '+b.channel+': '+comma(b.sessions)+' sessions, '+b.engaged+' engaged'}));});
 bd.appendChild(el('p',{cls:'h2note',text:'A country and channel pair, or a whole channel, is flagged as low-engagement when it has at least '+L.rule.min_sessions+' sessions in the period and under '+Math.round(L.rule.max_engaged*100)+'% of them are engaged (a visit that lasts 10 seconds, views 2 pages or takes an action). This is a heuristic, not proof of bots. The optional filter applies only to the sections listed below.'}));bd.appendChild(bl);bar.appendChild(bd);
 var v=S.view;bar.appendChild(el('p',{cls:'fsum'},['Showing ',el('b',{text:comma(v.sessShown)+' of '+comma(v.sessAll)+' sessions'}),' and ',el('b',{text:v.leadShown+' of '+v.leadAll+' lead events'}),' since '+fmtDate(L.start)+'. Applies to the leads, lead actions, organic sessions, conversion and source figures. Search Console figures, the Google Ads section and the keyword and journey sections are not filtered.']));
 return bar;}
function sourceSection(){var L=S0.slices;if(!L)return null;var m={};
 L.sessions.forEach(function(r){if(!okRow(L,r[1],r[2]))return;var x=m[r[2]]||(m[r[2]]={s:0,e:0,l:0,i:0});x.s+=r[3];x.e+=r[4];});
 L.events.forEach(function(r){if(!okRow(L,r[1],r[2]))return;var x=m[r[2]]||(m[r[2]]={s:0,e:0,l:0,i:0});if(L.leadEvents.indexOf(r[3])>=0)x.l+=r[4];else x.i+=r[4];});
 var rows=Object.keys(m).map(function(k){return [k,m[k]];}).sort(function(a,b){return b[1].s-a[1].s;});
 var s=el('section',{},[el('h2',{text:'Where traffic and leads come from'}),el('p',{cls:'h2note',text:'By source, since '+fmtDate(L.start)+', with the filters above applied. Engaged means a visit of 10 seconds or more, 2 or more pages, or an action.'})]);
 var tb=el('table',{cls:'t2'},[el('thead',{},[el('tr',{},['Source','Sessions','Engaged','Lead events','Lead actions'].map(function(t){return el('th',{text:t});}))])]);var bd=el('tbody');
 rows.forEach(function(r){var x=r[1];bd.appendChild(el('tr',{},[el('td',{text:r[0]}),el('td',{text:comma(x.s)}),el('td',{text:x.s?Math.round(x.e/x.s*100)+'%':'\u2014'}),el('td',{text:String(x.l)}),el('td',{text:String(x.i)})]));});
 tb.appendChild(bd);s.appendChild(el('div',{cls:'card',style:'margin-top:16px'},[el('div',{cls:'tw'},[tb])]));return s;}


function el(tag,attrs,kids){var e=document.createElement(tag);if(attrs)for(var k in attrs){if(k==='text')e.textContent=attrs[k];else if(k==='cls')e.className=attrs[k];else e.setAttribute(k,attrs[k]);}(kids||[]).forEach(function(c){if(c!=null)e.appendChild(typeof c==='string'?document.createTextNode(c):c);});return e;}
function d(s){var p=s.split('-');return new Date(Date.UTC(+p[0],+p[1]-1,+p[2]));}
function fmtDate(s){var x=d(s);return x.getUTCDate()+' '+MON[x.getUTCMonth()];}
function has(v){return v!==null&&v!==undefined&&v!==''&&!isNaN(v);}
function n(v,dec){if(!has(v))return '\u2014';v=+v;if(dec)return v.toFixed(dec);if(v>=10000)return (v/1000).toFixed(1).replace(/\.0$/,'')+'k';return Math.round(v).toLocaleString('en-US');}
function cur(){var c=-1,any=-1;S.weeks.forEach(function(w,i){if(has(w.leads)){any=i;if(!has(w.days)||+w.days>=3)c=i;}});return c>=0?c:any;}


function pct(a,b){if(!has(a)||!has(b)||+b===0)return null;return (a-b)/b*100;}
function pctTxt(p){if(p===null)return '\u2014';var r=Math.round(p);return (r>0?'+':r<0?'\u2212':'')+Math.abs(r)+'%';}
function cls(p){return p===null||Math.abs(p)<1?'flat':p>0?'up':'down';}

function fmtV(v){return v>=1e6?(v/1e6).toFixed(1).replace(/\.0$/,'')+'M':v>=1e4?Math.round(v/1e3)+'k':v>=1e3?(v/1e3).toFixed(1).replace(/\.0$/,'')+'k':String(Math.round(v));}
function comma(v){return Math.round(v).toLocaleString('en-US');}
function brow(label,sub,val,max,color,txt){return el('div',{cls:'brow'},[el('span',{cls:'lb'},[label,sub?el('small',{text:sub}):null]),el('span',{cls:'tr'},[el('i',{style:'width:'+(val>0&&max>0?Math.max(1.5,val/max*100):0)+'%;background:'+color})]),el('span',{cls:'vl',text:txt||comma(val)})]);}
function swatch(c,t,v){return el('span',{},[el('i',{cls:'sw',style:'background:'+c}),t,v?el('em',{text:v}):null]);}

function keywordSection(V){var K=V.keywords;if(!K)return null;
 var s=el('section',{},[el('h2',{text:'Keyword gaps'}),el('p',{cls:'h2note',text:'Monthly searches in the UAE and target overseas markets (India excluded), from the keyword analysis of '+fmtDate(K.built)+'. '+K.nameShare+'% of the '+fmtV(K.addressable)+' addressable searches are for names of developers, projects and communities, not generic terms.'})]);
 var col={gap:'var(--risk)',name:'var(--teal)',generic:'var(--secondary)'};var shade=[1,.78,.58,.4,1,.75,.55];
 var card=el('div',{cls:'card',style:'margin-top:16px'},[el('h3',{text:'Where the searches are'}),el('p',{cls:'cnote',text:'Share of '+comma(K.addressable)+' addressable monthly searches. Red is demand for projects the site has no page for.'})]);
 var st=el('div',{cls:'stack',role:'img','aria-label':'Share of addressable searches by type'});K.groups.forEach(function(g,i){var i2=el('i',{style:'width:'+(g.vol/K.addressable*100)+'%;background:'+col[g.kind]+';opacity:'+shade[i]});i2.setAttribute('title',g.label+': '+comma(g.vol));st.appendChild(i2);});card.appendChild(st);
 var keys=el('div',{cls:'keys'});K.groups.forEach(function(g,i){var c=el('span',{},[el('i',{cls:'sw',style:'background:'+col[g.kind]+';opacity:'+shade[i]}),g.label,el('em',{text:fmtV(g.vol)+' \u00b7 '+Math.round(g.vol/K.addressable*100)+'%'})]);keys.appendChild(c);});card.appendChild(keys);s.appendChild(card);
 var stats=el('div',{cls:'stats'},[el('div',{cls:'stat'},[el('b',{text:comma(K.gapProjects),style:'color:var(--risk)'}),el('span',{text:'projects people search for that the site has no page for'})]),el('div',{cls:'stat'},[el('b',{text:fmtV(K.gapVol),style:'color:var(--risk)'}),el('span',{text:'monthly searches for them ('+Math.round(K.gapVol/K.addressable*100)+'% of addressable)'})]),el('div',{cls:'stat'},[el('b',{text:fmtV(K.coveredVol)}),el('span',{text:'searches already matched by an existing page'})]),el('div',{cls:'stat'},[el('b',{text:comma(K.newPageKeywords)}),el('span',{text:'keywords that need a new page ('+fmtV(K.newPageVol)+' searches)'})])]);s.appendChild(stats);
 var cols=el('div',{cls:'cols'});
 var c1=el('div',{cls:'card'},[el('h3',{text:'Missing projects in this sample'}),el('p',{cls:'cnote',text:'Monthly searches. Each needs its own page.'})]);var mx=K.top[0].vol;K.top.forEach(function(p){c1.appendChild(brow(p.name,p.dev,p.vol,mx,'var(--risk)'));});cols.appendChild(c1);
 var c2=el('div',{cls:'card'},[el('h3',{text:'Missing demand by developer'}),el('p',{cls:'cnote',text:'Searches for projects not on the site, grouped by developer. Count is projects.'})]);var m2=K.devs[0].vol;K.devs.forEach(function(p){c2.appendChild(brow(p.dev,p.projects+' projects',p.vol,m2,'var(--gold)'));});cols.appendChild(c2);
 s.appendChild(cols);return s;}

function riskViz(r){var v=r.viz,box=el('div',{});
 if(v.type==='leads'||v.type==='intent'){var days=v.days,mx=1;days.forEach(function(x){var t=v.type==='leads'?x.leads:x.n;if(t>mx)mx=t;});
  var row=el('div',{cls:'cols-viz'});days.forEach(function(x){var t=v.type==='leads'?x.leads:x.n;var stk=el('div',{cls:'stk',style:'height:'+(t?Math.max(6,t/mx*70):2)+'px'});
   if(v.type==='leads'){var ok=x.leads-x.dup-x.burst;[[ok,'var(--teal)'],[x.dup,'var(--risk)'],[x.burst,'var(--gold)']].forEach(function(a){if(a[0])stk.appendChild(el('i',{style:'height:'+(a[0]/x.leads*100)+'%;background:'+a[1]}));});}
   else if(t)stk.appendChild(el('i',{style:'height:100%;background:var(--teal)'}));
   row.appendChild(el('div',{cls:'cv',title:fmtDate(x.d)+': '+t},[el('em',{text:t?String(t):'0',style:t?'':'color:var(--risk)'}),stk,el('small',{text:fmtDate(x.d)})]));});
  box.appendChild(row);
  if(v.type==='leads')box.appendChild(el('div',{cls:'leg2'},[swatch('var(--teal)','Counted'),swatch('var(--risk)','Probable duplicate (same minute)'),swatch('var(--gold)','Burst, looks like testing')]));
  else box.appendChild(el('div',{cls:'leg2'},[el('span',{text:'WhatsApp, phone and email clicks per day, all channels. Red 0 = nothing recorded.'})]));}
 if(v.type==='urls'){var mx2=1;v.sections.forEach(function(x){if(x['404']+x['307']>mx2)mx2=x['404']+x['307'];});
  v.sections.forEach(function(x){var tot=x['404']+x['307'];box.appendChild(el('div',{cls:'brow'},[el('span',{cls:'lb',text:x.s}),el('span',{cls:'tr',style:'display:flex'},[x['404']?el('i',{style:'width:'+x['404']/mx2*100+'%;background:var(--risk);border-radius:0'}):null,x['307']?el('i',{style:'width:'+x['307']/mx2*100+'%;background:var(--gold);border-radius:0'}):null]),el('span',{cls:'vl',text:comma(tot)})]));});
  box.appendChild(el('div',{cls:'leg2'},[swatch('var(--risk)','404 not found'),swatch('var(--gold)','307 temporary redirect to the homepage')]));}
   if(v.type==='ctr'){var ws=S.weeks.filter(function(w){return has(w.clicks)&&has(w.impressions)&&+w.impressions>0;}),top=.01;ws.forEach(function(w){top=Math.max(top,w.clicks/w.impressions*100);});
   ws.forEach(function(w){var value=w.clicks/w.impressions*100;box.appendChild(el('div',{cls:'ctrrow'},[el('span',{text:fmtDate(w.start)}),el('span',{cls:'tr'},[el('i',{style:'width:'+Math.max(1,value/top*100)+'%'})]),el('b',{text:value.toFixed(2)+'%'})]));});}
return box;}
function risksSection(V){if(!V.risks)return null;
 var s=el('section',{},[el('h2',{text:'Risks'}),el('p',{cls:'h2note',text:'Ordered by how much each could mislead or cost us. Charts use the saved snapshot.'})]);
 var g=el('div',{cls:'risks'});var LV={high:'High',med:'Medium',watch:'Watch'};
 V.risks.forEach(function(r){g.appendChild(el('div',{cls:'rk '+r.level},[el('span',{cls:'chip',text:LV[r.level]||r.level}),el('h3',{text:r.title}),el('div',{cls:'big'},[el('b',{text:r.big}),el('span',{text:r.bigNote})]),riskViz(r),el('p',{text:r.text})]));});
 s.appendChild(g);return s;}

function adsSection(V){var P=V.paid;if(!P)return null;var CUR=P.currency,T=P.totals;
 function money(v,d){return v==null?'\u2014':CUR+' '+Number(v).toLocaleString('en-US',{minimumFractionDigits:d||0,maximumFractionDigits:d||0});}
 var s=el('section',{},[el('h2',{text:'Google Ads'}),el('p',{cls:'h2note',text:'Traffic and leads from paid search, next to organic. Spend, clicks and impressions come from the Google Ads account; sessions and leads come from GA4 on the same definitions as the organic numbers above, so the two can be compared.'})]);
 if(!P.live)s.appendChild(el('p',{cls:'launch'},[el('b',{text:'Not live yet. '}),P.enabled+' of '+P.campaigns.length+' campaigns are enabled'+(P.start?'; both are set to start '+fmtDate(P.start):'')+'. Daily budget '+money(P.budget)+'. Every figure below fills in automatically once the campaigns spend. Until then, use the launch checks.']));
  if(P.manual)s.appendChild(el('p',{cls:'launch'},[el('b',{text:'Data source. '}),P.manual]));
 s.appendChild(el('div',{cls:'stats'},[
  el('div',{cls:'stat'},[el('b',{text:money(T.spend,T.spend<100?2:0)}),el('span',{text:'spend since '+fmtDate(P.start)})]),
  el('div',{cls:'stat'},[el('b',{text:comma(T.clicks)}),el('span',{text:'ad clicks'+(T.ctr!=null?' \u00b7 '+T.ctr.toFixed(1)+'% click-through':'')})]),
  el('div',{cls:'stat'},[el('b',{text:money(T.cpc,2)}),el('span',{text:'average cost per click'})]),
   el('div',{cls:'stat'},[el('b',{text:String(T.sessions)}),el('span',{text:'GA4 sessions recorded against a campaign ('+T.engaged+' engaged)'})]),
  el('div',{cls:'stat'},[el('b',{text:String(T.leads)}),el('span',{text:'paid leads (GA4 generate_lead)'})]),
  el('div',{cls:'stat'},[el('b',{text:money(T.cpl)}),el('span',{text:'cost per lead'})]),
  el('div',{cls:'stat'},[el('b',{text:String(T.intent)}),el('span',{text:'paid WhatsApp, phone and email clicks'})])]));
 var cols=el('div',{cls:'cols'});
 var c1=el('div',{cls:'card'},[el('h3',{text:'Paid against organic, last 7 days'}),el('p',{cls:'cnote',text:'Per day over the last 7 days of GA4 data. Paid counts only GA4 sessions that match a campaign in the Ads account; stray google / cpc sessions are left out (see the checks).'})]);
   var l7=(S.daily||[]).slice(-7),dset={},oS=0,oL=0,pS=0,pL=0;l7.forEach(function(x){dset[x.d]=1;oS+=x.sessions||0;oL+=x.orgLeads||0;});
  (P.daily||[]).forEach(function(x){if(dset[x.d]){pS+=x.sessions;pL+=x.leads;}});
  function pair(label,o,p,dec){var mx=Math.max(o,p,0.01);return el('div',{cls:'pair'},[el('span',{text:label}),el('div',{cls:'bars'},[el('div',{},[el('span',{cls:'tr'},[el('i',{style:'width:'+(o>0?Math.max(1,o/mx*100):0)+'%;background:var(--teal)'})]),el('b',{text:o.toFixed(dec)})]),el('div',{},[el('span',{cls:'tr'},[el('i',{style:'width:'+(p>0?Math.max(1,p/mx*100):0)+'%;background:var(--gold)'})]),el('b',{text:p.toFixed(dec)})])])]);}
  if(l7.length){var nd=l7.length;c1.appendChild(pair('Sessions',oS/nd,pS/nd,1));c1.appendChild(pair('Leads',oL/nd,pL/nd,1));
   c1.appendChild(el('div',{cls:'leg2'},[swatch('var(--teal)','Organic'),swatch('var(--gold)','Paid')]));
   c1.appendChild(el('p',{cls:'cnote',style:'margin-top:10px',text:fmtDate(l7[0].d)+' to '+fmtDate(l7[nd-1].d)+': organic '+oS+' sessions and '+oL+' leads, paid '+pS+' sessions and '+pL+' leads.'}));}
  else c1.appendChild(el('p',{cls:'cnote',text:'No data yet.'}));
 cols.appendChild(c1);
 var c2=el('div',{cls:'card'},[el('h3',{text:'Spend and leads by week'}),el('p',{cls:'cnote',text:'Weekly totals. Bar is spend.'})]);
 var mxs=Math.max.apply(null,P.weeks.map(function(x){return x.spend;}).concat([1]));
 if(!P.live)c2.appendChild(el('p',{cls:'cnote',text:'No spend yet.'}));
 else P.weeks.forEach(function(x){if(!x.spend&&!x.clicks&&!x.sessions)return;c2.appendChild(brow(fmtDate(x.start),'',x.spend,mxs,'var(--gold)',money(x.spend)+' \u00b7 '+x.clicks+' clicks \u00b7 '+x.sessions+' sessions \u00b7 '+x.leads+' leads'));});
 cols.appendChild(c2);s.appendChild(cols);
  var dr=(P.daily||[]).filter(function(x){return x.impr||x.clicks||x.sessions;});
  if(dr.length){var dc=el('div',{cls:'card',style:'margin-top:18px'},[el('h3',{text:'Day by day since launch'}),el('p',{cls:'cnote',text:'Impressions, clicks and spend are from the Ads account (pulled '+P.pulled.replace('T',' ').slice(0,16)+', provider time). Sessions, leads and lead actions are GA4 sessions matched to a campaign, so recent days can show more sessions than clicks until Ads is pulled again.'})]);
   var dt=el('table',{cls:'t2'},[el('thead',{},[el('tr',{},['Date','Impr.','Clicks','Spend','GA4 sessions','Engaged','Leads','Lead actions'].map(function(t){return el('th',{text:t});}))])]);var db=el('tbody');
   var lastD=(S.daily&&S.daily.length)?S.daily[S.daily.length-1].d:'';
   dr.forEach(function(x){db.appendChild(el('tr',{},[el('td',{text:fmtDate(x.d)+(lastD&&x.d>lastD?' (today, partial)':'')}),el('td',{text:comma(x.impr)}),el('td',{text:comma(x.clicks)}),el('td',{text:money(x.cost,2)}),el('td',{text:comma(x.sessions)}),el('td',{text:comma(x.engaged)}),el('td',{text:String(x.leads)}),el('td',{text:String(x.intent)})]));});
   dt.appendChild(db);dc.appendChild(el('div',{cls:'tw'},[dt]));s.appendChild(dc);}
 var cc=el('div',{cls:'card',style:'margin-top:18px'},[el('h3',{text:'Campaigns'})]);
 var tb=el('table',{cls:'t2'},[el('thead',{},[el('tr',{},['Campaign','Status','Starts','Budget/day','Spend','Clicks','Impr.','CTR','CPC'].map(function(t){return el('th',{text:t});}))])]);
 var bd=el('tbody');P.campaigns.forEach(function(k){bd.appendChild(el('tr',{},[el('td',{text:k.name}),el('td',{},[el('span',{cls:'st'+(k.status==='ENABLED'?' on':''),text:k.status==='ENABLED'?'Live':k.status.toLowerCase()})]),el('td',{text:k.start?fmtDate(k.start):'\u2014'}),el('td',{text:money(k.budget)}),el('td',{text:money(k.spend)}),el('td',{text:comma(k.clicks)}),el('td',{text:comma(k.impr)}),el('td',{text:k.ctr!=null?k.ctr.toFixed(1)+'%':'\u2014'}),el('td',{text:money(k.cpc,2)})]));});
 tb.appendChild(bd);cc.appendChild(el('div',{cls:'tw'},[tb]));s.appendChild(cc);
 var ck=el('div',{cls:'card',style:'margin-top:18px'},[el('h3',{text:'Launch checks'}),el('p',{cls:'cnote',text:'Recorded from the Ads account and GA4 on '+fmtDate(P.pulled.slice(0,10))+'. Green is fine, amber needs a look, red should be fixed before launch.'})]);
 var ul=el('ul',{cls:'ck'});P.checks.forEach(function(k){ul.appendChild(el('li',{},[el('i',{cls:'dot '+k.s}),el('b',{text:k.t}),el('span',{text:k.d})]));});ck.appendChild(ul);s.appendChild(ck);
 if(P.terms&&P.terms.length){var tc=el('div',{cls:'card',style:'margin-top:18px'},[el('h3',{text:'What people searched before clicking'}),el('p',{cls:'cnote',text:'Top search terms by clicks.'})]);
  var t2=el('table',{cls:'t2'},[el('thead',{},[el('tr',{},['Search term','Clicks','Impr.','Cost','Conv.'].map(function(t){return el('th',{text:t});}))])]);var b2=el('tbody');
  P.terms.forEach(function(t){b2.appendChild(el('tr',{},[el('td',{text:t.term}),el('td',{text:comma(t.clicks)}),el('td',{text:comma(t.impressions)}),el('td',{text:money(t.cost,2)}),el('td',{text:String(Math.round(t.conversions*10)/10)})]));});
  t2.appendChild(b2);tc.appendChild(el('div',{cls:'tw'},[t2]));s.appendChild(tc);}
 return s;}

function journeySection(V){var J=V.journey;if(!J)return null;
 var s=el('section',{},[el('h2',{text:'What visitors from Google do'}),el('p',{cls:'h2note',text:'Organic Search sessions in GA4, '+fmtDate(J.from)+' to '+fmtDate(J.to)+' alongside Search Console queries. These are aggregate landing-page, event and referrer/page views. They do not join individual Search Console clicks to people in GA4.'})]);
 var dev=J.devices||{},dt=(dev.desktop||0)+(dev.mobile||0)+(dev.tablet||0);
 s.appendChild(el('div',{cls:'stats'},[el('div',{cls:'stat'},[el('b',{text:String(J.sessions)}),el('span',{text:'organic sessions'})]),el('div',{cls:'stat'},[el('b',{text:Math.round(J.engaged/J.sessions*100)+'%'}),el('span',{text:'were engaged ('+J.engaged+' of '+J.sessions+')'})]),el('div',{cls:'stat'},[el('b',{text:J.visibleClicks?Math.round(J.brandClicks/J.visibleClicks*100)+'%':'\u2014'}),el('span',{text:'of clicks with a visible search query were for the brand name ('+J.brandClicks+' of '+J.visibleClicks+')'})]),el('div',{cls:'stat'},[el('b',{text:dt?Math.round((dev.mobile||0)/dt*100)+'% mobile':'\u2014'}),el('span',{text:(dev.desktop||0)+' desktop, '+(dev.mobile||0)+' mobile sessions'})])]));
 var cols=el('div',{cls:'cols'});
 var c1=el('div',{cls:'card'},[el('h3',{text:'How far they get'}),el('p',{cls:'cnote',text:'Reported activity by step; session, user and event counts can differ. Steps overlap and do not form a nested conversion funnel.'})]);J.funnel.forEach(function(f,i){c1.appendChild(brow(f.label,'',f.n,J.funnel[0].n,i===J.funnel.length-1?'var(--gold)':'var(--teal)'));});cols.appendChild(c1);
 var c2=el('div',{cls:'card'},[el('h3',{text:'Where they land'}),el('p',{cls:'cnote',text:'First page of the visit, grouped.'})]);J.landing.forEach(function(f){c2.appendChild(brow(f.label,'',f.n,J.landing[0].n,'var(--teal)',f.n+' \u00b7 '+Math.round(f.n/J.sessions*100)+'%'));});cols.appendChild(c2);
 var c3=el('div',{cls:'card'},[el('h3',{text:'How they arrive'}),el('p',{cls:'cnote',text:'Source and first page.'})]);(J.entry||[]).forEach(function(p){c3.appendChild(el('div',{cls:'pth2'},[el('span',{cls:'pth'},[p.from+' \u2192 '+p.to]),el('b',{text:p.n+(p.n===1?' visit':' visits')})]));});cols.appendChild(c3);
 var c4=el('div',{cls:'card'},[el('h3',{text:'Where they go next'}),el('p',{cls:'cnote',text:'Moves from one page to another inside the site.'})]);(J.onward||[]).forEach(function(p){c4.appendChild(el('div',{cls:'pth2'},[el('span',{cls:'pth'},[p.from+' \u2192 '+p.to]),el('b',{text:p.n+(p.n===1?' time':' times')})]));});cols.appendChild(c4);
 s.appendChild(cols);
 var ins=el('ul',{cls:'insights'});var home=J.landing.filter(function(x){return x.label==='Homepage';})[0],art=J.landing.filter(function(x){return x.label==='Guides and articles';})[0];
 if(home&&J.visibleClicks)ins.appendChild(el('li',{text:home.n+' of '+J.sessions+' visits ('+Math.round(home.n/J.sessions*100)+'%) start on the homepage, and '+Math.round(J.brandClicks/J.visibleClicks*100)+'% of the clicks we can attribute to a query were for the brand name in this snapshot. Hidden queries are not classified.'}));
 if(J.leadEvents>J.leadUsers&&J.leadUsers>0)ins.appendChild(el('li',{text:'All '+J.leadEvents+' organic lead events came from '+J.leadUsers+' visitor on '+J.leadPage+'. Event counts do not establish unique qualified prospects.'}));
 var fo=J.funnel[2],fs=J.funnel[5];if(fo&&fs&&fo.n>fs.n*3)ins.appendChild(el('li',{text:'The enquiry form opens for '+fo.n+' of '+J.sessions+' visitors but only '+fs.n+' starts filling it in. It may be opening on its own (a popup), so \u201cform opened\u201d is not a sign of intent.'}));
 s.appendChild(ins);
 s.appendChild(el('p',{cls:'caveat',text:'Small numbers: '+J.sessions+' sessions in the stated reporting period. Treat these as patterns to check, not conclusions. Search Console hides most query text for low-volume searches, so brand share covers only the clicks it shows.'}));
 return s;}

function webmasterSection(){
 var providers=S.webmasters;if(!providers||!providers.length)return null;
 var section=el('section',{},[el('h2',{text:'Bing and Yandex Webmaster'}),el('p',{cls:'h2note',text:'Separate source records. Connection status, property verification and traffic availability are different facts.'})]),cards=el('div',{cls:'cols'});
 providers.forEach(function(p){var card=el('div',{cls:'card'},[el('h3',{text:p.name}),el('p',{cls:'cnote',text:p.status}),el('p',{text:p.note})]);if(p.rows&&p.rows.length){var table=el('table',{cls:'t2'}),head=el('tr',{}),cols=Object.keys(p.rows[0]);cols.forEach(function(k){head.appendChild(el('th',{text:k}));});table.appendChild(el('thead',{},[head]));var body=el('tbody');p.rows.forEach(function(row){body.appendChild(el('tr',{},cols.map(function(k){return el('td',{text:row[k]===null?'Unavailable':String(row[k])});})));});table.appendChild(body);card.appendChild(el('div',{cls:'tw'},[table]));}cards.appendChild(card);});section.appendChild(cards);return section;
}

function render(){
 applyFilters();
 var root=document.getElementById('root');root.textContent='';
 var c=cur(),w=c>=0?S.weeks[c]:null;
 root.appendChild(el('header',{cls:'top'},[el('p',{cls:'brand'},[S.brand||'Example site',el('span',{text:' Search, analytics and advertising report'})]),el('p',{cls:'wk',text:w?'Week of '+fmtDate(w.start)+' '+d(w.start).getUTCFullYear():'No observations'})]));
 root.appendChild(el('p',{cls:'banner',text:S.sample?'Illustrative sample: fictional figures demonstrate the report layout. This is not live account data.': 'Reference sample from a supplied historical snapshot. This page makes no live API calls.'}));
 var fr=freshBar();if(fr)root.appendChild(fr);
 var fb=filterBar();if(fb)root.appendChild(fb);
 var ans=el('div',{cls:'answer'});
 ans.appendChild(el('h1',{text:w&&has(w.sessions)?n(w.sessions,1)+' organic sessions a day in the latest observed week.':'Search visibility and recorded visitor activity.'}));
 if(w)ans.appendChild(el('p',{cls:'sub',text:(has(w.leads)?n(w.leads,1)+' recorded lead events a day across channels. ':'')+(w.days?w.days+' observed days in this week. ':'')+'Lead events are measurements, not verified unique prospects.'}));
 root.appendChild(ans);
 var s1=el('section',{},[el('h2',{text:'Recorded lead events over time'}),el('p',{cls:'h2note',text:'Observed daily averages by week, with no forecasts. Missing observations are left blank.'}),el('div',{cls:'chart',id:'lead-history'})]);root.appendChild(s1);
 var g2=el('div',{cls:'grid2'});
 var s2=el('section',{},[el('h2',{text:'This week in context'}),el('p',{cls:'h2note',text:'Observed values and change from the preceding calendar week. Different sources can have different coverage.'})]);
 var ul=el('ul',{cls:'chain'});
 var EX={leads:'Recorded form/enquiry events, all channels',intent:'Recorded contact and form-action events, all channels',sessions:'Organic Search sessions in GA4',clicks:'Google Search Console clicks',impressions:'Google Search Console appearances',indexed:'Provider-reported indexed pages, when available'};
 FIELDS.forEach(function(f){var k=f[0],v=w?w[k]:null,prev=c>0?S.weeks[c-1][k]:null;var sm=el('small',{},[el('span',{cls:cls(pct(v,prev)),text:pctTxt(pct(v,prev))+' vs previous week'})]);ul.appendChild(el('li',{},[el('span',{cls:'nm',text:f[1]}),el('span',{cls:'val'},[n(v,f[2]),sm]),el('span',{cls:'ex',text:EX[k]})]));});
 s2.appendChild(ul);g2.appendChild(s2);
 var s3=el('section',{},[el('h2',{text:'Organic sessions per day'}),el('p',{cls:'h2note',text:'Observed weekly averages from GA4 only. Search clicks are a separate metric and are not used as substitute sessions.'}),el('div',{cls:'chart',id:'traffic'})]);g2.appendChild(s3);root.appendChild(g2);
 var V=S.visuals||{};
 [sourceSection(),webmasterSection(),adsSection(V),journeySection(V),keywordSection(V),risksSection(V)].forEach(function(x){if(x)root.appendChild(x);});
 var s4=el('section',{},[el('h2',{text:'This week'})]),nb=el('div',{cls:'notes two'});
 [['moved','What the data shows','n-move'],['decisions','Questions and next steps','n-dec']].forEach(function(x){var text=(S.notes&&S.notes[x[0]])||'',list=el('ul',{});text.split('\n').forEach(function(line){if(line.trim())list.appendChild(el('li',{text:line.trim()}));});nb.appendChild(el('div',{cls:x[2]},[el('h3',{text:x[1]}),text.trim()?list:el('p',{cls:'empty',text:'Nothing noted.'})]));});s4.appendChild(nb);root.appendChild(s4);
 root.appendChild(el('p',{cls:'foot',text:'Snapshot date '+S.updated+'. Lead events and sessions: GA4. Search clicks and impressions: Search Console. Ad spend and clicks: Google Ads. Metrics retain their own source scope.'}));
 drawHistory('lead-history','leads','Recorded lead events per day by observed week');drawHistory('traffic','sessions','Organic sessions per day by observed week');
}

function svgEl(tag,a){var e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(var k in a)e.setAttribute(k,a[k]);return e;}
function frame(box,h){var W=Math.max(320,box.clientWidth-16);var svg=svgEl('svg',{viewBox:'0 0 '+W+' '+h,width:W,height:h,role:'img'});return {svg:svg,W:W,H:h};}
function axisX(svg,x,H,b){S.weeks.forEach(function(w,i){var dt=d(w.start);var th=new Date(dt.getTime()+3*864e5);var prev=i>0?new Date(d(S.weeks[i-1].start).getTime()+3*864e5):null;if(!prev||prev.getUTCMonth()!==th.getUTCMonth()){var t=svgEl('text',{x:x(i),y:H-b+20,'font-size':12,fill:'var(--muted)'});t.textContent=MON[th.getUTCMonth()];svg.appendChild(t);}});}

function drawHistory(id,key,label){
 var box=document.getElementById(id);if(!box)return;var old=box.querySelector('svg');if(old)old.remove();
 var f=frame(box,id==='traffic'?240:300),svg=f.svg,W=f.W,H=f.H,l=44,r=12,t=18,b=38,N=S.weeks.length;
 var values=S.weeks.map(function(w){return has(w[key])?+w[key]:null;}),maximum=Math.max.apply(null,values.filter(function(v){return v!==null;}).concat([1]));
 var top=Math.ceil(maximum*1.2),bw=(W-l-r)/Math.max(1,N),x=function(i){return l+i*bw+bw/2;},y=function(v){return t+(H-t-b)*(1-v/top);};
 svg.setAttribute('aria-label',label);
 [0,top/2,top].forEach(function(v){svg.appendChild(svgEl('line',{x1:l,x2:W-r,y1:y(v),y2:y(v),stroke:'var(--line)'}));var tx=svgEl('text',{x:l-7,y:y(v)+4,'font-size':12,'text-anchor':'end',fill:'var(--muted)'});tx.textContent=n(v,v%1?1:0);svg.appendChild(tx);});
 values.forEach(function(v,i){if(v===null)return;var bar=svgEl('rect',{x:x(i)-bw*.28,width:bw*.56,y:y(v),height:Math.max(0,H-b-y(v)),rx:3,fill:'var(--teal)'}),title=svgEl('title',{});title.textContent='Week of '+fmtDate(S.weeks[i].start)+': '+n(v,1)+' per day';bar.appendChild(title);svg.appendChild(bar);var caption=svgEl('text',{x:x(i),y:H-b+21,'font-size':11,'text-anchor':'middle',fill:'var(--muted)'});caption.textContent=fmtDate(S.weeks[i].start);svg.appendChild(caption);});box.appendChild(svg);
}



render();
var rt;window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(function(){drawHistory('lead-history','leads','Recorded lead events per day by observed week');drawHistory('traffic','sessions','Organic sessions per day by observed week');},150);});
})();
