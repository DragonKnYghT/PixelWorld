const API_URL="https://pixelworld-0wr6.onrender.com";
let authToken = localStorage.getItem("pixelworld_token") || "";
if (location.hash.startsWith("#token=")) { authToken = decodeURIComponent(location.hash.slice(7)); localStorage.setItem("pixelworld_token", authToken); history.replaceState(null, "", location.pathname + location.search); }
function authHeaders(extra={}) { return authToken ? {...extra, Authorization: "Bearer " + authToken} : extra; }
const SIZE = 5000;
const COLORS = [
  "#000000","#ffffff","#ff3b30","#ff9500","#ffcc00","#34c759",
  "#00c7be","#007aff","#5856d6","#af52de","#ff2d55","#8e8e93",
  "#5ac8fa","#30d158","#64d2ff","#ffd60a","#ff9f0a","#ff375f",
  "#bf5af2","#ac8e68","#a2845e","#636366","#2c2c2e","#d1d1d6"
];

const canvas=document.getElementById("canvas"), wrapper=document.getElementById("mapWrapper"), ctx=canvas.getContext("2d");
const palette=document.getElementById("palette"), paletteSide=document.getElementById("paletteSide");
const balanceEl=document.getElementById("pixelBalance"), maxEl=document.getElementById("pixelMax"), rechargeEl=document.getElementById("rechargeText");
const pixelCountEl=document.getElementById("pixelCount"), playerDisplay=document.getElementById("playerDisplay"), playerDisplaySide=document.getElementById("playerDisplaySide");
const totalPlacedEl=document.getElementById("totalPlaced"), messageEl=document.getElementById("message"), pixelInfo=document.getElementById("pixelInfo");
const connectionDot=document.getElementById("connectionDot"), connectionText=document.getElementById("connectionText"), accountArea=document.getElementById("accountArea");

let pixels=new Map(), selectedColor=COLORS[2], zoom=0.28, offsetX=0, offsetY=0, dragging=false, moved=false, lastX=0, lastY=0;
let player=null, rechargeAt=0, rechargeSeconds=60;

function showMessage(text){ messageEl.textContent=text; messageEl.classList.add("show"); clearTimeout(showMessage.timer); showMessage.timer=setTimeout(()=>messageEl.classList.remove("show"),2600); }
function createPalette(container){ COLORS.forEach(color=>{ const b=document.createElement("button"); b.type="button"; b.className="color"; b.style.background=color; b.title=color; b.setAttribute("aria-label","Couleur "+color); if(color===selectedColor)b.classList.add("selected"); b.addEventListener("click",()=>{selectedColor=color;document.querySelectorAll(".color").forEach(x=>x.classList.toggle("selected",x.title===color));}); container.appendChild(b); }); }
createPalette(palette); createPalette(paletteSide);

function accountUI(){
  if(player){
    accountArea.innerHTML=`<span class="account-name">🎮 ${escapeHtml(player.username)}</span><button class="top-button" id="logoutBtn">Déconnexion</button>`;
    document.getElementById("logoutBtn").onclick=async()=>{await fetch(API_URL+"/auth/logout",{method:"POST",headers:authHeaders()});localStorage.removeItem("pixelworld_token");location.reload();};
    playerDisplay.textContent=player.username; playerDisplaySide.textContent=player.username;
  }else{
    accountArea.innerHTML=`<a class="discord-button" href="${API_URL}/auth/discord">🔵 Se connecter avec Discord</a>`;
    playerDisplay.textContent="Non connecté"; playerDisplaySide.textContent="-";
  }
}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));}

function resizeCanvas(){ const r=wrapper.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2); canvas.width=Math.floor(r.width*dpr);canvas.height=Math.floor(r.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw(); }
function cellSize(){return Math.max(.45,zoom);}
function fitGrid(){ const r=wrapper.getBoundingClientRect(); zoom=Math.min(r.width/SIZE,r.height/SIZE)*0.96; zoom=Math.max(.45,Math.min(20,zoom)); offsetX=(r.width-SIZE*zoom)/2; offsetY=(r.height-SIZE*zoom)/2; draw(); }
function draw(){
  const r=wrapper.getBoundingClientRect(),w=r.width,h=r.height,s=cellSize();
  ctx.clearRect(0,0,w,h);ctx.fillStyle="#07080c";ctx.fillRect(0,0,w,h);
  const minX=Math.max(0,Math.floor((-offsetX)/s)-1),maxX=Math.min(SIZE,Math.ceil((w-offsetX)/s)+1);
  const minY=Math.max(0,Math.floor((-offsetY)/s)-1),maxY=Math.min(SIZE,Math.ceil((h-offsetY)/s)+1);
  if(s>=5){
    ctx.fillStyle="#191c25";
    for(let y=minY;y<=maxY;y++){const py=offsetY+y*s;ctx.fillRect(0,Math.round(py),w,1);}
    for(let x=minX;x<=maxX;x++){const px=offsetX+x*s;ctx.fillRect(Math.round(px),0,1,h);}
  }
  for(const [key,p] of pixels){
    const [x,y]=key.split(",").map(Number),px=offsetX+x*s,py=offsetY+y*s;
    if(px+s<0||py+s<0||px>w||py>h)continue;
    ctx.fillStyle=p.color;ctx.fillRect(px,py,Math.max(1,s+.15),Math.max(1,s+.15));
  }
ctx.strokeStyle = "#3b3f50";
ctx.lineWidth = 4;
ctx.strokeRect(offsetX, offsetY, SIZE * s, SIZE * s);
}

