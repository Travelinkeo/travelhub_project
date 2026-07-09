#!/usr/bin/env python
"""
Compile .po files to .mo files without needing GNU gettext.
This is a standalone script that can run anywhere.
"""

import os
import struct


def generate_mo(input_file, output_file):
    """Convert .po file to .mo file."""
    messages = {}
    msgid = None
    msgstr = None
    in_msgid = False
    in_msgstr = False

    def clean_str(s):
        """Unescape standard PO string escape sequences."""
        return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')

    with open(input_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line.startswith("msgid "):
                if msgid is not None and msgstr is not None:
                    messages[clean_str(msgid)] = clean_str(msgstr)
                msgid = line[6:].strip('"')
                msgstr = None
                in_msgid = True
                in_msgstr = False
            elif line.startswith("msgstr "):
                msgstr = line[7:].strip('"')
                in_msgid = False
                in_msgstr = True
            elif line.startswith('"') and line.endswith('"'):
                content = line[1:-1]
                if in_msgid:
                    msgid += content
                elif in_msgstr:
                    msgstr += content

    if msgid is not None and msgstr is not None:
        messages[clean_str(msgid)] = clean_str(msgstr)

    # Keep the empty msgid (header) as it contains charset metadata (UTF-8)

    # Sort messages by msgid
    sorted_messages = sorted(messages.items())

    # Generate .mo file
    offsets = []
    ids = b""
    strs = b""

    for msgid, msgstr in sorted_messages:
        msgid_bytes = msgid.encode("utf-8")
        msgstr_bytes = msgstr.encode("utf-8")
        offsets.append((len(ids), len(msgid_bytes), len(strs), len(msgstr_bytes)))
        ids += msgid_bytes + b"\0"
        strs += msgstr_bytes + b"\0"

    # Header
    n = len(messages)
    start_of_original_strings = 7 * 4 + n * 8 + n * 8
    start_of_translation_strings = start_of_original_strings + len(ids)

    # Build the .mo file
    output = bytearray()

    # Magic number
    output += struct.pack("<I", 0x950412DE)
    # Version
    output += struct.pack("<I", 0)
    # Number of messages
    output += struct.pack("<I", n)
    # Offset of table of original strings
    output += struct.pack("<I", 7 * 4)
    # Offset of table of translation strings
    output += struct.pack("<I", 7 * 4 + n * 8)
    # Size of hashing table (0 = no hashing table)
    output += struct.pack("<I", 0)
    # Offset of hashing table (0 = no hashing table)
    output += struct.pack("<I", 0)

    # Table of original strings
    for msgid_offset_in_ids, msgid_len, _, _ in offsets:
        output += struct.pack("<I", msgid_len)
        output += struct.pack("<I", start_of_original_strings + msgid_offset_in_ids)

    # Table of translation strings
    for _, _, msgstr_offset_in_strs, msgstr_len in offsets:
        output += struct.pack("<I", msgstr_len)
        output += struct.pack("<I", start_of_translation_strings + msgstr_offset_in_strs)

    # Original strings
    output += ids

    # Translation strings
    output += strs

    with open(output_file, "wb") as f:
        f.write(output)

    return len(messages)


if __name__ == "__main__":
    # Use relative path to support host, builder, and runtime environments
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")

    for lang in ["es", "en"]:
        po_file = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
        mo_file = os.path.join(base_dir, lang, "LC_MESSAGES", "django.mo")

        if os.path.exists(po_file):
            count = generate_mo(po_file, mo_file)
            print(f"Compiled {po_file} -> {mo_file} ({count} messages)")
        else:
            print(f"File not found: {po_file}")
