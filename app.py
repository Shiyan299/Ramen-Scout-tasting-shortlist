from pathlib import Path
import altair as alt
import streamlit as st
from analysis import DATA_PATH, MIN_BRAND_RECORDS, THRESHOLD, brand_summary, filter_data, headline, load_data, shortlist

st.set_page_config(page_title="Ramen Scout | Tasting shortlist", page_icon="🍜", layout="wide")

@st.cache_data
def read_snapshot(modified_ns):
    return load_data()

st.title("🍜 Ramen Scout — Tasting shortlist")
st.caption("For an imported-food store's assortment manager: choose ramen products to request for a tasting before considering a listing.")
st.caption("Data period: unknown (no review dates in CSV) · Historical Kaggle snapshot · Proposed production refresh: weekly, before Monday's review.")
try:
    data = read_snapshot(Path(DATA_PATH).stat().st_mtime_ns)
except (OSError, ValueError) as error:
    st.error(f"Could not load the review snapshot: {error}")
    st.stop()

with st.sidebar:
    st.header("Your sourcing scope")
    origins = sorted(data["Origin"].unique().tolist())
    styles = sorted(data["Style"].unique().tolist())
    selected_origins = st.multiselect("Origin country / region", origins, default=origins)
    selected_styles = st.multiselect("Packaging", styles, default=styles)
    st.caption("Choose origins your suppliers serve and packaging your store can stock. Clear a selection to return no records.")
    st.divider()
    st.markdown("**Shortlist rule: ≥ 4 / 5 stars**")
    st.caption("A proposed tasting screen, not a validated predictor of demand. Brand comparisons need at least 5 scored review records in the selected scope.")
    st.markdown("[Dataset and provenance](https://www.kaggle.com/datasets/residentmario/ramen-ratings)")

scope = filter_data(data, selected_origins, selected_styles)
metrics = headline(scope)
excluded = int(scope["Score"].isna().sum())
st.info("Historical reviewer opinions, not current sales or customer demand. Use this shortlist for sample requests; verify availability, cost, margin and local tasting results before buying.")
first, second, third = st.columns(3)
first.metric("Scored review records", f"{metrics['rated']:,}")
second.metric("High-rated records · ≥ 4 / 5", f"{metrics['high']:,}")
third.metric("High-rated share", f"{metrics['share']:.1%}" if metrics["share"] is not None else "N/A")
st.caption(f"All metrics and charts use the selected scope. High-rated share = high-rated / scored records. Unscored or invalid records excluded in scope: {excluded}. Records are reviews, not unique SKUs.")
if not metrics["rated"]:
    st.warning("No scored reviews match this scope. Select at least one origin and packaging type, or broaden your choices.")
    st.stop()
if metrics["high"]:
    st.markdown(f"**Next step:** inspect the {metrics['high']:,} high-rated review records below and choose samples that your suppliers can provide.")
else:
    st.markdown("**Next step:** no reviews pass the tasting screen in this scope. Broaden the scope or assess products manually; this is not evidence of poor demand.")

left, right = st.columns([1.15, 1])
with left:
    st.subheader("Which brands merit a closer look?")
    brands = brand_summary(scope)
    if brands.empty:
        st.info("No brand has 5 scored records in this scope. Review individual candidates below; coverage is too small for a brand comparison.")
    else:
        shown = brands.head(12).copy()
        shown["Label"] = shown["Brand"] + "  (n=" + shown["rated"].astype(str) + ")"
        bars = alt.Chart(shown).mark_bar(color="#C75B39", cornerRadiusEnd=3).encode(
            x=alt.X("share:Q", title="Share rated ≥ 4 / 5", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%")),
            y=alt.Y("Label:N", sort=shown["Label"].tolist(), title=None),
            tooltip=[alt.Tooltip("Brand:N"), alt.Tooltip("rated:Q", title="Scored records"), alt.Tooltip("high:Q", title="High-rated records"), alt.Tooltip("share:Q", title="High-rated share", format=".1%")],
        ).properties(height=340)
        st.altair_chart(bars, width="stretch")
        st.caption(f"Top {len(shown)} of {len(brands)} eligible brands, ordered by share, scored count, then name. Minimum {MIN_BRAND_RECORDS} scored records per brand. These are product reviews, not repeat ratings of one product; small n still gives weak evidence.")
with right:
    st.subheader("How broad is the rating spread?")
    rated = scope.dropna(subset=["Score"])
    distribution = alt.Chart(rated).mark_bar(color="#427A78").encode(
        x=alt.X("Score:Q", bin=alt.Bin(step=0.5, extent=[0, 5]), title="Reviewer score / 5", scale=alt.Scale(domain=[0, 5])),
        y=alt.Y("count():Q", title="Review records"),
        tooltip=[alt.Tooltip("Score:Q", bin=alt.Bin(step=0.5, extent=[0, 5]), title="Score interval"), alt.Tooltip("count():Q", title="Records")],
    ).properties(height=340)
    cutoff = alt.Chart().mark_rule(color="#C75B39", strokeDash=[5, 4]).encode(x=alt.datum(THRESHOLD))
    st.altair_chart(distribution + cutoff, width="stretch")
    st.caption("Half-point bins; the dashed line is the ≥ 4 tasting screen. Valid zero-star reviews are retained. No time trend is implied.")

st.subheader("Review the tasting candidates")
candidates = shortlist(scope).rename(columns={"Score": "Stars / 5", "Origin": "Origin country / region"})
st.caption("Sorted by score, brand, product and review ID. Repeated descriptions remain separate review records: reconcile supplier SKUs before requesting duplicate samples. Export includes every matching candidate.")
st.dataframe(candidates, hide_index=True, width="stretch", height=330)
st.download_button("Download candidate reviews (CSV)", candidates.to_csv(index=False).encode("utf-8-sig"), "ramen-tasting-candidates.csv", "text/csv")
with st.expander("Source, refresh and interpretation"):
    st.markdown("""
    Source: [Ramen Ratings on Kaggle](https://www.kaggle.com/datasets/residentmario/ramen-ratings),
    an export of [The Ramen Rater's Big List](https://www.theramenrater.com/resources-2/the-list/).
    The referenced Kaggle version was last updated on 11 January 2018; this is a publication
    timestamp, **not** the start or end of the reviews. The CSV has no review dates.

    This demo reads a static CSV with **no automatic feed**. In production, ingest an authorized
    review snapshot weekly on Sunday, validate it, record the successful ingestion timestamp
    and compare snapshots. Review on Monday before requesting samples. Flag ingestion over
    7 days old and verify the feed before relying on changes.

    The reviewer selects products, so this is not a representative market sample.
    Missing `Style` becomes `Unknown`; `Unrated` and invalid scores are excluded from rating
    denominators. Missing `Top Ten` does not imply poor quality and is not used.
    Origins are countries / regions, not sales territories. No sales, prices, stock, margin,
    consumer demographics or current supplier availability are available.
    """)
