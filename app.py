import streamlit as st
import pickle
import requests
import re

st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

# Add your TMDB key to .streamlit/secrets.toml.
# The app can still open without a key, but posters and movie details may not load.
try:
    TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    TMDB_API_KEY = ""

@st.cache_data(show_spinner=False)
def tmdb_get(endpoint, params={}):
    try:
        r = requests.get(f"https://api.themoviedb.org/3/{endpoint}",
                         params={"api_key": TMDB_API_KEY, **params}, timeout=6)
        return r.json()
    except Exception:
        return {}

@st.cache_data(show_spinner=False)
def get_movie_info(movie_id, title):
    poster = None
    data   = {}

    # 1️⃣ Direct ID lookup
    d = tmdb_get(f"movie/{movie_id}")
    if d.get("poster_path"):
        poster = "https://image.tmdb.org/t/p/w500" + d["poster_path"]
        data = d

    # 2️⃣ Exact title search
    if not poster:
        hits = tmdb_get("search/movie", {"query": title}).get("results", [])
        for h in hits:
            if h.get("poster_path"):
                poster = "https://image.tmdb.org/t/p/w500" + h["poster_path"]
                data = h
                break

    # 3️⃣ Strip "The ", "A ", parentheticals and retry
    if not poster:
        clean = re.sub(r'\s*\(.*?\)', '', title).strip()
        clean = re.sub(r'^(The|A|An)\s+', '', clean, flags=re.I).strip()
        if clean.lower() != title.lower():
            hits = tmdb_get("search/movie", {"query": clean}).get("results", [])
            for h in hits:
                if h.get("poster_path"):
                    poster = "https://image.tmdb.org/t/p/w500" + h["poster_path"]
                    data = h
                    break

    # 4️⃣ First word(s) of title
    if not poster:
        words = title.split()[:3]
        hits = tmdb_get("search/movie", {"query": " ".join(words)}).get("results", [])
        for h in hits:
            if h.get("poster_path"):
                poster = "https://image.tmdb.org/t/p/w500" + h["poster_path"]
                data = h
                break

    rating   = round(float(data.get("vote_average") or 0), 1) or "N/A"
    year     = (data.get("release_date") or "")[:4] or "N/A"
    overview = data.get("overview", "")
    return {"poster": poster, "rating": rating, "year": year, "overview": overview}

@st.cache_resource
def load_data():
    m = pickle.load(open("movie_list.pkl", "rb"))
    s = pickle.load(open("similarity.pkl", "rb"))
    return m, s

movies_df, similarity = load_data()

def recommend(movie, n=10):
    idx  = movies_df[movies_df["title"] == movie].index[0]
    top  = sorted(enumerate(similarity[idx]), reverse=True, key=lambda x: x[1])[1:n+1]
    out  = []
    for i, score in top:
        row  = movies_df.iloc[i]
        info = get_movie_info(int(row["movie_id"]), row["title"])
        out.append({"title": row["title"], "score": round(score*100, 1), **info})
    return out

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{
  --bg:#08080d;--surface:#111118;--card:#18181f;
  --accent:#e94560;--gold:#f5c518;--text:#e6e6f0;--muted:#6b6b88;
  --border:rgba(233,69,96,.16);--glow:0 0 36px rgba(233,69,96,.2);
  --head:'Bebas Neue',sans-serif;--body:'DM Sans',sans-serif;
}
html,body,[class*="css"]{background:var(--bg)!important;color:var(--text)!important;font-family:var(--body)!important;}
#MainMenu,footer,header,.stDeployButton{display:none!important;}
.block-container{padding:0 2.5rem 5rem!important;max-width:1440px;margin:auto;}

.hero{background:linear-gradient(140deg,#08080d 0%,#140a14 50%,#08080d 100%);
  border-bottom:1px solid var(--border);padding:4rem 0 3rem;margin:0 -2.5rem 2.5rem;
  text-align:center;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% -20%,rgba(233,69,96,.15) 0%,transparent 65%);}
.eyebrow{font-size:.65rem;letter-spacing:.4em;color:var(--accent);text-transform:uppercase;margin-bottom:.8rem;}
.hero-title{font-family:var(--head);font-size:clamp(4rem,9vw,7.5rem);letter-spacing:.05em;line-height:1;margin:0;}
.hero-title span{color:var(--accent);}
.hero-sub{font-size:.95rem;color:var(--muted);margin-top:.8rem;font-weight:300;}

.stats-bar{display:flex;background:var(--surface);border:1px solid rgba(255,255,255,.04);
  border-radius:16px;overflow:hidden;margin-bottom:2.5rem;}
