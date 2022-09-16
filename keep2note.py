#!/usr/bin/python3

import datetime
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

root_dir = "keep-data"
notes = os.listdir(root_dir)
access_token = os.getenv("NOTION_ACCESS_KEY")
database_id = os.getenv("NOTION_DATABASE_ID")


def PostNote(
    title,
    body: str | None,
    list_items: dict | None,
    tags: list,
    date_created,
    date_updated,
):
    body_json = {
        "parent": {
            "type": "database_id",
            "database_id": database_id,
        },
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]},
            "Created": {"date": {"start": date_created}},
            "Edited": {"date": {"start": date_updated}},
            "Tags": {"multi_select": tags},
        },
        "children": [],
    }

    if body:
        last_line = ""
        for line in body.splitlines():
            if line == "" and line == last_line:
                last_line = line
                continue

            body_json["children"].append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line,
                                },
                            }
                        ]
                    },
                }
            )

            last_line = line
    if list_items:
        for item in list_items:
            checked = item["isChecked"]
            text = item["text"]

            body_json["children"].append(
                {
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": text},
                            }
                        ],
                        "checked": checked,
                        "color": "default",
                    },
                }
            )

    print(f"Importing: {title}...", end="")

    res = requests.post(
        "https://api.notion.com/v1/pages",
        json=body_json,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
        },
    )

    if res.status_code == 200:
        print(f"✅")
        return True
    else:
        print(f"Error {res.status_code}: {res.content.decode()}")
        return False


def FindTags(data: dict) -> list | None:
    tags = []

    for key in data.keys():
        if key.startswith("is") and data[key] == True:
            name = key[2:]
            tags.append({"name": name.lower()})

    return tags


def ProcessJson(file: str, data: dict) -> bool:
    if "title" not in data:
        print(f"Error: No `title` in {file} (in this a valid Google Takeout json?)")
        return False
    title = data["title"]
    date_created = datetime.datetime.fromtimestamp(
        data["createdTimestampUsec"] / 1000000
    )
    date_updated = datetime.datetime.fromtimestamp(
        data["userEditedTimestampUsec"] / 1000000
    )
    tags = FindTags(data)

    body = None
    list_content = None

    if "textContent" in data:
        body = data["textContent"]

    if "listContent" in data:
        list_content = data["listContent"]

    if body == None and list_content == None:
        print(f"Error: No `textContent` or `listContent` in {file}")
        return False

    res = PostNote(
        title,
        body,
        list_content,
        tags,
        f"{date_created}",
        f"{date_updated}",
    )
    return res


success = 0
failed = 0

for file in notes:
    if file.endswith(".json") == False:
        continue
    path = os.path.join(root_dir, file)

    try:
        f = open(path, "r")
        json_str = f.read()

        data = json.loads(json_str)

        if ProcessJson(file, data):
            success += 1
        else:
            failed += 1
        # break

    finally:
        f.close()

print(f"Finished, {success} Success, {failed} Failed.")
