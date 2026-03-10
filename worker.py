import asyncio
import os
import socket
import logging
import signal  # ADDED for graceful shutdown
from dotenv import load_dotenv

from repositories.base import get_connection, transaction
from repositories import node_execution_repository, execution_queue_repository, artifact_repository, workflow_repository
from artifact_service import ArtifactService
from groq_client import GroqClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"

groq_client = GroqClient()
artifact_service = ArtifactService(groq_client)

# ADDED for graceful shutdown
shutdown_event = asyncio.Event()

def handle_sigterm():
    """Обработчик сигналов завершения."""
    logger.info("Received SIGTERM/SIGINT, shutting down gracefully...")
    shutdown_event.set()

async def perform_node_processing(node_exec: dict) -> str:
    """Выполняет логику узла: вызывает LLM, сохраняет артефакт, возвращает artifact_id."""
    node_id = node_exec['node_definition_id']
    node = await workflow_repository.get_workflow_node_by_id(node_id)
    if not node:
        raise RuntimeError(f"Node {node_id} not found")

    node_config = node.get('config', {})
    # FIX: use custom_prompt if system_prompt is missing
    system_prompt = node_config.get('system_prompt')
    if system_prompt is None:
        system_prompt = node_config.get('custom_prompt')
    generation_config = {
        'system_prompt': system_prompt,
        'user_prompt_template': node_config.get('user_prompt_template'),
        'required_input_types': node_config.get('required_input_types', [])
    }
    artifact_type = node.get('node_id')
    input_artifact_ids = node_exec.get('input_artifact_ids') or []
    input_artifacts = await artifact_repository.get_artifacts_by_ids(input_artifact_ids)

    artifact_id = await artifact_service.generate_artifact(
        artifact_type=artifact_type,
        input_artifacts=input_artifacts,
        user_input="",
        model_id=None,
        project_id=node_exec['project_id'],
        generation_config=generation_config
    )
    return artifact_id


async def worker_loop():
    """Основной цикл обработки задач."""
    while not shutdown_event.is_set():  # ADDED shutdown check
        try:
            async with transaction() as tx:
                job = await execution_queue_repository.claim_job(WORKER_ID, tx=tx)
                if not job:
                    # Ожидание с проверкой события
                    await asyncio.sleep(0.5)
                    continue

                node_exec_id = job['node_execution_id']
                # Блокируем и при необходимости обновляем статус выполнения
                node_exec = await tx.conn.fetchrow(
                    "SELECT * FROM node_executions WHERE id = $1 FOR UPDATE", node_exec_id
                )
                if not node_exec:
                    await execution_queue_repository.complete_job(job['id'], success=False, tx=tx)
                    continue

                if node_exec['status'] != 'PROCESSING':
                    await node_execution_repository.update_node_execution_status(
                        node_exec_id, 'PROCESSING', tx=tx
                    )

                node_exec_dict = node_execution_repository._row_to_dict(node_exec)

            # Вне транзакции выполняем долгую операцию
            try:
                artifact_id = await perform_node_processing(node_exec_dict)
                # Успех
                async with transaction() as tx:
                    await node_execution_repository.update_node_execution_status(
                        node_exec_id, "COMPLETED", output_artifact_id=artifact_id, tx=tx
                    )
                    await execution_queue_repository.complete_job(job['id'], success=True, tx=tx)
                logger.info(f"Job {job['id']} completed, artifact {artifact_id}")
            except Exception as e:
                logger.error(f"Job {job['id']} failed: {e}", exc_info=True)
                async with transaction() as tx:
                    await node_execution_repository.update_node_execution_status(
                        node_exec_id, "FAILED", tx=tx
                    )
                    # Проверяем возможность повторной попытки
                    node_exec = await tx.conn.fetchrow(
                        "SELECT * FROM node_executions WHERE id = $1 FOR UPDATE", node_exec_id
                    )
                    if node_exec['attempt'] < node_exec['max_attempts']:
                        new_exec_id = await node_execution_repository.create_retry_attempt(
                            node_execution_repository._row_to_dict(node_exec), tx=tx
                        )
                        await execution_queue_repository.enqueue(new_exec_id, tx=tx)
                        # Текущую задачу помечаем как DONE (она выполнила свою работу)
                        await execution_queue_repository.complete_job(job['id'], success=True, tx=tx)
                    else:
                        # Попытки исчерпаны – задача окончательно FAILED
                        await execution_queue_repository.complete_job(job['id'], success=False, tx=tx)
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            # Короткая пауза перед следующей попыткой
            for _ in range(10):  # ADDED shutdown check during sleep
                if shutdown_event.is_set():
                    break
                await asyncio.sleep(0.5)


async def recovery_loop():
    """Периодически сбрасывает зависшие задачи."""
    while not shutdown_event.is_set():  # ADDED shutdown check
        await asyncio.sleep(60)  # раз в минуту
        if shutdown_event.is_set():  # ADDED check after sleep
            break
        try:
            async with transaction() as tx:
                count = await execution_queue_repository.reset_stuck_jobs(timeout_minutes=10, tx=tx)
                if count:
                    logger.info(f"Recovery: reset {count} stuck jobs")
        except Exception as e:
            logger.error(f"Recovery error: {e}")


async def main():
    """Главная функция: настраивает сигналы и запускает циклы."""
    loop = asyncio.get_running_loop()
    # ADDED signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_sigterm)

    worker_task = asyncio.create_task(worker_loop())
    recovery_task = asyncio.create_task(recovery_loop())

    # Ожидаем сигнала завершения
    await shutdown_event.wait()

    # Отменяем задачи и ждём их завершения
    worker_task.cancel()
    recovery_task.cancel()
    await asyncio.gather(worker_task, recovery_task, return_exceptions=True)
    logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())