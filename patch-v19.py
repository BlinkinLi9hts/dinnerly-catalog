"""Run this once: python patch-v19.py  — then delete it."""
src = open("index.html", encoding="utf-8").read()

# ── 1. Version bump ──────────────────────────────────────────────────────────
src = src.replace("v1.8", "v1.9")

# ── 2. Category system — insert after compressImage function ─────────────────
CAT_CODE = '''
// ── Category system ───────────────────────────────────────────────────────────
const CATEGORIES = [
  { id:"beef",    label:"Beef",    emoji:"\\u{1F969}", keywords:["beef","steak","burger","brisket","meatball","bolognese","ground beef","sirloin","ribeye","chuck"] },
  { id:"chicken", label:"Chicken", emoji:"\\u{1F357}", keywords:["chicken","poultry"] },
  { id:"pork",    label:"Pork",    emoji:"\\u{1F437}", keywords:["pork","bacon","ham","sausage","chorizo","pancetta","prosciutto","ribs"] },
  { id:"seafood", label:"Seafood", emoji:"\\u{1F990}", keywords:["shrimp","salmon","fish","tilapia","cod","tuna","scallop","lobster","crab","halibut","mahi","catfish","trout"] },
  { id:"lamb",    label:"Lamb",    emoji:"\\u{1F411}", keywords:["lamb","mutton"] },
  { id:"pasta",   label:"Pasta",   emoji:"\\u{1F35D}", keywords:["pasta","linguine","spaghetti","penne","rigatoni","fettuccine","macaroni","noodle","ramen","gnocchi","lasagna","ravioli"] },
  { id:"veggie",  label:"Veggie",  emoji:"\\u{1F331}", keywords:["tofu","vegetarian","veggie","lentil","chickpea","falafel","tempeh","cauliflower"] },
  { id:"eggs",    label:"Eggs",    emoji:"\\u{1F95A}", keywords:["egg","frittata","omelette","quiche","shakshuka"] },
  { id:"other",   label:"Other",   emoji:"\\u{1F37D}\\uFE0F", keywords:[] },
];

function detectCategory(title, saved) {
  if (saved && saved !== "other") return saved;
  const t = (title||"").toLowerCase();
  for (const cat of CATEGORIES) {
    if (cat.id === "other") continue;
    if (cat.keywords.some(k => t.includes(k))) return cat.id;
  }
  return "other";
}
function getCategoryInfo(id) { return CATEGORIES.find(c => c.id===id) || CATEGORIES[CATEGORIES.length-1]; }

'''

assert "function imgBlock(base64, mediaType) {" in src
src = src.replace("function imgBlock(base64, mediaType) {", CAT_CODE + "function imgBlock(base64, mediaType) {", 1)

