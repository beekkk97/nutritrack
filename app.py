import streamlit as st
import requests
import random
import math
from datetime import date, datetime
import pandas as pd

st.set_page_config(
    page_title="NutriTrack",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = "https://world.openfoodfacts.org/api/v2/search"

# Curated fallback foods: used whenever API data are missing/invalid.
# Values are approximate per 100 g and are not intended as medical prescriptions.
FALLBACK_FOODS = {
    "protein": [
        {"product_name":"Gjoks pule, i pjekur","kcal":165,"protein":31.0,"carbs":0.0,"fat":3.6},
        {"product_name":"Gjoks gjeli, i pjekur","kcal":135,"protein":29.0,"carbs":0.0,"fat":1.6},
        {"product_name":"Ton në ujë, i kulluar","kcal":116,"protein":26.0,"carbs":0.0,"fat":1.0},
        {"product_name":"Salmon","kcal":208,"protein":20.0,"carbs":0.0,"fat":13.0},
        {"product_name":"Vezë","kcal":143,"protein":12.6,"carbs":0.7,"fat":9.5},
        {"product_name":"Kos grek","kcal":73,"protein":9.9,"carbs":3.9,"fat":2.0},
        {"product_name":"Mish viçi pa dhjamë","kcal":170,"protein":26.0,"carbs":0.0,"fat":7.0},
    ],
    "carb": [
        {"product_name":"Oriz i gatuar","kcal":130,"protein":2.7,"carbs":28.2,"fat":0.3},
        {"product_name":"Tërshërë","kcal":389,"protein":16.9,"carbs":66.3,"fat":6.9},
        {"product_name":"Patate të ziera","kcal":87,"protein":1.9,"carbs":20.1,"fat":0.1},
        {"product_name":"Makarona të gatuara","kcal":158,"protein":5.8,"carbs":30.9,"fat":0.9},
        {"product_name":"Bukë integrale","kcal":247,"protein":13.0,"carbs":41.0,"fat":4.2},
        {"product_name":"Quinoa e gatuar","kcal":120,"protein":4.4,"carbs":21.3,"fat":1.9},
    ],
    "vegetable": [
        {"product_name":"Brokoli","kcal":35,"protein":2.4,"carbs":7.2,"fat":0.4},
        {"product_name":"Domate","kcal":18,"protein":0.9,"carbs":3.9,"fat":0.2},
        {"product_name":"Karrota","kcal":41,"protein":0.9,"carbs":9.6,"fat":0.2},
        {"product_name":"Speca","kcal":31,"protein":1.0,"carbs":6.0,"fat":0.3},
        {"product_name":"Sallatë jeshile","kcal":15,"protein":1.4,"carbs":2.9,"fat":0.2},
        {"product_name":"Perime të përziera","kcal":55,"protein":3.0,"carbs":10.0,"fat":0.5},
    ],
    "fruit": [
        {"product_name":"Banane","kcal":89,"protein":1.1,"carbs":22.8,"fat":0.3},
        {"product_name":"Mollë","kcal":52,"protein":0.3,"carbs":13.8,"fat":0.2},
        {"product_name":"Portokall","kcal":47,"protein":0.9,"carbs":11.8,"fat":0.1},
        {"product_name":"Manaferra","kcal":43,"protein":1.4,"carbs":9.6,"fat":0.5},
    ],
    "fat": [
        {"product_name":"Vaj ulliri","kcal":884,"protein":0.0,"carbs":0.0,"fat":100.0},
        {"product_name":"Bajame","kcal":579,"protein":21.2,"carbs":21.6,"fat":49.9},
        {"product_name":"Arra","kcal":654,"protein":15.2,"carbs":13.7,"fat":65.2},
        {"product_name":"Avokado","kcal":160,"protein":2.0,"carbs":8.5,"fat":14.7},
        {"product_name":"Fara chia","kcal":486,"protein":16.5,"carbs":42.1,"fat":30.7},
    ],
}

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
    .hero {
        padding: 1.1rem 1.2rem; border-radius: 22px;
        background: linear-gradient(135deg, rgba(35, 35, 45, .95), rgba(70, 70, 85, .88));
        color: white; margin-bottom: 1rem;
    }
    .hero h1 {margin:0; font-size: 2rem;}
    .hero p {margin:.35rem 0 0; opacity:.82;}
    .card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 18px; padding: .85rem 1rem;
        background: rgba(128,128,128,.06);
        min-height: 95px;
    }
    .card .label {font-size:.78rem; opacity:.68;}
    .card .value {font-size:1.45rem; font-weight:750; margin-top:.15rem;}
    .card .sub {font-size:.76rem; opacity:.65;}
    .meal-card {
        border:1px solid rgba(128,128,128,.22); border-radius:18px;
        padding:1rem; margin:.55rem 0; background:rgba(128,128,128,.045);
    }
    .meal-title {font-size:1.05rem; font-weight:750;}
    .food-line {padding:.28rem 0; border-bottom:1px dashed rgba(128,128,128,.18);}
    .food-line:last-child {border-bottom:0;}
    .muted {opacity:.68;}
    .success-box {padding:.8rem 1rem; border-radius:15px; background:rgba(50,180,100,.10); border:1px solid rgba(50,180,100,.25);}
    .warn-box {padding:.8rem 1rem; border-radius:15px; background:rgba(240,170,30,.10); border:1px solid rgba(240,170,30,.28);}
    .danger-box {padding:.8rem 1rem; border-radius:15px; background:rgba(220,60,60,.10); border:1px solid rgba(220,60,60,.28);}
    div[data-testid="stMetric"] {padding:.35rem;}
    @media (max-width: 700px) {
        .block-container {padding-left:.8rem; padding-right:.8rem;}
        .hero h1 {font-size:1.55rem;}
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session state
# -----------------------------
if "weight_log" not in st.session_state:
    st.session_state.weight_log = []
if "plan" not in st.session_state:
    st.session_state.plan = None
if "last_inputs" not in st.session_state:
    st.session_state.last_inputs = {}
if "meal_seeds" not in st.session_state:
    st.session_state.meal_seeds = {}

# -----------------------------
# Utilities
# -----------------------------
def num(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default

def latest_weight():
    if not st.session_state.weight_log:
        return None
    return sorted(st.session_state.weight_log, key=lambda x: x["date"])[-1]["weight"]

def calc_bmr(sex, weight, height, age):
    if sex == "Mashkull":
        return 10*weight + 6.25*height - 5*age + 5
    return 10*weight + 6.25*height - 5*age - 161

ACTIVITY = {
    "Sedentar": 1.20,
    "Pak aktiv": 1.375,
    "Mesatarisht aktiv": 1.55,
    "Shumë aktiv": 1.725,
    "Ekstremisht aktiv": 1.90,
}

def goal_assessment(start_weight, loss, months):
    weeks = months * 4.345
    weekly = loss / weeks if weeks else 0
    daily_deficit = loss * 7700 / (months * 30.44) if months else 0
    if loss <= 0:
        return ("neutral", "Pa humbje peshe", weekly, daily_deficit)
    if weekly <= 0.5:
        return ("good", "Gradual", weekly, daily_deficit)
    if weekly <= 1.0:
        return ("good", "Në interval të zakonshëm gradual", weekly, daily_deficit)
    if weekly <= 1.25:
        return ("warn", "Agresiv", weekly, daily_deficit)
    return ("danger", "Shumë agresiv", weekly, daily_deficit)

def macro_targets(kcal, weight, goal):
    # General adult fitness heuristic; not medical prescription.
    if goal == "Humbje peshe":
        protein_g = max(1.6 * weight, 100)
        fat_pct = 0.28
    elif goal == "Shtim peshe":
        protein_g = max(1.6 * weight, 100)
        fat_pct = 0.30
    else:
        protein_g = max(1.5 * weight, 90)
        fat_pct = 0.30
    fat_g = kcal * fat_pct / 9
    remaining = max(0, kcal - protein_g*4 - fat_g*9)
    carb_g = remaining / 4
    return round(protein_g), round(carb_g), round(fat_g)

def meal_targets(kcal, protein, carbs, fat, meals):
    # Slightly larger lunch/dinner; simple and transparent.
    weights = {
        2: [0.45, 0.55],
        3: [0.25, 0.40, 0.35],
        4: [0.22, 0.33, 0.18, 0.27],
        5: [0.20, 0.30, 0.15, 0.20, 0.15],
        6: [0.18, 0.25, 0.12, 0.18, 0.15, 0.12],
    }[meals]
    return [
        {
            "kcal": round(kcal*w),
            "protein": round(protein*w),
            "carbs": round(carbs*w),
            "fat": round(fat*w),
        } for w in weights
    ]

@st.cache_data(ttl=86400, show_spinner=False)
def api_category_search(category, pagesize=45):
    params = {
        "categories_tags": category,
        "page_size": pagesize,
        "fields": "product_name,brands,nutriments,categories_tags,nutriscore_grade,serving_size",
    }
    try:
        r = requests.get(API_BASE, params=params, timeout=12)
        r.raise_for_status()
        return r.json().get("products", [])
    except Exception:
        return []

ROLE_CATEGORIES = {
    "protein": [
        "en:chicken", "en:turkey", "en:eggs", "en:tuna", "en:fish",
        "en:salmon", "en:beef", "en:yogurts"
    ],
    "carb": [
        "en:rice", "en:oats", "en:whole-wheat-bread", "en:bread",
        "en:pasta", "en:potatoes", "en:cereals"
    ],
    "vegetable": [
        "en:vegetables", "en:frozen-vegetables", "en:tomatoes",
        "en:carrots", "en:broccoli"
    ],
    "fruit": [
        "en:fruits", "en:apples", "en:bananas", "en:oranges", "en:berries"
    ],
    "fat": [
        "en:nuts", "en:peanut-butters", "en:olive-oils", "en:seeds", "en:avocados"
    ],
}

def healthy_ok(p):
    grade = str(p.get("nutriscore_grade") or "").lower()
    n = p.get("nutriments", {}) or {}
    sugar = num(n.get("sugars_100g"))
    sat = num(n.get("saturated-fat_100g"))
    if grade in {"d", "e"}:
        return False
    if sugar > 25 and sat > 7:
        return False
    return True

@st.cache_data(ttl=86400, show_spinner=False)
def get_food_pool(role, mode):
    products = []
    for cat in ROLE_CATEGORIES[role]:
        products.extend(api_category_search(cat))
        if len(products) >= 140:
            break
    seen = set()
    out = []
    for p in products:
        name = str(p.get("product_name") or "").strip()
        if not name or name.lower() in seen or not valid_food(p):
            continue
        if mode == "Healthy" and not healthy_ok(p):
            continue
        seen.add(name.lower())
        out.append(p)

    # Always merge curated foods so the generator remains functional.
    for f in FALLBACK_FOODS[role]:
        if mode == "Healthy" and f["kcal"] > 650 and role != "fat":
            continue
        if f["product_name"].lower() not in seen:
            out.append(f)
            seen.add(f["product_name"].lower())
    return out

def food_nutrition(p, grams):
    n = p.get("nutriments", {}) or {}
    if n:
        kcal = num(n.get("energy-kcal_100g") or n.get("energy-kcal"))
        protein = num(n.get("proteins_100g"))
        carbs = num(n.get("carbohydrates_100g"))
        fat = num(n.get("fat_100g"))
    else:
        kcal = num(p.get("kcal"))
        protein = num(p.get("protein"))
        carbs = num(p.get("carbs"))
        fat = num(p.get("fat"))
    return {
        "kcal": kcal*grams/100,
        "protein": protein*grams/100,
        "carbs": carbs*grams/100,
        "fat": fat*grams/100,
    }

def valid_food(p):
    x = food_nutrition(p, 100)
    return (
        bool(str(p.get("product_name") or "").strip())
        and x["kcal"] > 0
        and (x["protein"] + x["carbs"] + x["fat"]) > 0
    )

def pick(pool, seed):
    if not pool:
        return None
    rng = random.Random(seed)
    return rng.choice(pool)

def build_meal(target, mode, meal_idx, seed):
    pools = {r: get_food_pool(r, mode) for r in ROLE_CATEGORIES}
    rng = random.Random(seed)
    best = None

    # Role portions make meals nutritionally logical instead of random piles.
    for attempt in range(35):
        chosen = []
        for role in ["protein", "carb", "vegetable", "fruit", "fat"]:
            pool = pools[role]
            if not pool:
                continue
            chosen.append((role, rng.choice(pool)))

        if not chosen:
            continue

        # Start with sensible serving ranges.
        grams = {
            "protein": rng.randint(120, 220),
            "carb": rng.randint(90, 240),
            "vegetable": rng.randint(150, 300),
            "fruit": rng.randint(80, 180),
            "fat": rng.randint(5, 20),
        }

        # Snack-like meals should be lighter; main meals get all roles.
        if target["kcal"] < 350:
            grams["protein"] = rng.randint(80, 150)
            grams["carb"] = rng.randint(40, 120)
            grams["vegetable"] = rng.randint(80, 180)
            grams["fruit"] = rng.randint(60, 140)
            grams["fat"] = rng.randint(5, 12)

        def calc(grams_map):
            total = {"kcal":0,"protein":0,"carbs":0,"fat":0}
            for role, p in chosen:
                x = food_nutrition(p, grams_map[role])
                for k in total:
                    total[k] += x[k]
            return total

        total = calc(grams)
        # Scale toward kcal, then make up to 3 local adjustments.
        scale = target["kcal"] / max(total["kcal"], 1)
        for role in grams:
            grams[role] = max(5, min(450, grams[role] * scale))
        for _ in range(3):
            total = calc(grams)
            ratio = target["kcal"] / max(total["kcal"], 1)
            for role in ["protein", "carb"]:
                grams[role] = max(5, min(450, grams[role] * ratio))
            if total["protein"] < target["protein"] * 0.75:
                grams["protein"] = min(300, grams["protein"] * 1.12)

        final = calc({r: round(g/5)*5 for r,g in grams.items()})
        score = (
            abs(final["kcal"]-target["kcal"]) / max(target["kcal"],1) * 6
            + abs(final["protein"]-target["protein"]) / max(target["protein"],1) * 3
            + abs(final["carbs"]-target["carbs"]) / max(target["carbs"],1) * 1
            + abs(final["fat"]-target["fat"]) / max(target["fat"],1) * 1
        )
        if best is None or score < best[0]:
            best = (score, {r:round(g/5)*5 for r,g in grams.items()}, chosen, final)

    if best is None:
        return {"items": [], "totals": {"kcal":0,"protein":0,"carbs":0,"fat":0}}

    _, grams, chosen, final = best
    items = []
    for role, p in chosen:
        g = grams[role]
        x = food_nutrition(p, g)
        if x["kcal"] <= 0:
            continue
        items.append({
            "role": role,
            "name": str(p.get("product_name") or "Food").strip(),
            "grams": g,
            **x,
        })

    # Hard guard against the previous 0 kcal issue.
    if not items or sum(i["kcal"] for i in items) <= 0:
        p = FALLBACK_FOODS["protein"][0]
        g = max(50, round(target["kcal"]/food_nutrition(p,100)["kcal"]*100/5)*5)
        x = food_nutrition(p,g)
        items = [{"role":"protein","name":p["product_name"],"grams":g,**x}]
        final = x

    return {"items": items, "totals": final}

def make_plan(total_kcal, protein, carbs, fat, meals, mode):
    targets = meal_targets(total_kcal, protein, carbs, fat, meals)
    names = ["Mëngjes", "Drekë", "Snack", "Darkë", "Snack 2", "Vakt 6"]
    plan = []
    for i in range(meals):
        seed = st.session_state.meal_seeds.get(i, random.randint(1, 10_000_000))
        st.session_state.meal_seeds[i] = seed
        meal = build_meal(targets[i], mode, i, seed)
        meal["name"] = names[i]
        meal["target"] = targets[i]
        plan.append(meal)
    return plan

def plan_totals(plan):
    t = {k:0 for k in ["kcal","protein","carbs","fat"]}
    for m in plan:
        for k in t:
            t[k] += m["totals"][k]
    return t

# -----------------------------
# Header
# -----------------------------
current_w = latest_weight()
st.markdown("""
<div class="hero">
<h1>🥗 NutriTrack</h1>
<p>TDEE • objektivi i peshës • makro • dietë • tracking</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Sidebar / inputs
# -----------------------------
with st.sidebar:
    st.header("⚙️ Të dhënat")
    sex = st.selectbox("Gjinia", ["Mashkull", "Femër"])
    age = st.number_input("Mosha", 18, 100, 30)
    weight = st.number_input("Pesha (kg)", 35.0, 250.0, float(current_w or 90.0), 0.1)
    height = st.number_input("Gjatësia (cm)", 120.0, 230.0, 175.0, 0.5)
    activity = st.selectbox("Aktiviteti", list(ACTIVITY.keys()), index=1)
    goal = st.selectbox("Qëllimi", ["Humbje peshe", "Mirëmbajtje", "Shtim peshe"])
    meals = st.selectbox("Numri i vakteve", [2,3,4,5,6], index=2)
    food_mode = st.selectbox("Baza ushqimore", ["Healthy", "All Foods"])
    st.caption("Open Food Facts përdoret si burim ushqimesh. Të dhënat e produkteve mund të jenë të paplota.")

# -----------------------------
# Main tabs
# -----------------------------
tab_dash, tab_goal, tab_diet, tab_week, tab_track, tab_settings = st.tabs(
    ["🏠 Dashboard", "🎯 Objektivi", "🍽️ Dieta", "📅 7 Ditë", "⚖️ Tracking", "⚙️ Settings"]
)

bmr = calc_bmr(sex, weight, height, age)
tdee = bmr * ACTIVITY[activity]

with tab_dash:
    st.subheader("Përmbledhje")
    if st.session_state.plan:
        kcal_target = st.session_state.last_inputs["kcal"]
        p_target = st.session_state.last_inputs["protein"]
        c_target = st.session_state.last_inputs["carbs"]
        f_target = st.session_state.last_inputs["fat"]
    else:
        kcal_target = round(tdee)
        p_target, c_target, f_target = macro_targets(kcal_target, weight, goal)

    cols = st.columns(5)
    vals = [
        ("⚡", "TDEE", f"{round(tdee):,} kcal", "mirëmbajtje"),
        ("🔥", "Target", f"{round(kcal_target):,} kcal", goal),
        ("🥩", "Protein", f"{p_target} g", "ditore"),
        ("🍚", "Carbs", f"{c_target} g", "ditore"),
        ("🥑", "Fat", f"{f_target} g", "ditore"),
    ]
    for col,(icon,label,value,sub) in zip(cols,vals):
        with col:
            st.markdown(f'<div class="card"><div class="label">{icon} {label}</div><div class="value">{value}</div><div class="sub">{sub}</div></div>', unsafe_allow_html=True)

    st.write("")
    if current_w:
        st.metric("⚖️ Pesha aktuale", f"{current_w:.1f} kg")
    else:
        st.info("Shto peshën e parë te Tracking për të parë progresin.")

    if st.session_state.weight_log:
        df = pd.DataFrame(st.session_state.weight_log).sort_values("date")
        df["date"] = pd.to_datetime(df["date"])
        st.line_chart(df.set_index("date")["weight"], height=240)

    if not st.session_state.plan:
        st.info("Vendos objektivin dhe kliko **Gjenero dietën** te tab-i 'Objektivi'.")

with tab_goal:
    st.subheader("🎯 Objektivi yt")
    c1,c2,c3 = st.columns(3)
    with c1:
        target_weight = st.number_input("Pesha e synuar (kg)", 35.0, 250.0, max(35.0, round(weight-5,1)), 0.1)
    with c2:
        months = st.selectbox("Periudha", [1,2,3], index=0, format_func=lambda x: f"{x} muaj")
    with c3:
        if goal == "Humbje peshe":
            desired_loss = max(0.0, weight-target_weight)
        elif goal == "Shtim peshe":
            desired_loss = max(0.0, target_weight-weight)
        else:
            desired_loss = 0.0
        st.metric("Ndryshimi i synuar", f"{desired_loss:.1f} kg")

    if goal == "Humbje peshe":
        status, label, weekly, deficit = goal_assessment(weight, desired_loss, months)
        st.write(f"**Ritmi i synuar:** {weekly:.2f} kg/javë")
        st.write(f"**Deficiti i përafërt:** {round(deficit):,} kcal/ditë")
        if status == "good":
            st.markdown(f'<div class="success-box">🟢 <b>{label}</b><br>Ky është një ritëm gradual për një të rritur. App-i do ta përdorë si objektiv të llogaritjes.</div>', unsafe_allow_html=True)
        elif status == "warn":
            st.markdown(f'<div class="warn-box">🟠 <b>{label}</b><br>Ky ritëm është më agresiv. Konsidero një periudhë më të gjatë ose humbje më të vogël.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="danger-box">🔴 <b>{label}</b><br>Objektivi është shumë agresiv për gjenerim automatik. Rrite periudhën ose ule humbjen e synuar.</div>', unsafe_allow_html=True)

        st.caption("Ky është një vlerësim i përgjithshëm për të rritur dhe nuk zëvendëson këshillën mjekësore. Për shtatzëni, nën 18 vjeç ose gjendje mjekësore, mos përdor objektiv automatik pa profesionist shëndetësor.")

    if st.button("🚀 Gjenero / Përditëso dietën", type="primary", use_container_width=True):
        if goal == "Humbje peshe":
            status, _, weekly, deficit = goal_assessment(weight, desired_loss, months)
            kcal = round(tdee - deficit)
            if status == "danger" or kcal < 1200:
                st.error("Objektivi është shumë agresiv ose rezulton në kalori shumë të ulëta për gjenerim automatik. Zgjat periudhën ose zvogëlo humbjen e synuar.")
                st.stop()
        elif goal == "Shtim peshe":
            surplus = max(150, round(tdee*0.10))
            kcal = round(tdee + surplus)
        else:
            kcal = round(tdee)

        protein, carbs, fat = macro_targets(kcal, weight, goal)
        st.session_state.meal_seeds = {}
        plan = make_plan(kcal, protein, carbs, fat, meals, food_mode)
        st.session_state.plan = plan
        st.session_state.last_inputs = {
            "kcal": kcal, "protein": protein, "carbs": carbs, "fat": fat,
            "tdee": tdee, "goal": goal, "weight": weight, "food_mode": food_mode
        }
        st.success("Dieta u gjenerua.")

with tab_diet:
    st.subheader("🍽️ Plani i sotëm")
    if not st.session_state.plan:
        st.info("Së pari gjenero dietën te **Objektivi**.")
    else:
        inp = st.session_state.last_inputs
        pt = plan_totals(st.session_state.plan)
        cols = st.columns(4)
        for col, label, val, target in [
            (cols[0],"Kalori",pt["kcal"],inp["kcal"]),
            (cols[1],"Protein",pt["protein"],inp["protein"]),
            (cols[2],"Carbs",pt["carbs"],inp["carbs"]),
            (cols[3],"Fat",pt["fat"],inp["fat"]),
        ]:
            with col:
                st.metric(label, f"{round(val):,}", f"target {target}")
        st.caption("Gramaturat janë të përafërta dhe bazohen në të dhënat ushqyese të produkteve nga API.")

        for i, meal in enumerate(st.session_state.plan):
            with st.container():
                st.markdown(f'<div class="meal-card"><div class="meal-title">🍽️ {meal["name"]} · {round(meal["totals"]["kcal"])} kcal</div>', unsafe_allow_html=True)
                for item in meal["items"]:
                    st.markdown(
                        f'<div class="food-line"><b>{item["name"]}</b> — {round(item["grams"])} g '
                        f'<span class="muted">· {round(item["kcal"])} kcal · P {item["protein"]:.1f}g · C {item["carbs"]:.1f}g · F {item["fat"]:.1f}g</span></div>',
                        unsafe_allow_html=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)
                if st.button("🔄 Rigjenero këtë vakt", key=f"regen_{i}", use_container_width=True):
                    st.session_state.meal_seeds[i] = random.randint(1, 10_000_000)
                    target = meal["target"]
                    new_meal = build_meal(target, inp["food_mode"], i, st.session_state.meal_seeds[i])
                    new_meal["name"] = meal["name"]
                    new_meal["target"] = target
                    st.session_state.plan[i] = new_meal
                    st.rerun()

        text = ["NUTRITRACK - PLANI DITOR", ""]
        text.append(f"Target: {inp['kcal']} kcal | Protein {inp['protein']}g | Carbs {inp['carbs']}g | Fat {inp['fat']}g")
        text.append("")
        for meal in st.session_state.plan:
            text.append(f"{meal['name']} - {round(meal['totals']['kcal'])} kcal")
            for item in meal["items"]:
                text.append(f"- {item['name']}: {round(item['grams'])} g")
            text.append("")
        st.download_button("📥 Shkarko planin (.txt)", "\n".join(text), "nutritrack_plan.txt", use_container_width=True)

with tab_week:
    st.subheader("📅 Plan 7-ditor")
    if not st.session_state.plan:
        st.info("Gjenero fillimisht dietën te **Objektivi**.")
    else:
        inp = st.session_state.last_inputs
        st.caption("Versioni bazë përdor të njëjtin target ditor dhe ndryshon kombinimet e ushqimeve.")
        days = ["E Hënë","E Martë","E Mërkurë","E Enjte","E Premte","E Shtunë","E Diel"]
        for d_i, day_name in enumerate(days):
            with st.expander(day_name, expanded=(d_i == 0)):
                for m_i, meal in enumerate(st.session_state.plan):
                    # Show compact preview; daily plan remains fast to load.
                    names = [x["name"] for x in meal["items"]]
                    st.write(f"**{meal['name']}** · ~{round(meal['totals']['kcal'])} kcal — " + ", ".join(names[:3]))

with tab_track:
    st.subheader("⚖️ Tracking i peshës")
    a,b = st.columns([1,1])
    with a:
        log_date = st.date_input("Data", value=date.today())
    with b:
        log_value = st.number_input("Pesha (kg)", 35.0, 250.0, float(current_w or weight), 0.1)
    if st.button("➕ Ruaj peshën", use_container_width=True):
        st.session_state.weight_log.append({"date": str(log_date), "weight": log_value})
        st.session_state.weight_log = sorted(st.session_state.weight_log, key=lambda x: x["date"])
        st.success("Pesha u ruajt.")
        st.rerun()

    if st.session_state.weight_log:
        df = pd.DataFrame(st.session_state.weight_log).sort_values("date")
        df["date"] = pd.to_datetime(df["date"])
        first = float(df.iloc[0]["weight"])
        last = float(df.iloc[-1]["weight"])
        ch = last-first
        c1,c2,c3 = st.columns(3)
        c1.metric("Fillimi", f"{first:.1f} kg")
        c2.metric("Aktualisht", f"{last:.1f} kg")
        c3.metric("Ndryshimi", f"{ch:+.1f} kg")
        st.line_chart(df.set_index("date")["weight"], height=280)
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Ende nuk ka regjistrime.")

with tab_settings:
    st.subheader("⚙️ Settings")
    st.write("**API:** Open Food Facts")
    try:
        test = requests.get("https://world.openfoodfacts.org/api/v2/search", params={"categories_tags":"en:apples","page_size":1,"fields":"product_name"}, timeout=8)
        if test.ok:
            st.success("🟢 API është online")
        else:
            st.warning("🟠 API u përgjigj, por jo me sukses.")
    except Exception:
        st.error("🔴 Nuk u arrit API. Kontrollo internetin.")
    st.caption("Shënim: Open Food Facts është databazë komunitare; cilësia e të dhënave ndryshon sipas produktit.")

st.divider()
st.caption("NutriTrack v3 • General nutrition planning tool — not medical advice.")
