from enferno.utils.logging_utils import get_logger

# Configure the logger
logger = get_logger()

# Log the initial configuration
logger.info("Bayanat is starting up...")

try:
    from enferno.app import create_app
    from enferno.settings import Config

    # Create the Flask application
    app = create_app(Config())
    app.logger = logger
    logger.info("Bayanat is up!")

except Exception as e:
    logger.error("Error during Bayanat startup.", exc_info=True)
    raise