# ── 3. CategoryScreen + RecipeListScreen — insert before LibraryScreen ────────
SCREENS = '''
// ── Category Landing ──────────────────────────────────────────────────────────
function CategoryScreen({ recipes, onSelectCategory, onAdd, onSettings }) {
  const counts = {};
  recipes.forEach(r => { const c=detectCategory(r.title,r.category); counts[c]=(counts[c]||0)+1; });
  const active = CATEGORIES.filter(c => counts[c.id]>0);
  const C2 = { ink:"#1C1C1E", paper:"#F5F2ED", card:"#FFFFFF", sage:"#4A7C59", sageDark:"#3A6147", sageMid:"#7AAE8A", sageLight:"#EBF2ED", orange:"#D9622B", muted:"#8A8A8E", border:"#E0DDD6" };
  return (
    <div style={{...base,minHeight:"100vh",background:C2.paper}}>
      <div style={{background:C2.sage,padding:"28px 28px 24px",display:"flex",alignItems:"flex-start",justifyContent:"space-between"}}>
        <div>
          <div style={{fontSize:28,fontWeight:700,color:"#fff",letterSpacing:"-0.5px"}}>Dinnerly</div>
          <div style={{fontSize:15,color:"rgba(255,255,255,0.85)",marginTop:6,fontStyle:"italic"}}>What are we cooking tonight?</div>
        </div>
        <div style={{display:"flex",gap:10,marginTop:4}}>
          <button onClick={onSettings} style={{...btnD,padding:"8px 12px",fontSize:18}}>&#9881;&#65039;</button>
          <button onClick={onAdd} style={{...btnP,background:C2.orange,display:"flex",alignItems:"center",gap:8,fontSize:14}}>
            <span style={{fontSize:18}}>&#65291;</span> Scan
          </button>
        </div>
      </div>
      <div style={{maxWidth:900,margin:"0 auto",padding:"32px 24px"}}>
        {recipes.length===0 ? (
          <div style={{textAlign:"center",padding:"80px 0",color:C2.muted}}>
            <div style={{fontSize:52,marginBottom:16}}>&#127859;</div>
            <div style={{fontSize:20,fontWeight:700,color:C2.ink,marginBottom:8}}>Your catalog is empty</div>
            <div style={{fontSize:15}}>Tap Scan to add your first Dinnerly recipe.</div>
          </div>
        ) : (
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))",gap:16}}>
            {active.map(cat=>(
              <button key={cat.id} onClick={()=>onSelectCategory(cat.id)} style={{...base,background:C2.card,border:`1.5px solid ${C2.border}`,borderRadius:16,padding:"28px 16px",cursor:"pointer",textAlign:"center",boxShadow:"0 2px 8px rgba(0,0,0,0.05)",transition:"all 0.18s",display:"flex",flexDirection:"column",alignItems:"center",gap:10}}>
                <span style={{fontSize:48}}>{cat.emoji}</span>
                <div style={{fontSize:17,fontWeight:700,color:C2.ink}}>{cat.label}</div>
                <div style={{fontSize:12,color:C2.sageDark,background:C2.sageLight,borderRadius:20,padding:"3px 12px",fontWeight:600}}>
                  {counts[cat.id]} recipe{counts[cat.id]!==1?"s":""}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Recipe List Screen ────────────────────────────────────────────────────────
function RecipeListScreen({ recipes, categoryId, onBack, onSelect, onDelete, onAdd }) {
  const cat = getCategoryInfo(categoryId);
  const filtered = recipes.filter(r=>detectCategory(r.title,r.category)===categoryId);
  return (
    <div style={{...base,minHeight:"100vh",background:C.paper}}>
      <div style={{background:C.sage,padding:"18px 24px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
        <button onClick={onBack} style={{...btnG,color:"rgba(255,255,255,0.8)",borderColor:"rgba(255,255,255,0.3)",padding:"7px 14px",fontSize:13}}>&#8592; Back</button>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <span style={{fontSize:22}}>{cat.emoji}</span>
          <span style={{color:"#fff",fontWeight:700,fontSize:18}}>{cat.label}</span>
        </div>
        <button onClick={onAdd} style={{...btnP,background:C.orange,padding:"8px 14px",fontSize:13}}>&#65291; Scan</button>
      </div>
      <div style={{maxWidth:900,margin:"0 auto",padding:"28px 24px"}}>
        {filtered.length===0 ? (
          <div style={{textAlign:"center",padding:"60px 0",color:C.muted}}><div style={{fontSize:15}}>No recipes in this category yet.</div></div>
        ) : (
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(250px,1fr))",gap:20}}>
            {filtered.map(r=><LibraryCard key={r.id} recipe={r} onSelect={()=>onSelect(r)} onDelete={()=>onDelete(r.id)}/>)}
          </div>
        )}
      </div>
    </div>
  );
}

'''

assert "function LibraryScreen(" in src
src = src.replace("function LibraryScreen(", SCREENS + "function LibraryScreen(", 1)

