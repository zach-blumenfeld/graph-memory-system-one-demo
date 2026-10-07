UV ?= uv
BLAST = $(UV) run blast

.PHONY: sync doctor import reset record export verify serve publish clean

sync:
	$(UV) sync
	$(UV) tool install --editable . --force   # `blast` on PATH for Claude Code's Bash

doctor:
	$(BLAST) doctor

import: ## step 1: Notion -> memory
	$(BLAST) import

reset: ## wipe the memory database
	$(BLAST) reset --yes

record: ## step 2: four headless agent runs (~25 min, ~$3)
	$(BLAST) record --all
	$(BLAST) verify traces

export: ## step 3a: source/ for the AIP authoring skill
	$(BLAST) traces export

serve: ## step 4: the aip server (reads ~/.config/aip/server.toml)
	aip server --inspector

publish: ## step 4: publish the authored skill
	aip validate ./launch-email-blast && aip publish ./launch-email-blast

clean:
	rm -rf .run
