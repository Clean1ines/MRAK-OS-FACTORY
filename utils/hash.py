# ADDED: Utility for content hashing
import hashlib
import json

def compute_content_hash(content):
    """Compute SHA256 hash of sorted JSON content."""
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
