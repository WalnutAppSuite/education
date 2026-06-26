import re
from html import escape

import frappe
from frappe import _

no_cache = 1

SOURCE_ROUTE_CANDIDATES = (
	"Std-1-to-10/no-school-bag",
	"Std-1-to-10/what-to-send-with-the-child",
)


def get_context(context):
	context.no_cache = 1
	context.title = _("Student Life Help")
	context.parents = [{"name": _("Home"), "route": "/"}]
	context.show_sidebar = False
	context.logo_url = "/files/Walnut-Logo-2023.png"
	context.help_menu = get_help_menu()
	context.article = get_wiki_article()
	context.article_html = render_wiki_content(context.article.get("content") or "")
	return context


def get_help_menu():
	"""Hardcoded MVP menu. Move this to a DocType when the prototype is accepted."""
	return [
		{
			"label": _("Student life"),
			"open": True,
			"items": [
				{
					"label": _("Exciting features"),
					"open": True,
					"items": [
						{
							"label": _("No School Bag"),
							"active": True,
							"route": "Std-1-to-10/what-to-send-with-the-child",
						},
						{"label": _("Subject wise rooms"), "route": "Std-1-to-10/subject-wise-classroom"},
						{"label": _("Balanced routine"), "route": "Std-1-to-10/daily-routine-walnut-school"},
						{"label": _("Daily sports"), "route": "Std-1-to-10/walnut-sports-leagues-updates"},
						{"label": _("Uniform"), "route": "Std-1-to-10/school-uniform"},
						{"label": _("Events"), "route": "Std-1-to-10/electric-saturday-events-walnut-school"},
					],
				},
				{"label": _("Core subjects")},
				{"label": _("Co-curriculars")},
				{"label": _("Learning system")},
				{"label": _("Cultural Connect")},
				{"label": _("Examinations")},
				{"label": _("Events")},
			],
		}
	]


def get_wiki_article():
	fields = ["name", "title", "route", "content", "published", "allow_guest"]
	filters_common = {"published": 1, "allow_guest": 1}

	for route in SOURCE_ROUTE_CANDIDATES:
		article = _get_first_wiki_page({**filters_common, "route": route}, fields)
		if article:
			if route != "Std-1-to-10/no-school-bag":
				article["prototype_label"] = _("No School Bag")
				article["source_note"] = _(
					"Prototype note: a dedicated 'No School Bag' Wiki Page was not found, so this MVP shows the closest existing article."
				)
			return article

	article = _get_first_wiki_page({**filters_common, "route": ["like", "Std-1-to-10/%"]}, fields)
	if article:
		article["source_note"] = _("Showing the first available published Std-1-to-10 Wiki Page.")
		return article

	return {
		"title": _("Student Life"),
		"route": "",
		"content": _("No published Wiki Page content was found for this prototype."),
		"source_note": _("Ask an administrator to publish a Wiki Page under Std-1-to-10."),
	}


def _get_first_wiki_page(filters, fields):
	try:
		rows = frappe.get_all("Wiki Page", filters=filters, fields=fields, limit_page_length=1)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Student Life Help: Wiki Page lookup failed")
		return None

	return rows[0] if rows else None


def render_wiki_content(content):
	content = (content or "").strip()
	if not content:
		return "<p>No content found.</p>"

	if _looks_like_html(content):
		return content

	for renderer in (_frappe_markdown, _python_markdown):
		try:
			html = renderer(content)
		except Exception:
			continue
		if html:
			return html

	return "<p>{}</p>".format(escape(content).replace("\n", "<br>\n"))


def _looks_like_html(content):
	return bool(re.search(r"<\s*(div|p|br|h[1-6]|ul|ol|li|table|img|a|strong|em|span)\b", content, re.I))


def _frappe_markdown(content):
	from frappe.utils import markdown

	return markdown(content)


def _python_markdown(content):
	import markdown

	return markdown.markdown(content, extensions=["extra", "nl2br", "sane_lists"])