# ── 4. CategoryPicker modal + update DetailScreen signature ──────────────────
CAT_PICKER = '''
// ── Category Picker Modal ─────────────────────────────────────────────────────
function CategoryPicker({ current, onSelect, onClose }) {
  return (
    <div style={{position:"fixed",inset:0,zIndex:300,background:"rgba(10,10,10,0.6)",display:"flex",alignItems:"center",justifyContent:"center",padding:20}}>
      <div style={{background:"#fff",borderRadius:16,width:"100%",maxWidth:400,overflow:"hidden",boxShadow:"0 16px 60px rgba(0,0,0,0.3)"}}>
        <div style={{background:C.sage,padding:"16px 20px",color:"#fff",fontWeight:700,fontSize:17}}>Change Category</div>
        <div style={{padding:"8px 0",maxHeight:"60vh",overflowY:"auto"}}>
          {CATEGORIES.map(cat=>(
            <div key={cat.id} onClick={()=>onSelect(cat.id)} style={{display:"flex",alignItems:"center",gap:14,padding:"14px 20px",cursor:"pointer",background:cat.id===current?C.sageLight:"#fff",borderLeft:cat.id===current?`3px solid ${C.sage}`:"3px solid transparent",transition:"background 0.15s"}}>
              <span style={{fontSize:24}}>{cat.emoji}</span>
              <span style={{fontSize:16,fontWeight:cat.id===current?700:400,color:C.ink}}>{cat.label}</span>
              {cat.id===current&&<span style={{marginLeft:"auto",color:C.sage,fontWeight:700}}>&#10003;</span>}
            </div>
          ))}
        </div>
        <div style={{padding:"12px 20px",borderTop:`1px solid ${C.border}`}}>
          <button onClick={onClose} style={{...btnG,width:"100%",padding:"10px"}}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

'''

assert "function DetailScreen({ recipe, onBack, onCook, onUpdatePhoto }) {" in src, "DetailScreen sig not found"
src = src.replace(
    "function DetailScreen({ recipe, onBack, onCook, onUpdatePhoto }) {",
    CAT_PICKER + "function DetailScreen({ recipe, onBack, onCook, onUpdatePhoto, onUpdateCategory }) {",
    1
)

# ── 5. Add category state + picker to DetailScreen body ──────────────────────
assert "  const [photoHover, setPhotoHover] = useState(false);" in src
src = src.replace(
    "  const [photoHover, setPhotoHover] = useState(false);",
    "  const [photoHover, setPhotoHover] = useState(false);\n  const [showCatPicker, setShowCatPicker] = useState(false);\n  const currentCat = getCategoryInfo(detectCategory(recipe.title, recipe.category));",
    1
)

# ── 6. Add category pill after TopBar ────────────────────────────────────────
old_topbar = "      <TopBar onBack={onBack} title={recipe.title}\n        right={<button onClick={()=>setShowChecklist(true)} style={{...btnP,background:C.orange,padding:\"8px 18px\",fontSize:14}}>Cook \u2192</button>}/>"
new_topbar = old_topbar + """
      <div style={{background:C.sageLight,padding:"8px 24px",display:"flex",alignItems:"center",gap:8}}>
        <span style={{fontSize:16}}>{currentCat.emoji}</span>
        <span style={{fontSize:13,color:C.sageDark,fontWeight:600}}>{currentCat.label}</span>
        <button onClick={()=>setShowCatPicker(true)} style={{...base,marginLeft:4,background:"none",border:`1px solid ${C.sageMid}`,borderRadius:6,padding:"2px 10px",fontSize:12,color:C.sage,cursor:"pointer"}}>Change</button>
      </div>"""
assert old_topbar in src, "TopBar line not found"
src = src.replace(old_topbar, new_topbar, 1)

# ── 7. Add CategoryPicker render + close to DetailScreen return ───────────────
old_end = "      {showChecklist&&<IngredientChecklist ingredients={scaledIng} onDone={handleChecklistDone}/>}\n    </div>\n  );\n}\n\nfunction CookScreen"
new_end = "      {showChecklist&&<IngredientChecklist ingredients={scaledIng} onDone={handleChecklistDone}/>}\n      {showCatPicker&&<CategoryPicker current={detectCategory(recipe.title,recipe.category)} onSelect={id=>{onUpdateCategory(recipe.id,id);setShowCatPicker(false);}} onClose={()=>setShowCatPicker(false)}/>}\n    </div>\n  );\n}\n\nfunction CookScreen"
assert old_end in src, "DetailScreen end not found"
src = src.replace(old_end, new_end, 1)

# ── 8. Update App state + routing ────────────────────────────────────────────
assert 'const [screen, setScreen] = useState("library");' in src
src = src.replace(
    'const [screen, setScreen] = useState("library");',
    'const [screen, setScreen] = useState("categories");\n  const [activeCategory, setActiveCategory] = useState(null);',
    1
)

