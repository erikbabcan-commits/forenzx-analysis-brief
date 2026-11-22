"""Render one bundled ForenZX synthetic demo. Default output is UTF-8 Markdown on stdout."""
import os
from pathlib import Path
import stat
import sys
import tempfile

if __package__:
    from . import render_brief as brief
else:
    import render_brief as brief


def _read_fixture(scenario):
    path = brief.PRODUCT / "fixtures" / (scenario + ".json")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise brief.BriefError("INVALID_FIXTURE_FILE")
        return brief.validator.read_bounded(source, brief.validator.Limits().max_bytes)


def _publish(path, document):
    # A same-directory hard link publishes complete bytes and refuses even dangling symlinks.
    with tempfile.NamedTemporaryFile(dir=path.parent) as pending:
        pending.write(document)
        pending.flush()
        os.fsync(pending.fileno())
        os.link(pending.name, path)


def main(argv=None):
    parser = brief.validator.SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("scenario", choices=brief.SCENARIOS)
    parser.add_argument("--output", type=Path, help="Create a new Markdown file")
    try:
        args = parser.parse_args(argv)
        document = brief.render_demo(args.scenario, _read_fixture(args.scenario))
        if args.output is None:
            sys.stdout.buffer.write(document)
            sys.stdout.buffer.flush()
        else:
            _publish(args.output, document)
        return 0
    except brief.BriefError as exc:
        code = str(exc)
    except brief.validator.CLIError:
        code = "INVALID_ARGUMENTS"
    except FileExistsError:
        code = "OUTPUT_EXISTS"
    except (OSError, ValueError, KeyError, TypeError):
        code = "DEMO_IO_OR_CONFIGURATION_ERROR"
    print(f"Prehľad nevytvorený ({code}).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
