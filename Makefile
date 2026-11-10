.PHONY: test analyze experiment generate

test:
	python -m pytest -q

analyze:
	python -m heatbridge_pk.cli analyze --output-dir outputs

experiment:
	python -m heatbridge_pk.cli experiment --output-dir outputs/default

generate:
	python -m heatbridge_pk.cli generate --output-dir data
