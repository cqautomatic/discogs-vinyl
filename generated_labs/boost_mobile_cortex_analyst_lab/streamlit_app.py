import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session
import json

def main():
    st.title("📊 Boost Mobile Analytics Assistant")
    st.markdown("**Ask questions about your data in natural language**")
    
    # Get Snowflake session
    session = get_active_session()
    
    # Query interface
    question = st.text_input(
        "Ask a question about Boost Mobile data:",
        placeholder="What are the top performing products this quarter?"
    )
    
    if question and st.button("Ask", type="primary"):
        with st.spinner("Analyzing data..."):
            try:
                # Execute Cortex Analyst query
                query_sql = f"""
                SELECT SNOWFLAKE.CORTEX.ANALYST_QUERY(
                    'BOOST MOBILE_CORTEX_ANALYST_DEMO.ANALYTICS.BOOST MOBILE_ANALYST_APP',
                    '{question}'
                ) as response
                """
                
                result = session.sql(query_sql).collect()
                
                if result:
                    response = json.loads(result[0]['RESPONSE'])
                    
                    # Display SQL generated
                    if 'sql' in response:
                        with st.expander("📝 Generated SQL"):
                            st.code(response['sql'], language='sql')
                    
                    # Display results
                    if 'data' in response:
                        st.subheader("📈 Results")
                        st.dataframe(response['data'])
                    
                    # Display insights
                    if 'insights' in response:
                        st.subheader("💡 Key Insights")
                        for insight in response['insights']:
                            st.write(f"• {insight}")
                            
                else:
                    st.warning("No response received. Please try again.")
                    
            except Exception as e:
                st.error(f"Analysis error: {str(e)}")
    
    # Sample questions
    st.sidebar.markdown("### 🤔 Sample Questions:")
    sample_questions = [
        "What are the monthly revenue trends?",
        "Which regions are performing best?", 
        "Show me top products by sales",
        "Compare performance across customer segments",
        "What are the seasonal patterns?"
    ]
    
    for question_text in sample_questions:
        if st.sidebar.button(question_text):
            st.experimental_set_query_params(question=question_text)
            st.experimental_rerun()

if __name__ == "__main__":
    main()