# back button routing
assert 'if (screen === "detail") { setScreen("library"); return; }' in src
src = src.replace(
    'if (screen === "detail") { setScreen("library"); return; }\n      if (screen === "scan") { setScreen("library"); return; }',
    'if (screen === "detail") { setScreen("recipelist"); return; }\n      if (screen === "recipelist") { setScreen("categories"); return; }\n      if (screen === "scan") { setScreen(activeCategory?"recipelist":"categories"); return; }',
    1
)

# handleSaved
assert 'const handleSaved = r => { const next=[r,...recipes]; setRecipes(next); saveRecipes(next); setScreen("library"); };' in src
src = src.replace(
    'const handleSaved = r => { const next=[r,...recipes]; setRecipes(next); saveRecipes(next); setScreen("library"); };',
    'const handleSaved = r => { const next=[r,...recipes]; setRecipes(next); saveRecipes(next); setScreen(activeCategory?"recipelist":"categories"); };\n  const handleUpdateCategory = (id, catId) => {\n    const next = recipes.map(r => r.id===id ? {...r, category:catId} : r);\n    setRecipes(next); saveRecipes(next);\n    if (active?.recipe?.id===id) setActive(prev=>({...prev,recipe:{...prev.recipe,category:catId}}));\n  };',
    1
)

# scan back
assert 'if (screen==="scan") return <ScanScreen onBack={()=>setScreen("library")} onSaved={handleSaved}/>;' in src
src = src.replace(
    'if (screen==="scan") return <ScanScreen onBack={()=>setScreen("library")} onSaved={handleSaved}/>;',
    'if (screen==="scan") return <ScanScreen onBack={()=>setScreen(activeCategory?"recipelist":"categories")} onSaved={handleSaved}/>;',
    1
)

# detail onBack + add onUpdateCategory
assert 'onCook={(recipe,guestCount,scaledIngredients)=>{ setActive({recipe,guestCount,scaledIngredients}); setScreen("cook"); }}/>' in src
src = src.replace(
    '    <DetailScreen recipe={active.recipe} onBack={()=>setScreen("library")}\n      onUpdatePhoto={handleUpdatePhoto}\n      onCook={(recipe,guestCount,scaledIngredients)=>{ setActive({recipe,guestCount,scaledIngredients}); setScreen("cook"); }}/>',
    '    <DetailScreen recipe={active.recipe} onBack={()=>setScreen("recipelist")}\n      onUpdatePhoto={handleUpdatePhoto}\n      onUpdateCategory={handleUpdateCategory}\n      onCook={(recipe,guestCount,scaledIngredients)=>{ setActive({recipe,guestCount,scaledIngredients}); setScreen("cook"); }}/>',
    1
)

# Add recipelist screen + replace CategoryScreen as home
old_return = '''  return (
    <>
      <LibraryScreen recipes={recipes} onAdd={()=>setScreen("scan")}
        onSelect={r=>{ setActive({recipe:r,guestCount:r.servings,scaledIngredients:r.ingredients}); setScreen("detail"); }}
        onDelete={handleDelete} onSettings={()=>setShowSettings(true)}/>'''
new_return = '''  if (screen==="recipelist"&&activeCategory) return (
    <RecipeListScreen recipes={recipes} categoryId={activeCategory}
      onBack={()=>setScreen("categories")}
      onSelect={r=>{ setActive({recipe:r,guestCount:r.servings,scaledIngredients:r.ingredients}); setScreen("detail"); }}
      onDelete={handleDelete}
      onAdd={()=>setScreen("scan")}/>
  );

  return (
    <>
      <CategoryScreen recipes={recipes} onAdd={()=>setScreen("scan")}
        onSelectCategory={id=>{ setActiveCategory(id); setScreen("recipelist"); }}
        onSettings={()=>setShowSettings(true)}/>'''
assert old_return in src, "Return block not found"
src = src.replace(old_return, new_return, 1)

open("index.html", "w", encoding="utf-8").write(src)
print("v1.9 written successfully!")
print("Lines:", src.count("\n"))
