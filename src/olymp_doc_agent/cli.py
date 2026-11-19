import argparse
import json
import sys

from .agent import EditAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Precisely edit a .docx document")
    parser.add_argument("input", help="Input .docx file")
    parser.add_argument("instruction", help="Natural-language editing instruction")
    parser.add_argument("output", help="Output .docx file")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the limited quoted-command parser instead of an AI model",
    )
    parser.add_argument("--json", action="store_true", help="Print the result as JSON")
    args = parser.parse_args()

    try:
        result = EditAgent(offline=args.offline).run(
            args.input, args.instruction, args.output
        )
        if result["error"]:
            if args.json:
                print(json.dumps({"ok": False, "error": result["error"]}))
            else:
                print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"ok": True, "output": args.output, "result": result}, default=str))
        else:
            print(f"Created {args.output}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
