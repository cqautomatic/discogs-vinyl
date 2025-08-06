#!/usr/bin/env python3
"""
Snowflake Quickstart Lab Generator
Transform official Snowflake quickstarts into company-branded 15-minute hands-on labs.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

class SnowflakeLabGenerator:
    def __init__(self):
        self.templates_dir = Path("templates")
        self.output_dir = Path("generated_labs")
        
    def extract_company_name(self, text: str) -> str:
        """Extract company name from 'for [Company]' or 'called [Company]' patterns."""
        patterns = [
            r'for\s+([A-Z][a-zA-Z\s&]+)',
            r'called\s+([A-Z][a-zA-Z\s&]+)',
            r'company\s+([A-Z][a-zA-Z\s&]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "YourCompany"
    
    def sanitize_name(self, company_name: str) -> str:
        """Convert company name to lowercase directory-safe name."""
        return re.sub(r'[^a-zA-Z0-9]', '_', company_name.lower()).strip('_')
    
    def generate_cortex_search_lab(self, company_name: str, industry_context: Dict) -> None:
        """Generate Cortex Search lab structure."""
        safe_name = self.sanitize_name(company_name)
        lab_dir = self.output_dir / f"{safe_name}_cortex_search_lab"
        
        # Create directory structure
        lab_dir.mkdir(parents=True, exist_ok=True)
        (lab_dir / "sample_docs").mkdir(exist_ok=True)
        
        # Generate README.md
        readme_content = self._generate_search_readme(company_name, industry_context)
        (lab_dir / "README.md").write_text(readme_content)
        
        # Generate setup.sql
        setup_sql = self._generate_search_setup_sql(company_name, safe_name)
        (lab_dir / "setup.sql").write_text(setup_sql)
        
        # Generate Streamlit app
        streamlit_app = self._generate_search_streamlit(company_name, safe_name)
        (lab_dir / "streamlit_app.py").write_text(streamlit_app)
        
        # Generate sample documents
        self._generate_sample_docs(lab_dir / "sample_docs", company_name, industry_context)
        
        print(f"✅ Generated Cortex Search lab: {lab_dir}")
    
    def generate_cortex_analyst_lab(self, company_name: str, industry_context: Dict) -> None:
        """Generate Cortex Analyst lab structure."""
        safe_name = self.sanitize_name(company_name)
        lab_dir = self.output_dir / f"{safe_name}_cortex_analyst_lab"
        
        # Create directory structure
        lab_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate README.md
        readme_content = self._generate_analyst_readme(company_name, industry_context)
        (lab_dir / "README.md").write_text(readme_content)
        
        # Generate setup.sql with INSERT statements
        setup_sql = self._generate_analyst_setup_sql(company_name, safe_name, industry_context)
        (lab_dir / "setup.sql").write_text(setup_sql)
        
        # Generate Streamlit app
        streamlit_app = self._generate_analyst_streamlit(company_name, safe_name)
        (lab_dir / "streamlit_app.py").write_text(streamlit_app)
        
        # Generate semantic model
        semantic_model = self._generate_semantic_model(company_name, industry_context)
        (lab_dir / "semantic_model.yaml").write_text(yaml.dump(semantic_model, default_flow_style=False))
        
        print(f"✅ Generated Cortex Analyst lab: {lab_dir}")
    
    def _generate_search_readme(self, company_name: str, industry_context: Dict) -> str:
        return f"""# {company_name} Cortex Search Lab

## Overview
Learn how to build an intelligent search assistant for {company_name} using Snowflake Cortex Search. This 15-minute hands-on lab will guide you through creating a semantic search application over {company_name}'s {industry_context.get('documents', 'documents')}.

## Prerequisites
- Snowflake account with Cortex Search enabled
- Basic familiarity with SQL and Streamlit

## Lab Steps

### Step 1: Environment Setup (3 minutes)
1. Open Snowsight and run the setup script:
```sql
-- Execute setup.sql to create database and stage
```

