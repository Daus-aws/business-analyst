import streamlit as st
import pandas as pd
import re
import os

# Function to extract columns and data types from Excel
def extract_excel_columns(file, header_row):
    df = pd.read_excel(file, header=header_row)
    column_types = df.dtypes.reset_index()
    column_types.columns = ['Column Names', 'Data Type']
    return column_types

# Function to parse SQL file and extract table and column information
def parse_sql_file(file_path):
    table_data = {}
    create_table_pattern = re.compile(r'CREATE TABLE `(\w+)`', re.I)
    column_pattern = re.compile(
        r'`(\w+)` ([\w\(\) ]+)( NOT NULL)?( AUTO_INCREMENT)?( PRIMARY KEY)?( DEFAULT (.*?))?( (.*?))?( COMMENT (.*?))?[,)]',
        re.I
    )

    with open(file_path, 'r') as sql_file:
        current_table = None
        for line in sql_file:
            # Check for table creation
            table_match = create_table_pattern.search(line)
            if table_match:
                current_table = table_match.group(1)
                table_data[current_table] = []
            elif current_table:
                # Check for column definitions
                column_match = column_pattern.search(line)
                if column_match:
                    column_name = column_match.group(1)
                    data_type = column_match.group(2).strip()
                    not_null = 'YES' if column_match.group(3) else 'NO'
                    auto_increment = 'YES' if column_match.group(4) else 'NO'
                    key = 'PRIMARY' if column_match.group(5) else 'NO'
                    default_value = column_match.group(7) if column_match.group(7) else 'NULL'
                    extra = column_match.group(9) if column_match.group(9) else ''
                    comment = column_match.group(11) if column_match.group(11) else ''

                    table_data[current_table].append((column_name, data_type, not_null, auto_increment, key, default_value, extra, comment))
                    
                # Check if we've reached the end of a table definition
                if line.strip().endswith(';'):
                    current_table = None
    return table_data

# Streamlit UI
st.title('Business Analyst Data Extraction App')

# Upload Excel file
st.header('Upload Excel File')
excel_file = st.file_uploader('Upload Excel file', type=['xlsx'])
header_row = st.number_input('Select header row to start from:', min_value=1, value=3) - 1  # 0-based index

if excel_file is not None:
    excel_columns = extract_excel_columns(excel_file, header_row)
    st.write('Excel Columns and Data Types:')
    st.dataframe(excel_columns)
    excel_columns.to_csv('excel_columns.csv', index=False)  # Save to CSV
    st.download_button(label='Download Excel Columns', data=open('excel_columns.csv', 'rb'), file_name='excel_columns.csv')

# Upload SQL file
st.header('Upload SQL Dump File')
sql_file = st.file_uploader('Upload SQL file', type=['sql'], key='sql_uploader')

# Clear session state if SQL file is removed
if sql_file is None:
    if 'sql_tables' in st.session_state:
        del st.session_state.sql_tables
    if 'preview_data' in st.session_state:
        del st.session_state.preview_data
    if 'preview_table_name' in st.session_state:
        del st.session_state.preview_table_name

# Store table data in session state
if sql_file is not None:
    # Save the uploaded SQL file temporarily
    with open('sql_dump.sql', 'wb') as f:
        f.write(sql_file.getbuffer())
    
    # Parse the SQL file and extract table and column information
    if 'sql_tables' not in st.session_state:
        st.session_state.sql_tables = parse_sql_file('sql_dump.sql')
    
    # Search bar for filtering table names
    search_query = st.text_input("Search for a table:")
    
    # Display tables and their columns
    for table_name, columns in st.session_state.sql_tables.items():
        if search_query.lower() in table_name.lower():  # Filter by search query
            # Create a layout for table name and buttons
            col1, col2, col3 = st.columns([4, 1, 1])  # Adjust column widths as needed
            
            with col1:
                st.subheader(table_name)
            
            with col2:
                # Button to show table preview
                if st.button(f'Preview', key=f'preview_{table_name}'):
                    st.session_state.preview_data = pd.DataFrame(columns, columns=['Column Name', 'Data Type', 'Not Null', 'Auto Increment', 'Key', 'Default', 'Extra', 'Comment'])
                    st.session_state.preview_table_name = table_name  # Store table name for display

            with col3:
                # Prepare for individual downloads
                table_file = f'{table_name}_columns.csv'
                column_df = pd.DataFrame(columns, columns=['Column Name', 'Data Type', 'Not Null', 'Auto Increment', 'Key', 'Default', 'Extra', 'Comment'])  # Create DataFrame again for download
                column_df.to_csv(table_file, index=False)
                st.download_button(label='Download', data=open(table_file, 'rb'), file_name=table_file)

            # Display preview data if it exists for this table
            if 'preview_data' in st.session_state and st.session_state.preview_table_name == table_name:
                st.write(f'**Preview for Table: {table_name}**')
                st.dataframe(st.session_state.preview_data)

# Download all tables
if 'sql_tables' in st.session_state:
    all_columns = []
    for table_name, columns in st.session_state.sql_tables.items():
        for col in columns:
            all_columns.append([table_name, col[0], col[1], col[2], col[3], col[4], col[5], col[6], col[7]])
    
    if all_columns:
        all_df = pd.DataFrame(all_columns, columns=['Table Name', 'Column Name', 'Data Type', 'Not Null', 'Auto Increment', 'Key', 'Default', 'Extra', 'Comment'])
        all_columns_file = 'all_sql_columns.csv'
        all_df.to_csv(all_columns_file, index=False)
        st.download_button(label='Download All SQL Columns', data=open(all_columns_file, 'rb'), file_name=all_columns_file)

# Clean up temporary files
if os.path.exists('sql_dump.sql'):
    os.remove('sql_dump.sql')
