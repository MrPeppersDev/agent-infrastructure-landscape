"""memory_bench — a neutral, reproducible benchmark for AI agent memory layers.

Every system is measured the same way: it ingests the same conversation
history through its own write path, is asked to retrieve memories for each
question through its own read path, and then ONE shared answer model turns
the retrieved memories into an answer that ONE shared judge model grades.
Only the memory layer differs between runs.

See bench/README.md for methodology, datasets and how to add a system.
"""

__version__ = "0.1.0"
