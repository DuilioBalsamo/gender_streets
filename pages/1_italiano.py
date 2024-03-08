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


st.set_page_config(page_title="Strade di genere",
                   page_icon="🇮🇹",
                   layout="wide"
                  )

# Pre-defined list of cities for the app
default_cities = ['Susa', 'Collegno', "Aosta", "Torino", "Genova", "Milano", "Trento", "Venezia", "Trieste",
                  "Bologna", "Firenze", "Ancona", "Perugia", "Roma", "L'Aquila", "Campobasso", "Napoli", "Bari",
                  "Potenza", "Catanzaro", "Palermo", "Cagliari"]

# Language dictionaries for the app
language_dict = {'Italiano': 'italy', 'Francese': 'france', 'Inglese': 'great_britain'}
spacy_dict = {'Italiano': 'it_core_news_sm', 'Francese': 'fr_core_news_sm', 'Inglese': 'en_core_web_sm'}

language = 'Italiano'
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
    
    st.write("Italiano")
    
    if st.button('Cambia Lingua/Change Language 🇬🇧'):
        # main.app()
        switch_page('english')

# Initialization of session state variables
    if 'proceed' not in st.session_state:
        st.session_state['proceed'] = False
    if 'map' not in st.session_state:
        st.session_state['map'] = False

    st.title('Strade di genere\n')
    st.header("Quante vie *nella tua città* sono intitolate a :violet[*donne*] ? E quante a  :green[*uomimi*]?",divider='rainbow')
    st.markdown("""
##### Ciao! 👋 
##### Avrai notato che alcune strade nelle nostre città sono dedicate a *luoghi* o *eventi storici*. 
##### Altre strade invece sono intitolate a :rainbow[**personə**].
##### Ti sei mai chiestə se queste vie commemorano :violet[*donne*] o :green[*uomini*] e perché?
##### Questa semplice *pagina web interattiva* mostra in maniera grafica se c'è disparità di genere nella toponomastica della tua città preferita!🧐 
##### :rainbow[**[SPOILER]**] *C'è.*


    """)
    st.text("")

    st.markdown("""
    ###### È molto semplice, ti basta scegliere una *città* e una *lingua*.
    
    Puoi anche selezionare *Other* per cercare una città non presente nella lista! (abbi pazienza in questo caso, scaricare i dati di città grosse potrebbe prendere un minuto almeno)
    """)

    options =  default_cities +['Other']
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_option = st.selectbox('Scegli una città:', options)
        if selected_option == 'Other':
            # Ask for a free field input
            city = None
            other_input = st.text_input("Specifica quale città:")
            if other_input:  # Optional: Do something with the input
                city = other_input
        else:
            # Optional: Do something with the selected option
            city = selected_option
    with col2:
        language = st.selectbox('Scegli una lingua:', ['Italiano', 'Francese', 'Inglese'])
        nlp,d = load_nlp(language)
    
    st.write("Ci siamo, clicca per far partite l'analisi!")
    
    with st.expander('Ah, interessante. E come lo fai?'):
        st.markdown("""
Tutto in maniera automatica!🤖  
**[Infatti le limitazioni e i possibili errori sono molti 🙈]**

Ecco come si procede:

- I dati sulle strade della città selezionata vengono scaricati da [OpenStreetMap](https://www.openstreetmap.org/) usando [osmnx](https://osmnx.readthedocs.io/en/stable/index.html).
- I nomi delle vie vengono analizzati con due tool di Natural Language Processing (NLP):
    - [Spacy](https://spacy.io/) analizza il nome della via e ci dice se questa contiene un nome di persona
    - [gender_guesser](https://github.com/lead-ratings/gender-guesser/tree/master) stima il genere (solo maschio/femmina 🤷🤦‍♂️)
- Le strade vengono visualizzate con [Folium e Streamlit](https://github.com/randyzwitch/streamlit-folium)!

**[ATTENZIONE]** Questa webpage è stata pensata e costruita solo per curiosità, non prendete i risultati esposti come assoluti!

**[DISCLAIMER]** Questa applicazione è stata pensata orginariamente per funzionare con nomi italiani, molto meno sforzo è stato messo per far funzionare Inglese e Francese, quindi i risultati potrebbero essere ancora meno attendibili 🙈

Il codice è disponibile su questo [Git](), buon divertimento!

""")
    
    streets = download_streets_and_infer_gender(city,language)

    
    if st.button('Via!', type="primary"):
        st.session_state.proceed = True
        # st.write(st.session_state.proceed)

    if st.session_state.proceed:
        # st.write(st.session_state.proceed)
        st.subheader(f'{city}')
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Totale strade",len(streets))
        col2.metric("Strade senza genere",
                    len(streets[streets.gender == 'unknown']),
                    delta = f" {int(100* round(len(streets[streets.gender == 'unknown'])/len(streets)+0.001,2))} %"
                   )
        col3.metric("Strade al femminile",
                    len(streets[streets.gender == 'female']),
                    delta = f"{int(100* round(len(streets[streets.gender == 'female'])/len(streets)+0.001,2))} %",
                    delta_color = 'inverse'
                   )
        col4.metric("Strade al maschile", len(streets[streets.gender == 'male']),
                    delta = f"{int(100* round(len(streets[streets.gender == 'male'])/len(streets)+0.001,2))} %",
                    delta_color = 'inverse'
                   )
        st.markdown(f"Nella città di **{city}** per **1 strada al femminile** ci sono circa **{round(len(streets[streets.gender == 'male'])/(len(streets[streets.gender == 'female'])+0.001))} strade al maschile**  ⚖️ 🤔")
    
        st.subheader('Map')
    
    else:
        st.write("Seleziona una città ed una lingua per iniziare")
        
    if st.session_state.proceed:
        
        if st.button('Fammi vedere la mappa!', type="primary"):
            st.session_state.map = True
            # st.write(st.session_state.map)

        if st.session_state.map:
        
            st.markdown("""
        ##### Coloriamo le strade

        Vediamo sulla cartina della città quali vie sono dedicate a :rainbow[**personə**].

        Nella mappa le strade intitolate a **donne** sono colorate in :violet[**violetto**], quelle intitolate a **uomini** in :green[**verde**].

        Le strade senza caratterizzazione di genere invece non sono colorate.

        *Cliccando su qualsiasi strada colorata puoi vedere* ***a chi è intitolata!***
        """)
            st.text(" ")
            st.write("Per velocizzare la visualizzazione puoi decidere di vedere solo i nomi delle vie intitolare a *donne*. Che ne dici?")

        #     folium.GeoJson(streets).add_to(graph_map)
            on = st.toggle('Ma si, tanto saranno quasi tutti maschi bianchi cis',True)

            if on:
                streets_mf = streets[streets.gender=='female']

                streets_g = streets[streets.gender=='male'].explode().groupby('gender').geometry.apply(lambda x: ops.linemerge(geometry.MultiLineString(x.values))).reset_index().set_crs('epsg:4326', allow_override=True)

                # gender_colors = {'male':'#32E3A1','female':'#E33274', 'unknown': '#D3D3D3'} #D046A5
                streets_g['gender_color'] = '#32E3A1'
                streets_g['name'] = 'basic white man'
                streets_mf= pd.concat([streets_mf,streets_g])

            else:
                streets_mf = streets[streets.gender!='unknown']

                
            graphmap = plot_graphto_folium(streets_mf, popup_attribute='name', tiles='Cartodb positron', colors = streets_mf['gender_color'], edge_width=4, edge_opacity=1)
            st_map = st_folium(graphmap,
                               use_container_width = True,
                               # height = 700, width = 700,
                               returned_objects=[])
    if st.session_state.proceed:
        st.subheader('Interessante. E quindi?')
        st.markdown(
            """
    Questo esperimento non ha nessuna valenza generale, ma come hai visto *è difficile trovare una città che commemori più le donne che gli uomini*.

    Probabilmente la ragione di questa disparità è di natura storica: gli uomini sono sempre stati considerati più importanti nel passato, e di riflesso ci sono più vie intitolate a loro. Non è vero però che questo sbilanciamento sia giusto, nè che debba essere così per sempre! 
    Sarebbe interessante infatti indagare il rapporto di genere nelle nuove strade e in quelle rinominate di recente.

    Quindi?

    Semplice, d'ora in poi tutte le nuove strade dovrebbero essere dedicate a donne.
            """
        )

if __name__ == "__main__":
    app()