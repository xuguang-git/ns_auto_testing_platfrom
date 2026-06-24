from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


@dataclass
class CleanupItem:
    """记录本次清理命中的文件或目录。"""

    path: Path
    size: int
    kind: str


class Command(BaseCommand):
    help = "清理过期运行日志和性能测试结果目录，默认只预览不删除。"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=15, help="清理超过多少天的文件或目录，默认 15 天。")
        parser.add_argument("--no-dry-run", action="store_true", help="真正执行删除；不加时只预览。")
        parser.add_argument("--include-perf-results", action="store_true", help="同时清理过期性能测试结果目录。")

    def handle(self, *args, **options):
        days = options["days"]
        if days <= 0:
            raise CommandError("--days 必须大于 0。")

        cutoff = timezone.now() - timedelta(days=days)
        dry_run = not options["no_dry_run"]
        items = self.collect_runtime_logs(cutoff)
        if options["include_perf_results"]:
            items.extend(self.collect_perf_results(cutoff))

        total_size = sum(item.size for item in items)
        for item in items:
            action = "预览" if dry_run else "删除"
            self.stdout.write(f"{action} {item.kind}: {item.path} ({item.size} bytes)")
            if not dry_run:
                self.delete_path(item.path)

        mode = "预览完成" if dry_run else "清理完成"
        self.stdout.write(self.style.SUCCESS(f"{mode}：命中 {len(items)} 项，合计 {total_size} bytes。"))

    def collect_runtime_logs(self, cutoff) -> list[CleanupItem]:
        """收集项目后端目录下可安全清理的运行日志文件。"""

        patterns = ("*.log", "*.out", "*.err", "*.out.log", "*.err.log")
        items: list[CleanupItem] = []
        for pattern in patterns:
            for path in settings.BASE_DIR.glob(pattern):
                if not path.is_file() or not self.is_expired(path, cutoff):
                    continue
                if path.name.startswith("celerybeat-schedule"):
                    continue
                items.append(CleanupItem(path=path, size=path.stat().st_size, kind="运行日志"))
        return self.deduplicate(items)

    def collect_perf_results(self, cutoff) -> list[CleanupItem]:
        """收集过期的性能测试结果目录或文件。"""

        root = Path(getattr(settings, "PERF_RESULT_DIR", settings.BASE_DIR / "perf_results"))
        if not root.exists():
            return []
        items: list[CleanupItem] = []
        for path in root.iterdir():
            if not self.is_expired(path, cutoff):
                continue
            items.append(CleanupItem(path=path, size=self.path_size(path), kind="性能结果"))
        return items

    def is_expired(self, path: Path, cutoff) -> bool:
        modified_at = timezone.datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.get_current_timezone())
        return modified_at < cutoff

    def path_size(self, path: Path) -> int:
        if path.is_file():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

    def delete_path(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
            return
        path.unlink(missing_ok=True)

    def deduplicate(self, items: list[CleanupItem]) -> list[CleanupItem]:
        seen = set()
        result = []
        for item in items:
            key = str(item.path.resolve())
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result
