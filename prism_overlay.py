import logging

from examples.overlay.__main__ import main

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Exception caught in main '{e}'")
