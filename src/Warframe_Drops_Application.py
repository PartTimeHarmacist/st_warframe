import streamlit as st
import pandas as pd
from collections.abc import Sequence
from sqlalchemy.sql import text
import re
from pathlib import Path

st.set_page_config(
    page_title="Warframe Drops Application",
    layout="wide"
)

conn = st.connection("postgresql", type="sql")

docs_root = Path("/home/appuser/app/repo")
if not docs_root.exists():
    docs_root = Path.cwd()

docs_root = docs_root / "src" / "docs"

@st.cache_data(ttl=3600)
@st.fragment
def retrieve_warframe_drop_tables() -> Sequence:
    with conn.session as s:
        rtn = s.execute(
            text("SELECT * FROM warframe_drops;")
        )
        s.commit()
    return rtn.fetchall()

@st.fragment
def get_missions_for_item(
        search_target: str,
        exclude: bool = False,
        selected_missions: list[str] = None,
        only_rarities: float = None
) -> pd.DataFrame:

    results = drop_tables[drop_tables["drop"].str.lower().str.contains(search_target.lower().strip())]

    if not (relic_results := results[results["drop_table_type"] == "Relics"]).empty:
        # Item is in a relic, or its parts are in a relic
        # Narrow down the relics to ignore the refined options
        relic_results = relic_results[relic_results["selector"].str.contains("(Intact)", regex=False)]

        relic_list = relic_results["selector"].to_list()
        relic_list = [r.rstrip("(Intact)").strip() for r in relic_list]

        missions = drop_tables[drop_tables["drop"].isin(relic_list)]

        if missions.empty:
            return missions

        if selected_missions:
            if exclude:
                missions = missions[
                    missions["selector"].apply(lambda x: not any(e in x for e in selected_missions))
                ]
            else:
                missions = missions[
                    missions["selector"].apply(lambda x: any(e in x for e in selected_missions))
                ]

        if rarity_pct_above:
            missions = missions[missions["chance_pct"] >= only_rarities]

        if missions.empty:
            return missions

        missions.sort_values(["drop", "chance_pct"], axis=0, ascending=False, inplace=True)
        return missions

    return relic_results


st.write("### Warframe Drops Application")

st.markdown(retrieve_doc_file("intro_header.md"))

drop_tables = pd.DataFrame(retrieve_warframe_drop_tables())
drop_tables = drop_tables[["drop_table_type", "selector", "rotation", "drop", "chance_desc", "chance_pct"]]

mission_re = re.compile(r"\((?P<mt>.*?)\)", re.I)
mission_types = drop_tables[drop_tables["drop_table_type"] == "Missions"]["selector"].unique()
mission_types = list(set([m.removesuffix("(Hard)").removesuffix("(Normal)").removesuffix("Extra") for m in mission_types]))
mission_types = [mission_re.findall(m)[-1] if mission_re.search(m) else m for m in mission_types]
mission_types = sorted(list(set(mission_types)))

# st.dataframe(drop_tables)

col1, col2, col3 = st.columns(3)
col2a, col2b = col2.columns(2)

target = col1.text_input("Item/Warframe to Search for", placeholder="Trumna")

exclude_include = col2a.toggle("Exclude")
selected_mission_types = col2b.multiselect(
    f"Mission types to {'Ex' if exclude_include else 'In'}clude",
    mission_types,
    placeholder="Disruption"
)

rarity_pct_above = col3.number_input(
    "Minimum Rarity Percentage",
    min_value=0,
    max_value=100,
    placeholder=5
)

st.columns(1)

if target:
    results = get_missions_for_item(target, exclude_include, selected_mission_types, rarity_pct_above)
    top_results = results.groupby("drop").head(1)
    top_missions = top_results.groupby("selector")["drop"].count()

    col1, col2 = st.columns(2)

    col1.write("Top Missions")
    col1.dataframe(
        top_missions,
        use_container_width=True,
        hide_index=False
    )

    col2.write("Top Results")
    col2.dataframe(
        top_results,
        use_container_width=True,
        hide_index=True
    )

    st.columns(1)

    st.write("All Results")
    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True
    )


