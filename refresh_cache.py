import json
import logging

from util import tidyhq

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load config from file
with open("config.json") as f:
    config: dict = json.load(f)

# Override the cache expiry time
config["cache_expiry"] = 20 * 60

# Get cache
cache = tidyhq.fresh_cache(config=config, force=True)

# Output some info about the cache

print(f"Cache has {len(cache['contacts'])} contacts")
print(f"Cache has {len(cache['groups'])} groups")
