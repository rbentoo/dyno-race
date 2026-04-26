import argparse
import sys
from src import logger
from src.game.engine import run_human

log = logger.get(__name__)


def main():
    parser = argparse.ArgumentParser(prog="dyno-race")
    parser.add_argument(
        "--mode", choices=["human", "ai", "ai-resume"], required=True,
        help="human=você joga; ai=NEAT do zero; ai-resume=continua do checkpoint",
    )
    args = parser.parse_args()
    log.info("iniciando dyno-race em modo=%s", args.mode)

    try:
        if args.mode == "human":
            run_human()
        else:
            from src.ai.trainer import run as run_ai
            run_ai(resume=(args.mode == "ai-resume"))
    except KeyboardInterrupt:
        log.warning("interrompido pelo usuário (Ctrl+C)")
        sys.exit(130)
    except Exception:
        log.exception("falha não tratada")
        sys.exit(1)
    log.info("encerrado")


if __name__ == "__main__":
    main()
