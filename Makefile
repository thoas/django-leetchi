pep8:
	flake8 djleetchi --ignore=E501,E127,E128,E124

test:
	coverage run --branch --source=djleetchi manage.py test -s -x djleetchi
	coverage report --omit=djleetchi/test*

release:
	python setup.py sdist register upload -s
