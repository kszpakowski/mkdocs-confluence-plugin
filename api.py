import requests

session = requests.Session()
session.auth = ("admin", "admin")

space= "DOK"
title = "mkdocs3"
baseUrl = "http://localhost:8090/rest/api/content"

def get_page_id(page):
    print(f"Getting id for page: {page}")
    url = f"{baseUrl}?title={page}"
    r = session.get(url)
    r.raise_for_status()
    results = r.json()["results"]
    return results[0]["id"] if len(results) > 0 else None

def find_page_children(id):
    print("Searching children of page id {id}")
    url = f"{baseUrl}/search?cql=ancestor={id}"
    r = session.get(url)
    r.raise_for_status()
    return [ page["id"] for page in r.json()["results"]]

def find_space_children(id):
    print("Searching children of page id {id}")
    url = f"{baseUrl}/search?cql=space={id}"
    r = session.get(url)
    r.raise_for_status()
    return [ page["id"] for page in r.json()["results"]]

def delete_page(id):
    print(f"Deleting page id {id}")
    url = f"{baseUrl}/{id}"
    r = session.delete(url)
    r.raise_for_status()

def delete_from_trash(id):
    print(f"Deleting page id {id} from trash")
    url = f"{baseUrl}/{id}?status=trashed"
    r = session.delete(url)
    r.raise_for_status()


def create_page(space, title, parent=None):
    print(f"Creating page: {title} in space {space}. Parent: {parent}")
    url = f"{baseUrl}"
    body = {'title': title, 'type': 'page', 'space': {'key': space}, 'body': {'wiki': {
            'value': 'h1. Hello world!',
            'representation': 'wiki'
    }}}
    if parent:
        parent_page_id = get_page_id(parent)
        body["ancestors"] = [{"id": parent_page_id}]

    r = session.post(url, json=body)
    r.raise_for_status()
    return r.json()["id"]

def cleanup_space(space):
    children = find_space_children(space)
    print(children)
    for id in children:
        delete_page(id)
        delete_from_trash(id)

cleanup_space(space)
# id = create_page(space, title)
# print(id)

