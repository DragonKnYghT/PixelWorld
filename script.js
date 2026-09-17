// En production, remplace cette URL par l'adresse publique de ton backend.
const API_URL = "https://pixelworld-0wr6.onrender.com";
const SIZE = 100;
const COOLDOWN = 60;
const COLORS = ["#000000","#ffffff","#ff3b30","#ff9500","#ffcc00","#34c759","#00c7be","#007aff","#5856d6","#af52de","#ff2d55","#8e8e93"];

const canvas=document.getElementById("canvas"), wrapper=document.getElementById("mapWrapper"), ctx=canvas.getContext("2d");
const palette=document.getElementById("palette"), paletteSide=document.getElementById("paletteSide");
const usernameInput=document.getElementById("username"), cooldownEl=document.getElementById("cooldown");
const pixelCountEl=document.getElementById("pixelCount"), playerDisplay=document.getElementById("playerDisplay");
const messageEl=document.getElementById("message"), connectionDot=document.getElementById("connectionDot"), connectionText=document.getElementById("connectionText");

let pixels=new Map(), selectedColor=COLORS[2], zoom=1, offsetX=0, offsetY=0, dragging=false, moved=false, lastX=0, lastY=0, cooldownUntil=0;

function showMessage(text){
  messageEl.textContent=text; messageEl.classList.add("show");
  clearTimeout(showMessage.timer); showMessage.timer=setTimeout(()=>messageEl.classList.remove("show"),2200);
}
function getUsername(){return usernameInput.value.trim().slice(0,20)||"Anonyme"}

function createPalette(container){
  COLORS.forEach(color=>{
    const b=document.createElement("button"); b.type="button"; b.className="color";
    b.style.background=color; b.title=color; b.setAttribute("aria-label","Couleur "+color);
    if(color===selectedColor)b.classList.add("selected");
    b.addEventListener("click",()=>{
      selectedColor=color;
      document.querySelectorAll(".color").forEach(x=>x.classList.remove("selected"));
      document.querySelectorAll(".color").forEach(x=>{if(x.title===color)x.classList.add("selected")});
    });
    container.appendChild(b);
  });
}
createPalette(palette); createPalette(paletteSide);

usernameInput.value=localStorage.getItem("pixelworld_username")||"";
usernameInput.addEventListener("input",()=>{
  localStorage.setItem("pixelworld_username",getUsername());
  playerDisplay.textContent=getUsername();
});
playerDisplay.textContent=getUsername();

function resizeCanvas(){
  const r=wrapper.getBoundingClientRect(), dpr=Math.min(devicePixelRatio||1,2);
  canvas.width=Math.floor(r.width*dpr); canvas.height=Math.floor(r.height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0); draw();
}
function cellSize(){return Math.max(2,5*zoom)}
function fitGrid(){
  const r=wrapper.getBoundingClientRect(); zoom=1;
  offsetX=(r.width-SIZE*cellSize())/2; offsetY=(r.height-SIZE*cellSize())/2; draw();
}
function draw(){
  const r=wrapper.getBoundingClientRect(),w=r.width,h=r.height,s=cellSize();
  ctx.clearRect(0,0,w,h); ctx.fillStyle="#08090d"; ctx.fillRect(0,0,w,h);
  ctx.fillStyle="#1a1c24";
  for(let y=0;y<=SIZE;y++){const py=offsetY+y*s;if(py>=0&&py<=h)ctx.fillRect(offsetX,py,SIZE*s,1)}
  for(let x=0;x<=SIZE;x++){const px=offsetX+x*s;if(px>=0&&px<=w)ctx.fillRect(px,offsetY,1,SIZE*s)}
  for(const [key,color] of pixels){
    const [x,y]=key.split(",").map(Number),px=offsetX+x*s,py=offsetY+y*s;
    if(px+s<0||py+s<0||px>w||py>h)continue;
    ctx.fillStyle=color;ctx.fillRect(px+1,py+1,Math.max(1,s-1),Math.max(1,s-1));
  }
}
function screenToCell(clientX,clientY){
  const r=canvas.getBoundingClientRect(),x=Math.floor((clientX-r.left-offsetX)/cellSize()),y=Math.floor((clientY-r.top-offsetY)/cellSize());
  return x>=0&&y>=0&&x<SIZE&&y<SIZE?{x,y}:null;
}

async function loadPixels(){
  try{
    const res=await fetch(API_URL+"/api/pixels"); if(!res.ok)throw Error();
    const data=await res.json(); pixels=new Map();
    data.pixels.forEach(p=>pixels.set(p.x+","+p.y,p.color));
    pixelCountEl.textContent=pixels.size;
    connectionDot.style.background="#34c759"; connectionText.textContent="Connecté"; draw();
  }catch{
    connectionDot.style.background="#ff3b30"; connectionText.textContent="Serveur inaccessible";
  }
}
async function placePixel(x,y){
  const remaining=Math.ceil((cooldownUntil-Date.now())/1000);
  if(remaining>0){showMessage("Attends encore "+remaining+"s.");return}
  try{
    const res=await fetch(API_URL+"/api/pixels",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({x,y,color:selectedColor,username:getUsername()})});
    const data=await res.json();
    if(!res.ok){if(data.cooldown)cooldownUntil=Date.now()+data.cooldown*1000;showMessage(data.error||"Impossible.");return}
    pixels.set(x+","+y,selectedColor); pixelCountEl.textContent=pixels.size;
    cooldownUntil=Date.now()+COOLDOWN*1000; draw(); showMessage("Pixel posé en "+x+", "+y+" !");
  }catch{showMessage("Impossible de contacter le serveur.")}
}

canvas.addEventListener("pointerdown",e=>{dragging=true;moved=false;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener("pointermove",e=>{
  const cell=screenToCell(e.clientX,e.clientY);
  if(cell)document.getElementById("coordinates").textContent="X: "+cell.x+", Y: "+cell.y;
  if(!dragging)return;
  const dx=e.clientX-lastX,dy=e.clientY-lastY;
  if(Math.abs(dx)+Math.abs(dy)>2)moved=true;
  offsetX+=dx;offsetY+=dy;lastX=e.clientX;lastY=e.clientY;draw();
});
canvas.addEventListener("pointerup",e=>{
  if(!dragging)return;dragging=false;
  if(!moved){const cell=screenToCell(e.clientX,e.clientY);if(cell)placePixel(cell.x,cell.y)}
});
canvas.addEventListener("wheel",e=>{
  e.preventDefault(); const old=cellSize(),r=canvas.getBoundingClientRect();
  const mx=e.clientX-r.left,my=e.clientY-r.top,wx=(mx-offsetX)/old,wy=(my-offsetY)/old;
  zoom*=e.deltaY<0?1.18:.85;zoom=Math.max(.5,Math.min(12,zoom));
  const n=cellSize();offsetX=mx-wx*n;offsetY=my-wy*n;draw();
},{passive:false});

document.getElementById("resetView").addEventListener("click",fitGrid);
function updateCooldown(){const s=Math.ceil((cooldownUntil-Date.now())/1000);cooldownEl.textContent=s<=0?"Disponible":s+"s"}
setInterval(updateCooldown,250); setInterval(loadPixels,3000);
window.addEventListener("resize",resizeCanvas); resizeCanvas(); fitGrid(); loadPixels();
