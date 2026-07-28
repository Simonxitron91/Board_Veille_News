const DAYS = [
  {key:"lundi", num:"01", label:"Lun"},
  {key:"mardi", num:"02", label:"Mar"},
  {key:"mercredi", num:"03", label:"Mer"},
  {key:"jeudi", num:"04", label:"Jeu"},
  {key:"vendredi", num:"05", label:"Ven"},
  {key:"samedi", num:"06", label:"Sam"},
  {key:"dimanche", num:"07", label:"Dim"},
];

const CATEGORY_ORDER = ["geopolitique","politique","economie","science","ia","cyber"];
const CATEGORY_DOTS = {
  geopolitique:"var(--dot-geo)",
  politique:"var(--dot-pol)",
  economie:"var(--dot-eco)",
  science:"var(--dot-sci)",
  ia:"var(--dot-ia)",
  cyber:"var(--dot-cyber)"
};

// Fallback embarqué (utilisé si le fetch des fichiers data/*.json échoue,
// par ex. en aperçu local sans serveur). Reprend le contenu de data/dimanche.json.
const FALLBACK = {
  dimanche: {
    weekday:"dimanche",
    generated_at:"2026-07-26T10:00:00Z",
    categories:{
      ia:{label:"Intelligence Artificielle", items:[
        {title:"L'AI Act européen approche de son échéance du 2 août", summary:"Les entreprises qui n'ont pas engagé leur mise en conformité entrent dans une zone grise réglementaire, avec des sanctions pouvant atteindre 7% du chiffre d'affaires mondial.", source:"ia-info.fr", url:"https://www.ia-info.fr", date:"2026-07-26"},
        {title:"Licenciements tech liés à l'IA en hausse", summary:"Plusieurs grandes entreprises technologiques ont annoncé des vagues de licenciements cette année, l'automatisation par l'IA étant identifiée comme facteur déterminant.", source:"TechCrunch (via ia-insights)", url:"https://www.ia-insights.fr/actualites-ia/", date:"2026-07-26"}
      ]},
      cyber:{label:"Cybersécurité", items:[
        {title:"Extorsion automatisée et fuites de données en hausse", summary:"Plusieurs groupes automatisent l'analyse de données volées pour calculer des rançons ; une attaque autonome a également touché Hugging Face.", source:"ZATAZ", url:"https://www.zataz.com", date:"2026-07-24"}
      ]},
      economie:{label:"Économie & Marchés", items:[
        {title:"CAC 40 porté par Airbus, tensions sur le pétrole", summary:"Le CAC 40 enchaîne une troisième hausse, porté par Airbus et l'énergie, tandis que le Brent poursuit sa remontée et que les taux obligataires se tendent.", source:"Invesse", url:"https://invesse.fr", date:"2026-07-22"}
      ]},
      geopolitique:{label:"Géopolitique & Général", items:[
        {title:"Tensions au Proche-Orient et marchés de l'énergie", summary:"La reprise du conflit et les menaces d'escalade continuent d'alimenter la volatilité du prix du Brent.", source:"Proximité Courtage", url:"https://proximite-courtage.fr", date:"2026-07-22"}
      ]},
      science:{label:"Science", items:[]},
      politique:{label:"Politique", items:[]}
    },
    investissement:{
      signaux:[
        "Volatilité énergie/pétrole en hausse (tensions Proche-Orient)",
        "Secteur semi-conducteurs sous pression après une correction marquée",
        "Échéance réglementaire AI Act (2 août) à surveiller pour les valeurs tech IA européennes"
      ],
      framework:"Cadre d'analyse à moyen/long terme : privilégier la diversification sectorielle plutôt que le pari sur un seul acteur IA ; suivre les échéances réglementaires qui peuvent créer de la volatilité court-terme ; garder une exposition mesurée à l'énergie en période de tensions géopolitiques ; le dollar-cost averaging reste une approche disciplinée pour lisser la volatilité.",
      disclaimer:"Ceci est une synthèse d'information générale et non une recommandation personnalisée. Elle ne remplace pas l'avis d'un conseiller en investissement financier agréé."
    }
  }
};

function emptyDay(key){
  return {
    weekday:key, generated_at:null,
    categories:{
      geopolitique:{label:"Géopolitique & Général", items:[]},
      politique:{label:"Politique", items:[]},
      economie:{label:"Économie & Marchés", items:[]},
      science:{label:"Science", items:[]},
      ia:{label:"Intelligence Artificielle", items:[]},
      cyber:{label:"Cybersécurité", items:[]}
    },
    investissement:{signaux:[], framework:"En attente de la première exécution automatique.", disclaimer:"Ceci est une synthèse d'information générale et non une recommandation personnalisée."}
  };
}

