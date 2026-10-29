from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Phishing Website Explorer", page_icon="🛡️", layout="wide")

COLORS = {"Phishing": "#eb6834", "Legitimate": "#2a78d6"}
ORDER = ["Phishing", "Legitimate"]


# 1. Load the data (read once, then cached)
@st.cache_data
def load_data():
    # the data file is in the same folder as app.py
    return pd.read_csv(Path(__file__).parent / "phishing_clean.csv.gz")


df = load_data()


# 2. Sidebar: description and filters
st.sidebar.title("About")
st.sidebar.write(
    "This dashboard explores the **PhiUSIIL Phishing URL Dataset** (UCI): "
    f"{len(df):,} websites, each labeled as **phishing** or **legitimate**, "
    "with features taken from the URL and from the page's source code."
)

st.sidebar.header("Filters")

class_choice = st.sidebar.selectbox("Class", ["All", "Phishing", "Legitimate"])

all_types = sorted(df["TLDType"].unique())
tld_types = st.sidebar.multiselect("TLD type", all_types, default=all_types)

min_len, max_len = st.sidebar.slider("URL length (characters)", 10, 200, (10, 200),
                                     help="200 also includes all longer URLs.")


# 3. Apply the filters (everything below uses "filtered")
filtered = df[df["TLDType"].isin(tld_types)]
if class_choice != "All":
    filtered = filtered[filtered["label_name"] == class_choice]
if max_len == 200:
    max_len = df["URLLength"].max()
filtered = filtered[filtered["URLLength"].between(min_len, max_len)]

st.sidebar.caption(f"Showing {len(filtered):,} of {len(df):,} websites")

st.title("🛡️ Phishing Website Explorer")
st.write("What makes phishing websites different from legitimate ones?")

if filtered.empty:
    st.warning("No websites match these filters. Try changing them in the sidebar.")
    st.stop()


# 4. Key numbers
col1, col2, col3, col4 = st.columns(4)
col1.metric("Websites", f"{len(filtered):,}")
col2.metric("Phishing", f"{(filtered['label'] == 0).mean() * 100:.1f}%")
col3.metric("Use HTTPS", f"{filtered['IsHTTPS'].mean() * 100:.1f}%")
col4.metric("Median URL length", f"{filtered['URLLength'].median():.0f}")


# 5. Tabs
tab_data, tab_charts, tab_insights = st.tabs(["Data", "Charts", "Insights"])

with tab_data:
    st.subheader("Data preview")
    preview_cols = ["URL", "label_name", "TLD", "TLDType", "URLLength", "IsHTTPS",
                    "NoOfLinesOfCode", "HasTitle", "HasPasswordField", "HasSocialNet"]
    st.dataframe(filtered[preview_cols].head(100))

    st.subheader("Summary statistics")
    key_cols = ["URLLength", "NoOfDigitsInURL", "NoOfSubDomain", "NoOfLinesOfCode",
                "NoOfImage", "NoOfExternalRef", "NoOfJS"]
    st.write("Median of each feature by class:")
    st.dataframe(filtered.groupby("label_name")[key_cols].median().T.reindex(columns=ORDER))
    st.write("All selected websites:")
    st.dataframe(filtered[key_cols].describe().T.round(1))

with tab_charts:
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
        st.caption("The top 1% of values are hidden so that the chart stays readable.")
    st.plotly_chart(fig)

    left, right = st.columns(2)

    with left:
        st.subheader("Phishing share by TLD type")
        by_type = ((filtered.groupby("TLDType")["label"].apply(lambda s: (s == 0).mean()) * 100)
                   .sort_values().reset_index(name="% phishing"))
        fig = px.bar(by_type, x="% phishing", y="TLDType", orientation="h", text_auto=".1f",
                     color_discrete_sequence=[COLORS["Phishing"]], range_x=[0, 100],
                     labels={"TLDType": ""})
        st.plotly_chart(fig)

    with right:
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

with tab_insights:
    st.subheader("Key insights")
    st.markdown("""
- **HTTPS does not mean safe:** about 1 in 4 websites that use HTTPS is phishing.
- **Phishing pages are minimal:** the median phishing page has 12 lines of code, compared to 1,105 for legitimate pages.
- **Trust signals are missing on phishing pages:** under 1% link to social media, compared to 79% of legitimate pages.
- **Some TLDs are risky:** new generic TLDs (`.app`, `.dev`, `.top`, ...) are 93.8% phishing, while `.gov` and `.edu` are almost never phishing.
- **Free hosting platforms** such as Firebase (`web.app`) and Cloudflare (`workers.dev`) host many phishing websites.
- **No single feature is enough:** the rarest signs (IP addresses, obfuscation, Punycode) are 100% phishing but catch only 1.3% of phishing websites.
""")
    st.subheader("Limitations")
    st.info(
        "All legitimate websites in this dataset are homepages (`https://www.domain`) with at least "
        "102 lines of code, and all have a `URLSimilarityIndex` of exactly 100. "
        "So some differences come from how the dataset was built, not only from how phishing websites behave."
    )
