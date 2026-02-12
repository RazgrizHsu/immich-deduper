from dsh import dash, htm
from conf import ks

dash.register_page(
	__name__,
	path=f'/404',
	title=f" 404 NotFound " + ks.title,
)

def layout(): return htm.H1("the link is 404 not found")
