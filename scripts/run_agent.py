from erd_agent.commands.erd import run_erd

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/run_agent.py <repo-path-or-git-url> [--ai-first]")
        sys.exit(1)

    repo = sys.argv[1]
    ai_first = "--ai-first" in sys.argv

    run_erd(
        repo,
        out_dbml="database.dbml",
        out_md="erd_summary.md",
        use_aoai=False,
        ai_first=ai_first,
    )