### Step 2: Upload Sample Documents (2 minutes)
1. Navigate to Data > Databases > {company_name.upper()}_CORTEX_SEARCH_DEMO > DOCS > Stages > DOCS_STAGE
2. Upload all files from the `sample_docs/` folder
3. Verify files are uploaded successfully

### Step 3: Create Cortex Search Service (3 minutes)
```sql
-- Create the search service over uploaded documents
CREATE OR REPLACE CORTEX SEARCH APPLICATION {company_name.upper()}_SEARCH_APP
ON docs_table
WAREHOUSE = COMPUTE_WH
ATTRIBUTES = (relative_path, file_content)
SERVICE_NAME = '{company_name.lower()}_search_service';
```

### Step 4: Test Search Functionality (2 minutes)
```sql
-- Test semantic search
SELECT relative_path, file_content
FROM TABLE({company_name.upper()}_SEARCH_APP!SEARCH('{industry_context.get('sample_query', 'company policies')}'));
```

### Step 5: Deploy Streamlit App (5 minutes)
1. Create new Streamlit app in Snowsight
2. Copy code from `streamlit_app.py`
3. Run the app and test with sample queries:
   - "{industry_context.get('sample_queries', ['What are the company policies?'])[0]}"
   - "{industry_context.get('sample_queries', ['How do I contact support?'])[1] if len(industry_context.get('sample_queries', [])) > 1 else 'How do I get help?'}"

## Expected Results
- Functional semantic search over {company_name} documents
- Interactive Streamlit interface for querying company knowledge
- Understanding of Cortex Search capabilities

## Next Steps
- Add more company-specific documents
- Implement advanced filtering and ranking
- Integrate with existing {company_name} systems
"""

    def _generate_search_setup_sql(self, company_name: str, safe_name: str) -> str:
        return f"""-- {company_name} Cortex Search Lab Setup
-- Creates database, schema, stage, and table structure

-- Create database and schema
CREATE OR REPLACE DATABASE {company_name.upper()}_CORTEX_SEARCH_DEMO;
CREATE OR REPLACE SCHEMA DOCS;
USE DATABASE {company_name.upper()}_CORTEX_SEARCH_DEMO;
USE SCHEMA DOCS;

-- Create stage for document uploads
CREATE OR REPLACE STAGE docs_stage
  FILE_FORMAT = (TYPE = 'JSON' STRIP_OUTER_ARRAY = FALSE);

-- Create table to hold document content
CREATE OR REPLACE TABLE docs_table (
    relative_path VARCHAR,
    file_content VARCHAR
);

-- Create warehouse if not exists
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE {company_name.upper()}_CORTEX_SEARCH_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA DOCS TO ROLE PUBLIC;
GRANT ALL ON TABLE docs_table TO ROLE PUBLIC;
GRANT ALL ON STAGE docs_stage TO ROLE PUBLIC;

SELECT 'Setup completed! Ready to upload documents to stage.' as status;
"""

    def _generate_search_streamlit(self, company_name: str, safe_name: str) -> str:
        company_upper = company_name.upper()
        return f"""import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session

