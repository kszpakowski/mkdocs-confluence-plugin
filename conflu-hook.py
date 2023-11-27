import logging
import requests
from md2cf.confluence_renderer import ConfluenceRenderer
import mistune
import types

log = logging.getLogger('mkdocs')

confluence_mistune = mistune.Markdown(renderer=ConfluenceRenderer(use_xhtml=True))

session = requests.Session()
session.auth = ("admin", "admin")

class Actions:
    CREATE_CONTENT = 'CREATE_CONTENT'
    UPDATE_CONTENT = 'UPDATE_CONTENT'
    DELETE_CONTENT = 'DELETE_CONTENT'

existing_pages=[]
plan = []

# Config
space= "DOK"
title = "mkdocs3"
baseUrl = "http://localhost:8090/rest/api/content"
dryRun = False


# plugin handlers

def on_nav(nav, config, files):
    for n in nav:
        handleNav(n)
   
def on_page_markdown(markdown,page,config,files):
    content = confluence_mistune(markdown)
    upsert_page(space, page.title, content, page.parent.title if page.parent else None)
    return markdown

def on_post_build(config):
    pages_in_conflu = find_space_children(space)
    pages_to_remove = [ page for page in pages_in_conflu if page["id"] not in existing_pages ]
    for page in pages_to_remove:
        plan.append({'action': Actions.DELETE_CONTENT, 'space': space, 'page':page})

    executePlan()

# ...

def handleNav(nav):
    if nav.is_section:
        handleSection(nav)

def handleSection(s):
    upsert_section(space, s.title,s.parent.title if s.parent else None)
    for n in s.children:
        handleNav(n)


def executePlan():
    for action in plan:
        match action["action"]:
            case Actions.CREATE_CONTENT:
                print(f'Create: {action["title"]} with parent {action["parent"]}')
                if not dryRun:
                    create_content(action["space"], action["title"], action["body"], action["parent"])
            case Actions.UPDATE_CONTENT:
                print(f'Update: {action["page"]["title"]} with parent {action["parent"]}')
                if not dryRun:
                    update_content(action["space"], action["page"], action["body"], action["parent"])
            case Actions.DELETE_CONTENT:
                print(f'Delete: {action["page"]["title"]}')
                if not dryRun:
                    delete_page(action["page"]["id"])


# Conflu api


# find page by it's title
def get_page(title):
    url = f"{baseUrl}?title={title}&expand=version,ancestors"
    r = session.get(url)
    r.raise_for_status()
    results = r.json()["results"]

    if(len(results) <= 0):
        return None

    page = {
        'id': results[0]['id'],
        'version': results[0]['version']['number'],
        'ancestor': next(iter(results[0]['ancestors']), None),
        'title': results[0]['title']
    }
    return page

# Create page or space
def create_content(space, title, body, parent):
    url = f"{baseUrl}"
    json = {'title': title, 
            'type': 'page',
            'space': {'key': space},
            'body': body
            }
    if parent:
        parent_page_id = get_page(parent)["id"]
        json["ancestors"] = [{"id": parent_page_id}]

    r = session.post(url, json=json)
    r.raise_for_status()
    id = r.json()["id"]
    return id

# Update page or space
def update_content(space, page, body, parent):
    url = f"{baseUrl}/{page['id']}"

    json = {
        "id": int(page['id']),
        "status": "current",
        "title": page['title'],
        "type": "page",
        "body":body,
        'space': {'key': space},
        "version": {
            "number": page['version'] + 1
        }
    }

    # TODO this should move page to the collection root if parent is empty
    if parent:
        parent_page_id = get_page(parent)["id"]
        json["ancestors"] = [{"id": parent_page_id}]

    r = session.put(url, json=json)
    r.raise_for_status()
    id = r.json()["id"]
    return id

def upsert_page(space, title, html, parent=None):
    body = {
                'storage': {
                    'value': html,
                    'representation': 'storage'
                }
            }

    page = get_page(title)
    if page:
        existing_pages.append(page["id"])
        plan.append({'action': Actions.UPDATE_CONTENT, 'space': space, 'page':page, 'body':body, 'parent':parent})
    else:
        plan.append({'action': Actions.CREATE_CONTENT, 'space': space, 'title':title, 'body':body, 'parent':parent})


def upsert_section(space, title, parent=None):
    body = { 'wiki': {
                'value': '{pageTree:root=@self}',
                'representation': 'wiki'
                }
            }
    section = get_page(title)
    if section:
        existing_pages.append(section["id"])
        plan.append({'action': Actions.UPDATE_CONTENT, 'space': space, 'page':section, 'body':body, 'parent':parent})
    else:
        plan.append({'action': Actions.CREATE_CONTENT, 'space': space, 'title':title, 'body':body, 'parent':parent})
    
def find_space_children(id):
    # print(f"Searching children of page id {id}")
    url = f"{baseUrl}/search?cql=space={id}"
    r = session.get(url)
    r.raise_for_status()
    return r.json()["results"]

def delete_page(id):
    # print(f"Deleting page id {id}")
    url = f"{baseUrl}/{id}"
    r = session.delete(url)
    r.raise_for_status()


## TODO add validation if all pages and sections have unique titles
## TODO add opt in unique title postprocessor




