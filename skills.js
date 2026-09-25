const API_URL="https://pixelworld-0wr6.onrender.com";
let authToken=localStorage.getItem("pixelworld_token")||"";
if(location.hash.startsWith("#token=")){authToken=decodeURIComponent(location.hash.slice(7));localStorage.setItem("pixelworld_token",authToken);history.replaceState(null,"",location.pathname+location.search);}
function authHeaders(extra={}){return authToken?{...extra,Authorization:"Bearer "+authToken}:extra;}
const MAX_LEVEL=36;
const accountArea=document.getElementById("accountArea"),pointsEl=document.getElementById("skillPoints"),totalEl=document.getElementById("totalPlaced"),messageEl=document.getElementById("skillMessage");
let player=null;
function esc(s){return String(s).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));}
function accountUI(){if(player){accountArea.innerHTML=`<span class="account-name">🎮 ${esc(player.username)}</span><button class="top-button" id="logoutBtn">Déconnexion</button>`;document.getElementById("logoutBtn").onclick=async()=>{await fetch(API_URL+"/auth/logout",{method:"POST",headers:authHeaders()});localStorage.removeItem("pixelworld_token");location.reload();};}else accountArea.innerHTML=`<a class="discord-button" href="${API_URL}/auth/discord">🔵 Se connecter avec Discord</a>`;}
function msg(t){messageEl.textContent=t;messageEl.classList.add("show");setTimeout(()=>messageEl.classList.remove("show"),3000);}
function render(){
  if(!player){pointsEl.textContent="0";totalEl.textContent="0";document.querySelectorAll(".skill-button").forEach(b=>b.disabled=true);return;}
  pointsEl.textContent=player.skill_points;totalEl.textContent=player.total_placed;
  const values={storage:[player.storage_level,`${player.max_storage} / 200 pixels`],cooldown:[player.cooldown_level,`${player.recharge_seconds} secondes / 20 secondes`],crit:[player.crit_level,`${player.crit_chance.toFixed(2)} % / 10 %` ]};
  for(const key of Object.keys(values)){
    const [lv,stat]=values[key];document.getElementById(key+"Level").textContent=`Niveau ${lv} / ${MAX_LEVEL}`;document.getElementById(key+"Stat").textContent=stat;document.getElementById(key+"Bar").style.width=(lv/MAX_LEVEL*100)+"%";
  }
  document.querySelectorAll(".skill-button").forEach(b=>{const key=b.dataset.skill,lv=player[key+"_level"];b.disabled=player.skill_points<1||lv>=MAX_LEVEL;b.textContent=lv>=MAX_LEVEL?"MAXIMUM":"Améliorer • 1 point";});
}
async function load(){try{const r=await fetch(API_URL+"/api/me",{headers:authHeaders()});const d=await r.json();player=d.player;accountUI();render();if(!player)msg("Connecte-toi avec Discord pour utiliser l'arbre de compétences.");}catch{msg("Serveur inaccessible.");}}
document.querySelectorAll(".skill-button").forEach(b=>b.onclick=async()=>{if(!player)return;b.disabled=true;const r=await fetch(API_URL+"/api/skills/"+b.dataset.skill,{method:"POST",headers:authHeaders()});const d=await r.json();if(!r.ok){msg(d.error||"Impossible.");render();return;}player=d.player;render();msg("🧠 Compétence améliorée !");});
load();
