"""Service layer: the only place that combines the DB with the analytics layer.

Routers stay thin (orchestrate + serialize); analytics stays pure (no DB).
Services bridge the two: load silver rows, shape them for analytics, return
plain results the API can serialize.
"""
