# Test cases for security/semgrep/error-handling.yml.
# Annotations: the line after a ruleid comment must be reported; after an ok comment it must stay silent.
import logging
import traceback

from fastapi import HTTPException
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


def broad(work):
    # ruleid: ieogagi-no-broad-except
    try:
        work()
    except Exception:
        log.info("failed")

    # ruleid: ieogagi-no-broad-except
    try:
        work()
    except Exception as exc:
        log.info("failed %s", type(exc).__name__)

    # ruleid: ieogagi-no-broad-except
    try:
        work()
    except BaseException:
        log.info("failed")

    # ruleid: ieogagi-no-broad-except
    try:
        work()
    except:  # noqa: E722
        log.info("failed")

    # ruleid: ieogagi-no-broad-except
    try:
        work()
    except ValueError:
        log.info("value")
    except Exception:
        log.info("failed")

    # ruleid: ieogagi-no-broad-except
    try:
        work()
    except (ValueError, Exception):
        log.info("failed")

    # ok: ieogagi-no-broad-except
    try:
        work()
    except ValueError:
        log.info("value")

    # ok: ieogagi-no-broad-except
    try:
        work()
    except (ValueError, KeyError) as exc:
        log.info("value %s", type(exc).__name__)


def empty(work):
    # ruleid: ieogagi-no-empty-except
    try:
        work()
    except ValueError:
        pass

    # ruleid: ieogagi-no-empty-except
    try:
        work()
    except ValueError as exc:
        pass

    # ruleid: ieogagi-no-broad-except, ieogagi-no-empty-except
    try:
        work()
    except:  # noqa: E722
        pass

    for item in range(3):
        # ruleid: ieogagi-no-empty-except
        try:
            work(item)
        except KeyError:
            continue

    # ok: ieogagi-no-empty-except
    try:
        work()
    except ValueError:
        log.warning("value error while working")

    # ok: ieogagi-no-empty-except
    try:
        work()
    except KeyError:
        raise


def leak(work):
    # ruleid: ieogagi-no-exception-leak
    traceback.format_exc()
    # ruleid: ieogagi-no-exception-leak
    traceback.print_exc()

    try:
        work()
    except ValueError as exc:
        # ruleid: ieogagi-no-exception-leak
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        work()
    except ValueError as exc:
        # ruleid: ieogagi-no-exception-leak
        raise HTTPException(status_code=400, detail=f"failed: {exc}")

    try:
        work()
    except ValueError as exc:
        # ruleid: ieogagi-no-exception-leak
        return JSONResponse({"error": {"message": str(exc)}}, status_code=500)

    try:
        work()
    except ValueError as exc:
        # ruleid: ieogagi-no-exception-leak
        return repr(exc)

    try:
        work()
    except ValueError:
        # ok: ieogagi-no-exception-leak
        raise HTTPException(status_code=400, detail="invalid request")

    try:
        work()
    except ValueError:
        log.exception("work failed")
        # ok: ieogagi-no-exception-leak
        return JSONResponse({"error": {"code": "bad_request", "message": "invalid request"}})


def leak_through_variable(work, flag):
    try:
        work()
    except ValueError as exc:
        message = str(exc)
        # ruleid: ieogagi-no-exception-leak
        return message

    try:
        work()
    except ValueError as exc:
        detail = f"failed: {exc}"
        log.warning("failed")
        # ruleid: ieogagi-no-exception-leak
        raise HTTPException(status_code=400, detail=detail)

    try:
        work()
    except ValueError as exc:
        text = repr(exc)
        # ruleid: ieogagi-no-exception-leak
        return JSONResponse({"error": {"code": "bad_request", "message": text}})

    try:
        work()
    except KeyError as exc:
        reason = exc.args[0]
        # ruleid: ieogagi-no-exception-leak
        raise HTTPException(status_code=404, detail={"reason": reason})

    try:
        work()
    except ValueError as exc:
        prefixed = "failed: " + str(exc)
        if flag:
            # ruleid: ieogagi-no-exception-leak
            return prefixed

    error = None
    try:
        work()
    except ValueError as exc:
        error = str(exc)
    if error:
        # ruleid: ieogagi-no-exception-leak
        raise HTTPException(status_code=400, detail=error)


def no_leak_through_variable(work):
    try:
        work()
    except ValueError as exc:
        message = type(exc).__name__
        log.info("failed %s", message)
        # ok: ieogagi-no-exception-leak
        return message

    try:
        work()
    except ValueError as exc:
        reason = str(exc)
        log.warning("failed: %s", reason)
        # ok: ieogagi-no-exception-leak
        raise HTTPException(status_code=400, detail="invalid request")

    safe = "invalid request"
    try:
        work()
    except ValueError:
        # ok: ieogagi-no-exception-leak
        return safe


async def handler(request, exc: Exception):
    # ruleid: ieogagi-no-exception-leak
    return JSONResponse({"error": {"code": "internal", "message": str(exc)}}, status_code=500)


async def validation_handler(request, exc: ValueError):
    # ruleid: ieogagi-no-exception-leak
    return JSONResponse({"error": exc.errors()}, status_code=422)


async def safe_handler(request, exc: Exception):
    # ok: ieogagi-no-exception-leak
    return JSONResponse({"error": {"code": "internal", "message": "internal error"}}, status_code=500)


def unrelated(user_id: int):
    # ok: ieogagi-no-exception-leak
    return {"id": str(user_id)}


def ellipsis_body(work):
    try:
        work()
    # ruleid: ieogagi-no-empty-except
    except ValueError:
        ...


async def handler_through_variable(request, exc: Exception):
    message = str(exc)
    # ruleid: ieogagi-no-exception-leak
    return JSONResponse({"error": {"code": "internal", "message": message}}, status_code=500)


async def validation_handler_through_variable(request, exc: ValueError):
    errors = exc.errors()
    # ruleid: ieogagi-no-exception-leak
    return JSONResponse({"error": errors}, status_code=422)


async def safe_handler_through_variable(request, exc: Exception):
    log.error("failed: %s", str(exc))
    message = "internal error"
    # ok: ieogagi-no-exception-leak
    return JSONResponse({"error": {"code": "internal", "message": message}}, status_code=500)
