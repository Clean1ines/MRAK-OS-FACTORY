import json
import hashlib

def compute_content_hash(content):
    """Вычисляет SHA256 от канонического JSON представления."""
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
