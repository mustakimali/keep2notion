#!/usr/bin/python3

import datetime
import json
import os
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

root_dir = "keep-data"
notes = os.listdir(root_dir)
access_token = os.getenv("NOTION_ACCESS_KEY")
database_id = os.getenv("NOTION_DATABASE_ID")
image_server_url = os.getenv("IMAGE_SERVER_URL")


def PostNote(
    title,
    body: str | None,
    list_items: dict | None,
    tags: list,
    attachments: list,
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
        },
        "children": [],
    }

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

    if attachments:
        tag_added_image = False
        tag_added_migration_error = False

        for item in attachments:
            file_path = os.path.join(root_dir, item["filePath"])
            if os.path.exists(file_path) is False:
                print(f"Invalid file {file_path}")

                if body:
                    body += f"\nMigration Error: Invalid attachment file {file_path}"

                if tag_added_migration_error == False:
                    tags.append({"name": "migration_error"})
                    tag_added_migration_error = True
                continue
            elif body:
                body += f"\nMigration: Attachment file: {file_path}"

            if image_server_url == "":
                continue

            f = open(file_path, "rb")

            try:
                id = uuid.uuid4()
                ext = file_path[-3:]
                url = f"{image_server_url}{id}.{ext}"
                print(f"[{title}]: Uploading: {url}")

                res = requests.post(url, files={"file": f.read()})
                if res.status_code != 202:
                    err = f"Error posting image {file_path} to {url}\n{res.content.decode()}"
                    print(err)
                    if body:
                        body += f"\nMigration Error: {err}"

                    if tag_added_migration_error == False:
                        tags.append({"name": "migration_error"})
                        tag_added_migration_error = True
                    return False

                body_json["children"].append(
                    {
                        "type": "image",
                        "image": {"type": "external", "external": {"url": url}},
                    }
                )
                if tag_added_image == False:
                    tags.append({"name": "image"})
                    tag_added_image = True
            finally:
                f.close()

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

    body_json["properties"]["Tags"] = {"multi_select": tags}

    res = requests.post(
        "https://api.notion.com/v1/pages",
        json=body_json,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
        },
    )

    if res.status_code == 200:
        return True
    else:
        print(f"[{title}] Error {res.status_code}: {res.content.decode()}")
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
    attachments = None

    if "textContent" in data:
        body = data["textContent"]

    if "listContent" in data:
        list_content = data["listContent"]

    if "attachments" in data:
        attachments = data["attachments"]

    if body == None and list_content == None and attachments == None:
        print(f"Error: No `textContent`, `listContent` or `attachments` in {file}")
        return False

    res = PostNote(
        title,
        body,
        list_content,
        tags,
        attachments,
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
