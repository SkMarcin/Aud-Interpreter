# Makefile for running the application and tests

.PHONY: run test

# The 'run' target executes main.py with optional -f and -c parameters.
# Usage: make run [FILE=your_file.py] [STRING="your_code"] [CONFIG=your_config.json]
run:
	@echo "Running main.py..."
	@python main.py $(if $(FILE),-f $(FILE)) $(if $(STRING), -s $(STRING)) $(if $(CONFIG),-c $(CONFIG) )

# The 'test' target discovers and runs tests in the tests folder.
test:
	python3 -m unittest discover -s tests -p "*_test.py"