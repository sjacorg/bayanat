# -*- coding: utf-8 -*-
import os

from celery.signals import worker_ready

from enferno.utils.logging_utils import get_logger

import enferno.tasks as tasks_pkg
from enferno.tasks import celery, cfg

logger = get_logger("celery.tasks.ml")


@celery.task
def load_whisper_model():
    if not tasks_pkg._flask_app.config["HAS_WHISPER"]:
        logger.warning("Whisper not available, skipping model load.")
        return
    try:
        # check if whisper is already downloaded
        whisper_model = cfg.WHISPER_MODEL
        if os.path.exists(
            os.path.expanduser(f"~/.cache/whisper/{whisper_model}.pt")
        ) and os.path.isfile(os.path.expanduser(f"~/.cache/whisper/{whisper_model}.pt")):
            logger.info("Whisper model already downloaded")
            return
        logger.info("Downloading Whisper model...")
        import whisper

        whisper.load_model(whisper_model)
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")


@worker_ready.connect
def load_whisper_model_on_startup(sender, **kwargs):
    if cfg.TRANSCRIPTION_ENABLED:
        load_whisper_model.delay()
    else:
        logger.info("Whisper model not loaded, transcription is disabled")
