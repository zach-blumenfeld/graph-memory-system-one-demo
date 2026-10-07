UV ?= uv
PMM = $(UV) run pmm

.PHONY: sync selftest doctor verify demo replay-from clean fixture record distill run-skill report

sync:
	$(UV) sync --all-groups

fixture:
	$(UV) run python tools/make_fixture.py

selftest: ## no network: fakes for Jev and the recorder
	$(UV) run pytest -q
	$(UV) run pmm-tools --selftest

doctor:
	$(PMM) doctor

verify: ## per-stage verifiers against the live workspace
	$(PMM) verify stage1
	$(PMM) verify stage3
	$(PMM) verify stage4
	$(PMM) verify stage5

demo: ## stages 0..5 end to end (needs all keys)
	$(PMM) doctor
	$(PMM) workspace attach
	$(PMM) ontology apply
	$(PMM) notion import
	$(PMM) verify stage1
	$(PMM) record --all
	$(PMM) verify stage3
	$(PMM) distill --install
	$(PMM) verify stage4
	$(PMM) run-skill --brief brief-013
	$(PMM) report

STAGE ?= 5
replay-from: ## start from a committed checkpoint: STAGE=3 replays traces, STAGE=5 runs the committed skill
	$(PMM) replay-from $(STAGE)

record:
	$(PMM) record --all

distill:
	$(PMM) distill --install

run-skill:
	$(PMM) run-skill --brief brief-013

report:
	$(PMM) report

clean:
	rm -rf .run .pytest_cache
