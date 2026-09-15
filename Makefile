.PHONY: install run dashboard check

install:
	python -m pip install -e '.[dev]'

run:
	precision-farm --scenario mixed --ticks 60 --seed 42

dashboard:
	streamlit run app.py

check:
	ruff check .
	pytest -q

