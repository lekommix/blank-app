import streamlit as st
from openai import OpenAI
import pdfplumber
from docx import Document
import os
import tempfile

# Настройки OpenAI
OPENAI_API_KEY = "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"  # Вставь свой ключ
client = OpenAI(api_key=OPENAI_API_KEY)

# Функции парсинга
def extract_text_from_pdf(path):
    with pdfplumber.open(path) as pdf:
        return '\n'.join([page.extract_text() or '' for page in pdf.pages]).strip()

def extract_text_from_docx(path):
    doc = Document(path)
    return '\n'.join([p.text for p in doc.paragraphs]).strip()

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

# Интерфейс Streamlit
st.set_page_config(page_title="Ассистент Битроникс", layout="centered")
st.title("🤖 Ассистент компании Битроникс")
st.markdown("Загрузи техническое задание и выбери режим работы:")

uploaded_file = st.file_uploader("📎 Загрузите файл (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
mode = st.radio("⚙️ Режим работы:", ["Отправить файл напрямую в OpenAI", "Распарсить текст и отправить как текст"])

if uploaded_file and st.button("🚀 Проанализировать"):
    with st.spinner("Обрабатываю файл..."):

        if mode == "Распарсить текст и отправить как текст":
            file_text = read_file(uploaded_file)
            if not file_text:
                st.error("❌ Не удалось прочитать файл.")
            else:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Ты — ассистент компании Битроникс. Анализируй ТЗ строго по инструкции. Сначала делай анализ, потом вывод в JSON или текст."},
                        {"role": "user", "content": file_text}
                    ]
                )
                result = response.choices[0].message.content.strip()
                st.success("✅ Анализ завершён.")
                st.text_area("📄 Результат анализа:", result, height=400)
                st.download_button("💾 Скачать результат как .txt", result, file_name="результат.txt")

        else:  # Отправка файла напрямую
            ext = os.path.splitext(uploaded_file.name)[-1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                response = client.responses.create(
                    prompt={
                        "id": "pmpt_68900ac35e7081959fe8c48c9a077aec0eeaf77803903995",
                        "version": "3"
                    },
                    file=f
                )
                result = response.content.strip()
                st.success("✅ GPT-4o обработал файл.")
                st.text_area("📄 Результат:", result, height=400)
                st.download_button("💾 Скачать результат как .txt", result, file_name="результат.txt")
