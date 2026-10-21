riverbed 1.8 is out. Pipeline state is now checkpointed. A restarted worker resumes where it stopped, without reprocessing.

Upgrade with one pip install:

```
pip install -U riverbed
```

1.8 also adds a CLI command that inspects a checkpoint. You can see what state a worker will resume from before you restart it. The quickstart shows the command and its output.

riverbed is a Tessera Labs project.

Upgrade and open the [checkpoint quickstart](https://tessera-labs.example/riverbed/). The full list of changes is in the [changelog](https://github.com/tessera-labs/riverbed/releases).

Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
