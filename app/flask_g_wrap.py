from flask import g


def g_wrap(current, *args, **kwargs):
    event_info = kwargs.pop("event_info", None)
    if not getattr(g, "subjects"):
        g.subjects = []
    if event_info is None and len(g.subjects) > 0:
        event_info = g.subjects[0].event_info()
    subject = current(*args, event_info=event_info, **kwargs)
    g.subjects.append(subject)
    return subject
