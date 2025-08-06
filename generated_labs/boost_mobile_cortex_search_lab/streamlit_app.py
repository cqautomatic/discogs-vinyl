import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session

def main():
    st.title("🔍 Boost Mobile Search Assistant")
    st.markdown("**Powered by Snowflake Cortex Search**")
    
    # Get Snowflake session
    session = get_active_session()
    
    # Search interface
    query = st.text_input(
        "Search Boost Mobile knowledge base:",
        placeholder="Ask about policies, procedures, or any company information..."
    )
    
    if query and st.button("Search", type="primary"):
        with st.spinner("Searching Boost Mobile documents..."):
            try:
                # Execute Cortex Search
                search_sql = f"""
                SELECT relative_path, file_content, RANK
                FROM TABLE(BOOST MOBILE_CORTEX_SEARCH_DEMO.DOCS.BOOST MOBILE_SEARCH_APP!SEARCH('{query}'))
                LIMIT 5
                """
                
                results = session.sql(search_sql).collect()
                
                if results:
                    st.success(f"Found {len(results)} relevant results")
                    
                    for i, row in enumerate(results, 1):
                        with st.expander(f"📄 {row['RELATIVE_PATH']} (Rank: {row['RANK']:.2f})"):
                            st.text_area(
                                "Content:",
                                row['FILE_CONTENT'][:500] + "..." if len(row['FILE_CONTENT']) > 500 else row['FILE_CONTENT'],
                                height=150,
                                key=f"content_{i}"
                            )
                else:
                    st.warning("No results found. Try a different search term.")
                    
            except Exception as e:
                st.error(f"Search error: {str(e)}")
    
    # Sample queries
    st.sidebar.markdown("### 💡 Try these sample queries:")
    sample_queries = [
        "What are the company policies?",
        "How do I contact support?",
        "What are the office hours?",
        "Employee benefits information",
        "Code of conduct guidelines"
    ]
    
    for query_text in sample_queries:
        if st.sidebar.button(query_text):
            st.experimental_set_query_params(query=query_text)
            st.experimental_rerun()

if __name__ == "__main__":
    main()
