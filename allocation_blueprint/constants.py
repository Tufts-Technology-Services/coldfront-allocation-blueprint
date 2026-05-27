from coldfront.core.config import ENV


BLUEPRINT_ENABLE_SIGNALS = ENV.get("BLUEPRINT_ENABLE_SIGNALS", "false").lower() == "true"
