build:
	docker build -t buddy-ai-test -f dockerfiles/python-3.11-base.dockefile .

bash: build
	docker run -it --entrypoint bash buddy-ai-test

serve: build
	docker run -it buddy-ai-test

