from erd_agent.agent import generate

if __name__ == "__main__":
    # 예: python scripts/run_agent.py /path/to/repo
    import sys
    repo = sys.argv[1]
    generate(repo, out="database.dbml", use_aoai=False)