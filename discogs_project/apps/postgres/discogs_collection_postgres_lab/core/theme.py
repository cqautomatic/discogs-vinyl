"""
Theme management for Streamlit application.
Handles light/dark/auto theme switching with proper CSS application.
"""

import streamlit as st

def apply_theme_css():
    """Apply theme-aware CSS based on user selection."""
    # Theme selector in sidebar
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = 'auto'
    
    with st.sidebar:
        st.markdown("### 🎨 Theme")
        theme_mode = st.selectbox(
            "Choose theme:",
            options=['auto', 'light', 'dark'],
            index=['auto', 'light', 'dark'].index(st.session_state.theme_mode),
            key='theme_selector'
        )
        st.session_state.theme_mode = theme_mode

    # Determine effective theme
    if theme_mode == 'auto':
        # Default to light since Streamlit doesn't support system detection
        effective_theme = 'light'
        st.sidebar.caption("ℹ️ Auto mode defaults to light theme")
    else:
        effective_theme = theme_mode

    # Apply theme-specific CSS
    if effective_theme == 'dark':
        css = get_dark_theme_css()
    else:  # light theme
        css = get_light_theme_css()
    
    st.markdown(css, unsafe_allow_html=True)

def get_dark_theme_css() -> str:
    """Get CSS for dark theme."""
    return """
    <style>
        .stApp {
            background-color: #0e1117;
            color: #e0e0e0;
        }
        /* Force text visibility in dark theme */
        .main .block-container {
            color: #e0e0e0 !important;
        }
        h1, h2, h3, h4, h5, h6, p, div, span, li {
            color: #e0e0e0 !important;
        }
        .stMarkdown, .stText {
            color: #e0e0e0 !important;
        }
        /* Streamlit specific elements */
        .stCaption {
            color: #8b949e !important;
        }
        .stMetric {
            color: #e0e0e0 !important;
        }
        .stSelectbox label, .stButton, .stRadio label {
            color: #e0e0e0 !important;
        }
        /* Main content area buttons for dark theme */
        .stButton > button {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        .stButton > button:hover {
            background-color: #243447 !important;
            border-color: #58a6ff !important;
        }
        /* Modal buttons specific styling for dark theme */
        div[data-testid="stButton"] button {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #243447 !important;
            border-color: #58a6ff !important;
        }
        /* Force ALL button visibility for dark theme */
        button, .stButton button, [data-testid="stButton"] button {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        button:hover, .stButton button:hover, [data-testid="stButton"] button:hover {
            color: #ffffff !important;
            background-color: #243447 !important;
            border-color: #58a6ff !important;
        }
        /* Expander buttons specifically */
        [data-testid="stExpander"] button {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        [data-testid="stExpander"] button:hover {
            background-color: #243447 !important;
            border-color: #58a6ff !important;
        }
        /* Nuclear option - force ALL elements with button in class/id for dark theme */
        [class*="button"], [id*="button"], input[type="button"], input[type="submit"] {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        [class*="button"]:hover, [id*="button"]:hover, input[type="button"]:hover, input[type="submit"]:hover {
            color: #ffffff !important;
            background-color: #243447 !important;
            border-color: #58a6ff !important;
        }
        /* Expander header and hover states for dark theme */
        [data-testid="stExpander"] {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [data-testid="stExpander"] > div {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [data-testid="stExpander"]:hover {
            background-color: #243447 !important;
            color: #ffffff !important;
        }
        [data-testid="stExpander"] > div:hover {
            background-color: #243447 !important;
            color: #ffffff !important;
        }
        [data-testid="stExpander"] * {
            color: #e0e0e0 !important;
        }
        [data-testid="stExpander"]:hover * {
            color: #ffffff !important;
        }
        /* Additional expander selectors for dark theme */
        .streamlit-expanderHeader, .streamlit-expanderHeader:hover {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        .streamlit-expanderHeader:hover {
            background-color: #243447 !important;
            color: #ffffff !important;
        }
        [class*="expander"], [class*="Expander"] {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        [class*="expander"]:hover, [class*="Expander"]:hover {
            color: #ffffff !important;
            background-color: #243447 !important;
        }
        /* Top banner/header styling for dark theme */
        header[data-testid="stHeader"] {
            background-color: #0e1117 !important;
            color: #e0e0e0 !important;
        }
        header[data-testid="stHeader"] * {
            color: #e0e0e0 !important;
        }
        .stDeployButton {
            color: #e0e0e0 !important;
        }
        /* Streamlit toolbar */
        .stToolbar {
            background-color: #0e1117 !important;
            color: #e0e0e0 !important;
        }
        .stToolbar * {
            color: #e0e0e0 !important;
        }
        /* Settings menu and dropdowns for dark theme */
        [data-testid="stPopover"] {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2f3a !important;
        }
        [data-testid="stPopover"] * {
            color: #e0e0e0 !important;
        }
        /* Main app settings menu */
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] {
            background-color: #1e222b !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] div {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        /* Additional settings menu selectors for dark theme */
        .main-menu, .main-menu *, .stPopover, .stPopover * {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        /* Streamlit menu items */
        [data-baseweb="menu"] {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [data-baseweb="menu"] * {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        [data-baseweb="menu-item"] {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        [data-baseweb="menu-item"]:hover {
            background-color: #243447 !important;
        }
        /* Force all dropdown and menu elements for dark theme */
        [class*="menu"], [class*="dropdown"], [class*="popover"] {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [class*="menu"] *, [class*="dropdown"] *, [class*="popover"] * {
            color: #e0e0e0 !important;
        }
        /* Settings gear menu specifically */
        [data-testid="stHeaderActionElements"] [data-testid="stPopover"] {
            background-color: #1e222b !important;
        }
        [data-testid="stHeaderActionElements"] [data-testid="stPopover"] * {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
        }
        /* Sidebar styling for dark theme */
        .css-1d391kg, .css-1aumxhk {
            background-color: #0e1117 !important;
        }
        .sidebar .sidebar-content, .stSidebar > div {
            background-color: #0e1117 !important;
            color: #e0e0e0 !important;
        }
        .sidebar h1, .sidebar h2, .sidebar h3, .sidebar h4, .sidebar h5, .sidebar h6,
        .sidebar p, .sidebar div, .sidebar span, .sidebar li,
        .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar h5, .stSidebar h6,
        .stSidebar p, .stSidebar div, .stSidebar span, .stSidebar li {
            color: #e0e0e0 !important;
        }
        .stSidebar .stMarkdown, .stSidebar .stText, .stSidebar .stCaption {
            color: #e0e0e0 !important;
        }
        .stSidebar .stSelectbox label, .stSidebar .stRadio label {
            color: #e0e0e0 !important;
        }
        /* Additional sidebar selectors for dark theme */
        section[data-testid="stSidebar"] {
            background-color: #0e1117 !important;
            color: #e0e0e0 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #e0e0e0 !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            color: #e0e0e0 !important;
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        /* COMPREHENSIVE DROPDOWN/SELECT STYLING FOR DARK THEME */
        
        /* Main content area dropdowns */
        .stSelectbox {
            color: #e0e0e0 !important;
        }
        .stSelectbox label {
            color: #e0e0e0 !important;
        }
        .stSelectbox > div > div {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2f3a !important;
        }
        .stSelectbox input {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border-color: #2a2f3a !important;
        }
        
        /* BaseWeb select components */
        [data-baseweb="select"] {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [data-baseweb="select"] > div {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border-color: #2a2f3a !important;
        }
        [data-baseweb="select"] input {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [data-baseweb="select"] svg {
            fill: #e0e0e0 !important;
        }
        
        /* Select dropdown options */
        [role="listbox"] {
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        [role="option"] {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        [role="option"]:hover {
            background-color: #243447 !important;
            color: #ffffff !important;
        }
        [role="option"][aria-selected="true"] {
            background-color: #58a6ff !important;
            color: #ffffff !important;
        }
        
        /* Sidebar specific dropdown styling */
        section[data-testid="stSidebar"] .stSelectbox {
            color: #e0e0e0 !important;
        }
        section[data-testid="stSidebar"] .stSelectbox label {
            color: #e0e0e0 !important;
        }
        section[data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2f3a !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] {
            color: #e0e0e0 !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border-color: #2a2f3a !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] input {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] svg {
            fill: #e0e0e0 !important;
        }
        
        /* Radio buttons for dark theme */
        .stRadio {
            color: #e0e0e0 !important;
        }
        .stRadio label {
            color: #e0e0e0 !important;
        }
        .stRadio > div {
            color: #e0e0e0 !important;
        }
        
        /* TEXT INPUT STYLING FOR DARK THEME */
        .stTextInput {
            color: #e0e0e0 !important;
        }
        .stTextInput label {
            color: #e0e0e0 !important;
        }
        .stTextInput > div > div {
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        .stTextInput input {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2f3a !important;
        }
        .stTextInput input:focus {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border-color: #58a6ff !important;
            box-shadow: 0 0 0 1px #58a6ff !important;
        }
        
        /* Number input styling */
        .stNumberInput {
            color: #e0e0e0 !important;
        }
        .stNumberInput label {
            color: #e0e0e0 !important;
        }
        .stNumberInput > div > div {
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        .stNumberInput input {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2f3a !important;
        }
        .stNumberInput input:focus {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border-color: #58a6ff !important;
            box-shadow: 0 0 0 1px #58a6ff !important;
        }
        
        /* Text area styling */
        .stTextArea {
            color: #e0e0e0 !important;
        }
        .stTextArea label {
            color: #e0e0e0 !important;
        }
        .stTextArea > div > div {
            background-color: #1e222b !important;
            border: 1px solid #2a2f3a !important;
        }
        .stTextArea textarea {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2f3a !important;
        }
        .stTextArea textarea:focus {
            background-color: #1e222b !important;
            color: #e0e0e0 !important;
            border-color: #58a6ff !important;
            box-shadow: 0 0 0 1px #58a6ff !important;
        }
        .release-card { 
            background-color: #1e222b !important; 
            border: 1px solid #2a2f3a !important;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .genre-tag { 
            background-color: #243447 !important; 
            color: #9ecbff !important;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin: 2px;
            display: inline-block;
        }
        .artwork-container { 
            background-color: #141823 !important; 
            border: 2px solid #2a2f3a !important;
            border-radius: 8px;
            padding: 5px;
            text-align: center;
        }
        .main-header {
            font-size: 2.5rem;
            color: #58a6ff;
            text-align: center;
            padding: 1rem 0;
            border-bottom: 2px solid #58a6ff;
            margin-bottom: 2rem;
        }
        .image-counter {
            font-size: 0.8rem;
            color: #8b949e;
            margin-top: 5px;
        }
        /* Dark theme for tables */
        .stDataFrame {
            background-color: #1e222b;
        }
        /* Dark theme for metrics */
        .metric-container {
            background-color: #1e222b;
            border: 1px solid #2a2f3a;
            border-radius: 8px;
            padding: 10px;
        }
        /* Tooltip styling for dark theme */
        [role="tooltip"], div[data-testid="stTooltipHoverTarget"] + div, [data-baseweb="tooltip"] {
            background-color: #2a2f3a !important;
            color: #e0e0e0 !important;
            border: 1px solid #3a4048 !important;
            border-radius: 4px !important;
        }
        [data-baseweb="tooltip"] > div {
            background-color: #2a2f3a !important;
            color: #e0e0e0 !important;
        }
        /* Release card hover styling for dark theme */
        .release-card-hover {
            position: relative;
            margin: 8px 0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .release-card-hover:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(88, 166, 255, 0.3);
        }
        .release-info-overlay {
            background: linear-gradient(to bottom, transparent 0%, rgba(30, 34, 43, 0.9) 70%, rgba(30, 34, 43, 0.95) 100%);
            padding: 8px;
            border-radius: 6px;
            margin-top: 4px;
        }
        .release-info-clean {
            background: rgba(30, 34, 43, 0.85);
            padding: 8px;
            border-radius: 6px;
            margin-top: 4px;
            border: 1px solid #2a2f3a;
        }
        .artist-title {
            color: #58a6ff !important;
            font-size: 0.9rem;
            margin-bottom: 2px;
        }
        .album-title {
            color: #e0e0e0 !important;
            font-size: 0.85rem;
            margin-bottom: 2px;
        }
        .year-label {
            color: #8b949e !important;
            font-size: 0.75rem;
        }
        /* Hide fullscreen button on images */
        [data-testid="stImageFullscreen"] {
            display: none !important;
        }
        button[title="View fullscreen"] {
            display: none !important;
        }
        .stImage > button {
            display: none !important;
        }
    </style>
    """

