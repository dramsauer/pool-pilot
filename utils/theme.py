import streamlit as st


def inject_theme():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;0,900;1,300;1,400;1,700;1,900&display=swap');

.stApp, .main, .block-container, .stMarkdown, p, li, label, h1, h2, h3, h4, h5, h6 {
    font-family: 'Merriweather', Georgia, serif;
}

h1, h2, h3, h4, h5, h6 {
    font-weight: 700;
}

.stAlert {
    border-left-color: #E8A838;
}
</style>
""",
        unsafe_allow_html=True,
    )
