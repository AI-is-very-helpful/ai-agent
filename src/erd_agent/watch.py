from __future__ import annotations
from pathlib import Path
import time
import typer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from erd_agent.agent import generate

app = typer.Typer(add_completion=False)

class Handler(FileSystemEventHandler):
    def __init__(self, repo: str, out_dbml: str, out_md: str, use_aoai: bool):
        self.repo = repo
        self.out_dbml = out_dbml
        self.out_md = out_md
        self.use_aoai = use_aoai
        self._last = 0.0

    def on_any_event(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() != ".java":
            return

        # 너무 잦은 재실행 방지(간단 debounce)
        now = time.time()
        if now - self._last < 0.8:
            return
        self._last = now

        generate(self.repo, out_dbml=self.out_dbml, out_md=self.out_md, use_aoai=self.use_aoai)

@app.command()
def watch(
    repo: str,
    out_dbml: str = "database.dbml",
    out_md: str = "erd_summary.md",
    use_aoai: bool = False,
):
    repo_path = Path(repo).expanduser()
    if not repo_path.exists():
        # URL일 수도 있으니 generate가 알아서 처리하게 하고,
        # watcher는 로컬 경로에만 의미가 있으므로 URL은 Stage3에서는 로컬 clone 경로로 사용 권장
        raise typer.BadParameter("watch는 로컬 경로에서 사용하세요. (URL은 generate로 먼저 clone 후 경로를 watch)")

    handler = Handler(repo, out_dbml, out_md, use_aoai)
    obs = Observer()
    obs.schedule(handler, str(repo_path), recursive=True)
    obs.start()
    try:
        while True:
            time.sleep(1)
    finally:
        obs.stop()
        obs.join()
``