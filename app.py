import streamlit as st
import os
from logic import MrakOrchestrator

st.set_page_config(page_title="MRAK-OS Factory", page_icon="🏭", layout="centered")

def init_session():
    if "orchestrator" not in st.session_state:
        key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
        if key:
            try:
                # Инициализируем с указанием пути к промпту
                st.session_state.orchestrator = MrakOrchestrator(api_key=key)
            except Exception as e:
                st.error(f"Ошибка инициализации: {e}")
                st.stop()
        else:
            st.warning("🔑 API Key не найден.")
            st.stop()

init_session()

st.title("🏭 MRAK-OS: Самоконфигурируемая Фабрика")
user_input = st.text_area("Введите запрос:", height=200)

if st.button("🚀 ЗАПУСК", type="primary"):
    if user_input:
        answer_container = st.empty()
        metrics_container = st.empty()
        
        with st.spinner("Фабрика работает..."):
            # Проверяем, загрузился ли промпт (не дефолтный ли он)
            if st.session_state.orchestrator.system_prompt == "Вы — полезный ИИ-ассистент.":
                st.error("Внимание: system_prompt.txt не найден! Используется резервный режим.")

            stream_gen = st.session_state.orchestrator.process_request_stream(user_input)
            
            last_result = None
            for result in stream_gen:
                if result["success"]:
                    answer_container.markdown(result["full_content"] + "▌")
                    metrics_container.caption(f"⏱ Время: {result['elapsed']:.2f} сек.")
                    last_result = result
                else:
                    st.error(result["error"])
                    st.stop()
            
            if last_result:
                answer_container.markdown(last_result["full_content"])
    else:
        st.info("Поле запроса пусто.")