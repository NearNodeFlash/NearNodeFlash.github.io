# Runs a container that lints all markdown (.md) files in the project.
# Uses the markdownlint-cli (https://github.com/igorshubovych/markdownlint-cli).
# Rules for markdownlint package can be found here:
# https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md
markdownlint:
	docker run --rm --name markdownlint \
		--volume ${PWD}:/workdir \
		ghcr.io/igorshubovych/markdownlint-cli:latest \
		--config .markdownlint.jsonc --ignore venv "**/*.md"

