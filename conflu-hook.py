import logging
import requests
from md2cf.confluence_renderer import ConfluenceRenderer
import mistune

log = logging.getLogger('mkdocs')

session = requests.Session()
session.auth = ("admin", "admin")

space= "DOK"
title = "mkdocs3"
baseUrl = "http://localhost:8090/rest/api/content"

confluence_mistune = mistune.Markdown(renderer=ConfluenceRenderer(use_xhtml=True))

existing_pages=[]

# plugin handlers

def on_nav(nav, config, files):
    print('--on nav')
    for n in nav:
        handleNav(n)
   
def on_page_markdown(markdown,page,config,files):
    print("--on_page_markdown")
    content = confluence_mistune(markdown)
    upsert_page(space, page.title, content, page.parent.title if page.parent else None)
    return markdown

def on_post_build(config):
    pages_in_conflu = find_space_children(space)
    pages_to_remove = [ page for page in pages_in_conflu if page not in existing_pages ]
    for page in pages_to_remove:
        delete_page(page)
    

# ...

def handleNav(nav):
    if nav.is_section:
        handleSection(nav)

def handleSection(s):
    print(f'Section title: {s.title}{ f", parent: {s.parent.title}" if s.parent else ""}')
    create_or_update_section(space, s.title,s.parent.title if s.parent else None)
    for n in s.children:
        handleNav(n)

# Conflu api


# find page by it's title
def get_page(title):
    print(f"Getting id for page: {title}")
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
    print(f"Creating content: {title} in space {space}. Parent: {parent}")
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
    existing_pages.append(id)
    return id

# Update page or space
def update_content(space, page, body, parent):
    print(f"Updating content: {page['title']} in space {space}. Parent: {parent}")
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

    if parent:
        parent_page_id = get_page(parent)["id"]
        json["ancestors"] = [{"id": parent_page_id}]

    r = session.put(url, json=json)
    r.raise_for_status()
    id = r.json()["id"]
    existing_pages.append(id)
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
        print(f'Page {title} already exists')
        update_content(space,page,body,parent)
    else:
        return create_content(space, title, body, parent)


def create_or_update_section(space, title, parent=None):
    body = { 'wiki': {
                'value': '{pageTree:root=@self}',
                'representation': 'wiki'
                }
            }
    section = get_page(title)
    if section:
        print(f'Section {title} already exists with id {section["id"]}')
        update_content(space, section, body, parent)
    else:
        return create_content(space, title, body, parent)
    
def find_space_children(id):
    print(f"Searching children of page id {id}")
    url = f"{baseUrl}/search?cql=space={id}"
    r = session.get(url)
    r.raise_for_status()
    return [ page["id"] for page in r.json()["results"]]

def delete_page(id):
    print(f"Deleting page id {id}")
    url = f"{baseUrl}/{id}"
    r = session.delete(url)
    r.raise_for_status()


## TODO add validation if all pages and sections have unique titles
## TODO add opt in unique title postprocessor




