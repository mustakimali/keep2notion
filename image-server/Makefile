
VERSION?=local
IMAGE_NAME?=mustakimali/private

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE_NAME):$(VERSION) -f Dockerfile .

.PHONY: build
build:
	@cargo build

.PHONY: docker-run
docker-run:
	docker run -ti --rm --name image_server -v $(shell pwd)/data:/app/data/ --publish 8000:8000 $(IMAGE_NAME):$(VERSION)

.PHONY: docker-push
docker-push:
	./Dockerpush.sh

.PHONY: docker-push-local
docker-push-local:
	./Dockerpush.local.sh