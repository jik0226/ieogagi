# Test cases for security/semgrep/unsafe-api.yml.
# Annotations: the line after a ruleid comment must be reported; after an ok comment it must stay silent.
import marshal
import pickle
import shelve
import tempfile

import yaml
from yaml import SafeLoader


def deserialize(raw, path):
    # ruleid: ieogagi-no-unsafe-deserialization
    pickle.loads(raw)
    # ruleid: ieogagi-no-unsafe-deserialization
    pickle.load(raw)
    # ruleid: ieogagi-no-unsafe-deserialization
    marshal.loads(raw)
    # ruleid: ieogagi-no-unsafe-deserialization
    shelve.open(path)
    # ruleid: ieogagi-no-unsafe-deserialization
    yaml.load(raw)
    # ruleid: ieogagi-no-unsafe-deserialization
    yaml.load(raw, Loader=yaml.Loader)
    # ruleid: ieogagi-no-unsafe-deserialization
    yaml.unsafe_load(raw)
    # ok: ieogagi-no-unsafe-deserialization
    yaml.safe_load(raw)
    # ok: ieogagi-no-unsafe-deserialization
    yaml.load(raw, Loader=yaml.SafeLoader)
    # ok: ieogagi-no-unsafe-deserialization
    yaml.load(raw, Loader=SafeLoader)
    # ok: ieogagi-no-unsafe-deserialization
    yaml.load(raw, yaml.SafeLoader)


def temp_files():
    # ruleid: ieogagi-no-tempfile-mktemp
    tempfile.mktemp()
    # ruleid: ieogagi-no-tempfile-mktemp
    tempfile.mktemp(suffix=".txt")
    # ok: ieogagi-no-tempfile-mktemp
    tempfile.mkstemp()
    # ok: ieogagi-no-tempfile-mktemp
    tempfile.NamedTemporaryFile()
