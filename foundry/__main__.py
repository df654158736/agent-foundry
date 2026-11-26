import argparse
import json
import os
import sys
from importlib.metadata import version
from pathlib import Path

from . import __version__
from .project import ROOT, extension, initialize, upgrade


def main():
    parser = argparse.ArgumentParser(prog="python -m foundry")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="独立业务项目目录")
    sub = parser.add_subparsers(dest="command", required=True)
    initialize_cmd = sub.add_parser("init")
    initialize_cmd.add_argument("destination", type=Path)
    initialize_cmd.add_argument("--example", choices=["dispatch"])
    update = sub.add_parser("upgrade")
    update.add_argument("source", type=Path)
    update.add_argument("destination", type=Path)
    sub.add_parser("doctor")
    chat = sub.add_parser("chat")
    chat.add_argument("prompt", nargs="?")
    evaluate = sub.add_parser("eval")
    evaluate.add_argument("--fixture", action="store_true")
    evaluate.add_argument("--case")
    evaluate.add_argument("--out", type=Path)
    compare_cmd = sub.add_parser("compare")
    compare_cmd.add_argument("baseline", type=Path)
    compare_cmd.add_argument("candidate", type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    if args.command == "init":
        print(initialize(args.destination, bool(args.example)))
        return 0
    if args.command == "upgrade":
        print(upgrade(args.source, args.destination))
        return 0
    if args.command == "compare":
        from .evaluation import compare
        return 0 if compare(args.baseline, args.candidate) else 1
    if not (root / "business/system.md").is_file():
        raise ValueError("请先 init 一个业务项目，或通过 --project 指定业务目录")
    if args.command == "doctor":
        registry = extension(root / "business/tools.py").TOOLS
        print(json.dumps({"foundry": __version__, "python": sys.version.split()[0],
            "deepagents": version("deepagents"), "tools": [getattr(t, "name", None) or t.__name__ for t in registry],
            "skills": sorted(p.parent.name for p in (root / "business/skills").glob("*/SKILL.md")),
            "model_configured": bool(os.getenv("FOUNDRY_MODEL") and os.getenv("OPENAI_API_KEY")),
            "lock": (ROOT / "uv.lock").exists()}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "chat":
        from .runtime import Session, live_model
        session = Session(root, live_model())
        if args.prompt:
            print(session.ask(args.prompt))
        else:
            while True:
                try:
                    question = input("> ").strip()
                except EOFError:
                    break
                if question == "/quit":
                    break
                if question:
                    print(session.ask(question))
        return 0
    from .evaluation import run
    folder, ok = run(root, args.fixture, args.case, args.out)
    print(folder)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        sys.exit(str(exc))