function todayKey(){
  const idx = new Date().getDay(); // 0=dimanche
  const map = ["dimanche","lundi","mardi","mercredi","jeudi","vendredi","samedi"];
  return map[idx];
}

async function loadDay(key){
  try{
    const res = await fetch(`data/${key}.json`, {cache:"no-store"});
    if(!res.ok) throw new Error("not ok");
    return await res.json();
  }catch(e){
    return FALLBACK[key] || emptyDay(key);
  }
}

function fmtDate(iso){
  if(!iso) return "pas encore de données";
  const d = new Date(iso);
  return d.toLocaleString("fr-FR", {day:"2-digit", month:"2-digit", year:"numeric", hour:"2-digit", minute:"2-digit"});
}

function renderTicker(data){
  const el = document.getElementById("ticker");
  el.innerHTML = "";
  CATEGORY_ORDER.forEach(cat=>{
    const c = data.categories[cat];
    if(!c) return;
    const chip = document.createElement("div");
    chip.className = "ticker-chip";
    chip.innerHTML = `<span class="dot" style="background:${CATEGORY_DOTS[cat]}"></span>${c.label} · ${c.items.length}`;
    el.appendChild(chip);
  });
}

function renderCategories(data){
  const wrap = document.getElementById("categories");
  wrap.innerHTML = "";
  CATEGORY_ORDER.forEach(cat=>{
    const c = data.categories[cat];
    if(!c) return;
    const sec = document.createElement("section");
    sec.className = "category";
    const head = document.createElement("div");
    head.className = "category-head";
    head.innerHTML = `<span class="dot" style="background:${CATEGORY_DOTS[cat]}"></span>
      <h2>${c.label}</h2><span class="category-count mono">${c.items.length} signal${c.items.length>1?"aux":""}</span>`;
    sec.appendChild(head);

    if(c.items.length === 0){
      const p = document.createElement("p");
      p.className = "empty-note";
      p.textContent = "Aucun signal collecté pour cette catégorie ce jour-là.";
      sec.appendChild(p);
    } else {
      c.items.forEach(item=>{
        const div = document.createElement("div");
        div.className = "item";
        div.innerHTML = `
          <p class="item-title">${item.title}</p>
          <div class="item-meta">${item.source} · ${item.date}</div>
          <div class="item-summary">${item.summary} <br><a href="${item.url}" target="_blank" rel="noopener">Lire la source →</a></div>
        `;
        div.addEventListener("click", ()=> div.classList.toggle("open"));
        sec.appendChild(div);
      });
    }
    wrap.appendChild(sec);
  });
}

function renderInvest(data){
  const inv = data.investissement || {signaux:[], framework:"", disclaimer:""};
  const ul = document.getElementById("invest-signals");
  ul.innerHTML = "";
  if(inv.signaux.length === 0){
    ul.innerHTML = `<li>Pas encore de signaux agrégés pour ce jour.</li>`;
  } else {
    inv.signaux.forEach(s=>{
      const li = document.createElement("li");
      li.textContent = s;
      ul.appendChild(li);
    });
  }
  document.getElementById("invest-framework").textContent = inv.framework;
  document.getElementById("invest-disclaimer").textContent = inv.disclaimer;
}

async function renderDay(key){
  const data = await loadDay(key);
  document.getElementById("updated-badge").textContent = fmtDate(data.generated_at);
  document.getElementById("updated-line").textContent = `Dernière mise à jour de l'onglet "${key}" : ${fmtDate(data.generated_at)}`;
  renderTicker(data);
  renderCategories(data);
  renderInvest(data);
}

function buildRail(){
  const rail = document.getElementById("day-rail");
  const today = todayKey();
  DAYS.forEach(d=>{
    const btn = document.createElement("button");
    btn.className = "day-tab" + (d.key===today ? " today" : "");
    btn.dataset.key = d.key;
    btn.innerHTML = `<span class="num">${d.num}</span>${d.label}`;
    btn.addEventListener("click", ()=>{
      document.querySelectorAll(".day-tab").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active");
      renderDay(d.key);
    });
    rail.appendChild(btn);
  });
  // active by default: today
  const defaultBtn = rail.querySelector(`[data-key="${today}"]`) || rail.firstChild;
  defaultBtn.classList.add("active");
  renderDay(defaultBtn.dataset.key);
}

buildRail();
