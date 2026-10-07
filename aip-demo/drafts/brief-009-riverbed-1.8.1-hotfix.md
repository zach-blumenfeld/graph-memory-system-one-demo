If you run riverbed 1.8.0, you can move to 1.8.1 now with a single pip install. 1.8.1 fixes a retry bug in checkpoint writes.

## What was wrong in 1.8.0

Under retry, 1.8.0 can write the same checkpoint twice. A worker that restarts after a double write may resume from the wrong offset.

## What 1.8.1 changes

1.8.1 fixes the retry path so each checkpoint is written once. Checkpoints again do what they are meant to do: a restarted worker resumes without reprocessing.

## What the upgrade involves

The upgrade is a drop-in pip install. The API is unchanged. You do not need to change your config or your pipeline code.

Check your version after the install:

```
python -c "import riverbed; print(riverbed.__version__)"
```

Release notes and the diff are in the repo: https://github.com/tessera-labs/riverbed

riverbed is a Tessera Labs project. It is experimental and community-supported.

**Upgrade today:**

```
pip install -U riverbed
```

Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
