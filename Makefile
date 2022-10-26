#!Makefile

install:
	python3 -m venv venv && \
		source venv/bin/activate && \
		pip install -r requirements.txt

lint:
	source venv/bin/activate && \
		pylint .

create-bundle:
	source venv/bin/activate && \
		pyinstaller --onefile maconomy.py 

install-bundle:
	sudo cp dist/maconomy /usr/local/bin/maconomy