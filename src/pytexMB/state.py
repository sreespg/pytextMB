"""Content-based freshness. Timestamps rebuild after a checkout or copy that
changes nothing and miss an edit restored from an older file; a hash of the
inputs does neither. A target's hash is recorded only after it builds, so a
failed build is never mistaken for a current one."""
import hashlib
import json


class State:
    def __init__(self, paths, force=False):
        self.paths = paths
        self.force = force
        self.recorded = {}
        try:
            self.recorded = json.loads(paths.state.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        digest = hashlib.sha256()
        for path in paths.inputs():
            digest.update(paths.label(path).encode() + b'\0')
            digest.update(path.read_bytes() + b'\0')
        self.inputs = digest.hexdigest()

    def key(self, *extra):
        return hashlib.sha256('\0'.join([self.inputs, *extra]).encode()).hexdigest()

    def current(self, target, output, key):
        return not self.force and output.is_file() and self.recorded.get(target) == key

    def record(self, target, key):
        self.recorded[target] = key
        self.paths.output.mkdir(parents=True, exist_ok=True)
        self.paths.state.write_text(json.dumps(self.recorded, indent=2) + '\n', encoding='utf-8')