def main():
    st.title("🔍 {company_name} Search Assistant")
    st.markdown("**Powered by Snowflake Cortex Search**")
    
    # Get Snowflake session
    session = get_active_session()
    
    # Search interface
    query = st.text_input(
        "Search {company_name} knowledge base:",
        placeholder="Ask about policies, procedures, or any company information..."
    )
    
    if query and st.button("Search", type="primary"):
        with st.spinner("Searching {company_name} documents..."):
            try:
                # Execute Cortex Search
                search_sql = f\"\"\"
                SELECT relative_path, file_content, RANK
                FROM TABLE({company_upper}_CORTEX_SEARCH_DEMO.DOCS.{company_upper}_SEARCH_APP!SEARCH('{{query}}'))
                LIMIT 5
                \"\"\"
                
                results = session.sql(search_sql).collect()
                
                if results:
                    st.success(f"Found {{len(results)}} relevant results")
                    
                    for i, row in enumerate(results, 1):
                        with st.expander(f"📄 {{row['RELATIVE_PATH']}} (Rank: {{row['RANK']:.2f}})"):
                            st.text_area(
                                "Content:",
                                row['FILE_CONTENT'][:500] + "..." if len(row['FILE_CONTENT']) > 500 else row['FILE_CONTENT'],
                                height=150,
                                key=f"content_{{i}}"
                            )
                else:
                    st.warning("No results found. Try a different search term.")
                    
            except Exception as e:
                st.error(f"Search error: {{str(e)}}")
    
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
"""

    def _generate_sample_docs(self, docs_dir: Path, company_name: str, industry_context: Dict) -> None:
        """Generate sample documents for the company."""
        
        # Company Policies
        (docs_dir / "company_policies.txt").write_text(f"""{company_name} Company Policies

1. Work Hours
Standard business hours are Monday through Friday, 9:00 AM to 5:00 PM.
Remote work is available with manager approval.

2. Communication Guidelines
All official communications should use company email.
Slack is available for informal team communication.

3. Equipment Policy
Company laptops must be returned upon termination.
Personal use of company equipment is permitted for reasonable use.

4. Time Off Policy
Employees accrue 15 days of vacation per year.
Sick leave is available as needed with proper documentation.

5. Code of Conduct
Maintain professional behavior at all times.
Report any violations to HR immediately.
""")

        # FAQ Document
        (docs_dir / "faq.txt").write_text(f"""{company_name} Frequently Asked Questions

Q: How do I reset my password?
A: Contact IT support at it-support@{company_name.lower().replace(' ', '')}.com or call ext. 1234.

Q: What are the office hours?
A: Our offices are open Monday through Friday from 8:00 AM to 6:00 PM.

Q: How do I request time off?
A: Submit requests through the HR portal or email hr@{company_name.lower().replace(' ', '')}.com.

Q: Where can I find the employee handbook?
A: The handbook is available on the company intranet under Resources.

Q: Who do I contact for IT issues?
A: For technical support, email it-support@{company_name.lower().replace(' ', '')}.com or call extension 1234.

Q: How do I submit an expense report?
A: Use the expense reporting system in the finance portal or contact accounting@{company_name.lower().replace(' ', '')}.com.
""")

        # Employee Benefits
        (docs_dir / "employee_benefits.txt").write_text(f"""{company_name} Employee Benefits Guide

Health Insurance
- Comprehensive medical, dental, and vision coverage
- Company pays 80% of premiums for employees
- Family coverage available at reduced rates

Retirement Plan
- 401(k) plan with company matching up to 4%
- Immediate vesting of company contributions
- Multiple investment options available

Paid Time Off
- 15 vacation days per year (increases with tenure)
- 10 sick days per year
- 12 company holidays

Professional Development
- $2,000 annual training budget per employee
- Conference attendance encouraged
- Internal mentorship programs

Additional Benefits
- Flexible work arrangements
- Employee assistance program
- Life and disability insurance
- Commuter benefits program
""")

        # Contact Directory
        (docs_dir / "contact_directory.txt").write_text(f"""{company_name} Contact Directory

Executive Team
- CEO: ceo@{company_name.lower().replace(' ', '')}.com
- COO: coo@{company_name.lower().replace(' ', '')}.com
- CFO: cfo@{company_name.lower().replace(' ', '')}.com

Department Contacts
- Human Resources: hr@{company_name.lower().replace(' ', '')}.com | Ext: 1100
- Information Technology: it-support@{company_name.lower().replace(' ', '')}.com | Ext: 1234
- Finance/Accounting: accounting@{company_name.lower().replace(' ', '')}.com | Ext: 1200
- Sales: sales@{company_name.lower().replace(' ', '')}.com | Ext: 1300
- Marketing: marketing@{company_name.lower().replace(' ', '')}.com | Ext: 1400

