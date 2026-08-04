.DEFAULT_GOAL := help
.PHONY: help data build index serve test clean deploy

help: ## Show this list of targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

data: ## Run the Python ETL against mail_archives/ and write data/posts.json. Human-run only — never invoked by `build` (mail_archives/ is gitignored and absent in CI).
	python3 pipeline/etl.py

build: ## Build the static site from the already-committed data/posts.json, then generate the search index.
	npx @11ty/eleventy
	$(MAKE) index

index: ## Generate the Pagefind search index against the built site.
	npx pagefind --site _site

serve: ## Run the Eleventy dev server with live reload.
	npx @11ty/eleventy --serve

test: ## Run the automated test suite (data integrity, functional, accessibility, performance, link integrity) against the built site.
	./scripts/run-tests.sh

clean: ## Remove build output. data/posts.json is a committed artifact and is left untouched.
	rm -rf _site .cache

deploy: build test ## Manual-fallback build+test; the primary deploy path is the GitHub Actions workflow on push to main.
	@echo "Build and test complete. Primary deployment path is GitHub Actions (push to main) — see .github/workflows/deploy.yml."
