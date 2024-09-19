import requests
import json
import os

# function to send orders requests to a Notion Table, was planning to merge with general order tracker

def post_order_tracker(request_dict):
    if (request_dict["quantity"].isnumeric() == False) or (int(request_dict["quantity"]) < 1) :
        return 404
    else :
      url = "https://api.notion.com/v1/pages"
      # database ID can be found in the URL of the table to send payload to
      database_id = os.environ["NOTION_DB"]

      # API key can be found in the connections settings of Notion (here we use the "Neoventory" connection)
      # /!\ dont forget to add the connection to the table or else this will fail miserably
      headers = {
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
        'Authorization': os.environ["NOTION_SECRET"],
      }
  
      payload = json.dumps({
        "parent": {
          "database_id": database_id
        },
        "properties": {
          "Name": {
            "title": [
              {
                "text": {
                  "content": request_dict["name"]
                }
              }
            ]
          },
          "Supplier": {
            "rich_text": [
              {
                "text": {
                  "content": request_dict["supplier"]
                }
              }
            ]
          },
          "Reference": {
            "rich_text": [
              {
                "text": {
                  "content": request_dict["ref"]
                }
              }
            ]
          },
          "Quantity": {
            "number": int(request_dict["quantity"])
          }
        }
      })
  
      response = requests.request("POST", url, headers=headers, data=payload)
  
      #print(response.content, file=sys.stderr)
  
      return response.status_code
