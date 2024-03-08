# Import necessary libraries
import streamlit as st
import osmnx as ox
import pandas as pd
import folium
from streamlit_folium import st_folium
from shapely import geometry, ops
import geopandas as gpd
import spacy
import gender_guesser.detector as gender
from streamlit_extras.switch_page_button import switch_page
from streamlit.source_util import get_pages


st.set_page_config(page_title="Gender Streets",
                   page_icon="🇬🇧",
                   layout="wide"
                  )
# Pre-defined list of cities for the app
default_cities = ["Torino", "Aosta", "Genova", "Milano", "Trento", "Venezia", "Trieste",
                  "Bologna", "Firenze", "Ancona", "Perugia", "Roma", "L'Aquila", "Campobasso", "Napoli", "Bari",
                  "Potenza", "Catanzaro", "Palermo", "Cagliari"]

# Language dictionaries for the app
language_dict = {'Italian': 'italy', 'French': 'france', 'English': 'great_britain'}
spacy_dict = {'Italian': 'it_core_news_sm', 'French': 'fr_core_news_sm', 'English': 'en_core_web_sm'}

language = 'Italian'
d = gender.Detector(case_sensitive=False)

# Function to load the NLP model based on the selected language
@st.cache_data
def load_nlp(language):
    nlp = spacy.load(spacy_dict[language])
    d = gender.Detector(case_sensitive=False)
    return nlp, d

nlp, d = load_nlp(language)

# Function to transform name list to string
def transform_name(x):
    return ', '.join(x) if isinstance(x, list) else x

# Function to get gender of a name
def get_gender(texts, language=language, d=d):
    doc = nlp(' '.join(texts))
    if 'PER' in [e.label_ for e in doc.ents]:
        res = [d.get_gender(t, country=language_dict[language]) for t in texts]
        res = [g for g in res if g in ['male', 'female']]
        return res[0] if len(res) > 0 else 'unknown'
    else:
        return 'unknown'

# Function to load streets data from disk
def load_from_disk(city):
    streets = gpd.read_file(f'data/{city.lower()}.geojson')
    return streets

# Function to download streets data from OpenStreetMap
def download_from_osm(city):
    graph = ox.graph_from_place(city, network_type='all')
    streets = ox.graph_to_gdfs(graph, nodes=False, edges=True)
    streets.dropna(subset=['name'], inplace=True)
    streets.name = streets.name.map(transform_name)
    streets = streets.groupby('name').geometry.apply(lambda x: ops.linemerge(geometry.MultiLineString(x.values))).reset_index().set_crs('epsg:4326', allow_override=True)
    return streets

# Function to download streets and infer gender
@st.cache_data
def download_streets_and_infer_gender(city, language, default_cities=default_cities):
    if city is None:
        return []
    streets = load_from_disk(city) if city in default_cities else download_from_osm(city)
    
    unique_streets_df = pd.DataFrame(streets.name.astype(str).unique(), columns=['name'])
    unique_streets_df['name_strip'] = unique_streets_df.name.str.split().str[:-1] if language == 'Inglese' else unique_streets_df.name.str.split().str[1:]
    unique_streets_df['gender'] = unique_streets_df.name_strip.map(lambda x: get_gender(x, language=language, d=d))
    unique_streets_df.set_index('name', inplace=True)

    streets['gender'] = streets.name.astype(str).map(unique_streets_df.gender)
    
    gender_colors = {'male': '#32E3A1', 'female': 'violet', 'unknown': '#D3D3D3'}
    streets['gender_color'] = streets['gender'].map(gender_colors)
    streets.sort_values('gender', ascending=False, inplace=True)
    return streets

# Function to plot streets to a Folium map
def plot_graphto_folium(gdf_edges, graph_map=None, popup_attribute=None, tiles=None, zoom=1, fit_bounds=True, colors=[], edge_width=2, edge_opacity=1):
    x, y = gdf_edges.unary_union.centroid.xy
    graph_centroid = (y[0], x[0])
    if graph_map is None:
        graph_map = folium.Map(location=graph_centroid, zoom_start=zoom, tiles=tiles, width=500, height=500)
    
    popup = folium.GeoJsonPopup(fields=["name"])
    
    folium.GeoJson(gdf_edges, style_function=lambda feature: {
        "color": feature["properties"]["gender_color"],
        "weight": 3,
    }, popup=popup).add_to(graph_map)

    if fit_bounds:
        tb = gdf_edges.total_bounds
        bounds = [(tb[1], tb[0]), (tb[3], tb[2])]
        graph_map.fit_bounds(bounds)
    return graph_map


