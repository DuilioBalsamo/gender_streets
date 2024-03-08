# import streamlit as st
# from streamlit.web import cli as stcli
# import sys
# import streamlit as st
# from streamlit_extras.switch_page_button import switch_page

# def run_app(language):
#     if language == 'English':
#         sys.argv = ["streamlit", "run", "english_page.py"]
#     elif language == 'Italiano':
#         sys.argv = ["streamlit", "run", "italian_page.py"]
#     sys.exit(stcli.main())

# st.title('Welcome/ Benvenuto')
# language = st.selectbox('Choose a language/ Seleziona una lingua:', ['English', 'Italiano'])

# if st.button('Confirm/ Conferma'):
#     run_app(language)
    
import streamlit as st
from streamlit_extras.switch_page_button import switch_page


st.set_page_config(
    page_title="Hello",
    page_icon="🦠",
    layout="wide"
)

switch_page('italiano')