Emergency Contacts
- Building Security: Ext: 911
- Facilities Management: facilities@{company_name.lower().replace(' ', '')}.com | Ext: 1500

Office Locations
- Main Office: 123 Business Plaza, Suite 456, City, State 12345
- Branch Office: 789 Corporate Blvd, City, State 67890
""")

        # Office Procedures
        (docs_dir / "office_procedures.txt").write_text(f"""{company_name} Office Procedures

Building Access
- Badge required for entry after 6:00 PM and weekends
- Visitors must sign in at reception
- Tailgating is strictly prohibited

Meeting Room Reservations
- Use the online booking system to reserve conference rooms
- Maximum 2-hour bookings during peak hours (9 AM - 3 PM)
- Clean up after meetings

Parking
- Assigned spots for full-time employees
- Visitor parking available in designated areas
- Carpooling encouraged - contact facilities for preferred spots

Mail and Packages
- Personal packages can be delivered to the office
- All mail is distributed daily by 2:00 PM
- For urgent items, contact reception

Emergency Procedures
- Fire exits are clearly marked throughout the building
- Assembly point is the parking lot across the street
- Report emergencies to security immediately

Food and Kitchen
- Refrigerator is cleaned weekly on Fridays
- Label all personal items
- Coffee and basic supplies provided
""")

    def _generate_analyst_readme(self, company_name: str, industry_context: Dict) -> str:
        entity = industry_context.get('primary_entity', 'transactions')
        return f"""# {company_name} Cortex Analyst Lab

## Overview
Build an AI-powered analytics assistant for {company_name} using Snowflake Cortex Analyst. This 15-minute lab demonstrates natural language querying over {company_name}'s {entity} data.

## Prerequisites
- Snowflake account with Cortex Analyst enabled
- Basic understanding of SQL and analytics

## Lab Steps

### Step 1: Database Setup (2 minutes)
Execute `setup.sql` to create database and insert sample data:
```sql
-- Creates {company_name.upper()}_CORTEX_ANALYST_DEMO database
-- Inserts {industry_context.get('record_count', '1000')} sample records
```

### Step 2: Create Semantic Model (3 minutes)
1. Upload `semantic_model.yaml` to a stage
2. Create the semantic model:
```sql
CREATE OR REPLACE CORTEX SEARCH APPLICATION {company_name.upper()}_ANALYST_APP
ON {entity}_table
WAREHOUSE = COMPUTE_WH
SEMANTIC_MODEL = '@MODELS_STAGE/semantic_model.yaml';
```

### Step 3: Test Natural Language Queries (5 minutes)
```sql
-- Ask questions in plain English
SELECT SNOWFLAKE.CORTEX.ANALYST_QUERY(
    '{company_name.upper()}_ANALYST_APP',
    'What are the top {industry_context.get('top_n', '5')} {entity} by {industry_context.get('metric', 'revenue')}?'
);
```

### Step 4: Deploy Analytics Dashboard (5 minutes)
1. Create Streamlit app with `streamlit_app.py`
2. Test with sample questions:
   - "{industry_context.get('sample_questions', ['What are the trends?'])[0]}"
   - "{industry_context.get('sample_questions', ['Show me the performance metrics'])[1] if len(industry_context.get('sample_questions', [])) > 1 else 'What are the key insights?'}"

## Expected Results
- Natural language interface for {company_name} analytics
- Automated chart generation and insights
- Understanding of Cortex Analyst capabilities

## Sample Queries to Try
- "Show me monthly trends"
- "What are the top performers?"
- "Compare performance by category"
- "Identify any anomalies or outliers"
"""

    def _generate_analyst_setup_sql(self, company_name: str, safe_name: str, industry_context: Dict) -> str:
        entity = industry_context.get('primary_entity', 'transactions')
        return f"""-- {company_name} Cortex Analyst Lab Setup
