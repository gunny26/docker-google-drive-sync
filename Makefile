# latest platform is local
export PLATFORM_LATEST ?= linux/amd64
# stable platform is target system
export PLATFORM_STABLE ?= linux/arm64/v8

export GITHUB_GHCR ?= ghcr.io
export GITHUB_USERNAME ?= gunny26
export REPOSITORY_NAME ?= $(shell pwd | rev | cut -d/ -f 1 | rev)

export DESCRIPTION ?= $(shell cat ./TITLE)
export DATESTRING ?= $(shell date -I)
export TAG ?= $(shell git describe --always)

export REGISTRY ?= $(GITHUB_GHCR)/$(GITHUB_USERNAME)/$(REPOSITORY_NAME)
export IMAGE_NAME ?= $(REGISTRY):$(DATESTRING)-$(TAG)
export IMAGE_NAME_LATEST ?= $(REGISTRY):latest
export IMAGE_NAME_STABLE ?= $(REGISTRY):stable

test:
	# needs docker-compose-v2 to be installed
	docker compose up -d && docker compose down

latest:
	git checkout latest
	git add . || git commit -a -m "automatic latest image built commit"
	git push origin latest
	echo "building image tag $(IMAGE_NAME) and $(IMAGE_NAME_LATEST)"
	docker buildx build \
 	--label "org.opencontainers.image.source=https://github.com/$(GITHUB_USERNAME)/$(REPOSITORY_NAME)" \
 	--label "org.opencontainers.image.description=My container $(REPOSITORY_NAME)" \
 	--label "org.opencontainers.image.licenses=MIT" \
	--label "org.opencontainers.image.description=$(DESCRIPTION)" \
	--platform $(PLATFORM_LATEST) \
	--tag $(IMAGE_NAME) \
	--tag $(IMAGE_NAME_LATEST) \
	.

stable:
	git checkout main
	git pull origin main
	git merge latest
	# echo "building image tag $(IMAGE_NAME) and $(IMAGE_NAME_STABLE)"
	# docker buildx build \
 	# --label "org.opencontainers.image.source=https://github.com/$(GITHUB_USERNAME)/$(REPOSITORY_NAME)" \
 	# --label "org.opencontainers.image.description=My container $(REPOSITORY_NAME)" \
 	# --label "org.opencontainers.image.licenses=MIT" \
	# --label "org.opencontainers.image.description=$(DESCRIPTION)" \
	# --platform $(PLATFORM_LATEST) \
	# --platform $(PLATFORM_STABLE) \
	# --tag $(IMAGE_NAME) \
	# --tag $(IMAGE_NAME_STABLE) \
	# --push \
	# .
	# back to latest
	git checkout latest

lint:
	ruff check build/main.py
	ruff format build/main.py

clean:
	docker buildx prune
