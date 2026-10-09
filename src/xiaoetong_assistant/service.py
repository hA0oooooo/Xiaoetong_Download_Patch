"""Shared native-session catalog used by the interface and integration checks."""
from dataclasses import dataclass, field, replace


@dataclass
class VideoCatalog:
    resources: list = field(default_factory=list)
    course_rows: list = field(default_factory=list)

    @property
    def videos(self):
        return [item for item in self.resources if item.resource_type == 3]


def discover_videos(client, progress=lambda *_: None, cancelled=lambda: False, on_catalog=None):
    if not client.status().get("authenticated"):
        raise PermissionError("Native client login is required")
    courses = [course for page in client.course_pages() for course in page]
    result = VideoCatalog(course_rows=courses)
    def publish():
        if on_catalog:
            # The UI queue must not observe lists subsequently mutated by this worker.
            on_catalog(replace(result, resources=list(result.resources), course_rows=list(result.course_rows)))
    publish()
    for index, course in enumerate(courses, 1):
        if cancelled():
            return result
        progress(index, len(courses))
        if int(course.get("resource_type", 0)) != 50:
            publish()
            continue
        try:
            resources = client.resources(course)
        except (PermissionError, ValueError, RuntimeError):
            publish()
            continue
        for item in resources:
            if item.resource_type in (3, 51) and item.unlocked and not item.trial:
                result.resources.append(item)
        publish()
    return result


def selected_resources(table, resources, nodes=None):
    """Expand selected courses and deduplicate selected descendants in display order."""
    keys = set()
    def walk(node):
        if node in resources:
            keys.add(node)
        for child in table.get_children(node):
            walk(child)
    for node in table.selection() if nodes is None else nodes:
        walk(node)
    return [item for key, item in resources.items() if key in keys]
