import html
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import UUID

from careerpilot.core import (
    ApplicationService,
    Database,
    SummaryVersion,
)


def markdown_text(value: Any) -> str:
    escaped = html.escape(str(value or ""), quote=False)
    return re.sub(r"([\\`*_\[\]])", r"\\\1", escaped)


class MarkdownRenderer:
    def __init__(self, database: Database, directory: Path) -> None:
        self.applications = ApplicationService(database)
        self.directory = directory

    def path(self, application_id: UUID) -> Path:
        return self.directory / f"{application_id}.md"

    def __call__(self, application_id: UUID, summary: SummaryVersion) -> str:
        application = self.applications.get(application_id)
        details = self.applications.details(application_id)
        content = summary.content
        lines = [
            f"# {markdown_text(application.company)} — {markdown_text(application.role)}",
            "",
            f"- Application ID: `{application_id}`",
            f"- Summary version: {summary.version}",
            f"- Generated at: {summary.created_at.isoformat()}",
            "",
            "## Application",
            "",
        ]
        lines.extend(
            f"- **{markdown_text(field)}:** {markdown_text(value)}"
            for field, value in application.values.items()
            if value not in (None, "")
        )
        lines.extend(["", "## Timeline", ""])
        lines.extend(
            f"- {markdown_text(item['created_at'])} — "
            f"{markdown_text(item['payload'].get('field', item['event_type']))}: "
            f"{markdown_text(item['payload'].get('value', ''))}"
            for item in details["timeline"]
        )
        if not details["timeline"]:
            lines.append("- No timeline evidence.")
        lines.extend(["", "## Mail evidence", ""])
        lines.extend(
            f"- {markdown_text(item['sent_at'] or 'time unknown')} — "
            f"{markdown_text(item['subject'])} ({markdown_text(item['sender'])})"
            for item in details["emails"]
        )
        if not details["emails"]:
            lines.append("- No linked mail evidence.")
        lines.extend(
            [
                "",
                "## Summary",
                "",
                markdown_text(content["overview"]),
            ]
        )
        for title, key in (
            ("JD highlights", "jd_highlights"),
            ("Process clues", "process_clues"),
            ("Written test", "written_test"),
            ("Interview", "interview"),
            ("Known facts", "known_facts"),
            ("Unknowns and uncertainty", "unknowns"),
        ):
            lines.extend(["", f"### {title}", ""])
            values = content.get(key, [])
            lines.extend(f"- {markdown_text(value)}" for value in values)
            if not values:
                lines.append("- None identified.")
        lines.extend(["", "## Sources", ""])
        for source in content["sources"]:
            lines.append(
                f"- [{markdown_text(source['title'])}]({source['url']})"
                f" — fetched {source['fetched_at']}"
            )
        text = "\n".join(lines).rstrip() + "\n"
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.path(application_id)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.directory, delete=False
        ) as temporary:
            temporary.write(text)
            temporary_path = Path(temporary.name)
        temporary_path.replace(target)
        return str(target)
