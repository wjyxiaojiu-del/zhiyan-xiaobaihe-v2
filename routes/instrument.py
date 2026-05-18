"""仪器指南路由"""
from flask import Blueprint, render_template
from data.instrument_meta import INSTRUMENT_META
from data.protocol_meta import PROTOCOL_META
from data.svg_icons import get_instrument_svg

instrument_bp = Blueprint("instrument", __name__)


@instrument_bp.route("/instruments")
def instruments():
    return render_template("instruments.html", instruments=INSTRUMENT_META, svg=get_instrument_svg)


@instrument_bp.route("/instrument/<instrument_id>")
def instrument_detail(instrument_id):
    inst = next((i for i in INSTRUMENT_META if i["id"] == instrument_id), None)
    if not inst:
        return "Instrument not found", 404
    related_protocols = [p for p in PROTOCOL_META if p["id"] in inst.get("protocols", [])]
    svg_html = get_instrument_svg(inst.get("icon", ""))
    return render_template("instrument.html", inst=inst, protocols=related_protocols, svg=svg_html)
