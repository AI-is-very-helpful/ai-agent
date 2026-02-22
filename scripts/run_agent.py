from erd_agent.agent import generate

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/run_agent.py <repo-path-or-git-url>")
        sys.exit(1)

    repo = sys.argv[1]

    generate(
        repo,
        out_dbml="database.dbml",
        out_md="erd_summary.md",
        use_aoai=False,
    )