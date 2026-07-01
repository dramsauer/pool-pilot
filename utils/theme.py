import streamlit as st


def inject_theme():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;0,900;1,300;1,400;1,700;1,900&display=swap');

html, body, [class*="css"], [class*="st-"] {
    font-family: 'Merriweather', Georgia, serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Merriweather', Georgia, serif;
    font-weight: 700;
}

.stAlert {
    border-left-color: #E8A838 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
