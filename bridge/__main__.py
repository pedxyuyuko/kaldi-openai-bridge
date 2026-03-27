"""Entry point for `python -m bridge`."""

import logging

import uvicorn

from bridge.app import create_app
from bridge.config import parse_args


def main() -> None:
    config = parse_args()

    logging.basicConfig(
        level=config.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
