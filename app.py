import streamlit as st
import os
from logic import MrakOrchestrator

st.set_page_config(page_title="MRAK-OS Factory", page_icon="🏭", layout="centered")

def init_session():
    """Безопасная инициализация без вылета по FileNotFoundError."""
    if "orchestrator" not in st.session_state:
        # ПРИОРЯТЕТ 1: Переменные окружения (Render/Docker)
        key = os.environ.get("GROQ_API_KEY")
        
        # ПРИОРЯТЕТ 2: Если в системе нет, пробуем Secrets (Локально), но БЕЗ паники
        if not key:
            try:
                key = st.secrets.get("GROQ_API_KEY")
            except Exception:
                key = None

        if key:
            try:
                st.session_state.orchestrator = MrakOrchestrator(api_key=key)
            except Exception as e:
                st.error(f"Ошибка инициализации оркестратора: {e}")
                st.stop()
        else:
            st.warning("🔑 API Key не найден (проверьте Environment Variables на Render).")
            st.stop()

# Запускаем инициализацию
init_session()

st.title("🏭 MRAK-OS: Самоконфигурируемая Фабрика")
st.caption("v2.0 | Cloud Ready | Optimized for Heavy Payloads")

user_input = st.text_area("Введите запрос:", height=200, placeholder="Напиши что-нибудь...")

if st.button("🚀 ЗАПУСК", type="primary"):
    if user_input:
        answer_container = st.empty()
        metrics_container = st.empty()
        
        with st.spinner("Фабрика работает..."):
            # Проверяем статус системного промпта
            current_prompt = st.session_state.orchestrator.system_prompt
            if current_prompt == "Вы — полезный ИИ-ассистент.":
                st.error("⚠️ Внимание: Системный промпт не загружен (используется fallback).")

            try:
                stream_gen = st.session_state.orchestrator.process_request_stream(user_input)
                
                last_result = None
                for result in stream_gen:
                    if result["success"]:
                        # Рендерим поток текста
                        answer_container.markdown(result["full_content"] + "▌")
                        metrics_container.caption(f"⏱ Время обработки: {result['elapsed']:.2f} сек.")
                        last_result = result
                    else:
                        st.error(f"Ошибка API: {result['error']}")
                        st.stop()
                
                # Финальный рендер без курсора
                if last_result:
                    answer_container.markdown(last_result["full_content"])
            
            except Exception as e:
                st.error(f"Критическая ошибка выполнения: {e}")
    else:
        st.info("Поле запроса пусто.")