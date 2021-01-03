# -*- coding: utf-8 -*-
# Copyright 2020-2021 Lovac42
# Copyright 2019-2020 Nickolay <kelciour@gmail.com>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# Note: The original file for 2.0 was missing the license. However, under the 2019 terms of agreement, any addon uploaded to AnkiWeb without a license must be under AGPL. This file was taken from AnkiWeb and ported to CCBC.


import re
from aqt import mw
from anki.hooks import wrap, addHook, runHook
from aqt.editor import Editor
from aqt.reviewer import Reviewer


config = {
  "tag": "div",
  "undo": True
}


UNSAFE_TYPES = {
    "soundReg": re.compile(r"\[sound:(.+?)\]"),
    "clozeReg": re.compile(r"\<span class\=cloze\>"),

    # untested:
    "mathJaxReg": re.compile(r"(?si)(\\[\[\(])(.*?)(\\[\]\)])"),
    "latexStandard": re.compile(r"\[latex\](.+?)\[/latex\]", re.DOTALL | re.IGNORECASE),
    "latexExpression": re.compile(r"\[\$\](.+?)\[/\$\]", re.DOTALL | re.IGNORECASE),
    "latexMath": re.compile(r"\[\$\$\](.+?)\[/\$\$\]", re.DOTALL | re.IGNORECASE),
}


def editField(text, extra, context, field, fullname):
    if any(r.search(text) for r in UNSAFE_TYPES.values()):
        return text

    tag = config['tag']

    spanjs = "" if tag != "span" else """\
$("[contenteditable=true][data-field='%s']").keydown(function(evt) {
    if (evt.keyCode == 8){evt.stopPropagation();}
});""" % field

    return """\
<%s contenteditable="true" data-field="%s">%s</%s>
<script>
$("[contenteditable=true][data-field='%s']").blur(function() {
  py.link("edit_field_off:" + $(this).data("field") + "#" + $(this).html());
});
$("[contenteditable=true][data-field='%s']").focus(function() {
  py.link("edit_field_on:");
});
%s
</script>
""" % (
    tag, field, text, tag,
    field, field, spanjs
)

addHook('fmod_edit', editField) #filter hook



def saveField(note, fld, val):
    TAG_FIELD = True if fld == "Tags" else False

    if TAG_FIELD:
        old_data = note.tags
        t = mw.col.tags.split(val)
        new_data = mw.col.tags.canonify(t)
    else:
        old_data = note[fld]

        # https://github.com/dae/anki/blob/47eab46f05c8cc169393c785f4c3f49cf1d7cca8/aqt/editor.py#L257-L263
        editor = object.__new__(Editor)
        txt = editor._filterHTML(val, localize=False)
        txt = txt.replace("\x00", "")
        new_data = mw.col.media.escapeImages(txt, unescape=True)

    if old_data != new_data:
        if config['undo']:
            mw.checkpoint("Edited Field")
        if TAG_FIELD:
            note.tags = new_data
        else:
            note[fld] = new_data
        note.flush()



def linkHandler(rev, url, _old):
    if url.startswith("edit_field"):
        (cmd, arg) = url.split(":", 1)
        if cmd == "edit_field_off":
            # runHook("edit_field", False)

            fld, val = arg.split("#", 1)
            note = rev.card.note()
            saveField(note, fld, val)
            rev.card.q(reload=True)
        else:
            runHook("edit_field", True)

            # For speed focus, to stop the timer.
            mw.reviewer.bottom.web.eval("""\
if (typeof autoAnswerTimeout !== 'undefined') {
    clearTimeout(autoAnswerTimeout);
}
if (typeof autoAlertTimeout !== 'undefined') {
    clearTimeout(autoAlertTimeout);
}
if (typeof autoAgainTimeout !== 'undefined') {
    clearTimeout(autoAgainTimeout);
}
""")

        return
    return _old(rev, url)


Reviewer._linkHandler = wrap(
    Reviewer._linkHandler, linkHandler, "around"
)