def get_light_theme_css() -> str:
    """Get CSS for light theme."""
    return """
    <style>
        .stApp {
            background-color: #ffffff;
            color: #222222;
        }
        /* Force text visibility in light theme */
        .main .block-container {
            color: #222222 !important;
        }
        h1, h2, h3, h4, h5, h6, p, div, span, li {
            color: #222222 !important;
        }
        .stMarkdown, .stText {
            color: #222222 !important;
        }
        /* Streamlit specific elements */
        .stCaption {
            color: #666666 !important;
        }
        .stMetric {
            color: #222222 !important;
        }
        .stSelectbox label, .stButton, .stRadio label {
            color: #222222 !important;
        }
        /* Main content area buttons for light theme */
        .stButton > button {
            color: #222222 !important;
            background-color: #f0f0f0 !important;
            border: 1px solid #dddddd !important;
        }
        .stButton > button:hover {
            background-color: #e0e0e0 !important;
            border-color: #1f77b4 !important;
        }
        /* Modal buttons specific styling for light theme */
        div[data-testid="stButton"] button {
            color: #222222 !important;
            background-color: #f0f0f0 !important;
            border: 1px solid #dddddd !important;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #e0e0e0 !important;
            border-color: #1f77b4 !important;
        }
        /* Force ALL button visibility for light theme */
        button, .stButton button, [data-testid="stButton"] button {
            color: #222222 !important;
            background-color: #f0f0f0 !important;
            border: 1px solid #dddddd !important;
        }
        button:hover, .stButton button:hover, [data-testid="stButton"] button:hover {
            color: #000000 !important;
            background-color: #e0e0e0 !important;
            border-color: #1f77b4 !important;
        }
        /* Expander buttons specifically */
        [data-testid="stExpander"] button {
            color: #222222 !important;
            background-color: #f0f0f0 !important;
            border: 1px solid #dddddd !important;
        }
        [data-testid="stExpander"] button:hover {
            background-color: #e0e0e0 !important;
            border-color: #1f77b4 !important;
        }
        /* Nuclear option - force ALL elements with button in class/id for light theme */
        [class*="button"], [id*="button"], input[type="button"], input[type="submit"] {
            color: #222222 !important;
            background-color: #f0f0f0 !important;
            border: 1px solid #dddddd !important;
        }
        [class*="button"]:hover, [id*="button"]:hover, input[type="button"]:hover, input[type="submit"]:hover {
            color: #000000 !important;
            background-color: #e0e0e0 !important;
            border-color: #1f77b4 !important;
        }
        /* Expander header and hover states for light theme */
        [data-testid="stExpander"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [data-testid="stExpander"] > div {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [data-testid="stExpander"]:hover {
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }
        [data-testid="stExpander"] > div:hover {
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }
        [data-testid="stExpander"] * {
            color: #222222 !important;
        }
        [data-testid="stExpander"]:hover * {
            color: #000000 !important;
        }
        /* Additional expander selectors for light theme */
        .streamlit-expanderHeader, .streamlit-expanderHeader:hover {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        .streamlit-expanderHeader:hover {
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }
        [class*="expander"], [class*="Expander"] {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        [class*="expander"]:hover, [class*="Expander"]:hover {
            color: #000000 !important;
            background-color: #f0f0f0 !important;
        }
        /* Top banner/header styling for light theme */
        header[data-testid="stHeader"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        header[data-testid="stHeader"] * {
            color: #222222 !important;
        }
        .stDeployButton {
            color: #222222 !important;
        }
        /* Streamlit toolbar */
        .stToolbar {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        .stToolbar * {
            color: #222222 !important;
        }
        /* Settings menu and dropdowns for light theme */
        [data-testid="stPopover"] {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #dddddd !important;
        }
        [data-testid="stPopover"] * {
            color: #222222 !important;
        }
        /* Main app settings menu */
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] {
            background-color: #ffffff !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] div {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        /* Additional settings menu selectors for light theme */
        .main-menu, .main-menu *, .stPopover, .stPopover * {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        /* Streamlit menu items */
        [data-baseweb="menu"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [data-baseweb="menu"] * {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        [data-baseweb="menu-item"] {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        [data-baseweb="menu-item"]:hover {
            background-color: #f0f0f0 !important;
        }
        /* Force all dropdown and menu elements for light theme */
        [class*="menu"], [class*="dropdown"], [class*="popover"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [class*="menu"] *, [class*="dropdown"] *, [class*="popover"] * {
            color: #222222 !important;
        }
        /* Settings gear menu specifically */
        [data-testid="stHeaderActionElements"] [data-testid="stPopover"] {
            background-color: #ffffff !important;
        }
        [data-testid="stHeaderActionElements"] [data-testid="stPopover"] * {
            color: #222222 !important;
            background-color: #ffffff !important;
        }
        /* Sidebar styling for light theme */
        .css-1d391kg, .css-1aumxhk {
            background-color: #ffffff !important;
        }
        .sidebar .sidebar-content, .stSidebar > div {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        .sidebar h1, .sidebar h2, .sidebar h3, .sidebar h4, .sidebar h5, .sidebar h6,
        .sidebar p, .sidebar div, .sidebar span, .sidebar li,
        .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar h5, .stSidebar h6,
        .stSidebar p, .stSidebar div, .stSidebar span, .stSidebar li {
            color: #222222 !important;
        }
        .stSidebar .stMarkdown, .stSidebar .stText, .stSidebar .stCaption {
            color: #222222 !important;
        }
        .stSidebar .stSelectbox label, .stSidebar .stRadio label {
            color: #222222 !important;
        }
        /* Additional sidebar selectors for light theme */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #222222 !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            color: #222222 !important;
            background-color: #f0f0f0 !important;
            border: 1px solid #dddddd !important;
        }
        /* COMPREHENSIVE DROPDOWN/SELECT STYLING FOR LIGHT THEME */
        
        /* Main content area dropdowns */
        .stSelectbox {
            color: #222222 !important;
        }
        .stSelectbox label {
            color: #222222 !important;
        }
        .stSelectbox > div > div {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #dddddd !important;
        }
        .stSelectbox input {
            background-color: #ffffff !important;
            color: #222222 !important;
            border-color: #dddddd !important;
        }
        
        /* BaseWeb select components */
        [data-baseweb="select"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #222222 !important;
            border-color: #dddddd !important;
        }
        [data-baseweb="select"] input {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [data-baseweb="select"] svg {
            fill: #222222 !important;
        }
        
        /* Select dropdown options */
        [role="listbox"] {
            background-color: #ffffff !important;
            border: 1px solid #dddddd !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        [role="option"] {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        [role="option"]:hover {
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }
        [role="option"][aria-selected="true"] {
            background-color: #1f77b4 !important;
            color: #ffffff !important;
        }
        
        /* Sidebar specific dropdown styling */
        section[data-testid="stSidebar"] .stSelectbox {
            color: #222222 !important;
        }
        section[data-testid="stSidebar"] .stSelectbox label {
            color: #222222 !important;
        }
        section[data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #dddddd !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] {
            color: #222222 !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #222222 !important;
            border-color: #dddddd !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] input {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] svg {
            fill: #222222 !important;
        }
        
        /* Radio buttons for light theme */
        .stRadio {
            color: #222222 !important;
        }
        .stRadio label {
            color: #222222 !important;
        }
        .stRadio > div {
            color: #222222 !important;
        }
        
        /* TEXT INPUT STYLING FOR LIGHT THEME */
        .stTextInput {
            color: #222222 !important;
        }
        .stTextInput label {
            color: #222222 !important;
        }
        .stTextInput > div > div {
            background-color: #ffffff !important;
            border: 1px solid #dddddd !important;
        }
        .stTextInput input {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #dddddd !important;
        }
        .stTextInput input:focus {
            background-color: #ffffff !important;
            color: #222222 !important;
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 1px #1f77b4 !important;
        }
        
        /* Number input styling */
        .stNumberInput {
            color: #222222 !important;
        }
        .stNumberInput label {
            color: #222222 !important;
        }
        .stNumberInput > div > div {
            background-color: #ffffff !important;
            border: 1px solid #dddddd !important;
        }
        .stNumberInput input {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #dddddd !important;
        }
        .stNumberInput input:focus {
            background-color: #ffffff !important;
            color: #222222 !important;
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 1px #1f77b4 !important;
        }
        
        /* Text area styling */
        .stTextArea {
            color: #222222 !important;
        }
        .stTextArea label {
            color: #222222 !important;
        }
        .stTextArea > div > div {
            background-color: #ffffff !important;
            border: 1px solid #dddddd !important;
        }
        .stTextArea textarea {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #dddddd !important;
        }
        .stTextArea textarea:focus {
            background-color: #ffffff !important;
            color: #222222 !important;
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 1px #1f77b4 !important;
        }
        .release-card { 
            background-color: #fafafa !important; 
            border: 1px solid #dddddd !important;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .genre-tag { 
            background-color: #e1ecf4 !important; 
            color: #39739d !important;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin: 2px;
            display: inline-block;
        }
        .artwork-container { 
            background-color: #ffffff !important; 
            border: 2px solid #dddddd !important;
            border-radius: 8px;
            padding: 5px;
            text-align: center;
        }
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            padding: 1rem 0;
            border-bottom: 2px solid #1f77b4;
            margin-bottom: 2rem;
        }
        .image-counter {
            font-size: 0.8rem;
            color: #666;
            margin-top: 5px;
        }
        /* Light theme for tables */
        .stDataFrame {
            background-color: #ffffff;
        }
        /* Light theme for metrics */
        .metric-container {
            background-color: #fafafa;
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 10px;
        }
        /* Tooltip styling for light theme */
        [role="tooltip"], div[data-testid="stTooltipHoverTarget"] + div, [data-baseweb="tooltip"] {
            background-color: #ffffff !important;
            color: #222222 !important;
            border: 1px solid #cccccc !important;
            border-radius: 4px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        [data-baseweb="tooltip"] > div {
            background-color: #ffffff !important;
            color: #222222 !important;
        }
        /* Release card hover styling for light theme */
        .release-card-hover {
            position: relative;
            margin: 8px 0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .release-card-hover:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(31, 119, 180, 0.3);
        }
        .release-info-overlay {
            background: linear-gradient(to bottom, transparent 0%, rgba(255, 255, 255, 0.9) 70%, rgba(255, 255, 255, 0.95) 100%);
            padding: 8px;
            border-radius: 6px;
            margin-top: 4px;
        }
        .release-info-clean {
            background: rgba(255, 255, 255, 0.85);
            padding: 8px;
            border-radius: 6px;
            margin-top: 4px;
            border: 1px solid #dddddd;
        }
        .artist-title {
            color: #1f77b4 !important;
            font-size: 0.9rem;
            margin-bottom: 2px;
        }
        .album-title {
            color: #222222 !important;
            font-size: 0.85rem;
            margin-bottom: 2px;
        }
        .year-label {
            color: #666666 !important;
            font-size: 0.75rem;
        }
        /* Hide fullscreen button on images */
        [data-testid="stImageFullscreen"] {
            display: none !important;
        }
        button[title="View fullscreen"] {
            display: none !important;
        }
        .stImage > button {
            display: none !important;
        }
    </style>
    """

def get_current_theme() -> str:
    """Get the currently selected theme."""
    return st.session_state.get('theme_mode', 'auto')

def is_dark_theme() -> bool:
    """Check if dark theme is currently active."""
    theme = get_current_theme()
    return theme == 'dark'