function screenToCell(clientX,clientY){const r=canvas.getBoundingClientRect(),s=cellSize();const x=Math.floor((clientX-r.left-offsetX)/s),y=Math.floor((clientY-r.top-offsetY)/s);return x>=0&&y>=0&&x<SIZE&&y<SIZE?{x,y}:null;}

async function loadPixels(){
  try{const res=await fetch(API_URL+"/api/pixels");if(!res.ok)throw Error();const data=await res.json();pixels=new Map();data.pixels.forEach(p=>pixels.set(p.x+","+p.y,p));pixelCountEl.textContent=pixels.size;connectionDot.style.background="#34c759";connectionText.textContent="Connecté";draw();}
  catch{connectionDot.style.background="#ff3b30";connectionText.textContent="Serveur inaccessible";}
}
async function loadMe(){
  try{const res=await fetch(API_URL+"/api/me",{headers:authHeaders()});const data=await res.json();player=data.player;accountUI();if(player){balanceEl.textContent=player.pixel_balance;maxEl.textContent=player.max_storage;totalPlacedEl.textContent=player.total_placed;rechargeSeconds=player.recharge_seconds;rechargeAt=Date.now()+Math.max(0, rechargeSeconds*1000);}
  }catch{player=null;accountUI();}
}
function updateCharge(){
  if(!player){balanceEl.textContent="0";maxEl.textContent="20";rechargeEl.textContent="Connexion requise";return;}
  const current=Math.min(player.max_storage,player.pixel_balance+Math.floor(Math.max(0,Date.now()-rechargeAt)/1000/rechargeSeconds));
  balanceEl.textContent=current;
  if(current>=player.max_storage){rechargeEl.textContent="Stockage plein";}
  else{const seconds=Math.max(0,rechargeSeconds-Math.floor(Math.max(0,Date.now()-rechargeAt)/1000)%rechargeSeconds);rechargeEl.textContent="+1 charge dans "+seconds+"s";}
}
async function placePixel(x,y){
  if(!player){showMessage("Connecte-toi avec Discord pour poser un pixel.");return;}
  try{
    const res=await fetch(API_URL+"/api/pixels",{method:"POST",headers:authHeaders({"Content-Type":"application/json"}),body:JSON.stringify({x,y,color:selectedColor})});
    const data=await res.json();
    if(!res.ok){showMessage(data.error||"Impossible.");if(data.login_required)accountUI();return;}
    pixels.set(x+","+y,{x,y,color:selectedColor,username:player.username,updated_at:new Date().toISOString()});
    player=data.player;balanceEl.textContent=player.pixel_balance;maxEl.textContent=player.max_storage;totalPlacedEl.textContent=player.total_placed;rechargeSeconds=player.recharge_seconds;rechargeAt=Date.now();draw();
    showMessage(data.critical?"✨ Pixel critique ! Aucun pixel consommé.":`Pixel posé en ${x}, ${y} !`); beep(data.critical?880:520,0.09);
  }catch{showMessage("Impossible de contacter le serveur.");}
}
function showPixelInfo(cell){const p=pixels.get(cell.x+","+cell.y);if(p){const date=new Date(p.updated_at);pixelInfo.innerHTML=`<b>Pixel ${cell.x}, ${cell.y}</b><br>🎨 ${escapeHtml(p.color)}<br>👤 ${escapeHtml(p.username)}<br>🕒 ${date.toLocaleString("fr-FR")}`;}else pixelInfo.textContent=`Pixel ${cell.x}, ${cell.y} • Vide`;
}
function beep(freq=520,duration=.08){try{const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;const a=new AC(),o=a.createOscillator(),g=a.createGain();o.frequency.value=freq;o.type="sine";g.gain.setValueAtTime(.035,a.currentTime);g.gain.exponentialRampToValueAtTime(.0001,a.currentTime+duration);o.connect(g);g.connect(a.destination);o.start();o.stop(a.currentTime+duration);setTimeout(()=>a.close(),duration*1000+80);}catch{}}
let wasFull=false;
function chargeSound(){if(!player)return;const full=Number(balanceEl.textContent)>=player.max_storage;if(full&&!wasFull)beep(1046,.14);wasFull=full;}

canvas.addEventListener("pointerdown",e=>{dragging=true;moved=false;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener("pointermove",e=>{const cell=screenToCell(e.clientX,e.clientY);if(cell){document.getElementById("coordinates").textContent="X: "+cell.x+", Y: "+cell.y;showPixelInfo(cell);}if(!dragging)return;const dx=e.clientX-lastX,dy=e.clientY-lastY;if(Math.abs(dx)+Math.abs(dy)>2)moved=true;offsetX+=dx;offsetY+=dy;lastX=e.clientX;lastY=e.clientY;draw();});
canvas.addEventListener("pointerup",e=>{if(!dragging)return;dragging=false;if(!moved){const cell=screenToCell(e.clientX,e.clientY);if(cell)placePixel(cell.x,cell.y);}});
canvas.addEventListener("wheel",e=>{e.preventDefault();const old=cellSize(),r=canvas.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,wx=(mx-offsetX)/old,wy=(my-offsetY)/old;zoom*=e.deltaY<0?1.18:.85;zoom=Math.max(.45,Math.min(20,zoom));const n=cellSize();offsetX=mx-wx*n;offsetY=my-wy*n;draw();},{passive:false});
document.getElementById("resetView").addEventListener("click",fitGrid);
setInterval(updateCharge,250);setInterval(chargeSound,1000);setInterval(loadPixels,5000);setInterval(loadMe,10000);window.addEventListener("resize",resizeCanvas);
resizeCanvas();fitGrid();loadMe();loadPixels();
