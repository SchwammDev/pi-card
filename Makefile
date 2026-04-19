.PHONY: install run service uninstall clean

CONFIG_DIR  := $(HOME)/.config/pi-card
CONFIG_FILE := $(CONFIG_DIR)/config.yaml
STATE_DIR   := $(HOME)/.local/state/pi-card
SYSTEMD_DIR := $(HOME)/.config/systemd/user
UNIT_NAME   := pi-card.service
UNIT_FILE   := $(SYSTEMD_DIR)/$(UNIT_NAME)
UV          := $(shell command -v uv)

install:
	@if [ -z "$(UV)" ]; then echo "uv not found in PATH"; exit 1; fi
	$(UV) sync
	@mkdir -p $(CONFIG_DIR)
	@if [ ! -f $(CONFIG_FILE) ]; then \
		cp config.yaml.example $(CONFIG_FILE); \
		echo "Wrote default config to $(CONFIG_FILE). Edit it to set base_url, api_key, model."; \
	else \
		echo "Config already exists at $(CONFIG_FILE); leaving it untouched."; \
	fi

run:
	$(UV) run python -m pi_card --config $(CONFIG_FILE) --log-level INFO

service: install
	@mkdir -p $(SYSTEMD_DIR)
	sed -e 's|@WORKDIR@|$(CURDIR)|g' \
	    -e 's|@UV@|$(UV)|g' \
	    -e 's|@CONFIG@|$(CONFIG_FILE)|g' \
	    systemd/pi-card.service.in > $(UNIT_FILE)
	systemctl --user daemon-reload
	systemctl --user enable --now $(UNIT_NAME)
	@echo "Service installed. For auto-start without login: sudo loginctl enable-linger $$USER"

uninstall:
	-systemctl --user disable --now $(UNIT_NAME) 2>/dev/null || true
	-rm -f $(UNIT_FILE)
	-systemctl --user daemon-reload 2>/dev/null || true
	-rm -rf $(CONFIG_DIR)
	-rm -rf $(STATE_DIR)
	@echo "pi-card uninstalled (service, config, and logs removed)."

clean:
	rm -rf .venv .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
