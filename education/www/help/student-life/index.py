import re
from html import escape
from urllib.parse import parse_qs, quote, unquote, urlparse

import frappe
from frappe import _

no_cache = 1

WIKI_SPACE_ROUTE = "Std-1-to-10"
DEFAULT_SOURCE_ROUTE = "Std-1-to-10/what-to-send-with-the-child"
FILE_ORIGIN = "https://erp.walnutedu.in"


def get_context(context):
	context.no_cache = 1
	context.title = _("Student Life Help")
	context.parents = [{"name": _("Home"), "route": "/"}]
	context.show_sidebar = False
	context.app_mode = is_app_mode()
	context.app_query = "&app=1" if context.app_mode else "&app=0"
	context.menu_page_href = "/help/student-life/menu?app={}".format(1 if context.app_mode else 0)

	context.menu_tree = get_wiki_menu_tree()
	valid_routes = collect_menu_routes(context.menu_tree)
	context.selected_source_route = get_selected_source_route(valid_routes)
	mark_active_menu(context.menu_tree, context.selected_source_route)
	context.menu_label = get_active_top_label(context.menu_tree) or _("Student life")

	context.article = get_wiki_article(context.selected_source_route)
	context.article_html = render_wiki_content(context.article.get("content") or "")
	return context


def get_wiki_menu_tree():
	menu_tree = get_wiki_sidebar_menu_tree()
	if not menu_tree:
		return fallback_menu_tree()
	return menu_tree


