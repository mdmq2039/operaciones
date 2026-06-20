"""
sorteo_app.py - Sorteo al Azar desde Excel
Ejecutar: streamlit run sorteo_app.py --server.port 8502
"""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(
    page_title="Sorteo al Azar",
    page_icon="🎰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp {background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)}
    header, footer, #MainMenu {visibility: hidden}
    .stFileUploader > div {border-color: rgba(233,69,96,.5) !important; border-radius: 16px !important}
    .stNumberInput input {text-align: center; font-weight: 700; font-size: 1.2rem}
</style>
""", unsafe_allow_html=True)


def parse_excel(uploaded):
    df = pd.read_excel(uploaded)
    col_name = None
    col_turno = None
    col_empresa = None
    for c in df.columns:
        cl = c.strip().lower()
        if any(a in cl for a in ["nombres completos", "nombre completo", "nombres", "nombre"]):
            if col_name is None:
                col_name = c
        if any(a in cl for a in ["turno", "tuno", "shift"]):
            col_turno = c
        if any(a in cl for a in ["empresa", "company", "service"]):
            col_empresa = c
    if not col_name:
        return None, "No se encontró columna de nombres"
    rows = []
    for _, r in df.iterrows():
        name = str(r.get(col_name, "")).strip()
        if not name or name == "nan":
            continue
        rows.append({
            "name": name,
            "turno": str(r.get(col_turno, "")).strip() if col_turno else "",
            "empresa": str(r.get(col_empresa, "")).strip() if col_empresa else "",
        })
    return rows, None


def raffle_html(participants_json, total_winners, company):
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--gold:#e94560;--gold-light:#ff6b6b;--bg:#1a1a2e;--card:rgba(255,255,255,.07)}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:transparent;
  color:#eee;overflow-x:hidden;min-height:100%;padding:10px}}

.header{{text-align:center;margin-bottom:12px}}
.logo{{font-size:.9rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;opacity:.6}}
.company{{font-size:1.4rem;font-weight:800;
  background:linear-gradient(135deg,var(--gold),var(--gold-light),#ffd93d);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.progress{{font-size:.8rem;opacity:.5;margin-top:4px}}

.slot-container{{
  width:100%;max-width:400px;height:260px;margin:0 auto 16px;
  border-radius:18px;overflow:hidden;position:relative;
  background:var(--card);border:1px solid rgba(233,69,96,.2)}}
.slot-mask{{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:2;
  background:linear-gradient(to bottom,var(--bg) 0%,transparent 25%,transparent 75%,var(--bg) 100%)}}
.slot-highlight{{position:absolute;top:50%;left:0;right:0;height:60px;transform:translateY(-50%);
  border-top:2px solid var(--gold);border-bottom:2px solid var(--gold);
  background:rgba(233,69,96,.08);z-index:1}}
.slot-track{{position:absolute;top:0;left:0;right:0}}
.slot-item{{height:60px;display:flex;align-items:center;justify-content:center;
  flex-direction:column;padding:4px 14px}}
.slot-item .nm{{font-size:1rem;font-weight:700;color:#fff}}
.slot-item .dt{{font-size:.65rem;opacity:.45;margin-top:1px}}

.btn{{padding:14px 40px;border:none;border-radius:50px;font-size:1.1rem;
  font-weight:700;cursor:pointer;transition:.3s;text-transform:uppercase;
  letter-spacing:1px;display:block;margin:0 auto}}
.btn-go{{background:linear-gradient(135deg,#ffd93d,#ff6b35,var(--gold));
  color:#fff;box-shadow:0 4px 25px rgba(255,217,61,.3);animation:gp 2s infinite}}
@keyframes gp{{0%,100%{{box-shadow:0 4px 25px rgba(255,217,61,.3)}}
  50%{{box-shadow:0 4px 45px rgba(255,217,61,.6)}}}}
.btn-go:disabled{{animation:none;opacity:.35}}
.btn-go:active{{transform:scale(.96)}}

.btn-new{{background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.2);
  margin-top:14px;font-size:.85rem;padding:10px 26px}}

.overlay{{position:fixed;top:0;left:0;right:0;bottom:0;display:none;
  align-items:center;justify-content:center;flex-direction:column;z-index:100}}
.overlay.on{{display:flex}}
.cd-bg{{background:rgba(10,10,30,.92)}}
.wr-bg{{background:rgba(10,10,30,.95)}}
.cd-num{{font-size:7rem;font-weight:900;
  background:linear-gradient(135deg,var(--gold),#ffd93d);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:cp .5s ease-out}}
.cd-lbl{{font-size:1rem;opacity:.4;margin-top:6px}}
@keyframes cp{{0%{{transform:scale(2);opacity:0}}100%{{transform:scale(1);opacity:1}}}}

.wb{{font-size:.95rem;font-weight:700;color:var(--gold);text-transform:uppercase;
  letter-spacing:3px;margin-bottom:8px;opacity:0;animation:fd .5s .2s forwards}}
.wn{{font-size:2rem;font-weight:900;text-align:center;padding:0 16px;
  background:linear-gradient(135deg,#ffd93d,#ff6b35,var(--gold));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  opacity:0;animation:fd .5s .5s forwards}}
.wd{{opacity:0;margin-top:10px;text-align:center;animation:fd .5s .8s forwards}}
.wd span{{display:inline-block;padding:3px 12px;margin:3px;
  background:rgba(233,69,96,.2);border-radius:18px;font-size:.8rem}}
.wcl{{margin-top:24px;opacity:0;animation:fd .5s 1.1s forwards;
  background:linear-gradient(135deg,var(--gold),var(--gold-light));
  color:#fff;box-shadow:0 4px 20px rgba(233,69,96,.4)}}
@keyframes fd{{0%{{opacity:0;transform:translateY(-18px)}}100%{{opacity:1;transform:translateY(0)}}}}

.wlist{{width:100%;max-width:400px;margin:14px auto 0}}
.wlist h4{{font-size:.8rem;opacity:.4;text-transform:uppercase;letter-spacing:2px;
  text-align:center;margin-bottom:8px}}
.wcard{{background:var(--card);border-radius:12px;padding:12px 14px;margin-bottom:6px;
  display:flex;align-items:center;gap:12px;border-left:3px solid var(--gold);
  animation:si .4s ease-out}}
@keyframes si{{0%{{opacity:0;transform:translateX(-25px)}}100%{{opacity:1;transform:translateX(0)}}}}
.wnum{{width:28px;height:28px;border-radius:50%;
  background:linear-gradient(135deg,var(--gold),var(--gold-light));
  display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:.8rem;color:#fff;flex-shrink:0}}
.wi{{flex:1;min-width:0}}
.wi .n{{font-weight:700;font-size:.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.wi .m{{font-size:.7rem;opacity:.45;margin-top:1px}}

canvas#confetti{{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:200}}
</style>
</head>
<body>
<canvas id="confetti"></canvas>

<div class="header">
  <div class="logo">&#9733; Sorteo &#9733;</div>
  <div class="company" id="co">{company}</div>
  <div class="progress" id="prog">Ganador 1 de {total_winners}</div>
</div>

<div class="slot-container" id="sc">
  <div class="slot-mask"></div>
  <div class="slot-highlight"></div>
  <div class="slot-track" id="st"></div>
</div>

<button class="btn btn-go" id="btnGo" disabled>&#127942; Iniciar Sorteo</button>

<div class="wlist" id="wlist"><h4>Ganadores</h4></div>
<button class="btn btn-new" id="btnNew" style="display:none" onclick="location.reload()">Nuevo Sorteo</button>

<div class="overlay cd-bg" id="cdOv">
  <div class="cd-num" id="cdN">5</div>
  <div class="cd-lbl">Preparando sorteo...</div>
</div>

<div class="overlay wr-bg" id="wrOv">
  <div class="wb" id="wrB">Ganador #1</div>
  <div class="wn" id="wrN">Nombre</div>
  <div class="wd" id="wrD"><span>Turno</span><span>Empresa</span></div>
  <button class="btn wcl" onclick="closeReveal()">Continuar</button>
</div>

<script>
const P={participants_json};
const TW={total_winners};
let rem=[...P],winners=[],spinning=false,spI=null,phase='init';
const IH=60;

function esc(s){{let d=document.createElement('div');d.textContent=s;return d.innerHTML}}

// countdown
function countdown(cb){{
  const ov=document.getElementById('cdOv'),n=document.getElementById('cdN');
  ov.classList.add('on');let c=5;
  n.textContent=c;n.style.animation='none';void n.offsetWidth;n.style.animation='cp .5s ease-out';
  const iv=setInterval(()=>{{
    c--;
    if(c<=0){{clearInterval(iv);n.textContent='🎉';
      n.style.animation='none';void n.offsetWidth;n.style.animation='cp .5s ease-out';
      setTimeout(()=>{{ov.classList.remove('on');cb()}},600);return}}
    n.textContent=c;n.style.animation='none';void n.offsetWidth;n.style.animation='cp .5s ease-out';
  }},1000);
}}

function buildTrack(){{
  const t=document.getElementById('st');t.innerHTML='';
  const pool=rem.length?rem:P;
  const tot=Math.max(pool.length*3,60);
  for(let i=0;i<tot;i++){{const p=pool[i%pool.length];
    const d=document.createElement('div');d.className='slot-item';
    d.innerHTML=`<div class="nm">${{esc(p.name)}}</div><div class="dt">${{esc(p.turno)}} · ${{esc(p.empresa)}}</div>`;
    t.appendChild(d)}}
}}

function startSpin(){{
  if(spinning)return;spinning=true;
  const t=document.getElementById('st'),sc=document.getElementById('sc');
  const tot=t.children.length;let pos=0;
  const co=(sc.offsetHeight/2)-(IH/2);
  spI=setInterval(()=>{{
    pos-=8;if(pos<=-(tot*IH)+sc.offsetHeight)pos=0;
    t.style.transform=`translateY(${{pos+co}}px)`;
  }},30);
}}

function stopSpin(){{spinning=false;if(spI){{clearInterval(spI);spI=null}}}}

function slowDown(winner,cb){{
  if(spI){{clearInterval(spI);spI=null}}
  buildTrack();
  const t=document.getElementById('st'),sc=document.getElementById('sc');
  const co=(sc.offsetHeight/2)-(IH/2);
  const items=t.children;let ti=-1;
  for(let i=Math.floor(items.length/2);i<items.length;i++){{
    const ne=items[i].querySelector('.nm');
    if(ne&&ne.textContent===winner.name){{ti=i;break}}
  }}
  if(ti===-1)ti=Math.floor(items.length/2);
  const tp=-(ti*IH)+co;let cp2=0;const td=Math.abs(tp)+500;let tv=0;
  spI=setInterval(()=>{{
    const pr=Math.min(tv/td,1),e=1-Math.pow(pr,3),sp=Math.max(12*e,0.5);
    tv+=sp;cp2-=sp;
    if(cp2<=tp){{clearInterval(spI);spI=null;
      t.style.transform=`translateY(${{tp}}px)`;setTimeout(cb,300);return}}
    t.style.transform=`translateY(${{cp2}}px)`;
  }},30);
}}

function showWinner(w){{
  const ov=document.getElementById('wrOv');
  document.getElementById('wrB').textContent='🏆 Ganador #'+winners.length;
  document.getElementById('wrN').textContent=w.name;
  document.getElementById('wrD').innerHTML=
    `<span>📋 ${{esc(w.turno)}}</span><span>🏢 ${{esc(w.empresa)}}</span>`;
  ['wrB','wrN','wrD'].forEach(id=>{{
    const el=document.getElementById(id);el.style.animation='none';void el.offsetWidth}});
  document.getElementById('wrB').style.animation='fd .5s .2s forwards';
  document.getElementById('wrN').style.animation='fd .5s .5s forwards';
  document.getElementById('wrD').style.animation='fd .5s .8s forwards';
  ov.classList.add('on');confetti();
}}

function closeReveal(){{
  document.getElementById('wrOv').classList.remove('on');
  addCard(winners[winners.length-1],winners.length);
  updProg();
  if(winners.length>=TW){{
    document.getElementById('btnGo').style.display='none';
    document.getElementById('btnNew').style.display='block';
    stopSpin();
  }}else{{buildTrack();startSpin();
    const b=document.getElementById('btnGo');b.disabled=false;b.textContent='🏆 Ganador'}}
}}

function addCard(w,n){{
  const l=document.getElementById('wlist');
  const c=document.createElement('div');c.className='wcard';
  c.innerHTML=`<div class="wnum">${{n}}</div><div class="wi">
    <div class="n">${{esc(w.name)}}</div>
    <div class="m">${{esc(w.turno)}} · ${{esc(w.empresa)}}</div></div>`;
  l.appendChild(c);
}}

function updProg(){{
  document.getElementById('prog').textContent=
    `Ganador ${{Math.min(winners.length+1,TW)}} de ${{TW}}`;
}}

function confetti(){{
  const cv=document.getElementById('confetti'),ctx=cv.getContext('2d');
  cv.width=window.innerWidth;cv.height=window.innerHeight;
  const pcs=[],cols=['#e94560','#ffd93d','#ff6b6b','#0f3460','#4ecdc4','#ff6b35'];
  for(let i=0;i<100;i++)pcs.push({{x:Math.random()*cv.width,y:-Math.random()*cv.height,
    w:Math.random()*10+4,h:Math.random()*6+2,
    color:cols[Math.floor(Math.random()*cols.length)],
    vy:Math.random()*4+2,vx:(Math.random()-.5)*3,
    rot:Math.random()*360,vr:(Math.random()-.5)*8}});
  let f=0;
  function draw(){{ctx.clearRect(0,0,cv.width,cv.height);let alive=false;
    pcs.forEach(p=>{{p.y+=p.vy;p.x+=p.vx;p.rot+=p.vr;p.vy+=.05;
      if(p.y<cv.height+20)alive=true;
      ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.rot*Math.PI/180);
      ctx.fillStyle=p.color;ctx.globalAlpha=Math.max(0,1-p.y/cv.height);
      ctx.fillRect(-p.w/2,-p.h/2,p.w,p.h);ctx.restore()}});
    f++;if(alive&&f<150)requestAnimationFrame(draw);
    else ctx.clearRect(0,0,cv.width,cv.height)}}
  draw();
}}

// main flow
document.getElementById('btnGo').addEventListener('click',function(){{
  const btn=this;btn.disabled=true;
  if(phase==='init'){{
    phase='running';
    countdown(()=>{{buildTrack();startSpin();
      btn.disabled=false;btn.textContent='🏆 Ganador'}});
    return;
  }}
  if(winners.length>=TW)return;
  const idx=Math.floor(Math.random()*rem.length);
  const w=rem.splice(idx,1)[0];winners.push(w);
  slowDown(w,()=>{{stopSpin();showWinner(w)}});
}});

document.getElementById('btnGo').disabled=false;
</script>
</body>
</html>
"""


# ── UI ──
st.markdown("""
<div style="text-align:center;padding:10px 0">
  <div style="font-size:.9rem;font-weight:700;letter-spacing:2px;
    text-transform:uppercase;opacity:.5">&#9733; Sorteo &#9733;</div>
  <div style="font-size:1.6rem;font-weight:800;
    background:linear-gradient(135deg,#e94560,#ff6b6b,#ffd93d);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent">
    Sorteo al Azar</div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Cargar archivo Excel", type=["xlsx", "xls"],
                            label_visibility="collapsed")

if uploaded:
    participants, err = parse_excel(uploaded)
    if err:
        st.error(err)
    elif not participants:
        st.warning("El archivo no contiene participantes válidos.")
    else:
        company = participants[0]["empresa"] if participants[0]["empresa"] else "Sorteo"
        st.success(f"**{len(participants)}** participantes cargados")

        total = st.number_input("Cantidad de ganadores", min_value=1,
                                max_value=len(participants), value=1, step=1)

        if st.button("🎰 Iniciar Sorteo", type="primary", use_container_width=True):
            pjson = json.dumps(participants, ensure_ascii=False)
            html = raffle_html(pjson, int(total), company)
            components.html(html, height=700, scrolling=True)
