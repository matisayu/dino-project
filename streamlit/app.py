import streamlit as st
import streamlit.components.v1 as components
from data import load_occurrences
from map import build_map

st.set_page_config(page_title='Mapping the Age of Discovery', layout='wide')
st.title('Mapping the Age of Discovery')

df = load_occurrences()

year_min = int(df['discovery_year'].min())
year_max = int(df['discovery_year'].max())

EPOCHS_ORDERED = [
    'Late Cretaceous',
    'Early Cretaceous',
    'Late Jurassic',
    'Middle Jurassic',
    'Early Jurassic',
    'Late Triassic',
    'Middle Triassic',
    'Early Triassic',
]
EPOCHS_ORDERED = [e for e in EPOCHS_ORDERED if e in df['geological_epoch'].unique()]

if 'discovery' not in st.session_state:
    st.session_state['discovery'] = (year_min, year_max)

origin = st.session_state.get('origin', (EPOCHS_ORDERED[0], EPOCHS_ORDERED[-1]))
lo = EPOCHS_ORDERED.index(origin[0])
hi = EPOCHS_ORDERED.index(origin[1])
selected_epochs = EPOCHS_ORDERED[lo:hi + 1]

filtered = df[
    (df['discovery_year'] >= st.session_state['discovery'][0]) &
    (df['discovery_year'] <= st.session_state['discovery'][1]) &
    (df['geological_epoch'].isin(selected_epochs))
]

st.write(f'Showing {len(filtered):,} of {len(df):,} occurrences')
components.html(build_map(filtered), height=620)

col1, col2 = st.columns(2)
with col1:
    st.slider('Discovery Year', min_value=year_min, max_value=year_max, step=1, key='discovery')
with col2:
    st.select_slider(
        'Geological Epoch',
        options=EPOCHS_ORDERED,
        value=(EPOCHS_ORDERED[0], EPOCHS_ORDERED[-1]),
        key='origin',
    )
    ticks = ''.join(
        f'<div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:0;text-align:center;">'
        f'<div style="width:1px;height:5px;background:#666;margin-bottom:3px;"></div>'
        f'<div style="font-size:8px;color:#999;line-height:1.3;word-break:break-word;">{epoch}</div>'
        f'</div>'
        for epoch in EPOCHS_ORDERED
    )
    st.markdown(
        f'<div style="display:flex;margin-top:-14px;padding:0 1%;">{ticks}</div>',
        unsafe_allow_html=True
    )
