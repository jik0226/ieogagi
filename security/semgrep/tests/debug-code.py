# Test cases for security/semgrep/debug-code.yml.
# Annotations: the line after a ruleid comment must be reported; after an ok comment it must stay silent.
import logging
import pdb
import pprint
import uvicorn
from fastapi import FastAPI

log = logging.getLogger(__name__)


def prints(value):
    # ruleid: ieogagi-no-print
    print(value)
    # ruleid: ieogagi-no-print
    pprint.pprint(value)
    # ruleid: ieogagi-no-print
    breakpoint()
    # ruleid: ieogagi-no-print
    pdb.set_trace()
    # ok: ieogagi-no-print
    log.info("value received")


# ruleid: ieogagi-no-main-block
if __name__ == "__main__":
    prints(1)

# ruleid: ieogagi-no-main-block
if "__main__" == __name__:
    prints(2)

# ok: ieogagi-no-main-block
if __name__ == "other":
    prints(3)


def modes(flag):
    # ruleid: ieogagi-no-debug-mode
    FastAPI(debug=True)
    # ruleid: ieogagi-no-debug-mode
    uvicorn.run("app.main:app", reload=True)
    # ruleid: ieogagi-no-debug-mode
    logging.basicConfig(level=logging.DEBUG)
    # ruleid: ieogagi-no-debug-mode
    log.setLevel(logging.DEBUG)
    # ok: ieogagi-no-debug-mode
    FastAPI(debug=False, docs_url=None)
    # ok: ieogagi-no-debug-mode
    FastAPI(debug=flag)
    # ok: ieogagi-no-debug-mode
    uvicorn.run("app.main:app", reload=False)
    # ok: ieogagi-no-debug-mode
    logging.basicConfig(level=logging.INFO)
