"""
Phishing Website Explorer: what gives a phishing website away?
Jana Mosleh Alzobidi · Unit 3 Final Project · Tuwaiq Academy

Run from the main folder:  streamlit run app/app.py
"""
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Phishing Website Explorer", page_icon=":material/shield:", layout="wide")

# colors: orange = phishing, blue = legitimate (the same as in the notebook and the report)
PHISH, LEGIT, CYAN = "#eb6834", "#2a78d6", "#06b6d4"
COLORS = {"Phishing": PHISH, "Legitimate": LEGIT}
ORDER = ["Phishing", "Legitimate"]
SCALE = [LEGIT, "#f0efec", PHISH]   # blue (safe) → light gray → orange (phishing)
RISKY_TYPES = ["New generic", "IP address (no TLD)", "Non-Latin (Punycode)"]

# ═════════════════════════ design ═════════════════════════
# colors are transparent tints, so the page works in both light and dark mode
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');
.stApp { font-family: 'Space Grotesk', sans-serif; }
h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.01em; }

/* header with a cyber grid and a scanning line */
.hero { position: relative; overflow: hidden; border-radius: 20px; padding: 26px 32px; margin-bottom: 18px;
        border: 1px solid rgba(6,182,212,.35);
        background-image: linear-gradient(120deg, rgba(6,182,212,.16), rgba(235,104,52,.10)),
                          linear-gradient(rgba(127,127,127,.09) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(127,127,127,.09) 1px, transparent 1px);
        background-size: 100% 100%, 22px 22px, 22px 22px;
        display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.hero .scan { position: absolute; top: 0; left: -35%; width: 35%; height: 100%; pointer-events: none;
              background: linear-gradient(90deg, transparent, rgba(6,182,212,.22), transparent);
              animation: scan 5s linear infinite; }
@keyframes scan { to { left: 110%; } }
.hero .kicker { font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: .12em; color: #06b6d4; font-weight: 600; }
.hero .kicker .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #eb6834;
                     margin-right: 8px; animation: blink 1.2s ease-in-out infinite; }
@keyframes blink { 50% { opacity: .2; } }
.hero .title { font-size: 46px; font-weight: 700; line-height: 1.05; margin: 8px 0 6px; }
.hero .sub { font-size: 17px; opacity: .8; max-width: 760px; }
.hero svg { flex-shrink: 0; }
/* the fish (the user) swims to the bait (a URL with a padlock) */
@media (prefers-reduced-motion: no-preference) {
  .hero .fish { animation: swim 5s ease-in-out infinite; }
  @keyframes swim { 0% { transform: translateX(-70px); } 55%, 70% { transform: translateX(0); } 100% { transform: translateX(-70px); } }
  .hero .tail { transform-box: fill-box; transform-origin: 100% 50%; animation: wag .35s ease-in-out infinite alternate; }
  @keyframes wag { from { transform: rotate(-14deg); } to { transform: rotate(14deg); } }
  .hero .bait { animation: bob 1.4s ease-in-out infinite; }
  @keyframes bob { 50% { transform: translateY(5px); } }
  .hero .bubble { animation: rise 3s linear infinite; }
  .hero .bubble.b2 { animation-delay: 1s; }
  .hero .bubble.b3 { animation-delay: 2s; }
  @keyframes rise { 0% { transform: translateY(0); opacity: 0; } 20% { opacity: .8; } 100% { transform: translateY(-70px); opacity: 0; } }
}

/* key number cards */
.kpi { border: 1px solid rgba(127,127,127,.25); background: rgba(127,127,127,.06); border-radius: 16px;
       padding: 14px 18px; transition: transform .2s, border-color .2s; height: 100%; }
.kpi:hover { transform: translateY(-3px); border-color: rgba(6,182,212,.65); }
.kpi .bar { width: 42px; height: 4px; border-radius: 4px; margin-bottom: 10px; }
.kpi .v { font-family: 'JetBrains Mono', monospace; font-size: 30px; font-weight: 700; line-height: 1.1; }
.kpi .l { font-size: 14px; opacity: .7; margin-top: 2px; }

/* tabs as buttons (works with old and new Streamlit versions) */
.stTabs [role="tablist"] { gap: 8px; flex-wrap: wrap; border-bottom: none; }
.stTabs [role="tab"] { border: 1px solid rgba(127,127,127,.25); background: rgba(127,127,127,.06);
                       border-radius: 12px; padding: 8px 16px; transition: all .2s; }
.stTabs [role="tab"]:hover { border-color: rgba(6,182,212,.6); transform: translateY(-2px); }
.stTabs [role="tab"][aria-selected="true"] { background: rgba(6,182,212,.16); border-color: rgba(6,182,212,.7); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"],
.stTabs .react-aria-SelectionIndicator { display: none; }

/* insight boxes */
.insight { border-left: 4px solid #06b6d4; background: rgba(6,182,212,.08); border-radius: 0 12px 12px 0;
           padding: 12px 16px; margin: 4px 0 18px; font-size: 16px; line-height: 1.6; }
.insight b { color: #eb6834; }

/* spot the phish game */
.url-card { font-family: 'JetBrains Mono', monospace; font-size: 16px; word-break: break-all; text-align: center;
            border: 1px dashed rgba(127,127,127,.45); border-radius: 14px; padding: 26px 16px; min-height: 96px;
            display: flex; align-items: center; justify-content: center; background: rgba(127,127,127,.05);
            margin-bottom: 10px; }
.url-card.phish { border: 2px solid #eb6834; background: rgba(235,104,52,.10); }
.url-card.legit { border: 2px solid #2a78d6; background: rgba(42,120,214,.10); }
.chip { display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 13px; margin: 4px 4px 0 0;
        background: rgba(235,104,52,.16); border: 1px solid rgba(235,104,52,.45); }
.chip.ok { background: rgba(42,120,214,.14); border-color: rgba(42,120,214,.45); }

.foot { font-size: 13px; opacity: .6; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)


def insight(html):
    st.markdown(f'<div class="insight">💡 {html}</div>', unsafe_allow_html=True)


# ═════════════════════════ 1. load the data ═════════════════════════
@st.cache_data
def load_data():
    # the data file is in the same folder as app.py
    return pd.read_csv(Path(__file__).parent / "phishing_clean.csv.gz")


df = load_data()


def red_flags(data):
    # the warning signs found in the EDA, one column per sign (True = the website has this sign)
    return pd.DataFrame({
        "No HTTPS": data["IsHTTPS"] == 0,
        "No title": data["HasTitle"] == 0,
        "Tiny page (20 lines of code or fewer)": data["NoOfLinesOfCode"] <= 20,
        "No social media links": data["HasSocialNet"] == 0,
        "No copyright info": data["HasCopyrightInfo"] == 0,
        "Risky TLD type (new generic, IP or Punycode)": data["TLDType"].isin(RISKY_TYPES),
        "Digits in the URL": data["NoOfDigitsInURL"] > 0,
        "3 or more special characters in the URL": data["NoOfOtherSpecialCharsInURL"] >= 3,
    })


# ═════════════════════════ 2. sidebar ═════════════════════════
st.sidebar.title(":material/shield: Phishing Explorer")
st.sidebar.write(
    "This dashboard explores the **PhiUSIIL Phishing URL Dataset** (UCI): "
    f"{len(df):,} websites, each labeled as **phishing** or **legitimate**, "
    "with features taken from the URL and from the page's source code."
)
st.sidebar.header(":material/filter_alt: Filters")

class_choice = st.sidebar.selectbox("Class", ["All", "Phishing", "Legitimate"])
all_types = sorted(df["TLDType"].unique())
tld_types = st.sidebar.multiselect("TLD type", all_types, default=all_types)
min_len, max_len = st.sidebar.slider("URL length (characters)", 10, 200, (10, 200),
                                     help="200 also includes all longer URLs.")

# ═════════════════════════ 3. apply the filters ═════════════════════════
# everything below uses "filtered", except the URL Inspector and the game (they use all the data)
filtered = df[df["TLDType"].isin(tld_types)]
if class_choice != "All":
    filtered = filtered[filtered["label_name"] == class_choice]
if max_len == 200:
    max_len = df["URLLength"].max()
filtered = filtered[filtered["URLLength"].between(min_len, max_len)]

st.sidebar.caption(f"Showing {len(filtered):,} of {len(df):,} websites")
st.sidebar.divider()
st.sidebar.caption("Source: PhiUSIIL Phishing URL Dataset, UCI Machine Learning Repository\n\n"
                   "Made by **Jana Mosleh Alzobidi**")

# ═════════════════════════ header ═════════════════════════
st.markdown(f"""
<div class="hero">
  <div class="scan"></div>
  <div>
    <div class="kicker"><span class="dot"></span>LIVE ANALYSIS · {len(df):,} WEBSITES · UCI PHIUSIIL</div>
    <div class="title">Phishing Website Explorer</div>
    <div class="sub">Phishing websites copy real ones to steal passwords and bank details.
    What gives them away? Explore the URL, the page and the warning signs.</div>
  </div>
  <svg width="300" height="160" viewBox="0 0 260 140" aria-hidden="true">
    <line x1="190" y1="0" x2="190" y2="44" stroke="#94a3b8" stroke-width="1.5"/>
    <g class="bait">
      <path d="M190 44 v14 a9 9 0 1 1 -18 0" fill="none" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
      <g transform="translate(146 68)">
        <rect width="76" height="22" rx="11" fill="rgba(235,104,52,.18)" stroke="{PHISH}" stroke-width="1.5"/>
        <rect x="9" y="8" width="7" height="6" rx="1" fill="{PHISH}"/>
        <path d="M10.5 8 v-2 a2 2 0 0 1 4 0 v2" fill="none" stroke="{PHISH}" stroke-width="1.2"/>
        <text x="21" y="15" font-size="10" fill="{PHISH}" font-family="JetBrains Mono, monospace" font-weight="700">https://</text>
      </g>
    </g>
    <g class="fish"><g transform="translate(100 82)">
      <g class="tail"><path d="M-22 0 L-40 -12 L-40 12 Z" fill="{LEGIT}"/></g>
      <ellipse cx="0" cy="0" rx="24" ry="13" fill="{LEGIT}"/>
      <circle cx="11" cy="-3" r="3" fill="#0b1120"/>
    </g></g>
    <circle class="bubble" cx="40" cy="130" r="3" fill="none" stroke="{CYAN}"/>
    <circle class="bubble b2" cx="225" cy="132" r="2.5" fill="none" stroke="{CYAN}"/>
    <circle class="bubble b3" cx="70" cy="134" r="2" fill="none" stroke="{CYAN}"/>
  </svg>
</div>""", unsafe_allow_html=True)

if filtered.empty:
    st.warning("No websites match these filters. Try changing them in the sidebar.", icon=":material/warning:")
    st.stop()

# ═════════════════════════ 4. key numbers ═════════════════════════
kpis = [(f"{len(filtered):,}", f"websites ({len(filtered) / len(df):.0%} of the data)", CYAN),
        (f"{(filtered['label'] == 0).mean():.1%}", "are phishing", PHISH),
        (f"{filtered['IsHTTPS'].mean():.1%}", "use HTTPS (the padlock)", LEGIT),
        (f"{filtered['URLLength'].median():.0f}", "median URL length (characters)", "#8b8b8b")]
for col, (value, label, color) in zip(st.columns(4), kpis):
    col.markdown(f'<div class="kpi"><div class="bar" style="background:{color}"></div>'
                 f'<div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)
st.write("")

# ═════════════════════════ 5. tabs ═════════════════════════
tab_data, tab_charts, tab_flags, tab_inspector, tab_game, tab_insights = st.tabs([
    ":material/table: Data", ":material/bar_chart: Charts", ":material/flag: Red flags",
    ":material/travel_explore: URL Inspector", ":material/sports_esports: Spot the phish",
    ":material/lightbulb: Insights"])

# ───────────────────────── Data ─────────────────────────
with tab_data:
    with st.container(border=True):
        st.subheader("Data preview")
        search = st.text_input("Search URLs", placeholder="for example: login, secure, verify, .xyz",
                               icon=":material/search:")
        preview = filtered
        if search:
            preview = filtered[filtered["URL"].str.contains(search, case=False, regex=False)]
            phishing_share = (preview["label"] == 0).mean() * 100 if len(preview) else 0
            insight(f"<b>{len(preview):,}</b> URLs contain \"{search}\", and <b>{phishing_share:.1f}%</b> of them are phishing.")
        preview_cols = ["URL", "label_name", "TLD", "TLDType", "URLLength", "IsHTTPS",
                        "NoOfLinesOfCode", "HasTitle", "HasPasswordField", "HasSocialNet"]
        st.dataframe(preview[preview_cols].head(100), hide_index=True)
        st.download_button("Download the filtered data (CSV)", preview.to_csv(index=False).encode("utf-8"),
                           "phishing_filtered.csv", "text/csv", icon=":material/download:")

    key_cols = ["URLLength", "NoOfDigitsInURL", "NoOfSubDomain", "NoOfLinesOfCode",
                "NoOfImage", "NoOfExternalRef", "NoOfJS"]
    left, right = st.columns([2, 3])
    with left:
        with st.container(border=True):
            st.subheader("Median by class")
            st.dataframe(filtered.groupby("label_name")[key_cols].median().T.reindex(columns=ORDER))
    with right:
        with st.container(border=True):
            st.subheader("Summary statistics")
            st.dataframe(filtered[key_cols].describe().T.round(1))

# ───────────────────────── Charts ─────────────────────────
with tab_charts:
    with st.container(border=True):
        st.subheader("Compare a feature between the two classes")
        numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != "label"]
        feature = st.selectbox("Feature", numeric_cols, index=numeric_cols.index("URLLength"))

        if df[feature].nunique() == 2:
            # binary feature: % of websites in each class where the feature = 1
            share = (filtered.groupby("label_name")[feature].mean() * 100).reset_index()
            fig = px.bar(share, x="label_name", y=feature, color="label_name",
                         color_discrete_map=COLORS, text_auto=".1f",
                         labels={"label_name": "", feature: f"% with {feature} = 1"})
        else:
            # numeric feature: distribution in each class (top 1% hidden to keep it readable)
            limit = filtered[feature].quantile(0.99)
            fig = px.histogram(filtered[filtered[feature] <= limit], x=feature, color="label_name",
                               color_discrete_map=COLORS, category_orders={"label_name": ORDER},
                               barmode="overlay", histnorm="percent", nbins=50,
                               labels={"label_name": "Class"})
            fig.update_layout(yaxis_title="% of websites in each class")
            fig.update_traces(opacity=0.75)
            st.caption("The top 1% of values are hidden so that the chart stays readable.")
        st.plotly_chart(fig)

    with st.container(border=True):
        st.subheader("Explore the TLDs")
        st.caption("Each box is a TLD, grouped by TLD type. Size = number of websites, color = % phishing. "
                   "Click a box to zoom in, and click the top bar to go back.")
        tlds = (filtered.groupby(["TLDType", "TLD"])
                .agg(Websites=("label", "size"), Phishing=("label", lambda s: (s == 0).mean() * 100))
                .reset_index())
        fig = px.treemap(tlds, path=[px.Constant("All TLDs"), "TLDType", "TLD"], values="Websites",
                         color="Phishing", range_color=[0, 100], color_continuous_scale=SCALE,
                         labels={"Phishing": "% phishing"})
        fig.update_traces(hovertemplate="<b>%{label}</b><br>Websites: %{value:,}<br>"
                                        "Phishing: %{color:.1f}%<extra></extra>")
        fig.update_layout(height=550, margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig)
        insight("<b>.com</b> is huge but only about 39% phishing, while almost every <b>new generic</b> TLD "
                "(.app, .top, .xyz, ...) is orange.")

    with st.container(border=True):
        st.subheader("URL length vs. page size")
        st.caption("A random sample of up to 3,000 websites per class. Hover over a dot to see its URL.")
        sample = filtered.groupby("label_name").sample(frac=1, random_state=42).groupby("label_name").head(3000)
        fig = px.scatter(sample, x="URLLength", y="NoOfLinesOfCode", color="label_name",
                         color_discrete_map=COLORS, category_orders={"label_name": ORDER},
                         log_x=True, log_y=True, opacity=0.6, hover_data={"URL": True, "TLD": True},
                         labels={"URLLength": "URL length (log scale)", "NoOfLinesOfCode": "Lines of code (log scale)",
                                 "label_name": "Class"})
        fig.update_traces(marker_size=5)
        fig.update_xaxes(tickvals=[20, 30, 50, 100, 200, 500, 1000])
        fig.update_yaxes(tickvals=[1, 10, 100, 1000, 10000, 100000])
        fig.update_layout(height=500)
        st.plotly_chart(fig)

    left, right = st.columns(2)
    with left:
        with st.container(border=True, height="stretch"):
            st.subheader("Phishing share by TLD type")
            by_type = ((filtered.groupby("TLDType")["label"].apply(lambda s: (s == 0).mean()) * 100)
                       .sort_values().reset_index(name="% phishing"))
            fig = px.bar(by_type, x="% phishing", y="TLDType", orientation="h", text_auto=".1f",
                         color_discrete_sequence=[PHISH], range_x=[0, 100], labels={"TLDType": ""})
            st.plotly_chart(fig)
    with right:
        with st.container(border=True, height="stretch"):
            st.subheader("Security indicators")
            indicators = {"Uses HTTPS": "IsHTTPS", "IP address as domain": "IsDomainIP",
                          "Obfuscated characters": "HasObfuscation", "Password field": "HasPasswordField",
                          "Social media links": "HasSocialNet", "Copyright info": "HasCopyrightInfo"}
            share = filtered.groupby("label_name")[list(indicators.values())].mean() * 100
            share = share.rename(columns={v: k for k, v in indicators.items()}).T.reset_index()
            share = share.melt(id_vars="index", var_name="Class", value_name="% of websites")
            fig = px.bar(share, x="% of websites", y="index", color="Class", orientation="h",
                         barmode="group", color_discrete_map=COLORS, range_x=[0, 100],
                         category_orders={"Class": ORDER}, labels={"index": ""})
            st.plotly_chart(fig)

# ───────────────────────── Red flags ─────────────────────────
with tab_flags:
    st.subheader("How many red flags does a website have?")
    st.write("Each red flag is a warning sign found in the EDA. Choose the flags to count, and see how the share "
             "of phishing websites changes with the number of flags.")

    all_flags = red_flags(filtered)
    chosen = st.pills("Red flags to count", list(all_flags.columns), selection_mode="multi",
                      default=list(all_flags.columns))

    if not chosen:
        st.info("Choose at least one red flag.", icon=":material/info:")
    else:
        flag_count = all_flags[chosen].sum(axis=1)
        by_count = (pd.DataFrame({"Red flags": flag_count, "phishing": filtered["label"] == 0})
                    .groupby("Red flags")["phishing"].agg(Websites="size", Phishing="mean").reset_index())
        by_count["% phishing"] = by_count["Phishing"] * 100

        with st.container(border=True):
            fig = px.bar(by_count, x="Red flags", y="% phishing", text_auto=".0f",
                         color="% phishing", range_color=[0, 100], color_continuous_scale=SCALE,
                         hover_data={"Websites": ":,"}, title="% phishing by number of red flags")
            fig.update_layout(coloraxis_showscale=False, xaxis=dict(dtick=1), yaxis_range=[0, 105])
            st.plotly_chart(fig)
            low = by_count[by_count["Red flags"] <= 1]
            low_share = (low["Phishing"] * low["Websites"]).sum() / max(low["Websites"].sum(), 1) * 100
            insight(f"Websites with <b>0 or 1</b> red flag are only <b>{low_share:.1f}%</b> phishing. "
                    "Look at how fast the bars rise: no single sign is enough, but together they give phishing away.")

        with st.container(border=True):
            st.markdown("##### Each red flag on its own")
            single = pd.DataFrame({
                "Red flag": chosen,
                "% of websites": [all_flags[f].mean() * 100 for f in chosen],
                "% phishing": [(filtered.loc[all_flags[f], "label"] == 0).mean() * 100 for f in chosen],
            })
            st.dataframe(single, hide_index=True, column_config={
                "% of websites": st.column_config.NumberColumn(format="%.1f%%"),
                "% phishing": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})
        st.caption("Note: no legitimate website in this dataset is a tiny page or uses HTTP, so these two flags are "
                   "partly caused by how the dataset was built.")


# ───────────────────────── URL Inspector ─────────────────────────
def url_parts(url):
    # split a URL into its host (without port) and the part after the host
    rest = url.split("://", 1)[-1]
    host = rest.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0].lower()
    path = rest[len(rest.split("/", 1)[0]):]
    return host, path


@st.cache_data
def url_signals(data):
    # signals computed from the URL text of every website in the dataset
    return pd.DataFrame({
        "https": data["URL"].str.startswith("https://"),
        "has_path": data["URL"].map(lambda u: len(url_parts(u)[1].strip("/")) > 0),
        "has_digits": data["URL"].str.contains(r"\d", regex=True),
        "punycode": data["URL"].str.contains("xn--", regex=False),
        "length": data["URL"].str.len(),
        "phishing": data["label"] == 0,
    })


def tld_type(tld):
    if tld == "IP":
        return "IP address (no TLD)"
    if tld.startswith("xn--"):
        return "Non-Latin (Punycode)"
    if tld in ["gov", "edu", "mil", "int"]:
        return "Restricted"
    if tld in ["com", "org", "net", "info", "biz"]:
        return "Classic generic"
    if len(tld) == 2:
        return "Country code"
    return "New generic"


with tab_inspector:
    st.subheader("Inspect a URL")
    st.write("Type any URL to see which warning signs it has, and how often websites with the same sign "
             "are phishing in this dataset. This uses the full dataset (the sidebar filters do not apply here).")
    examples = ["https://www.wikipedia.org", "http://43.134.167.94/servicelogin?continue=https://accounts.google.com",
                "https://secure-login-verify-2026.web.app/account", "https://www.uni-mainz.de"]

    def use_example():
        # copy the chosen example into the URL box
        if st.session_state["example"] != "(type your own)":
            st.session_state["url"] = st.session_state["example"]

    st.selectbox("Try an example", ["(type your own)"] + examples, key="example", on_change=use_example)
    url = st.text_input("URL", key="url", placeholder="https://www.example.com", icon=":material/link:").strip()

    if url:
        if "://" not in url:
            url = "https://" + url
        signals = url_signals(df)
        host, path = url_parts(url)
        is_ip = re.fullmatch(r"[\d.]+", host) is not None
        tld = "IP" if is_ip else host.rsplit(".", 1)[-1]
        length = len(url)

        def share(mask):
            return mask.sum(), signals.loc[mask, "phishing"].mean() * 100 if mask.any() else None

        checks = [
            ("Protocol", "HTTPS" if url.startswith("https://") else "HTTP (no HTTPS)",
             *share(signals["https"] == url.startswith("https://"))),
            ("TLD", f".{tld}" if not is_ip else "IP address", *share(df["TLD"] == tld)),
            ("TLD type", tld_type(tld), *share(df["TLDType"] == tld_type(tld))),
            ("Path after the domain", "Yes" if path.strip("/") else "No",
             *share(signals["has_path"] == bool(path.strip("/")))),
            ("Digits in the URL", "Yes" if re.search(r"\d", url) else "No",
             *share(signals["has_digits"] == bool(re.search(r"\d", url)))),
            ("URL length", f"{length} characters", *share(signals["length"].between(length - 5, length + 5))),
        ]
        if "xn--" in url:
            checks.append(("Punycode (xn--)", "Yes", *share(signals["punycode"])))

        result = pd.DataFrame(checks, columns=["Check", "This URL", "Websites with the same value", "% phishing"])
        risky = result["% phishing"].fillna(0) >= 80

        c1, c2 = st.columns([1, 3])
        c1.markdown(f'<div class="kpi"><div class="bar" style="background:{PHISH if risky.sum() >= 3 else CYAN}"></div>'
                    f'<div class="v">{risky.sum()} / {len(result)}</div><div class="l">warning signs</div></div>',
                    unsafe_allow_html=True)
        with c2:
            if risky.sum() >= 3:
                st.error("Many warning signs: this URL looks like the phishing websites in the dataset.",
                         icon=":material/gpp_bad:")
            elif risky.sum() >= 1:
                st.warning("Some warning signs: be careful with this URL.", icon=":material/warning:")
            else:
                st.success("No strong warning signs: this URL looks like the legitimate websites in the dataset.",
                           icon=":material/verified_user:")

        st.dataframe(result, hide_index=True, column_config={
            "Websites with the same value": st.column_config.NumberColumn(format="%d"),
            "% phishing": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})
        st.caption("A warning sign is a value where 80% or more of the websites in the dataset are phishing. "
                   "This is not a real phishing detector: it only compares the URL with this dataset, and some checks "
                   "(HTTPS and the path) are affected by how the dataset was built.")

# ───────────────────────── Spot the phish (game) ─────────────────────────
with tab_game:
    st.subheader("Can you spot the phishing URL?")
    st.write("One URL is phishing and one is legitimate, both real websites from the dataset. "
             "Pick the phishing one, then see the red flags behind it.")

    if "score" not in st.session_state:
        st.session_state.update(score=0, rounds=0, pair=None, picked=None)

    def new_round():
        phishing_pool = df[df["label"] == 0]
        if st.session_state.get("level") == "Hard":
            # hard: the phishing URL also looks like a homepage (https://www. and no path)
            rest = phishing_pool["URL"].str.split("://").str[1].str.rstrip("/")
            phishing_pool = phishing_pool[phishing_pool["URL"].str.startswith("https://www.")
                                          & ~rest.str.contains("/", regex=False)]
        pair = [phishing_pool.sample(1).index[0], df[df["label"] == 1].sample(1).index[0]]
        if pd.Series([0, 1]).sample(1).iloc[0] == 1:   # random order
            pair.reverse()
        st.session_state.pair = pair
        st.session_state.picked = None

    def pick(i):
        st.session_state.picked = i
        st.session_state.rounds += 1
        if df.loc[st.session_state.pair[i], "label"] == 0:
            st.session_state.score += 1

    st.segmented_control("Level", ["Easy", "Hard"], default="Easy", key="level", on_change=new_round,
                         help="Hard: the phishing URL also starts with https://www. and has no path, "
                              "just like the legitimate ones.")
    if st.session_state.pair is None:
        new_round()

    pair, picked = st.session_state.pair, st.session_state.picked
    for i, (col, idx) in enumerate(zip(st.columns(2, gap="large"), pair)):
        row = df.loc[idx]
        shown = row["URL"].rstrip("/")   # the trailing "/" would give the answer away
        css = "" if picked is None else ("phish" if row["label"] == 0 else "legit")
        with col:
            st.markdown(f'<div class="url-card {css}">{shown}</div>', unsafe_allow_html=True)
            st.button("This one is phishing", key=f"pick_{i}", on_click=pick, args=(i,),
                      disabled=picked is not None, icon=":material/phishing:", width="stretch")
            if picked is not None:
                flags = red_flags(df.loc[[idx]]).iloc[0]
                found = [f for f, on in flags.items() if on]
                label = "Phishing" if row["label"] == 0 else "Legitimate"
                chips = "".join(f'<span class="chip{" ok" if row["label"] == 1 else ""}">{f}</span>' for f in found)
                st.markdown(f"**{label}** · {len(found)} red flag{'s' if len(found) != 1 else ''}<br>{chips}",
                            unsafe_allow_html=True)

    if picked is not None:
        if df.loc[pair[picked], "label"] == 0:
            st.success("Correct, you caught the phish!", icon=":material/check_circle:")
        else:
            st.error("Not this time: that one was the legitimate website.", icon=":material/cancel:")

    c1, c2, c3 = st.columns([1, 1, 2], vertical_alignment="center")
    c1.metric("Score", f"{st.session_state.score} / {st.session_state.rounds}", border=True)
    c2.button("Next round", on_click=new_round, icon=":material/refresh:", width="stretch")
    c3.caption("The URLs are shown as text only and cannot be clicked, because the phishing ones are real.")

# ───────────────────────── Insights ─────────────────────────
with tab_insights:
    insights = [
        (":material/lock_open:", "HTTPS does not mean safe", "About 1 in 4 websites that use HTTPS is phishing."),
        (":material/code:", "Phishing pages are minimal", "The median phishing page has 12 lines of code, compared to 1,105 for legitimate pages."),
        (":material/verified:", "Trust signals are missing", "Under 1% of phishing pages link to social media, compared to 79% of legitimate pages."),
        (":material/language:", "Some TLDs are risky", "New generic TLDs (.app, .dev, .top, ...) are 93.8% phishing, while .gov and .edu are almost never phishing."),
        (":material/cloud:", "Free hosting is popular", "Many phishing websites use free platforms such as Firebase (web.app) and Cloudflare (workers.dev)."),
        (":material/search:", "No single feature is enough", "IP addresses, obfuscation and Punycode are 100% phishing but catch only 1.3% of phishing websites."),
    ]
    for row in [insights[:3], insights[3:]]:
        cols = st.columns(3)
        for col, (icon, title, text) in zip(cols, row):
            with col.container(border=True, height="stretch"):
                st.markdown(f"#### {icon} {title}")
                st.write(text)

    st.warning(
        "**Limitations:** all legitimate websites in this dataset are homepages (`https://www.domain`) with at least "
        "102 lines of code, and all have a `URLSimilarityIndex` of exactly 100. "
        "So some differences come from how the dataset was built, not only from how phishing websites behave.",
        icon=":material/info:",
    )

st.markdown('<div class="foot">Phishing Website Explorer · Jana Mosleh Alzobidi · Unit 3 Final Project, Tuwaiq Academy · '
            'Data: PhiUSIIL Phishing URL Dataset (Prasad &amp; Chandra, 2024), UCI Machine Learning Repository</div>',
            unsafe_allow_html=True)