.stat{flex:1;padding:1.1rem 1.5rem;text-align:center;border-right:1px solid rgba(255,255,255,.04);}
.stat:last-child{border-right:none;}
.stat-num{font-family:var(--head);font-size:1.7rem;color:var(--accent);line-height:1;}
.stat-lbl{font-size:.6rem;letter-spacing:.22em;text-transform:uppercase;color:var(--muted);margin-top:.25rem;}

[data-testid="stSelectbox"]>div>div{background:var(--card)!important;border:1.5px solid var(--border)!important;
  border-radius:14px!important;color:var(--text)!important;font-size:1rem!important;box-shadow:var(--glow)!important;}
[data-testid="stSelectbox"]>div>div:focus-within{border-color:var(--accent)!important;}

.stButton>button{width:100%;background:linear-gradient(135deg,#e94560,#b0253e)!important;
  color:#fff!important;border:none!important;border-radius:14px!important;font-family:var(--head)!important;
  font-size:1.25rem!important;letter-spacing:.14em!important;padding:.9rem 1rem!important;
  box-shadow:0 4px 22px rgba(233,69,96,.35)!important;transition:transform .15s,box-shadow .15s!important;margin-top:.75rem!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 30px rgba(233,69,96,.5)!important;}

.sec-head{font-family:var(--head);font-size:1.9rem;letter-spacing:.07em;
  border-left:4px solid var(--accent);padding-left:.8rem;margin:2.5rem 0 1.4rem;}

.sel-hero{display:flex;gap:2rem;background:var(--card);border:1px solid var(--border);
  border-radius:20px;overflow:hidden;margin-bottom:2.5rem;box-shadow:var(--glow);animation:fadeUp .45s ease;}
.sel-poster{width:170px;min-width:170px;object-fit:cover;}
.sel-info{padding:1.8rem 1.8rem 1.8rem .4rem;display:flex;flex-direction:column;justify-content:center;}
.sel-eye{font-size:.6rem;letter-spacing:.35em;text-transform:uppercase;color:var(--accent);margin-bottom:.5rem;}
.sel-title{font-family:var(--head);font-size:2.3rem;letter-spacing:.04em;line-height:1;margin-bottom:.6rem;}
.sel-meta{font-size:.78rem;color:var(--muted);margin-bottom:.8rem;display:flex;gap:1.2rem;}
.sel-ov{font-size:.86rem;line-height:1.75;color:rgba(230,230,240,.68);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}

/* GRID */
.card-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;align-items:start;}

/* CARD */
.movie-card{background:var(--card);border:1px solid rgba(255,255,255,.05);border-radius:14px;
  overflow:hidden;transition:transform .25s,box-shadow .25s,border-color .25s;cursor:pointer;}
.movie-card:hover{transform:translateY(-7px) scale(1.025);box-shadow:0 18px 44px rgba(233,69,96,.22);border-color:var(--accent);}

/* POSTER AREA — fixed 2:3 ratio always */
.pw{position:relative;width:100%;padding-bottom:150%;overflow:hidden;}
.pw img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .4s;}
.movie-card:hover .pw img{transform:scale(1.06);}

