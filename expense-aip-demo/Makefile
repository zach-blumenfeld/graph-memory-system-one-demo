# The expense demo on AIP 0.9. `make setup` once, then `make reset` and `make console`; `make down` after.
# Settings come from .env (copy .env.example). This folder has its own servers (8310 main, 8311 empty for
# part 5) and consoles (4283, and 4285 for the loan appendix), so the loan demo's servers are never touched.

-include .env
AIP_DEMO_MAIN_PORT    ?= 8310
AIP_DEMO_EMPTY_PORT   ?= 8311
AIP_DEMO_CONSOLE_PORT ?= 4283
AIP_DEMO_CONSOLE_LOAN_PORT ?= 4285
CONSOLE ?= $(HOME)/dev/aip-0.9/console
MAIN  := http://127.0.0.1:$(AIP_DEMO_MAIN_PORT)
EMPTY := http://127.0.0.1:$(AIP_DEMO_EMPTY_PORT)
# Every aip command below talks to this folder's main server, never to `aip config server`.
export AIP_SERVER := $(MAIN)

.PHONY: setup up down status reset reset-empty prebuild-5 console console-loan _console check check-v2 check-5 publish-solution publish-v2 clean

setup: ## install aip from the checkout, the aip skill into Claude Code, the agent's venv, the console
	uv tool install --force --reinstall --no-cache 'agent-instruction-protocol[server] @ $(HOME)/dev/aip-0.9'
	aip --version
	aip skill install claude-code
	cd agents/langgraph && uv sync -q
	cd $(CONSOLE) && npm install --no-audit --no-fund && npm run build

up: ## both servers in the background: main (.aip/main.rl) and empty (.aip/empty.rl, part 5)
	mkdir -p .aip
	@if curl -fs $(MAIN)/health >/dev/null 2>&1; then echo "main server already up at $(MAIN)"; else \
	  nohup aip server --host 127.0.0.1 --port $(AIP_DEMO_MAIN_PORT) --backend relate --path .aip/main.rl --log-level warning > .aip/main.log 2>&1 < /dev/null & echo $$! > .aip/main.pid; fi
	@if curl -fs $(EMPTY)/health >/dev/null 2>&1; then echo "empty server already up at $(EMPTY)"; else \
	  nohup aip server --host 127.0.0.1 --port $(AIP_DEMO_EMPTY_PORT) --backend relate --path .aip/empty.rl --log-level warning > .aip/empty.log 2>&1 < /dev/null & echo $$! > .aip/empty.pid; fi
	@for i in 1 2 3 4 5 6 7 8 9 10; do curl -fs $(MAIN)/health >/dev/null 2>&1 && curl -fs $(EMPTY)/health >/dev/null 2>&1 && break; sleep 1; done
	@echo "main  $(MAIN)"; curl -fs $(MAIN)/health; echo
	@echo "empty $(EMPTY)"; curl -fs $(EMPTY)/health; echo

down: ## stop both servers and both consoles
	-@for p in main empty console console-loan; do test -f .aip/$$p.pid && kill $$(cat .aip/$$p.pid) 2>/dev/null && rm -f .aip/$$p.pid && echo "stopped $$p"; done; true
	@for i in 1 2 3 4 5 6 7 8 9 10; do curl -fs $(MAIN)/health >/dev/null 2>&1 || curl -fs $(EMPTY)/health >/dev/null 2>&1 || break; sleep 1; done

status:
	@curl -fs $(MAIN)/health && echo || echo "main down ($(MAIN))"
	@curl -fs $(EMPTY)/health && echo || echo "empty down ($(EMPTY))"

reset: down ## forget the main store, the ledger and ./built; keep the empty store (part 5's pre-build); start again
	rm -rf ./built
	rm -f ./.aip/main.rl ./ledger.txt
	$(MAKE) up

reset-empty: down ## forget the empty store too: part 5's pre-build is gone until `make prebuild-5` runs again
	rm -f ./.aip/empty.rl
	$(MAKE) up

prebuild-5: reset-empty ## part 5's first `aip agent` on the empty server, before the demo; writes solutions/part5.md and .session
	AIP_SERVER=$(EMPTY) python3 prebuild_5.py

console: ## the console in the background: http://localhost:4283/ (AIP_DEMO_CONSOLE_PORT)
	@$(MAKE) --no-print-directory _console NAME=console PORT=$(AIP_DEMO_CONSOLE_PORT) WORKDIR=$(CURDIR)

console-loan: ## the appendix: a console whose working directory is ../loan-aip-demo: http://localhost:4285/
	@$(MAKE) --no-print-directory _console NAME=console-loan PORT=$(AIP_DEMO_CONSOLE_LOAN_PORT) WORKDIR=$(abspath $(CURDIR)/../loan-aip-demo)

_console:
	@mkdir -p .aip
	@if test -f .aip/$(NAME).pid && kill -0 $$(cat .aip/$(NAME).pid) 2>/dev/null; then echo "$(NAME) already up: http://localhost:$(PORT)/"; exit 0; fi; \
	 held=$$(lsof -nP -iTCP:$(PORT) -sTCP:LISTEN -t 2>/dev/null | head -1); \
	 if [ -n "$$held" ]; then echo "port $(PORT) is held by pid $$held ($$(ps -o command= -p $$held | cut -c1-80)); kill it, or set its port in .env"; exit 1; fi; \
	 (cd $(CONSOLE) && nohup node bin/aip-console.mjs --server $(MAIN) --port $(PORT) --workdir $(WORKDIR) > $(CURDIR)/.aip/$(NAME).log 2>&1 < /dev/null &); \
	 for i in 1 2 3 4 5 6 7 8 9 10; do curl -fs http://127.0.0.1:$(PORT)/ >/dev/null 2>&1 && break; sleep 1; done; \
	 lsof -nP -iTCP:$(PORT) -sTCP:LISTEN -t 2>/dev/null | head -1 > .aip/$(NAME).pid; \
	 if curl -fs http://127.0.0.1:$(PORT)/ >/dev/null 2>&1; then echo "$(NAME) up: http://localhost:$(PORT)/  (server $(MAIN), workdir $(WORKDIR); log .aip/$(NAME).log)"; else echo "$(NAME) did not start; see .aip/$(NAME).log"; cat .aip/$(NAME).log; exit 1; fi

publish-solution: ## the fallback for part 1: the procedure as the Studio built it in rehearsal
	aip publish solutions/expense_claim_review

publish-v2: ## part 3: the procedure with the rule change, as the next revision
	aip publish solutions/expense_claim_review-v2

check: ## every run beside its known outcome
	python3 check.py

check-v2: ## the same, with runs on the newest revision held to the changed rule
	python3 check.py --v2

check-5: ## part 5: every run of the agent-built procedure on the empty server
	AIP_SERVER=$(EMPTY) python3 check.py --name $$(cat solutions/part5.name)

clean: down
	rm -rf ./.aip ./built
	rm -f ./ledger.txt
