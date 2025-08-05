import streamlit as st
from openai import OpenAI
import pdfplumber
from docx import Document
import os
import tempfile

# Настройки OpenAI
OPENAI_API_KEY = "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"  # Вставь свой API-ключ
PROJECT_ID = "proj_3LFcRXiyy2eIhtVUFDx06BmA"  # Твой ID проекта
client = OpenAI(api_key=OPENAI_API_KEY, project=PROJECT_ID)

# --- Функции парсинга текста ---
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

# --- Интерфейс Streamlit ---
st.set_page_config(page_title="Ассистент Битроникс", layout="centered")
st.title("🤖 Ассистент компании Битроникс")
st.markdown("Загрузи техническое задание и получи разбор:")

uploaded_file = st.file_uploader("📎 Загрузите файл (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file and st.button("🚀 Проанализировать"):
    with st.spinner("Обрабатываю файл..."):
        file_text = read_file(uploaded_file)
        
        if not file_text:
            st.error("❌ Не удалось прочитать файл.")
        else:
            try:
                # GPT-4o, кастомный промпт через system message
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты — ассистент компании Битроникс. "
                                "Твоя задача — анализировать технические задания строго по инструкции компании. "
                                "Сначала сделай анализ, затем выведи результат в виде структурированного текста или JSON."
                            )
                        },
                        {
                            "role": "user",
                            "content": file_text
                        }
                    ]
                )
                result = response.choices[0].message.content.strip()
                st.success("✅ Анализ завершён.")
                st.text_area("📄 Результат анализа:", result, height=400)
                st.download_button("💾 Скачать результат как .txt", result, file_name="результат.txt")

            except Exception as e:
                st.error(f"🚨 Ошибка при обращении к OpenAI: {e}")
