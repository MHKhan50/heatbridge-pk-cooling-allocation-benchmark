.PHONY: test generate experiment

test:
	python -m unittest discover -s tests -v

generate:
	python -m heatbridge_pk.cli generate --output-dir data --scenarios 60 --neighbourhoods 35 --shelters 9 --seed 17

experiment:
	python -m heatbridge_pk.cli experiment --output-dir outputs --scenarios 60 --neighbourhoods 35 --shelters 9 --seed 17
