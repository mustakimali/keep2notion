# Google Keep to Notion

## How to use

* Take a [Google Takeout](https://takeout.google.com/) for Google Keep notes.
* Extract the zip file to a temporary location
* Copy all files from `Takeout/Keep` into the folder `keep-data` next to `keep2note.py`
* Rename `.env.sample` -> `.env` and populate the value
  * [Create an internal integration](https://developers.notion.com/docs/getting-started#step-1-create-an-integration) and populate the `NOTION_ACCESS_KEY` with the Internal Integration Token.
  * Create a Database and add this integration using the `Add Connection` option by [following the steps here](https://developers.notion.com/docs/getting-started#step-1-create-an-integration). Then copy paste the URL of the ID of the database.
  * For example: If the address is `https://www.notion.so/your_user_name/9e7f1e7b40cb4121a158846c5b93009d?v=93b29b811eac4775ae41a2e179bfded2` then the ID is `9e7f1e7b40cb4121a158846c5b93009d`

* Install required dependencies using pip3: `pip3 install -r requirements.txt`
* Run the script `./keep2note.py`

## Supported notes
- [x] Plain text notes
- [x] To Do Items
- [x] Label Archived and Deleted notes
- [ ] Handle links well
- [ ] Handle large notes (with > 100 lines)
- [ ] Handle large paragraph (with > 2000 characters)