import streamlit as st
from openai import OpenAI
import os
import tempfile

# Настройки
OPENAI_API_KEY = "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"  # Project API Key
PROJECT_ID = "proj_3LFcRXiyy2eIhtVUFDx06BmA"         # Project ID
PROMPT_ID = "pmpt_68900ac35e7081959fe8c48c9a077aec0eeaf77803903995"  # Твой prompt

client = OpenAI(api_key=OPENAI_API_KEY, project=PROJECT_ID)

# Интерфейс
st.set_page_config(page_title="Ассистент Битроникс", layout="centered")
st.title("🤖 Ассистент компании Битроникс")
st.markdown("Загрузи ТЗ и отправь его в OpenAI, используя сохранённый prompt.")

uploaded_file = st.file_uploader("📎 Загрузите файл (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file and st.button("🚀 Отправить через prompt"):
    with st.spinner("Обрабатываю файл..."):
        ext = os.path.splitext(uploaded_file.name)[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            try:
                response = client.responses.create(
                    prompt={
                        "id": PROMPT_ID,
                        "version": "latest"
                    },
                    file=f
                )
                result = response.content.strip()
                st.success("✅ Ответ получен от OpenAI.")
                st.text_area("📄 Результат:", result, height=400)
                st.download_button("💾 Скачать результат", result, file_name="результат.txt")

            except Exception as e:
                st.error(f"Ошибка при обращении к OpenAI:\n\n{str(e)}")
