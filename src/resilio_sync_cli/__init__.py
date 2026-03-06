import logging
import re
import sys
import warnings
from argparse import ArgumentParser
from argparse import Namespace
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from typing import Any
from typing import Iterator
from urllib.parse import urlencode
from urllib.parse import urljoin
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from requests import Session
from urllib3.exceptions import InsecureRequestWarning


class UserError(Exception):
    pass


@dataclass
class ResilioSyncSession:
    session: Session
    base_url: str
    token: str

    def call(self, action: str, /, **kwargs: str) -> Any:
        parts = urlsplit(urljoin(self.base_url, "gui/"))
        parts = parts._replace(
            query=urlencode(dict(token=self.token, action=action, **kwargs))
        )

        response = self.session.get(urlunsplit(parts))
        return response.json()


@contextmanager
def resilio_sync_session(base_url: str) -> Iterator[ResilioSyncSession]:
    with Session() as session:
        session.verify = False

        response = session.get(urljoin(base_url, "gui/token.html"))
        match = re.search("[^>]+(?=</div>)", response.text)
        assert match
        token = match.group()

        yield ResilioSyncSession(session, base_url, token)


def rescan_command(base_url: str, local_path: Path) -> None:
    local_path = local_path.absolute()

    with resilio_sync_session(base_url) as session:
        s = Session()
        s.verify = False

        result = session.call("getsyncfolders", discovery="1")
        folder_paths_by_ids = {i["id"]: Path(i["path"]) for i in result["folders"]}
        id = next(
            (
                id
                for id, path in folder_paths_by_ids.items()
                if path.is_relative_to(local_path)
            ),
            None,
        )

        if id is None:
            raise UserError(
                f'No synced folder found containing path "{local_path}".\n'
                f"Synced folders:\n"
                f"{'\n'.join(sorted(f'- {i}' for i in folder_paths_by_ids.values()))}"
            )

        logging.info(f'Re-scanning folder "{folder_paths_by_ids[id]}" with ID {id}.')
        result = session.call("rescanfolder", id=id)

        if result["status"] != 200:
            raise UserError(
                f"Error:\n"  #
                f"{pformat(result)}"
            )


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--base-url", type=str, required=True)

    subparsers = parser.add_subparsers(dest="command", required=True)

    rescan_parser = subparsers.add_parser("rescan")
    rescan_parser.add_argument("--local-path", type=Path, default=Path("."))

    return parser.parse_args()


def main(command: str, **kwargs: Any) -> None:
    commands: dict[str, Callable[..., None]] = {"rescan": rescan_command}

    commands[command](**kwargs)


def entry_point() -> None:
    warnings.filterwarnings("ignore", category=InsecureRequestWarning)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        main(**vars(parse_args()))
    except UserError as e:
        logging.error(f"error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error("Operation interrupted.")
        sys.exit(130)
