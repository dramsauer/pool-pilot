import os
import streamlit as st
from PIL import Image
from database.db import get_engine, init_db, get_session
from database.repository import save_photo, get_photos, delete_photo

st.set_page_config(page_title="Fotos", page_icon="📸")

engine = get_engine()
init_db(engine)
session = get_session(engine)

PHOTO_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

st.title("📸 Foto-Dokumentation")

uploaded = st.file_uploader("Foto hochladen", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
for file in uploaded:
    img = Image.open(file)
    img.thumbnail((800, 800))
    path = os.path.join(PHOTO_DIR, file.name)
    img.save(path)
    caption = st.text_input("Bildunterschrift", key=f"cap_{file.name}")
    save_photo(session, image_path=path, caption=caption or "")
    st.success(f"{file.name} gespeichert!")

st.divider()
st.subheader("🖼️ Galerie")

photos = get_photos(session)
if not photos:
    st.info("Noch keine Fotos vorhanden.")
else:
    cols = st.columns(3)
    for i, photo in enumerate(photos):
        with cols[i % 3]:
            if os.path.exists(photo.image_path):
                st.image(photo.image_path, caption=photo.caption, use_container_width=True)
                if st.button("🗑️ Löschen", key=f"del_{photo.id}"):
                    if os.path.exists(photo.image_path):
                        os.remove(photo.image_path)
                    delete_photo(session, photo.id)
                    st.rerun()

st.page_link("app.py", label="← Zurück zum Dashboard", use_container_width=True)