-- Creates database with sample {entity} data

-- Create database and schema
CREATE OR REPLACE DATABASE {company_name.upper()}_CORTEX_ANALYST_DEMO;
CREATE OR REPLACE SCHEMA ANALYTICS;
USE DATABASE {company_name.upper()}_CORTEX_ANALYST_DEMO;
USE SCHEMA ANALYTICS;

-- Create {entity} table
CREATE OR REPLACE TABLE {entity}_table (
    id INTEGER,
    date DATE,
    category VARCHAR(50),
    amount DECIMAL(10,2),
    region VARCHAR(50),
    customer_segment VARCHAR(50),
    product_line VARCHAR(50)
);

-- Insert sample data
INSERT INTO {entity}_table VALUES
{self._generate_sample_data(industry_context)}

-- Create stage for semantic model
CREATE OR REPLACE STAGE models_stage;

-- Create warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE {company_name.upper()}_CORTEX_ANALYST_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA ANALYTICS TO ROLE PUBLIC;
GRANT ALL ON TABLE {entity}_table TO ROLE PUBLIC;
GRANT ALL ON STAGE models_stage TO ROLE PUBLIC;

SELECT 'Setup completed! Sample data loaded successfully.' as status;
SELECT COUNT(*) as record_count FROM {entity}_table;
"""

    def _generate_sample_data(self, industry_context: Dict) -> str:
        """Generate INSERT statements for sample data."""
        # This is a simplified version - in real implementation, 
        # would generate more sophisticated sample data
        data_lines = []
        categories = industry_context.get('categories', ['Category A', 'Category B', 'Category C'])
        regions = ['North', 'South', 'East', 'West']
        segments = ['Enterprise', 'SMB', 'Consumer']
        products = ['Product 1', 'Product 2', 'Product 3']
        
        import random
        import datetime
        
        base_date = datetime.date(2023, 1, 1)
        for i in range(50):  # 50 sample records for demo
            date = base_date + datetime.timedelta(days=random.randint(0, 365))
            category = random.choice(categories)
            amount = round(random.uniform(100, 10000), 2)
            region = random.choice(regions)
            segment = random.choice(segments)
            product = random.choice(products)
            
            data_lines.append(f"({i+1}, '{date}', '{category}', {amount}, '{region}', '{segment}', '{product}')")
        
        return ',\n'.join(data_lines) + ';'

    def _generate_analyst_streamlit(self, company_name: str, safe_name: str) -> str:
        company_upper = company_name.upper()
        return f"""import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session
import json

