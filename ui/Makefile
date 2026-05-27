.PHONY: build install update generate-helm docker-clean uninstall clean format lint test pre-install release

build:
	@if [ -d ../nv-config-manager-temporal ]; then \
		cd ../nv-config-manager-temporal; \
		make build-ui; \
	else \
		echo "Must checkout ../nv-config-manager-temporal to run the full app locally"; \
	fi \

local-install:
	@if [ -d ../nv-config-manager-temporal ]; then \
		cd ../nv-config-manager-temporal; \
		make local-install-with-ui; \
	else \
		echo "Must checkout ../nv-config-manager-temporal to run the full app locally"; \
	fi \

local-update:
	@if [ -d ../nv-config-manager-temporal ]; then \
		cd ../nv-config-manager-temporal; \
		make local-update-with-ui; \
	else \
		echo "Must checkout ../nv-config-manager-temporal to run the full app locally"; \
	fi \

