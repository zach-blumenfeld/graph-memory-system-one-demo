# The loan demo on AIP 0.9. `make setup`, `make up`, then the README's four parts; `make down`.
# Settings come from .env (copy .env.example); defaults below.

-include .env
AIP_DEMO_BACKEND    ?= local
AIP_DEMO_BACKEND    := $(strip $(AIP_DEMO_BACKEND))
AIP_DEMO_MAIN_PORT  ?= 8300
AIP_DEMO_EMPTY_PORT ?= 8301
AIP_DEMO_CONSOLE_PORT       ?= 4280
AIP_DEMO_CONSOLE_EMPTY_PORT ?= 4281
AIP_DEMO_AURA_DATABASE ?= neo4j
CONSOLE ?= $(HOME)/dev/aip-0.9/console
MAIN  := http://127.0.0.1:$(AIP_DEMO_MAIN_PORT)
EMPTY := http://127.0.0.1:$(AIP_DEMO_EMPTY_PORT)

ifeq ($(AIP_DEMO_BACKEND),aura)
MAIN_BACKEND := --backend neo4j --uri "$(AIP_DEMO_AURA_URI)" --user "$(AIP_DEMO_AURA_USER)" --password "$(AIP_DEMO_AURA_PASSWORD)" --database "$(AIP_DEMO_AURA_DATABASE)"
else
MAIN_BACKEND := --backend relate --path .aip/main.rl
endif

.PHONY: setup up down status reset reset-empty prebuild-4 console console-empty _console check check-v2 check-4 publish-solution publish-v2 clean

setup: ## install aip from the checkout, the aip skill into Claude Code, the agents' venvs, the console
	uv tool install --force --reinstall --no-cache 'agent-instruction-protocol[server] @ $(HOME)/dev/aip-0.9'
	aip --version
	aip skill install claude-code
	aip config server $(MAIN)
	cd agents/adk && uv sync -q
	cd agents/langgraph && uv sync -q
	cd $(CONSOLE) && npm install --no-audit --no-fund && npm run build

up: ## both servers in the background: the main one (parts 1 to 3) and the empty one (part 4); the client points at the main one
	mkdir -p .aip
	@if curl -fs $(MAIN)/health >/dev/null 2>&1; then echo "main server already up at $(MAIN)"; else \
	  nohup aip server --host 127.0.0.1 --port $(AIP_DEMO_MAIN_PORT) $(MAIN_BACKEND) --log-level warning > .aip/main.log 2>&1 & echo $$! > .aip/main.pid; fi
	@if curl -fs $(EMPTY)/health >/dev/null 2>&1; then echo "empty server already up at $(EMPTY)"; else \
	  nohup aip server --host 127.0.0.1 --port $(AIP_DEMO_EMPTY_PORT) --backend relate --path .aip/empty.rl --log-level warning > .aip/empty.log 2>&1 & echo $$! > .aip/empty.pid; fi
	@for i in 1 2 3 4 5 6 7 8 9 10; do curl -fs $(MAIN)/health >/dev/null 2>&1 && curl -fs $(EMPTY)/health >/dev/null 2>&1 && break; sleep 1; done
	@echo "main  $(MAIN)   ($(AIP_DEMO_BACKEND))"; curl -fs $(MAIN)/health; echo
	@echo "empty $(EMPTY)  (relate, .aip/empty.rl)"; curl -fs $(EMPTY)/health; echo
	@aip config server $(MAIN) >/dev/null && echo "aip config server $(MAIN)"

down: ## stop both servers and both consoles, and wait until the server ports are closed
	-@for p in main empty console console-empty; do test -f .aip/$$p.pid && kill $$(cat .aip/$$p.pid) 2>/dev/null && rm -f .aip/$$p.pid && echo "stopped $$p"; done; true
	@for i in 1 2 3 4 5 6 7 8 9 10; do curl -fs $(MAIN)/health >/dev/null 2>&1 || curl -fs $(EMPTY)/health >/dev/null 2>&1 || break; sleep 1; done

status:
	@curl -fs $(MAIN)/health && echo || echo "main down ($(MAIN))"
	@curl -fs $(EMPTY)/health && echo || echo "empty down ($(EMPTY))"

reset: down ## forget the main store (only when local) and the live build under ./built, keep the empty server's store (part 4's pre-build), and start again
	rm -rf built
	@if [ "$(AIP_DEMO_BACKEND)" = "local" ]; then rm -f .aip/main.rl; else echo "aura store left as it is; empty it in Aura if you need to"; fi
	$(MAKE) up

reset-empty: down ## forget the empty server's store too: part 4's pre-build is gone until `make prebuild-4` runs again
	rm -f .aip/empty.rl
	$(MAKE) up

prebuild-4: reset-empty ## part 4's first `aip agent` on the empty server, done before the demo; records solutions/part4.md and solutions/part4.session
	AIP_SERVER=$(EMPTY) python3 prebuild_4.py

console: ## the console on the main server, in the background: http://localhost:4280/ (AIP_DEMO_CONSOLE_PORT)
	@$(MAKE) --no-print-directory _console NAME=console SERVER=$(MAIN) PORT=$(AIP_DEMO_CONSOLE_PORT)

console-empty: ## a second console on the empty server: http://localhost:4281/ (AIP_DEMO_CONSOLE_EMPTY_PORT)
	@$(MAKE) --no-print-directory _console NAME=console-empty SERVER=$(EMPTY) PORT=$(AIP_DEMO_CONSOLE_EMPTY_PORT)

_console:
	@mkdir -p .aip
	@if test -f .aip/$(NAME).pid && kill -0 $$(cat .aip/$(NAME).pid) 2>/dev/null; then echo "$(NAME) already up: http://localhost:$(PORT)/"; exit 0; fi; \
	 held=$$(lsof -nP -iTCP:$(PORT) -sTCP:LISTEN -t 2>/dev/null | head -1); \
	 if [ -n "$$held" ]; then echo "port $(PORT) is held by pid $$held ($$(ps -o command= -p $$held | cut -c1-80)); kill it, or set AIP_DEMO_CONSOLE_PORT / AIP_DEMO_CONSOLE_EMPTY_PORT in .env"; exit 1; fi; \
	 (cd $(CONSOLE) && nohup node bin/aip-console.mjs --server $(SERVER) --port $(PORT) --workdir $(CURDIR) > $(CURDIR)/.aip/$(NAME).log 2>&1 & echo $$! > $(CURDIR)/.aip/$(NAME).pid); \
	 for i in 1 2 3 4 5 6 7 8 9 10; do curl -fs http://127.0.0.1:$(PORT)/ >/dev/null 2>&1 && break; sleep 1; done; \
	 if curl -fs http://127.0.0.1:$(PORT)/ >/dev/null 2>&1; then echo "$(NAME) up: http://localhost:$(PORT)/  (server $(SERVER); log .aip/$(NAME).log; make down stops it)"; else echo "$(NAME) did not start; see .aip/$(NAME).log"; cat .aip/$(NAME).log; exit 1; fi

publish-solution: ## the fallback for part 1: the prebuilt, tested procedure
	aip publish solutions/assess_business_loan

publish-v2: ## the fallback for part 3: the procedure with the rule change, as the next revision
	aip publish solutions/assess_business_loan-v2

check: ## every run beside its known outcome
	python3 check.py

check-v2: ## the same, with runs on the newest revision held to the changed rule
	python3 check.py --v2

check-4: ## part 4: every run of the agent-built procedure on the empty server beside the known outcome
	AIP_SERVER=$(EMPTY) python3 check.py --name $$(cat solutions/part4.name)

clean: down
	rm -rf .aip
