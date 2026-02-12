from typing import Optional
import dash.html as htm
import dash_bootstrap_components as dbc
from util import log
from conf import ks, co
from mod import models

lg = log.get(__name__)

def mkExifRows(asset:models.Asset):
	rows = []

	if asset.jsonExif:
		rows = mkExifGrid(asset.jsonExif.toDict())
		pass

	return rows

def mkExifGrid(dicExif:dict):
	table = []

	for key in ks.defs.exif.keys():
		if key in dicExif and dicExif[key] is not None:
			display_key = ks.defs.exif.get(key, key)

			value = dicExif[key]
			if key == "fileSizeInByte": display_value = co.fmt.size(value)
			elif key == "focalLength" and isinstance(value, (int, float)): display_value = f"{value} mm"
			elif key == "fNumber" and isinstance(value, (int, float)): display_value = f"f/{value}"
			else:
				if not value: continue
				display_value = co.fmt.date(value)

			table.append(
				htm.Tr([
					htm.Td(display_key),
					htm.Td(display_value),
				])
			)

	# for key, value in dicExif.items():
	#     if key not in ks.defs.exif and value is not None:
	#         table.append(
	#             htm.Tr([
	#                 htm.Td(key),
	#                 htm.Td(str(value)),
	#             ])
	#         )

	return table


def mkTipExif(assId, dicExif: Optional[models.AssetExif]):
	if not dicExif: return None

	table = mkExifGrid(dicExif.toDict())

	if len(table) > 0:
		return dbc.Popover(
			dbc.PopoverBody(
				htm.Table(
					htm.Tbody(table),
					className="table-sm table-striped",
					style={
						"backgroundColor": "white",
						"color": "black",
						"width": "100%",
						"borderRadius": "4px"
					}
				),
				style={"maxWidth": "400px", "maxHeight": "400px", "overflow": "auto", "padding": "8px"}
			),
			target={"type": "exif-badge", "index": assId},
			trigger="hover focus",
			placement="auto",
			className="popover-exif-info",
		)

	return None
