VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install run ai ai-resume results clean help

help:
	@echo "Dyno Race — comandos disponíveis:"
	@echo "  make install      cria venv e instala dependências"
	@echo "  make run          modo humano (espaço pula, ↓ abaixa)"
	@echo "  make ai           NEAT do zero (treina nova população)"
	@echo "  make ai-resume    continua treinando do melhor genoma salvo"
	@echo "  make results      gera e abre relatório HTML dos experimentos"
	@echo "  make clean        remove venv e checkpoints"

install:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; echo "→ .env criado a partir de .env.example"; fi

run:
	$(PY) -m src.main --mode human

ai:
	$(PY) -m src.main --mode ai

ai-resume:
	$(PY) -m src.main --mode ai-resume

results:
	$(PY) -m src.reports.results

clean:
	rm -rf $(VENV) checkpoints/*.pkl logs/
