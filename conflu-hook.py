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

def get_page_id(page):
    print(f"Getting id for page: {page}")
    url = f"{baseUrl}?title={page}"
    r = session.get(url)
    r.raise_for_status()
    results = r.json()["results"]
    return results[0]["id"] if len(results) > 0 else None

def create_content(space, title, body, parent):
    print(f"Creating content: {title} in space {space}. Parent: {parent}")
    url = f"{baseUrl}"
    json = {'title': title, 
            'type': 'page',
            'space': {'key': space},
            'body': body
            }
    if parent:
        parent_page_id = get_page_id(parent)
        json["ancestors"] = [{"id": parent_page_id}]

    r = session.post(url, json=json)
    r.raise_for_status()
    return r.json()["id"]

## TODO pass page content as html
def create_page(space, title, html, parent=None):
    print(f"Creating page: {title} in space {space}. Parent: {parent}")
    body =  {
                'storage': {
                    'value': html,
                    'representation': 'storage'
                    }
                }
    return create_content(space, title, body, parent)


def create_section(space, title, parent=None):
    print(f"Creating section: {title} in space {space}. Parent: {parent}")
    
    body = {
                'wiki': {
                    'value': '{pageTree:root=@self}',
                    'representation': 'wiki'
                    }
                }
    return create_content(space, title, body, parent)


## TODO add validation if all pages and sections have unique titles
## TODO add opt in unique title postprocessor

def on_nav(nav, config, files):
    print('--on nav')
    for n in nav:
        handleNav(n)
   
def on_page_markdown(markdown,page,config,files):
    print("--on_page_markdown")
    content = confluence_mistune(markdown)
    create_page(space, page.title, content, page.parent.title if page.parent else None)
    return markdown


def handleNav(nav):
    if nav.is_section:
        handleSection(nav)

def handleSection(s):
    print(f'Section title: {s.title}{ f", parent: {s.parent.title}" if s.parent else ""}')
    create_section(space, s.title,s.parent.title if s.parent else None)
    for n in s.children:
        handleNav(n)
