import streamlit as st
from openai import OpenAI
import pdfplumber
from docx import Document
import os
import tempfile

# Настройки
OPENAI_API_KEY = "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"  # Project API Key
PROJECT_ID = "proj_3LFcRXiyy2eIhtVUFDx06BmA"         # ← ВСТАВЬ СЮДА свой project ID
PROMPT_ID = "pmpt_68900ac35e7081959fe8c48c9a077aec0eeaf77803903995"

client = OpenAI(api_key=OPENAI_API_KEY, project=PROJECT_ID)

# 📄 Парсинг PDF
def extract_text_from_pdf(path):
    with pdfplumber.open(path) as pdf:
        return '\n'.join([page.extract_text() or '' for page in pdf.pages]).strip()

# 📄 Парсинг DOCX
def extract_text_from_docx(path):
    doc = Document(path)
    return '\n'.join([p.text for p in doc.paragraphs]).strip()

# 📄 Универсальный парсер
def read_file(file):
    ext = os.path.splitext(file.name)[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    if ext == '.pdf':
        return extract_text_from_pdf(tmp_path)
    elif ext == '.docx':
        return extract_text_from_docx(tmp_path)
    elif ext == '.txt':
        with open(tmp_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return None

# 🚀 Интерфейс Streamlit
st.set_page_config(page_title="Ассистент Битроникс", layout="centered")
st.title("🤖 Ассистент компании Битроникс")
st.markdown("Загрузи техническое задание и выбери режим работы:")

uploaded_file = st.file_uploader("📎 Загрузите файл (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
mode = st.radio("⚙️ Режим работы:", ["Распарсить текст и отправить в GPT-4o", "Отправить файл напрямую через Prompt"])

if uploaded_file and st.button("🚀 Проанализировать"):
    with st.spinner("Обрабатываю..."):
        try:
            ext = os.path.splitext(uploaded_file.name)[-1].lower()

            if mode == "Распарсить текст и отправить в GPT-4o":
                file_text = read_file(uploaded_file)
                if not file_text:
                    st.error("❌ Не удалось прочитать файл.")
                else:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "Ты — ассистент компании Битроникс. Анализируй ТЗ строго по инструкции. Сначала делай анализ, потом выводи в JSON или текст."},
                            {"role": "user", "content": file_text}
                        ]
                    )
                    result = response.choices[0].message.content.strip()
                    st.success("✅ GPT-4o завершил анализ.")
                    st.text_area("📄 Результат анализа:", result, height=400)
                    st.download_button("💾 Скачать результат как .txt", result, file_name="результат.txt")

            else:
                # Сохраняем файл временно
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                # Загружаем файл в OpenAI
                uploaded = client.files.create(
                    file=open(tmp_path, "rb"),
                    purpose="assistants"
                )

                # Вызываем сохранённый Prompt
                response = client.responses.create(
                    prompt={
                        "id": PROMPT_ID,
                        "version": "latest"
                    },
                    file_ids=[uploaded.id]
                )

                result = response.content.strip()
                st.success("✅ Prompt обработал файл.")
                st.text_area("📄 Результат:", result, height=400)
                st.download_button("💾 Скачать результат как .txt", result, file_name="результат.txt")

        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