def app():
        
    if st.button('Change Language/Cambia Lingua 🇮🇹'):
        # main.app()
        switch_page('italiano')

    # Initialization of session state variables
    if 'proceed' not in st.session_state:
        st.session_state['proceed'] = False
    if 'map' not in st.session_state:
        st.session_state['map'] = False

    st.title('Gendered Streets\n')
    st.header("How many streets *in your city* are named after :violet[*women*]? And how many after :green[*men*]?", divider='rainbow')
    st.markdown("""
##### Hello! 👋 
##### You might have noticed that some streets in our cities are dedicated to *places* or *historical events*. 
##### Other streets, however, are named after :rainbow[**people**].
##### Have you ever wondered if these streets commemorate :violet[*women*] or :green[*men*] and why?
##### This *interactive web page* shows in simple terms if there's a gender disparity in the toponymy of your favorite city!🧐 
##### :rainbow[**[SPOILER]**] *There is.*


    """)
    st.text("")

    st.markdown("""
    ###### It's very simple, you just need to choose a *city* and a *language*.
    
    You can also select *Other* to search for a city not on the list! 
    
    (Please be patient in this case, downloading data for large cities might take a couple of minutes.)
    """)

    options = default_cities + ['Other']
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_option = st.selectbox('Choose a city:', options)
        if selected_option == 'Other':
            # Ask for a free field input
            city = None
            other_input = st.text_input("Specify which city:")
            if other_input:  # Optional: Do something with the input
                city = other_input
        else:
            # Optional: Do something with the selected option
            city = selected_option
    with col2:
        language = st.selectbox('Choose a language:', ['Italian', 'French', 'English'])
        nlp, d = load_nlp(language)
    
    st.write("We're ready, click to start the analysis!")
    
    with st.expander('Ah, interesting. And how do you do it?'):
        st.markdown("""
Everything is automatic!🤖  
**[Indeed, there are many limitations and potential errors 🙈]**

Here's how it proceeds:

- The street data for the selected city are downloaded from [OpenStreetMap](https://www.openstreetmap.org/) using [osmnx](https://osmnx.readthedocs.io/en/stable/index.html).
- Street names are analyzed with two Natural Language Processing (NLP) tools:
    - [Spacy](https://spacy.io/) analyzes the street name and tells us if it contains a person's name
    - [gender_guesser](https://github.com/lead-ratings/gender-guesser/tree/master) estimates the gender (male/female only 🤷🤦)
- The streets are displayed with [Folium and Streamlit](https://github.com/randyzwitch/streamlit-folium)!

**[WARNING]** This webpage was designed and built just for curiosity, do not take the results presented as absolute!

**[DISCLAIMER]** This application was originally designed to work with Italian names, much less effort was put to make English and French work, so the results might be even less reliable 🙈

The code is available on this [Git](), have fun!

""")
    
    streets = download_streets_and_infer_gender(city, language)

    
    if st.button('Go!', type="primary"):
        st.session_state.proceed = True

    if st.session_state.proceed:
        st.subheader(f'{city}')
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total streets", len(streets))
        col2.metric("Streets without gender",
                    len(streets[streets.gender == 'unknown']),
                    delta=f" {int(100* round(len(streets[streets.gender == 'unknown'])/len(streets)+0.001,2))} %"
                   )
        col3.metric("Streets named after women",
                    len(streets[streets.gender == 'female']),
                    delta=f"{int(100* round(len(streets[streets.gender == 'female'])/len(streets)+0.001,2))} %",
                    delta_color='inverse'
                   )
        col4.metric("Streets named after men", len(streets[streets.gender == 'male']),
                    delta=f"{int(100* round(len(streets[streets.gender == 'male'])/len(streets)+0.001,2))} %",
                    delta_color='inverse'
                   )
        st.markdown(f"In the city of **{city}**, for **every 1 street named after a woman**, there are approximately **{round(len(streets[streets.gender == 'male'])/(len(streets[streets.gender == 'female'])+0.001))} streets named after men** ⚖️ 🤔")
        
        st.subheader('Map')
    
    else:
        st.write("Select a city and a language to start")
        
        
    if st.session_state.proceed:
        
        if st.button('Show me the map!', type="primary"):
            st.session_state.map = True

        if st.session_state.map:
        
            st.markdown("""
        ##### Let's color the streets

        Let's see on the map of the city which streets are dedicated to :rainbow[**people**].

        In the map, streets named after **women** are colored in :violet[**violet**], those named after **men** in :green[**green**].

        Streets without gender characterization are not colored.

        *Clicking on any colored street you can see* ***whom it is named after!***
        """)
            st.text(" ")
            st.write("To speed up the visualization, you can choose to see only the names of streets named after *women*. What do you think?")

            on = st.toggle('Sure, most will be cis white men anyway', True)

            if on:
                streets_mf = streets[streets.gender == 'female']

                streets_g = streets[streets.gender == 'male'].explode().groupby('gender').geometry.apply(lambda x: ops.linemerge(geometry.MultiLineString(x.values))).reset_index().set_crs('epsg:4326', allow_override=True)

                streets_g['gender_color'] = '#32E3A1'
                streets_g['name'] = 'basic white man'
                streets_mf = pd.concat([streets_mf, streets_g])

            else:
                streets_mf = streets[streets.gender != 'unknown']

                
            graphmap = plot_graphto_folium(streets_mf, popup_attribute='name', tiles='Cartodb positron', colors=streets_mf['gender_color'], edge_width=4, edge_opacity=1)
            st_map = st_folium(graphmap,
                               use_container_width=True)
    if st.session_state.proceed:
        st.subheader('Interesting. So what?')
        st.markdown(
            """
    This experiment has no general significance, but as you've seen, *it's hard to find a city that commemorates more women than men*.

    The reason for this disparity is probably historical: men have always been considered more important in the past, and consequently, there are more streets named after them. However, this imbalance is not necessarily right, nor does it have to be this way forever! 
    It would indeed be interesting to investigate the gender ratio in new streets and those recently renamed.

    So what?

    Simply put, from now on, all new streets should be dedicated to women.
            """
        )


if __name__ == "__main__":
    app()