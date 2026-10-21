Upgrade riverbed to 1.8.1 today if you run 1.8.0.

```
pip install -U riverbed
```

riverbed 1.8.0 can write a checkpoint twice when a checkpoint write is retried. Version 1.8.1 fixes that bug.

The upgrade is a drop-in pip install. It needs no config change. Your pipelines keep checkpointing state so a restarted worker resumes without reprocessing.

riverbed is a Tessera Labs project. Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