/* NO-POSTER FALLBACK — styled gradient, no broken image */
.pw-fallback{
  position:absolute;inset:0;
  background:linear-gradient(135deg,#1a0a1e 0%,#0d1a2e 60%,#1a0a0e 100%);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:1rem;text-align:center;gap:.6rem;
}
.pw-fallback .film-icon{font-size:2.5rem;opacity:.45;}
.pw-fallback .fb-title{
  font-family:var(--head);font-size:1rem;letter-spacing:.06em;
  color:rgba(230,230,240,.55);line-height:1.2;
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;
}

.pw-ov{position:absolute;inset:0;background:linear-gradient(to top,rgba(8,8,13,.93) 0%,transparent 52%);
  display:flex;flex-direction:column;justify-content:flex-end;padding:.85rem;opacity:0;transition:opacity .28s;}
.movie-card:hover .pw-ov{opacity:1;}
.ov-desc{font-size:.7rem;color:rgba(230,230,240,.85);line-height:1.5;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}

.badge{position:absolute;top:9px;right:9px;background:var(--accent);color:#fff;
  font-family:var(--head);font-size:.82rem;letter-spacing:.06em;padding:.18rem .5rem;
  border-radius:7px;box-shadow:0 2px 8px rgba(233,69,96,.4);}

.cb{padding:.8rem .9rem .9rem;}
.ct{font-family:var(--head);font-size:1rem;letter-spacing:.04em;line-height:1.2;margin-bottom:.35rem;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.cm{display:flex;align-items:center;gap:.55rem;font-size:.72rem;color:var(--muted);}
.cr{color:var(--gold);}

@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
.anim{animation:fadeUp .48s ease both;}
.divider{border:none;border-top:1px solid rgba(255,255,255,.05);margin:2rem 0;}
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px;}
</style>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="eyebrow">✦ AI-Powered &nbsp;·&nbsp; Content-Based Filtering &nbsp;·&nbsp; 5000+ Films ✦</div>
  <h1 class="hero-title">CINE<span>MATCH</span></h1>
  <p class="hero-sub">Discover films that resonate — powered by intelligent similarity.</p>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="stats-bar">
  <div class="stat"><div class="stat-num">{len(movies_df):,}</div><div class="stat-lbl">Movies Indexed</div></div>
  <div class="stat"><div class="stat-num">5K</div><div class="stat-lbl">Feature Vectors</div></div>
  <div class="stat"><div class="stat-num">10</div><div class="stat-lbl">Recommendations</div></div>
  <div class="stat"><div class="stat-num">NLP</div><div class="stat-lbl">Cosine Similarity</div></div>
</div>""", unsafe_allow_html=True)

# ── SEARCH ────────────────────────────────────────────────────────────────────
st.markdown('<span style="font-size:.7rem;letter-spacing:.25em;text-transform:uppercase;color:var(--muted);">🎬 &nbsp; Pick a movie you love</span>', unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1:
    selected = st.selectbox("", sorted(movies_df["title"].values), label_visibility="collapsed")
with c2:
    st.write("")
    go = st.button("FIND MATCHES ›")

# ── Card builder ──────────────────────────────────────────────────────────────
def poster_html(title, poster_url):
    """Return inner poster HTML: real image OR tasteful fallback."""
    if poster_url:
        return f'<img src="{poster_url}" alt="{title}" loading="lazy">'
    else:
        # Elegant gradient fallback — no text that says "No Poster"
        return f"""
<div class="pw-fallback">
  <div class="film-icon">🎬</div>
  <div class="fb-title">{title}</div>
</div>"""

def card_html(title, info, score=None, delay=0):
    badge  = f'<div class="badge">{score}%</div>' if score is not None else ""
    desc   = (info["overview"][:220]+"…") if info.get("overview") else ""
    inner  = poster_html(title, info.get("poster"))
    return f"""
<div class="movie-card anim" style="animation-delay:{delay:.2f}s">
  <div class="pw">
    {inner}
    {badge}
    <div class="pw-ov"><div class="ov-desc">{desc}</div></div>
  </div>
  <div class="cb">
    <div class="ct">{title}</div>
    <div class="cm">
      <span>📅 {info.get('year','N/A')}</span>
      <span class="cr">⭐ {info.get('rating','N/A')}</span>
    </div>
  </div>
</div>"""

def render_grid(items):
    html = "".join(card_html(t, i, s, d*0.055) for d,(t,i,s) in enumerate(items))
    st.markdown(f'<div class="card-grid">{html}</div>', unsafe_allow_html=True)

# ── RESULTS / LANDING ─────────────────────────────────────────────────────────
if go and selected:
    row  = movies_df[movies_df["title"] == selected].iloc[0]
    info = get_movie_info(int(row["movie_id"]), selected)
    poster_tag = f'<img class="sel-poster" src="{info["poster"]}" alt="{selected}">' if info.get("poster") else \
                 f'<div class="sel-poster" style="background:linear-gradient(135deg,#1a0a1e,#0d1a2e);display:flex;align-items:center;justify-content:center;font-size:3rem;">🎬</div>'
    st.markdown(f"""
    <div class="sel-hero anim">
      {poster_tag}
      <div class="sel-info">
        <div class="sel-eye">🎯 &nbsp; You selected</div>
        <div class="sel-title">{selected}</div>
        <div class="sel-meta">
          <span>📅 {info['year']}</span>
          <span>⭐ {info['rating']} / 10</span>
        </div>
        <div class="sel-ov">{info['overview']}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-head">RECOMMENDED FOR YOU</div>', unsafe_allow_html=True)
    with st.spinner("Finding your perfect matches…"):
        recs = recommend(selected)
    render_grid([(r["title"], r, r["score"]) for r in recs])
    st.markdown('<hr class="divider"><p style="text-align:center;color:var(--muted);font-size:.72rem;letter-spacing:.18em;">CINEMATCH &nbsp;·&nbsp; Cosine Similarity &nbsp;·&nbsp; Data via TMDB</p>', unsafe_allow_html=True)

else:
    st.markdown('<div class="sec-head">TRENDING IN THE COLLECTION</div>', unsafe_allow_html=True)
    sample = movies_df.sample(10, random_state=7)
    items  = [(row["title"], get_movie_info(int(row["movie_id"]), row["title"]), None)
              for _, row in sample.iterrows()]
    render_grid(items)