def get_wiki_sidebar_menu_tree():
	"""Build the help menu from the existing Wiki Space sidebar.

	This keeps maintenance in the normal Wiki sidebar/pages instead of a giant
	secondary markdown index page.
	"""
	try:
		space_name = frappe.db.get_value("Wiki Space", {"route": WIKI_SPACE_ROUTE}, "name")
		if not space_name:
			return []

		space = frappe.get_doc("Wiki Space", space_name)
		items = [item for item in (space.get("wiki_sidebars") or []) if not item.get("hide_on_sidebar")]
		page_names = [item.get("wiki_page") for item in items if item.get("wiki_page")]
		if not page_names:
			return []

		pages = frappe.get_all(
			"Wiki Page",
			filters={"name": ["in", page_names], "published": 1, "allow_guest": 1},
			fields=["name", "title", "route"],
			limit_page_length=2000,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Student Life Help: Wiki sidebar menu lookup failed")
		return []

	pages_by_name = {page.name: page for page in pages if page.get("route")}
	roots = []
	groups = {}

	for item in items:
		page = pages_by_name.get(item.get("wiki_page"))
		if not page:
			continue

		group_label = (item.get("parent_label") or _("Student life")).strip()
		if group_label not in groups:
			group = {"label": group_label, "route": "", "href": "", "children": [], "active": False, "open": False}
			groups[group_label] = group
			roots.append(group)

		route = normalize_route(page.get("route"))
		if not route.startswith("{}/".format(WIKI_SPACE_ROUTE)):
			continue

		groups[group_label]["children"].append(
			{
				"label": page.get("title") or route,
				"route": route,
				"href": make_help_href(route),
				"children": [],
				"active": False,
				"open": False,
			}
		)

	return [group for group in roots if group.get("children")]


def parse_markdown_menu(content):
	"""Parse an indented markdown bullet list into an N-level menu tree."""
	roots = []
	stack = []

	for raw_line in (content or "").splitlines():
		if not raw_line.strip():
			continue

		match = re.match(r"^(\s*)-\s+(.+?)\s*$", raw_line.expandtabs(2))
		if not match:
			continue

		indent, body = match.groups()
		level = len(indent) // 2
		node = parse_menu_line(body)

		while stack and stack[-1][0] >= level:
			stack.pop()

		if stack:
			stack[-1][1]["children"].append(node)
		else:
			roots.append(node)

		stack.append((level, node))

	return roots


def parse_menu_line(body):
	link = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", body.strip())
	if link:
		label, route = link.groups()
		route = normalize_route(route)
		return {
			"label": label.strip(),
			"route": route,
			"href": make_help_href(route),
			"children": [],
			"active": False,
			"open": False,
		}

	return {"label": body.strip(), "route": "", "href": "", "children": [], "active": False, "open": False}


def normalize_route(route):
	route = (route or "").strip()
	parsed = urlparse(route)
	if parsed.path.strip("/") == "help/student-life":
		source = parse_qs(parsed.query).get("source", [""])[0]
		return unquote(source).strip().lstrip("/")

	return unquote(route).strip().lstrip("/")


def is_app_mode():
	return str(frappe.form_dict.get("app") or "0").strip().lower() in ("1", "true", "yes")


def make_help_href(route, app_mode=None):
	if app_mode is None:
		app_mode = is_app_mode()

	href = "/help/student-life?source={}".format(quote(normalize_route(route), safe=""))
	return "{}&app={}".format(href, 1 if app_mode else 0)


def collect_menu_routes(menu_tree):
	routes = []

	def walk(nodes):
		for node in nodes:
			if node.get("route"):
				routes.append(node.get("route"))
			walk(node.get("children") or [])

	walk(menu_tree or [])
	return routes


def get_selected_source_route(valid_routes):
	valid_routes = valid_routes or []
	requested = normalize_route(frappe.form_dict.get("source"))

	if requested in valid_routes:
		return requested
	if DEFAULT_SOURCE_ROUTE in valid_routes:
		return DEFAULT_SOURCE_ROUTE
	return valid_routes[0] if valid_routes else DEFAULT_SOURCE_ROUTE


def mark_active_menu(menu_tree, selected_route):
	def walk(nodes):
		matched = False
		for node in nodes:
			child_matched = walk(node.get("children") or [])
			self_matched = bool(node.get("route") and node.get("route") == selected_route)
			node["active"] = self_matched
			node["open"] = self_matched or child_matched
			matched = matched or node["open"]
		return matched

	walk(menu_tree or [])


def get_active_top_label(menu_tree):
	for node in menu_tree or []:
		if node.get("open") or node.get("active"):
			return node.get("label")
	return None


def fallback_menu_tree():
	return [
		{
			"label": _("Student life"),
			"route": "",
			"href": "",
			"active": False,
			"open": True,
			"children": [
				{
					"label": _("Daily routine"),
					"route": "",
					"href": "",
					"active": False,
					"open": True,
					"children": [
						{
							"label": _("What to send with the child"),
							"route": DEFAULT_SOURCE_ROUTE,
							"href": make_help_href(DEFAULT_SOURCE_ROUTE),
							"children": [],
							"active": True,
							"open": True,
						}
					],
				}
			],
		}
	]


def get_wiki_article(route):
	fields = ["name", "title", "route", "content", "published", "allow_guest"]
	article = get_wiki_page_by_route(route, fields=fields)
	if article:
		return article

	fallback = get_wiki_page_by_route(DEFAULT_SOURCE_ROUTE, fields=fields)
	if fallback:
		fallback["source_note"] = _("Showing the default help article because the selected Wiki Page was not found.")
		return fallback

	return {
		"title": _("Student Life"),
		"route": "",
		"content": _("No published Wiki Page content was found for this prototype."),
		"source_note": _("Ask an administrator to publish a Wiki Page under Std-1-to-10."),
	}


def get_wiki_page_by_route(route, fields=None):
	fields = fields or ["name", "title", "route", "content"]
	try:
		rows = frappe.get_all(
			"Wiki Page",
			filters={"route": normalize_route(route), "published": 1, "allow_guest": 1},
			fields=fields,
			limit_page_length=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Student Life Help: Wiki Page lookup failed")
		return None

	return rows[0] if rows else None


def render_wiki_content(content):
	content = (content or "").strip()
	if not content:
		return "<p>No content found.</p>"

	if _looks_like_html(content):
		return rewrite_file_urls(content)

	for renderer in (_frappe_markdown, _python_markdown):
		try:
			html = renderer(content)
		except Exception:
			continue
		if html:
			return rewrite_file_urls(html)

	return rewrite_file_urls("<p>{}</p>".format(escape(content).replace("\n", "<br>\n")))


def rewrite_file_urls(html):
	return re.sub(
		r'(?P<attr>\s(?:src|href)=["\'])(?P<url>/files/[^"\']+)(?P<quote>["\'])',
		lambda match: "{}{}{}{}".format(match.group("attr"), FILE_ORIGIN, match.group("url"), match.group("quote")),
		html or "",
	)


def _looks_like_html(content):
	return bool(re.search(r"<\s*(div|p|br|h[1-6]|ul|ol|li|table|img|a|strong|em|span)\b", content, re.I))


def _frappe_markdown(content):
	from frappe.utils import markdown

	return markdown(content)


def _python_markdown(content):
	import markdown

	return markdown.markdown(content, extensions=["extra", "nl2br", "sane_lists"])
