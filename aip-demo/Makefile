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
	aip validate ./skills/launch-email-blast && aip publish ./skills/launch-email-blast

clean:
	rm -rf .run

author: ## step 3b: Claude Code + the aip authoring skill compile ./skills/launch-email-blast from source/ (~15 min)
	claude -p "$$(cat prompts/author.md)" --allowedTools "Read,Write,Edit,Glob,Grep,Bash,Skill" --permission-mode dontAsk --output-format json > .run/author.json; python3 -c "import json;d=json.load(open('.run/author.json'));print(d.get('result','')[:3000]);print('cost',d.get('total_cost_usd'),'turns',d.get('num_turns'))"

fresh: ## before a live run: forget previous local runs, drafts and the campaign-log working copy
	rm -rf .aip/runs .run/drafts .run/notion drafts
