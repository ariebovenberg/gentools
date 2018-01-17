.PHONY: docs test build publish clean

init:
	pip install -r requirements/dev.txt

docs:
	@touch docs/api.rst  # ensure api docs always rebuilt
	make -C docs/ html

test:
	detox

test-examples:
	pytest examples/

coverage:
	pytest --cov=gentools --cov-report html --cov-report term --cov-branch --cov-fail-under 100

publish: clean
	rm -rf build dist .egg gentools.egg-info
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean:
	make -C docs/ clean
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf
	python setup.py clean --all
