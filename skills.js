const API_URL = "https://pixelworld-0wr6.onrender.com";
function authHeaders() {
    const token = localStorage.getItem("pixelworld_token");
    return token
        ? { "Authorization": `Bearer ${token}` }
        : {};
}

const accountArea=document.getElementById("accountArea"), pointsEl=document.getElementById("skillPoints"), totalEl=document.getElementById("totalPlaced"), messageEl=document.getElementById("skillMessage");
let player=null;
function esc(s){return String(s).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));}
function accountUI(){if(player){accountArea.innerHTML=`<span class="account-name">🎮 ${esc(player.username)}</span><button class="top-button" id="logoutBtn">Déconnexion</button>`;document.getElementById("logoutBtn").onclick=async()=>{await fetch(API_URL+"/auth/logout",{method:"POST",headers:authHeaders()});localStorage.removeItem("pixelworld_token");location.reload();};}else accountArea.innerHTML=`<a class="discord-button" href="${API_URL}/auth/discord">🔵 Se connecter avec Discord</a>`;}
function msg(t){messageEl.textContent=t;messageEl.classList.add("show");setTimeout(()=>messageEl.classList.remove("show"),3000);}
function render(){if(!player){pointsEl.textContent="0";totalEl.textContent="0";document.querySelectorAll(".skill-button").forEach(b=>b.disabled=true);return;}pointsEl.textContent=player.skill_points;totalEl.textContent=player.total_placed;document.getElementById("storageLevel").textContent=`Niveau ${player.storage_level} / 5`;document.getElementById("cooldownLevel").textContent=`Niveau ${player.cooldown_level} / 5`;document.getElementById("critLevel").textContent=`Niveau ${player.crit_level} / 5`;document.querySelectorAll(".skill-button").forEach(b=>{const key=b.dataset.skill,lv=player[key+"_level"];b.disabled=player.skill_points<1||lv>=5;b.textContent=lv>=5?"MAXIMUM":"Améliorer • 1 point";});}
async function load(){try{const r=await fetch(API_URL+"/api/me",{headers:authHeaders()});const d=await r.json();player=d.player;accountUI();render();if(!player)msg("Connecte-toi avec Discord pour utiliser l'arbre de compétences.");}catch{msg("Serveur inaccessible.");}}
document.querySelectorAll(".skill-button").forEach(b=>b.onclick=async()=>{if(!player)return;const r=await fetch(API_URL+"/api/skills/"+b.dataset.skill,{method:"POST",headers:authHeaders()});const d=await r.json();if(!r.ok){msg(d.error||"Impossible.");return;}player=d.player;render();msg("🧠 Compétence améliorée !");});
load();

// Ceci est un commentaire sur une seule ligne