def main():
    st.title("📊 {company_name} Analytics Assistant")
    st.markdown("**Ask questions about your data in natural language**")
    
    # Get Snowflake session
    session = get_active_session()
    
    # Query interface
    question = st.text_input(
        "Ask a question about {company_name} data:",
        placeholder="What are the top performing products this quarter?"
    )
    
    if question and st.button("Ask", type="primary"):
        with st.spinner("Analyzing data..."):
            try:
                # Execute Cortex Analyst query
                query_sql = f\"\"\"
                SELECT SNOWFLAKE.CORTEX.ANALYST_QUERY(
                    '{company_upper}_CORTEX_ANALYST_DEMO.ANALYTICS.{company_upper}_ANALYST_APP',
                    '{{question}}'
                ) as response
                \"\"\"
                
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
                            st.write(f"• {{insight}}")
                            
                else:
                    st.warning("No response received. Please try again.")
                    
            except Exception as e:
                st.error(f"Analysis error: {{str(e)}}")
    
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
"""

    def _generate_semantic_model(self, company_name: str, industry_context: Dict) -> Dict:
        entity = industry_context.get('primary_entity', 'transactions')
        return {
            'name': f'{company_name}AnalyticsModel',
            'description': f'Semantic model for {company_name} {entity} analytics',
            'tables': [
                {
                    'name': f'{entity}_table',
                    'description': f'{company_name} {entity} data',
                    'columns': [
                        {'name': 'id', 'type': 'integer', 'description': f'{entity.title()} identifier'},
                        {'name': 'date', 'type': 'date', 'description': f'{entity.title()} date'},
                        {'name': 'category', 'type': 'string', 'description': f'{entity.title()} category'},
                        {'name': 'amount', 'type': 'decimal', 'description': f'{entity.title()} amount in dollars'},
                        {'name': 'region', 'type': 'string', 'description': 'Geographic region'},
                        {'name': 'customer_segment', 'type': 'string', 'description': 'Customer segment classification'},
                        {'name': 'product_line', 'type': 'string', 'description': 'Product line category'}
                    ]
                }
            ],
            'measures': [
                {
                    'name': 'total_amount',
                    'type': 'sum',
                    'column': 'amount',
                    'description': f'Total {entity} amount'
                },
                {
                    'name': 'avg_amount', 
                    'type': 'average',
                    'column': 'amount',
                    'description': f'Average {entity} amount'
                },
                {
                    'name': 'transaction_count',
                    'type': 'count',
                    'column': 'id', 
                    'description': f'Number of {entity}'
                }
            ],
            'dimensions': [
                {'name': 'category', 'type': 'string'},
                {'name': 'region', 'type': 'string'},
                {'name': 'customer_segment', 'type': 'string'},
                {'name': 'product_line', 'type': 'string'},
                {'name': 'date', 'type': 'date'}
            ]
        }

# Industry context configurations
INDUSTRY_CONTEXTS = {
    'boost_mobile': {
        'primary_entity': 'sales',
        'categories': ['Prepaid Plans', 'Postpaid Plans', 'Devices', 'Accessories'],
        'documents': 'customer support documents and service policies',
        'sample_query': 'mobile plan features',
        'sample_queries': ['What are the available mobile plans?', 'How do I upgrade my device?'],
        'sample_questions': ['What are the monthly sales trends by plan type?', 'Which regions have the highest device sales?'],
        'record_count': '2000',
        'metric': 'revenue',
        'top_n': '5'
    },
    'tesla': {
        'primary_entity': 'vehicle_sales',
        'categories': ['Model S', 'Model 3', 'Model X', 'Model Y'],
        'documents': 'vehicle specifications and service manuals',
        'sample_query': 'Tesla model features',
        'sample_queries': ['What are the Tesla model specifications?', 'How do I schedule service?'],
        'sample_questions': ['What are the top selling Tesla models?', 'Show me quarterly delivery trends'],
        'record_count': '1500',
        'metric': 'units_sold',
        'top_n': '4'
    },
    'amazon': {
        'primary_entity': 'product_sales',
        'categories': ['Electronics', 'Books', 'Clothing', 'Home & Garden'],
        'documents': 'product catalogs and customer service guides',
        'sample_query': 'product information',
        'sample_queries': ['What products are available?', 'How do I return an item?'],
        'sample_questions': ['What are the best selling products?', 'Show me sales performance by category'],
        'record_count': '5000',
        'metric': 'revenue',
        'top_n': '10'
    }
}

def main():
    """Main function to generate labs."""
    generator = SnowflakeLabGenerator()
    
    # Example: Generate Boost Mobile labs
    company_name = "Boost Mobile"
    industry_context = INDUSTRY_CONTEXTS['boost_mobile']
    
    print(f"🚀 Generating Snowflake labs for {company_name}...")
    
    # Generate both types of labs
    generator.generate_cortex_search_lab(company_name, industry_context)
    generator.generate_cortex_analyst_lab(company_name, industry_context)
    
    print(f"\n✨ Lab generation completed!")
    print(f"📁 Check the 'generated_labs' directory for your {company_name} labs")

if __name__ == "__main__":
    main()