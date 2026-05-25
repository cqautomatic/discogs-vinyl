import streamlit as st
import pandas as pd
from snowflake.snowpark import Session
import os

st.set_page_config(page_title='Discogs Collection (SiS)', page_icon='🎵', layout='wide')

@st.cache_resource
def get_session():
    return Session.builder.configs({
        "account": os.getenv('SNOWFLAKE_ACCOUNT'),
        "user": os.getenv('SNOWFLAKE_USER'),
        "password": os.getenv('SNOWFLAKE_PASSWORD'),
        "role": os.getenv('SNOWFLAKE_ROLE', 'DISCOGS_READER_ROLE'),
        "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'DISCOGS_WH'),
        "database": os.getenv('SNOWFLAKE_DATABASE', 'DISCOGS_DB'),
        "schema": os.getenv('SNOWFLAKE_SCHEMA', 'COLLECTION_DATA'),
    }).create()


def load_collection_stats(session: Session) -> pd.DataFrame:
    # Approximate stats from releases
    df = session.sql(
        """
        SELECT
          COUNT(*) AS total_items,
          COUNT(DISTINCT ARTIST) AS unique_artists,
          COUNT(DISTINCT LABEL) AS unique_labels,
          MIN(NULLIF(YEAR, 0)) AS earliest_year,
          MAX(NULLIF(YEAR, 0)) AS latest_year,
          AVG(NULLIF(COMMUNITY_AVERAGE_RATING, 0)) AS avg_community_rating
        FROM RELEASES
        """
    ).to_pandas()
    return df


def load_decade_analysis(session: Session) -> pd.DataFrame:
    df = session.sql(
        """
        WITH base AS (
          SELECT YEAR FROM RELEASES WHERE YEAR IS NOT NULL AND YEAR >= 1950
        )
        SELECT (YEAR/10)*10 AS decade, COUNT(*) AS release_count
        FROM base
        GROUP BY (YEAR/10)*10
        ORDER BY decade
        """
    ).to_pandas()
    return df


def main():
    st.title('🎵 Discogs Collection (SiS)')
    session = get_session()

    st.subheader('Overview')
    stats = load_collection_stats(session)
    if not stats.empty:
        s = stats.iloc[0]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric('Total Items', int(s.get('TOTAL_ITEMS') or 0))
        with c2:
            st.metric('Unique Artists', int(s.get('UNIQUE_ARTISTS') or 0))
        with c3:
            st.metric('Unique Labels', int(s.get('UNIQUE_LABELS') or 0))
    else:
        st.info('No data loaded yet')

    st.subheader('Releases by Decade')
    dec = load_decade_analysis(session)
    if not dec.empty:
        st.bar_chart(dec.set_index('DECADE')['RELEASE_COUNT'])
    else:
        st.info('No decade data available')

if __name__ == '__main__':
    main()
