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
    for command in (initialize_cmd, update):
        command.add_argument("--frontend", action="store_true", help="启用通用 Web 界面审查 Skill")
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
    compare_cmd.add_argument("--require-review", action="store_true", help="候选还须逐题业务与正文复核通过")
    review_cmd = sub.add_parser("review", help="查看运行复核状态或追加一条已有裁定")
    review_cmd.add_argument("run", type=Path)
    review_cmd.add_argument("--record", type=Path, help="来自实际复核的单用例 JSON")
    args = parser.parse_args()
    root = args.project.resolve()
    if args.command == "init":
        print(initialize(args.destination, bool(args.example), frontend=args.frontend))
        return 0
    if args.command == "upgrade":
        print(upgrade(args.source, args.destination, frontend=args.frontend))
        return 0
    if args.command == "review":
        from .review import show
        show(args.run, args.record)
        return 0
    if args.command == "compare":
        from .evaluation import compare
        return 0 if compare(args.baseline, args.candidate, require_review=args.require_review) else 1
    if not (root / "business/system.md").is_file():
        raise ValueError("请先 init 一个业务项目，或通过 --project 指定业务目录")
    if args.command == "doctor":
        from .runtime import inspect_business_skills
        skills, skipped = inspect_business_skills(root)
        registry = extension(root / "business/tools.py").TOOLS
        print(json.dumps({"foundry": __version__, "python": sys.version.split()[0],
            "deepagents": version("deepagents"), "tools": [getattr(t, "name", None) or t.__name__ for t in registry],
            "skills": skills, "skipped_skills": skipped,
            "model_configured": bool(os.getenv("FOUNDRY_MODEL") and os.getenv("OPENAI_API_KEY")),
            "lock": (ROOT / "uv.lock").exists()}, ensure_ascii=False, indent=2))
        return 2 if skipped else 0
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
    print("自动检查已结束，使用 foundry review 查看业务与正文复核状态。")
    print(folder)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        sys.exit(str(exc))
