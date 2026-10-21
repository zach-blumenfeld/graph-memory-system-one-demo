UV ?= uv
LOAN = $(UV) run loan

.PHONY: sync doctor fixture import rule reset record export author serve console publish verify clean fresh

sync:
	$(UV) sync
	$(UV) tool install --editable . --force   # `loan` on PATH for Claude Code's Bash

doctor:
	$(LOAN) doctor

fixture: ## step 1: regenerate data/bank/*.json (deterministic)
	$(UV) run python tools/make_fixture.py
	$(LOAN) verify fixture

import: ## step 2: the five bank systems -> memory (R7 does not exist yet; `make rule` adds it)
	$(LOAN) import --without-rule R7

rule: ## the rule change: add R7 to the compliance system in memory (Rule node + SUBJECT_TO edges)
	$(LOAN) import --rules-only

reset: ## wipe the memory database
	$(LOAN) reset --yes

record: ## step 4: five headless agent runs (minutes each)
	$(LOAN) record --all
	$(LOAN) verify traces

export: ## step 5a: source/ for the AIP authoring skill
	$(LOAN) traces export

author: ## step 5b: Claude Code + the aip authoring skill compile ./skills/assess-business-loan from source/
	mkdir -p .run
	LOAN_RECORD=0 claude -p "$$(cat prompts/author.md)" --allowedTools "Read,Write,Edit,Glob,Grep,Bash,Skill" --permission-mode dontAsk --output-format json > .run/author.json; python3 -c "import json;d=json.load(open('.run/author.json'));print(d.get('result','')[:3000]);print('cost',d.get('total_cost_usd'),'turns',d.get('num_turns'))"

serve: ## step 6: the aip server (reads ~/.config/aip/server.toml); the console is separate, see `make console`
	aip server

console: ## the web console against the server `aip config` names (http://localhost:4280/)
	npx aip-console --server http://localhost:8000

publish: ## step 6: publish the authored skill
	aip validate ./skills/assess-business-loan && aip publish ./skills/assess-business-loan

verify:
	$(LOAN) verify fixture
	$(LOAN) verify import
	$(LOAN) verify traces

clean:
	rm -rf .run

fresh: ## before a live run: forget previous rationales (run files live in ~/.aip/runs)
	rm -rf .run/rationales
