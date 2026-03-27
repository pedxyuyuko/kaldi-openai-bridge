"""Entry point for `python -m bridge`."""

import uvicorn

from bridge.app import create_app
from bridge.config import parse_args


def main() -> None:
    config = parse_args()
    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
