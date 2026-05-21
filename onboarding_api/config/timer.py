import time
from functools import wraps


def log_execution_time(logger):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            start_time = time.perf_counter()

            logger.info(
                f"{func.__name__} execution started"
            )

            try:
                result = func(*args, **kwargs)

                logger.info(
                    f"{func.__name__} execution completed successfully"
                )

                return result

            except Exception as e:

                logger.exception(
                    f"{func.__name__} execution failed: {str(e)}"
                )

                raise

            finally:

                execution_time = (
                    time.perf_counter() - start_time
                )

                logger.info(
                    f"{func.__name__} execution completed in "
                    f"{execution_time:.4f} seconds"
                )

        return wrapper

    return decorator